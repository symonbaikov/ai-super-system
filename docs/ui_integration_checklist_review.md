# UI Integration Checklist Review

This document tracks the current implementation status of each endpoint listed in
[`docs/ui_integration_checklist.md`](./ui_integration_checklist.md) based on the
FastAPI application under `backend/api`.

For verification we exercised the public routes via `fastapi.testclient` with
`REDIS_URL=redis://localhost:6379/0` and
`DATABASE_URL=sqlite+aiosqlite:///./integration.db` to satisfy settings
validation. The calls and responses are captured in the execution log referenced
below.

## Endpoint status summary

| Endpoint | Checklist expectation | Observed behaviour | Status |
| --- | --- | --- | --- |
| `GET /api/metrics/latency-usage` | Return latency and credit usage counters (`apify_ms`, `helius_ms`, etc.). | Implemented in `backend/api/routes/integration.py` returning mock latency and credit numbers with a suggestion string, matching the documented shape.【F:backend/api/routes/integration.py†L17-L30】 Sample call returns HTTP 200 with the expected fields.【b9b5bd†L1-L6】 | ✅ Implemented (mock data). |
| `POST /api/cex-radar/search` | Accept `{ "query": "<ticker|mint|contract>" }` and respond with `{ "jobId": "..." }`. | Integration router validates `query` and responds with a random job id as required.【F:backend/api/routes/integration.py†L33-L43】 Test call succeeds with job id string.【b9b5bd†L6-L9】 | ✅ Implemented (mock job id). |
| `GET /api/cex-radar/result?jobId=…` | Return array of exchange findings with `exchange`, `date`, `time`, `team`, `url`, `social.tw_1h`, `social.tg_online`. | Integration router returns a single Binance record with the documented shape and mock social metrics.【F:backend/api/routes/integration.py†L46-L60】 Test call confirms the structure.【b9b5bd†L9-L12】 | ✅ Implemented (static mock). |
| `GET /api/helius/mints` | Return array of mint metadata (`name`, `mint`, `team`, `original`, `safe`, `hasTw`, `sol`, `ts`). | Route produces a list with one hard-coded mint carrying all required fields.【F:backend/api/routes/integration.py†L63-L78】 Test call returns the matching payload.【b9b5bd†L12-L15】 | ✅ Implemented (mock data). |
| `POST /api/whales/scan` | Return `{ "jobId": "..." }`. | Integration router returns random job id without inspecting body, fulfilling contract.【F:backend/api/routes/integration.py†L81-L85】 Verified via test call.【b9b5bd†L15-L16】 | ✅ Implemented (mock job id). |
| `GET /api/whales/top3?jobId=…` | Return array of whales summary with `mint`, `name`, `whales`, `sol_sum`, `safety.{rugcheck,solsniffer}`, `hype.{tw_1h,tg_1h}`, `links.birdeye`. | Route returns a single object containing every required field with mock values.【F:backend/api/routes/integration.py†L88-L103】 Test call shows the expected payload.【b9b5bd†L16-L20】 | ✅ Implemented (static mock). |
| `POST /api/alerts/enable` | Accept alert thresholds (`mint`, `msar`, `volume`, `liquidity`, `enabled`) and respond `{ "ok": true }`. | Integration route validates presence of required keys and returns `{ "ok": True }` as per checklist.【F:backend/api/routes/integration.py†L106-L114】 Behaviour confirmed in test call.【b9b5bd†L20-L21】 | ✅ Implemented (validation only). |
| `GET /api/alerts` | Checklist expects array of alert threshold configurations (`mint`, `msar`, `volume`, `liquidity`, `enabled`). | Actual mounted route is `backend/api/routes/alerts.py`, which returns persisted alert records with schema `{id,title,severity,source,message,payload,...}` and depends on the database/redis queue; the integration mock defined later is not invoked.【F:backend/api/main.py†L34-L39】【F:backend/api/routes/alerts.py†L12-L53】 Current response is an empty list when no alerts exist, so the payload shape diverges from the checklist contract.【b9b5bd†L21-L22】 | ⚠️ **Not aligned**: needs adjustment (either update UI expectations or expose checklist-compatible endpoint). |
| `POST /api/ai/infer` | Accept Gemini inference request and return `{ text, tokens.{input,output}, cost_usd }`. | Integration route enforces `provider == "gemini"` and returns placeholder text plus token and cost metadata matching the spec.【F:backend/api/routes/integration.py†L117-L126】 Test call succeeds with mock response.【b9b5bd†L22-L24】 | ✅ Implemented (mock Gemini reply). |

## Required follow-up

1. **Alerts listing contract** – decide whether the UI should consume the real alerts API (`/api/alerts`) that exposes stored alert records (`id`, `title`, etc.) or whether the backend must provide the checklist schema (`mint`, `msar`, `volume`, `liquidity`, `enabled`). If the latter, adjust routing to avoid the collision with the production alerts endpoint or map data accordingly.【F:backend/api/routes/alerts.py†L12-L53】
2. If genuine backend integrations (Apify, Helius, BullMQ) are required instead of mock data, replace the placeholder implementations in `backend/api/routes/integration.py` with real queue/database interactions. Currently every successful check relies on static or randomly generated values.【F:backend/api/routes/integration.py†L17-L126】
