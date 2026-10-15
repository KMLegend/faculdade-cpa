"""Auxiliares de teste: acesso ao banco do compose.

Os testes de banco são pulados quando o Postgres não está acessível, para que a
suíte continue rodando offline (CI sem serviços).
"""

import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

URL_TESTE = os.getenv(
    "DATABASE_URL_TESTE", "postgresql+asyncpg://cpa:cpa@localhost:5432/cpa"
)


def _banco_acessivel() -> bool:
    async def tentar() -> bool:
        engine = create_async_engine(URL_TESTE)
        try:
            async with engine.connect() as c:
                await c.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
        finally:
            await engine.dispose()

    try:
        return asyncio.run(tentar())
    except Exception:
        return False


BANCO_OK = _banco_acessivel()

precisa_banco = pytest.mark.skipif(
    not BANCO_OK,
    reason="Postgres indisponível — suba com `docker compose --profile offline up -d banco`",
)
