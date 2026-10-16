"""Aceite da Fase 5 (doc 10 §12), sem precisar de credenciais.

Usa o cliente falso: a suíte roda offline, no CI, sem tocar a conta da CPA.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.errors import AnonimatoViolado, ConflitoEstado, EstruturaCongelada
from app.db.base import Base
from app.models import (
    BlocoPergunta, EstadoSync, Formulario, FormularioPergunta, PeriodoLetivo,
    Segmento, SincronizacaoLog, Submissao, TipoInstrumento, TipoPergunta,
)
from app.services.google.estrutura import agrupar, para_requests
from app.services.google.ingestao import ingerir
from app.services.google.sincronizador import publicar_no_google, sincronizar
from tests.apoio import URL_TESTE, precisa_banco
from tests.falso_google import FalsoGoogleForms

pytestmark = [precisa_banco, pytest.mark.asyncio]

URL_SANDBOX = URL_TESTE.rsplit("/", 1)[0] + "/cpa_google_teste"


@pytest_asyncio.fixture
async def sandbox():
    admin = create_async_engine(
        URL_TESTE.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT"
    )
    async with admin.connect() as c:
        await c.execute(text("DROP DATABASE IF EXISTS cpa_google_teste WITH (FORCE)"))
        await c.execute(text("CREATE DATABASE cpa_google_teste"))
    await admin.dispose()

    engine = create_async_engine(URL_SANDBOX, poolclass=NullPool)
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    async with fabrica() as s:
        from seeds.executar import semear_sinaes

        dims = await semear_sinaes(s)
        periodo = PeriodoLetivo(codigo="2026.2", ano=2026, semestre=2, ativo=True)
        s.add(periodo)
        await s.flush()

        form = Formulario(
            periodo_letivo_id=periodo.id,
            tipo_instrumento=TipoInstrumento.DOCENTE,
            segmento=Segmento.DOCENTE,
            titulo="CPA 2026.2 — Avaliação Docente",
        )
        s.add(form)
        await s.flush()

        # 3 Likert numa dimensão + 1 texto livre
        for i, (texto_p, tipo) in enumerate(
            [
                ("O docente domina o conteúdo?", TipoPergunta.LIKERT_5),
                ("O docente é pontual?", TipoPergunta.LIKERT_5),
                ("A didática contribui?", TipoPergunta.LIKERT_5),
                ("Comentários livres", TipoPergunta.TEXTO_LIVRE),
            ],
            start=1,
        ):
            s.add(
                FormularioPergunta(
                    formulario_id=form.id,
                    codigo=i,
                    equivalencia_id=i,
                    versao_texto=1,
                    dimensao_id=dims[2],
                    bloco=BlocoPergunta.INSTITUCIONAL,
                    texto_snapshot=texto_p,
                    tipo_snapshot=tipo,
                    obrigatoria_snapshot=tipo is not TipoPergunta.TEXTO_LIVRE,
                    ordem=i,
                )
            )
        await s.commit()
        form_id = form.id

    yield fabrica, form_id

    await engine.dispose()
    admin = create_async_engine(
        URL_TESTE.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT"
    )
    async with admin.connect() as c:
        await c.execute(text("DROP DATABASE IF EXISTS cpa_google_teste WITH (FORCE)"))
    await admin.dispose()


class TestSincronizacao:
    async def test_cria_e_grava_question_ids(self, sandbox):
        fabrica, form_id = sandbox
        cliente = FalsoGoogleForms()
        async with fabrica() as s:
            r = await sincronizar(form_id, s, cliente=cliente)
        assert r["resultado"] == "CRIADO"

        async with fabrica() as s:
            form = await s.get(Formulario, form_id)
            itens = (
                await s.scalars(
                    select(FormularioPergunta).where(
                        FormularioPergunta.formulario_id == form_id
                    )
                )
            ).all()
        assert form.google_form_id
        assert form.google_responder_uri
        assert form.estado_sync is EstadoSync.SINCRONIZADO
        # ⭐ é o question_id que substitui o cruzamento por texto de 2025.2
        assert all(i.google_question_id for i in itens), [
            (i.codigo, i.google_question_id) for i in itens
        ]
        assert len({i.google_question_id for i in itens}) == 4

    async def test_formulario_criado_nasce_fechado(self, sandbox):
        """Rascunho recém-criado não pode estar aceitando resposta.

        `forms.create` devolve o formulário já aberto. Se ele ficar assim, uma
        resposta precoce congela a estrutura (RN-42) de um formulário que a CPA
        ainda não revisou — e a janela de aplicação deixa de significar algo.
        """
        fabrica, form_id = sandbox
        cliente = FalsoGoogleForms()
        async with fabrica() as s:
            await sincronizar(form_id, s, cliente=cliente)

        async with fabrica() as s:
            form = await s.get(Formulario, form_id)
        estado = cliente.formularios[form.google_form_id]["publishSettings"][
            "publishState"
        ]
        assert estado["isAcceptingResponses"] is False, estado
        assert ("publicar", (form.google_form_id, False)) in cliente.chamadas

    async def test_abrir_no_google_exige_janela(self, sandbox):
        """doc 05 §2 — o caminho do Google é o que abre ao aluno; trancá-lo também.

        Sem esta guarda, bastava chamar `publicar-no-google` para pular a
        exigência de janela que o `publicar` local já fazia.
        """
        fabrica, form_id = sandbox
        cliente = FalsoGoogleForms()
        async with fabrica() as s:
            await sincronizar(form_id, s, cliente=cliente)

        async with fabrica() as s:
            form = await s.get(Formulario, form_id)
            form.abre_em = None
            form.fecha_em = None
            await s.commit()

        async with fabrica() as s:
            with pytest.raises(ConflitoEstado):
                await publicar_no_google(form_id, True, s, cliente=cliente)

        # fechar nunca depende de janela — é a saída de emergência
        async with fabrica() as s:
            r = await publicar_no_google(form_id, False, s, cliente=cliente)
        assert r["aceitando_respostas"] is False

    async def test_segunda_sincronizacao_nao_emite_request(self, sandbox):
        """RN-40 — `hash_estrutura` igual ⇒ nenhuma chamada de estrutura."""
        fabrica, form_id = sandbox
        cliente = FalsoGoogleForms()
        async with fabrica() as s:
            await sincronizar(form_id, s, cliente=cliente)
        chamadas_antes = len(cliente.chamadas)

        async with fabrica() as s:
            r = await sincronizar(form_id, s, cliente=cliente)
        assert r["resultado"] == "SEM_MUDANCA"
        assert r["requests"] == 0
        assert len(cliente.chamadas) == chamadas_antes, "não tocou o Google"

    async def test_anonimato_divergente_bloqueia(self, sandbox):
        """RN-41 — coleta de e-mail ligada impede a publicação."""
        fabrica, form_id = sandbox
        # A coleta está ligada no Google e o nosso write não gruda — é
        # exatamente o caso em que só a RELEITURA salva (doc 10 §5).
        cliente = FalsoGoogleForms(
            email_collection="VERIFIED", email_collection_fixo=True
        )
        with pytest.raises(AnonimatoViolado) as erro:
            async with fabrica() as s:
                await sincronizar(form_id, s, cliente=cliente)
        assert erro.value.detalhes["emailCollectionType"] == "VERIFIED"

    async def test_estrutura_congela_com_resposta(self, sandbox):
        """RN-42 — editar form com resposta desloca colunas e corrompe a série."""
        fabrica, form_id = sandbox
        cliente = FalsoGoogleForms()
        async with fabrica() as s:
            await sincronizar(form_id, s, cliente=cliente)

        async with fabrica() as s:
            s.add(
                Submissao(
                    formulario_id=form_id,
                    data_envio=__import__("datetime").date(2026, 11, 24),
                    google_response_id="resp-1",
                )
            )
            form = await s.get(Formulario, form_id)
            form.hash_estrutura = "forca-diferenca"
            await s.commit()

        with pytest.raises(EstruturaCongelada) as erro:
            async with fabrica() as s:
                await sincronizar(form_id, s, cliente=cliente)
        assert erro.value.detalhes["submissoes"] == 1

    async def test_registra_log_de_sincronizacao(self, sandbox):
        """O log é a rota de recuperação do vínculo (doc 10 §6.1.2)."""
        fabrica, form_id = sandbox
        async with fabrica() as s:
            await sincronizar(form_id, s, cliente=FalsoGoogleForms())
            log = await s.scalar(
                select(SincronizacaoLog).where(
                    SincronizacaoLog.formulario_id == form_id
                )
            )
        assert log is not None
        assert log.requests_enviadas > 0
        assert log.detalhe, "o JSON do formulário precisa ficar guardado"


class TestPublicacao:
    async def test_abre_e_fecha_janela(self, sandbox):
        fabrica, form_id = sandbox
        cliente = FalsoGoogleForms()
        async with fabrica() as s:
            await sincronizar(form_id, s, cliente=cliente)
            form = await s.get(Formulario, form_id)
            form.abre_em = datetime(2026, 11, 24, tzinfo=timezone.utc)
            form.fecha_em = datetime(2026, 12, 1, tzinfo=timezone.utc)
            await s.commit()

            r = await publicar_no_google(form_id, True, s, cliente=cliente)
            assert r["aceitando_respostas"] is True
            r = await publicar_no_google(form_id, False, s, cliente=cliente)
            assert r["status"] == "ENCERRADO"


class TestIngestao:
    async def test_ingere_por_question_id(self, sandbox):
        fabrica, form_id = sandbox
        cliente = FalsoGoogleForms()
        async with fabrica() as s:
            await sincronizar(form_id, s, cliente=cliente)
            form = await s.get(Formulario, form_id)
            gid = form.google_form_id

        qids = cliente.question_ids(gid)
        cliente.semear_resposta(
            gid, {qids[0]: "5", qids[1]: "4", qids[3]: "Ótimo curso"}, "resp-A"
        )

        async with fabrica() as s:
            r = await ingerir(form_id, s, cliente=cliente)
        assert r["novas"] == 1
        assert r["orfas"] == 0

        async with fabrica() as s:
            from app.models import RespostaItem

            itens = (await s.scalars(select(RespostaItem))).all()
            sub = await s.scalar(select(Submissao))
        assert len(itens) == 3
        assert {i.valor_numerico for i in itens if i.valor_numerico} == {5, 4}
        assert any(i.valor_texto == "Ótimo curso" for i in itens)
        # RN-31 — só a data, nunca a hora
        assert sub.data_envio.isoformat() == "2026-11-24"

    async def test_ingerir_duas_vezes_nao_duplica(self, sandbox):
        fabrica, form_id = sandbox
        cliente = FalsoGoogleForms()
        async with fabrica() as s:
            await sincronizar(form_id, s, cliente=cliente)
            gid = (await s.get(Formulario, form_id)).google_form_id
        cliente.semear_resposta(gid, {cliente.question_ids(gid)[0]: "5"}, "resp-A")

        async with fabrica() as s:
            await ingerir(form_id, s, cliente=cliente)
        async with fabrica() as s:
            r = await ingerir(form_id, s, cliente=cliente)
            total = await s.scalar(select(func.count()).select_from(Submissao))
        assert r["novas"] == 0
        assert r["ja_importadas"] == 1
        assert total == 1

    async def test_question_id_desconhecido_vira_orfa(self, sandbox):
        """Nunca reatribuir por texto — foi o defeito de 2025.2."""
        fabrica, form_id = sandbox
        cliente = FalsoGoogleForms()
        async with fabrica() as s:
            await sincronizar(form_id, s, cliente=cliente)
            gid = (await s.get(Formulario, form_id)).google_form_id
        cliente.semear_resposta(gid, {"q-inexistente": "5"}, "resp-X")

        async with fabrica() as s:
            r = await ingerir(form_id, s, cliente=cliente)
        assert r["orfas"] == 1
        assert r["detalhe_orfas"][0]["question_id"] == "q-inexistente"
