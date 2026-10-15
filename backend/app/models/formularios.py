"""Formulários e o snapshot congelado de suas perguntas (doc 02, doc 10)."""

from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, SmallInteger,
    String, Text, UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps
from app.models.enums import (
    BlocoPergunta, EstadoSync, Segmento, StatusFormulario, TipoInstrumento,
    TipoPergunta, tipo_enum,
)


class Formulario(Base, Timestamps):
    """Um instrumento gerado para um período — espelhado em um Google Form.

    20 registros em 2026.2: 17 de turma + 3 institucionais.
    """

    __tablename__ = "formulario"

    id: Mapped[int] = mapped_column(primary_key=True)
    #: Chave pública: é o que vai no QR. Nunca exponha `id`.
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, default=uuid_lib.uuid4
    )
    periodo_letivo_id: Mapped[int] = mapped_column(ForeignKey("periodo_letivo.id"))
    tipo_instrumento: Mapped[TipoInstrumento] = mapped_column(
        tipo_enum(TipoInstrumento, "tipo_instrumento")
    )
    #: Derivado do instrumento, materializado para consulta.
    segmento: Mapped[Segmento] = mapped_column(tipo_enum(Segmento, "segmento"))
    turma_id: Mapped[int | None] = mapped_column(ForeignKey("turma.id"))
    titulo: Mapped[str] = mapped_column(String(220))
    status: Mapped[StatusFormulario] = mapped_column(
        tipo_enum(StatusFormulario, "status_formulario"),
        default=StatusFormulario.RASCUNHO,
    )
    abre_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ── integração Google Forms (doc 10 §6.1) ──────────────────────────────
    google_form_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    google_responder_uri: Mapped[str | None] = mapped_column(Text)
    google_edit_uri: Mapped[str | None] = mapped_column(Text)
    google_revision_id: Mapped[str | None] = mapped_column(String(40))
    #: sha256 da estrutura desejada — se igual, a sincronização não emite request.
    hash_estrutura: Mapped[str | None] = mapped_column(String(64))
    estado_sync: Mapped[EstadoSync] = mapped_column(
        tipo_enum(EstadoSync, "estado_sync"), default=EstadoSync.NAO_CRIADO
    )
    sincronizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: doc 04 §6.1 D2 — segunda fase, quando o instrumento muda no meio do ciclo.
    substitui_formulario_id: Mapped[int | None] = mapped_column(
        ForeignKey("formulario.id")
    )

    turma: Mapped["object | None"] = relationship("Turma")
    itens: Mapped[list[FormularioPergunta]] = relationship(
        back_populates="formulario",
        cascade="all, delete-orphan",
        order_by="FormularioPergunta.ordem",
    )
    submissoes: Mapped[list["object"]] = relationship(
        "Submissao", back_populates="formulario"
    )

    __table_args__ = (
        # Só o instrumento de turma tem turma.
        CheckConstraint(
            "(tipo_instrumento = 'DISCENTE_TURMA' AND turma_id IS NOT NULL)"
            " OR (tipo_instrumento <> 'DISCENTE_TURMA' AND turma_id IS NULL)",
            name="turma_coerente_com_instrumento",
        ),
        CheckConstraint(
            "fecha_em IS NULL OR abre_em IS NULL OR fecha_em > abre_em",
            name="janela_coerente",
        ),
        # Idempotência da geração em lote (RN-25): índices parciais.
        Index(
            "uq_formulario_turma",
            "periodo_letivo_id",
            "turma_id",
            unique=True,
            postgresql_where=text("tipo_instrumento = 'DISCENTE_TURMA'"),
        ),
        Index(
            "uq_formulario_institucional",
            "periodo_letivo_id",
            "tipo_instrumento",
            unique=True,
            postgresql_where=text("tipo_instrumento <> 'DISCENTE_TURMA'"),
        ),
    )


class FormularioPergunta(Base):
    """Snapshot congelado (RN-26).

    Carrega `codigo`, `equivalencia_id` e `dimensao_id` COPIADOS: alterar o banco
    de perguntas depois não reescreve o histórico, e o relatório continua sabendo
    exatamente qual pergunta foi respondida.
    """

    __tablename__ = "formulario_pergunta"

    id: Mapped[int] = mapped_column(primary_key=True)
    formulario_id: Mapped[int] = mapped_column(
        ForeignKey("formulario.id", ondelete="CASCADE")
    )
    pergunta_id: Mapped[int | None] = mapped_column(ForeignKey("pergunta.id"))

    codigo: Mapped[int] = mapped_column(Integer)
    equivalencia_id: Mapped[int] = mapped_column(Integer)
    versao_texto: Mapped[int] = mapped_column(SmallInteger, default=1)
    dimensao_id: Mapped[int] = mapped_column(ForeignKey("dimensao_sinaes.id"))

    #: NULL = bloco institucional; preenchido = bloco de uma matéria.
    oferta_id: Mapped[int | None] = mapped_column(ForeignKey("oferta.id"))
    bloco: Mapped[BlocoPergunta] = mapped_column(tipo_enum(BlocoPergunta, "bloco_pergunta"))
    #: Substitui o sufixo "(Disciplina - Professor)" digitado à mão em 2025.2.
    rotulo_oferta: Mapped[str | None] = mapped_column(String(240))

    texto_snapshot: Mapped[str] = mapped_column(Text)
    tipo_snapshot: Mapped[TipoPergunta] = mapped_column(
        tipo_enum(TipoPergunta, "tipo_pergunta")
    )
    opcoes_snapshot: Mapped[list | None] = mapped_column(JSONB)
    obrigatoria_snapshot: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(Integer)

    # ── ponte com o Google (doc 10 §6.1.1) ─────────────────────────────────
    google_item_id: Mapped[str | None] = mapped_column(String(40))
    #: ⭐ chave da ingestão. Volátil: recriar o item gera id novo.
    google_question_id: Mapped[str | None] = mapped_column(String(40), index=True)

    formulario: Mapped[Formulario] = relationship(back_populates="itens")

    __table_args__ = (
        UniqueConstraint("formulario_id", "ordem", name="formulario_pergunta_ordem"),
        Index("ix_formulario_pergunta_oferta", "formulario_id", "oferta_id"),
        CheckConstraint(
            "(bloco = 'INSTITUCIONAL' AND oferta_id IS NULL)"
            " OR (bloco <> 'INSTITUCIONAL' AND oferta_id IS NOT NULL)",
            name="oferta_coerente_com_bloco",
        ),
    )
