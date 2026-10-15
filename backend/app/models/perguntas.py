"""Dimensões SINAES, equivalências e o banco de perguntas (doc 02, doc 04)."""

from __future__ import annotations

from sqlalchemy import (
    Boolean, CheckConstraint, ForeignKey, Integer, SmallInteger, String, Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps
from app.models.enums import (
    AplicacaoPergunta, BlocoPergunta, TipoAlvo, TipoInstrumento, TipoPergunta,
    tipo_enum,
)


class EixoSinaes(Base):
    """Os 5 eixos do instrumento de avaliação institucional do INEP."""

    __tablename__ = "eixo_sinaes"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(SmallInteger, unique=True)  # 1–5
    nome: Mapped[str] = mapped_column(String(120))

    dimensoes: Mapped[list[DimensaoSinaes]] = relationship(back_populates="eixo")


class DimensaoSinaes(Base):
    """As 10 dimensões da Lei 10.861/2004.

    `nome_institucional` e `codigo_institucional` preservam a nomenclatura que a
    CPA já publica no Power BI: renomear quebraria a série histórica, que é
    justamente o que o MEC espera ver.
    """

    __tablename__ = "dimensao_sinaes"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(SmallInteger, unique=True)  # 1–10
    nome: Mapped[str] = mapped_column(String(160))
    eixo_id: Mapped[int] = mapped_column(ForeignKey("eixo_sinaes.id"))
    nome_institucional: Mapped[str | None] = mapped_column(String(160))
    codigo_institucional: Mapped[str | None] = mapped_column(String(40))
    descricao: Mapped[str | None] = mapped_column(Text)
    ordem_exibicao: Mapped[int] = mapped_column(Integer, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    eixo: Mapped[EixoSinaes] = relationship(back_populates="dimensoes")

    __table_args__ = (
        CheckConstraint("numero BETWEEN 1 AND 10", name="numero_dimensao_valido"),
    )


class EquivalenciaPergunta(Base, Timestamps):
    """Agrupa a mesma pergunta entre segmentos — 67 grupos (doc 04 §5.1).

    É o que permite comparar públicos de propósito, em vez do cruzamento por
    texto de 2025.2, que fazia isso por acidente.
    """

    __tablename__ = "equivalencia_pergunta"

    id: Mapped[int] = mapped_column(primary_key=True)
    rotulo: Mapped[str] = mapped_column(String(240))
    dimensao_id: Mapped[int] = mapped_column(ForeignKey("dimensao_sinaes.id"))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    dimensao: Mapped[DimensaoSinaes] = relationship()
    perguntas: Mapped[list[Pergunta]] = relationship(back_populates="equivalencia")


class Pergunta(Base, Timestamps):
    """Uma pergunta do banco oficial da CPA.

    `codigo` é a IDENTIDADE PERMANENTE (doc 04 §5.1): atribuído uma vez, nunca
    renumerado, nunca reutilizado. 1–163 vêm do ciclo 2025.2; novas a partir de
    164. A posição no formulário é `ordem_exibicao`, independente do código.
    """

    __tablename__ = "pergunta"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[int] = mapped_column(Integer, unique=True)
    texto: Mapped[str] = mapped_column(Text)
    versao_texto: Mapped[int] = mapped_column(SmallInteger, default=1)
    ordem_exibicao: Mapped[int] = mapped_column(Integer, default=0)

    equivalencia_id: Mapped[int] = mapped_column(
        ForeignKey("equivalencia_pergunta.id")
    )
    dimensao_id: Mapped[int] = mapped_column(ForeignKey("dimensao_sinaes.id"))

    tipo_instrumento: Mapped[TipoInstrumento] = mapped_column(
        tipo_enum(TipoInstrumento, "tipo_instrumento")
    )
    bloco: Mapped[BlocoPergunta] = mapped_column(tipo_enum(BlocoPergunta, "bloco_pergunta"))
    aplicacao: Mapped[AplicacaoPergunta] = mapped_column(
        tipo_enum(AplicacaoPergunta, "aplicacao_pergunta"),
        default=AplicacaoPergunta.TODAS,
    )
    tipo: Mapped[TipoPergunta] = mapped_column(
        tipo_enum(TipoPergunta, "tipo_pergunta"), default=TipoPergunta.LIKERT_5
    )
    opcoes: Mapped[list | None] = mapped_column(JSONB)
    obrigatoria: Mapped[bool] = mapped_column(Boolean, default=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    equivalencia: Mapped[EquivalenciaPergunta] = relationship(back_populates="perguntas")
    dimensao: Mapped[DimensaoSinaes] = relationship()
    vinculos: Mapped[list[PerguntaVinculo]] = relationship(
        back_populates="pergunta", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("codigo > 0", name="codigo_positivo"),
        CheckConstraint("versao_texto >= 1", name="versao_texto_positiva"),
        # RN-17: só o instrumento de turma admite blocos por matéria.
        CheckConstraint(
            "(tipo_instrumento = 'DISCENTE_TURMA'"
            "   AND bloco IN ('INSTITUCIONAL', 'DISCIPLINA', 'PROFESSOR'))"
            " OR (tipo_instrumento <> 'DISCENTE_TURMA' AND bloco = 'INSTITUCIONAL')",
            name="bloco_coerente_com_instrumento",
        ),
        # RN-20: só perguntas repetidas por oferta admitem vínculo específico.
        CheckConstraint(
            "bloco IN ('DISCIPLINA', 'PROFESSOR') OR aplicacao = 'TODAS'",
            name="vinculo_so_em_bloco_de_materia",
        ),
        # MULTIPLA_ESCOLHA_UNICA é o único tipo que carrega opções.
        CheckConstraint(
            "tipo = 'MULTIPLA_ESCOLHA_UNICA' OR opcoes IS NULL",
            name="opcoes_so_em_multipla_escolha",
        ),
    )

    @property
    def por_materia(self) -> bool:
        return self.bloco in (BlocoPergunta.DISCIPLINA, BlocoPergunta.PROFESSOR)


class PerguntaVinculo(Base):
    """Alvos de uma pergunta `ESPECIFICA` (doc 04 §3)."""

    __tablename__ = "pergunta_vinculo"

    id: Mapped[int] = mapped_column(primary_key=True)
    pergunta_id: Mapped[int] = mapped_column(
        ForeignKey("pergunta.id", ondelete="CASCADE")
    )
    alvo_tipo: Mapped[TipoAlvo] = mapped_column(tipo_enum(TipoAlvo, "tipo_alvo"))
    alvo_id: Mapped[int] = mapped_column(Integer)

    pergunta: Mapped[Pergunta] = relationship(back_populates="vinculos")

    __table_args__ = (
        UniqueConstraint(
            "pergunta_id", "alvo_tipo", "alvo_id", name="pergunta_vinculo_alvo"
        ),
    )
