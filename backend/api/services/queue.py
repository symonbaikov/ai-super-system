from __future__ import annotations

import json
import time
import uuid
from typing import Any, Optional

from redis.asyncio import Redis


class QueueService:
    """Minimal Redis-based queue helper bridging FastAPI → Node worker."""

    def __init__(self, redis_url: str, namespace: str = "sp") -> None:
        self._redis_url = redis_url
        self._namespace = namespace
        self._redis: Optional[Redis] = None

    async def connect(self) -> None:
        if self._redis is None:
            self._redis = Redis.from_url(self._redis_url, encoding="utf-8", decode_responses=True)

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    def _queue_key(self, queue_name: str) -> str:
        return f"{self._namespace}:queue:{queue_name}"

    async def enqueue(self, queue_name: str, payload: dict[str, Any], *, job_id: Optional[uuid.UUID] = None) -> uuid.UUID:
        if self._redis is None:
            raise RuntimeError("QueueService is not connected")
        job_uuid = job_id or uuid.uuid4()
        job = {
            "id": str(job_uuid),
            "queue": queue_name,
            "payload": payload,
            "enqueued_at": int(time.time()),
        }
        await self._redis.rpush(self._queue_key(queue_name), json.dumps(job))
        return job_uuid

    async def publish_alert(self, payload: dict[str, Any]) -> None:
        if self._redis is None:
            raise RuntimeError("QueueService is not connected")
        await self._redis.publish(f"{self._namespace}:alerts", json.dumps(payload))
