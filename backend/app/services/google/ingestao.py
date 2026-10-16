"""Ingestão das respostas do Google (doc 10 §9).

Substitui o `main.py` de 2025.2, que baixava 17 CSVs por URL de exportação e
casava pergunta com dimensão **pelo texto** — misturando segmentos em silêncio.
Aqui cada resposta chega por `google_question_id`, que aponta para exatamente
uma `formulario_pergunta`, e ela já carrega `codigo`, `equivalencia_id`,
`dimensao_id` e `oferta_id`.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflitoEstado, NaoEncontrado
from app.models import (
    Formulario, FormularioPergunta, RespostaItem, Submissao, TipoPergunta,
)
from app.services.google.cliente import ClienteGoogleForms

logger = logging.getLogger(__name__)

LIMITE_TEXTO = 2000


def _data_de(resposta: dict):
    """Só a DATA — hora permitiria cruzar com a lista de presença (RN-31)."""
    bruto = resposta.get("lastSubmittedTime") or resposta.get("createTime")
    if not bruto:
        return datetime.now().date()
    return datetime.fromisoformat(bruto.replace("Z", "+00:00")).date()


def _valor(pergunta: FormularioPergunta, resposta_item: dict):
    """Extrai (numérico, texto) conforme o tipo congelado no snapshot."""
    respostas = resposta_item.get("textAnswers", {}).get("answers", [])
    if not respostas:
        return None, None
    bruto = (respostas[0].get("value") or "").strip()
    if not bruto:
        return None, None

    if pergunta.tipo_snapshot is TipoPergunta.TEXTO_LIVRE:
        return None, bruto[:LIMITE_TEXTO]
    if pergunta.tipo_snapshot is TipoPergunta.SIM_NAO:
        return (1 if bruto.lower() in ("sim", "yes", "1", "true") else 0), None
    try:
        return int(bruto), None
    except ValueError:
        # Likert com rótulo textual: guarda o texto em vez de descartar.
        return None, bruto[:LIMITE_TEXTO]


async def ingerir(formulario_id: int, s: AsyncSession, cliente=None) -> dict:
    """Puxa respostas novas. Idempotente por `google_response_id`."""
    formulario = await s.get(
        Formulario, formulario_id, options=[selectinload(Formulario.itens)]
    )
    if formulario is None:
        raise NaoEncontrado(f"Formulário {formulario_id} não encontrado.")
    if not formulario.google_form_id:
        raise ConflitoEstado(
            "Formulário ainda não sincronizado com o Google.",
            {"formulario_id": formulario_id},
        )

    por_question_id = {
        item.google_question_id: item
        for item in formulario.itens
        if item.google_question_id
    }
    if not por_question_id:
        raise ConflitoEstado(
            "Nenhum `google_question_id` registrado. Sincronize antes de ingerir.",
            {"formulario_id": formulario_id},
        )

    ja_importadas = set(
        (
            await s.scalars(
                select(Submissao.google_response_id).where(
                    Submissao.formulario_id == formulario_id
                )
            )
        ).all()
    )

    cliente = cliente or ClienteGoogleForms()
    novas = duplicadas = 0
    orfas: list[dict] = []
    cursor = None

    while True:
        pagina = cliente.listar_respostas(formulario.google_form_id, None, cursor)
        for resposta in pagina.get("responses", []):
            id_google = resposta.get("responseId")
            if not id_google or id_google in ja_importadas:
                duplicadas += 1
                continue

            submissao = Submissao(
                formulario_id=formulario_id,
                data_envio=_data_de(resposta),
                google_response_id=id_google,
            )
            s.add(submissao)
            await s.flush()

            for question_id, item_resposta in (resposta.get("answers") or {}).items():
                pergunta = por_question_id.get(question_id)
                if pergunta is None:
                    # Alguém editou o formulário à mão. NÃO tente casar por
                    # texto: foi assim que o pipeline de 2025.2 se contaminou.
                    orfas.append(
                        {"response_id": id_google, "question_id": question_id}
                    )
                    continue
                numerico, texto = _valor(pergunta, item_resposta)
                if numerico is None and texto is None:
                    continue
                s.add(
                    RespostaItem(
                        submissao_id=submissao.id,
                        formulario_pergunta_id=pergunta.id,
                        valor_numerico=numerico,
                        valor_texto=texto,
                    )
                )
            ja_importadas.add(id_google)
            novas += 1

        cursor = pagina.get("nextPageToken")
        if not cursor:
            break

    await s.commit()

    if orfas:
        logger.warning(
            "ingestão: %d resposta(s) órfã(s) no formulário %s — estrutura divergente",
            len(orfas), formulario_id,
        )
    return {
        "formulario_id": formulario_id,
        "novas": novas,
        "ja_importadas": duplicadas,
        "orfas": len(orfas),
        "detalhe_orfas": orfas[:20],
    }


async def ingerir_lote(periodo_letivo_id: int, s: AsyncSession, cliente=None) -> dict:
    formularios = (
        await s.scalars(
            select(Formulario).where(
                Formulario.periodo_letivo_id == periodo_letivo_id,
                Formulario.google_form_id.isnot(None),
            )
        )
    ).all()
    cliente = cliente or ClienteGoogleForms()

    total = {"novas": 0, "ja_importadas": 0, "orfas": 0, "formularios": 0, "erros": []}
    for f in formularios:
        try:
            r = await ingerir(f.id, s, cliente=cliente)
            total["novas"] += r["novas"]
            total["ja_importadas"] += r["ja_importadas"]
            total["orfas"] += r["orfas"]
            total["formularios"] += 1
        except ConflitoEstado as e:
            total["erros"].append({"id": f.id, "motivo": e.mensagem})
    return total
