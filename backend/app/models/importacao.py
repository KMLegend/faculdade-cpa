"""Staging da importação da grade (doc 03, RN-13).

Nada é gravado no domínio enquanto a conciliação não for aplicada.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime, ForeignKey, Index, Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps
from app.models.enums import Modalidade, StatusImportacao, StatusLinha, tipo_enum


class ImportacaoGrade(Base, Timestamps):
    __tablename__ = "importacao_grade"

    id: Mapped[int] = mapped_column(primary_key=True)
    periodo_letivo_id: Mapped[int] = mapped_column(ForeignKey("periodo_letivo.id"))
    nome_arquivo: Mapped[str] = mapped_column(String(200))
    #: sha256 — detecta reimportação do mesmo arquivo.
    hash_arquivo: Mapped[str] = mapped_column(String(64))
    status: Mapped[StatusImportacao] = mapped_column(
        tipo_enum(StatusImportacao, "status_importacao"),
        default=StatusImportacao.PROCESSANDO,
    )
    resumo: Mapped[dict | None] = mapped_column(JSONB)
    aplicada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    linhas: Mapped[list[ImportacaoLinha]] = relationship(
        back_populates="importacao", cascade="all, delete-orphan"
    )


class ImportacaoLinha(Base):
    """Uma alocação interpretada, aguardando decisão humana."""

    __tablename__ = "importacao_linha"

    id: Mapped[int] = mapped_column(primary_key=True)
    importacao_id: Mapped[int] = mapped_column(
        ForeignKey("importacao_grade.id", ondelete="CASCADE")
    )
    aba: Mapped[str | None] = mapped_column(String(80))
    celula: Mapped[str | None] = mapped_column(String(12))
    texto_origem: Mapped[str] = mapped_column(Text)

    dia_semana: Mapped[str | None] = mapped_column(String(40))
    horario: Mapped[str | None] = mapped_column(String(40))
    duracao_horarios: Mapped[int | None] = mapped_column()

    turma_proposta: Mapped[dict | None] = mapped_column(JSONB)
    disciplina_proposta: Mapped[str | None] = mapped_column(String(240))
    professor_proposto: Mapped[str | None] = mapped_column(String(120))
    modalidade_proposta: Mapped[Modalidade | None] = mapped_column(
        tipo_enum(Modalidade, "modalidade")
    )

    disciplina_id_sugerida: Mapped[int | None] = mapped_column(
        ForeignKey("disciplina.id")
    )
    professor_id_sugerido: Mapped[int | None] = mapped_column(ForeignKey("professor.id"))
    confianca: Mapped[float | None] = mapped_column(Numeric(4, 3))

    status: Mapped[StatusLinha] = mapped_column(
        tipo_enum(StatusLinha, "status_linha"), default=StatusLinha.OK
    )
    motivos: Mapped[list | None] = mapped_column(JSONB)
    decisao_admin: Mapped[dict | None] = mapped_column(JSONB)

    importacao: Mapped[ImportacaoGrade] = relationship(back_populates="linhas")

    __table_args__ = (Index("ix_importacao_linha_status", "importacao_id", "status"),)
