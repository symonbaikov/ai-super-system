from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..dependencies import get_db_session, get_queue_service, get_settings_dependency
from ..models import Candidate, LogEntry
from ..schemas.parser import ParserRunRequest, ParserRunResponse
from ..services.queue import QueueService

router = APIRouter(prefix="/api/parser", tags=["parser"])


@router.post("/run", response_model=ParserRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def parser_run(
    payload: ParserRunRequest,
    session: AsyncSession = Depends(get_db_session),
    queue: QueueService = Depends(get_queue_service),
    settings: Settings = Depends(get_settings_dependency),
) -> ParserRunResponse:
    symbol = payload.symbol.upper()
    sources = payload.sources or settings.parser_default_sources
    filters = payload.filters or settings.parser_default_filters

    candidate = Candidate(
        symbol=symbol,
        source=payload.trigger or "api",
        status="queued",
        score=(payload.metadata or {}).get("score", 0),
        meta={
            "priority": payload.priority,
            "sources": sources,
            "filters": filters,
            "requested_by": payload.trigger or "api",
            "metadata": payload.metadata,
        },
    )
    session.add(candidate)
    await session.flush()

    job_payload = {
        "candidate_id": str(candidate.id),
        "symbol": candidate.symbol,
        "sources": sources,
        "filters": filters,
        "priority": payload.priority,
        "metadata": payload.metadata,
    }

    job_id = await queue.enqueue(settings.parser_queue_name, job_payload)
    candidate.meta["queue_job_id"] = str(job_id)

    log = LogEntry(
        level="info",
        message="parser_run_enqueued",
        source="api",
        context={"candidate_id": str(candidate.id), "job_id": str(job_id)},
    )
    session.add(log)
    await session.commit()

    return ParserRunResponse(
        job_id=job_id,
        status=candidate.status,
        symbol=candidate.symbol,
        sources=sources,
        priority=payload.priority,
    )
