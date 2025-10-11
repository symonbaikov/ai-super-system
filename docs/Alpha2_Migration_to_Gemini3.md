# Переход с Apify на Gemini 3 — Инструкция

Это финальная инструкция по отключению Apify и переводу системы Alpha-2 на новую архитектуру с Gemini 3. После выполнения этих шагов можно будет протестировать работу системы в продакшне без ошибок.

---

## 1. Отключаем Apify

В файле `.env` удалить или закомментировать все переменные, связанные с Apify:

```bash
# APIFY_TOKEN=
# APIFY_ACTOR=
ENABLE_APIFY=false
```

В коде FastAPI удалить или закомментировать вызовы Apify (`apify:` или `apify_dataset`). Пайплайн `Apify → FastAPI → Candidate` будет заменён на новый маршрут `/api/intake/social`.

---

## 2. Новый приёмник для соц-сигналов

Добавить эндпоинт `/api/intake/social` в `main.py`:

```python
@app.post("/api/intake/social")
def intake_social(events: list[dict]):
    # events = [{source, author, text, ts, links[], contract, metrics{likes,retweets,replies}}]
    r.lpush("social:jobs", json.dumps(events))
    r.hincrby("metrics:latency", "parser_ms", 1)
    return {"ok": True, "accepted": len(events)}
```

Теперь любые пакеты данных можно отправлять POST-запросом на `/api/intake/social`. Эти события будут добавляться в очередь `social:jobs` и обрабатываться воркером.

---

## 3. Добавляем intake для Helius

Добавить webhook-эндпоинт `/api/intake/onchain` для получения данных от Helius:

```python
@app.post("/api/intake/onchain")
def intake_onchain(payload: dict):
    # Сохраняем в Redis список последних минтов
    r.lpush("helius:mints", json.dumps(payload))
    r.ltrim("helius:mints", 0, 200)
    return {"ok": True}
```

---

## 4. Подключаем Gemini 3

В файле `worker/index.js` заменить обработчик `ai_infer` на следующий код:

```javascript
new Worker('ai_infer', async job => {
  const { prompt } = job.data;
  const resp = await fetch("https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key="+process.env.GEMINI_API_KEY, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contents: [{ parts: [{ text: prompt }]}] })
  });
  const data = await resp.json();
  const text = data?.candidates?.[0]?.content?.parts?.[0]?.text || "No response";
  return { text, provider:"gemini3", model:"gemini-2.5-flash" };
});
```

Теперь все запросы `/api/ai/infer` будут выполняться через Gemini 3, без участия Apify.

---

## 5. Проверка после изменений

### Пересобрать контейнеры

```bash
docker compose up -d --build
```

### Проверить intake соц-сигналов

```bash
curl -X POST http://localhost:8080/api/intake/social \
  -H "Content-Type: application/json" \
  -d '[{"source":"twitter","author":"@test","text":"New coin soon","ts":"2025-10-10T12:00:00Z"}]'
```

### Проверить очередь

```bash
redis-cli LLEN social:jobs
```

### Проверить работу Gemini 3

```bash
curl -X POST http://localhost:8080/api/ai/infer \
  -H "Content-Type: application/json" \
  -d '{"provider":"gemini","model":"gemini-3","prompt":"Summarize market"}'
```

---

## 6. Ожидаемый результат

✅ Apify полностью отключён  
✅ Данные приходят через `/api/intake/social` и `/api/intake/onchain`  
✅ Gemini 3 обрабатывает запросы через `/api/ai/infer`  
✅ Все остальные эндпоинты (`/api/metrics`, `/api/helius/mints`, `/api/whales`, `/api/alerts`) работают без изменений

📅 После этого можно протестировать систему в продакшне: проверить сигналы, графики и китов.