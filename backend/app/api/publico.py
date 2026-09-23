"""Endpoints públicos.

Com a arquitetura Google Forms (doc 10), o respondente nunca toca esta API.
Sobram apenas a saúde do serviço e o QR Code.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import obter_settings
from app.db.session import obter_sessao

router = APIRouter(tags=["público"])


@router.get("/health")
async def health(sessao: AsyncSession = Depends(obter_sessao)) -> dict:
    """Usado pelo health check do Render. Sem autenticação."""
    try:
        await sessao.execute(text("SELECT 1"))
        banco = "ok"
    except Exception:  # noqa: BLE001 - health check não deve derrubar o serviço
        banco = "indisponivel"
    return {"status": "ok", "banco": banco, "versao": obter_settings().versao}
