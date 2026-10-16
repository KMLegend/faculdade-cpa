"""Credenciais OAuth2 a partir do refresh token (doc 10 §4).

O refresh token é obtido uma vez por `scripts/autorizar_google.py` e vive em
variável de ambiente. Aqui ele vira um objeto de credenciais que a biblioteca
do Google renova sozinha quando o access token expira.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import obter_settings
from app.core.errors import CredencialInvalida

ESCOPOS = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/drive.file",
]

TOKEN_URI = "https://oauth2.googleapis.com/token"


def configurado() -> bool:
    """As três variáveis obrigatórias estão presentes?"""
    s = obter_settings()
    return bool(s.google_client_id and s.google_client_secret and s.google_refresh_token)


@lru_cache
def obter_credenciais():
    """Credenciais prontas para a API. Cacheadas: a renovação é interna."""
    if not configurado():
        raise CredencialInvalida(
            "Integração com o Google não configurada. Gere as credenciais com "
            "`python -m scripts.autorizar_google` (Anexo C).",
            {"faltando": _faltando()},
        )
    try:
        from google.oauth2.credentials import Credentials
    except ImportError as exc:  # pragma: no cover - dependência declarada
        raise CredencialInvalida(
            "Biblioteca do Google ausente. Instale as dependências do backend.",
            {"erro": str(exc)},
        ) from exc

    s = obter_settings()
    return Credentials(
        token=None,
        refresh_token=s.google_refresh_token,
        client_id=s.google_client_id,
        client_secret=s.google_client_secret,
        token_uri=TOKEN_URI,
        scopes=ESCOPOS,
    )


def _faltando() -> list[str]:
    s = obter_settings()
    return [
        nome
        for nome, valor in (
            ("GOOGLE_CLIENT_ID", s.google_client_id),
            ("GOOGLE_CLIENT_SECRET", s.google_client_secret),
            ("GOOGLE_REFRESH_TOKEN", s.google_refresh_token),
        )
        if not valor
    ]


def limpar_cache() -> None:
    """Após trocar o refresh token sem reiniciar o serviço."""
    obter_credenciais.cache_clear()
