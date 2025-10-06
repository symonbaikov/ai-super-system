from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TradeConfirmRequest(BaseModel):
    trade_id: str
    candidate_id: str
    status: str = Field(default="confirmed")
    tx_hash: Optional[str] = None
    executed_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TradeConfirmResponse(BaseModel):
    trade_id: str
    candidate_id: str
    status: str
    tx_hash: Optional[str] = None
    executed_at: Optional[datetime] = None
