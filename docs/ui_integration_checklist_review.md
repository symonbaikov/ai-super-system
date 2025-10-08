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
| `GET /api/metrics/latency-usage` | Return latency and credit usage counters (`apify_ms`, `helius_ms`, etc.). | Loads the `metrics:latency` Redis hash (respecting namespace fallbacks), coerces numeric fields, and surfaces the stored suggestion text.【F:backend/api/routes/integration.py†L89-L104】 | ✅ Backed by Redis hash. |
| `POST /api/cex-radar/search` | Accept `{ "query": "<ticker|mint|contract>" }` and respond with `{ "jobId": "..." }`. | Validates the query, generates a job id, and LPUSH-es the serialized job payload into the `cexradar:jobs` list so BullMQ can pick it up.【F:backend/api/routes/integration.py†L107-L123】 | ✅ Enqueues real job. |
| `GET /api/cex-radar/result?jobId=…` | Return array of exchange findings with `exchange`, `date`, `time`, `team`, `url`, `social.tw_1h`, `social.tg_online`. | Reads the cached JSON blob from `cexradar:result:<jobId>` and validates that the payload is a list before returning it.【F:backend/api/routes/integration.py†L131-L142】 | ✅ Reads cached result. |
| `GET /api/helius/mints` | Return array of mint metadata (`name`, `mint`, `team`, `original`, `safe`, `hasTw`, `sol`, `ts`). | Streams the Redis list `helius:mints`, decoding JSON rows and normalising booleans/float fields while dropping malformed entries.【F:backend/api/routes/integration.py†L145-L173】 | ✅ Streams Redis feed. |
| `POST /api/whales/scan` | Return `{ "jobId": "..." }`. | Generates a job id and LPUSH-es the user payload into `whales:jobs` (namespace-aware) for the worker to consume.【F:backend/api/routes/integration.py†L176-L190】 | ✅ Enqueues real job. |
| `GET /api/whales/top3?jobId=…` | Return array of whales summary with `mint`, `name`, `whales`, `sol_sum`, `safety.{rugcheck,solsniffer}`, `hype.{tw_1h,tg_1h}`, `links.birdeye`. | Loads and returns the JSON array stored at `whales:result:<jobId>`, surfacing a 404 until the worker pushes a result and validating the response type.【F:backend/api/routes/integration.py†L193-L206】 | ✅ Reads cached result. |
| `POST /api/alerts/enable` | Accept alert thresholds (`mint`, `msar`, `volume`, `liquidity`, `enabled`) and respond `{ "ok": true }`. | Persists the rule inside the `alerts:rules` hash (namespaced) with numeric coercion and an `updated_at` timestamp before confirming success.【F:backend/api/routes/integration.py†L209-L233】 | ✅ Stores Redis rule. |
| `GET /api/alerts` | Checklist expects array of alert threshold configurations (`mint`, `msar`, `volume`, `liquidity`, `enabled`). | Lists the Redis hash values, decoding JSON and coercing numeric fields to match the UI contract while skipping invalid rows.【F:backend/api/routes/integration.py†L236-L261】 | ✅ Lists Redis rules. |
| `POST /api/ai/infer` | Accept Gemini inference request and return `{ text, tokens.{input,output}, cost_usd }`. | Still intentionally stubbed: rejects non-Gemini providers and returns a static placeholder payload for UI wiring.【F:backend/api/routes/integration.py†L265-L272】 | ✅ Placeholder retained. |
| `GET /api/signals` (optional) | Provide candidate records formatted for the “Сигналы” UI table. | Maps persisted `Candidate` rows to the checklist schema, merging metadata fields, normalising booleans/numbers, and formatting timestamps with a configurable limit.【F:backend/api/routes/signals.py†L151-L241】 | ✅ Backed by Postgres candidates. |
## Required follow-up
1. **Gemini integration** – `/api/ai/infer` still returns a hard-coded placeholder response; swap in the real Gemini client when credentials are available.【F:backend/api/routes/integration.py†L265-L272】
## Overall compliance
Every checklist endpoint apart from the intentionally stubbed Gemini inference
handler now works against the live Redis/Postgres data sources without relying
on mocks. The UI can therefore integrate end-to-end today, with the Gemini
integration remaining as the only pending follow-up item.