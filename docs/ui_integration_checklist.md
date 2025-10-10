# Alpha-2 UI Integration Checklist

**Цель:** быстро и без расхождений интегрировать backend (FastAPI + BullMQ + Redis + Postgres) с UI Alpha-2 (PR111 + патч-добавки). Ниже — минимально необходимый контракт эндпоинтов, тестовые команды и критерии приёмки.

## 1. Базовые эндпоинты и контракт JSON

### GET /api/metrics/latency-usage

```json
{
  "apify_ms": <int>,
  "helius_ms": <int>,
  "parser_ms": <int>,
  "apify_credits_used": <int>,
  "groq_credits_used": <int>,
  "suggestion": "<string>"
}
```

- **Статус 2025-10-08:** ✅ 200 (данные возвращаются корректно)

### POST /api/cex-radar/search

**Request:**
```json
{
  "query": "<ticker|mint|contract>"
}
```
- **Статус 2025-10-08:** ✅ 200 (jobId выдаётся)

**Response:**
```json
{
  "jobId": "<string>"
}
```

### GET /api/cex-radar/result?jobId=...

```json
[
  {
    "exchange": "Binance",
    "date": "YYYY-MM-DD",
    "time": "HH:MM:SS",
    "team": "anon|doxxed|unknown",
    "url": "https://birdeye.so/token/<mint>?chain=solana",
    "social": {
      "tw_1h": <int>,
      "tg_online": <int>
    }
  }
]
```
- **Статус 2025-10-08:** ✅ 200 (результат доступен для ранее выданного jobId)

### GET /api/helius/mints

```json
[
  {
    "name": "$DOGE99",
    "mint": "So1...",
    "team": "anon|doxxed|unknown",
    "original": true,
    "safe": true,
    "hasTw": true,
    "sol": <float>,
    "ts": "YYYY-MM-DD HH:MM:SS"
  }
]
```
- **Статус 2025-10-08:** ✅ 200 (возвращает список минтов)

### POST /api/whales/scan

**Response:**
```json
{
  "jobId": "<string>"
}
```
- **Статус 2025-10-08:** 🟡 202 Accepted (job ставится в очередь `sp:queue:whales:scan`)

### GET /api/whales/top3?jobId=...

```json
[
  {
    "mint": "So1...",
    "name": "$TRUMP42",
    "whales": <int>,
    "sol_sum": <float>,
    "safety": {
      "rugcheck": "ok|warn|bad",
      "solsniffer": "ok|warn|bad"
    },
    "hype": {
      "tw_1h": <int>,
      "tg_1h": <int>
    },
    "links": {
      "birdeye": "https://birdeye.so/token/So1...?chain=solana"
    }
  }
]
```

> Статус 2025-10-08: эндпоинты `/api/whales/scan` и `/api/whales/top3` реализованы в `backend/api/routes/integration.py`. Задачи складываются в Redis (`sp:queue:whales:scan`), обработчик воркера `backend/src/worker/handlers/whales-scan.js` формирует топ-3 и кеширует ответ на 10 минут по ключу `sp:whales:result:<jobId>`. Пока результат не готов, API возвращает `202 Pending`.
- **Статус 2025-10-08:** ✅ 200 (после обработки воркером результат доступен)

### POST /api/alerts/enable

**Request:**
```json
{
  "mint": "So1...",
  "msar": <float>,
  "volume": <int>,
  "liquidity": <int>,
  "enabled": true
}
```

**Response:**
```json
{
  "ok": true
}
```
- **Статус 2025-10-08:** ✅ 200 (алерт включается)

### GET /api/alerts

```json
[
  {
    "mint": "So1...",
    "msar": 0.6,
    "volume": 5000,
    "liquidity": 20000,
    "enabled": true
  }
]
```
- **Статус 2025-10-08:** ✅ 200 (список алертов отдаётся)

### POST /api/ai/infer

**Request:**
```json
{
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "prompt": "...",
  "strategyId": "S1"
}
```

**Response:**
```json
{
  "text": "...",
  "tokens": {
    "input": <int>,
    "output": <int>
  },
  "cost_usd": <float>
}
```
- **Статус 2025-10-08:** ✅ 200 (ответ mock Gemini возвращается)

### GET /api/signals (опционально)

Выдаёт список кандидатов в формате UI-вкладки «Сигналы» (см. Mapping ниже).
- **Статус 2025-10-08:** ✅ 200 (берёт свежие записи из `candidates`, преобразует метаданные для UI)

## 2. Mapping Candidate → UI «Сигналы»

Привести Postgres-модель Candidate к формату, который ожидает таблица «Сигналы».

**UI ожидает поля:**
```json
{
  "id": "<string>",
  "word": "<string>",
  "isOG": <bool>,
  "type": "слово|токен",
  "detectedAt": "YYYY-MM-DD HH:MM",
  "source": "Twitter|Telegram|Helius",
  "author": "@handle|source",
  "link": "<url>",
  "tweetCount": <int>,
  "communitySize": <int>,
  "nameChanges": <int>,
  "spamScore": <float 0..1>,
  "devTeam": "doxxed|anon|unknown",
  "communityLink": "<url>",
  "contract": "<mint|contract>",
  "chain": "Solana",
  "safety": {
    "noMint": <bool>,
    "burnLP": <bool>,
    "blacklist": <bool>
  },
  "summary": "<краткое описание>"
}
```

## 3) Redis-ключи / очереди

**Минимальный набор ключей:**
- `cexradar:jobs` (list) — буфер LPUSH от API до BullMQ
- `cexradar:result:<jobId>` — JSON результата
- `whales:jobs` (list), `whales:result:<jobId>` — топ-3 по китам
- `helius:mints` (list) — поток последних минтов (worker → API)
- `alerts:rules` (hash) — включённые правила
- `metrics:latency` (hash) — apify_ms, helius_ms, parser_ms, кредиты и suggestion

## 4. Тестовые команды (curl)

### 1. Метрики:
```bash
curl -s http://localhost:8080/api/metrics/latency-usage | jq
```

### 2. CEX Radar:
```bash
JOB=$(curl -s -X POST http://localhost:8080/api/cex-radar/search -H 'Content-Type: application/json' -d '{"query":"OPTIMUS"}' | jq -r .jobId)
curl -s "http://localhost:8080/api/cex-radar/result?jobId=$JOB" | jq
```

### 3. Helius mints:
```bash
curl -s http://localhost:8080/api/helius/mints | jq
```

### 4. Whales top3:
```bash
JOB=$(curl -s -X POST http://localhost:8080/api/whales/scan | jq -r .jobId)
curl -s "http://localhost:8080/api/whales/top3?jobId=$JOB" | jq
```

### 5. Alerts enable/list:
```bash
curl -s -X POST http://localhost:8080/api/alerts/enable -H 'Content-Type: application/json' -d '{"mint":"So1...","msar":0.6,"volume":5000,"liquidity":20000,"enabled":true}' | jq
curl -s http://localhost:8080/api/alerts | jq
```

### 6. AI infer:
```bash
curl -s -X POST http://localhost:8080/api/ai/infer -H 'Content-Type: application/json' -d '{"provider":"gemini","model":"gemini-2.5-flash","prompt":"test"}' | jq
```

## 5. Критерии приёмки (E2E)

- ✓ В UI отображаются задержки/кредиты и строка «suggestion» (панель LatencyUsagePanel)
- ✓ CEX Radar ищется по query, выдаёт выровненную таблицу и social-метрики
- ✓ Helius / Whales возвращают данные в нужном формате; алерты включаются/видны
- ✓ /api/signals (если используется) выдает кандидатов, и в «Сигналы» есть очищенные хайп-слова
- ✓ Очереди BullMQ пустеют (LLEN=0), задания помечаются выполненными, метрики обновляются

## 6. Docker & ENV

**docker-compose.flowith.yml** (минимум): redis, api (uvicorn), worker (node).

**ENV** (пример .env.example):
```env
REDIS_URL=redis://redis:6379/0
POSTGRES_URL=postgresql://user:pass@postgres:5432/db
GEMINI_BASE_URL=https://api.flowith.io/v1/gemini
GEMINI_API_KEY=...
HELIUS_API_KEY=...
BIRDEYE_API_KEY=...
RUGCHECK_API_KEY=...
GROQ_API_KEY=...
```

## 7. CI/CD

**GitHub Actions (рекомендации):**
- Lint + Tests (pytest + node tests)
- Build containers
- Deploy (по тэгу/branch)

**Secrets:** GEMINI_API_KEY, HELIUS_API_KEY, REDIS_URL, POSTGRES_URL и т.д.

## 8. Примечания

- `/api/ai/infer` — провайдер-агностичный (gemini/groq/openai). Возвращайте text + учёт токенов/cost.
- Если поля не готовы из реальных источников — временно используйте демо-заглушки, но строго в указанном JSON-формате.
- Для «копировать mint» и «Открыть в Birdeye» UI уже содержит готовые компоненты (из патча).
