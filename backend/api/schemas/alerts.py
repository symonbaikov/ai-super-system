from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    title: str
    severity: str = Field(default="info")
    source: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    tenant: Optional[str] = None


class AlertAcknowledge(BaseModel):
    acked: bool = True


class AlertAckResponse(BaseModel):
    id: UUID
    acked: bool
    updated_at: Optional[datetime] = None


class AlertQuery(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    severity: Optional[str] = None
    source: Optional[str] = None
