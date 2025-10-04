# Super Parser AI — Execution Plan

> Автогенерация: первая итерация плана. Все действия сверены с `rules.md` и доступными docs/*.md (где они присутствуют в репозитории).

## Phase I — Архитектурная синхронизация
- **Description:** Проверка актуальной структуры монорепозитория, соответствие папок `ai_core/`, `backend/` (super-parser-ultimate-pro) и `web/` целевым требованиям.
- **Tasks:**
  1. Проанализировать `rules.md` и README-файлы подпроектов.
  2. Зафиксировать несоответствия структуры (если есть) в разделе Compliance Check.
  3. Убедиться в наличии конфигураций AI Core и FastAPI/API слоёв.
- **Key Files / Directories:** `rules.md`, `ai_core/configs/*`, `super-parser-ultimate-pro/src`, `web/src/App.jsx`.
- **Expected Output:** Документированное понимание текущей структуры и зависимостей, список рисков.
- **Definition of Done:** Все основные директории подтверждены; нет критичных расхождений с `rules.md`.
- **Verification Checklist:**
  - `rules.md` — раздел «📂 Общая структура проекта».
  - `rules.md` — раздел «🧩 Что теперь нужно сделать».
- **Next Steps:** Приступить к фазе II после фиксации статуса в Compliance Check.

## Phase II — Документация (plan.md)
- **Description:** Поддержание и актуализация `plan.md`, детализация задач по фазам.
- **Tasks:**
  1. Разбить каждую фазу на подзадачи с привязкой к файлам.
  2. Добавить критерии качества и зависимости.
  3. Обновлять Compliance Check после завершения фаз.
- **Key Files:** `plan.md`, `rules.md`, релевантные документы в `super-parser-ultimate-pro/docs/sources`.
- **Expected Output:** Актуальная дорожная карта со статусами.
- **Definition of Done:** Все фазы описаны; присутствуют блоки Verification Checklist и Next Steps.
- **Verification Checklist:**
  - `rules.md` — раздел «🧭 Алгоритм работы Codex» (пункты 2–4).
- **Next Steps:** Старт фазы III после подтверждения фаз I–II.

## Phase III — Backend API (FastAPI)
- **Description:** Реализация FastAPI-бэкенда с эндпоинтами `/api/parser/run`, `/api/apify/callback`, `/api/helius/webhook`, `/api/alerts`, `/api/trade/confirm`.
- **Tasks:**
  1. Настроить приложение FastAPI (структура `backend/api` или отдельный сервис) согласно `rules.md`.
  2. Определить Pydantic-схемы запросов/ответов.
  3. Настроить интеграции: Redis, PostgreSQL, Groq, Apify.
  4. Реализовать логирование и обработку ошибок.
- **Key Files:** `backend/api/main.py` (или эквивалент), `backend/api/routes/*.py`, `.env.sample`.
- **Expected Output:** Рабочий FastAPI-сервис, покрытый тестами.
- **Definition of Done:** Все эндпоинты отвечают, тесты проходят, интеграции протестированы через mock.
- **Verification Checklist:**
  - `rules.md` — раздел «🧩 Что теперь нужно сделать» (Backend).
  - `super-parser-ultimate-pro/docs/sources/чтобы система не падала. Парсер +А.docx.txt` (описание API-пайплайнов).
- **Next Steps:** Передать события в Worker (фаза IV).

## Phase IV — Worker (Node)
- **Description:** Настройка очередей BullMQ, обработка Helius webhook и внешних адаптеров RugCheck/Sniffer.
- **Tasks:**
  1. Настроить Redis/BullMQ соединение.
  2. Реализовать обработчики задач (Helius, Apify, CEX).
  3. Настроить отправку алертов в FastAPI `/api/alerts`.
- **Key Files:** `backend/src/jobs/*.js`, `backend/src/adapters/*.js`, `backend/src/server/api.js`.
- **Expected Output:** Рабочие фоновые задачи с ретраями и мониторингом.
- **Definition of Done:** Очереди принимают и обрабатывают события без ошибок.
- **Verification Checklist:**
  - `rules.md` — раздел «Worker (Node)».
  - `super-parser-ultimate-pro/docs/sources/чтобы соединить Альфы2.docx.txt`.
- **Next Steps:** Интеграция с фронтендом через SSE/REST (фаза V).

## Phase V — Frontend (React PR112)
- **Description:** Перенос и фиксация интерфейса PR112, исправление ошибок, добавление SSE/REST интеграций.
- **Tasks:**
  1. Сверить `web/src/App.jsx` с PR112 эталоном.
  2. Реализовать Tabs, контексты, SSE-подписки.
  3. Настроить тесты и локальный билд (Vite).
- **Key Files:** `web/src/App.jsx`, `web/src/components/*`, `web/package.json`.
- **Expected Output:** Стабильный UI со всеми вкладками.
- **Definition of Done:** Все вкладки работают, сборка `npm run build` успешна.
- **Verification Checklist:**
  - `rules.md` — раздел «🧩 Что теперь нужно сделать» (Frontend).
  - `ui_addons_patch_v1/*.md` (если присутствуют).
- **Next Steps:** Связать AI Core через `/advice` (фаза VI).

## Phase VI — AI Core
- **Description:** Подключение цепочки Scout → Analyst → Judge и экспонирование `/advice`.
- **Tasks:**
  1. Изучить `ai_core/configs/*.json` и `README_TRIPLE_AI.md`.
  2. Настроить orchestrator (LLM Router, weights, risk policy).
  3. Подключить FastAPI и Worker к AI Core.
- **Key Files:** `ai_core/server/*`, `ai_core/configs/*`, FastAPI `/advice` маршруты.
- **Expected Output:** Доступ к AI цепочке с валидацией решений.
- **Definition of Done:** Эндпоинт `/advice` возвращает валидированные ответы.
- **Verification Checklist:**
  - `ai_core/docs/README_TRIPLE_AI.md`.
  - `rules.md` — раздел «AI Core».
- **Next Steps:** Инфраструктурная упаковка (фаза VII).

## Phase VII — Инфраструктура
- **Description:** Docker-compose для всех сервисов (ui, api, worker, redis, postgres, proxy) + TLS.
- **Tasks:**
  1. Создать `docker-compose.yml` в корне.
  2. Настроить образы/сборки, volume, сети.
  3. Добавить Caddy/Nginx конфигурацию с TLS.
- **Key Files:** `docker-compose.yml`, `deploy/`, `Caddyfile` или `nginx.conf`.
- **Expected Output:** `docker compose up -d` разворачивает систему.
- **Definition of Done:** Все контейнеры поднимаются без ошибок, сервисы доступны.
- **Verification Checklist:**
  - `rules.md` — раздел «Docker Compose».
  - `freelancer_task2.md` (если доступен) — архитектурные диаграммы.
- **Next Steps:** Настроить CI/CD (фаза VIII).

## Phase VIII — CI/CD
- **Description:** Автоматизация сборки, тестов и деплоя через GitHub Actions.
- **Tasks:**
  1. Создать workflow для backend/frontend тестов.
  2. Добавить шаги деплоя (Docker Registry / сервер).
  3. Настроить секреты и уведомления.
- **Key Files:** `.github/workflows/*.yml`.
- **Expected Output:** Автоматические проверки и деплой при push/PR.
- **Definition of Done:** Workflow проходит без ошибок, деплой запускается автоматически.
- **Verification Checklist:**
  - `rules.md` — раздел «CI/CD».
- **Next Steps:** Финальные e2e проверки (фаза IX).

## Phase IX — Финальные тесты
- **Description:** End-to-end прогон: парсинг → mint → алерт → лог.
- **Tasks:**
  1. Написать e2e сценарии (можно в Playwright/Postman/Newman).
  2. Проверить работу всех интеграций и алертов.
  3. Зафиксировать результаты в отчёте.
- **Key Files:** `tests/e2e/*`, логи сервисов.
- **Expected Output:** Протокол успешного прогона.
- **Definition of Done:** Все сценарии завершаются без критических ошибок.
- **Verification Checklist:**
  - `rules.md` — раздел «🧩 13. Контрольный чек-лист перед релизом».
- **Next Steps:** Перейти к релизу после подтверждения.

---

## Compliance Check
- *Phase I:* ☐ Pending
- *Phase II:* ☐ Pending
- *Phase III:* ☐ Pending
- *Phase IV:* ☐ Pending
- *Phase V:* ☐ Pending
- *Phase VI:* ☐ Pending
- *Phase VII:* ☐ Pending
- *Phase VIII:* ☐ Pending
- *Phase IX:* ☐ Pending

> Примечание: Некоторые источники из `.docx` представлены в текстовом виде в `super-parser-ultimate-pro/docs/sources`. Требуется дополнительное изучение перед началом соответствующих фаз.
