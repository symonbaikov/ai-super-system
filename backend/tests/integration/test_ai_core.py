from __future__ import annotations

from pathlib import Path

import pytest

from ai_core.server.pipeline import TripleAIPipeline

CONFIG_DIR = Path(__file__).resolve().parents[3] / "ai_core" / "configs"


@pytest.fixture(scope="module")
def pipeline() -> TripleAIPipeline:
    return TripleAIPipeline.from_path(CONFIG_DIR)


def _base_metrics():
    return {
        "SOCIAL_BURST": 5,
        "FREQ_5M": 6,
        "MENTIONS": 180,
        "LIQ_USD": 50000,
        "LP_LOCK_PCT": 85,
        "MCAP_USD": 15000,
        "VOL_5M_USD": 6000,
        "HOLDERS": 420,
        "TOP_HOLDER_PCT": 12,
        "UNIQUENESS_SCORE": 0.7,
    }


@pytest.mark.asyncio
async def test_pipeline_returns_buy_when_metrics_are_strong(pipeline: TripleAIPipeline) -> None:
    metadata = {
        "profile": "pump",
        "metrics": _base_metrics(),
        "scores": {
            "rugcheck_min_score": 80,
            "solsniffer_min_score": 8,
        },
        "risk_flags": {
            "mint_authority_active": False,
            "freeze_authority_active": False,
        },
    }

    result = await pipeline.run("Check the new SOL meme", metadata)

    assert result.decision["verdict"] == "BUY"
    assert result.decision["risk_level"] in {"low", "medium"}
    assert result.chain == ["scout", "analyst", "judge"]
    assert result.analyst.findings["failed"] == []


@pytest.mark.asyncio
async def test_pipeline_fail_closed_on_critical_flag(pipeline: TripleAIPipeline) -> None:
    metadata = {
        "metrics": _base_metrics(),
        "scores": {
            "rugcheck_min_score": 10,
        },
        "risk_flags": {
            "mint_authority_active": True,
        },
    }

    result = await pipeline.run("Token with mint authority still active", metadata)

    assert result.decision["verdict"] == "NO"
    assert "mint_authority_active" in result.decision["critical_hits"]
    assert result.judge.findings["critical_hits"]
