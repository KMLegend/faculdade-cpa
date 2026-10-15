"""Período letivo, curso, professor, disciplina, turma, oferta e alocação (doc 02)."""

from __future__ import annotations

from datetime import time

from sqlalchemy import (
    Boolean, CheckConstraint, ForeignKey, Index, Integer, SmallInteger,
    String, Text, Time, UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps
from app.models.enums import Modalidade, Turno, tipo_enum


class PeriodoLetivo(Base, Timestamps):
    __tablename__ = "periodo_letivo"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True)  # "2026.2"
    ano: Mapped[int] = mapped_column(Integer)
    semestre: Mapped[int] = mapped_column(SmallInteger)
    ativo: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        CheckConstraint("semestre IN (1, 2)", name="semestre_valido"),
        # Índice parcial: no máximo um período ativo por vez (doc 02).
        Index(
            "uq_periodo_letivo_unico_ativo",
            "ativo",
            unique=True,
            postgresql_where=text("ativo"),
        ),
    )


class Curso(Base, Timestamps):
    __tablename__ = "curso"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    turmas: Mapped[list[Turma]] = relationship(back_populates="curso")


class Professor(Base, Timestamps):
    __tablename__ = "professor"

    id: Mapped[int] = mapped_column(primary_key=True)
    #: Primeiro nome, como vem da planilha. Ver RN-14 sobre homônimos.
    nome_exibicao: Mapped[str] = mapped_column(String(120))
    nome_completo: Mapped[str | None] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    email: Mapped[str | None] = mapped_column(String(160))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    aliases: Mapped[list[ProfessorAlias]] = relationship(
        back_populates="professor", cascade="all, delete-orphan"
    )


class Disciplina(Base, Timestamps):
    __tablename__ = "disciplina"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(240))
    slug: Mapped[str] = mapped_column(String(240), unique=True)
    #: NULL = interdisciplinar / ciclo básico.
    curso_id: Mapped[int | None] = mapped_column(ForeignKey("curso.id"))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    aliases: Mapped[list[DisciplinaAlias]] = relationship(
        back_populates="disciplina", cascade="all, delete-orphan"
    )


class ProfessorAlias(Base, Timestamps):
    """Grafias já conciliadas — faz a importação melhorar a cada semestre."""

    __tablename__ = "professor_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    professor_id: Mapped[int] = mapped_column(
        ForeignKey("professor.id", ondelete="CASCADE")
    )
    texto_origem: Mapped[str] = mapped_column(String(240))
    slug_origem: Mapped[str] = mapped_column(String(240), unique=True)

    professor: Mapped[Professor] = relationship(back_populates="aliases")


class DisciplinaAlias(Base, Timestamps):
    __tablename__ = "disciplina_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    disciplina_id: Mapped[int] = mapped_column(
        ForeignKey("disciplina.id", ondelete="CASCADE")
    )
    texto_origem: Mapped[str] = mapped_column(String(240))
    slug_origem: Mapped[str] = mapped_column(String(240), unique=True)

    disciplina: Mapped[Disciplina] = relationship(back_populates="aliases")


class Turma(Base, Timestamps):
    """RN-04 — a chave é (período, curso, turno, período_numero).

    Módulo e rótulo ficam FORA da chave: são recortes operacionais da mesma
    turma de alunos. Incluí-los inflaria 17 turmas para 21 e entregaria dois
    formulários aos mesmos alunos.
    """

    __tablename__ = "turma"

    id: Mapped[int] = mapped_column(primary_key=True)
    periodo_letivo_id: Mapped[int] = mapped_column(ForeignKey("periodo_letivo.id"))
    curso_id: Mapped[int] = mapped_column(ForeignKey("curso.id"))
    turno: Mapped[Turno] = mapped_column(tipo_enum(Turno, "turno"))
    periodo_numero: Mapped[int] = mapped_column(SmallInteger)

    modulo: Mapped[str | None] = mapped_column(String(120))
    rotulos_origem: Mapped[list | None] = mapped_column(JSONB)
    abas_origem: Mapped[list | None] = mapped_column(JSONB)
    colunas_origem: Mapped[list | None] = mapped_column(JSONB)
    compartilhada_ciclo_basico: Mapped[bool] = mapped_column(Boolean, default=False)
    total_alunos: Mapped[int | None] = mapped_column(Integer)
    observacao: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    curso: Mapped[Curso] = relationship(back_populates="turmas")
    ofertas_turma: Mapped[list[OfertaTurma]] = relationship(back_populates="turma")

    __table_args__ = (
        UniqueConstraint(
            "periodo_letivo_id",
            "curso_id",
            "turno",
            "periodo_numero",
            name="turma_chave_rn04",
        ),
        CheckConstraint("periodo_numero > 0", name="periodo_numero_positivo"),
    )

    @property
    def rotulo(self) -> str:
        return (
            f"{self.curso.nome} · {self.turno.value.title()} · "
            f"{self.periodo_numero}º período"
        )


class Oferta(Base, Timestamps):
    """RN-09 — a unidade avaliada: (disciplina, professor) no período.

    ⚠️ `turma_id` NÃO existe aqui. A relação com turma é N:N, em `oferta_turma`.
    """

    __tablename__ = "oferta"

    id: Mapped[int] = mapped_column(primary_key=True)
    periodo_letivo_id: Mapped[int] = mapped_column(ForeignKey("periodo_letivo.id"))
    disciplina_id: Mapped[int] = mapped_column(ForeignKey("disciplina.id"))
    professor_id: Mapped[int] = mapped_column(ForeignKey("professor.id"))
    #: RN-15 — TCC, estágio e optativas nascem não avaliáveis.
    avaliavel: Mapped[bool] = mapped_column(Boolean, default=True)
    observacao: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    disciplina: Mapped[Disciplina] = relationship()
    professor: Mapped[Professor] = relationship()
    ofertas_turma: Mapped[list[OfertaTurma]] = relationship(
        back_populates="oferta", cascade="all, delete-orphan"
    )
    alocacoes: Mapped[list[Alocacao]] = relationship(
        back_populates="oferta", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "periodo_letivo_id",
            "disciplina_id",
            "professor_id",
            name="oferta_chave_rn09",
        ),
        Index("ix_oferta_professor_periodo", "professor_id", "periodo_letivo_id"),
        Index("ix_oferta_disciplina", "disciplina_id"),
    )

    @property
    def rotulo(self) -> str:
        return f"{self.disciplina.nome} · Prof. {self.professor.nome_exibicao}"


class OfertaTurma(Base):
    """RN-07 — quais turmas cursam a oferta. 27 das 105 têm mais de uma."""

    __tablename__ = "oferta_turma"

    id: Mapped[int] = mapped_column(primary_key=True)
    oferta_id: Mapped[int] = mapped_column(
        ForeignKey("oferta.id", ondelete="CASCADE")
    )
    turma_id: Mapped[int] = mapped_column(ForeignKey("turma.id", ondelete="CASCADE"))

    oferta: Mapped[Oferta] = relationship(back_populates="ofertas_turma")
    turma: Mapped[Turma] = relationship(back_populates="ofertas_turma")

    __table_args__ = (UniqueConstraint("oferta_id", "turma_id", name="oferta_turma_par"),)


class Alocacao(Base):
    """A grade horária propriamente dita — auditoria, não usada na avaliação.

    Mescla vertical na planilha vira UMA alocação com `duracao_horarios = N`.
    """

    __tablename__ = "alocacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    oferta_id: Mapped[int] = mapped_column(ForeignKey("oferta.id", ondelete="CASCADE"))
    turma_id: Mapped[int | None] = mapped_column(ForeignKey("turma.id"))
    dia_semana: Mapped[int | None] = mapped_column(SmallInteger)  # 1=Seg … 6=Sáb
    horario_rotulo: Mapped[str | None] = mapped_column(String(40))
    horario_inicio: Mapped[time | None] = mapped_column(Time)
    duracao_horarios: Mapped[int] = mapped_column(SmallInteger, default=1)
    modalidade: Mapped[Modalidade] = mapped_column(
        tipo_enum(Modalidade, "modalidade"), default=Modalidade.NAO_INFORMADA
    )
    aba_origem: Mapped[str | None] = mapped_column(String(80))
    celula_origem: Mapped[str | None] = mapped_column(String(12))
    #: RN-11 — sempre preenchido, é a rastreabilidade da importação.
    texto_origem: Mapped[str] = mapped_column(Text)

    oferta: Mapped[Oferta] = relationship(back_populates="alocacoes")

    __table_args__ = (
        CheckConstraint(
            "dia_semana IS NULL OR dia_semana BETWEEN 1 AND 7", name="dia_semana_valido"
        ),
        CheckConstraint("duracao_horarios >= 1", name="duracao_positiva"),
    )
