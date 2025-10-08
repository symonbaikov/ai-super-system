from datetime import datetime, timezone

from backend.api import dependencies
from backend.api.schemas.whales import WhaleScanResult, WhaleTopEntry
import uuid

import pytest

from backend.tests.conftest import _fetch_alerts, _fetch_candidates


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


@pytest.mark.asyncio
async def test_whales_scan_flow(api_client, fake_whale_service):
    client, fake_queue = api_client

    response = await client.post(
        "/api/whales/scan",
        json={"mint": "SoTestMint"},
    )
    assert response.status_code == 202
    job_id = response.json()["jobId"]
    assert fake_queue.enqueued[-1][0] == "whales:scan"
    assert fake_queue.enqueued[-1][1]["filters"]["mint"] == "SoTestMint"

    pending = await client.get(f"/api/whales/top3?jobId={job_id}")
    assert pending.status_code == 202

    sample_entry = WhaleTopEntry(
        mint="SoTestMint",
        name="$TEST",
        whales=4,
        sol_sum=42.5,
        safety={"rugcheck": "ok", "solsniffer": "warn"},
        hype={"tw_1h": 120, "tg_1h": 80},
        links={"birdeye": "https://birdeye.so/token/SoTestMint?chain=solana"},
    )
    result = WhaleScanResult(
        jobId=job_id,
        generatedAt=datetime.now(timezone.utc),
        items=[sample_entry],
    )
    await fake_whale_service.store_result(result)

    final = await client.get(f"/api/whales/top3?jobId={job_id}")
    assert final.status_code == 200
    data = final.json()
    assert len(data) == 1
    assert data[0]["mint"] == "SoTestMint"


@pytest.mark.asyncio
async def test_signals_endpoint(api_client):
    client, _ = api_client

    metadata = {
        "word": "OPTIMUS",
        "isOG": True,
        "type": "слово",
        "detectedAt": "2025-10-08 12:00",
        "source": "Twitter",
        "author": "@alpha",
        "link": "https://twitter.com/alpha/status/1",
        "tweetCount": 12,
        "communitySize": 4200,
        "nameChanges": 1,
        "spamScore": 0.05,
        "devTeam": "doxxed",
        "communityLink": "https://t.me/alpha",
        "contract": "SoTestMint",
        "chain": "Solana",
        "safety": {"noMint": True, "burnLP": False, "blacklist": False},
        "summary": "Demo candidate",
    }

    payload = {
        "symbol": "OPTIMUS",
        "sources": ["twitter"],
        "priority": 5,
        "metadata": metadata,
    }
    await client.post("/api/parser/run", json=payload)

    response = await client.get("/api/signals")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data
    item = data[0]
    assert item["word"] == "OPTIMUS"
    assert item["safety"]["noMint"] is True
    assert item["safety"]["noMint"] is True
