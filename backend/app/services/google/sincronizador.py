"""Sincronização do formulário com o Google (doc 10 §6 e §7).

Três garantias que este módulo existe para dar:

1. **Idempotência** — `hash_estrutura` igual ⇒ nenhuma request.
2. **Anonimato** — `emailCollectionType` afirmado E relido; divergência bloqueia.
3. **Congelamento** — formulário com resposta nunca tem a estrutura alterada.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import obter_settings
from app.core.errors import (
    AnonimatoViolado, ConflitoEstado, EstruturaCongelada, NaoEncontrado,
)
from app.models import (
    DimensaoSinaes, EstadoSync, Formulario, ResultadoSync, SincronizacaoLog,
    StatusFormulario, Submissao,
)
from app.services.google.cliente import ClienteGoogleForms
from app.services.google.estrutura import (
    agrupar, mapear_question_ids, para_requests,
)

logger = logging.getLogger(__name__)


async def _dimensoes(s: AsyncSession) -> dict[int, str]:
    return {
        d.id: f"Dimensão {d.numero} — {d.nome_institucional or d.nome}"
        for d in (await s.scalars(select(DimensaoSinaes))).all()
    }


async def _tem_respostas(formulario_id: int, s: AsyncSession) -> int:
    return await s.scalar(
        select(func.count())
        .select_from(Submissao)
        .where(Submissao.formulario_id == formulario_id)
    ) or 0


async def montar_estrutura(formulario: Formulario, s: AsyncSession):
    return agrupar(formulario.titulo, list(formulario.itens), await _dimensoes(s))


async def sincronizar(
    formulario_id: int, s: AsyncSession, cliente=None
) -> dict:
    """Aplica a estrutura desejada no Google. Uma única `batchUpdate`."""
    # `populate_existing` é obrigatório: sem ele, um objeto já no identity map
    # (o caso do lote, que carrega os 20 antes) volta do `get` SEM o eager load,
    # e o primeiro acesso a `.itens` estoura MissingGreenlet.
    formulario = await s.get(
        Formulario,
        formulario_id,
        options=[selectinload(Formulario.itens)],
        populate_existing=True,
    )
    if formulario is None:
        raise NaoEncontrado(f"Formulário {formulario_id} não encontrado.")
    if not formulario.itens:
        raise ConflitoEstado(
            "Formulário sem perguntas no snapshot. Gere o lote antes de sincronizar.",
            {"formulario_id": formulario_id},
        )

    estrutura = await montar_estrutura(formulario, s)
    hash_novo = estrutura.hash()

    if formulario.google_form_id and formulario.hash_estrutura == hash_novo:
        formulario.estado_sync = EstadoSync.SINCRONIZADO
        await _registrar(s, formulario, ResultadoSync.SEM_MUDANCA, 0)
        await s.commit()
        return {
            "resultado": ResultadoSync.SEM_MUDANCA.value,
            "requests": 0,
            "formulario_id": formulario_id,
        }

    # doc 10 §6.4 — editar um form com respostas desloca colunas e corrompe a série.
    respostas = await _tem_respostas(formulario_id, s)
    if respostas and formulario.google_form_id:
        formulario.estado_sync = EstadoSync.CONGELADO
        await _registrar(s, formulario, ResultadoSync.BLOQUEADO, 0)
        await s.commit()
        raise EstruturaCongelada(
            f"O formulário já recebeu {respostas} resposta(s). Alterar a estrutura "
            "agora corromperia a série. Aplique no próximo ciclo ou encerre e "
            "reabra (doc 04 §6.1).",
            {"formulario_id": formulario_id, "submissoes": respostas},
        )

    cliente = cliente or ClienteGoogleForms()
    settings = obter_settings()
    revisao_antes = formulario.google_revision_id
    criado_agora = False

    if not formulario.google_form_id:
        criado = cliente.criar(formulario.titulo)
        formulario.google_form_id = criado["formId"]
        formulario.google_responder_uri = criado.get("responderUri")
        criado_agora = True
        # Grava o id ANTES de qualquer outra chamada. O formulário já existe no
        # Drive; se o passo seguinte falhar e a transação voltar atrás, ele vira
        # órfão — e a próxima tentativa cria um segundo com o mesmo título.
        await s.commit()
        # ⚠️ `forms.create` devolve o formulário JÁ aceitando respostas. Um
        # rascunho no ar é risco duplo: a CPA ainda não revisou, e uma resposta
        # precoce dispara o congelamento (RN-42) de um formulário não aprovado.
        # Fecha na criação; só `publicar`, que exige a janela, reabre (doc 05 §2).
        cliente.publicar(formulario.google_form_id, aceitando=False)
        if settings.google_drive_folder_id:
            cliente.mover_para_pasta(
                formulario.google_form_id, settings.google_drive_folder_id
            )

    atual = cliente.obter(formulario.google_form_id)
    requests = _remover_itens(atual) + para_requests(estrutura)

    resposta = cliente.atualizar(
        formulario.google_form_id,
        requests,
        revision_id=None if criado_agora else atual.get("revisionId"),
    )
    form_google = resposta.get("form", {})

    _gravar_ids(formulario, estrutura, form_google)
    _verificar_anonimato(formulario, cliente)

    formulario.google_responder_uri = (
        form_google.get("responderUri") or formulario.google_responder_uri
    )
    formulario.google_revision_id = form_google.get("revisionId")
    formulario.hash_estrutura = hash_novo
    formulario.estado_sync = EstadoSync.SINCRONIZADO
    formulario.sincronizado_em = datetime.now(timezone.utc)

    await _registrar(
        s,
        formulario,
        ResultadoSync.CRIADO if criado_agora else ResultadoSync.ATUALIZADO,
        len(requests),
        revisao_antes=revisao_antes,
        detalhe=form_google,
    )
    await s.commit()
    return {
        "resultado": (
            ResultadoSync.CRIADO if criado_agora else ResultadoSync.ATUALIZADO
        ).value,
        "requests": len(requests),
        "formulario_id": formulario_id,
        "responder_uri": formulario.google_responder_uri,
    }


def _remover_itens(form_google: dict) -> list[dict]:
    """Apaga os itens atuais, de trás para frente.

    `deleteItem` usa ÍNDICE, não id: apagar de frente para trás faria os
    índices deslizarem e removeria o item errado (doc 10 §6.3).
    """
    total = len(form_google.get("items", []))
    return [
        {"deleteItem": {"location": {"index": i}}} for i in range(total - 1, -1, -1)
    ]


def _gravar_ids(formulario: Formulario, estrutura, form_google: dict) -> None:
    mapa = mapear_question_ids(estrutura, form_google)
    for item in formulario.itens:
        par = mapa.get(item.id)
        if par:
            item.google_item_id, item.google_question_id = par


def _verificar_anonimato(formulario: Formulario, cliente) -> None:
    """Relê o que o Google gravou. Nunca confie no write (doc 10 §5)."""
    conferido = cliente.obter(formulario.google_form_id)
    tipo = (conferido.get("settings") or {}).get("emailCollectionType")
    if tipo not in (None, "DO_NOT_COLLECT"):
        formulario.estado_sync = EstadoSync.DIVERGENTE
        raise AnonimatoViolado(
            "O formulário está coletando e-mail dos respondentes. A publicação "
            "fica bloqueada até que isso seja corrigido no Google.",
            {
                "formulario_id": formulario.id,
                "google_form_id": formulario.google_form_id,
                "emailCollectionType": tipo,
            },
        )


async def _registrar(
    s: AsyncSession,
    formulario: Formulario,
    resultado: ResultadoSync,
    requests: int,
    revisao_antes: str | None = None,
    detalhe: dict | None = None,
) -> None:
    s.add(
        SincronizacaoLog(
            formulario_id=formulario.id,
            resultado=resultado,
            requests_enviadas=requests,
            revision_id_antes=revisao_antes,
            revision_id_depois=formulario.google_revision_id,
            detalhe=detalhe,
        )
    )


async def sincronizar_lote(
    periodo_letivo_id: int, s: AsyncSession, cliente=None
) -> dict:
    """Fila sequencial — nunca paralelize: a cota é por minuto (doc 10 §8)."""
    formularios = (
        await s.scalars(
            select(Formulario)
            .where(Formulario.periodo_letivo_id == periodo_letivo_id)
            .order_by(Formulario.id)
        )
    ).all()
    cliente = cliente or ClienteGoogleForms()

    resumo = {"sincronizados": 0, "sem_mudanca": 0, "bloqueados": [], "erros": []}
    for f in formularios:
        try:
            r = await sincronizar(f.id, s, cliente=cliente)
            if r["resultado"] == ResultadoSync.SEM_MUDANCA.value:
                resumo["sem_mudanca"] += 1
            else:
                resumo["sincronizados"] += 1
        except EstruturaCongelada as e:
            resumo["bloqueados"].append({"id": f.id, "motivo": e.mensagem})
        except (AnonimatoViolado, ConflitoEstado) as e:
            resumo["erros"].append({"id": f.id, "erro": e.codigo, "motivo": e.mensagem})
    return resumo


async def publicar_no_google(
    formulario_id: int, aceitando: bool, s: AsyncSession, cliente=None
) -> dict:
    """Abre ou fecha a janela no Google (doc 10 §7)."""
    formulario = await s.get(Formulario, formulario_id)
    if formulario is None:
        raise NaoEncontrado(f"Formulário {formulario_id} não encontrado.")
    if not formulario.google_form_id:
        raise ConflitoEstado(
            "Sincronize o formulário com o Google antes de publicar.",
            {"formulario_id": formulario_id},
        )

    # doc 05 §2 — este é o caminho que de fato abre o formulário ao aluno;
    # a mesma exigência de janela do `publicar` local vale aqui, senão basta
    # chamar o endpoint do Google para contorná-la.
    if aceitando:
        if not formulario.abre_em or not formulario.fecha_em:
            raise ConflitoEstado(
                "Defina a janela de aplicação (abre_em e fecha_em) antes de "
                "abrir o formulário no Google.",
                {
                    "formulario_id": formulario_id,
                    "abre_em": (
                        formulario.abre_em.isoformat() if formulario.abre_em else None
                    ),
                    "fecha_em": (
                        formulario.fecha_em.isoformat() if formulario.fecha_em else None
                    ),
                },
            )
        if formulario.fecha_em <= formulario.abre_em:
            raise ConflitoEstado(
                "A data de fechamento precisa ser posterior à de abertura.",
                {
                    "abre_em": formulario.abre_em.isoformat(),
                    "fecha_em": formulario.fecha_em.isoformat(),
                },
            )

    cliente = cliente or ClienteGoogleForms()
    _verificar_anonimato(formulario, cliente)
    cliente.publicar(formulario.google_form_id, aceitando)

    formulario.status = (
        StatusFormulario.PUBLICADO if aceitando else StatusFormulario.ENCERRADO
    )
    await s.commit()
    return {
        "formulario_id": formulario_id,
        "status": formulario.status.value,
        "aceitando_respostas": aceitando,
    }
