from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db_session
from ..models import Candidate


router = APIRouter(prefix="/api", tags=["signals"])


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
        elif value is not None:
            return value
    return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        return lowered in {"1", "true", "yes", "y", "on", "og", "ok"}
    return False


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        if isinstance(value, str) and not value.strip():
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, str) and not value.strip():
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        text = text.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
    return None


def _format_detected(value: Any, fallback: datetime | None) -> str:
    detected = _parse_datetime(value) or fallback
    if detected is None:
        detected = datetime.now(timezone.utc)
    if detected.tzinfo is None:
        detected = detected.replace(tzinfo=timezone.utc)
    else:
        detected = detected.astimezone(timezone.utc)
    return detected.strftime("%Y-%m-%d %H:%M")


def _lookup(containers: list[dict[str, Any]], *keys: str) -> Any:
    for key in keys:
        for container in containers:
            if isinstance(container, dict) and key in container:
                value = container[key]
                if isinstance(value, str):
                    value = value.strip()
                    if not value:
                        continue
                if value is not None:
                    return value
    return None


def _extract_safety(containers: list[dict[str, Any]]) -> dict[str, bool]:
    safety_container = _lookup(containers, "safety")
    merged_candidates = [
        safety_container if isinstance(safety_container, dict) else {},
        *containers,
    ]
    return {
        "noMint": _as_bool(
            _lookup(merged_candidates, "noMint", "no_mint", "no_mint_flag", "no_mint_detected")
        ),
        "burnLP": _as_bool(
            _lookup(merged_candidates, "burnLP", "burn_lp", "lp_burned", "burned_lp")
        ),
        "blacklist": _as_bool(
            _lookup(merged_candidates, "blacklist", "is_blacklisted", "blacklisted")
        ),
    }


def _normalise_source(value: Any, fallback: str | None) -> str:
    source = _first_non_empty(value, fallback, "unknown")
    mapping = {
        "twitter": "Twitter",
        "telegram": "Telegram",
        "helius": "Helius",
        "discord": "Discord",
        "worker": "Worker",
        "apify": "Apify",
    }
    return mapping.get(str(source).lower(), str(source))


def _normalise_type(value: Any, word: str | None) -> str:
    if isinstance(value, str) and value.strip():
        return value
    if word and word.strip().startswith("$"):
        return "токен"
    return "слово"


@router.get("/signals")
async def list_signals(
    limit: int = Query(default=200, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    stmt = select(Candidate).order_by(Candidate.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    candidates = result.scalars().all()

    signals: list[dict[str, Any]] = []
    for candidate in candidates:
        meta = candidate.meta or {}
        metadata = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else {}
        containers = [metadata, meta]

        word = _first_non_empty(
            _lookup(containers, "word", "token", "symbol", "name"),
            candidate.symbol,
        )
        raw_type = _lookup(containers, "type", "kind", "category")
        detected_raw = _lookup(
            containers,
            "detectedAt",
            "detected_at",
            "detected",
            "ts",
            "timestamp",
            "time",
        )

        author = _lookup(containers, "author", "handle", "username")
        link = _lookup(containers, "link", "url", "tweet_url", "post_url")
        community_link = _lookup(
            containers,
            "community_link",
            "communityLink",
            "telegram",
            "discord",
            "community",
        )
        contract = _lookup(containers, "contract", "mint", "address")

        tweet_count = _coerce_int(
            _lookup(containers, "tweetCount", "tweet_count", "tweets", "tweets_1h")
        )
        community_size = _coerce_int(
            _lookup(containers, "communitySize", "community_size", "followers", "members")
        )
        name_changes = _coerce_int(
            _lookup(containers, "nameChanges", "name_changes", "rename_count")
        )
        spam_score = _coerce_float(
            _lookup(containers, "spamScore", "spam_score", "spam")
        )
        if spam_score is not None and spam_score > 1:
            spam_score = spam_score / 100 if spam_score <= 100 else 1.0

        summary = _lookup(containers, "summary", "note", "notes", "description", "analysis")
        dev_team = _lookup(containers, "devTeam", "dev_team", "team")
        chain = _first_non_empty(_lookup(containers, "chain"), "Solana")

        is_og = _as_bool(_lookup(containers, "isOG", "is_og", "og"))
        source = _normalise_source(_lookup(containers, "source", "origin"), candidate.source)
        safety = _extract_safety(containers)

        detected_at = _format_detected(detected_raw, candidate.created_at)

        signals.append(
            {
                "id": str(candidate.id),
                "word": str(word) if word is not None else candidate.symbol,
                "isOG": is_og,
                "type": _normalise_type(raw_type, word if isinstance(word, str) else None),
                "detectedAt": detected_at,
                "source": source,
                "author": author,
                "link": link,
                "tweetCount": tweet_count,
                "communitySize": community_size,
                "nameChanges": name_changes,
                "spamScore": spam_score,
                "devTeam": dev_team,
                "communityLink": community_link,
                "contract": contract,
                "chain": chain,
                "safety": safety,
                "summary": summary,
            }
        )

    return signals
