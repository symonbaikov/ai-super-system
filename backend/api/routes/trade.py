from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db_session
from ..models import Candidate, LogEntry
from ..schemas.trade import TradeConfirmRequest, TradeConfirmResponse

router = APIRouter(prefix="/api/trade", tags=["trade"])


@router.post("/confirm", response_model=TradeConfirmResponse, status_code=status.HTTP_200_OK)
async def confirm_trade(
    payload: TradeConfirmRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TradeConfirmResponse:
    try:
        candidate_uuid = uuid.UUID(payload.candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid candidate_id") from exc

    candidate = await session.get(Candidate, candidate_uuid)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="candidate not found")

    candidate.status = payload.status
    candidate.meta.setdefault("trades", [])
    candidate.meta["trades"].append(
        {
            "trade_id": payload.trade_id,
            "status": payload.status,
            "tx_hash": payload.tx_hash,
            "executed_at": payload.executed_at.isoformat() if payload.executed_at else None,
            "metadata": payload.metadata,
        }
    )

    session.add(
        LogEntry(
            level="info",
            message="trade_confirmed",
            source="trade",
            context={
                "candidate_id": payload.candidate_id,
                "trade_id": payload.trade_id,
                "status": payload.status,
            },
        )
    )
    await session.commit()

    return TradeConfirmResponse(
        trade_id=payload.trade_id,
        candidate_id=payload.candidate_id,
        status=payload.status,
        tx_hash=payload.tx_hash,
        executed_at=payload.executed_at,
    )
