from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..dependencies import get_db_session, get_queue_service, get_settings_dependency
from ..models import LogEntry
from ..schemas.helius import HeliusWebhook
from ..services.queue import QueueService
from ..services.signature import verify_signature

router = APIRouter(prefix="/api/helius", tags=["helius"])


@router.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def helius_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    queue: QueueService = Depends(get_queue_service),
    settings: Settings = Depends(get_settings_dependency),
):
    raw_body = await request.body()
    try:
        payload = HeliusWebhook.model_validate_json(raw_body)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid payload") from exc

    signature = request.headers.get("x-helius-signature")
    if settings.helius_webhook_secret and not verify_signature(settings.helius_webhook_secret, raw_body, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signature")

    session.add(
        LogEntry(
            level="info",
            message="helius_webhook_received",
            source="helius",
            context={"items": len(payload.data)},
        )
    )
    await session.commit()

    for item in payload.data:
        await queue.enqueue(
            settings.helius_queue_name,
            {
                "type": item.type,
                "transactionSignature": item.transactionSignature,
                "account": item.account,
                "nativeTransfers": item.nativeTransfers,
                "tokenTransfers": item.tokenTransfers,
                "events": item.events,
                "raw": item.raw,
            },
        )

    return {"ok": True, "count": len(payload.data)}
