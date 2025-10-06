from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend.tests.conftest import FakeQueue, _fetch_alerts, _fetch_candidates


@pytest.mark.asyncio
async def test_full_signal_to_trade_flow(api_client):
    client, fake_queue = api_client

    # 1. Seed candidate via parser run (social signals ingestion analogue)
    parser_payload = {"symbol": "WIF", "sources": ["twitter", "discord"], "priority": 9}
    parser_response = await client.post("/api/parser/run", json=parser_payload)
    assert parser_response.status_code == 202
    candidates = await _fetch_candidates()
    candidate_id = str(candidates[0].id)

    assert fake_queue.enqueued[0][0] == "parser:run"

    # 2. Request AI advice for the candidate
    advice_request = {
        "prompt": f"Evaluate candidate {candidate_id} with social momentum and whales",
        "metadata": {
            "profile": "pump",
            "metrics": {
                "SOCIAL_BURST": 6,
                "FREQ_5M": 7,
                "MENTIONS": 220,
                "LIQ_USD": 80000,
            },
        },
    }
    advice_response = await client.post("/api/advice", json=advice_request)
    assert advice_response.status_code == 200
    advice_json = advice_response.json()
    assert advice_json["decision"]["verdict"] in {"BUY", "WATCH", "NO"}

    # 3. Simulate worker alert emitted back into API
    alert_payload = {
        "title": "Triple AI BUY",
        "severity": "info",
        "source": "ai-core",
        "message": "AI recommends BUY",
        "payload": {"candidate_id": candidate_id, "decision": advice_json["decision"]},
    }
    alert_response = await client.post("/api/alerts", json=alert_payload)
    assert alert_response.status_code == 201
    alert_id = alert_response.json()["id"]
    assert fake_queue.published[0]["alert_id"] == alert_id

    # 4. Confirm a trade for the candidate (downstream execution)
    trade_payload = {
        "trade_id": str(uuid.uuid4()),
        "candidate_id": candidate_id,
        "status": "filled",
        "tx_hash": "0xabc123",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {"exchange": "jupiter", "size_sol": 10},
    }
    trade_response = await client.post("/api/trade/confirm", json=trade_payload)
    assert trade_response.status_code == 200

    # 5. Verify persisted state (alerts + candidate trade log)
    candidates = await _fetch_candidates()
    assert candidates and candidates[0].meta.get("trades")

    alerts = await _fetch_alerts()
    assert any(a.id == uuid.UUID(alert_id) for a in alerts)
