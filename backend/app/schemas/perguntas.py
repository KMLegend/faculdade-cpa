"""Payloads do banco de perguntas (doc 06 §3)."""

from pydantic import BaseModel, Field

from app.models.enums import (
    AplicacaoPergunta, BlocoPergunta, TipoInstrumento, TipoPergunta,
)
from app.schemas.comum import Saida


class EixoSaida(Saida):
    id: int
    numero: int
    nome: str


class DimensaoSaida(Saida):
    id: int
    numero: int
    nome: str
    nome_institucional: str | None
    eixo_id: int
    ativo: bool


class PerguntaSaida(Saida):
    id: int
    codigo: int
    texto: str
    versao_texto: int
    equivalencia_id: int
    dimensao_id: int
    tipo_instrumento: TipoInstrumento
    bloco: BlocoPergunta
    aplicacao: AplicacaoPergunta
    tipo: TipoPergunta
    obrigatoria: bool
    ordem_exibicao: int
    ativo: bool


class PerguntaEntrada(BaseModel):
    """Criação. O `codigo` NÃO é informado: o sistema atribui o próximo livre."""

    texto: str = Field(min_length=1)
    tipo_instrumento: TipoInstrumento
    bloco: BlocoPergunta
    dimensao_id: int
    equivalencia_id: int | None = Field(
        default=None, description="Nulo cria um grupo de equivalência próprio."
    )
    tipo: TipoPergunta = TipoPergunta.LIKERT_5
    aplicacao: AplicacaoPergunta = AplicacaoPergunta.TODAS
    obrigatoria: bool = True
    ordem_exibicao: int = 0


class PerguntaPatch(BaseModel):
    """Edição.

    `codigo` não aparece aqui de propósito: é imutável (doc 04 §5.1). Mudança de
    sentido do enunciado exige pergunta nova, não edição.
    """

    texto: str | None = None
    #: Obrigatório quando `texto` muda — ver doc 04 §6.1.
    correcao_de_redacao: bool | None = Field(
        default=None,
        description=(
            "true = mesma pergunta, incrementa versao_texto. "
            "false = o sentido mudou; use POST para criar outra."
        ),
    )
    dimensao_id: int | None = None
    obrigatoria: bool | None = None
    ordem_exibicao: int | None = None
    ativo: bool | None = None


class ImpactoPergunta(Saida):
    """Alcance de uma alteração (doc 04 §6.1) — mostrado antes de confirmar."""

    codigo: int
    formularios: int
    publicados: int
    congelados: int
    rascunhos: int
    proximo_codigo_livre: int
