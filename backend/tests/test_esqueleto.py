"""Fase 0 — o esqueleto responde e a configuração é coerente."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.texto import slugificar
from app.main import app

cliente = TestClient(app)


def test_health_responde():
    r = cliente.get("/api/health")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["status"] == "ok"
    assert "banco" in corpo and "versao" in corpo


def test_docs_abre():
    assert cliente.get("/docs").status_code == 200


def test_frontend_url_sem_barra_final():
    s = Settings(frontend_url="https://cpa.exemplo.br/")
    assert s.frontend_url_limpa == "https://cpa.exemplo.br"


def test_origens_cors_incluem_localhost():
    s = Settings(frontend_url="https://cpa.exemplo.br")
    assert "https://cpa.exemplo.br" in s.origens_cors
    assert "http://localhost:3000" in s.origens_cors


def test_faixas_isg():
    assert Settings().faixas_isg == [0.25, 0.46, 0.72]


class TestSlugificar:
    """doc 02 — normalização usada por importador e matching."""

    def test_remove_acento_e_pontuacao(self):
        assert slugificar("Profa Victória") == "profa victoria"
        assert slugificar("Bioética e Deontologia") == "bioetica e deontologia"

    def test_colapsa_espacos(self):
        assert slugificar("Prof  Prof   André") == "prof prof andre"

    def test_nao_resolve_typo(self):
        # Limitação deliberada: typo é papel do fuzzy matching (doc 03 §4).
        assert slugificar("Washignton") != slugificar("Washington")

    def test_vazio(self):
        assert slugificar("") == ""
        assert slugificar(None) == ""
