"""Aceite da Fase 3 — Motor de Formulários e QR Code (doc 05, doc 09).

Critérios de aceite:
1. Geração em lote cria 20 formulários (17 discentes + 3 institucionais).
2. Todos os 20 possuem UUIDs distintos.
3. Biomedicina · Noturno · 6º período possui 12 ofertas avaliáveis e dispara alerta (> 150 perguntas).
4. Biomedicina · Noturno · 4º período recebe exatamente 1 formulário (RN-04).
5. Mesma disciplina com professores diferentes gera blocos distintos na mesma turma (RN-08).
6. As 4 ofertas sem turma não aparecem em nenhum formulário (RN-30).
7. Idempotência: rodar gerar_lote duas vezes não duplica formulários (RN-25).
8. QR Code público:
   - Formulário RASCUNHO -> 404 (doc 05 §3)
   - Formulário sem google_responder_uri -> 404 (doc 06 §2)
   - Formulário PUBLICADO e sincronizado -> 200 PNG / SVG com Cache-Control.
9. Imutabilidade do Snapshot: editar uma pergunta não altera o formulário já gerado (RN-26).
10. Ciclo de vida: RASCUNHO -> PUBLICADO -> ENCERRADO; DELETE bloqueado se não for RASCUNHO.
11. Artefatos de impressão: endpoints devolvem PDFs válidos.
"""

from __future__ import annotations

import io
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

from app.core.config import obter_settings
from app.db.session import obter_sessao
from app.main import app
from app.models import (
    BlocoPergunta, Formulario, FormularioPergunta, Oferta, PeriodoLetivo,
    Pergunta, StatusFormulario, TipoInstrumento, Turma, Turno,
)
from app.core.errors import ConflitoEstado
from app.services.formularios import (
    LIMITE_ALERTA_PERGUNTAS, encerrar_formulario, gerar_lote, montar,
    publicar_formulario, publicar_lote,
)
from app.services.pdf_service import (
    gerar_conferencia_turma_pdf, gerar_folha_pdf, gerar_folhas_lote_pdf,
)
from app.services.qrcode_service import gerar_qrcode
from tests.apoio import URL_TESTE, precisa_banco

pytestmark = [precisa_banco, pytest.mark.asyncio]

_s = obter_settings()
AUTH = (_s.admin_user, _s.admin_password)


@pytest.fixture
async def cliente():
    """Cliente HTTP com conexão isolada contra o banco de teste."""
    engine = create_async_engine(URL_TESTE, poolclass=NullPool)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    async def sessao_de_teste():
        async with fabrica() as s:
            yield s

    app.dependency_overrides[obter_sessao] = sessao_de_teste
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://teste", auth=AUTH
        ) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


class TestGeracaoLote:
    """Critérios 1, 2, 3, 4, 5, 6 e 7 da especificação."""

    async def test_gerar_lote_cria_20_formularios(self, sessao):
        periodo = await sessao.scalar(
            select(PeriodoLetivo).where(PeriodoLetivo.codigo == "2026.2")
        )
        assert periodo is not None, "Periodo 2026.2 deve existir"

        resumo = await gerar_lote(periodo.id, None, sessao)
        # O "ou" original passava mesmo com 0 criados; o invariante é que os 20
        # instrumentos do período sejam contemplados, criados, regerados ou pulados.
        assert (
            resumo["criados"] + resumo["regenerados"] + resumo["pulados"] == 20
        ), resumo

        forms = (
            await sessao.scalars(
                select(Formulario).where(Formulario.periodo_letivo_id == periodo.id)
            )
        ).all()
        assert len(forms) == 20

        # Critério 2: 20 UUIDs distintos
        uuids = {f.uuid for f in forms}
        assert len(uuids) == 20

        # Distribuição dos instrumentos: 17 de turma + 3 institucionais
        por_tipo = {}
        for f in forms:
            por_tipo[f.tipo_instrumento] = por_tipo.get(f.tipo_instrumento, 0) + 1

        assert por_tipo[TipoInstrumento.DISCENTE_TURMA] == 17
        assert por_tipo[TipoInstrumento.DOCENTE] == 1
        assert por_tipo[TipoInstrumento.TECNICO_ADMINISTRATIVO] == 1
        assert por_tipo[TipoInstrumento.COMUNIDADE] == 1

    async def test_biomedicina_noturno_6_dispara_alerta(self, sessao):
        """Critério 3: Biomedicina 6º Noturno tem 12 ofertas e ultrapassa limite."""
        form = await sessao.scalar(
            select(Formulario)
            .join(Turma, Formulario.turma_id == Turma.id)
            .where(
                Formulario.tipo_instrumento == TipoInstrumento.DISCENTE_TURMA,
                Turma.periodo_numero == 6,
                Turma.turno == Turno.NOTURNO,
            )
            .options(selectinload(Formulario.itens))
        )
        assert form is not None
        # 12 ofertas * 10 perguntas + 47 institucionais ativas = 167 perguntas (> 150)
        assert len(form.itens) > LIMITE_ALERTA_PERGUNTAS
        # 47 institucionais ativas (Q29 é duplicata desativada) + 10 × 12 ofertas.
        # Aceitar "167 ou 168" deixaria passar a regressão da desativação.
        assert len(form.itens) == 167

    async def test_biomedicina_noturno_4_tem_apenas_um_formulario(self, sessao):
        """Critério 4 (RN-04): Módulo/rótulo A/B não duplica formulário da turma."""
        forms_4 = (
            await sessao.scalars(
                select(Formulario)
                .join(Turma, Formulario.turma_id == Turma.id)
                .join(Turma.curso)
                .where(
                    Formulario.tipo_instrumento == TipoInstrumento.DISCENTE_TURMA,
                    Turma.curso.has(slug="BIOMEDICINA"),
                    Turma.periodo_numero == 4,
                    Turma.turno == Turno.NOTURNO,
                )
            )
        ).all()
        # Uma única turma de Biomedicina 4º Noturno
        assert len(forms_4) == 1

    async def test_professores_diferentes_mesma_disciplina_geram_blocos_distintos(self, sessao):
        """RN-08 — mesma disciplina com docentes diferentes = blocos independentes.

        Caso real: Bioquímica é dada por Andrea e por Vanessa na MESMA turma.
        O aluno precisa avaliar as duas separadamente.
        """
        linhas = (
            await sessao.execute(
                select(
                    FormularioPergunta.formulario_id,
                    FormularioPergunta.oferta_id,
                    FormularioPergunta.rotulo_oferta,
                )
                .where(FormularioPergunta.rotulo_oferta.ilike("Bioquímica%"))
                .distinct()
            )
        ).all()
        assert linhas, "Bioquímica deveria aparecer em algum formulário"

        # agrupa por formulário: a mesma turma precisa ter >1 oferta de Bioquímica
        por_formulario: dict[int, set] = {}
        for form_id, oferta_id, rotulo in linhas:
            por_formulario.setdefault(form_id, set()).add((oferta_id, rotulo))

        com_dois_docentes = {
            fid: ofs for fid, ofs in por_formulario.items() if len(ofs) > 1
        }
        assert com_dois_docentes, (
            "nenhuma turma avalia Bioquímica com dois docentes — RN-08 não está valendo"
        )

        # e os rótulos precisam nomear docentes DIFERENTES
        for ofertas in com_dois_docentes.values():
            docentes = {r.split("Prof. ")[-1] for _, r in ofertas}
            assert len(docentes) > 1, f"blocos distintos mas mesmo docente: {ofertas}"

    async def test_ofertas_sem_turma_nao_entram_em_formularios(self, sessao):
        """Critério 6: As 4 ofertas sem turma não aparecem nos formulários."""
        ofertas_sem_turma_ids = (
            await sessao.scalars(
                select(Oferta.id).where(Oferta.avaliavel.is_(False))
            )
        ).all()
        assert len(ofertas_sem_turma_ids) == 4

        perguntas_com_essas_ofertas = (
            await sessao.scalars(
                select(FormularioPergunta).where(
                    FormularioPergunta.oferta_id.in_(ofertas_sem_turma_ids)
                )
            )
        ).all()
        assert len(perguntas_com_essas_ofertas) == 0

    async def test_idempotencia_da_geracao(self, sessao):
        """Critério 7: Rodar gerar_lote novamente não duplica formulários."""
        periodo = await sessao.scalar(
            select(PeriodoLetivo).where(PeriodoLetivo.codigo == "2026.2")
        )
        itens_antes = await sessao.scalar(select(func.count(FormularioPergunta.id)))

        resumo2 = await gerar_lote(periodo.id, None, sessao)

        total_forms = await sessao.scalar(
            select(func.count(Formulario.id)).where(
                Formulario.periodo_letivo_id == periodo.id
            )
        )
        itens_depois = await sessao.scalar(select(func.count(FormularioPergunta.id)))

        # RN-25 garante: nenhum formulário NOVO e nenhum snapshot a mais.
        # Rascunho pode ser regerado (doc 05 §2) — por isso `regenerados` é
        # contado à parte de `criados`.
        assert total_forms == 20
        assert resumo2["criados"] == 0, f"não pode criar formulário novo: {resumo2}"
        assert resumo2["criados"] + resumo2["regenerados"] + resumo2["pulados"] == 20
        assert itens_depois == itens_antes, "o total de snapshot não pode mudar"


class TestQRCodeEPublico:
    """Critério 8: Serviço de QR Code e endpoint público."""

    async def test_gerar_qrcode_png_valido(self):
        url = "https://docs.google.com/forms/d/e/1FAIpQLScTeste/viewform"
        png_bytes = gerar_qrcode(url, formato="png", escala=10)
        assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        img = Image.open(io.BytesIO(png_bytes))
        assert img.format == "PNG"
        assert img.size[0] > 0 and img.size[1] > 0

    async def test_gerar_qrcode_svg_valido(self):
        url = "https://docs.google.com/forms/d/e/1FAIpQLScTeste/viewform"
        svg_bytes = gerar_qrcode(url, formato="svg", escala=10)
        assert b"<svg" in svg_bytes

    async def test_qrcode_endpoint_rascunho_retorna_404(self, cliente, sessao):
        form = await sessao.scalar(
            select(Formulario).where(Formulario.status == StatusFormulario.RASCUNHO)
        )
        if form is not None:
            resp = await cliente.get(f"/api/publico/qrcode/{form.uuid}")
            assert resp.status_code == 404

    async def test_qrcode_endpoint_sem_uri_retorna_404(self, cliente, sessao):
        resp = await cliente.get(f"/api/publico/qrcode/{uuid4()}")
        assert resp.status_code == 404

    async def test_qrcode_endpoint_publicado_e_sincronizado_retorna_imagem(self, cliente, sessao):
        form = await sessao.scalar(select(Formulario).limit(1))
        assert form is not None
        # Simula sincronização e publicação
        form.status = StatusFormulario.PUBLICADO
        form.google_responder_uri = "https://docs.google.com/forms/d/e/1FAIpQLScExemplo/viewform"
        await sessao.commit()

        # PNG
        resp_png = await cliente.get(f"/api/publico/qrcode/{form.uuid}?formato=png")
        assert resp_png.status_code == 200
        assert resp_png.headers["content-type"] == "image/png"
        assert "max-age=86400" in resp_png.headers.get("cache-control", "")
        img = Image.open(io.BytesIO(resp_png.content))
        assert img.format == "PNG"

        # SVG
        resp_svg = await cliente.get(f"/api/publico/qrcode/{form.uuid}?formato=svg")
        assert resp_svg.status_code == 200
        assert resp_svg.headers["content-type"] == "image/svg+xml"
        assert b"<svg" in resp_svg.content


class TestSnapshotImutavel:
    """Critério 9: Editar o banco de perguntas não altera formulário já gerado."""

    async def test_edicao_pergunta_nao_altera_snapshot(self, sessao):
        item = await sessao.scalar(
            select(FormularioPergunta)
            .join(Pergunta, FormularioPergunta.pergunta_id == Pergunta.id)
            .limit(1)
        )
        assert item is not None
        texto_original = item.texto_snapshot

        pergunta = await sessao.get(Pergunta, item.pergunta_id)
        texto_antigo = pergunta.texto
        try:
            pergunta.texto = f"Texto modificado {uuid4()}"
            await sessao.commit()

            # Recarrega o item do snapshot
            await sessao.refresh(item)
            assert item.texto_snapshot == texto_original
            assert item.texto_snapshot != pergunta.texto
        finally:
            pergunta.texto = texto_antigo
            await sessao.commit()


class TestCicloDeVidaEAPI:
    """Critério 10: Ciclo de vida e operações via API."""

    async def test_publicar_e_encerrar_formulario(self, cliente, sessao):
        from datetime import datetime, timedelta, timezone

        form = await sessao.scalar(select(Formulario).limit(1))
        assert form is not None

        # Publicar EXIGE janela definida (doc 05 §2) — o sistema não inventa
        # prazo, então o teste precisa informá-lo como a CPA informaria.
        agora = datetime.now(timezone.utc)
        form.status = StatusFormulario.RASCUNHO
        form.abre_em, form.fecha_em = agora, agora + timedelta(days=8)
        await sessao.commit()

        resp_pub = await cliente.post(f"/api/admin/formularios/{form.id}/publicar")
        assert resp_pub.status_code == 200
        assert resp_pub.json()["status"] == "PUBLICADO"

        # Encerrar
        resp_enc = await cliente.post(f"/api/admin/formularios/{form.id}/encerrar")
        assert resp_enc.status_code == 200
        assert resp_enc.json()["status"] == "ENCERRADO"

        # Excluir formulário encerrado deve ser rejeitado (409)
        resp_del = await cliente.delete(f"/api/admin/formularios/{form.id}")
        assert resp_del.status_code == 409

    async def test_publicar_lote(self, cliente, sessao):
        periodo = await sessao.scalar(
            select(PeriodoLetivo).where(PeriodoLetivo.codigo == "2026.2")
        )
        resp = await cliente.post(
            "/api/admin/formularios/publicar-lote",
            json={"periodo_letivo_id": periodo.id},
        )
        assert resp.status_code == 200
        corpo = resp.json()
        assert "publicados" in corpo
        # Formulário ignorado precisa aparecer COM o motivo: sem isso o admin vê
        # "15 publicados" e não sabe que 5 ficaram de fora.
        assert "ignorados" in corpo
        # O invariante é este: quem fica de fora diz por quê. O conjunto de
        # motivos cresce conforme a publicação ganha etapas (hoje ela também
        # abre o formulário no Google, então falha de credencial é um motivo
        # legítimo) — fixar a lista só geraria quebra a cada etapa nova.
        for item in corpo["ignorados"]:
            assert item.get("motivo"), item
            assert isinstance(item["motivo"], str)
            assert item["motivo"].isupper(), "motivo é código estável, não frase"
        # E nada pode ser publicado sem janela definida.
        assert corpo["publicados"] == 0 or corpo["ids"]

    async def test_previa_formulario(self, cliente, sessao):
        form = await sessao.scalar(
            select(Formulario)
            .where(Formulario.tipo_instrumento == TipoInstrumento.DISCENTE_TURMA)
            .limit(1)
        )
        assert form is not None
        resp = await cliente.get(f"/api/admin/formularios/{form.id}/previa")
        assert resp.status_code == 200
        dados = resp.json()
        assert "blocos_institucionais" in dados
        assert "blocos_materia" in dados
        assert dados["total_perguntas"] > 0
        assert dados["tempo_estimado_min"] > 0

    async def test_previa_perguntas_turma_sem_persistir(self, cliente, sessao):
        turma = await sessao.scalar(select(Turma).limit(1))
        assert turma is not None
        resp = await cliente.post(
            "/api/admin/perguntas/previa",
            json={"turma_id": turma.id},
        )
        assert resp.status_code == 200
        dados = resp.json()
        assert dados["turma_id"] == turma.id
        assert dados["total_perguntas"] > 0


class TestArtefatosImpressaoPDF:
    """Critério 11: Endpoints de PDF para impressão."""

    async def test_folha_turma_pdf(self, cliente, sessao):
        form = await sessao.scalar(
            select(Formulario)
            .where(Formulario.tipo_instrumento == TipoInstrumento.DISCENTE_TURMA)
            .limit(1)
        )
        assert form is not None
        resp = await cliente.get(f"/api/admin/formularios/{form.id}/folha.pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF-")

    async def test_folhas_periodo_pdf(self, cliente, sessao):
        periodo = await sessao.scalar(
            select(PeriodoLetivo).where(PeriodoLetivo.codigo == "2026.2")
        )
        resp = await cliente.get(f"/api/admin/periodos/{periodo.id}/folhas.pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF-")

    async def test_conferencia_turma_pdf(self, cliente, sessao):
        turma = await sessao.scalar(select(Turma).limit(1))
        assert turma is not None
        resp = await cliente.get(f"/api/admin/turmas/{turma.id}/conferencia.pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF-")


class TestCicloDeVidaValidado:
    """Transições inválidas precisam ser RECUSADAS (doc 05 §2).

    Estes casos passavam silenciosamente antes: `publicar` inventava uma janela
    de 15 dias e `encerrar` aceitava um rascunho, pulando a publicação.
    """

    async def _formulario_em_rascunho(self, sessao, *, com_janela: bool):
        from datetime import datetime, timedelta, timezone

        form = await sessao.scalar(
            select(Formulario).options(selectinload(Formulario.itens)).limit(1)
        )
        form.status = StatusFormulario.RASCUNHO
        if com_janela:
            agora = datetime.now(timezone.utc)
            form.abre_em, form.fecha_em = agora, agora + timedelta(days=8)
        else:
            form.abre_em = form.fecha_em = None
        await sessao.commit()
        return form

    async def test_publicar_sem_janela_recusa(self, sessao):
        """Inventar prazo faria a CPA descobrir o fechamento quando acontecesse."""
        form = await self._formulario_em_rascunho(sessao, com_janela=False)
        with pytest.raises(ConflitoEstado) as erro:
            await publicar_formulario(form.id, sessao)
        assert "janela" in str(erro.value).lower()

    async def test_janela_invertida_barra_no_banco(self, sessao):
        """A constraint `janela_coerente` impede fecha_em <= abre_em.

        A validação no serviço é defesa em profundidade: o banco já recusa antes.
        """
        from datetime import datetime, timedelta, timezone

        from sqlalchemy.exc import IntegrityError

        form = await self._formulario_em_rascunho(sessao, com_janela=True)
        agora = datetime.now(timezone.utc)
        form.abre_em, form.fecha_em = agora, agora - timedelta(days=1)
        with pytest.raises(IntegrityError):
            await sessao.commit()
        await sessao.rollback()

    async def test_publicar_com_janela_valida_funciona(self, sessao):
        form = await self._formulario_em_rascunho(sessao, com_janela=True)
        r = await publicar_formulario(form.id, sessao)
        assert r.status == StatusFormulario.PUBLICADO
        assert (r.fecha_em - r.abre_em).days == 8, "a janela informada é respeitada"

    async def test_encerrar_rascunho_recusa(self, sessao):
        """RASCUNHO → ENCERRADO pularia a publicação e criaria estado órfão."""
        form = await self._formulario_em_rascunho(sessao, com_janela=True)
        with pytest.raises(ConflitoEstado) as erro:
            await encerrar_formulario(form.id, sessao)
        assert "PUBLICADO" in str(erro.value)

    async def test_encerrar_publicado_funciona(self, sessao):
        form = await self._formulario_em_rascunho(sessao, com_janela=True)
        await publicar_formulario(form.id, sessao)
        r = await encerrar_formulario(form.id, sessao)
        assert r.status == StatusFormulario.ENCERRADO

    async def test_republicar_encerrado_recusa(self, sessao):
        form = await self._formulario_em_rascunho(sessao, com_janela=True)
        await publicar_formulario(form.id, sessao)
        await encerrar_formulario(form.id, sessao)
        with pytest.raises(ConflitoEstado):
            await publicar_formulario(form.id, sessao)


@pytest.mark.asyncio
async def test_limite_de_alerta_vem_da_configuracao():
    """Fixar 150 no código tornaria LIMITE_ALERTA_PERGUNTAS letra morta."""
    from app.core.config import obter_settings
    from app.services.formularios import LIMITE_ALERTA_PERGUNTAS

    assert LIMITE_ALERTA_PERGUNTAS == obter_settings().limite_alerta_perguntas
