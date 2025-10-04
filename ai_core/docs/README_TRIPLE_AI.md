# Triple‑AI SuperCenter (M1/M2/M3)

**Цель:** разнести функции по трём ИИ‑модулям: быстрый скаут, глубокий аналитик, арбитр‑политик. 
Используем 5‑мин цикл → эскалация до 1‑мин при условиях; на выходе — SocialAlert → RiskDecision → FinalDecision.

## Модули
- **M1 SocialScout (scout)** — быстрые задачи: классификация, извлечение сущностей, memeability, антиспам, краткое резюме. Groq 8B.
- **M2 OnchainAnalyst (analyst)** — глубокий разбор: merge соц+ончейн, whales, security, скоринг, пояснения, отчёт. Groq 70B.
- **M3 JudgePolicy (judge)** — консистентность, глобальные правила, fail‑closed, объяснимость, запись в память (Chroma), аудит.

## Поток
1) M1 собирает соц‑батч, использует `seed_whitelist.txt` и `vision_anchors.txt`. При memeability≥0.6 И (freq≥порог или trusted автор) — переключается на 1‑мин цикл; выдаёт SocialAlert.
2) M2 подтягивает Helius/Birdeye/Dexscreener, считает risk и скор по `ai_fine_filters.json`/`ai_weights_v2.json`, применяет `risk_policy.json`; формирует DraftDecision.
3) M3 проверяет правила, делает majority‑vote/объяснение, пишет в Chroma, возвращает FinalDecision.

## Файлы
- `llm_router.json` — маршрутизация 3‑модульная.
- `ai_supercenter.json` — роли/входы/выходы/схемы.
- `profiles_config.json` — привязка профилей к маршрутам.
- `risk_policy.json` — fail‑closed политика.
- Требуются внешние: `seed_whitelist.txt`, `vision_anchors.txt`, `ai_fine_filters.json`, `ai_weights_v2.json`, `alerts_presets.json`.

## Интеграция (коротко)
1. Положить JSON из патча в `configs/` вашей системы.
2. Убедиться, что в `.env` заданы ключи провайдеров LLM (GROQ_API_KEY, OPENROUTER_KEY и т.п.).
3. Включить профили `twitter/pump/whales30d/find_token/listings`; финальное решение идёт через `judge`.
