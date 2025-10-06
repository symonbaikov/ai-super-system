from __future__ import annotations

from typing import Any, Optional

import httpx


class GroqClient:
    """Async client for Groq's OpenAI-compatible chat endpoints."""

    def __init__(self, base_url: str, api_key: Optional[str], model: str, timeout: int = 15) -> None:
        self._base_url = base_url.rstrip('/')
        self._api_key = api_key or ''
        self._default_model = model
        self._timeout = timeout

    @property
    def default_model(self) -> str:
        return self._default_model

    async def chat_completion(
        self,
        *,
        messages: list[dict[str, Any]],
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        if not self._api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")
        payload_messages: list[dict[str, Any]] = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(messages)
        payload = {
            "model": model or self._default_model,
            "messages": payload_messages,
            "metadata": metadata or {},
        }
        if temperature is not None:
            payload["temperature"] = temperature
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def summarize_signal(self, prompt: str, *, metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        data = await self.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            system="You are the Judge module for Super Parser AI.",
            metadata=metadata,
        )
        return {
            "id": data.get("id"),
            "choices": data.get("choices", []),
            "usage": data.get("usage", {}),
        }
