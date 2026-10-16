"""Integração com o Google Forms (doc 06 §3, doc 10)."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import obter_settings
from app.core.errors import NaoEncontrado
from app.core.security import exigir_admin
from app.db.session import obter_sessao
from app.models import EstadoSync, Formulario, SincronizacaoLog
from app.services.google.credenciais import _faltando, configurado
from app.services.google.ingestao import ingerir, ingerir_lote
from app.services.google.sincronizador import (
    montar_estrutura, publicar_no_google, sincronizar, sincronizar_lote,
)

router = APIRouter(dependencies=[Depends(exigir_admin)], tags=["integração Google"])


@router.get("/integracao/status")
async def status(s: AsyncSession = Depends(obter_sessao)) -> dict:
    """Saúde da integração — primeira coisa a olhar quando algo não sincroniza."""
    por_estado = {
        estado.value: await s.scalar(
            select(func.count())
            .select_from(Formulario)
            .where(Formulario.estado_sync == estado)
        )
        for estado in EstadoSync
    }
    ultima = await s.scalar(
        select(SincronizacaoLog).order_by(SincronizacaoLog.id.desc()).limit(1)
    )
    settings = obter_settings()
    return {
        "configurado": configurado(),
        "variaveis_faltando": _faltando(),
        "pasta_drive": settings.google_drive_folder_id or None,
        "formularios_por_estado": por_estado,
        "ultima_sincronizacao": (
            {
                "formulario_id": ultima.formulario_id,
                "resultado": ultima.resultado.value,
                "requests": ultima.requests_enviadas,
                "em": ultima.executado_em.isoformat(),
            }
            if ultima
            else None
        ),
    }


@router.get("/formularios/{formulario_id}/estrutura-google")
async def previa_estrutura(
    formulario_id: int, s: AsyncSession = Depends(obter_sessao)
) -> dict:
    """O que seria enviado ao Google — sem enviar nada."""
    from sqlalchemy.orm import selectinload

    from app.services.google.estrutura import para_requests

    formulario = await s.get(
        Formulario, formulario_id, options=[selectinload(Formulario.itens)]
    )
    if formulario is None:
        raise NaoEncontrado("Formulário não encontrado.")

    estrutura = await montar_estrutura(formulario, s)
    requests = para_requests(estrutura)
    return {
        "titulo": estrutura.titulo,
        "total_perguntas": estrutura.total_perguntas,
        "blocos": [
            {
                "titulo": b.titulo,
                "perguntas": len(b.perguntas),
                "oferta_id": b.oferta_id,
                "dimensao_id": b.dimensao,
            }
            for b in estrutura.blocos
        ],
        "texto_livre": len(estrutura.texto_livre),
        "paginas": len(estrutura.blocos),
        "requests": len(requests),
        "hash_estrutura": estrutura.hash(),
        "ja_sincronizado": formulario.hash_estrutura == estrutura.hash(),
    }


@router.post("/formularios/{formulario_id}/sincronizar")
async def sincronizar_um(formulario_id: int, s: AsyncSession = Depends(obter_sessao)):
    return await sincronizar(formulario_id, s)


@router.post("/periodos/{periodo_letivo_id}/sincronizar")
async def sincronizar_periodo(
    periodo_letivo_id: int, s: AsyncSession = Depends(obter_sessao)
):
    return await sincronizar_lote(periodo_letivo_id, s)


@router.post("/formularios/{formulario_id}/publicar-no-google")
async def abrir_janela(formulario_id: int, s: AsyncSession = Depends(obter_sessao)):
    return await publicar_no_google(formulario_id, True, s)


@router.post("/formularios/{formulario_id}/encerrar-no-google")
async def fechar_janela(formulario_id: int, s: AsyncSession = Depends(obter_sessao)):
    return await publicar_no_google(formulario_id, False, s)


@router.post("/formularios/{formulario_id}/importar-respostas")
async def importar_um(formulario_id: int, s: AsyncSession = Depends(obter_sessao)):
    return await ingerir(formulario_id, s)


@router.post("/periodos/{periodo_letivo_id}/importar-respostas")
async def importar_periodo(
    periodo_letivo_id: int, s: AsyncSession = Depends(obter_sessao)
):
    return await ingerir_lote(periodo_letivo_id, s)
