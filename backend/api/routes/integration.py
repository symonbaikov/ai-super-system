from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..config import Settings
from ..dependencies import get_gemini_service, get_queue_service, get_settings_dependency
from ..services.gemini import GeminiService
from ..services.queue import QueueService

router = APIRouter(prefix="/api", tags=["integration"])


def _namespaced_keys(settings: Settings, base: str) -> list[str]:
    namespace = (settings.queue_namespace or "").strip()
    if namespace:
        return [f"{namespace}:{base}", base]
    return [base]


async def _first_existing_key(
    queue: QueueService,
    settings: Settings,
    base: str,
    *,
    candidates: Optional[Iterable[str]] = None,
) -> str:
    keys = list(candidates) if candidates is not None else _namespaced_keys(settings, base)
    for key in keys:
        if await queue.exists(key):
            return key
    return keys[0]


async def _load_hash(queue: QueueService, settings: Settings, base: str) -> dict[str, str]:
    for key in _namespaced_keys(settings, base):
        data = await queue.hgetall(key)
        if data:
            return data
    return {}


async def _load_json_value(queue: QueueService, settings: Settings, base: str) -> Any:
    for key in _namespaced_keys(settings, base):
        raw = await queue.get(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="invalid cached payload") from exc
    return None


async def _load_list(queue: QueueService, settings: Settings, base: str, *, limit: int = 50) -> list[str]:
    for key in _namespaced_keys(settings, base):
        raw_items = await queue.lrange(key, 0, max(limit - 1, -1) if limit > 0 else -1)
        if raw_items:
            return raw_items
    return []


def _coerce_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"invalid integer for {field}") from exc


def _coerce_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"invalid float for {field}") from exc


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


@router.get("/metrics/latency-usage")
async def get_latency_usage(
    queue: QueueService = Depends(get_queue_service),
    settings: Settings = Depends(get_settings_dependency),
) -> dict[str, Any]:
    metrics = await _load_hash(queue, settings, "metrics:latency")
    if not metrics:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="latency metrics not available")

    result: dict[str, Any] = {}
    for field in ("apify_ms", "helius_ms", "parser_ms", "apify_credits_used", "groq_credits_used"):
        if field in metrics:
            result[field] = _coerce_int(metrics[field], field)
    if "suggestion" in metrics:
        result["suggestion"] = metrics["suggestion"]
    return result


@router.post("/cex-radar/search")
async def post_cex_radar_search(
    payload: dict[str, Any],
    queue: QueueService = Depends(get_queue_service),
    settings: Settings = Depends(get_settings_dependency),
) -> dict[str, str]:
    query = payload.get("query") if isinstance(payload, dict) else None
    if not isinstance(query, str) or not query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query is required")

    job_id = f"cex-{uuid4().hex}"
    job_payload = {
        "jobId": job_id,
        "query": query.strip(),
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    key = await _first_existing_key(queue, settings, "cexradar:jobs")
    await queue.lpush_json(key, job_payload)
    return {"jobId": job_id}


@router.get("/cex-radar/result")
async def get_cex_radar_result(
    job_id: str = Query(..., alias="jobId"),
    queue: QueueService = Depends(get_queue_service),
    settings: Settings = Depends(get_settings_dependency),
) -> list[dict[str, Any]]:
    if not job_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="jobId is required")

    result = await _load_json_value(queue, settings, f"cexradar:result:{job_id}")
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job result not ready")
    if not isinstance(result, list):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="invalid job result payload")
    return result


@router.get("/helius/mints")
async def get_helius_mints(
    queue: QueueService = Depends(get_queue_service),
    settings: Settings = Depends(get_settings_dependency),
) -> list[dict[str, Any]]:
    entries = await _load_list(queue, settings, "helius:mints", limit=100)
    mints: list[dict[str, Any]] = []
    for raw in entries:
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict):
            continue
        mint = {
            "name": item.get("name"),
            "mint": item.get("mint"),
            "team": item.get("team"),
            "original": _as_bool(item.get("original")),
            "safe": _as_bool(item.get("safe")),
            "hasTw": _as_bool(item.get("hasTw") or item.get("has_tw")),
            "sol": _coerce_float(item.get("sol"), "sol") if item.get("sol") is not None else None,
            "ts": item.get("ts") or item.get("timestamp"),
        }
        if mint["name"] and mint["mint"]:
            if mint["sol"] is None and item.get("sol") is None:
                mint.pop("sol")
            mints.append({k: v for k, v in mint.items() if v is not None})
    return mints


@router.post("/whales/scan")
async def post_whales_scan(
    payload: Optional[dict[str, Any]] = None,
    queue: QueueService = Depends(get_queue_service),
    settings: Settings = Depends(get_settings_dependency),
) -> dict[str, str]:
    job_id = f"whale-{uuid4().hex}"
    job_payload = {
        "jobId": job_id,
        "payload": payload or {},
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    key = await _first_existing_key(queue, settings, "whales:jobs")
    await queue.lpush_json(key, job_payload)
    return {"jobId": job_id}


@router.get("/whales/top3")
async def get_whales_top3(
    job_id: str = Query(..., alias="jobId"),
    queue: QueueService = Depends(get_queue_service),
    settings: Settings = Depends(get_settings_dependency),
) -> list[dict[str, Any]]:
    if not job_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="jobId is required")
    result = await _load_json_value(queue, settings, f"whales:result:{job_id}")
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job result not ready")
    if not isinstance(result, list):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="invalid job result payload")
    return result


@router.post("/alerts/enable")
async def post_alerts_enable(
    payload: dict[str, Any],
    queue: QueueService = Depends(get_queue_service),
    settings: Settings = Depends(get_settings_dependency),
) -> dict[str, bool]:
    required_keys = {"mint", "msar", "volume", "liquidity", "enabled"}
    if not isinstance(payload, dict) or not required_keys.issubset(payload):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing fields")

    mint = payload.get("mint")
    if not isinstance(mint, str) or not mint:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mint is required")

    rule = {
        "mint": mint,
        "msar": _coerce_float(payload.get("msar"), "msar"),
        "volume": _coerce_int(payload.get("volume"), "volume"),
        "liquidity": _coerce_int(payload.get("liquidity"), "liquidity"),
        "enabled": _as_bool(payload.get("enabled")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    hash_key = await _first_existing_key(queue, settings, "alerts:rules")
    await queue.hset_json(hash_key, mint, rule)
    return {"ok": True}


@router.get("/alerts")
async def get_alerts(
    queue: QueueService = Depends(get_queue_service),
    settings: Settings = Depends(get_settings_dependency),
) -> list[dict[str, Any]]:
    rules = await _load_hash(queue, settings, "alerts:rules")
    parsed: list[dict[str, Any]] = []
    for raw in rules.values():
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        try:
            entry = {
                "mint": data.get("mint"),
                "msar": _coerce_float(data.get("msar"), "msar"),
                "volume": _coerce_int(data.get("volume"), "volume"),
                "liquidity": _coerce_int(data.get("liquidity"), "liquidity"),
                "enabled": _as_bool(data.get("enabled")),
            }
        except HTTPException:
            continue
        if entry["mint"]:
            parsed.append(entry)
    return parsed


@router.post("/ai/infer")
async def post_ai_infer(
    payload: dict[str, Any],
    gemini: GeminiService = Depends(get_gemini_service),
) -> dict[str, Any]:
    if payload.get("provider") != "gemini":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported provider")
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="prompt is required")

    strategy_id = payload.get("strategyId")
    model = payload.get("model")
    return gemini.infer(prompt.strip(), strategy_id=strategy_id, model=model)


@router.get("/ai/gemini/status")
async def get_gemini_status(
    gemini: GeminiService = Depends(get_gemini_service),
) -> dict[str, Any]:
    """Lightweight status endpoint to diagnose live Flowith connectivity.

    Returns whether the client is configured, last HTTP status, and ok flag.
    """
    return gemini.ping()
