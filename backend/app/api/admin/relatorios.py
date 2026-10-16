"""Relatórios da CPA (doc 06 §3, doc 08 §3)."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NaoEncontrado
from app.core.security import exigir_admin
from app.db.session import obter_sessao
from app.models import RespostaItem, Segmento
from app.services.relatorios.consultas import (
    adesao, por_dimensao, por_oferta, por_professor, por_questao,
)
from app.services.relatorios.exportacao import exportar_csv

router = APIRouter(dependencies=[Depends(exigir_admin)], tags=["relatórios"])


@router.get("/relatorios/adesao")
async def rel_adesao(
    periodo_letivo_id: int, s: AsyncSession = Depends(obter_sessao)
):
    """Visível DURANTE a janela — só contagens, nunca conteúdo (RN-34)."""
    return await adesao(periodo_letivo_id, s)


@router.get("/relatorios/dimensoes")
async def rel_dimensoes(
    periodo_letivo_id: int,
    segmento: Segmento | None = None,
    s: AsyncSession = Depends(obter_sessao),
):
    """⭐ O relatório que alimenta o documento oficial da CPA."""
    return await por_dimensao(periodo_letivo_id, s, segmento)


@router.get("/relatorios/questoes")
async def rel_questoes(
    periodo_letivo_id: int, s: AsyncSession = Depends(obter_sessao)
):
    """ISG por `codigo` — reproduz a página do painel histórico."""
    return await por_questao(periodo_letivo_id, s)


@router.get("/relatorios/oferta/{oferta_id}")
async def rel_oferta(oferta_id: int, s: AsyncSession = Depends(obter_sessao)):
    resultado = await por_oferta(oferta_id, s)
    if resultado.get("encontrada") is False:
        raise NaoEncontrado("Oferta não encontrada.")
    return resultado


@router.get("/relatorios/professor/{professor_id}")
async def rel_professor(
    professor_id: int,
    periodo_letivo_id: int,
    s: AsyncSession = Depends(obter_sessao),
):
    resultado = await por_professor(professor_id, periodo_letivo_id, s)
    if resultado.get("encontrado") is False:
        raise NaoEncontrado("Professor não encontrado.")
    return resultado


@router.get("/relatorios/exportar.csv")
async def rel_csv(periodo_letivo_id: int, s: AsyncSession = Depends(obter_sessao)):
    conteudo = await exportar_csv(periodo_letivo_id, s)
    return Response(
        content=conteudo,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="cpa_{periodo_letivo_id}.csv"'
            )
        },
    )


@router.patch("/comentarios/{resposta_item_id}")
async def moderar_comentario(
    resposta_item_id: int, oculto: bool, s: AsyncSession = Depends(obter_sessao)
):
    """RN-35 — ocultar comentário ofensivo ou identificável. Nunca apagar."""
    item = await s.get(RespostaItem, resposta_item_id)
    if item is None or item.valor_texto is None:
        raise NaoEncontrado("Comentário não encontrado.")
    item.oculto = oculto
    await s.commit()
    return {"id": resposta_item_id, "oculto": oculto}
