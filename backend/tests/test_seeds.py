"""Aceite da Fase 2 — o banco semeado reflete o instrumento oficial da CPA."""

import pytest
from sqlalchemy import func, select

from app.models import (
    BlocoPergunta, Curso, DimensaoSinaes, EixoSinaes, EquivalenciaPergunta,
    Pergunta, TipoInstrumento,
)
from tests.apoio import precisa_banco

pytestmark = [precisa_banco, pytest.mark.asyncio]


async def test_referencia_sinaes(sessao):
    assert await sessao.scalar(select(func.count()).select_from(EixoSinaes)) == 5
    assert await sessao.scalar(select(func.count()).select_from(DimensaoSinaes)) == 10


async def test_cursos_sem_ciclo_basico(sessao):
    """RN-03 — ciclo básico não é curso."""
    slugs = set((await sessao.scalars(select(Curso.slug))).all())
    assert slugs == {"BIOMEDICINA", "ENFERMAGEM", "EDUCACAO_FISICA", "GTI"}
    assert "CICLO_BASICO" not in slugs


async def test_163_perguntas_com_codigo_continuo(sessao):
    total = await sessao.scalar(select(func.count()).select_from(Pergunta))
    menor = await sessao.scalar(select(func.min(Pergunta.codigo)))
    maior = await sessao.scalar(select(func.max(Pergunta.codigo)))
    assert (total, menor, maior) == (163, 1, 163)


async def test_distribuicao_do_instrumento_discente(sessao):
    """48 institucionais + 10 repetidas por matéria (doc 04 §2.1)."""
    async def contar(bloco=None, blocos=None):
        q = select(func.count()).select_from(Pergunta).where(
            Pergunta.tipo_instrumento == TipoInstrumento.DISCENTE_TURMA
        )
        if bloco:
            q = q.where(Pergunta.bloco == bloco)
        if blocos:
            q = q.where(Pergunta.bloco.in_(blocos))
        return await sessao.scalar(q)

    assert await contar(bloco=BlocoPergunta.INSTITUCIONAL) == 48
    assert await contar(blocos=[BlocoPergunta.DISCIPLINA, BlocoPergunta.PROFESSOR]) == 10


async def test_distribuicao_dos_demais_instrumentos(sessao):
    esperado = {
        TipoInstrumento.DOCENTE: 60,
        TipoInstrumento.TECNICO_ADMINISTRATIVO: 42,
        TipoInstrumento.COMUNIDADE: 3,
    }
    for instrumento, qtd in esperado.items():
        n = await sessao.scalar(
            select(func.count())
            .select_from(Pergunta)
            .where(Pergunta.tipo_instrumento == instrumento)
        )
        assert n == qtd, instrumento


async def test_67_equivalencias(sessao):
    n = await sessao.scalar(select(func.count()).select_from(EquivalenciaPergunta))
    assert n == 67


async def test_equivalencia_liga_os_tres_segmentos(sessao):
    """codigo 1 (discente) ↔ 59 (docente) ↔ 119 (técnico) — a mesma pergunta."""
    perguntas = (
        await sessao.scalars(select(Pergunta).where(Pergunta.codigo.in_([1, 59, 119])))
    ).all()
    assert len(perguntas) == 3
    assert len({p.equivalencia_id for p in perguntas}) == 1, "mesmo grupo"
    assert {p.tipo_instrumento for p in perguntas} == {
        TipoInstrumento.DISCENTE_TURMA,
        TipoInstrumento.DOCENTE,
        TipoInstrumento.TECNICO_ADMINISTRATIVO,
    }


async def test_toda_pergunta_tem_dimensao(sessao):
    """RN-16 — sem dimensão não existe relatório por dimensão."""
    n = await sessao.scalar(
        select(func.count()).select_from(Pergunta).where(Pergunta.dimensao_id.is_(None))
    )
    assert n == 0


async def test_grupo_de_equivalencia_tem_dimensao_unica(sessao):
    """Membros do mesmo grupo precisam compartilhar a dimensão."""
    sub = (
        select(Pergunta.equivalencia_id)
        .group_by(Pergunta.equivalencia_id)
        .having(func.count(func.distinct(Pergunta.dimensao_id)) > 1)
    ).subquery()
    assert await sessao.scalar(select(func.count()).select_from(sub)) == 0


async def test_duplicatas_nascem_desativadas(sessao):
    """Anexo B §B.6 — Q29 e Q86 repetem Q24 e Q81."""
    por_codigo = {
        p.codigo: p
        for p in (
            await sessao.scalars(select(Pergunta).where(Pergunta.codigo.in_([24, 29, 81, 86])))
        ).all()
    }
    assert por_codigo[24].ativo and por_codigo[81].ativo
    assert not por_codigo[29].ativo and not por_codigo[86].ativo


async def test_proximo_codigo_livre_e_164(sessao):
    """Pergunta nova NÃO reaproveita código; entra em 164 (doc 04 §5.1)."""
    maior = await sessao.scalar(select(func.max(Pergunta.codigo)))
    assert maior + 1 == 164
