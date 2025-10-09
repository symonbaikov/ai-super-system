from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis

from ..schemas.whales import WhaleScanRequest, WhaleScanResult


class WhaleScanService:
    """Manage whale scan jobs and results stored in Redis."""

    def __init__(
        self,
        redis_url: str,
        namespace: str,
        *,
        result_ttl: int = 600,
        redis_client: Optional[Redis] = None,
    ) -> None:
        self._redis_url = redis_url
        self._namespace = namespace
        self._result_ttl = result_ttl
        self._redis: Optional[Redis] = redis_client

    async def connect(self) -> None:
        if self._redis is None:
            self._redis = Redis.from_url(self._redis_url, encoding="utf-8", decode_responses=True)

    async def close(self) -> None:
        if self._redis is not None:
            close = getattr(self._redis, "aclose", None)
            if callable(close):
                await close()
            else:
                await self._redis.close()
            self._redis = None

    def _require_redis(self) -> Redis:
        if self._redis is None:
            raise RuntimeError("WhaleScanService is not connected")
        return self._redis

    def _status_key(self, job_id: str) -> str:
        return f"{self._namespace}:whales:status:{job_id}"

    def _result_key(self, job_id: str) -> str:
        return f"{self._namespace}:whales:result:{job_id}"

    async def mark_status(self, job_id: str, status: str, *, extra: Optional[dict[str, Any]] = None) -> None:
        redis = self._require_redis()
        payload: dict[str, Any] = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            payload.update(extra)
        await redis.hset(self._status_key(job_id), mapping=payload)
        await redis.expire(self._status_key(job_id), self._result_ttl)

    async def enqueue_scan(
        self,
        queue,
        queue_name: str,
        request: WhaleScanRequest,
    ) -> str:
        filters = request.model_dump(exclude_unset=True, exclude_none=True)
        job_uuid = await queue.enqueue(queue_name, {"filters": filters})
        job_id = str(job_uuid)
        await self.mark_status(job_id, "queued", extra={"filters": json.dumps(filters)})
        return job_id

    async def store_result(self, result: WhaleScanResult) -> None:
        redis = self._require_redis()
        payload = jsonable_encoder(result, by_alias=True)
        await redis.set(
            self._result_key(result.jobId),
            json.dumps(payload),
            ex=self._result_ttl,
        )
        await self.mark_status(
            result.jobId,
            "completed",
            extra={"generated_at": result.generated_at.isoformat()},
        )

    async def get_result(self, job_id: str) -> Optional[WhaleScanResult]:
        redis = self._require_redis()
        raw = await redis.get(self._result_key(job_id))
        if not raw:
            return None
        data = json.loads(raw)
        return WhaleScanResult.model_validate(data)

    async def has_job(self, job_id: str) -> bool:
        redis = self._require_redis()
        return bool(await redis.exists(self._status_key(job_id)))
