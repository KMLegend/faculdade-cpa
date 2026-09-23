"""Autenticação do painel: Basic Auth estática (doc 06 §1).

Aceitável no MVP porque não há dado pessoal de respondente no sistema — a coleta
acontece no Google Forms (doc 10). Ao adicionar perfis, trocar por JWT.
"""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import obter_settings

_basic = HTTPBasic(auto_error=False)


def exigir_admin(
    credenciais: HTTPBasicCredentials | None = Depends(_basic),
) -> str:
    s = obter_settings()
    if credenciais is None:
        _negar()

    usuario_ok = secrets.compare_digest(credenciais.username, s.admin_user)
    senha_ok = secrets.compare_digest(credenciais.password, s.admin_password)
    if not (usuario_ok and senha_ok):
        _negar()
    return credenciais.username


def _negar() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "erro": "NAO_AUTORIZADO",
            "mensagem": "Credenciais inválidas.",
            "detalhes": {},
        },
        headers={"WWW-Authenticate": "Basic"},
    )
