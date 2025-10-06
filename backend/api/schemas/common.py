from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CandidateOut(BaseModel):
    id: UUID
    symbol: str
    source: str
    status: str
    score: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertOut(BaseModel):
    id: UUID
    title: str
    severity: str
    source: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    acked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LogOut(BaseModel):
    id: UUID
    level: str
    message: str
    source: str
    context: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class SettingOut(BaseModel):
    key: str
    value: dict[str, Any]
    updated_at: datetime

    model_config = {"from_attributes": True}
