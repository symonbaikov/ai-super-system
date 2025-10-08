import os
import uuid
from pathlib import Path
from typing import Optional

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./backend/tests/test_api.db")

from backend.api import dependencies  # noqa: E402
from backend.api.database import close_database, get_session, init_database  # noqa: E402
from backend.api.main import app  # noqa: E402
from backend.api.models import Alert, Candidate  # noqa: E402
from backend.api.services.whales import WhaleScanService  # noqa: E402

_DB_PATH = Path("backend/tests/test_api.db")


class FakeQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, dict]] = []
        self.published: list[dict] = []

    async def connect(self) -> None:  # pragma: no cover - compatibility stub
        return None

    async def close(self) -> None:  # pragma: no cover - compatibility stub
        return None

    async def enqueue(
        self, queue_name: str, payload: dict, *, job_id: Optional[uuid.UUID] = None
    ) -> uuid.UUID:
        job_uuid = job_id or uuid.uuid4()
        self.enqueued.append((queue_name, payload))
        return job_uuid

    async def publish_alert(self, payload: dict) -> None:
        self.published.append(payload)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def fake_queue(monkeypatch: pytest.MonkeyPatch) -> FakeQueue:
    queue = FakeQueue()
    original = getattr(dependencies, "_queue_service", None)
    dependencies._queue_service = queue  # type: ignore[attr-defined]
    try:
        yield queue
    finally:
        if original is not None:
            dependencies._queue_service = original  # type: ignore[attr-defined]


@pytest.fixture
def fake_whale_service(monkeypatch: pytest.MonkeyPatch) -> WhaleScanService:
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    service = WhaleScanService(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        namespace="sp",
        result_ttl=600,
        redis_client=fake_redis,
    )
    original = getattr(dependencies, "_whale_service", None)
    dependencies._whale_service = service  # type: ignore[attr-defined]
    try:
        yield service
    finally:
        if original is not None:
            dependencies._whale_service = original  # type: ignore[attr-defined]


@pytest_asyncio.fixture
async def api_client(fake_queue: FakeQueue, fake_whale_service: WhaleScanService):
    if _DB_PATH.exists():
        _DB_PATH.unlink()

    await init_database()
    await dependencies.connect_queue()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, fake_queue

    await dependencies.close_queue()
    await close_database()

    if _DB_PATH.exists():
        _DB_PATH.unlink()


async def _fetch_candidates() -> list[Candidate]:
    gen = get_session()
    session = await gen.__anext__()
    try:
        result = await session.execute(select(Candidate))
        return result.scalars().all()
    finally:
        await session.close()
        await gen.aclose()


async def _fetch_alerts() -> list[Alert]:
    gen = get_session()
    session = await gen.__anext__()
    try:
        result = await session.execute(select(Alert))
        return result.scalars().all()
    finally:
        await session.close()
        await gen.aclose()
