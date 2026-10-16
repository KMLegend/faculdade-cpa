"""Cliente da Forms API, com backoff e respeito às cotas (doc 10 §8).

Cotas: 375 escritas/min/projeto, 150/min/usuário. Uma sincronização completa
usa ~60 requisições — folgado, desde que cada formulário gaste UM `batchUpdate`.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Protocol

from app.core.errors import CotaExcedida, CredencialInvalida, RevisaoDesatualizada
from app.services.google.credenciais import obter_credenciais

logger = logging.getLogger(__name__)

TENTATIVAS = 5
ESPERA_BASE = 1.0


class ClienteForms(Protocol):
    """Contrato mínimo — permite substituir por um falso nos testes."""

    def criar(self, titulo: str) -> dict: ...
    def obter(self, form_id: str) -> dict: ...
    def atualizar(self, form_id: str, requests: list[dict], revision_id: str | None) -> dict: ...
    def publicar(self, form_id: str, aceitando: bool) -> dict: ...
    def listar_respostas(self, form_id: str, filtro: str | None, cursor: str | None) -> dict: ...
    def mover_para_pasta(self, form_id: str, pasta_id: str) -> None: ...


def _com_retentativa(operacao, descricao: str):
    """Backoff exponencial com jitter em 429 e 5xx (doc 10 §8)."""
    from googleapiclient.errors import HttpError

    for tentativa in range(TENTATIVAS):
        try:
            return operacao()
        except HttpError as erro:
            status = getattr(erro.resp, "status", None)
            if status == 400 and b"revision" in (erro.content or b"").lower():
                raise RevisaoDesatualizada(
                    "O formulário foi alterado no Google desde a última leitura. "
                    "Releia antes de sincronizar.",
                    {"detalhe": erro.reason},
                ) from erro
            if status in (401, 403) and "insufficient" not in str(erro).lower():
                raise CredencialInvalida(
                    "O Google recusou a credencial. Regere o refresh token (Anexo C).",
                    {"status": status, "detalhe": erro.reason},
                ) from erro
            if status == 429 or (status and 500 <= status < 600):
                if tentativa == TENTATIVAS - 1:
                    raise CotaExcedida(
                        "O Google recusou por excesso de requisições. Tente em alguns "
                        "minutos.",
                        {"status": status},
                    ) from erro
                espera = ESPERA_BASE * (2**tentativa) + random.uniform(0, 0.5)
                logger.warning(
                    "google: %s devolveu %s; nova tentativa em %.1fs",
                    descricao, status, espera,
                )
                time.sleep(espera)
                continue
            raise


class ClienteGoogleForms:
    """Implementação real sobre `googleapiclient`."""

    def __init__(self, credenciais: Any | None = None) -> None:
        from googleapiclient.discovery import build

        cred = credenciais or obter_credenciais()
        self._forms = build("forms", "v1", credentials=cred, cache_discovery=False)
        self._drive = build("drive", "v3", credentials=cred, cache_discovery=False)

    def criar(self, titulo: str) -> dict:
        return _com_retentativa(
            lambda: self._forms.forms()
            .create(body={"info": {"title": titulo, "documentTitle": titulo}})
            .execute(),
            "forms.create",
        )

    def obter(self, form_id: str) -> dict:
        return _com_retentativa(
            lambda: self._forms.forms().get(formId=form_id).execute(), "forms.get"
        )

    def atualizar(
        self, form_id: str, requests: list[dict], revision_id: str | None = None
    ) -> dict:
        corpo: dict[str, Any] = {
            "requests": requests,
            "includeFormInResponse": True,
        }
        if revision_id:
            # Se alguém editou à mão no Google, falha em vez de sobrescrever.
            corpo["writeControl"] = {"requiredRevisionId": revision_id}
        return _com_retentativa(
            lambda: self._forms.forms()
            .batchUpdate(formId=form_id, body=corpo)
            .execute(),
            "forms.batchUpdate",
        )

    def publicar(self, form_id: str, aceitando: bool) -> dict:
        return _com_retentativa(
            lambda: self._forms.forms()
            .setPublishSettings(
                formId=form_id,
                body={
                    "publishSettings": {
                        "publishState": {
                            "isPublished": True,
                            "isAcceptingResponses": aceitando,
                        }
                    },
                    "updateMask": "publishState",
                },
            )
            .execute(),
            "forms.setPublishSettings",
        )

    def listar_respostas(
        self, form_id: str, filtro: str | None = None, cursor: str | None = None
    ) -> dict:
        parametros: dict[str, Any] = {"formId": form_id}
        if filtro:
            parametros["filter"] = filtro
        if cursor:
            parametros["pageToken"] = cursor
        return _com_retentativa(
            lambda: self._forms.forms().responses().list(**parametros).execute(),
            "forms.responses.list",
        )

    def mover_para_pasta(self, form_id: str, pasta_id: str) -> None:
        if not pasta_id:
            return
        atual = _com_retentativa(
            lambda: self._drive.files()
            .get(fileId=form_id, fields="parents")
            .execute(),
            "drive.files.get",
        )
        anteriores = ",".join(atual.get("parents", []))
        _com_retentativa(
            lambda: self._drive.files()
            .update(fileId=form_id, addParents=pasta_id, removeParents=anteriores)
            .execute(),
            "drive.files.update",
        )
