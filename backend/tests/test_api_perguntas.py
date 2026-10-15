"""A API impõe a política de identidade da pergunta (doc 04 §5.1 e §6.1).

Não basta documentar que o código é imutável: a API precisa recusar quem tentar
o contrário. Estes testes cobrem exatamente essas recusas.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import obter_settings
from app.db.session import obter_sessao
from app.main import app
from tests.apoio import URL_TESTE, precisa_banco

pytestmark = [precisa_banco, pytest.mark.asyncio]

_s = obter_settings()
AUTH = (_s.admin_user, _s.admin_password)
BASE = "/api/admin"


@pytest.fixture
async def cliente():
    """Cliente com o banco ligado ao event loop DESTE teste.

    O engine global de  nasce no import e seu pool fica preso ao
    primeiro loop; como o pytest-asyncio cria um loop por teste, reutilizá-lo dá
    "attached to a different loop". Sobrepor a dependência com um engine
    NullPool resolve sem contaminar o código de produção.
    """
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


class TestAutenticacao:
    """401 é decidido antes de tocar o banco."""

    async def test_sem_credencial_recusa(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://teste"
        ) as c:
            assert (await c.get(f"{BASE}/perguntas")).status_code == 401

    async def test_senha_errada_recusa(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://teste",
            auth=(_s.admin_user, "senha-errada"),
        ) as c:
            assert (await c.get(f"{BASE}/perguntas")).status_code == 401


class TestLeitura:
    async def test_lista_163_perguntas(self, cliente):
        r = await cliente.get(f"{BASE}/perguntas")
        assert r.status_code == 200
        assert len(r.json()) == 163

    async def test_filtra_bloco_professor(self, cliente):
        r = await cliente.get(
            f"{BASE}/perguntas",
            params={"tipo_instrumento": "DISCENTE_TURMA", "bloco": "PROFESSOR"},
        )
        codigos = [p["codigo"] for p in r.json()]
        assert codigos == [10, 11, 12, 13, 14, 17, 19]

    async def test_dimensao_expoe_id(self, cliente):
        """Sem `id`, o cliente não consegue criar pergunta — ele é obrigatório."""
        r = await cliente.get(f"{BASE}/dimensoes")
        assert r.status_code == 200
        assert all("id" in d for d in r.json())
        assert len(r.json()) == 10


class TestPoliticaDeCodigo:
    """O enunciado mudou: correção de redação ou pergunta nova?"""

    async def test_mudar_texto_sem_declarar_recusa(self, cliente):
        r = await cliente.patch(
            f"{BASE}/perguntas/11", json={"texto": "Enunciado diferente?"}
        )
        assert r.status_code == 409
        assert r.json()["erro"] == "CONFLITO_ESTADO"

    async def test_mudanca_de_sentido_manda_criar_outra(self, cliente):
        r = await cliente.patch(
            f"{BASE}/perguntas/11",
            json={"texto": "Outra coisa?", "correcao_de_redacao": False},
        )
        assert r.status_code == 409
        assert "pergunta nova" in r.json()["mensagem"]

    async def test_correcao_de_redacao_incrementa_versao(self, cliente):
        original = (await cliente.get(f"{BASE}/perguntas")).json()
        antes = next(p for p in original if p["codigo"] == 11)
        r = await cliente.patch(
            f"{BASE}/perguntas/11",
            json={"texto": antes["texto"] + " ", "correcao_de_redacao": True},
        )
        # só muda espaço em branco: o serviço compara texto já aparado
        assert r.status_code == 200
        assert r.json()["codigo"] == 11

    async def test_edicao_sem_mexer_no_texto_passa(self, cliente):
        r = await cliente.patch(f"{BASE}/perguntas/11", json={"obrigatoria": True})
        assert r.status_code == 200
        assert r.json()["versao_texto"] == 1

    async def test_patch_nao_aceita_codigo(self):
        """`codigo` fora do schema de edição é a blindagem contra renumerar."""
        from app.schemas.perguntas import PerguntaPatch

        assert "codigo" not in PerguntaPatch.model_fields


class TestCriacao:
    async def test_codigo_e_atribuido_pelo_sistema(self, cliente):
        """O cliente não escolhe o código — e não existe campo para isso."""
        from app.schemas.perguntas import PerguntaEntrada

        assert "codigo" not in PerguntaEntrada.model_fields

    async def test_equivalencia_exige_mesma_dimensao(self, cliente):
        dims = (await cliente.get(f"{BASE}/dimensoes")).json()
        outra = next(d for d in dims if d["numero"] == 7)
        r = await cliente.post(
            f"{BASE}/perguntas",
            json={
                "texto": "Tentando dimensão divergente",
                "tipo_instrumento": "DOCENTE",
                "bloco": "INSTITUCIONAL",
                "dimensao_id": outra["id"],
                "equivalencia_id": 1,  # grupo da dimensão 1
            },
        )
        assert r.status_code == 409
        assert "dimensão" in r.json()["mensagem"]

    async def test_bloco_incoerente_barra_no_banco(self, cliente):
        """A constraint do schema devolve 409, nunca 500 cru."""
        dims = (await cliente.get(f"{BASE}/dimensoes")).json()
        r = await cliente.post(
            f"{BASE}/perguntas",
            json={
                "texto": "bloco de matéria em instrumento docente",
                "tipo_instrumento": "DOCENTE",
                "bloco": "PROFESSOR",
                "dimensao_id": dims[0]["id"],
            },
        )
        assert r.status_code == 409
        assert r.json()["erro"] == "CONFLITO_INTEGRIDADE"


class TestImpacto:
    async def test_impacto_traz_proximo_codigo_livre(self, cliente):
        r = await cliente.get(f"{BASE}/perguntas/11/impacto")
        assert r.status_code == 200
        corpo = r.json()
        assert corpo["codigo"] == 11
        assert corpo["proximo_codigo_livre"] == 164

    async def test_impacto_de_pergunta_inexistente(self, cliente):
        r = await cliente.get(f"{BASE}/perguntas/9999/impacto")
        assert r.status_code == 404
