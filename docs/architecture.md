# Super Parser AI — Architecture Snapshot

## Monorepo Layout
- `ai_core/` — merged AI SuperCenter configs, datasets, and vendor gateways migrated from `AI_SUPER_SYSTEM_merged_v6` (aligns with `docs/rules.md:13`).
- `backend/` — FastAPI/BullMQ service formerly `super-parser-ultimate-pro`, retaining `src/`, `configs/`, and Docker assets required by `docs/rules.md:29-58`.
- `web/` — React/Vite client bootstrapped with legacy UI add-ons and docs, satisfying the `web/` contract from `docs/rules.md:60-65`.

## Module Notes
- **AI Core** (`ai_core/`): configs such as `configs/llm_router.json`, `configs/risk_policy.json`, and supercenter scripts remain untouched; integration endpoints documented in `ai_core/docs/*.md`.
- **Backend** (`backend/`): Node orchestrатор с adapter'ами, pipelines, SSE сервером и FastAPI слоем (`backend/api/` маршруты `/api/parser/run`, `/api/apify/callback`, `/api/helius/webhook`, `/api/alerts`, `/api/trade/confirm`, `/api/advice`) — соединяет воркер, Groq/AI Core и фронтенд; legacy FastAPI заглушка сохранена в `backend/legacy/web_int_parser_stub/`.
- **Worker** (`backend/src/worker/*`): BullMQ очереди (`parser-run`, `helius-events`, `apify-dataset`) получают задачи от FastAPI через Redis-бирдж `RedisBullBridge`; обработчики обогащают данные RugCheck/Sniffer и шлют алерты обратно в API.
- **Frontend** (`web/`): React/Vite client с контекстом (`src/context/AppContext.jsx`), вкладками и SSE подпиской; `src/App.jsx` интегрирует REST (`/api/*`) и `EventSource /stream`, компоненты лежат в `src/components/*`, спецификации/UX — в `web/docs/`.

## Data & Docs
- Shared documentation retained in `docs/` with compliance tracking in `docs/plan.md` and architecture alignment recorded here.

## Deployment
- Docker Compose (`docker-compose.yml`) orchestrates `proxy`, `web`, `api`, `worker`, `ai-core`, `redis`, and `postgres` services with TLS termination handled by Caddy.
- Persistent data is stored in named volumes (`postgres_data`, `redis_data`, `caddy_data`, `ai_core_cache`).
- Service-level healthchecks gate startups; see `docs/deploy.md` for operational commands.

## CI/CD
- GitHub Actions workflow `ci.yml` runs backend pytest, Node worker tests, web Vitest/build, and Docker build validation on each push/PR to `main`.

## Testing
- Unit/API tests live in `backend/tests/api`, Triple-AI integration in `backend/tests/integration`, and the Phase IX end-to-end scenario in `backend/tests/e2e/test_full_cycle.py`.

## Integrations
- Groq, Apify, Helius, and QuickNode integrations are implemented as described in `docs/integrations.md`, wiring external APIs into the Triple-AI advice flow and on-chain ingest worker.
