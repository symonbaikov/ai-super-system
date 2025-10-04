# Super Parser AI — Architecture Snapshot

## Monorepo Layout
- `ai_core/` — merged AI SuperCenter configs, datasets, and vendor gateways migrated from `AI_SUPER_SYSTEM_merged_v6` (aligns with `docs/rules.md:13`).
- `backend/` — FastAPI/BullMQ service formerly `super-parser-ultimate-pro`, retaining `src/`, `configs/`, and Docker assets required by `docs/rules.md:29-58`.
- `web/` — React/Vite client bootstrapped with legacy UI add-ons and docs, satisfying the `web/` contract from `docs/rules.md:60-65`.

## Module Notes
- **AI Core** (`ai_core/`): configs such as `configs/llm_router.json`, `configs/risk_policy.json`, and supercenter scripts remain untouched; integration endpoints documented in `ai_core/docs/*.md`.
- **Backend** (`backend/`): Node orchestrator with adapters, pipelines, jobs, and SSE server; FastAPI stub preserved in `backend/legacy/web_int_parser_stub/` for reference.
- **Frontend** (`web/`): Houses `src/components/*` controls, new `src/App.jsx`, `vite.config.js`, and legacy specs under `web/docs/` for the PR112 parity plan.

## Data & Docs
- Shared documentation retained in `docs/` with compliance tracking in `docs/plan.md` and architecture alignment recorded here.
