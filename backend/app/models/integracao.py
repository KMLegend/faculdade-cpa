"""Auditoria da sincronização com o Google Forms (doc 10)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ResultadoSync, tipo_enum


class SincronizacaoLog(Base):
    """Guarda o que foi enviado ao Google em cada sincronização.

    É a rota de recuperação do vínculo `google_question_id → formulario_pergunta`
    quando ele se perde (doc 10 §6.1.2) — e a resposta para "por que esta
    pergunta sumiu do formulário?" meses depois.
    """

    __tablename__ = "sincronizacao_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    formulario_id: Mapped[int] = mapped_column(ForeignKey("formulario.id"))
    executado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resultado: Mapped[ResultadoSync] = mapped_column(
        tipo_enum(ResultadoSync, "resultado_sync")
    )
    requests_enviadas: Mapped[int] = mapped_column(Integer, default=0)
    revision_id_antes: Mapped[str | None] = mapped_column(String(40))
    revision_id_depois: Mapped[str | None] = mapped_column(String(40))
    #: JSON completo do formulário devolvido pelo batchUpdate.
    detalhe: Mapped[dict | None] = mapped_column(JSONB)
