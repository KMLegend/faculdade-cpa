"""Engine assíncrona e sessão por requisição."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import obter_settings

_settings = obter_settings()

engine = create_async_engine(_settings.database_url, pool_pre_ping=True, future=True)

SessaoLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def obter_sessao() -> AsyncGenerator[AsyncSession, None]:
    async with SessaoLocal() as sessao:
        yield sessao
