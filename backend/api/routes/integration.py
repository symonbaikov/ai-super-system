from __future__ import annotations

import random
import string
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..dependencies import (
    get_db_session,
    get_queue_service,
    get_settings_dependency,
    get_whale_service,
)
from ..models import Candidate
from ..schemas.whales import WhaleScanRequest, WhaleScanResponse, WhaleTopEntry
from ..services.queue import QueueService
from ..services.whales import WhaleScanService

router = APIRouter(prefix="/api", tags=["integration"])


def _random_job_id(prefix: str = "job") -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
    return f"{prefix}-{suffix}"


@router.get("/metrics/latency-usage")
async def get_latency_usage() -> dict[str, Any]:
    return {
        "apify_ms": random.randint(80, 220),
        "helius_ms": random.randint(40, 150),
        "parser_ms": random.randint(25, 80),
        "apify_credits_used": random.randint(1, 25),
        "groq_credits_used": random.randint(1, 15),
        "suggestion": "Reduce Apify frequency to 10 minutes if credits > 80%",
    }


@router.post("/cex-radar/search")
async def post_cex_radar_search(payload: dict[str, Any]) -> dict[str, str]:
    if "query" not in payload or not isinstance(payload["query"], str) or not payload["query"].strip():
        raise HTTPException(status_code=400, detail="query is required")
    return {"jobId": _random_job_id("cex")}


@router.get("/cex-radar/result")
async def get_cex_radar_result(jobId: str = Query(...)) -> list[dict[str, Any]]:  # pylint: disable=invalid-name
    now = datetime.now(timezone.utc)
    return [
        {
            "exchange": "Binance",
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "team": "doxxed",
            "url": "https://birdeye.so/token/So11111111111111111111111111111111111111112?chain=solana",
            "social": {"tw_1h": 240, "tg_online": 1800},
        }
    ]


@router.get("/helius/mints")
async def get_helius_mints() -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    return [
        {
            "name": "$DOGE99",
            "mint": "So11111111111111111111111111111111111111112",
            "team": "anon",
            "original": True,
            "safe": True,
            "hasTw": True,
            "sol": round(random.uniform(5, 40), 2),
            "ts": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
    ]


@router.post(
    "/whales/scan",
    response_model=WhaleScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_whales_scan(
    payload: WhaleScanRequest = Body(default_factory=WhaleScanRequest),
    queue: QueueService = Depends(get_queue_service),
    settings: Settings = Depends(get_settings_dependency),
    whales: WhaleScanService = Depends(get_whale_service),
) -> WhaleScanResponse:
    job_id = await whales.enqueue_scan(queue, settings.whales_queue_name, payload)
    return WhaleScanResponse(jobId=job_id)


@router.get("/whales/top3", response_model=list[WhaleTopEntry])
async def get_whales_top3(
    jobId: str = Query(..., description="Job identifier returned by /api/whales/scan"),  # pylint: disable=invalid-name
    whales: WhaleScanService = Depends(get_whale_service),
) -> list[WhaleTopEntry]:
    result = await whales.get_result(jobId)
    if result is None:
        exists = await whales.has_job(jobId)
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail="pending")
    return [entry for entry in result.items]


def _resolve_detected_at(candidate: Candidate, metadata: dict[str, Any]) -> str:
    detected_at = metadata.get("detectedAt")
    if isinstance(detected_at, str) and detected_at.strip():
        return detected_at
    created_at = candidate.created_at or datetime.utcnow()
    return created_at.strftime("%Y-%m-%d %H:%M")


def _resolve_safety(metadata: dict[str, Any]) -> dict[str, bool]:
    safety_meta = metadata.get("safety")
    if not isinstance(safety_meta, dict):
        safety_meta = {}
    return {
        "noMint": bool(safety_meta.get("noMint", False)),
        "burnLP": bool(safety_meta.get("burnLP", False)),
        "blacklist": bool(safety_meta.get("blacklist", False)),
    }


@router.get("/signals")
async def get_signals(
    limit: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Return latest candidates mapped to the UI format."""

    result = await session.execute(
        select(Candidate).order_by(Candidate.created_at.desc()).limit(limit)
    )
    candidates = result.scalars().all()

    signals: list[dict[str, Any]] = []
    for candidate in candidates:
        meta = candidate.meta or {}
        metadata = meta.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}

        signal = {
            "id": str(candidate.id),
            "word": metadata.get("word") or candidate.symbol,
            "isOG": bool(metadata.get("isOG", False)),
            "type": metadata.get("type") or "слово",
            "detectedAt": _resolve_detected_at(candidate, metadata),
            "source": metadata.get("source") or candidate.source,
            "author": metadata.get("author") or "@unknown",
            "link": metadata.get("link") or "",
            "tweetCount": metadata.get("tweetCount", 0),
            "communitySize": metadata.get("communitySize", 0),
            "nameChanges": metadata.get("nameChanges", 0),
            "spamScore": metadata.get("spamScore", 0.0),
            "devTeam": metadata.get("devTeam") or "unknown",
            "communityLink": metadata.get("communityLink") or "",
            "contract": metadata.get("contract") or metadata.get("mint") or candidate.symbol,
            "chain": metadata.get("chain") or "Solana",
            "safety": _resolve_safety(metadata),
            "summary": metadata.get("summary") or meta.get("summary") or "",
        }
        signals.append(signal)

    return signals


@router.post("/alerts/enable")
async def post_alerts_enable(payload: dict[str, Any]) -> dict[str, bool]:
    required_keys = {"mint", "msar", "volume", "liquidity", "enabled"}
    if not required_keys.issubset(payload.keys()):
        raise HTTPException(status_code=400, detail="missing fields")
    return {"ok": True}


@router.get("/alerts")
async def get_alerts() -> list[dict[str, Any]]:
    return [
        {
            "mint": "So11111111111111111111111111111111111111112",
            "msar": 0.62,
            "volume": 5200,
            "liquidity": 21000,
            "enabled": True,
        }
    ]


@router.post("/ai/infer")
async def post_ai_infer(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("provider") != "gemini":
        raise HTTPException(status_code=400, detail="unsupported provider")
    return {
        "text": "Gemini response placeholder: market outlook is cautiously bullish.",
        "tokens": {"input": 512, "output": 240},
        "cost_usd": 0.0125,
    }
