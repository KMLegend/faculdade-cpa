"""Relatórios e limiar de exibição (doc 08 §3).

O foco aqui é a SUPRESSÃO: em turma pequena, uma média baixa somada a um
comentário identifica a pessoa. O relatório precisa recusar-se a mostrar.
"""

from __future__ import annotations

import datetime as dt

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import obter_settings
from app.db.base import Base
from app.models import (
    BlocoPergunta, Curso, Disciplina, Formulario, FormularioPergunta, Oferta,
    PeriodoLetivo, Professor, RespostaItem, Segmento, StatusFormulario,
    Submissao, TipoInstrumento, TipoPergunta,
)
from app.services.relatorios.consultas import (
    SEGMENTOS_RESTRITOS, limiar_de, por_dimensao, por_oferta,
)
from tests.apoio import URL_TESTE, precisa_banco

pytestmark = [precisa_banco, pytest.mark.asyncio]

URL_SANDBOX = URL_TESTE.rsplit("/", 1)[0] + "/cpa_relatorios_teste"


async def _criar_banco():
    admin = create_async_engine(
        URL_TESTE.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT"
    )
    async with admin.connect() as c:
        await c.execute(
            text("DROP DATABASE IF EXISTS cpa_relatorios_teste WITH (FORCE)")
        )
        await c.execute(text("CREATE DATABASE cpa_relatorios_teste"))
    await admin.dispose()


async def _destruir_banco():
    admin = create_async_engine(
        URL_TESTE.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT"
    )
    async with admin.connect() as c:
        await c.execute(
            text("DROP DATABASE IF EXISTS cpa_relatorios_teste WITH (FORCE)")
        )
    await admin.dispose()


@pytest_asyncio.fixture
async def cenario():
    """Uma oferta com respostas — a quantidade é definida por cada teste."""
    await _criar_banco()
    engine = create_async_engine(URL_SANDBOX, poolclass=NullPool)
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    async with fabrica() as s:
        from seeds.executar import semear_sinaes

        dims = await semear_sinaes(s)
        periodo = PeriodoLetivo(codigo="2026.2", ano=2026, semestre=2, ativo=True)
        curso = Curso(nome="Biomedicina", slug="BIOMEDICINA")
        disc = Disciplina(nome="Toxicologia", slug="toxicologia")
        prof = Professor(nome_exibicao="Washington", slug="washington")
        s.add_all([periodo, curso, disc, prof])
        await s.flush()

        oferta = Oferta(
            periodo_letivo_id=periodo.id,
            disciplina_id=disc.id,
            professor_id=prof.id,
        )
        s.add(oferta)
        await s.flush()
        await s.commit()
        ids = {
            "periodo": periodo.id,
            "oferta": oferta.id,
            "dimensao": dims[2],
        }

    async def semear(quantidade: int, segmento=Segmento.DISCENTE, encerrado=False):
        async with fabrica() as s:
            form = Formulario(
                periodo_letivo_id=ids["periodo"],
                tipo_instrumento=(
                    TipoInstrumento.DISCENTE_TURMA
                    if segmento is Segmento.DISCENTE
                    else TipoInstrumento(segmento.value)
                ),
                segmento=segmento,
                titulo="teste",
                status=(
                    StatusFormulario.ENCERRADO
                    if encerrado
                    else StatusFormulario.PUBLICADO
                ),
            )
            if segmento is Segmento.DISCENTE:
                from app.models import Turma, Turno

                turma = Turma(
                    periodo_letivo_id=ids["periodo"],
                    curso_id=(await s.scalar(select(Curso))).id,
                    turno=Turno.NOTURNO,
                    periodo_numero=4,
                )
                s.add(turma)
                await s.flush()
                form.turma_id = turma.id
            s.add(form)
            await s.flush()

            pergunta = FormularioPergunta(
                formulario_id=form.id, codigo=11, equivalencia_id=11,
                versao_texto=1, dimensao_id=ids["dimensao"],
                oferta_id=ids["oferta"], bloco=BlocoPergunta.PROFESSOR,
                rotulo_oferta="Toxicologia · Prof. Washington",
                texto_snapshot="O docente domina o conteúdo?",
                tipo_snapshot=TipoPergunta.LIKERT_5,
                obrigatoria_snapshot=True, ordem=1,
            )
            comentario = FormularioPergunta(
                formulario_id=form.id, codigo=19, equivalencia_id=19,
                versao_texto=1, dimensao_id=ids["dimensao"],
                oferta_id=ids["oferta"], bloco=BlocoPergunta.PROFESSOR,
                rotulo_oferta="Toxicologia · Prof. Washington",
                texto_snapshot="Comentário",
                tipo_snapshot=TipoPergunta.TEXTO_LIVRE,
                obrigatoria_snapshot=False, ordem=2,
            )
            s.add_all([pergunta, comentario])
            await s.flush()

            for i in range(quantidade):
                sub = Submissao(
                    formulario_id=form.id,
                    data_envio=dt.date(2026, 11, 24),
                    google_response_id=f"{segmento.value}-{i}",
                )
                s.add(sub)
                await s.flush()
                s.add(
                    RespostaItem(
                        submissao_id=sub.id,
                        formulario_pergunta_id=pergunta.id,
                        valor_numerico=5,
                    )
                )
                s.add(
                    RespostaItem(
                        submissao_id=sub.id,
                        formulario_pergunta_id=comentario.id,
                        valor_texto=f"comentário {i}",
                    )
                )
            await s.commit()

    yield fabrica, ids, semear
    await engine.dispose()
    await _destruir_banco()


class TestLimiar:
    async def test_abaixo_do_limiar_suprime(self, cenario):
        fabrica, ids, semear = cenario
        await semear(4)  # limiar padrão é 5
        async with fabrica() as s:
            r = await por_oferta(ids["oferta"], s)
        assert r["suprimido"] is True
        assert r["motivo"] == "AMOSTRA_INSUFICIENTE"
        assert r["perguntas"] == []
        assert r["comentarios"] == []

    async def test_no_limiar_exibe(self, cenario):
        fabrica, ids, semear = cenario
        await semear(5)
        async with fabrica() as s:
            r = await por_oferta(ids["oferta"], s)
        assert r["suprimido"] is False
        assert r["submissoes"] == 5
        assert r["perguntas"][0]["isg_pct"] == 100.0


class TestComentarios:
    async def test_comentario_oculto_enquanto_publicado(self, cenario):
        """RN-35 — comentário só aparece depois do encerramento."""
        fabrica, ids, semear = cenario
        await semear(6, encerrado=False)
        async with fabrica() as s:
            r = await por_oferta(ids["oferta"], s)
        assert r["comentarios_liberados"] is False
        assert r["comentarios"] == []

    async def test_comentario_liberado_apos_encerrar(self, cenario):
        fabrica, ids, semear = cenario
        await semear(6, encerrado=True)
        async with fabrica() as s:
            r = await por_oferta(ids["oferta"], s)
        assert r["comentarios_liberados"] is True
        assert len(r["comentarios"]) == 6

    async def test_comentario_moderado_nao_aparece(self, cenario):
        fabrica, ids, semear = cenario
        await semear(6, encerrado=True)
        async with fabrica() as s:
            item = await s.scalar(
                select(RespostaItem).where(RespostaItem.valor_texto.isnot(None))
            )
            item.oculto = True
            await s.commit()
        async with fabrica() as s:
            r = await por_oferta(ids["oferta"], s)
        assert len(r["comentarios"]) == 5, "o moderado sai, os outros ficam"


class TestPorDimensao:
    async def test_distingue_nao_aplicada_de_amostra_insuficiente(self, cenario):
        """São coisas diferentes: uma é de projeto, outra protege anonimato."""
        fabrica, ids, semear = cenario
        await semear(6, segmento=Segmento.DISCENTE)

        async with fabrica() as s:
            r = await por_dimensao(ids["periodo"], s)

        celulas = [
            (d["numero"], seg, cel)
            for eixo in r["eixos"]
            for d in eixo["dimensoes"]
            for seg, cel in d["por_segmento"].items()
        ]
        motivos = {c["motivo"] for _, _, c in celulas if c.get("suprimido")}
        assert "DIMENSAO_NAO_APLICADA" in motivos
        # a dimensão 2 do discente tem 6 respostas: aparece
        visiveis = [
            (n, seg) for n, seg, c in celulas if not c.get("suprimido")
        ]
        assert ("DISCENTE" in {seg for _, seg in visiveis})

    async def test_tecnico_com_9_respostas_fica_suprimido(self, cenario):
        """Limiar restrito é 10 — 9 respostas não bastam."""
        fabrica, ids, semear = cenario
        await semear(9, segmento=Segmento.TECNICO_ADMINISTRATIVO)
        async with fabrica() as s:
            r = await por_dimensao(
                ids["periodo"], s, segmento=Segmento.TECNICO_ADMINISTRATIVO
            )
        celulas = [
            c
            for eixo in r["eixos"]
            for d in eixo["dimensoes"]
            for c in d["por_segmento"].values()
            if c["respostas"] == 9
        ]
        assert celulas, "a dimensão com 9 respostas precisa aparecer na estrutura"
        assert all(c["suprimido"] for c in celulas)
        assert all(c["motivo"] == "AMOSTRA_INSUFICIENTE" for c in celulas)
