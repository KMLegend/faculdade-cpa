"""Payloads dos cadastros acadêmicos (doc 06 §3)."""

from pydantic import BaseModel, Field

from app.models.enums import Turno
from app.schemas.comum import Saida


class CursoSaida(Saida):
    id: int
    nome: str
    slug: str
    ativo: bool


class ProfessorSaida(Saida):
    id: int
    nome_exibicao: str
    nome_completo: str | None
    slug: str
    email: str | None
    ativo: bool
    ofertas: int = 0


class ProfessorEntrada(BaseModel):
    nome_exibicao: str = Field(min_length=1, max_length=120)
    nome_completo: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=160)


class ProfessorPatch(BaseModel):
    nome_exibicao: str | None = Field(default=None, min_length=1, max_length=120)
    nome_completo: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=160)
    ativo: bool | None = None


class DisciplinaSaida(Saida):
    id: int
    nome: str
    slug: str
    curso_id: int | None
    ativo: bool


class DisciplinaEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=240)
    curso_id: int | None = None


class DisciplinaPatch(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=240)
    curso_id: int | None = None
    ativo: bool | None = None


class PeriodoLetivoSaida(Saida):
    id: int
    codigo: str
    ano: int
    semestre: int
    ativo: bool


class TurmaSaida(Saida):
    id: int
    curso_id: int
    #: Campos de exibição — o painel não deve precisar resolver ids (doc 06).
    curso: str | None = None
    rotulo: str | None = None
    turno: Turno
    periodo_numero: int
    modulo: str | None
    rotulos_origem: list | None
    colunas_origem: list | None
    compartilhada_ciclo_basico: bool
    total_alunos: int | None
    total_ofertas: int = 0
    total_perguntas: int = 0
    ativo: bool


class OfertaSaida(Saida):
    id: int
    disciplina_id: int
    professor_id: int
    disciplina: str | None = None
    professor: str | None = None
    rotulo: str | None = None
    turmas: list[int] = []
    qtd_turmas: int = 0
    avaliavel: bool
    ativo: bool


class OfertaPatch(BaseModel):
    """RN-15 — alternar se a oferta entra na avaliação."""

    avaliavel: bool | None = None
    observacao: str | None = None
    ativo: bool | None = None
