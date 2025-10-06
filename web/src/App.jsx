import React, { useMemo, useState } from 'react'
import { AppProvider, useAppContext } from './context/AppContext.jsx'
import SafetyRulesPanel from './components/SafetyRulesPanel.jsx'
import RateLimitControls from './components/RateLimitControls.jsx'
import WhalesFilters from './components/WhalesFilters.jsx'
import CopyMintButton from './components/CopyMintButton.jsx'
import LatencyUsagePanel from './components/LatencyUsagePanel.jsx'
import SocialMetricsPanel from './components/SocialMetricsPanel.jsx'
import CexRadarSearchBar from './components/CexRadarSearchBar.jsx'
import { Tabs } from './components/Tabs.jsx'
import { EventsTable } from './components/EventsTable.jsx'
import { AlertsPanel } from './components/AlertsPanel.jsx'
import { ParserRunForm } from './components/ParserRunForm.jsx'
import { SourcesPanel } from './components/SourcesPanel.jsx'
import { ExportPanel } from './components/ExportPanel.jsx'
import { AdvicePanel } from './components/AdvicePanel.jsx'

const tabs = [
  { id: 'start', label: 'Старт' },
  { id: 'parser', label: 'Парсер' },
  { id: 'sources', label: 'Источники' },
  { id: 'logs', label: 'Логи' },
  { id: 'export', label: 'Экспорт' },
]

function ConnectionBadge() {
  const { state } = useAppContext()
  const { connection } = state

  const tone = connection.status === 'open' ? 'text-emerald-300' : connection.status === 'error' ? 'text-rose-300' : 'text-slate-300'
  const label = connection.status === 'open' ? 'SSE подключено' : connection.status === 'error' ? 'SSE ошибка' : 'SSE подключаемся'

  return <span className={`text-xs ${tone}`}>{label}</span>
}

function ErrorBanner() {
  const { state, actions } = useAppContext()
  if (!state.error) return null
  return (
    <div className="rounded-lg border border-rose-700 bg-rose-900/20 px-4 py-3 text-sm text-rose-200">
      {state.error}
      <button type="button" onClick={actions.clearError} className="ml-3 text-xs uppercase tracking-wide text-rose-300 underline">
        скрыть
      </button>
    </div>
  )
}

function StartTab() {
  const { state } = useAppContext()
  const [limits, setLimits] = useState({ hour: 200, day: 2000, helius: 1000, das: 500 })
  const services = useMemo(() => ({ goplus: true, rugcheck: true, sniffer: true }), [])

  return (
    <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
      <div className="space-y-6">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="text-sm font-semibold text-slate-200">Запуск парсера</h2>
          <p className="mt-1 text-xs text-slate-400">Отправьте ручной запуск для проверки цепочек Scout → Analyst → Judge.</p>
          <div className="mt-4">
            <ParserRunForm />
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="text-sm font-semibold text-slate-200">Безопасность и сервисы</h2>
          <SafetyRulesPanel checked={Object.keys(services)} services={services} onLoadRules={() => {}} />
        </div>
      </div>
      <div className="space-y-6">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <h3 className="text-sm font-semibold text-slate-200">SSE состояние</h3>
          <p className="mt-2 text-xs text-slate-400">Последний сигнал: {state.connection.lastEventAt ? new Date(state.connection.lastEventAt).toLocaleTimeString() : '—'}</p>
          <ConnectionBadge />
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <h3 className="text-sm font-semibold text-slate-200">Лимиты</h3>
          <RateLimitControls initial={limits} onSave={setLimits} />
        </div>
      </div>
    </div>
  )
}

function ParserTab() {
  const { state } = useAppContext()
  const [cexResults, setCexResults] = useState([])
  const latency = useMemo(() => ({ apify: '420 ms', helius: '180 ms', filters: '250 ms' }), [])
  const usage = useMemo(() => ({ apify_used: '56% / 24h', groq_used: '73% / 24h', rate_left: '44 req' }), [])

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <div className="grid gap-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <LatencyUsagePanel latency={latency} limits={usage} tips={['Scout обновление 45 сек', 'Analyst экономит Groq при rate_left < 20']} />
            <SocialMetricsPanel metrics={{ twitter: { mentions: 128, delta: 36 }, telegram: { mentions: 54, delta: -5 } }} />
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200">CEX Radar Lookup</h3>
              <CopyMintButton text="So11111111111111111111111111111111111111112" />
            </div>
            <div className="mt-4 space-y-3">
              <CexRadarSearchBar onResults={setCexResults} />
              {cexResults.length > 0 && (
                <ul className="space-y-2 text-sm text-slate-200">
                  {cexResults.map((row, index) => (
                    <li key={index} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2">
                      <span className="font-semibold">{row.symbol}</span>
                      <span className="text-xs text-slate-400">{row.exchange}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          <EventsTable events={state.signals} />
        </div>
        <div className="space-y-6">
          <WhalesFilters
            onStart={(payload) => console.debug('whales start', payload)}
            onStop={() => console.debug('whales stop')}
            onOpen={(row) => console.debug('open', row)}
          />
          <AdvicePanel />
        </div>
      </div>
    </div>
  )
}

function LogsTab() {
  return <AlertsPanel />
}

function AppShell() {
  const { state, actions } = useAppContext()

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-2xl font-semibold">Super Parser AI — Control Center</h1>
            <p className="text-sm text-slate-400">Scout → Analyst → Judge</p>
          </div>
          <ConnectionBadge />
        </div>
      </header>
      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8">
        <Tabs tabs={tabs} current={state.currentTab} onChange={actions.setTab} />
        <ErrorBanner />
        {state.currentTab === 'start' && <StartTab />}
        {state.currentTab === 'parser' && <ParserTab />}
        {state.currentTab === 'sources' && <SourcesPanel />}
        {state.currentTab === 'logs' && <LogsTab />}
        {state.currentTab === 'export' && <ExportPanel />}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <AppProvider>
      <AppShell />
    </AppProvider>
  )
}
