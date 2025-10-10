from collections.abc import AsyncIterator
import os
import sys

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings
from .models import Base

_settings = get_settings()

# Prefer an isolated SQLite DB when running under pytest to avoid leaking
# state from a Postgres instance provided via container environment.
_database_url = _settings.database_url
is_pytest = "pytest" in sys.modules or bool(os.environ.get("PYTEST_CURRENT_TEST"))
if is_pytest:
    # Use a writable path inside containers to avoid permission/relative-path issues
    if not _database_url.startswith("sqlite"):
        _database_url = "sqlite+aiosqlite:////tmp/test_api.db"
    else:
        # Normalise any relative sqlite path to a safe absolute one
        if ":///" in _database_url and not _database_url.startswith("sqlite+aiosqlite:////"):
            _database_url = "sqlite+aiosqlite:////tmp/test_api.db"

_engine = create_async_engine(_database_url, echo=_settings.api_debug, future=True)
_SessionFactory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with _SessionFactory() as session:
        yield session


async def init_database() -> None:
    async with _engine.begin() as conn:
        # Ensure a clean schema when running tests in a shared process
        if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    await _engine.dispose()
