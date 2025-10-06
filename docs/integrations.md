# API Integrations Overview

This document explains how Super Parser AI integrates with the four external APIs required for live operation: **Groq**, **Apify**, **Helius**, and **QuickNode**.

## Groq — Triple-AI Orchestration
- **Where:** `backend/api/services/groq.py`, `ai_core/server/pipeline.py`.
- **How:** `/api/advice` now invokes the asynchronous Triple-AI pipeline. When `GROQ_API_KEY` is present, each stage (Scout, Analyst, Judge) calls Groq's `chat/completions` endpoint with stage-specific system prompts and routing derived from `ai_core/configs/llm_router.json`.
- **Fallback:** If no key is provided or Groq returns an error, the pipeline falls back to a deterministic summary so the advice endpoint still responds.
- **Configuration:** `GROQ_API_KEY`, `GROQ_MODEL`, and `GROQ_BASE_URL` (defaults to `https://api.groq.com/openai/v1`).

## Apify — Actor Runs & Webhooks
- **Where:** `backend/api/routes/apify.py`, `backend/api/services/apify.py`.
- **How:** `POST /api/apify/run` triggers an Apify actor via `ApifyClient.trigger_actor`, logs the run, and returns the run identifier. Apify webhooks post back to `/api/apify/callback`, which verifies signatures, stores results, and enqueues worker tasks.
- **Configuration:** `APIFY_TOKEN`, `APIFY_BASE_URL` (defaults to `https://api.apify.com`), optional `APIFY_ACTOR_ID`.

## Helius — On-chain Activity Feed
- **Where:** `backend/src/providers/helius.js`, `backend/src/pipelines/ingest_onchain.js`.
- **How:** `HeliusProvider` issues JSON-RPC requests to `getSignaturesForAddress` and exposes a REST helper for transaction lookups. The on-chain ingest loop pulls recent activity counts for tracked mints and converts them into candle metadata.
- **Configuration:** `HELIUS_API_KEY` (required), optional `HELIUS_REST_URL` to override the default `https://api.helius.xyz`.

## QuickNode — Token Price Snapshots
- **Where:** `backend/src/providers/quicknode.js`, `backend/src/pipelines/ingest_onchain.js`.
- **How:** `QuickNodeProvider` calls the `qn_getTokenPrice` JSON-RPC method to obtain live USD prices. The ingest loop combines these prices with Helius activity counts to produce updated candles per mint.
- **Configuration:** `QUICKNODE_URL`, optional `QUICKNODE_TOKEN` (sent as `x-qn-api-key`).

## Testing & CI
- Python: `backend/tests/api/test_routes.py` and `backend/tests/e2e/test_full_cycle.py` mock Groq/Apify interactions and validate the social→AI→trade flow.
- Node: `backend/tests/test_providers.js` stubs fetch to confirm Helius/QuickNode adapters parse responses correctly.
- GitHub Actions (`.github/workflows/ci.yml`) runs all suites plus Docker build validation.

Refer to `docs/deploy.md` for environment setup and `docs/release_report.md` for the Phase IX validation template.
