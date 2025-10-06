from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ApifyActorRun(BaseModel):
    id: str = Field(..., alias="id")
    status: str
    startedAt: Optional[datetime] = None
    finishedAt: Optional[datetime] = None
    succeeded: Optional[bool] = None


class ApifyCallbackPayload(BaseModel):
    actorRun: ApifyActorRun
    datasetItems: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class ApifyRunRequest(BaseModel):
    actor_id: Optional[str] = None
    input: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


class ApifyRunResponse(BaseModel):
    actor_id: str
    run_id: str
    status: str
    data: dict[str, Any] = Field(default_factory=dict)
