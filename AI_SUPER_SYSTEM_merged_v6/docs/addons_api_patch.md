# Addons API — Triple‑AI Patch

## POST /ai/route
Body: {"task":"classification|reasoning|judge","payload":{...}}
Uses llm_router.json to select scout|analyst|judge.

## POST /ai/alert/social
Accepts SocialAlert(v1). Forwards to pipeline M2→M3.

## GET /ai/health
Returns latency and status for scout/analyst/judge providers.
