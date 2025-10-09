from datetime import datetime, timezone

from backend.api import dependencies
from backend.api.schemas.whales import WhaleScanResult, WhaleTopEntry
import uuid
from pathlib import Path

import json

import pytest

from backend.api.services import gemini
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
async def test_signals_endpoint_maps_candidate_metadata(api_client):
    client, _ = api_client
    metadata = {
        "word": "$DOGE",
        "type": "токен",
        "detected_at": "2025-09-17T10:15:00Z",
        "source": "twitter",
        "author": "@elonmusk",
        "link": "https://x.com/elon/status/1",
        "tweet_count": 420,
        "community_size": 125000,
        "name_changes": 2,
        "spam_score": 12,
        "dev_team": "unknown",
        "community_link": "https://t.me/example",
        "contract": "So1xxxx...abcd",
        "chain": "Solana",
        "safety": {"no_mint": True, "burn_lp": False, "blacklist": True},
        "summary": "Высокий хайп, но есть риски с листингом.",
        "is_og": True,
    }
    response = await client.post(
        "/api/parser/run",
        json={
            "symbol": "DOGE",
            "sources": ["twitter"],
            "priority": 4,
            "metadata": metadata,
        },
    )
    assert response.status_code == 202

    listing = await client.get("/api/signals")
    assert listing.status_code == 200
    signals = listing.json()
    assert len(signals) == 1
    signal = signals[0]

    assert signal["word"] == "$DOGE"
    assert signal["type"] == "токен"
    assert signal["source"] == "Twitter"
    assert signal["author"] == "@elonmusk"
    assert signal["link"] == "https://x.com/elon/status/1"
    assert signal["tweetCount"] == 420
    assert signal["communitySize"] == 125000
    assert signal["nameChanges"] == 2
    assert signal["spamScore"] == 0.12
    assert signal["devTeam"] == "unknown"
    assert signal["communityLink"] == "https://t.me/example"
    assert signal["contract"] == "So1xxxx...abcd"
    assert signal["chain"] == "Solana"
    assert signal["isOG"] is True
    assert signal["safety"]["noMint"] is True
    assert signal["safety"]["burnLP"] is False
    assert signal["safety"]["blacklist"] is True
    assert signal["summary"] == metadata["summary"]
    assert signal["detectedAt"] == "2025-09-17 10:15"


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
async def test_gemini_infer_returns_ranked_accounts(api_client):
    client, _ = api_client
    response = await client.post(
        "/api/ai/infer",
        json={
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "prompt": "Highlight Solana ecosystem founders and key influencers",
            "strategyId": "S1",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tokens"]["input"] >= 5
    assert data["tokens"]["output"] >= 5
    assert data["cost_usd"] > 0
    assert any("@aeyakovenko" == entry["handle"] for entry in data["accounts"])
    assert "Gemini scanned" in data["text"]
    assert "Strategy context" in data["text"]
    assert data["provider"] == "flowith-local"
    assert data["analysis"]["coverage"]["total_accounts"] >= len(data["accounts"])


def test_gemini_service_prefers_precomputed_cache(tmp_path):
    repo_root = tmp_path
    derived_dir = repo_root / "backend" / "configs" / "derived"
    derived_dir.mkdir(parents=True)
    cache_path = derived_dir / "gemini_accounts_cache.json"
    cache_payload = [
        {
            "handle": "@cache_account",
            "description": "Cached influencer",
            "keywords": ["cache", "gemini"],
            "clusters": ["Test"],
            "mints": ["CACHE"],
            "weight": 2.5,
        }
    ]
    cache_path.write_text(json.dumps(cache_payload), encoding="utf-8")

    service = gemini.GeminiService(repo_root)
    try:
        accounts = service.accounts
    finally:
        service.close()

    assert len(accounts) == 1
    assert accounts[0].handle == "@cache_account"
    assert accounts[0].keywords == ("cache", "gemini")
    assert accounts[0].clusters == ("Test",)
    assert accounts[0].mints == ("CACHE",)
    assert accounts[0].weight == 2.5


@pytest.mark.asyncio
async def test_gemini_infer_requires_prompt(api_client):
    client, _ = api_client
    response = await client.post(
        "/api/ai/infer",
        json={"provider": "gemini", "model": "gemini-2.5-flash"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "prompt is required"


@pytest.mark.asyncio
async def test_gemini_infer_uses_flowith_when_available(monkeypatch, api_client):
    client, _ = api_client

    class DummyResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    class DummyClient:
        def __init__(self, payload):
            self.payload = payload
            self.calls: list[dict[str, object]] = []

        def post(self, url, json=None, headers=None):
            self.calls.append({"url": url, "json": json, "headers": headers})
            return DummyResponse(self.payload)

    fake_payload = {
        "text": "Flowith summary",
        "tokens": {"input": 64, "output": 32},
        "cost": {"usd": 0.045},
        "accounts": [
            {"handle": "@flowith", "description": "Flowith AI", "score": 9.9, "keywords": ["flowith"]},
        ],
        "analysis": {"sentiment": {"score": 0.88, "label": "bullish"}},
    }
    fake_client = DummyClient(fake_payload)

    from backend.api.services.gemini import GeminiService

    service = GeminiService(
        Path("."),
        api_url="https://api.flowith.io/v1/gemini",
        api_key="test-token",
        http_client=fake_client,  # type: ignore[arg-type]
    )
    monkeypatch.setattr(dependencies, "_gemini_service", service, raising=False)

    try:
        response = await client.post(
            "/api/ai/infer",
            json={
                "provider": "gemini",
                "prompt": "Give me Flowith insights",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "flowith"
        assert data["text"] == "Flowith summary"
        assert data["tokens"] == {"input": 64, "output": 32}
        assert data["cost_usd"] == 0.045
        assert data["analysis"]["sentiment"]["label"] == "bullish"
        assert data["accounts"][0]["handle"] == "@flowith"
        assert fake_client.calls[0]["headers"]["Authorization"] == "Bearer test-token"
    finally:
        service.close()

