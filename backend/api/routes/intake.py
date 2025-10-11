from __future__ import annotations

import hashlib
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..dependencies import get_db_session, get_queue_service, get_settings_dependency
from ..models import Candidate, LogEntry
from ..services.queue import QueueService

router = APIRouter(prefix="/api/intake", tags=["intake"])


TOKEN_PATTERN = re.compile(r"\$([A-Z0-9]{2,12})")
MINT_PATTERN = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")


def _namespaced_key(settings: Settings, base: str) -> str:
    namespace = (settings.queue_namespace or "").strip()
    if namespace:
        return f"{namespace}:{base}"
    return base


def _extract_symbol(event: dict[str, Any]) -> str | None:
    for key in ("symbol", "token", "ticker", "word", "contract", "mint"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            cleaned = value.strip().upper().lstrip("$")
            if cleaned:
                return cleaned
    text = event.get("text")
    if isinstance(text, str):
        match = TOKEN_PATTERN.search(text.upper())
        if match:
            return match.group(1)
    return None


def _extract_contract(event: dict[str, Any]) -> str | None:
    for key in ("contract", "mint", "address"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    text = event.get("text")
    if isinstance(text, str):
        match = MINT_PATTERN.search(text)
        if match:
            return match.group(0)
    return None


def _build_dedupe_key(event: dict[str, Any], symbol: str) -> str:
    parts = [
        str(event.get("id") or event.get("source_id") or event.get("event_id") or ""),
        str(event.get("source") or ""),
        str(event.get("ts") or event.get("timestamp") or ""),
        symbol.upper(),
        event.get("text") or "",
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()


async def _upsert_candidate(
    session: AsyncSession,
    event: dict[str, Any],
    symbol: str,
    dedupe_key: str,
) -> Candidate:
    stmt = select(Candidate).where(Candidate.meta["dedupe_key"].as_string() == dedupe_key)
    result = await session.execute(stmt)
    candidate = result.scalars().first()

    source = (event.get("source") or "social").lower()
    score = event.get("score")
    if score is None and isinstance(event.get("metrics"), dict):
        score = event["metrics"].get("score")
    try:
        score_value = int(score) if score is not None else 0
    except (TypeError, ValueError):
        score_value = 0

    if candidate is None:
        candidate = Candidate(
            symbol=symbol,
            source=source,
            status="social_received",
            score=score_value,
            meta={
                "sources": [source],
                "filters": event.get("filters") or [],
                "requested_by": event.get("requested_by", source),
                "metadata": event,
                "dedupe_key": dedupe_key,
            },
        )
        session.add(candidate)
        await session.flush()
    else:
        candidate.symbol = symbol
        candidate.source = source
        candidate.status = "social_received"
        candidate.score = score_value
        meta = candidate.meta or {}
        existing_sources = set(meta.get("sources") or [])
        existing_sources.add(source)
        meta["sources"] = sorted(existing_sources)
        meta.setdefault("filters", event.get("filters") or [])
        meta["requested_by"] = event.get("requested_by", meta.get("requested_by", source))
        meta["metadata"] = event
        meta["dedupe_key"] = dedupe_key
        candidate.meta = meta

    contract = _extract_contract(event)
    if contract:
        metadata = candidate.meta.get("metadata") if isinstance(candidate.meta.get("metadata"), dict) else {}
        metadata["contract"] = contract
        candidate.meta["metadata"] = metadata

    return candidate


async def _ensure_social_enabled(settings: Settings) -> None:
    if not settings.enable_social_intake:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="social intake disabled")


@router.post("/social", status_code=status.HTTP_202_ACCEPTED)
async def intake_social(
    events: list[dict[str, Any]],
    session: AsyncSession = Depends(get_db_session),
    queue: QueueService = Depends(get_queue_service),
    settings: Settings = Depends(get_settings_dependency),
) -> dict[str, Any]:
    await _ensure_social_enabled(settings)
    if not isinstance(events, list) or not all(isinstance(item, dict) for item in events):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="events must be a list of objects")

    processed = 0
    created = 0
    candidate_ids: list[str] = []
    candidates_map: dict[str, Candidate] = {}

    for event in events:
        symbol = _extract_symbol(event)
        if not symbol:
            continue

        dedupe_key = _build_dedupe_key(event, symbol)
        candidate = await _upsert_candidate(session, event, symbol, dedupe_key)
        candidate_ids.append(str(candidate.id))
        candidates_map[str(candidate.id)] = candidate
        processed += 1
        if event.get("created") or event.get("is_new") or not candidate.meta.get("seen"):
            created += 1
        candidate.meta["seen"] = True
        session.add(
            LogEntry(
                level="info",
                message="intake_social_event",
                source="intake",
                context={
                    "candidate_id": str(candidate.id),
                    "dedupe_key": dedupe_key,
                    "source": event.get("source"),
                },
            )
        )

    job_id: str | None = None
    if candidate_ids:
        job_payload = {
            "candidate_ids": candidate_ids,
            "events": events,
            "source": "social",
            "metadata": {
                "processed": processed,
                "created": created,
            },
        }
        job_uuid = await queue.enqueue(
            settings.social_queue_name,
            job_payload,
        )
        job_id = str(job_uuid)
        for candidate in candidates_map.values():
            queue_meta = candidate.meta.get("queue_jobs") or {}
            queue_meta["social_intake"] = job_id
            candidate.meta["queue_jobs"] = queue_meta

    if processed:
        metrics_key = _namespaced_key(settings, "metrics:latency")
        await queue.hincrby(metrics_key, "parser_ms", processed)

    await session.commit()

    response: dict[str, Any] = {
        "ok": True,
        "accepted": len(events),
        "processed": processed,
        "created": created,
        "candidate_ids": candidate_ids,
    }
    if job_id is not None:
        response["job_id"] = job_id
    return response


@router.post("/onchain", status_code=status.HTTP_202_ACCEPTED)
async def intake_onchain(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_db_session),
    queue: QueueService = Depends(get_queue_service),
    settings: Settings = Depends(get_settings_dependency),
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payload must be an object")

    key = _namespaced_key(settings, "helius:mints")
    await queue.lpush_json(key, payload)
    await queue.ltrim(key, 0, 200)

    session.add(
        LogEntry(
            level="info",
            message="intake_onchain_event",
            source="intake",
            context={"keys": list(payload.keys())[:5]},
        )
    )
    await session.commit()
    return {"ok": True}
