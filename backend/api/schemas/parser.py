from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ParserRunRequest(BaseModel):
    symbol: str = Field(..., description="Token symbol or identifier")
    sources: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    priority: int = Field(default=5, ge=1, le=10)
    metadata: dict[str, Any] = Field(default_factory=dict)
    trigger: Optional[str] = Field(default=None, description="Which system initiated the run")


class ParserRunResponse(BaseModel):
    job_id: UUID
    status: str = "queued"
    symbol: str
    sources: list[str]
    priority: int
