# Alpha‑2 — Страница «Киты» (React UI)

Боевой каркас страницы для централизованного контроля за «китами» и 5 сценариями:
1) Pre‑Pool Tester
2) Whale Cluster + CopyNet
3) Whale + Social Burst
4) Big Swap Hunter
5) LP & Route Manip

## Структура
```
alpha2-whales-page/
  └─ src/pages/WhalesPage.tsx
```

## Интеграция
1. Скопируйте `src/pages/WhalesPage.tsx` в ваш React‑проект.
2. Импортируйте компонент в роутинг, например:
```tsx
import WhalesPage from "@/pages/WhalesPage";
// ...
<Route path="/whales" element={<WhalesPage/>} />
```
3. Убедитесь, что подключён TailwindCSS или адаптируйте классы.
4. Подключите реальные источники в хендлерах (помечены `// TODO`):
   - Birdeye, GMGN, Solscan, RugCheck, SolSniffer, GROQ, Apify (+ Helius/RPC при наличии).
   - Поднимите Rule Engine (REST/WS) и передавайте/получайте кандидатов в формате `CandidateDto`.

## Шаблоны JSON
В компоненте доступны кнопки «Шаблоны JSON» для экспорта:
- `rules.template.json` — набор правил (8 шт).
- `whales.template.json` — список китов с метками.

Готово для быстрой вставки без переписывания ядра.
