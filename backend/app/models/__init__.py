"""Models do domínio. Importados aqui para o Alembic enxergar o metadata."""

from app.models.academico import (
    Alocacao, Curso, Disciplina, DisciplinaAlias, Oferta, OfertaTurma,
    PeriodoLetivo, Professor, ProfessorAlias, Turma,
)
from app.models.enums import (
    SEGMENTO_DO_INSTRUMENTO, AplicacaoPergunta, BlocoPergunta, EstadoSync,
    Modalidade, ResultadoSync, Segmento, StatusFormulario, StatusImportacao,
    StatusLinha, TipoAlvo, TipoInstrumento, TipoPergunta, Turno,
)
from app.models.formularios import Formulario, FormularioPergunta
from app.models.importacao import ImportacaoGrade, ImportacaoLinha
from app.models.integracao import SincronizacaoLog
from app.models.perguntas import (
    DimensaoSinaes, EixoSinaes, EquivalenciaPergunta, Pergunta, PerguntaVinculo,
)
from app.models.respostas import RespostaItem, Submissao

__all__ = [
    "SEGMENTO_DO_INSTRUMENTO", "Alocacao", "AplicacaoPergunta", "BlocoPergunta",
    "Curso", "DimensaoSinaes", "Disciplina", "DisciplinaAlias", "EixoSinaes",
    "EquivalenciaPergunta", "EstadoSync", "Formulario", "FormularioPergunta",
    "ImportacaoGrade", "ImportacaoLinha", "Modalidade", "Oferta", "OfertaTurma",
    "PeriodoLetivo", "Pergunta", "PerguntaVinculo", "Professor", "ProfessorAlias",
    "ResultadoSync", "RespostaItem", "Segmento", "SincronizacaoLog",
    "StatusFormulario", "StatusImportacao", "StatusLinha", "Submissao", "TipoAlvo",
    "TipoInstrumento", "TipoPergunta", "Turma", "Turno",
]
