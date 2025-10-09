from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WhaleScanRequest(BaseModel):
    mint: Optional[str] = Field(default=None, description="Mint or contract to prioritise")
    min_sol: float = Field(default=5.0, ge=0, description="Minimum SOL amount to consider a whale event")
    window_sec: int = Field(default=60, ge=1, le=3600, description="Aggregation window in seconds")
    aggressive: bool = Field(
        default=False, description="Aggressive mode lowers required whale count threshold"
    )
    tags: list[str] = Field(default_factory=list, description="Additional narrative tags or filters")


class WhaleScanResponse(BaseModel):
    jobId: str


class WhaleSafety(BaseModel):
    rugcheck: str
    solsniffer: str


class WhaleHype(BaseModel):
    tw_1h: int
    tg_1h: int


class WhaleLinks(BaseModel):
    birdeye: str


class WhaleTopEntry(BaseModel):
    mint: str
    name: str
    whales: int
    sol_sum: float = Field(..., alias="sol_sum")
    safety: WhaleSafety
    hype: WhaleHype
    links: WhaleLinks

    class Config:
        populate_by_name = True


class WhaleScanResult(BaseModel):
    jobId: str
    generated_at: datetime = Field(..., alias="generatedAt")
    items: list[WhaleTopEntry]

    class Config:
        populate_by_name = True
