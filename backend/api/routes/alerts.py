from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db_session, get_queue_service
from ..models import Alert
from ..schemas.alerts import AlertCreate, AlertQuery
from ..schemas.common import AlertOut
from ..services.queue import QueueService

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
async def create_alert(
    payload: AlertCreate,
    session: AsyncSession = Depends(get_db_session),
    queue: QueueService = Depends(get_queue_service),
) -> AlertOut:
    alert = Alert(
        title=payload.title,
        severity=payload.severity,
        source=payload.source,
        message=payload.message,
        payload=payload.payload,
    )
    session.add(alert)
    await session.commit()
    await session.refresh(alert)

    await queue.publish_alert(
        {
            "alert_id": str(alert.id),
            "title": alert.title,
            "severity": alert.severity,
            "source": alert.source,
            "payload": payload.payload,
            "tenant": payload.tenant,
        }
    )

    return AlertOut.model_validate(alert)


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    query: AlertQuery = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> list[AlertOut]:
    stmt = select(Alert).order_by(Alert.created_at.desc()).limit(query.limit)
    if query.severity:
        stmt = stmt.where(Alert.severity == query.severity)
    if query.source:
        stmt = stmt.where(Alert.source == query.source)
    result = await session.execute(stmt)
    alerts = result.scalars().all()
    return [AlertOut.model_validate(alert) for alert in alerts]


@router.post("/{alert_id}/ack", response_model=AlertOut)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AlertOut:
    alert = await session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="alert not found")
    alert.acked = True
    await session.commit()
    await session.refresh(alert)
    return AlertOut.model_validate(alert)
