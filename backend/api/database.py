from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings
from .models import Base

_settings = get_settings()
_engine = create_async_engine(_settings.database_url, echo=_settings.api_debug, future=True)
_SessionFactory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with _SessionFactory() as session:
        yield session


async def init_database() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    await _engine.dispose()
