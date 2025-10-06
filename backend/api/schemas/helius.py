from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class HeliusWebhookItem(BaseModel):
    type: str
    transactionSignature: Optional[str] = Field(default=None)
    account: Optional[str] = Field(default=None)
    nativeTransfers: Optional[list[dict[str, Any]]] = None
    tokenTransfers: Optional[list[dict[str, Any]]] = None
    events: Optional[dict[str, Any]] = None
    raw: Optional[dict[str, Any]] = None


class HeliusWebhook(BaseModel):
    data: list[HeliusWebhookItem]
    webhook_id: Optional[str] = None
    webhook_type: Optional[str] = None
