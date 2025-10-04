# 🧠 Super Parser AI — RULES.md

## 📘 Описание проекта
**Super Parser AI** — это интегрированная система мониторинга криптосигналов и мем-токенов, объединяющая:
- анализ социальных сигналов (X/Twitter, Telegram);
- мониторинг on-chain активности (Helius, QuickNode);
- отслеживание листингов (CEX Radar);
- систему принятия решений на основе трёх ИИ-модулей (Scout → Analyst → Judge);
- визуальный интерфейс с локальным TradeView-графиком, алертами и API-ключами.

## 📂 Общая структура проекта

super-parser-ai/
├── ai_core/ # AI_SUPER_SYSTEM_merged_v5 (ИИ-ядро)
│ ├── configs/
│ │ ├── llm_router.json
│ │ ├── ai_supercenter.json
│ │ ├── profiles_config.json
│ │ ├── ai_global_rules.json
│ │ ├── ai_fine_filters.json
│ │ ├── ai_weights_v2.json
│ │ ├── risk_policy.json
│ │ ├── config.yaml
│ └── docs/
│ ├── README_TRIPLE_AI.md
│ ├── addons_api_patch.md
│ └── ui_spec.md
│
├── backend/ # super-parser-ultimate-pro (сервер, пайплайны, джобы)
│ ├── src/
│ │ ├── adapters/
│ │ │ ├── price/cex.js
│ │ │ └── chain/solana.js
│ │ ├── pipelines/
│ │ │ ├── ingest_onchain.js
│ │ │ └── ingest_cex.js
│ │ ├── jobs/
│ │ │ ├── detect_listings.js
│ │ │ └── whales.js
│ │ ├── server/
│ │ │ ├── sse.js
│ │ │ └── api.js
│ │ ├── monitoring/
│ │ │ ├── prometheus.js
│ │ │ └── sentry.js
│ │ ├── signals/
│ │ │ ├── engine.js
│ │ │ └── schema.js
│ │ └── index.js
│ ├── configs/
│ │ ├── rules.json
│ │ ├── platforms.json
│ │ ├── accounts.json
│ │ └── derived/
│ ├── docker-compose.yml
│ ├── .env.sample
│ ├── package.json
│ └── README.md
│
└── web/ # React UI (последний веб интерфейс с Хелиус PR111)
├── src/
│ ├── App.jsx
│ └── components/
├── package.json
└── README.md
---
## ⚙️ 1. Установка окружения

### 1.1 Требования
- Node.js 20+
- Docker + Docker Compose
- Redis
- (Опционально) RabbitMQ
- Git / VS Code

### 1.2 Подготовка проекта
```bash
git clone <repo_url> super-parser-ai
cd super-parser-ai

⚙️ 2. Настройка .env

Создай .env в папке backend/ по образцу .env.sample:
HELIUS_API_KEY=<твой ключ>
RPC_URL=https://mainnet.helius-rpc.com/?api-key=<твой ключ>
QUICKNODE_URL=https://<твой>.quicknode.com
REDIS_URL=redis://redis:6379

GOLIB_URL=http://localhost:9200/ai
GOLIB_KEY=<секретный_ключ_ИИ>

BINANCE_API_KEY=<...>
OKX_API_KEY=<...>
BYBIT_API_KEY=<...>
MEXC_API_KEY=<...>
GATE_API_KEY=<...>

QUEUE_BACKEND=redis
PORT=8811

🐳 3. Docker-сервисы
3.1 Поднятие Redis и RabbitMQ

cd backend
docker compose up -d redis
# если нужно RabbitMQ:
docker compose up -d rabbitmq


⚡ 4. Установка зависимостей
cd backend
npm install

Фронтенд:
cd ../web
npm install


🧩 5. Подключение реальных источников данных
5.1 Helius / QuickNode

Файл: backend/src/pipelines/ingest_onchain.js

Заменить:
function toCandle() { /* demo */ }

на реальный вызов:
import axios from "axios";

async function toCandle(addr) {
  const { data } = await axios.get(
    `${process.env.HELIUS_API_URL}/v0/addresses/${addr}/transactions?api-key=${process.env.HELIUS_API_KEY}`
  );
  return transformToCandles(data);
}


5.2 CEX API

Файл: backend/src/adapters/price/cex.js

Реализовать:
export async function getListings(ticker) {
  // пример для Binance
  const res = await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${ticker}`);
  return await res.json();
}

export async function getPrice(exchange, ticker) {
  // switch(exchange) -> return нужный API call
}

🧠 6. Интеграция ИИ SuperCenter
6.1 Подключить маршруты

Файл: backend/src/server/api.js

Добавить:
import axios from "axios";

app.post("/advice", async (req, res) => {
  const { query } = req.body;
  const result = await axios.post(
    `${process.env.GOLIB_URL}/route`,
    { input: query },
    { headers: { "Authorization": `Bearer ${process.env.GOLIB_KEY}` } }
  );
  res.json(result.data);
});

6.2 Включить цепочку M1→M2→M3

Файл: ai_core/configs/ai_supercenter.json
Убедись, что прописано:

{
  "chain": ["scout", "analyst", "judge"],
  "routing": {
    "scout": "groq-8b",
    "analyst": "groq-70b",
    "judge": "mixtral-8x7b"
  }
}

🌐 7. Запуск систем
7.1 Backend
cd backend
node src/index.js

Проверка:

Метрики: http://localhost:9110/metrics
Поток сигналов: http://localhost:8811/stream

7.2 Frontend
cd web
npm run dev

Фронт откроется по адресу http://localhost:5173
(или http://localhost:3000, в зависимости от Vite/CRA).

🧾 8. Проверка работы

В UI открой вкладку «Аккаунты»:

загрузить списки Twitter/TG аккаунтов (CSV или JSON);

задать интервал парсинга (5/15/30/60 мин);

добавить API-ключи Helius, Groq, Nansen и др.

Запустить:

вкладка Signals — поток сигналов;

Helius AR — поиск оригинальных минтов;

CEX Radar — мониторинг первых листингов.

Проверить Tradeview:

нажать “Сигналы” — должны появиться BUY/SELL/WHALE/HYPE.

Вкладка Logs — смотреть состояние парсера и ИИ.

🧰 9. Dev-тесты и CI
Юнит-тесты
npm test

Самотесты фронта

Вкладка Selftests — встроенные проверки:

parseTickers ✅

uniqueHypeWords ✅

genSeries ✅

CI (опционально)

Создай .github/workflows/deploy.yml:
name: Deploy
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd backend && npm i && npm test

🧩 10. Архитектурная логика
Компонент	Назначение
AI Core	Три ИИ-модуля анализируют соцсигналы, фильтры, риски и принимают решение.
Backend	Сбор, трансформация и маршрутизация данных; отправка SSE-потоков фронту.
Frontend	Интерфейс мониторинга: сигналы, графики, Helius, CEX Radar, алерты.
Redis	Кэш сигналов, метрики, алерты.
Helius / QuickNode	Источники on-chain событий.
CEX API	Цены, листинги.
Groq / Mixtral	LLM-движок (ИИ-логика).

🔒 11. Безопасность и политика риска
Файл: ai_core/configs/risk_policy.json

Основные правила:

Любой токен с mint/freeze/blacklist = true → red zone;

LP не залочен → warning;

Киты <3 / ликвидность <20k$ → skip trade;

Только Scout может поднять период обновления до 1 минуты;

Judge имеет приоритет в policy-gate.

🚀 12. Развёртывание в продакшн
docker build -t super-parser-ai .
docker compose up -d


Frontend можно собрать отдельно:
cd web
npm run build
и отдать через Nginx / Vercel / Cloudflare Pages.


📄 13. Контрольный чек-лист перед релизом
.env заполнен и ключи рабочие
Redis поднят
Helius API отвечает
CEX адаптер возвращает цены
ИИ цепочка отвечает на /advice
Вкладки UI активны: Signals, Helius, CEX Radar, Tradeview
Экспорт JSON/CSV работает
Selftests → PASS


🏁 Результат

После выполнения всех пунктов система Super Parser AI будет полностью функциональна:

собирает сигналы из соцсетей и on-chain источников,

обрабатывает через тройной ИИ,

отображает в интерактивном интерфейсе с графиками и алертами.

Автор:
Super Parser AI v5.111
Helius PR / Groq / Mixtral Integration
Дата: 2025-10-04

🧩 Что теперь нужно сделать (обновлённый план rules.md):

Взять App.jsx из PR112 (последний документ) как основу фронта.

Проверить ошибки рендера, импортов (React, recharts и т.д.).

Добавить Tabs-компоненты и useContext как в коде.

Собрать проект с Vite.

Бэкенд на FastAPI:

Создать /api/parser/run, /api/apify/callback, /api/helius/webhook, /api/alerts и /api/trade/confirm.

Реализовать прокси к Groq и Apify (через их токены).

Настроить Redis-очереди для задач (BullMQ-воркер слушает события).

Worker (Node):

Подключить Helius Webhooks (mint, poolCreated, addLiq, largeTx).

Добавить RugCheck/Sniffer запросы.

Отправлять алерты в FastAPI через POST /api/alerts.

Интеграции:

Apify → Twitter/TG акторы;

Groq → LLM анализ сигналов;

Helius → on-chain события;

QuickNode → фолбэк по ценам и tx;

Jupiter/Jito → торговая симуляция (опционально).

БД PostgreSQL:

Таблицы: alerts, candidates, logs, settings.

Docker Compose:

Собрать 6 контейнеров (ui, api, worker, redis, postgres, proxy);

Убедиться, что docker compose up -d запускает без ошибок.

TLS + Deploy:

Через Caddy (или Nginx + Certbot);

Автодеплой через GitHub Actions.

ВАЖНО! Заходи и смотри текстовые файлы. Там важные детали по реализации. Каждый шаг сравнивай с тем что надо реализовать