from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..dependencies import get_ai_pipeline
from ..services.ai_pipeline import AIPipelineService

router = APIRouter(prefix="/api/advice", tags=["advice"])


class AdviceRequest(BaseModel):
    prompt: str = Field(..., description="Natural language request for the AI core")
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("", status_code=status.HTTP_200_OK)
async def fetch_advice(payload: AdviceRequest, pipeline: AIPipelineService = Depends(get_ai_pipeline)) -> Dict[str, Any]:
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="prompt is required")
    result = await pipeline.advise(prompt, payload.metadata)
    return result
