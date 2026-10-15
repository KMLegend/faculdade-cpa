"""Fixtures compartilhadas."""

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.apoio import URL_TESTE


@pytest_asyncio.fixture
async def sessao():
    """Sessão de leitura contra o banco do compose."""
    engine = create_async_engine(URL_TESTE)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as s:
        yield s
    await engine.dispose()
