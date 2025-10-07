# Super Parser AI — Runbook

This repository bundles the full Super Parser AI stack: FastAPI gateway, BullMQ worker, Triple-AI Core service, React control center, Redis, Postgres, and a Caddy proxy. The guide below explains how to configure, run, and test every component end to end.

## Demo

https://github.com/user-attachments/assets/2fe563ee-ffad-41be-a886-42bf1315f52f


## 1. Prerequisites

- Docker Engine 24+ and Docker Compose v2
- Node.js 20+ with npm (for local testing)
- Python 3.11+ (matching the container runtime)
- Optional tooling: `curl`, `jq`, `openssl` for webhook signing/debugging

## 2. Environment Configuration

1. Copy the provided samples and adjust values:
   ```bash
   cp .env.example .env                # global docker-compose settings (FQDN, admin email)
   cp backend/.env.sample backend/.env # backend/worker/API secrets
   ```
2. Mandatory variables in `backend/.env`:
   - `REDIS_URL`, `DATABASE_URL` — connection strings (already pointing at docker services if you keep defaults).
   - `APIFY_TOKEN`, `APIFY_ACTOR_ID`, `APIFY_ACTOR_TWITTER`, `APIFY_ACTOR_TELEGRAM` — Apify API tokens.
   - `GROQ_API_KEY` — Groq key for the Triple-AI pipeline.
   - `HELIUS_API_KEY`, `RPC_URL`, `QUICKNODE_URL` — on-chain providers. Leave QuickNode empty in demo mode and the worker will skip the placeholder endpoint.
   - `ALERTS_SIGNATURE_SECRET`, `HELIUS_WEBHOOK_SECRET` — HMAC secrets for webhook validation.

3. Ensure the root `.env` defines domains (defaults: `app.localhost`, `api.localhost`, `ai.localhost`) used by Caddy.

## 3. Running the Stack (Docker)

1. Build and start everything:
   ```bash
   docker compose up --build -d
   ```

2. Check service health:
   ```bash
   docker compose ps
   ```
   All services (`api`, `worker`, `ai-core`, `web`, `proxy`, `redis`, `postgres`, `parser-http`, `parser-browser`) should reach `Up (healthy)`.

3. Quick smoke checks:
   - FastAPI health: `curl -k https://api.localhost/api/health`
   - UI dashboard: open `https://app.localhost`
   - SSE stream: `curl -k https://api.localhost/stream`

4. Stop and clean:
   ```bash
   docker compose down
   ```

> Development stack: for live code mounts and forwarded ports use the new `docker-compose.dev.yml` file.
> ```bash
> docker compose -f docker-compose.dev.yml up --build -d
> ```
> Stop it the same way with `docker compose -f docker-compose.dev.yml down`.

## 4. Local Test Suites

### Backend (FastAPI, Triple-AI)

```bash
python3 -m pytest backend/tests
```

This runs unit, API, integration, and the e2e flow (`backend/tests/e2e/test_full_cycle.py`).

### Worker (Node + BullMQ)

```bash
cd backend
npm install   # first run
npm test
```

The script executes:
- `tests/test_engine.js` — signal engine smoke test
- `tests/test_worker.js` — risk scoring helper
- `tests/test_providers.js` — Helius/QuickNode adapters

### Web (React control center)

```bash
cd web
npm install   # first run
npm test
```

Vitest covers key UI components, context state, and API helpers.

## 5. Verifying Critical Flows & Integrations

### 5.0 API integrations (Groq, Apify, Helius, QuickNode)

**Groq advice endpoint** — requires `GROQ_API_KEY` in `backend/.env`.
```bash
curl -k -X POST https://api.localhost/api/advice \
  -H 'Content-Type: application/json' \
  -d '{
        "prompt": "Evaluate meme coin momentum",
        "metadata": {
          "profile": "pump",
          "metrics": {"SOCIAL_BURST":6, "FREQ_5M":7, "MENTIONS":200}
        }
      }'
```
Expect `200 OK` with a `decision` block and the `chain` field (`scout → analyst → judge`).

**Apify webhook** — see §5.2 for full pipeline instructions (make sure `ALERTS_SIGNATURE_SECRET` is set).

**Helius webhook intake** — with `HELIUS_WEBHOOK_SECRET`, send a signed sample:
```bash
tee tmp_helius_payload.json <<'JSON'
{
  "data": [{
    "type": "transfer",
    "transactionSignature": "demo-signature",
    "account": "demo-account",
    "nativeTransfers": [{"amount": 750000000000}],
    "tokenTransfers": [],
    "events": {},
    "raw": {}
  }]
}
JSON

export HELIUS_SECRET=$(grep ^HELIUS_WEBHOOK_SECRET backend/.env | cut -d= -f2)
python3 - <<'PY'
import hmac, hashlib, os
secret = os.environ['HELIUS_SECRET'].encode()
body = open('tmp_helius_payload.json','rb').read()
print(hmac.new(secret, body, hashlib.sha256).hexdigest())
PY

curl -k -X POST https://api.localhost/api/helius/webhook \
  -H 'Content-Type: application/json' \
  -H 'x-helius-signature: <hex-signature>' \
  --data-binary @tmp_helius_payload.json
```
Worker logs should show a whale alert if the transfer crosses `HELIUS_HIGH_VALUE_SOL`.

**QuickNode integration** — set `QUICKNODE_URL` (and optional `QUICKNODE_TOKEN`) in `backend/.env`, then run:
```bash
cd backend
npm test -- tests/test_providers.js
```
This validates the `QuickNodeProvider` response parsing. When the worker runs with the real URL, watch `docker compose logs -f worker` for `[quicknode]` price fetch messages.

### 5.1 Parser → Candidate → Worker Loop

Trigger a parser run via API:

```bash
curl -k -X POST https://api.localhost/api/parser/run \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"WIF","sources":["twitter"],"filters":["hot"],"priority":9}'
```

Expected results:
- HTTP `202 Accepted` containing a `job_id`.
- A new row in `candidates` with status `queued`.
- Worker emits an SSE event `parser_job`. If overall risk is `info`, the worker auto-simulates a BUY via `/api/trade/confirm` and broadcasts `trade_simulated`.

### 5.2 Apify → FastAPI Callback → BullMQ Worker

1. Craft a payload and signature (`ALERTS_SIGNATURE_SECRET`):
   ```bash
   tee tmp_apify_payload.json <<'JSON'
   {
     "actorRun": {
       "id": "run-local-123",
       "status": "SUCCEEDED",
       "startedAt": "2025-10-06T20:00:00.000Z",
       "finishedAt": "2025-10-06T20:05:00.000Z",
       "succeeded": true
     },
     "datasetItems": [{ "symbol": "TEST", "score": 87, "tweet": "Demo signal" }],
     "meta": {
       "priority": 7,
       "sources": ["twitter"],
       "filters": ["hot"],
       "requested_by": "apify-demo"
     }
   }
   JSON

   python3 - <<'PY'
   import hmac, hashlib
   secret = b'replace-me'  # set to ALERTS_SIGNATURE_SECRET
   body = open('tmp_apify_payload.json','rb').read()
   print(hmac.new(secret, body, hashlib.sha256).hexdigest())
   PY
   ```

2. Send the callback:
```bash
curl -k -X POST https://api.localhost/api/apify/callback \
  -H 'Content-Type: application/json' \
  -H 'x-apify-signature: <hex-signature>' \
  --data-binary @tmp_apify_payload.json
```

Expect a `200 OK` response in under ~2 seconds.

3. Verify end-to-end:
   - Candidate stored: `docker compose exec postgres psql -U parser -d super_parser -c "SELECT symbol,status FROM candidates ORDER BY created_at DESC LIMIT 5;"`
   - Queue consumed: `docker compose exec redis redis-cli LLEN sp:queue:apify:dataset`
   - Worker logs/SSE show `social_signal` events.

### 5.3 Helius Webhook Intake

1. Set `HELIUS_WEBHOOK_SECRET`.
2. Point Helius to `https://api.localhost/api/helius/webhook`.
3. When a high-volume transfer arrives, the worker will:
   - Emit an SSE `helius_event`.
   - Post a `warn` alert if SOL volume ≥ `HELIUS_HIGH_VALUE_SOL` (default 500).

### 5.4 Inspecting Worker Behaviour

- Stream logs: `docker compose logs -f worker`
- Queue lengths: `docker compose exec redis redis-cli LLEN sp:queue:<name>`
- Metrics: `curl http://localhost:9110/metrics`
- To disable auto trade simulation, introduce an env guard inside `parser-run.js` (e.g., `WORKER_ENABLE_TRADE_SIM=false`).

## 6. Frequently Used URLs & Commands

| Purpose                | Endpoint / Command                                |
|------------------------|----------------------------------------------------|
| UI dashboard           | `https://app.localhost`
| FastAPI Swagger        | `https://api.localhost/docs`
| SSE signal stream      | `https://api.localhost/stream`
| AI Core health         | `https://ai.localhost/health`
| Worker metrics         | `curl http://localhost:9110/metrics`
| Tear down with volumes | `docker compose down -v`

## 7. Further Reading

- `docs/requirements.md` — feature checklist and current status
- `docs/integrations.md` — Groq, Apify, Helius, QuickNode integration notes
- `docs/demo_setup.txt` — scripted scenarios for demos
- `docs/web_interface_adjusments.txt` — UI tweaks and backlog
- Git branching: submit changes via the `feature/apify-integration` branch targeting `dev`
- Logging: view service logs with `docker compose[ -f docker-compose.dev.yml] logs <service>` (stdout/err)

For troubleshooting, inspect `docker compose logs <service>` and confirm environment variables are correctly set.
