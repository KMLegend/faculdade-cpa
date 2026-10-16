"""Payloads da importação da grade (doc 06 §3)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import StatusImportacao, StatusLinha
from app.schemas.comum import Saida


class ImportacaoSaida(Saida):
    id: int
    periodo_letivo_id: int
    nome_arquivo: str
    hash_arquivo: str
    status: StatusImportacao
    resumo: dict | None
    criado_em: datetime
    aplicada_em: datetime | None


class LinhaSaida(Saida):
    id: int
    aba: str | None
    celula: str | None
    texto_origem: str
    dia_semana: str | None
    horario: str | None
    duracao_horarios: int | None
    turma_proposta: dict | None
    disciplina_proposta: str | None
    professor_proposto: str | None
    disciplina_id_sugerida: int | None
    professor_id_sugerido: int | None
    confianca: float | None
    status: StatusLinha
    motivos: list | None
    decisao_admin: dict | None


class DecisaoLinha(BaseModel):
    """O que o admin decidiu sobre uma linha (doc 07 §3.4)."""

    disciplina_id: int | None = None
    disciplina_nova: str | None = None
    professor_id: int | None = None
    professor_novo: str | None = None
    criar_alias: bool = Field(
        default=True,
        description="Grava a grafia como alias para a próxima importação casar sozinha.",
    )
    status: StatusLinha | None = Field(
        default=None, description="OK confirma a linha; IGNORADA a deixa de fora."
    )


class DiffSaida(BaseModel):
    turmas_novas: list[str]
    turmas_existentes: int
    ofertas_novas: list[str]
    ofertas_existentes: int
    ofertas_desativadas: list[str]
    professores_novos: list[str]
    disciplinas_novas: list[str]
    alocacoes: int
    vazio: bool
