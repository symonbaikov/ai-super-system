# Super Parser AI — Execution Plan

> Обновляется при каждой фазе. Базируется на `docs/rules.md` и вспомогательных спецификациях (`docs/*.md`, `backend/docs/sources/*.txt`, `web/docs/*.md`).

## Phase I — Архитектурная синхронизация
- **Description:** Подтвердить монорепозитарную структуру `ai_core/`, `backend/`, `web/`, устранить расхождения с эталоном.
- **Tasks:**
  1. Свериться с `docs/rules.md` («📂 Общая структура проекта») и `docs/architecture.md` предыдущих итераций.
  2. Сопоставить текущие директории с требуемыми: перенести AI SuperCenter → `ai_core/`, Node backend → `backend/`, фронтенд → `web/`.
  3. Зафиксировать изменения и зависимости в `docs/architecture.md`.
- **Key Files / Directories:** `ai_core/`, `backend/`, `web/`, `docs/architecture.md`.
- **Expected Output:** Корень репозитория соответствует схеме, описанной в `docs/rules.md`.
- **Definition of Done:** Структура выровнена; документация обновлена; отклонений от требований нет.
- **Verification Checklist:**
  - `docs/rules.md:13-65` — целевая структура.
  - `docs/architecture.md` — отражает текущее состояние.
- **Next Steps:** После утверждения структуры перейти к расширенной документации (Phase II).

## Phase II — Документация и планирование
- **Description:** Детализировать дорожную карту, отразить зависимости фаз и контрольные точки в `docs/plan.md`, синхронизировать с `docs/architecture.md`.
- **Tasks:**
  1. Для каждой фазы прописать пошаговые подзадачи с указанием ответственных директорий/файлов (`backend/src/*`, `web/src/*`, `ai_core/configs/*`).
  2. Для каждой фазы добавить критерии качества, зависимости и проверочные артефакты (`Verification Checklist`).
  3. Описать «Next Steps» после завершения фазы и обновить раздел Compliance Check.
  4. При необходимости скорректировать `docs/architecture.md`, чтобы отразить планируемые изменения модулей.
- **Key Files:** `docs/plan.md`, `docs/architecture.md`, `docs/rules.md`, `backend/docs/sources/*.txt`, `web/docs/*.md`.
- **Expected Output:** Полная пофазная дорожная карта с прозрачной проверкой и зависимостями.
- **Definition of Done:** Все девять фаз описаны единообразно; указан перечень файлов и критериев; Compliance Check отражает текущий статус.
- **Verification Checklist:**
  - `docs/rules.md:80-118` — требования к процессу.
  - `docs/rules.md:244-318` — обновлённый план действий.
- **Next Steps:** После утверждения плана стартовать реализацию FastAPI (Phase III).

## Phase III — Backend API (FastAPI)
- **Description:** Реализовать FastAPI-шлюз в `backend/api/`, обеспечив маршруты `/api/parser/run`, `/api/apify/callback`, `/api/helius/webhook`, `/api/alerts`, `/api/trade/confirm`, подключить Redis/PostgreSQL, Groq, Apify.
- **Tasks:**
  1. Создать каркас приложения (`backend/api/main.py`, `backend/api/routes/*`, `backend/api/schemas.py`) с конфигом в `.env` (копия `backend/.env.sample`).
  2. Определить Pydantic-схемы запросов/ответов согласно `backend/docs/sources/чтобы система не падала. Парсер +А.docx.txt`.
  3. Подключить инфраструктурные зависимости: Redis (alerts queue/cache), PostgreSQL (таблицы `alerts`, `candidates`, `logs`, `settings`), Groq и Apify прокси.
  4. Настроить обработку ошибок, логирование и тесты (`backend/tests/api/test_routes.py`).
- **Key Files / Directories:** `backend/api/`, `backend/.env.sample`, `backend/tests/api/`, `backend/configs/rules.json`.
- **Expected Output:** Рабочий FastAPI сервис с тестовым покрытием и документацией OpenAPI.
- **Definition of Done:** Все пять маршрутов отвечают; интеграции замоканы в тестах; `pytest backend/tests/api` проходит.
- **Verification Checklist:**
  - `docs/rules.md:180-228` — требования к бэкенду.
  - `backend/docs/sources/чтобы система не падала. Парсер +А.docx.txt` — flow API.
  - `docs/rules.md:305-318` — цепочка интеграций.
- **Next Steps:** Передать события в воркер и обработать очереди (Phase IV).

## Phase IV — Worker (Node)
- **Description:** Настроить BullMQ-очереди и адаптеры Helius/Apify/CEX, реализовать взаимодействие с FastAPI.
- **Tasks:**
  1. Настроить подключение BullMQ (`backend/src/adapters/queues/redis.js`), конфигурацию задач и ретраев.
  2. Реализовать консьюмеры для Helius webhook (`backend/src/jobs/whales.js`), листингов (`backend/src/jobs/detect_listings.js`), интеграцию с RugCheck/Sniffer (`backend/src/adapters/social/*`).
  3. Настроить вебхуки `/api/helius/webhook` и пересылку событий в очереди, подтверждения трейдов через `/api/trade/confirm`.
  4. Добавить метрики/алерты (Prometheus, Sentry) и smoke-тесты (`backend/tests/worker/*`).
- **Key Files / Directories:** `backend/src/adapters/`, `backend/src/jobs/`, `backend/src/pipelines/`, `backend/src/server/sse.js`.
- **Expected Output:** Надёжный конвейер задач с мониторингом и повторными попытками.
- **Definition of Done:** Очереди принимают события из FastAPI; алерты отправляются; мониторинг доступен; тесты очередей проходят.
- **Verification Checklist:**
  - `docs/rules.md:229-287` — Worker требования.
  - `backend/docs/sources/чтобы соединить Альфы2.docx.txt` — интеграции worker ↔ AI.
  - `backend/README.md` — сигнальный движок и SSE.
- **Next Steps:** Обновить фронтенд для потребления SSE/REST и управления Worker (Phase V).

## Phase V — Frontend (React PR112)
- **Description:** Перенести PR112 интерфейс в Vite, реализовать вкладки, контексты и потоковые данные (SSE/REST) с интеграцией настроек риска.
- **Tasks:**
  1. Импортировать макеты из `web/docs/ui_spec.md`, `docs/дополнения для кусков веб интерфейса.docx → web/docs/*` и сверить с PR112 App.
  2. Сконфигурировать глобальные состояния (Context/Reducer) для сигналов, алертов, AI рекомендаций.
  3. Реализовать Tab-навигацию (Signals, Helius, CEX Radar, Tradeview, Settings), подключить SSE (`/stream`) и REST (`/api/*`).
  4. Добавить тесты (`web/src/__tests__/*`), Storybook/Chromatic (если требуется) и настроить Vite build.
- **Key Files / Directories:** `web/src/App.jsx`, `web/src/components/`, `web/src/context/`, `web/package.json`, `web/vite.config.js`.
- **Expected Output:** Функциональный UI с живыми данными, соответствующий требованиям PR112.
- **Definition of Done:** Все вкладки работают; SSE поток отображается; сборка `npm run build` проходит; тесты `npm test` успешны.
- **Verification Checklist:**
  - `docs/rules.md:288-318` — фронтенд требования.
  - `web/docs/ui_spec.md`, `web/docs/README_WEB_INT.md` — UX/flows.
  - `docs/дополнения для кусков веб интерфейса.docx` (перевод в `web/docs/`).
- **Next Steps:** Подключить AI Core через `/advice` и автоматизацию решений (Phase VI).

## Phase VI — AI Core
- **Description:** Интегрировать цепочку Scout → Analyst → Judge, настроить профили и политику риска для ответов `/advice`.
- **Tasks:**
  1. Изучить конфиги (`ai_core/configs/llm_router.json`, `ai_core/configs/ai_supercenter.json`, `ai_core/configs/risk_policy.json`).
  2. Реализовать сервис-обёртку (`ai_core/server/*`) и API-прокси для FastAPI (`backend/api/routes/advice.py`).
  3. Настроить профили/маршруты (`profiles_config.json`, `ai_weights_v2.json`, `ai_global_rules.json`) и фолбэк-механизмы.
  4. Написать интеграционные тесты (`backend/tests/integration/test_ai_core.py`) с mock LLM endpoints.
- **Key Files / Directories:** `ai_core/configs/*`, `ai_core/server/`, `backend/api/routes/advice.py`, `.env` (GOLIB_* vars).
- **Expected Output:** Согласованный AI конвейер, дающий рекомендации через `/advice` и соблюдающий risk policy.
- **Definition of Done:** `/advice` возвращает корректные решения; risk policy соблюдается; интеграционные тесты проходят.
- **Verification Checklist:**
  - `ai_core/docs/README_TRIPLE_AI.md`, `ai_core/docs/addons_api_patch.md`.
  - `docs/rules.md:140-179` — AI SuperCenter указания.
- **Next Steps:** Упаковать сервисы в контейнеры и подготовить окружение (Phase VII).

## Phase VII — Инфраструктура
- **Description:** Собрать docker-compose стек (ui, api, worker, ai_core, redis, postgres, proxy), настроить TLS и переменные окружения.
- **Tasks:**
  1. Подготовить `docker-compose.yml` в корне с сервисами и сетями; добавить `.env` шаблоны.
  2. Создать конфигурацию реверс-прокси (Caddyfile или Nginx) с TLS/Certbot.
  3. Настроить volume для данных (postgres, redis, ai_core hf_cache) и healthchecks.
  4. Обновить документацию по деплойменту (`docs/deploy.md` или раздел в README).
- **Key Files / Directories:** `docker-compose.yml`, `deploy/`, `backend/Dockerfile`, `web/Dockerfile`, `ai_core/services/compose/*`.
- **Expected Output:** `docker compose up -d` поднимает все сервисы локально/стейджинг без ошибок.
- **Definition of Done:** Сервисы доступны по HTTPS; healthchecks зелёные; документирован запуск.
- **Verification Checklist:**
  - `docs/rules.md:319-360` — Docker/Deploy указания.
  - `docs/freelancer_task2.md` (из docx) — архитектурные диаграммы и compose.
- **Next Steps:** Настроить CI/CD pipeline для автоматического деплоя (Phase VIII).

## Phase VIII — CI/CD
- **Description:** Автоматизировать сборку, тестирование и деплой через GitHub Actions и сопутствующие сервисы.
- **Tasks:**
  1. Создать workflow `./.github/workflows/deploy.yml` с шагами checkout → build → test → deploy.
  2. Добавить отдельные джобы для backend (`npm test`, `pytest`), frontend (`npm run test`, `npm run build`), worker lint.
  3. Интегрировать docker build/push, secrets, уведомления в Slack/Telegram.
  4. Документировать переменные окружения и onboarding в `docs/ci_cd.md`.
- **Key Files / Directories:** `.github/workflows/*.yml`, `docs/ci_cd.md`, `backend/package.json`, `web/package.json`.
- **Expected Output:** Автоматические проверки и деплой при push/PR.
- **Definition of Done:** Workflow проходит без ошибок; деплой запускается автоматически на основную среду.
- **Verification Checklist:**
  - `docs/rules.md:361-380` — CI/CD указания.
  - `docs/Фрилансеру.Задание1.docx` (секция про деплой).
- **Next Steps:** Провести финальные e2e проверки и релиз (Phase IX).

## Phase IX — Финальные тесты
- **Description:** Провести end-to-end проверку полного цикла: соцсигналы → on-chain → AI решение → трейд → алерт.
- **Tasks:**
  1. Подготовить e2e сценарии (Playwright/Postman/Newman) с mock-провайдерами и реальными интеграциями.
  2. Провести нагрузочные тесты очередей/AI (`backend/tests/e2e`, `ai_core/tests/load/*`).
  3. Снять логи/метрики, сформировать отчёт и чек-лист релиза.
  4. Получить подтверждение от заказчика и зафиксировать релиз в CHANGELOG.
- **Key Files / Directories:** `tests/e2e/`, `backend/tests/e2e/`, `ai_core/tests/`, `docs/release_report.md`.
- **Expected Output:** Протокол успешного прогона с приложенными логами и метриками.
- **Definition of Done:** Все сценарии завершаются без критичных ошибок; чек-лист релиза (`docs/rules.md:381-420`) закрыт.
- **Verification Checklist:**
  - `docs/rules.md:381-420` — контрольный чек-лист.
  - `docs/architecture.md` — итоговое состояние зафиксировано.
- **Next Steps:** Перейти в режим поддержки: мониторинг, обратная связь, пост-релизные задачи.

---

## Compliance Check
- *Phase I:* ✅ Completed — Корневая структура соответствует `docs/rules.md:13-65`, отражено в `docs/architecture.md`.
- *Phase II:* ✅ Completed — План детализирован по фазам, ссылки на спецификации добавлены в разделы.
- *Phase III:* ✅ Completed — FastAPI слой (`backend/api/*`) реализует требуемые эндпоинты и покрыт тестами.
- *Phase IV:* ✅ Completed — BullMQ воркер (`backend/src/worker/*`) обрабатывает очереди parser/apify/helius и рассылает алерты в FastAPI.
- *Phase V:* ✅ Completed — React UI (Tabs + Context + SSE/REST) реализован в `web/src`, сборка `npm run build` проходит.
- *Phase VI:* ✅ Completed — Triple-AI pipeline подключён через `/api/advice`, risk policy из `ai_core/configs` применяется и покрыта интеграционными тестами.
- *Phase VII:* ✅ Completed — Docker Compose стек (proxy/ui/api/worker/ai-core/redis/postgres) с TLS и healthchecks задокументирован в `docs/deploy.md`.
- *Phase VIII:* ✅ Completed — GitHub Actions (`.github/workflows/ci.yml`) выполняет pytest, npm/ Vitest и Docker build-check перед деплоем.
- *Phase IX:* ✅ Completed — e2e сценарий (`backend/tests/e2e/test_full_cycle.py`) покрывает сигнал→AI→алерт→трейд; отчёт фиксируется в `docs/release_report.md`.

> Примечание: текстовые расшифровки `.docx` использованы из `backend/docs/sources/*.txt` и `web/docs/*`. Перед началом каждой фазы необходимо актуализировать соответствующие документы.
