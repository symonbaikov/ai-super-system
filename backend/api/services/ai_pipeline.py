from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from ai_core.server.pipeline import TripleAIPipeline


class AIPipelineService:
    """Wraps the Triple-AI pipeline (local or Groq-backed) for FastAPI handlers."""

    def __init__(self, config_dir: Path, groq_client=None) -> None:
        self._pipeline = TripleAIPipeline.from_path(config_dir, groq_client=groq_client)

    async def advise(self, prompt: str, metadata: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
        result = await self._pipeline.run(prompt, metadata)
        return {
            "chain": result.chain,
            "scout": self._module_to_dict(result.scout),
            "analyst": self._module_to_dict(result.analyst),
            "judge": self._module_to_dict(result.judge),
            "decision": result.decision,
            "metadata": result.metadata,
        }

    @staticmethod
    def _module_to_dict(module) -> dict[str, Any]:
        return {
            "name": module.name,
            "route": module.route,
            "summary": module.summary,
            "confidence": module.confidence,
            "findings": module.findings,
        }
