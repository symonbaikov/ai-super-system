# Deployment Guide — Phase VII Stack

This repository now ships with a Docker Compose stack that bundles the entire Super Parser AI platform: web UI, FastAPI gateway, Node worker, Triple-AI core, Redis, Postgres, and a TLS-enabled Caddy proxy.

## 1. Prerequisites
- Docker Engine ≥ 24 and Docker Compose plugin.
- Hostnames `app.localhost`, `api.localhost`, and `ai.localhost` resolving to the deployment host (the `*.localhost` suffix works out of the box on modern OSes).

## 2. Environment Files
1. Copy the root template and adjust secrets:
   ```bash
   cp .env.example .env
   ```
2. Provision backend secrets (Groq, Apify, Helius, QuickNode) by copying the Node/FastAPI template:
   ```bash
   cp backend/.env.sample backend/.env
   ```
   The Compose stack injects most connection strings automatically (Redis, Postgres, AI Core). Populate vendor credentials (`GROQ_API_KEY`, `APIFY_TOKEN`, `HELIUS_API_KEY`, `QUICKNODE_URL`, optional `QUICKNODE_TOKEN`).

## 3. Start the Stack
```bash
docker compose up -d --build
```
The services exposed by the proxy:

| Host | Service | Notes |
|------|---------|-------|
| `https://app.localhost` | Web UI (static) | Served by Nginx behind Caddy. |
| `https://api.localhost` | FastAPI + `/stream` SSE | `/stream` is forwarded to the Node worker; REST resides on FastAPI. |
| `https://ai.localhost` | Triple-AI pipeline | Direct access to the pipeline service (mirrors `/api/advice`). |

Caddy issues internal TLS certificates automatically (`tls internal`), so browsers will trust the endpoints after the first visit (you may need to accept the self-signed CA once).

## 4. Service Topology
- **api** — Python 3.11 + uvicorn, depends on Postgres, Redis, and `ai-core`.
- **worker** — Node 20 service powering SSE, alerts, and queue processing.
- **ai-core** — Lightweight FastAPI wrapper around `TripleAIPipeline` with `/route` and `/advice` endpoints.
- **web** — Vite build served via Nginx; build args set `VITE_API_URL` / `VITE_STREAM_URL` to the proxy domain.
- **redis** / **postgres** — Data stores with persistent volumes (`redis_data`, `postgres_data`).
- **proxy** — Caddy reverse proxy with internal TLS and gzip compression.

Health checks ensure containers report `healthy` before dependents start; the shared Redis/Postgres URLs are baked into environment anchors inside `docker-compose.yml`.

## 5. Maintenance Commands
- View logs: `docker compose logs -f proxy api worker`
- Rebuild after code changes: `docker compose build api worker web ai-core`
- Stop stack: `docker compose down`
- Reset state (destructive): `docker compose down -v`

## 6. Next Steps
Phase VII is complete. Proceed to Phase VIII (CI/CD automation) once you are comfortable with the container workflow.
