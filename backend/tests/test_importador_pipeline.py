"""Aceite do importador completo (doc 03 §6).

Roda o pipeline inteiro contra um banco próprio, criado e destruído pelo teste:
matching → staging → conciliação → diff → commit → reimportação.

É o teste que vale pela Fase 3: se ele passa, a grade do próximo semestre entra
sem ninguém digitar nada.
"""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.errors import ConflitoEstado
from app.db.base import Base
from app.models import (
    Alocacao, Curso, Disciplina, ImportacaoLinha, Oferta, OfertaTurma,
    PeriodoLetivo, Professor, StatusImportacao, StatusLinha, Turma,
)
from app.services.importador.commit import aplicar, calcular_diff
from app.services.importador.staging import (
    criar_entidades_novas_em_lote, criar_importacao,
)
from seeds.executar import semear_aliases, semear_cursos, semear_sinaes
from tests.apoio import URL_TESTE, precisa_banco

pytestmark = [precisa_banco, pytest.mark.asyncio]

PLANILHA = os.getenv("PLANILHA_TESTE", "/anexos/horario_20262.xlsx")
if not os.path.exists(PLANILHA):
    from pathlib import Path

    PLANILHA = str(
        Path(__file__).resolve().parents[2]
        / ".agent/02-especificacao/anexos/horario_20262.xlsx"
    )

URL_SANDBOX = URL_TESTE.rsplit("/", 1)[0] + "/cpa_pipeline_teste"


@pytest_asyncio.fixture(scope="module")
async def sandbox():
    """Banco descartável só para este módulo."""
    admin = create_async_engine(
        URL_TESTE.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT"
    )
    async with admin.connect() as c:
        await c.execute(text("DROP DATABASE IF EXISTS cpa_pipeline_teste WITH (FORCE)"))
        await c.execute(text("CREATE DATABASE cpa_pipeline_teste"))
    await admin.dispose()

    engine = create_async_engine(URL_SANDBOX, poolclass=NullPool)
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    async with fabrica() as s:
        dims = await semear_sinaes(s)
        await semear_cursos(s)
        await semear_aliases(s)
        s.add(PeriodoLetivo(codigo="2026.2", ano=2026, semestre=2, ativo=True))
        await s.commit()

    yield fabrica

    await engine.dispose()
    admin = create_async_engine(
        URL_TESTE.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT"
    )
    async with admin.connect() as c:
        await c.execute(text("DROP DATABASE IF EXISTS cpa_pipeline_teste WITH (FORCE)"))
    await admin.dispose()


async def _periodo_id(fabrica) -> int:
    async with fabrica() as s:
        return (await s.scalar(select(PeriodoLetivo))).id


async def _rodar_importacao(fabrica, periodo_id: int) -> tuple[int, dict]:
    """Executa upload → criação em lote → resolve pendências → diff."""
    async with fabrica() as s:
        imp = await criar_importacao(PLANILHA, "horario 20262.xlsx", periodo_id, s)
        await s.commit()
        imp_id, resumo = imp.id, dict(imp.resumo)

    async with fabrica() as s:
        await criar_entidades_novas_em_lote(imp_id, s)
        await s.commit()

    async with fabrica() as s:
        pendentes = (
            await s.scalars(
                select(ImportacaoLinha).where(
                    ImportacaoLinha.importacao_id == imp_id,
                    ImportacaoLinha.status.in_(
                        [StatusLinha.REVISAR, StatusLinha.ERRO]
                    ),
                )
            )
        ).all()
        for linha in pendentes:
            # O admin confirma a proposta; o bilhete administrativo fica de fora.
            linha.status = (
                StatusLinha.IGNORADA
                if linha.status is StatusLinha.ERRO
                else StatusLinha.OK
            )
        await s.commit()
    return imp_id, resumo


async def _contagens(fabrica) -> dict[str, int]:
    async with fabrica() as s:
        return {
            m.__name__: await s.scalar(select(func.count()).select_from(m))
            for m in (Turma, Oferta, Alocacao, OfertaTurma, Professor, Disciplina)
        }


class TestPipelineCompleto:
    async def test_primeira_importacao_produz_a_grade_correta(self, sandbox):
        periodo_id = await _periodo_id(sandbox)
        imp_id, resumo = await _rodar_importacao(sandbox, periodo_id)

        assert resumo["alocacoes"] == 164, "164 células de aula na planilha real"
        assert resumo["turmas_propostas"] == 17

        async with sandbox() as s:
            await aplicar(imp_id, s)

        c = await _contagens(sandbox)
        assert c["Turma"] == 17, "RN-04 — curso + turno + período"
        assert c["Oferta"] == 105, "RN-09 — disciplina + professor, sem a turma"
        assert c["OfertaTurma"] == 136, "RN-07 — vínculos N:N"
        assert c["Professor"] == 29
        assert c["Alocacao"] == 163, "164 menos a célula ignorada do Preceptor"

    async def test_nenhum_curso_ciclo_basico(self, sandbox):
        """RN-03 — ciclo básico é grade compartilhada, não curso."""
        async with sandbox() as s:
            slugs = set((await s.scalars(select(Curso.slug))).all())
        assert "CICLO_BASICO" not in slugs
        assert slugs == {"BIOMEDICINA", "ENFERMAGEM", "EDUCACAO_FISICA", "GTI"}

    async def test_ciclo_basico_expande_nos_cursos_reais(self, sandbox):
        """A aba compartilhada gera turma de Biomedicina E de Enfermagem."""
        async with sandbox() as s:
            turmas = (
                await s.execute(
                    select(Curso.slug, Turma.turno, Turma.periodo_numero)
                    .join(Turma, Turma.curso_id == Curso.id)
                    .where(Turma.compartilhada_ciclo_basico.is_(True))
                )
            ).all()
        cursos = {t[0] for t in turmas}
        assert {"BIOMEDICINA", "ENFERMAGEM"} <= cursos

    async def test_subturmas_viram_uma_turma(self, sandbox):
        """Sub-Turma A e B de Biomedicina Matutino são a mesma turma do 4º."""
        async with sandbox() as s:
            turma = await s.scalar(
                select(Turma)
                .join(Curso)
                .where(
                    Curso.slug == "BIOMEDICINA",
                    Turma.turno == "MATUTINO",
                    Turma.periodo_numero == 4,
                )
            )
        assert turma is not None
        assert len(turma.colunas_origem or []) >= 2, "alimentada por 2+ colunas"

    async def test_ofertas_sem_turma_nascem_nao_avaliaveis(self, sandbox):
        """RN-15 — estágio e TCC não entram na avaliação."""
        async with sandbox() as s:
            sem_turma = (
                await s.scalars(
                    select(Oferta).where(
                        ~Oferta.ofertas_turma.any(), Oferta.ativo.is_(True)
                    )
                )
            ).all()
            nao_avaliaveis = await s.scalar(
                select(func.count())
                .select_from(Oferta)
                .where(Oferta.avaliavel.is_(False))
            )
        assert len(sem_turma) == 4
        assert nao_avaliaveis == 4
        assert all(not o.avaliavel for o in sem_turma)

    async def test_texto_origem_em_toda_alocacao(self, sandbox):
        """RN-11 — rastreabilidade de 100%."""
        async with sandbox() as s:
            vazios = await s.scalar(
                select(func.count())
                .select_from(Alocacao)
                .where(Alocacao.texto_origem.is_(None) | (Alocacao.texto_origem == ""))
            )
        assert vazios == 0

    async def test_reimportacao_tem_diff_vazio(self, sandbox):
        """RN-12 — o critério central do importador."""
        periodo_id = await _periodo_id(sandbox)
        antes = await _contagens(sandbox)

        imp_id, resumo = await _rodar_importacao(sandbox, periodo_id)
        # Com os aliases já criados, o matching casa quase tudo na etapa 1.
        assert resumo["OK"] == 158, resumo

        async with sandbox() as s:
            diff = await calcular_diff(imp_id, s)
            assert diff.vazio, diff.como_dict()
            await aplicar(imp_id, s)

        assert await _contagens(sandbox) == antes, "reimportar não pode duplicar nada"

    async def test_aliases_criados_pelo_commit(self, sandbox):
        """A decisão vira alias: 'Washignton' casa sozinho no próximo ciclo."""
        from app.models import ProfessorAlias

        async with sandbox() as s:
            aliases = {
                a.slug_origem
                for a in (await s.scalars(select(ProfessorAlias))).all()
            }
        assert "washignton" in aliases
        assert "vitoria" in aliases


class TestBloqueioDeCommit:
    async def test_aplicar_com_pendencia_recusa(self, sandbox):
        """RN-13 — nada entra no domínio com linha em revisão."""
        periodo_id = await _periodo_id(sandbox)
        async with sandbox() as s:
            imp = await criar_importacao(PLANILHA, "grade.xlsx", periodo_id, s)
            await s.commit()
            imp_id = imp.id

        async with sandbox() as s:
            with pytest.raises(ConflitoEstado) as erro:
                await aplicar(imp_id, s)
            assert "revisão" in str(erro.value)
            assert erro.value.detalhes["total"] > 0

        async with sandbox() as s:
            imp = await s.get(type(imp), imp_id)
            assert imp.status is StatusImportacao.AGUARDANDO_REVISAO
