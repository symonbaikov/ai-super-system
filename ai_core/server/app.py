from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from .pipeline import TripleAIPipeline


class RouteRequest(BaseModel):
    prompt: str = Field(..., description="Raw user input or narrative to evaluate")
    metadata: Dict[str, Any] = Field(default_factory=dict)


@lru_cache(maxsize=1)
def _get_pipeline() -> TripleAIPipeline:
    config_dir = Path(os.getenv("AI_CORE_CONFIG_DIR", "ai_core/configs")).expanduser()
    if not config_dir.is_absolute():
        # Resolve relative to repository root when packaged inside the container.
        config_dir = (Path(__file__).resolve().parents[2] / config_dir).resolve()
    return TripleAIPipeline.from_path(config_dir)


app = FastAPI(title="Triple-AI Route Service", version="0.1.0")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    pipeline = _get_pipeline()
    result = await pipeline.run("ping")
    return {
        "status": "ok",
        "chain": " > ".join(result.chain),
    }


@app.post("/route", tags=["route"])
@app.post("/advice", tags=["route"])
async def route(request: RouteRequest) -> dict[str, Any]:
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="prompt is required")

    result = await _get_pipeline().run(prompt, request.metadata)
    return {
        "chain": result.chain,
        "scout": {
            "summary": result.scout.summary,
            "confidence": result.scout.confidence,
            "findings": result.scout.findings,
        },
        "analyst": {
            "summary": result.analyst.summary,
            "confidence": result.analyst.confidence,
            "findings": result.analyst.findings,
        },
        "judge": {
            "summary": result.judge.summary,
            "confidence": result.judge.confidence,
            "findings": result.judge.findings,
        },
        "decision": result.decision,
        "metadata": result.metadata,
    }
