from __future__ import annotations

from typing import Optional

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..dependencies import get_apify_client, get_db_session, get_queue_service, get_settings_dependency
from ..models import Candidate, LogEntry
from ..schemas.apify import ApifyCallbackPayload, ApifyRunRequest, ApifyRunResponse
from ..services.apify import ApifyClient
from ..services.queue import QueueService
from ..services.signature import verify_signature



def _extract_symbol(payload: ApifyCallbackPayload) -> Optional[str]:
    meta_symbol = (payload.meta or {}).get('symbol')
    if isinstance(meta_symbol, str) and meta_symbol.strip():
        return meta_symbol.strip()
    items = payload.datasetItems or []
    for item in items:
        if isinstance(item, dict):
            for key in ('symbol', 'ticker', 'token', 'mint'):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return None
router = APIRouter(prefix="/api/apify", tags=["apify"])


@router.post("/run", response_model=ApifyRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def apify_run(
    payload: ApifyRunRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dependency),
    client: ApifyClient = Depends(get_apify_client),
) -> ApifyRunResponse:
    actor_id = payload.actor_id or settings.apify_actor_id
    if not actor_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="actor_id is required")

    try:
        run = await client.trigger_actor(actor_id, input_payload={"input": payload.input, "meta": payload.meta})
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    run_data = run.get("data") if isinstance(run, dict) else None
    if run_data is None and isinstance(run, dict):
        run_data = run
    run_id = (run_data or {}).get("id") or (run_data or {}).get("runId")
    status_label = (run_data or {}).get("status", "RUNNING")
    if not run_id:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="unexpected Apify response")

    session.add(
        LogEntry(
            level="info",
            message="apify_run_started",
            source="apify",
            context={"actor_id": actor_id, "run_id": run_id, "status": status_label},
        )
    )
    await session.commit()

    return ApifyRunResponse(actor_id=actor_id, run_id=run_id, status=status_label, data=run_data or {})


@router.post("/callback", status_code=status.HTTP_200_OK)
async def apify_callback(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    queue: QueueService = Depends(get_queue_service),
    settings: Settings = Depends(get_settings_dependency),
):
    raw_body = await request.body()
    try:
        payload = ApifyCallbackPayload.model_validate_json(raw_body)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid payload") from exc

    signature = request.headers.get("x-apify-signature")
    if settings.alerts_signature_secret and not verify_signature(settings.alerts_signature_secret, raw_body, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signature")

    candidate_id = payload.meta.get("candidate_id") if payload.meta else None
    candidate: Optional[Candidate] = None
    if candidate_id:
        try:
            candidate_uuid = uuid.UUID(candidate_id)
        except ValueError:
            candidate_uuid = None
        if candidate_uuid:
            candidate = await session.get(Candidate, candidate_uuid)

    created = False
    if candidate is None:
        symbol = _extract_symbol(payload)
        if not symbol:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="symbol is required in Apify payload")
        meta = payload.meta or {}
        score_val = meta.get("score")
        try:
            score = int(score_val) if score_val is not None else 0
        except (TypeError, ValueError):
            score = 0
        candidate = Candidate(
            symbol=symbol.upper(),
            source=meta.get("source", "apify"),
            status="apify_received",
            score=score,
            meta={
                "priority": meta.get("priority", 5),
                "sources": meta.get("sources", ["apify"]),
                "filters": meta.get("filters", []),
                "requested_by": meta.get("requested_by", "apify"),
                "metadata": meta,
            },
        )
        session.add(candidate)
        await session.flush()
        candidate_id = str(candidate.id)
        created = True
    else:
        candidate_id = str(candidate.id)

    candidate.meta.setdefault("apify", {})
    candidate.meta["apify"].update(
        {
            "run": payload.actorRun.model_dump(mode="json"),
            "dataset_items": payload.datasetItems,
        }
    )
    candidate.status = "apify_completed" if payload.actorRun.succeeded else "apify_failed"

    session.add(
        LogEntry(
            level="info",
            message="apify_callback_received",
            source="apify",
            context={
                "candidate_id": candidate_id,
                "run_id": payload.actorRun.id,
                "status": payload.actorRun.status,
                "created": created,
            },
        )
    )

    await session.commit()

    await queue.enqueue(
        settings.apify_queue_name,
        {
            "run_id": payload.actorRun.id,
            "status": payload.actorRun.status,
            "candidate_id": candidate_id,
            "dataset_items": payload.datasetItems,
        },
    )

    return {"ok": True, "processed": True, "candidate_id": candidate_id}
