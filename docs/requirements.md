Коротко — что нужно сделать (Scope):

    Настроить Apify акторы для X (Twitter) и Telegram, которые постят результаты в наш webhook /api/apify/callback.

    Интерфейс между Apify → FastAPI: нормализация, валидация, создание Candidate + enqueue в BullMQ/Redis.

    Интеграция Groq для скоринга кандидатов (через вызовы LLM, результат — score + hints).

    Подписка Helius webhooks (mint, poolCreated, addLiquidity, largeTx) + QuickNode RPC fallback.

    Worker (Node) — обработка очереди: quick checks (RugCheck/Chainbase stub), push alert в DB и UI, и симуляция flow «Buy» (лог).

    Собрать в Docker (ui, api, worker, parser-http, parser-browser, redis, postgres, proxy) + GitHub Actions автодеплой.

    Провести E2E тест на тестовых ключах и подготовить отчёт по результатам.


Deliverables

    Локальный сценарий запуска (docker compose dev) и подтверждение что api, ui, redis, postgres стартуют.

    Рабочий flow: Apify → FastAPI → enqueue → worker stub → логирование (на тестовых ключах).

    Короткий отчёт: список найденных блокеров/ошибок, ETA по полноценной интеграции и ориентиp по цене для итераций 1/2/3.

    PR/ветка с кодом или патчем + инструкция по локальному запуску (README.md).

Пост-assessment — Milestones и цена (после оценки):

    М1 (инфраструктура: BД, Redis, базовые эндпоинты) — оценка часов/€ после assessment.

    М2 (Apify интеграция + Groq) — оценка.

    М3 (Helius/QuickNode + worker + автодеплой) — оценка.
    (каждый milestone — отдельный платёж/счёт, принимается по критериям приёмки).

Критерии приёмки (чтобы считать задачу выполненной):

    docker compose up -d поднимает ui, api, redis, postgres без ошибок.

    /api/health возвращает OK.

    Apify callback приходит → данные нормализуются и появляются в /api/candidates.

    Job уходит в BullMQ и воркер логирует успешную обработку (trace/log).

    В репозитории — docker-compose.dev.yml, .env.example, README.md, и пр.

    Видео 2–5 минут: запуск локально + демонстрация flow (Apify → callback → candidate → job processed).

Технические детали / ожидания (чтобы не гадать):

    Webhook: POST /api/apify/callback принимает JSON, возвращает 200 быстро (<2s).

    Groq: используйте переменную GROQ_API_KEY в .env (тестовый ключ).

    Helius: HELIUS_API_KEY — тестовые. Webhook для Helius POST /api/helius/webhook.

    Никаких продакшн-ключей в коммите.

    Код — через ветку feature/apify-integration, PR в dev.

    Логи: stdout/stderr + сохранение ошибок в /logs или через docker logs.

    Требую CONCURRENCY параметры через .env (для парсера и browser-pool).

## Статус проверки (2025-10-06)

- [x] Настроить Apify акторы для X/TG и постинг в `/api/apify/callback` — `/api/apify/run` теперь поддерживает пресеты twitter/telegram, задаёт webhook (`FASTAPI_URL/api/apify/callback`) и запускает актора через Apify API.
- [x] Интерфейс Apify → FastAPI с созданием Candidate — callback теперь создаёт кандидатов при отсутствии `candidate_id`, сохраняет результаты и ставит задачу в очередь (см. `backend/api/routes/apify.py`).
- [x] Интеграция Groq для скоринга — Triple-AI pipeline (`ai_core/server/pipeline.py`) вызывает Groq через `GroqClient.chat_completion`; pytest `backend/tests/integration/test_ai_core.py` проходит (требуется реальный ключ для боевого запроса).
- [x] Подписка Helius + QuickNode fallback — провайдеры (`backend/src/providers/helius.js`, `quicknode.js`) и ingest-loop обновлены; unit-тест `npm test` (providers) проходит, реальные ключи не проверялись.
- [x] Worker BullMQ flow (RugCheck стобы, алерт, симуляция buy) — real worker теперь триггерит Apify, публикует алерты и имитирует BUY через `/api/trade/confirm`, события видны в SSE и FastAPI логах.
- [x] Docker стек (ui, api, worker, parser-http, parser-browser, redis, postgres, proxy) — parser-http/parser-browser добавлены в `docker-compose.yml`, но `docker compose up` ещё не прогонялся на реальном окружении.
- [ ] E2E тест с тестовыми ключами и итоговый отчёт — автоматизированный pytest (`backend/tests/e2e/test_full_cycle.py`) проходит, но прогон на реальных ключах и заполнение `docs/release_report.md` не выполнены.

### Выполненные проверки

- `python3 -m pytest backend/tests`
- `npm test` в `backend/` (включая провайдеры Helius/QuickNode)
- `npm test` в `web/`
- Ответ `/api/health` проверен через FastAPI TestClient (ENV: sqlite/redis локальные).
