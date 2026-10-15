"""As regras de negócio que vivem no BANCO (doc 02).

Constraint não é detalhe de implementação: é a última barreira contra o erro que
nenhuma revisão de código pega. Estes testes verificam que o banco REJEITA o que
deve rejeitar.
"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import (
    AplicacaoPergunta, BlocoPergunta, Curso, DimensaoSinaes, Oferta, OfertaTurma,
    PeriodoLetivo, Pergunta, Professor, Disciplina, TipoInstrumento, TipoPergunta,
    Turma, Turno,
)
from tests.apoio import precisa_banco

pytestmark = [precisa_banco, pytest.mark.asyncio]


async def _cenario(sessao):
    """Período, curso, disciplina e professor para pendurar os testes."""
    periodo = await sessao.scalar(
        select(PeriodoLetivo).where(PeriodoLetivo.codigo == "2026.2")
    )
    if periodo is None:
        periodo = PeriodoLetivo(codigo="2026.2", ano=2026, semestre=2, ativo=False)
        sessao.add(periodo)
        await sessao.flush()
    curso = await sessao.scalar(select(Curso).where(Curso.slug == "BIOMEDICINA"))
    disc = await sessao.scalar(select(Disciplina).limit(1))
    prof = await sessao.scalar(select(Professor).limit(1))
    return periodo, curso, disc, prof


class TestTurma:
    async def test_chave_rn04_recusa_duplicata(self, sessao):
        """Mesmo curso+turno+período é UMA turma, ainda que o módulo difira."""
        periodo, curso, _, _ = await _cenario(sessao)
        sessao.add(
            Turma(
                periodo_letivo_id=periodo.id, curso_id=curso.id,
                turno=Turno.NOTURNO, periodo_numero=4, modulo="AB",
            )
        )
        await sessao.flush()
        sessao.add(
            Turma(
                periodo_letivo_id=periodo.id, curso_id=curso.id,
                turno=Turno.NOTURNO, periodo_numero=4, modulo="OUTRO MÓDULO",
            )
        )
        with pytest.raises(IntegrityError):
            await sessao.flush()
        await sessao.rollback()

    async def test_periodo_numero_precisa_ser_positivo(self, sessao):
        periodo, curso, _, _ = await _cenario(sessao)
        sessao.add(
            Turma(
                periodo_letivo_id=periodo.id, curso_id=curso.id,
                turno=Turno.MATUTINO, periodo_numero=0,
            )
        )
        with pytest.raises(IntegrityError):
            await sessao.flush()
        await sessao.rollback()


class TestOferta:
    async def test_chave_rn09_recusa_duplicata(self, sessao):
        """(período, disciplina, professor) é único — a turma não entra."""
        periodo, _, disc, prof = await _cenario(sessao)
        for _ in range(2):
            sessao.add(
                Oferta(
                    periodo_letivo_id=periodo.id,
                    disciplina_id=disc.id,
                    professor_id=prof.id,
                )
            )
        with pytest.raises(IntegrityError):
            await sessao.flush()
        await sessao.rollback()

    async def test_nao_existe_turma_id_na_oferta(self):
        """Blindagem contra o erro mais fácil de cometer aqui (doc 02)."""
        assert "turma_id" not in Oferta.__table__.c, (
            "turma_id na oferta transformaria 105 ofertas em 136"
        )
        assert "oferta_id" in OfertaTurma.__table__.c


class TestPergunta:
    async def test_codigo_nunca_reutilizado(self, sessao):
        """Reutilizar código somaria perguntas diferentes (doc 04 §5.1)."""
        dim = await sessao.scalar(select(DimensaoSinaes).limit(1))
        sessao.add(
            Pergunta(
                codigo=11,  # já existe
                texto="tentando reutilizar",
                equivalencia_id=1,
                dimensao_id=dim.id,
                tipo_instrumento=TipoInstrumento.DOCENTE,
                bloco=BlocoPergunta.INSTITUCIONAL,
            )
        )
        with pytest.raises(IntegrityError):
            await sessao.flush()
        await sessao.rollback()

    async def test_bloco_de_materia_so_no_instrumento_de_turma(self, sessao):
        """RN-17 — não há disciplina a avaliar no instrumento docente."""
        dim = await sessao.scalar(select(DimensaoSinaes).limit(1))
        sessao.add(
            Pergunta(
                codigo=9001, texto="teste", equivalencia_id=1, dimensao_id=dim.id,
                tipo_instrumento=TipoInstrumento.DOCENTE,
                bloco=BlocoPergunta.PROFESSOR,
            )
        )
        with pytest.raises(IntegrityError):
            await sessao.flush()
        await sessao.rollback()

    async def test_vinculo_especifico_so_em_bloco_de_materia(self, sessao):
        """RN-20 — pergunta institucional não tem alvo a que vincular."""
        dim = await sessao.scalar(select(DimensaoSinaes).limit(1))
        sessao.add(
            Pergunta(
                codigo=9002, texto="teste", equivalencia_id=1, dimensao_id=dim.id,
                tipo_instrumento=TipoInstrumento.DOCENTE,
                bloco=BlocoPergunta.INSTITUCIONAL,
                aplicacao=AplicacaoPergunta.ESPECIFICA,
            )
        )
        with pytest.raises(IntegrityError):
            await sessao.flush()
        await sessao.rollback()

    async def test_opcoes_so_em_multipla_escolha(self, sessao):
        dim = await sessao.scalar(select(DimensaoSinaes).limit(1))
        sessao.add(
            Pergunta(
                codigo=9003, texto="teste", equivalencia_id=1, dimensao_id=dim.id,
                tipo_instrumento=TipoInstrumento.DOCENTE,
                bloco=BlocoPergunta.INSTITUCIONAL,
                tipo=TipoPergunta.LIKERT_5,
                opcoes=["a", "b"],
            )
        )
        with pytest.raises(IntegrityError):
            await sessao.flush()
        await sessao.rollback()
