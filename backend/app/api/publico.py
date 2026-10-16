import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import obter_settings
from app.core.errors import NaoEncontrado
from app.db.session import obter_sessao
from app.models import Formulario, StatusFormulario
from app.services.qrcode_service import gerar_qrcode

logger = logging.getLogger(__name__)

router = APIRouter(tags=["público"])


@router.get("/health")
async def health(sessao: AsyncSession = Depends(obter_sessao)) -> dict:
    """Usado pelo health check do Render. Sem autenticação."""
    try:
        await sessao.execute(text("SELECT 1"))
        banco = "ok"
    except Exception as exc:  # noqa: BLE001 - health check não derruba o serviço
        # Engolir a causa cega o diagnóstico: registra no log do serviço.
        logger.warning("health: banco indisponível — %s: %s", type(exc).__name__, exc)
        banco = "indisponivel"
    return {"status": "ok", "banco": banco, "versao": obter_settings().versao}


@router.get("/publico/qrcode/{uuid}")
async def obter_qrcode(
    uuid: UUID,
    formato: str = Query("png", regex="^(png|svg)$"),
    escala: int = Query(10, ge=1, le=20),
    sessao: AsyncSession = Depends(obter_sessao),
):
    """Codifica o google_responder_uri do formulário (doc 05 §3, doc 06 §2)."""
    form = await sessao.scalar(select(Formulario).where(Formulario.uuid == uuid))
    if form is None:
        raise NaoEncontrado("Formulário não encontrado.")

    if form.status == StatusFormulario.RASCUNHO or not form.google_responder_uri:
        # doc 05 §3: QR de formulário RASCUNHO -> 404
        # doc 06 §2: 404 se ainda não foi sincronizado (google_responder_uri nulo)
        raise NaoEncontrado("QR Code indisponível para formulário não sincronizado ou em rascunho.")

    dados_qr = gerar_qrcode(form.google_responder_uri, formato=formato, escala=escala)
    media_type = "image/svg+xml" if formato.lower() == "svg" else "image/png"

    return Response(
        content=dados_qr,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
