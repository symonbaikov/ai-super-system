import React, { useMemo, useRef, useState } from "react";

/**
 * Alpha‑2 — Страница «Киты» (боевой каркас UI)
 * -------------------------------------------------
 * Цель: единый центр управления 5 режимами детекции китов + панель кандидатов.
 *
 * Особенности:
 *  - Верхняя панель: Start/Stop, Сохранить профиль фильтров, Глобальные фильтры (модалка),
 *    Импорт проверенных китов (whales.json) и правил (rules.json), Просмотр правил.
 *  - Левая колонка: 5 команд/режимов с «тонкими настройками» (ползунки + тумблеры).
 *  - Правая колонка: лента «Кандидаты» (карточки) + таймлайн выбранного токена + кнопки действий.
 *  - Кнопки быстрых ссылок: Birdeye, GMGN, Solscan, RugCheck, SolSniffer; копирование mint.
 *  - Экспорт шаблонов JSON (rules.json, whales.json) одним кликом.
 *
 * Примечания для интеграции:
 *  - Все API‑интеграции помечены как TODO (см. handlers). Их должен подключить фрилансер.
 *  - Форматы DTO кандидатов и правил — см. константы TEMPLATE_RULES_JSON, TEMPLATE_WHALES_JSON и тип CandidateDto.
 *  - Валидация импорта правил и китов присутствует (минимальная) + предпросмотр.
 *  - В правой колонке предусмотрены ползунки SL/TP и чекбокс Auto‑BUY (исполнять только если risk‑gates пройдены).
 *  - Лёгкий, «чистый» Tailwind без сторонних компонентов: надёжно рендерится.
 */

// ===== Типы =====

type CandidateDto = {
  mint: string;
  symbol: string;
  scenario: "PrePool" | "WhaleCluster" | "SocialWhale" | "BigSwap" | "LPManip";
  scores: { priority: number; whale?: number; social?: number; prepool?: number; lp?: number };
  facts: {
    whales?: number;
    followers_5m?: number;
    prepool?: boolean;
    route_consistency?: number;
    lp_risk?: "low" | "medium" | "high";
  };
  links: { birdeye?: string; gmgn?: string; solscan?: string; rugcheck?: string; solsniffer?: string };
  timestamps?: { first_seen?: string; last_event?: string };
};

// ===== Шаблоны JSON для импорта/экспорта =====

export const TEMPLATE_WHALES_JSON = {
  version: 1,
  as_of: "2025-09-30T00:00:00Z",
  labels: ["market_maker", "early_minter", "clean_whale"],
  whales: [
    { address: "SoLx...A1", labels: ["clean_whale"], weight: 0.9 },
    { address: "SoLx...B2", labels: ["market_maker"], weight: 0.7 }
  ]
};

export const TEMPLATE_RULES_JSON = {
  rules: [
    // 1) PrePool Tester — тестовые/скрытые переводы до пула
    {
      rule_id: "prepool_v1",
      name: "Pre-Pool Tester",
      inputs: ["onchain.transfers"],
      params: { time_window_min: 30, min_test_transfers: 5, min_unique_addresses: 4, min_test_value_sol: 0.01 },
      conditions: [
        { type: "aggregate", field: "test_transfer_count", op: ">=", value: "params.min_test_transfers" },
        { type: "aggregate", field: "unique_from_addresses", op: ">=", value: "params.min_unique_addresses" },
        { type: "aggregate", field: "avg_test_value_sol", op: ">=", value: "params.min_test_value_sol" }
      ],
      actions: [{ type: "emit_candidate", scenario: "PrePool", priority_weight: 0.6 }]
    },

    // 2) Whale Cluster + CopyNet — ≥N китов + всплеск копитрейдеров
    {
      rule_id: "whale_cluster_v1",
      name: "Whale Cluster Detector",
      inputs: ["onchain.transfers", "onchain.swaps", "social.events"],
      params: {
        time_window_min: 10,
        min_whales: 5,
        whale_value_sol: 50,
        min_followers: 100,
        follower_window_sec: 300
      },
      conditions: [
        { type: "aggregate", field: "unique_whale_addresses", op: ">=", value: "params.min_whales" },
        { type: "aggregate", field: "followers_in_window", op: ">=", value: "params.min_followers" }
      ],
      actions: [{ type: "emit_candidate", scenario: "WhaleCluster", priority_weight: 0.8 }]
    },

    // 3) Whale + Social Burst — ончейн + соц-взрыв
    {
      rule_id: "social_whale_v1",
      name: "Whale + Social Burst",
      inputs: ["onchain.transfers", "social.events"],
      params: { social_window_min: 15, social_spike_multiplier: 5, min_sources: 2, min_sentiment: 0.2 },
      conditions: [
        { type: "flag", field: "on_chain_whale_event", eq: true },
        { type: "aggregate", field: "social_burst_score", op: ">", value: 0.5 },
        { type: "aggregate", field: "verified_sources", op: ">=", value: "params.min_sources" },
        { type: "aggregate", field: "sentiment", op: ">= ", value: "params.min_sentiment" }
      ],
      actions: [{ type: "emit_candidate", scenario: "SocialWhale", priority_weight: 0.7 }]
    },

    // 4) Big Swap Hunter — крупные свопы / маршрутная консистентность / priority fees
    {
      rule_id: "big_swap_v1",
      name: "Big Swap Hunter",
      inputs: ["onchain.swaps"],
      params: { min_swap_sol: 5, route_consistency_min: 0.8, time_window_sec: 90, min_price_impact: 0.01 },
      conditions: [
        { type: "aggregate", field: "swap_value_sol", op: ">=", value: "params.min_swap_sol" },
        { type: "aggregate", field: "route_consistency", op: ">=", value: "params.route_consistency_min" },
        { type: "aggregate", field: "expected_price_impact", op: ">=", value: "params.min_price_impact" }
      ],
      actions: [{ type: "emit_candidate", scenario: "BigSwap", priority_weight: 0.55 }]
    },

    // 5) LP & Route Manip — манипуляции с LP/маршрутами ликвидности
    {
      rule_id: "lp_manip_v1",
      name: "LP & Route Manipulation",
      inputs: ["onchain.lp_events"],
      params: { lp_move_percent: 30, lp_moves_24h: 2 },
      conditions: [
        { type: "aggregate", field: "lp_move_percent", op: ">=", value: "params.lp_move_percent" },
        { type: "aggregate", field: "lp_moves_24h", op: ">=", value: "params.lp_moves_24h" }
      ],
      actions: [{ type: "emit_candidate", scenario: "LPManip", priority_weight: 0.5 }]
    },

    // 6) Anti‑Rug — жёсткие ворота безопасности
    {
      rule_id: "anti_rug_v1",
      name: "Anti‑Rug Gate",
      inputs: ["sec.rugcheck", "sec.solsniffer", "onchain.lp_events"],
      params: { max_risk: 0.6, require_lp_lock_or_burn: true, max_dev_supply_pct: 30 },
      conditions: [
        { type: "aggregate", field: "rug_risk", op: "<=", value: "params.max_risk" },
        { type: "gate", field: "lp_locked_or_burned", eq: "params.require_lp_lock_or_burn" },
        { type: "aggregate", field: "dev_supply_pct", op: "<=", value: "params.max_dev_supply_pct" }
      ],
      actions: [{ type: "set_gate", key: "risk_ok", value: true }]
    },

    // 7) FollowNet — всплеск копитрейдеров (поведенческий «отпечаток»)
    {
      rule_id: "copynet_v1",
      name: "Copy Trader Surge",
      inputs: ["onchain.swaps"],
      params: { follower_window_sec: 300, min_followers: 100, bot_pattern_similarity_max: 0.9 },
      conditions: [
        { type: "aggregate", field: "followers_in_window", op: ">=", value: "params.min_followers" },
        { type: "aggregate", field: "bot_signature_similarity", op: "<=", value: "params.bot_pattern_similarity_max" }
      ],
      actions: [{ type: "emit_tag", tag: "CopyNet" }]
    },

    // 8) TradeLimit — безопасные лимиты авто‑покупок
    {
      rule_id: "trade_limit_v1",
      name: "Trade Limits",
      inputs: ["decision"],
      params: { max_auto_buy_sol: 0.5, max_positions: 3 },
      conditions: [
        { type: "aggregate", field: "current_positions", op: "<", value: "params.max_positions" },
        { type: "aggregate", field: "auto_buy_amount_sol", op: "<=", value: "params.max_auto_buy_sol" }
      ],
      actions: [{ type: "set_gate", key: "trade_limit_ok", value: true }]
    }
  ]
};

// ===== Вспомогательные утилиты =====

function downloadJSON(filename: string, data: any) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function classNames(...lst: Array<string | false | null | undefined>) {
  return lst.filter(Boolean).join(" ");
}

// ===== Главный компонент страницы «Киты» =====

export default function WhalesPage() {
  // Глобальные состояния
  const [running, setRunning] = useState(false);
  const [autoBuy, setAutoBuy] = useState(false);

  // Профиль настроек 5 режимов (тонкие фильтры)
  const [prepool, setPrepool] = useState({ minTestTransfers: 5, minUniqueAddresses: 4, windowMin: 30, minTestValue: 0.01, ignoreDevBlacklist: true, followMinter: true });
  const [cluster, setCluster] = useState({ whaleThresholdSol: 50, minWhales: 5, windowMin: 10, minFollowers: 100, requireJito: false, excludeBots: true });
  const [social, setSocial] = useState({ multiplier: 5, windowMin: 15, minSources: 2, verifiedOnly: true, ignoreAdsBelow: 0.6 });
  const [bigswap, setBigswap] = useState({ minSwapSol: 5, routeConsistency: 0.8, windowSec: 90, minImpact: 0.01, requirePriorityFees: false, ignoreArbBelow: 0.003 });
  const [lpmanip, setLpmanip] = useState({ lpMovePct: 30, lpMoves24h: 2, requireLockOrBurn: true, maxRugRisk: 0.6 });

  // Глобальные фильтры (модалка)
  const [showFilters, setShowFilters] = useState(false);
  const [globalFilters, setGlobalFilters] = useState({
    whitelist: [] as string[],
    blacklist: [] as string[],
    minLiquidityUsd: 5000,
    minVol: { m5: 1000, m15: 2500, h1: 5000 },
    minHolders: 50,
    maxTop10Pct: 80,
    allowedDex: ["Raydium", "Orca"],
    maxRugRisk: 0.6,
    stopWords: ["airdrop", "giveaway"],
    timeWindows: { day: true, night: true }
  });

  // Импорт whales.json и rules.json
  const [whalesImport, setWhalesImport] = useState<any | null>(null);
  const [rulesImport, setRulesImport] = useState<any | null>(null);
  const whalesInputRef = useRef<HTMLInputElement>(null);
  const rulesInputRef = useRef<HTMLInputElement>(null);

  // Кандидаты (демо‑список до интеграции API)
  const [candidates, setCandidates] = useState<CandidateDto[]>([
    {
      mint: "8f3a...",
      symbol: "FROGME",
      scenario: "WhaleCluster",
      scores: { priority: 0.82, whale: 0.9, social: 0.6, prepool: 0.4, lp: 0.2 },
      facts: { whales: 7, followers_5m: 213, prepool: true, route_consistency: 0.81, lp_risk: "low" },
      links: { birdeye: "https://birdeye.so/token/8f3a", gmgn: "https://gmgn.ai/8f3a", solscan: "https://solscan.io/token/8f3a" }
    }
  ]);

  const latencyInfo = useMemo(() => ({ apifyMs: 180, solscanMs: 220, birdeyeMs: 140, gmgnMs: 190, groqMs: 120 }), []);
  const quotas = useMemo(() => ({ apify: { used: 32, limit: 1000 }, groq: { used: 12, limit: 500 }, birdeye: { used: 40, limit: 2000 } }), []);

  // ====== Handlers / TODO: интеграции ======

  const handleStart = () => {
    // TODO: запуск стримов (Helius/Solscan pull, Apify соц‑парсеры)
    setRunning((v) => !v);
  };

  const handleSaveProfile = () => {
    const profile = { prepool, cluster, social, bigswap, lpmanip, globalFilters, autoBuy };
    downloadJSON("whales_profile.json", profile);
  };

  const onImportWhales = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    try {
      const json = JSON.parse(text);
      if (!json.whales || !Array.isArray(json.whales)) throw new Error("Invalid whales.json format");
      setWhalesImport(json);
    } catch (err) {
      alert("Ошибка импорта whales.json: " + (err as Error).message);
    }
  };

  const onImportRules = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    try {
      const json = JSON.parse(text);
      if (!json.rules || !Array.isArray(json.rules)) throw new Error("Invalid rules.json format");
      setRulesImport(json);
    } catch (err) {
      alert("Ошибка импорта rules.json: " + (err as Error).message);
    }
  };

  const applyImports = () => {
    // TODO: отдать whalesImport и rulesImport в backend Rule Engine (REST/WS)
    alert("Импорт применён (демо). Передайте в backend Rule Engine.");
  };

  const exportTemplates = () => {
    downloadJSON("rules.template.json", TEMPLATE_RULES_JSON);
    downloadJSON("whales.template.json", TEMPLATE_WHALES_JSON);
  };

  const copyMint = async (mint: string) => {
    await navigator.clipboard.writeText(mint);
    alert("Mint скопирован: " + mint);
  };

  const quickOpen = (url?: string) => {
    if (!url) return;
    window.open(url, "_blank");
  };

  const applySLTP = (idx: number, sl: number, tp: number) => {
    // TODO: передать в бот/бекенд параметры SL/TP
    console.log("Set SL/TP:", candidates[idx].symbol, sl, tp);
  };

  // ====== UI ======

  return (
    <div className="min-h-screen w-full bg-slate-950 text-slate-100">
      {/* Верхняя панель */}
      <div className="sticky top-0 z-20 w-full border-b border-slate-800 bg-slate-900/80 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 py-3 flex items-center gap-3">
          <button onClick={handleStart} className={classNames("px-4 py-2 rounded-2xl text-sm font-semibold shadow", running ? "bg-emerald-600" : "bg-emerald-700 hover:bg-emerald-600")}>{running ? "Стоп" : "Старт скан"}</button>
          <button onClick={handleSaveProfile} className="px-4 py-2 rounded-2xl text-sm font-semibold shadow bg-blue-700 hover:bg-blue-600">Сохранить профиль</button>
          <button onClick={() => setShowFilters(true)} className="px-4 py-2 rounded-2xl text-sm font-semibold shadow bg-slate-700 hover:bg-slate-600">Фильтры</button>

          <div className="ml-auto flex items-center gap-2">
            <button onClick={() => whalesInputRef.current?.click()} className="px-4 py-2 rounded-2xl text-sm font-semibold shadow bg-amber-700 hover:bg-amber-600">Загрузка китов</button>
            <input ref={whalesInputRef} type="file" accept="application/json" className="hidden" onChange={onImportWhales} />
            <button onClick={() => rulesInputRef.current?.click()} className="px-4 py-2 rounded-2xl text-sm font-semibold shadow bg-amber-700 hover:bg-amber-600">Загрузка правил</button>
            <input ref={rulesInputRef} type="file" accept="application/json" className="hidden" onChange={onImportRules} />
            <button onClick={applyImports} className="px-4 py-2 rounded-2xl text-sm font-semibold shadow bg-amber-800 hover:bg-amber-700">Применить импорт</button>
            <button onClick={exportTemplates} className="px-4 py-2 rounded-2xl text-sm font-semibold shadow bg-slate-700 hover:bg-slate-600">Шаблоны JSON</button>
          </div>
        </div>

        {/* Полоса задержек/квот */}
        <div className="mx-auto max-w-7xl px-4 pb-3 text-xs text-slate-300">
          <div className="flex flex-wrap gap-4">
            <LatencyBadge name="Apify" ms={latencyInfo.apifyMs} used={quotas.apify.used} limit={quotas.apify.limit} />
            <LatencyBadge name="Solscan" ms={latencyInfo.solscanMs} />
            <LatencyBadge name="Birdeye" ms={latencyInfo.birdeyeMs} used={quotas.birdeye.used} limit={quotas.birdeye.limit} />
            <LatencyBadge name="GMGN" ms={latencyInfo.gmgnMs} />
            <LatencyBadge name="GROQ" ms={latencyInfo.groqMs} used={quotas.groq.used} limit={quotas.groq.limit} />
            <div className="ml-auto flex items-center gap-2">
              <label className="flex items-center gap-2"><input type="checkbox" checked={autoBuy} onChange={(e)=>setAutoBuy(e.target.checked)} /> Auto‑BUY</label>
            </div>
          </div>
        </div>
      </div>

      {/* Контент: 2 колонки */}
      <div className="mx-auto max-w-7xl grid grid-cols-1 md:grid-cols-2 gap-6 px-4 py-6">
        {/* Левая колонка — 5 режимов */}
        <div className="flex flex-col gap-6">
          <Card title="1) Pre‑Pool Tester" subtitle="Тестовые/скрытые tx до создания пула">
            <Range label="Мин. тестовых переводов" min={1} max={20} step={1} value={prepool.minTestTransfers} onChange={(v)=>setPrepool({...prepool, minTestTransfers:v})} />
            <Range label="Мин. уникальных адресов" min={1} max={15} step={1} value={prepool.minUniqueAddresses} onChange={(v)=>setPrepool({...prepool, minUniqueAddresses:v})} />
            <Range label="Окно (мин)" min={5} max={120} step={5} value={prepool.windowMin} onChange={(v)=>setPrepool({...prepool, windowMin:v})} />
            <Range label="Min test value (SOL)" min={0.001} max={0.2} step={0.001} value={prepool.minTestValue} onChange={(v)=>setPrepool({...prepool, minTestValue:v})} />
            <Tog label="Игнорировать dev‑blacklist" value={prepool.ignoreDevBlacklist} onChange={(v)=>setPrepool({...prepool, ignoreDevBlacklist:v})} />
            <Tog label="Считать серию inbound на связанный minter" value={prepool.followMinter} onChange={(v)=>setPrepool({...prepool, followMinter:v})} />
            <LinkRow />
          </Card>

          <Card title="2) Whale Cluster + CopyNet" subtitle="≥N китов + всплеск копитрейдеров">
            <Range label="Порог «кит» (SOL)" min={10} max={1000} step={5} value={cluster.whaleThresholdSol} onChange={(v)=>setCluster({...cluster, whaleThresholdSol:v})} />
            <Range label="Мин. китов" min={2} max={25} step={1} value={cluster.minWhales} onChange={(v)=>setCluster({...cluster, minWhales:v})} />
            <Range label="Окно кластера (мин)" min={1} max={60} step={1} value={cluster.windowMin} onChange={(v)=>setCluster({...cluster, windowMin:v})} />
            <Range label="Копитрейдеры / 5 мин" min={10} max={1000} step={10} value={cluster.minFollowers} onChange={(v)=>setCluster({...cluster, minFollowers:v})} />
            <Tog label="Требовать Jito priority‑fees" value={cluster.requireJito} onChange={(v)=>setCluster({...cluster, requireJito:v})} />
            <Tog label="Исключать бот‑подписи" value={cluster.excludeBots} onChange={(v)=>setCluster({...cluster, excludeBots:v})} />
            <LinkRow />
          </Card>

          <Card title="3) Whale + Social Burst" subtitle="Ончейн + соц‑всплеск (Apify + GROQ)">
            <Range label="Соц‑множитель (×база)" min={2} max={20} step={1} value={social.multiplier} onChange={(v)=>setSocial({...social, multiplier:v})} />
            <Range label="Окно соц‑аналитики (мин)" min={5} max={60} step={5} value={social.windowMin} onChange={(v)=>setSocial({...social, windowMin:v})} />
            <Range label="Мин. источников" min={1} max={5} step={1} value={social.minSources} onChange={(v)=>setSocial({...social, minSources:v})} />
            <Tog label="Только верифицированные инфлюенсеры" value={social.verifiedOnly} onChange={(v)=>setSocial({...social, verifiedOnly:v})} />
            <Range label="Игнорировать релевантность ниже" min={0} max={1} step={0.05} value={social.ignoreAdsBelow} onChange={(v)=>setSocial({...social, ignoreAdsBelow:v})} />
            <LinkRow />
          </Card>

          <Card title="4) Big Swap Hunter" subtitle="Крупные свопы/маршруты/импакт">
            <Range label="Min swap (SOL)" min={1} max={100} step={1} value={bigswap.minSwapSol} onChange={(v)=>setBigswap({...bigswap, minSwapSol:v})} />
            <Range label="Route consistency" min={0} max={1} step={0.01} value={bigswap.routeConsistency} onChange={(v)=>setBigswap({...bigswap, routeConsistency:v})} />
            <Range label="Окно цепочек (сек)" min={10} max={300} step={5} value={bigswap.windowSec} onChange={(v)=>setBigswap({...bigswap, windowSec:v})} />
            <Range label="Min price impact" min={0} max={0.1} step={0.001} value={bigswap.minImpact} onChange={(v)=>setBigswap({...bigswap, minImpact:v})} />
            <Tog label="Требовать priority‑fees" value={bigswap.requirePriorityFees} onChange={(v)=>setBigswap({...bigswap, requirePriorityFees:v})} />
            <Range label="Игнорировать арбитраж ниже" min={0} max={0.05} step={0.001} value={bigswap.ignoreArbBelow} onChange={(v)=>setBigswap({...bigswap, ignoreArbBelow:v})} />
            <LinkRow />
          </Card>

          <Card title="5) LP & Route Manip" subtitle="Манипуляции LP/маршруты, риск‑контроль">
            <Range label="LP move %" min={5} max={100} step={1} value={lpmanip.lpMovePct} onChange={(v)=>setLpmanip({...lpmanip, lpMovePct:v})} />
            <Range label="LP moves / 24h" min={1} max={10} step={1} value={lpmanip.lpMoves24h} onChange={(v)=>setLpmanip({...lpmanip, lpMoves24h:v})} />
            <Tog label="LP lock/burn обязат." value={lpmanip.requireLockOrBurn} onChange={(v)=>setLpmanip({...lpmanip, requireLockOrBurn:v})} />
            <Range label="Max rug risk" min={0} max={1} step={0.05} value={lpmanip.maxRugRisk} onChange={(v)=>setLpmanip({...lpmanip, maxRugRisk:v})} />
            <LinkRow />
          </Card>
        </div>

        {/* Правая колонка — кандидаты + таймлайн */}
        <div className="flex flex-col gap-6">
          <div className="border border-slate-800 rounded-2xl p-4 bg-slate-900/40">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-xl font-bold">Кандидаты</h2>
                <p className="text-xs text-slate-400">Реальные сигналы после Rule Engine + Risk Gates</p>
              </div>
              <div className="text-xs text-slate-400">{candidates.length} шт.</div>
            </div>

            <div className="grid gap-4">
              {candidates.map((c, idx) => (
                <div key={c.mint+idx} className="rounded-xl border border-slate-800 bg-slate-900 p-4 shadow">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-semibold">{c.symbol}</span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700">{c.scenario}</span>
                        <span className={classNames("text-xs px-2 py-0.5 rounded-full border", c.scores.priority>=0.75?"bg-emerald-900/40 border-emerald-700":"bg-yellow-900/30 border-yellow-700")}>prio {c.scores.priority.toFixed(2)}</span>
                      </div>
                      <div className="mt-1 text-xs text-slate-400 flex items-center gap-2">
                        <span>mint:</span>
                        <code className="text-slate-300">{c.mint}</code>
                        <button onClick={()=>copyMint(c.mint)} className="text-emerald-400 hover:underline">копировать</button>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <QuickLink label="Birdeye" onClick={()=>quickOpen(c.links.birdeye)} />
                      <QuickLink label="GMGN" onClick={()=>quickOpen(c.links.gmgn)} />
                      <QuickLink label="Solscan" onClick={()=>quickOpen(c.links.solscan)} />
                      <QuickLink label="RugCheck" onClick={()=>quickOpen(c.links.rugcheck)} />
                      <QuickLink label="SolSniffer" onClick={()=>quickOpen(c.links.solsniffer)} />
                    </div>
                  </div>

                  <div className="mt-3 grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
                    {typeof c.facts.whales === 'number' && <Badge label={`Whales: ${c.facts.whales}`} />}
                    {typeof c.facts.followers_5m === 'number' && <Badge label={`CopyNet: ${c.facts.followers_5m}/5m`} />}
                    {typeof c.facts.prepool === 'boolean' && <Badge label={`Pre‑Pool: ${c.facts.prepool? 'yes':'no'}`} />}
                    {typeof c.facts.route_consistency === 'number' && <Badge label={`Route: ${c.facts.route_consistency?.toFixed(2)}`} />}
                    {c.facts.lp_risk && <Badge label={`LP‑risk: ${c.facts.lp_risk}`} />}
                  </div>

                  <div className="mt-4 flex flex-wrap items-center gap-4 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">SL %</span>
                      <input type="range" min={5} max={50} defaultValue={25} onChange={(e)=>applySLTP(idx, Number(e.target.value), 0)} />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">TP %</span>
                      <input type="range" min={5} max={300} defaultValue={60} onChange={(e)=>applySLTP(idx, 0, Number(e.target.value))} />
                    </div>
                    <button className="px-3 py-1.5 rounded-xl bg-emerald-700 hover:bg-emerald-600 font-semibold">BUY</button>
                    {autoBuy && <span className="text-xs text-emerald-300">Auto‑BUY доступен (ворота пройдены)</span>}
                  </div>

                  {/* Таймлайн (демо) */}
                  <div className="mt-4 text-xs text-slate-400">
                    <div>t0: whale in • t+2m: +150 копи • t+7m: 5 инфлюенсеров</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Просмотр импортированных файлов (предпросмотр) */}
          <div className="border border-slate-800 rounded-2xl p-4 bg-slate-900/40">
            <h3 className="text-lg font-semibold mb-2">Импорт — предпросмотр</h3>
            <div className="grid md:grid-cols-2 gap-4 text-xs">
              <div className="rounded-lg border border-slate-800 p-3 bg-slate-900/40 overflow-auto max-h-60">
                <div className="font-semibold mb-1">whales.json</div>
                <pre className="whitespace-pre-wrap break-words">{whalesImport? JSON.stringify(whalesImport, null, 2): "— не загружено —"}</pre>
              </div>
              <div className="rounded-lg border border-slate-800 p-3 bg-slate-900/40 overflow-auto max-h-60">
                <div className="font-semibold mb-1">rules.json</div>
                <pre className="whitespace-pre-wrap break-words">{rulesImport? JSON.stringify(rulesImport, null, 2): "— не загружено —"}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Модалка глобальных фильтров */}
      {showFilters && (
        <div className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={()=>setShowFilters(false)}>
          <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900 p-4" onClick={(e)=>e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold">Глобальные фильтры</h3>
              <button onClick={()=>setShowFilters(false)} className="text-slate-300 hover:text-white">✕</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <TextArray label="Whitelist (адреса)" values={globalFilters.whitelist} onChange={(arr)=>setGlobalFilters({...globalFilters, whitelist:arr})} />
              <TextArray label="Blacklist (адреса)" values={globalFilters.blacklist} onChange={(arr)=>setGlobalFilters({...globalFilters, blacklist:arr})} />
              <NumberField label="Min Liquidity ($)" value={globalFilters.minLiquidityUsd} onChange={(v)=>setGlobalFilters({...globalFilters, minLiquidityUsd:v})} />
              <div className="rounded-xl border border-slate-800 p-3">
                <div className="text-xs text-slate-400 mb-1">Min Volume</div>
                <div className="grid grid-cols-3 gap-2">
                  <NumberField label="5m" value={globalFilters.minVol.m5} onChange={(v)=>setGlobalFilters({...globalFilters, minVol:{...globalFilters.minVol, m5:v}})} />
                  <NumberField label="15m" value={globalFilters.minVol.m15} onChange={(v)=>setGlobalFilters({...globalFilters, minVol:{...globalFilters.minVol, m15:v}})} />
                  <NumberField label="1h" value={globalFilters.minVol.h1} onChange={(v)=>setGlobalFilters({...globalFilters, minVol:{...globalFilters.minVol, h1:v}})} />
                </div>
              </div>
              <NumberField label="Min Holders" value={globalFilters.minHolders} onChange={(v)=>setGlobalFilters({...globalFilters, minHolders:v})} />
              <NumberField label="Max Top10 %" value={globalFilters.maxTop10Pct} onChange={(v)=>setGlobalFilters({...globalFilters, maxTop10Pct:v})} />
              <TextArray label="DEX allowlist" values={globalFilters.allowedDex} onChange={(arr)=>setGlobalFilters({...globalFilters, allowedDex:arr})} />
              <NumberField label="Max Rug Risk" value={globalFilters.maxRugRisk} onChange={(v)=>setGlobalFilters({...globalFilters, maxRugRisk:v})} step={0.05} />
              <TextArray label="Stop‑words (соцсети)" values={globalFilters.stopWords} onChange={(arr)=>setGlobalFilters({...globalFilters, stopWords:arr})} />
              <div className="rounded-xl border border-slate-800 p-3">
                <div className="text-xs text-slate-400 mb-1">Временные окна</div>
                <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={globalFilters.timeWindows.day} onChange={(e)=>setGlobalFilters({...globalFilters, timeWindows:{...globalFilters.timeWindows, day:e.target.checked}})} /> День</label>
                <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={globalFilters.timeWindows.night} onChange={(e)=>setGlobalFilters({...globalFilters, timeWindows:{...globalFilters.timeWindows, night:e.target.checked}})} /> Ночь</label>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <button onClick={()=>setShowFilters(false)} className="px-4 py-2 rounded-xl bg-blue-700 hover:bg-blue-600">Сохранить</button>
              <button onClick={()=>downloadJSON("global_filters.json", globalFilters)} className="px-4 py-2 rounded-xl bg-slate-700 hover:bg-slate-600">Экспорт</button>
            </div>
          </div>
        </div>
      )}

      {/* Врезка: указания для интегратора (фрилансера) */}
      <div className="mx-auto max-w-7xl px-4 pb-10 pt-2 text-xs text-slate-400">
        <p className="opacity-80">TODO для интегратора: подключить источники данных — Birdeye, GMGN, RugCheck, SolSniffer, Solscan, GROQ, Apify; 
          завести REST/WS на Rule Engine; прокинуть кандидатов (DTO) и risk‑gates. 
          Для проверки: используйте TEMPLATE_RULES_JSON и TEMPLATE_WHALES_JSON (кнопка «Шаблоны JSON»).</p>
      </div>
    </div>
  );
}

// ====== Мелкие UI компоненты ======

function Card({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 shadow">
      <div className="mb-3">
        <div className="text-lg font-semibold">{title}</div>
        {subtitle && <div className="text-xs text-slate-400">{subtitle}</div>}
      </div>
      <div className="grid gap-3">{children}</div>
    </div>
  );
}

function Range({ label, min, max, step, value, onChange }:{ label:string; min:number; max:number; step:number; value:number; onChange:(v:number)=>void }){
  return (
    <div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-300">{label}</span>
        <span className="text-xs text-slate-400">{typeof value === 'number' ? value.toString(): ''}</span>
      </div>
      <input className="w-full" type="range" min={min} max={max} step={step} value={value} onChange={(e)=>onChange(Number(e.target.value))} />
    </div>
  );
}

function Tog({ label, value, onChange }:{ label:string; value:boolean; onChange:(v:boolean)=>void }){
  return (
    <label className="flex items-center gap-2 text-xs">
      <input type="checkbox" checked={value} onChange={(e)=>onChange(e.target.checked)} />
      {label}
    </label>
  );
}

function QuickLink({ label, onClick }:{ label:string; onClick:()=>void }){
  return <button onClick={onClick} className="text-xs px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700">{label}</button>;
}

function Badge({ label }:{ label:string }){
  return <div className="px-2 py-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-200">{label}</div>;
}

function LinkRow(){
  return (
    <div className="flex flex-wrap gap-2 text-xs mt-1">
      <span className="text-slate-400">Быстрые ссылки:</span>
      <span className="px-2 py-1 rounded bg-slate-800 border border-slate-700">Birdeye</span>
      <span className="px-2 py-1 rounded bg-slate-800 border border-slate-700">GMGN</span>
      <span className="px-2 py-1 rounded bg-slate-800 border border-slate-700">Solscan</span>
      <span className="px-2 py-1 rounded bg-slate-800 border border-slate-700">RugCheck</span>
      <span className="px-2 py-1 rounded bg-slate-800 border border-slate-700">SolSniffer</span>
    </div>
  );
}

function LatencyBadge({ name, ms, used, limit }:{ name:string; ms:number; used?:number; limit?:number }){
  return (
    <div className="flex items-center gap-2 px-2 py-1 rounded-lg border border-slate-800 bg-slate-900/40">
      <span className="text-[11px] text-slate-300">{name}</span>
      <span className="text-[11px] text-slate-400">{ms} ms</span>
      {typeof used === 'number' && typeof limit === 'number' && (
        <span className="text-[11px] text-slate-500">{used}/{limit}</span>
      )}
    </div>
  );
}

function TextArray({ label, values, onChange }:{ label:string; values:string[]; onChange:(arr:string[])=>void }){
  const [text, setText] = useState(values.join(","));
  return (
    <div className="rounded-xl border border-slate-800 p-3">
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <input value={text} onChange={(e)=>{setText(e.target.value); onChange(e.target.value.split(",").map(s=>s.trim()).filter(Boolean));}} className="w-full rounded-lg bg-slate-800 border border-slate-700 px-2 py-1 text-sm" placeholder="addr1, addr2, ..." />
    </div>
  );
}

function NumberField({ label, value, onChange, step=1 }:{ label:string; value:number; onChange:(v:number)=>void; step?:number }){
  return (
    <div className="rounded-xl border border-slate-800 p-3">
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <input type="number" step={step} value={value} onChange={(e)=>onChange(Number(e.target.value))} className="w-full rounded-lg bg-slate-800 border border-slate-700 px-2 py-1 text-sm" />
    </div>
  );
}
