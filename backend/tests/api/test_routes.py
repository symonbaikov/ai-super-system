from backend.api import dependencies
import uuid

import pytest

from backend.tests.conftest import FakeQueue, _fetch_alerts, _fetch_candidates


@pytest.mark.asyncio
async def test_parser_run_creates_candidate(api_client):
    client, fake_queue = api_client
    response = await client.post(
        "/api/parser/run",
        json={"symbol": "DEGEN", "sources": ["twitter"], "priority": 7},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["symbol"] == "DEGEN"
    assert data["priority"] == 7

    candidates = await _fetch_candidates()
    assert len(candidates) == 1
    assert fake_queue.enqueued[0][0] == "parser:run"


@pytest.mark.asyncio
async def test_alerts_flow(api_client):
    client, fake_queue = api_client
    response = await client.post(
        "/api/alerts",
        json={
            "title": "Whale alarm",
            "severity": "warn",
            "source": "worker",
            "message": "Whale spotted",
            "payload": {"mint": "So111"},
        },
    )
    assert response.status_code == 201
    alert_id = response.json()["id"]

    listing = await client.get("/api/alerts")
    assert listing.status_code == 200
    alerts = listing.json()
    assert any(item["id"] == alert_id for item in alerts)

    ack = await client.post(f"/api/alerts/{alert_id}/ack")
    assert ack.status_code == 200
    assert ack.json()["acked"] is True

    alerts_db = await _fetch_alerts()
    assert len(alerts_db) == 1
    assert fake_queue.published[0]["alert_id"] == alert_id


@pytest.mark.asyncio
async def test_advice_proxy(monkeypatch, api_client):
    client, _ = api_client

    class FakePipeline:
        async def advise(self, prompt, metadata=None):
            return {
                "chain": ["scout", "analyst", "judge"],
                "scout": {"name": "scout", "route": "scout", "summary": prompt, "confidence": 0.5, "findings": {}},
                "analyst": {"name": "analyst", "route": "analyst", "summary": prompt, "confidence": 0.5, "findings": {}},
                "judge": {"name": "judge", "route": "judge", "summary": prompt, "confidence": 0.5, "findings": {}},
                "decision": {"verdict": "WATCH", "score": 0.4, "risk_level": "medium", "confidence": 0.6, "critical_hits": [], "warnings": [], "fallback_used": False},
                "metadata": {"profile": metadata.get('profile') if metadata else None},
            }

    original = getattr(__import__('backend.api.dependencies', fromlist=['_ai_pipeline']), '_ai_pipeline', None)
    from backend.api import dependencies

    dependencies._ai_pipeline = FakePipeline()
    try:
        response = await client.post('/api/advice', json={"prompt": "test prompt", "metadata": {"profile": 'twitter'}})
        assert response.status_code == 200
        data = response.json()
        assert data['decision']['verdict'] == 'WATCH'
        assert data['chain'] == ['scout', 'analyst', 'judge']
    finally:
        if original is not None:
            dependencies._ai_pipeline = original


@pytest.mark.asyncio
async def test_trade_confirm_updates_candidate(api_client):
    client, _ = api_client
    await client.post(
        "/api/parser/run",
        json={"symbol": "BOME", "sources": ["telegram"], "priority": 3},
    )
    candidates = await _fetch_candidates()
    candidate_id = str(candidates[0].id)

    trade_payload = {
        "trade_id": str(uuid.uuid4()),
        "candidate_id": candidate_id,
        "status": "filled",
        "tx_hash": "tx123",
        "metadata": {"exchange": "jupiter"},
    }
    trade_response = await client.post("/api/trade/confirm", json=trade_payload)
    assert trade_response.status_code == 200
    trade_json = trade_response.json()
    assert trade_json["candidate_id"] == candidate_id
    assert trade_json["status"] == "filled"

    candidates = await _fetch_candidates()
    assert candidates[0].meta["trades"]


@pytest.mark.asyncio
async def test_apify_run_triggers_actor(api_client):
    client, _ = api_client

    class FakeApify:
        def __init__(self):
            self.calls = []

        async def trigger_actor(self, actor_id, *, input_payload):
            self.calls.append((actor_id, input_payload))
            return {"data": {"id": "run-123", "status": "RUNNING"}}

    original = getattr(dependencies, '_apify_client', None)
    fake = FakeApify()
    dependencies._apify_client = fake
    try:
        response = await client.post('/api/apify/run', json={"actor_id": "team~actor", "input": {"foo": "bar"}})
        assert response.status_code == 202
        data = response.json()
        assert data['run_id'] == 'run-123'
        assert fake.calls[0][0] == 'team~actor'
        assert fake.calls[0][1]['input']['foo'] == 'bar'
    finally:
        if original is not None:
            dependencies._apify_client = original

