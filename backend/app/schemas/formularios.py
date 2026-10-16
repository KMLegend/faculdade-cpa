"""Payloads de formulários (doc 06 §3)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import (
    BlocoPergunta, EstadoSync, Segmento, StatusFormulario, TipoInstrumento,
    TipoPergunta,
)
from app.schemas.comum import Saida


class JanelaEntrada(BaseModel):
    abre_em: datetime | None = None
    fecha_em: datetime | None = None


class GerarLoteEntrada(BaseModel):
    periodo_letivo_id: int
    janelas: dict[str, JanelaEntrada] | None = Field(
        default=None,
        description="Janela de aplicação por TipoInstrumento (opcional)",
    )


class PublicarLoteEntrada(BaseModel):
    periodo_letivo_id: int | None = None
    tipo_instrumento: TipoInstrumento | None = None


class PublicarLoteSaida(BaseModel):
    publicados: int
    ids: list[int]
    #: Formulários que ficaram de fora e por quê — sem isto o admin vê
    #: "15 publicados" e não sabe que 5 falharam.
    ignorados: list[dict] = []


class ResumoGeracaoSaida(BaseModel):
    criados: int = 0
    #: Rascunhos que tiveram o snapshot refeito. Somar com `criados` esconderia
    #: do admin que um formulário existente foi reescrito.
    regenerados: int = 0
    pulados: int = 0
    sem_oferta: list[dict] = []
    alertas: list[dict] = []


class FormularioItemSaida(Saida):
    id: int
    uuid: UUID
    periodo_letivo_id: int
    tipo_instrumento: TipoInstrumento
    segmento: Segmento
    titulo: str
    turma_id: int | None = None
    turma: str | None = None
    modulo: str | None = None
    status: StatusFormulario
    abre_em: datetime | None = None
    fecha_em: datetime | None = None
    google_form_id: str | None = None
    google_responder_uri: str | None = None
    estado_sync: EstadoSync
    total_ofertas: int = 0
    total_perguntas: int = 0
    tempo_estimado_min: int = 0
    acima_do_limite: bool = False
    submissoes: int = 0
    anonimato_ok: bool = True


class PerguntaPrevia(BaseModel):
    codigo: int
    texto: str
    bloco: BlocoPergunta
    tipo: TipoPergunta


class BlocoInstitucionalPrevia(BaseModel):
    dimensao: int
    nome: str
    perguntas: list[PerguntaPrevia]


class BlocoMateriaPrevia(BaseModel):
    oferta_id: int
    disciplina: str
    professor: str
    perguntas: list[PerguntaPrevia]


class TurmaPrevia(BaseModel):
    id: int
    rotulo: str
    modulo: str | None = None


class FormularioCabecalhoPrevia(BaseModel):
    id: int
    titulo: str
    tipo_instrumento: TipoInstrumento
    segmento: Segmento
    estado_sync: EstadoSync
    acima_do_limite: bool


class DiffPrevia(BaseModel):
    unidade: str
    incluidas: int = 0
    alteradas: int = 0
    removidas: int = 0
    inalteradas: int = 0


class PreviaFormularioSaida(BaseModel):
    formulario: FormularioCabecalhoPrevia
    turma: TurmaPrevia | None = None
    perguntas_institucionais: int
    perguntas_por_materia: int
    total_ofertas: int
    total_perguntas: int
    total_paginas: int
    tempo_estimado_min: int
    blocos_institucionais: list[BlocoInstitucionalPrevia]
    blocos_materia: list[BlocoMateriaPrevia]
    diff: DiffPrevia | None = None


class PreviaPerguntasTurmaEntrada(BaseModel):
    turma_id: int


class PreviaPerguntasTurmaSaida(BaseModel):
    turma_id: int
    total_perguntas: int
    perguntas_institucionais: int
    perguntas_por_materia: int
    total_ofertas: int
    tempo_estimado_min: int
    acima_do_limite: bool
