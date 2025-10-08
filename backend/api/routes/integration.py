from __future__ import annotations

import random
import string
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

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


@router.post("/whales/scan")
async def post_whales_scan(payload: Optional[dict[str, Any]] = None) -> dict[str, str]:
    return {"jobId": _random_job_id("whale")}


@router.get("/whales/top3")
async def get_whales_top3(jobId: str = Query(...)) -> list[dict[str, Any]]:  # pylint: disable=invalid-name
    return [
        {
            "mint": "So11111111111111111111111111111111111111112",
            "name": "$TRUMP42",
            "whales": 5,
            "sol_sum": 38.2,
            "safety": {"rugcheck": "ok", "solsniffer": "warn"},
            "hype": {"tw_1h": 320, "tg_1h": 210},
            "links": {
                "birdeye": "https://birdeye.so/token/So11111111111111111111111111111111111111112?chain=solana",
            },
        }
    ]


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
