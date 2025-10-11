### Backend .env template (feature flags + AI provider)

Save as `backend/.env`.

```env
# Core
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql://parser:parser@postgres:5432/super_parser
FASTAPI_URL=http://api:9000

# Queues
QUEUE_NAMESPACE=sp
BULLMQ_PREFIX=sp-worker
WORKER_CONCURRENCY=2

# Feature flags
ENABLE_APIFY=false
ENABLE_SOCIAL_INTAKE=true

# AI provider selection
AI_PROVIDER=gemini
AI_PROVIDER_FALLBACK=groq

# Apify (optional if ENABLE_APIFY=true)
APIFY_TOKEN=
APIFY_ACTOR_ID=
APIFY_ACTOR_TWITTER=
APIFY_ACTOR_TELEGRAM=

# Gemini (Flowith)
GEMINI_BASE_URL=https://api.flowith.io/v1/gemini
GEMINI_API_KEY=

# Optional Google Gemini
GOOGLE_GEMINI_API_KEY=
GOOGLE_GEMINI_MODEL=gemini-2.5-flash

# Groq (optional)
GROQ_API_KEY=
GROQ_MODEL=mixtral-8x7b

# Security / signatures
HELIUS_WEBHOOK_SECRET=
ALERTS_SIGNATURE_SECRET=

# API TTLs / knobs
WHALES_RESULT_TTL_SECONDS=600
```

Switching modes:

- Gemini-only: `ENABLE_APIFY=false`, `ENABLE_SOCIAL_INTAKE=true`, `AI_PROVIDER=gemini`.
- Back to Apify: `ENABLE_APIFY=true`, `ENABLE_SOCIAL_INTAKE=false`, keep `AI_PROVIDER=gemini`.
- Groq provider: `AI_PROVIDER=groq` and set `GROQ_API_KEY`.

After changes: rebuild/restart api and worker.
