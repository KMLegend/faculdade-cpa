"""Enums do domínio (doc 02).

Todos viram tipo nativo no Postgres. O `values_callable` abaixo faz o SQLAlchemy
gravar o VALOR do membro (`"MATUTINO"`), não o nome do atributo — sem isso, uma
renomeação de atributo em Python mudaria silenciosamente o dado no banco.
"""

from enum import Enum

import sqlalchemy as sa


def tipo_enum(enum_cls: type[Enum], nome: str) -> sa.Enum:
    return sa.Enum(
        enum_cls,
        name=nome,
        values_callable=lambda e: [m.value for m in e],
        native_enum=True,
    )


class Turno(str, Enum):
    MATUTINO = "MATUTINO"
    NOTURNO = "NOTURNO"


class Segmento(str, Enum):
    DISCENTE = "DISCENTE"
    DOCENTE = "DOCENTE"
    TECNICO_ADMINISTRATIVO = "TECNICO_ADMINISTRATIVO"
    COMUNIDADE = "COMUNIDADE"


class TipoInstrumento(str, Enum):
    DISCENTE_TURMA = "DISCENTE_TURMA"
    DOCENTE = "DOCENTE"
    TECNICO_ADMINISTRATIVO = "TECNICO_ADMINISTRATIVO"
    COMUNIDADE = "COMUNIDADE"


#: Relação fixa instrumento → segmento (doc 02). Não é tabela: é constante.
SEGMENTO_DO_INSTRUMENTO: dict[TipoInstrumento, Segmento] = {
    TipoInstrumento.DISCENTE_TURMA: Segmento.DISCENTE,
    TipoInstrumento.DOCENTE: Segmento.DOCENTE,
    TipoInstrumento.TECNICO_ADMINISTRATIVO: Segmento.TECNICO_ADMINISTRATIVO,
    TipoInstrumento.COMUNIDADE: Segmento.COMUNIDADE,
}


class BlocoPergunta(str, Enum):
    DISCIPLINA = "DISCIPLINA"
    PROFESSOR = "PROFESSOR"
    INSTITUCIONAL = "INSTITUCIONAL"


class AplicacaoPergunta(str, Enum):
    TODAS = "TODAS"
    ESPECIFICA = "ESPECIFICA"


class TipoPergunta(str, Enum):
    LIKERT_5 = "LIKERT_5"
    SIM_NAO = "SIM_NAO"
    TEXTO_LIVRE = "TEXTO_LIVRE"
    MULTIPLA_ESCOLHA_UNICA = "MULTIPLA_ESCOLHA_UNICA"


class Modalidade(str, Enum):
    PRELECAO = "PRELECAO"
    PRATICA = "PRATICA"
    PRATICA_HOSPITALAR = "PRATICA_HOSPITALAR"
    EAD = "EAD"
    EXTENSAO = "EXTENSAO"
    ESTAGIO = "ESTAGIO"
    NAO_INFORMADA = "NAO_INFORMADA"


class StatusFormulario(str, Enum):
    RASCUNHO = "RASCUNHO"
    PUBLICADO = "PUBLICADO"
    ENCERRADO = "ENCERRADO"


class EstadoSync(str, Enum):
    """Estado do espelho no Google Forms (doc 10 §6)."""

    NAO_CRIADO = "NAO_CRIADO"
    PENDENTE = "PENDENTE"
    SINCRONIZADO = "SINCRONIZADO"
    DIVERGENTE = "DIVERGENTE"
    CONGELADO = "CONGELADO"


class StatusImportacao(str, Enum):
    PROCESSANDO = "PROCESSANDO"
    AGUARDANDO_REVISAO = "AGUARDANDO_REVISAO"
    APLICADA = "APLICADA"
    CANCELADA = "CANCELADA"


class StatusLinha(str, Enum):
    OK = "OK"
    REVISAR = "REVISAR"
    ERRO = "ERRO"
    IGNORADA = "IGNORADA"


class TipoAlvo(str, Enum):
    DISCIPLINA = "DISCIPLINA"
    PROFESSOR = "PROFESSOR"
    CURSO = "CURSO"


class ResultadoSync(str, Enum):
    SEM_MUDANCA = "SEM_MUDANCA"
    CRIADO = "CRIADO"
    ATUALIZADO = "ATUALIZADO"
    BLOQUEADO = "BLOQUEADO"
    ERRO = "ERRO"
