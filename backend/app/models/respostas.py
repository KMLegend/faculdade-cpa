"""Submissões anônimas e itens de resposta (doc 02, RN-31).

⚠️ Esta é a parte do schema onde o anonimato é estrutural. NÃO acrescente IP,
e-mail, matrícula, `user_agent` nem hora — só a DATA do envio.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Boolean, CheckConstraint, Date, ForeignKey, Index, SmallInteger, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Submissao(Base):
    """Um envio anônimo completo."""

    __tablename__ = "submissao"

    id: Mapped[int] = mapped_column(primary_key=True)
    formulario_id: Mapped[int] = mapped_column(ForeignKey("formulario.id"))
    #: ⚠️ DATE, não timestamp: hora permitiria cruzar com a lista de presença.
    data_envio: Mapped[date] = mapped_column(Date)
    #: Id opaco do Google — torna a ingestão idempotente. Não identifica pessoa.
    google_response_id: Mapped[str] = mapped_column(String(80), unique=True)

    formulario: Mapped["object"] = relationship("Formulario", back_populates="submissoes")
    itens: Mapped[list[RespostaItem]] = relationship(
        back_populates="submissao", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_submissao_formulario", "formulario_id"),)


class RespostaItem(Base):
    __tablename__ = "resposta_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    submissao_id: Mapped[int] = mapped_column(
        ForeignKey("submissao.id", ondelete="CASCADE")
    )
    formulario_pergunta_id: Mapped[int] = mapped_column(
        ForeignKey("formulario_pergunta.id")
    )
    valor_numerico: Mapped[int | None] = mapped_column(SmallInteger)
    valor_texto: Mapped[str | None] = mapped_column(Text)
    #: Moderação de comentário (RN-35). Nunca apagar.
    oculto: Mapped[bool] = mapped_column(Boolean, default=False)

    submissao: Mapped[Submissao] = relationship(back_populates="itens")

    __table_args__ = (
        UniqueConstraint(
            "submissao_id", "formulario_pergunta_id", name="resposta_item_unica"
        ),
        CheckConstraint(
            "valor_numerico IS NOT NULL OR valor_texto IS NOT NULL",
            name="resposta_tem_valor",
        ),
        CheckConstraint(
            "valor_numerico IS NULL OR valor_numerico BETWEEN 0 AND 5",
            name="valor_numerico_na_escala",
        ),
        # Índice da agregação: o relatório soma por pergunta do snapshot.
        Index("ix_resposta_item_pergunta", "formulario_pergunta_id"),
    )
