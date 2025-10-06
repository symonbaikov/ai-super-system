from __future__ import annotations

from typing import Any, Optional

import httpx


class ApifyClient:
    """Simple wrapper around Apify Actors API."""

    def __init__(self, base_url: str, token: Optional[str], timeout: int = 15) -> None:
        self._base_url = base_url.rstrip('/')
        self._token = token or ''
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    async def trigger_actor(
        self,
        actor_id: str,
        *,
        input_payload: dict[str, Any],
        webhook_url: Optional[str] = None,
        event_types: Optional[list[str]] = None,
        wait: int = 0,
    ) -> dict[str, Any]:
        if not self._token:
            raise RuntimeError("APIFY_TOKEN is not configured")
        params = {"wait": wait}
        if webhook_url:
            params["webhookUrl"] = webhook_url
            if event_types:
                params["webhookEventTypes"] = ",".join(event_types)
        url = f"{self._base_url}/v2/acts/{actor_id}/runs"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, headers=self._headers(), params=params, json=input_payload)
            response.raise_for_status()
            return response.json()
