# Merge Notes v5
- Объединение v3_FIXED + деплой из v1.
- Добавлены ai_global_rules.json, ai_fine_filters.json, ai_weights_v2.json, alerts_presets.json, whales_providers.json.
- Документация: docs/ui_spec.md, docs/addons_api.md.


[Triple-AI Integration 2025-09-28T11:23:06.174700Z]
- Added 3-model router (scout/analyst/judge) in configs/llm_router.json
- Supercenter wiring in configs/ai_supercenter.json
- Profiles (twitter/pump/whales30d/find_token/listings) mapped to routes in configs/profiles_config.json
- Fail-closed risk policy updated in configs/risk_policy.json
- Added data resources: seed_whitelist.txt, vision_anchors.txt
- Added docs: README_TRIPLE_AI.md, addons_api_patch.md; raw_sources updated with latest .docx
- All previous rules/filters/weights preserved (ai_global_rules.json, ai_fine_filters.json, ai_weights_v2.json)

[AI Vendors & Compose]
- Added vendors/ with vLLM, llama.cpp, mistral-inference, Qwen2 sources
- Added services/compose/docker-compose.ai.yml and .env.ai.example
- Added scripts/launch_triple_ai.sh and download_weights.py
- Added configs/llm_endpoints.json to point router to local OpenAI-compatible endpoints

[Gateway & CPU Judge 2025-09-28T11:47:02.323842Z]
- Добавлен volume-монтаж HF cache (все vLLM сервисы используют volume `hf_cache`)
- Добавлен сервис `judge-llamacpp` (CPU) с OpenAI-like API на :8004
- Добавлен reverse-proxy `gateway` (Nginx) с ACL + Basic Auth на :8080
- Обновлён `configs/llm_endpoints.json` (профили `direct` и `via_gateway`)
- Добавлен `docs/SECURITY_GATEWAY.md`
