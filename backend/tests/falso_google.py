"""Cliente falso da Forms API — permite testar a Fase 5 sem credenciais.

Reproduz o contrato de `ClienteForms`: guarda os formulários em memória,
atribui `itemId`/`questionId` como o Google faria e registra o que foi
chamado, para os testes afirmarem sobre as requests enviadas.
"""

from __future__ import annotations

import itertools
from typing import Any


class FalsoGoogleForms:
    def __init__(
        self,
        email_collection: str = "DO_NOT_COLLECT",
        email_collection_fixo: bool = False,
    ) -> None:
        #: `fixo` simula o caso real que importa: alguém ligou a coleta de
        #: e-mail na interface (ou uma política do Workspace a força) e o nosso
        #: `updateSettings` NÃO gruda. É só relendo que se descobre.
        self.email_collection_fixo = email_collection_fixo
        self.formularios: dict[str, dict] = {}
        self.chamadas: list[tuple[str, Any]] = []
        self.respostas: dict[str, list[dict]] = {}
        self._seq = itertools.count(1)
        #: Para simular alguém ligando a coleta de e-mail na interface.
        self.email_collection = email_collection

    # ── contrato ────────────────────────────────────────────────────────────
    def criar(self, titulo: str) -> dict:
        form_id = f"form{next(self._seq)}"
        self.formularios[form_id] = {
            "formId": form_id,
            "info": {"title": titulo},
            "items": [],
            "revisionId": "r1",
            "responderUri": f"https://docs.google.com/forms/d/e/{form_id}/viewform",
            "settings": {"emailCollectionType": self.email_collection},
        }
        self.chamadas.append(("criar", titulo))
        return self.formularios[form_id]

    def obter(self, form_id: str) -> dict:
        self.chamadas.append(("obter", form_id))
        return self.formularios[form_id]

    def atualizar(
        self, form_id: str, requests: list[dict], revision_id: str | None = None
    ) -> dict:
        form = self.formularios[form_id]
        if revision_id and revision_id != form["revisionId"]:
            from googleapiclient.errors import HttpError  # pragma: no cover

            raise AssertionError("revisão desatualizada")

        self.chamadas.append(("atualizar", len(requests)))
        for req in requests:
            if "deleteItem" in req:
                indice = req["deleteItem"]["location"]["index"]
                if 0 <= indice < len(form["items"]):
                    form["items"].pop(indice)
            elif "createItem" in req:
                form["items"].append(self._materializar(req["createItem"]["item"]))
            elif "updateSettings" in req:
                if not self.email_collection_fixo:
                    form["settings"].update(req["updateSettings"]["settings"])
            elif "updateFormInfo" in req:
                form["info"].update(req["updateFormInfo"]["info"])

        form["revisionId"] = f"r{len(self.chamadas)}"
        return {"form": form}

    def publicar(self, form_id: str, aceitando: bool) -> dict:
        self.chamadas.append(("publicar", (form_id, aceitando)))
        self.formularios[form_id]["publishSettings"] = {
            "publishState": {"isPublished": True, "isAcceptingResponses": aceitando}
        }
        return self.formularios[form_id]

    def listar_respostas(
        self, form_id: str, filtro: str | None = None, cursor: str | None = None
    ) -> dict:
        self.chamadas.append(("listar_respostas", form_id))
        return {"responses": self.respostas.get(form_id, [])}

    def mover_para_pasta(self, form_id: str, pasta_id: str) -> None:
        self.chamadas.append(("mover", (form_id, pasta_id)))

    # ── apoio aos testes ────────────────────────────────────────────────────
    def _materializar(self, item: dict) -> dict:
        novo = dict(item)
        novo["itemId"] = f"i{next(self._seq)}"
        if "questionGroupItem" in novo:
            grupo = dict(novo["questionGroupItem"])
            grupo["questions"] = [
                {**q, "questionId": f"q{next(self._seq)}"}
                for q in grupo.get("questions", [])
            ]
            novo["questionGroupItem"] = grupo
        elif "questionItem" in novo:
            q = dict(novo["questionItem"]["question"])
            q["questionId"] = f"q{next(self._seq)}"
            novo["questionItem"] = {"question": q}
        return novo

    def question_ids(self, form_id: str) -> list[str]:
        ids: list[str] = []
        for item in self.formularios[form_id]["items"]:
            if "questionGroupItem" in item:
                ids += [
                    q["questionId"]
                    for q in item["questionGroupItem"]["questions"]
                ]
            elif "questionItem" in item:
                ids.append(item["questionItem"]["question"]["questionId"])
        return ids

    def semear_resposta(self, form_id: str, valores: dict[str, str], id_: str) -> None:
        """Registra uma resposta como o Google a devolveria."""
        self.respostas.setdefault(form_id, []).append(
            {
                "responseId": id_,
                "lastSubmittedTime": "2026-11-24T16:32:48.000Z",
                "answers": {
                    qid: {"textAnswers": {"answers": [{"value": v}]}}
                    for qid, v in valores.items()
                },
            }
        )
