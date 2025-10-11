from __future__ import annotations

import json
import time
import uuid
from datetime import date, datetime
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

    def _require_redis(self) -> Redis:
        if self._redis is None:
            raise RuntimeError("QueueService is not connected")
        return self._redis

    @staticmethod
    def _json_dumps(payload: Any) -> str:
        def _default(obj: Any) -> str:
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)!r} is not JSON serializable")

        return json.dumps(payload, default=_default)

    async def enqueue(self, queue_name: str, payload: dict[str, Any], *, job_id: Optional[uuid.UUID] = None) -> uuid.UUID:
        redis = self._require_redis()
        job_uuid = job_id or uuid.uuid4()
        job = {
            "id": str(job_uuid),
            "queue": queue_name,
            "payload": payload,
            "enqueued_at": int(time.time()),
        }
        await redis.rpush(self._queue_key(queue_name), json.dumps(job))
        return job_uuid

    async def publish_alert(self, payload: dict[str, Any]) -> None:
        redis = self._require_redis()
        await redis.publish(f"{self._namespace}:alerts", json.dumps(payload))

    async def lpush_json(self, key: str, payload: dict[str, Any]) -> None:
        redis = self._require_redis()
        await redis.lpush(key, self._json_dumps(payload))

    async def lrange(self, key: str, start: int = 0, stop: int = -1) -> list[str]:
        redis = self._require_redis()
        return await redis.lrange(key, start, stop)

    async def ltrim(self, key: str, start: int, stop: int) -> None:
        redis = self._require_redis()
        await redis.ltrim(key, start, stop)

    async def get(self, key: str) -> Optional[str]:
        redis = self._require_redis()
        return await redis.get(key)

    async def set_json(self, key: str, payload: Any) -> None:
        redis = self._require_redis()
        await redis.set(key, self._json_dumps(payload))

    async def hgetall(self, key: str) -> dict[str, str]:
        redis = self._require_redis()
        return await redis.hgetall(key)

    async def hset_json(self, key: str, field: str, payload: Any) -> None:
        redis = self._require_redis()
        await redis.hset(key, field, self._json_dumps(payload))

    async def hincrby(self, key: str, field: str, increment: int = 1) -> int:
        redis = self._require_redis()
        return await redis.hincrby(key, field, increment)

    async def exists(self, key: str) -> bool:
        redis = self._require_redis()
        return bool(await redis.exists(key))
