# Super Parser — ULTIMATE (Core only, no web)

**Готов к интеграции**: Golib (3 модели) через `/advice`, веб-интерфейс через `/stream` (SSE) и REST `/signals/analyze`.
**Встроено**: очереди (Redis/BullMQ или RabbitMQ), метрики (Prometheus), ошибки (Sentry), on-chain (Solana @web3.js, EVM viem), сигнальный движок (RSI/EMA/SMA/BB + pump/dump/whales стуб).

## Быстрый старт
```bash
npm i
cp .env.sample .env   # заполни переменные
node src/index.js
# Метрики: http://localhost:${METRICS_PORT}/metrics
# Стрим сигналов: http://localhost:${PORT}/stream
```

## API
- `POST /signals/analyze` → `{candles:[{t,o,h,l,c,v}], options?}` → `{signals:[...]}`
- `POST /advice` → прокси к Golib (единая точка для 3 моделей)
- `GET /status` → ping
- `GET /stream` → SSE поток сигналов (для отрисовки поверх графика во фронте)

## Подключения
- **Очереди**: `QUEUE_BACKEND=redis|rabbitmq` (BullMQ/AMQP)
- **On-chain**: `RPC_URL` (Solana), Helius API ключ в `HELIUS_API_KEY`
- **EVM**: viem-провайдер (добавь RPC)
- **Мониторинг**: Prometheus (prom-client), Sentry (@sentry/node)

## Signals движок (коротко)
- Heuristics: Pump (Δ% + RSI), Dump (Δ% + RSI), BB bounce, EMA20/Сross SMA50 → Entry/Exit
- Выводит аннотации: `{kind, t, price, strength, meta}` — готово для рисования на графике.
- Добавляй модели свечей/фичи: объёмные всплески, z-score, whale_in и т.д.

## Дальше
- Подключить реальные источники CEX/DEX цен в `adapters/price/cex.js`
- Реализовать whale-события (Helius/QuickNode) и передавать их как `whale_in` сигналы
- Привязать `/advice` к бэку Голиба (3 модели) — см. `.env.sample`
```

## FastAPI слой (Phase III)
- Запуск: `python -m backend.api` (порт по умолчанию `API_PORT` из `.env`).
- Маршруты:
  - `POST /api/parser/run` — ставит задачу парсинга в очередь и создаёт запись в `candidates`.
  - `POST /api/apify/callback` — принимает callback Apify и прокладывает события в очередь.
  - `POST /api/helius/webhook` — подписка на события Helius (подпись через `HELIUS_WEBHOOK_SECRET`).
  - `POST /api/alerts` / `GET /api/alerts` — CRUD алертов + публикация в Redis канал.
  - `POST /api/trade/confirm` — фиксирует подтверждения сделок.
- Зависимости: `backend/requirements.txt` (FastAPI, SQLAlchemy async, Redis, httpx).
- Для миграции схемы БД используем автосоздание при старте (или позднее Alembic).

## BullMQ worker
- Воркеры запускаются вместе с Express-сервисом через `startWorkers()` (смотри `src/worker/index.js`).
- Очереди FastAPI (`parser:run`, `apify:dataset`, `helius:events`) бриджатся через Redis в BullMQ и обрабатываются обработчиками в `src/worker/handlers/*`.
- Для отправки алертов используется REST `/api/alerts` FastAPI (`FASTAPI_URL` в `.env`).
- Поддерживаются проверки RugCheck/Sniffer (настройка через `RUGCHECK_API_URL`, `SNIFFER_API_URL`).
