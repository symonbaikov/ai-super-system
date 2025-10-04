import React, { useMemo, useState } from 'react'
import SafetyRulesPanel from './components/SafetyRulesPanel.jsx'
import RateLimitControls from './components/RateLimitControls.jsx'
import WhalesFilters from './components/WhalesFilters.jsx'
import CopyMintButton from './components/CopyMintButton.jsx'
import LatencyUsagePanel from './components/LatencyUsagePanel.jsx'
import SocialMetricsPanel from './components/SocialMetricsPanel.jsx'
import CexRadarSearchBar from './components/CexRadarSearchBar.jsx'

export default function App(){
  const [selectedServices, setSelectedServices] = useState(['goplus'])
  const [limits, setLimits] = useState({hour: 200, day: 2000, helius: 1000, das: 500})
  const [cexResults, setCexResults] = useState([])
  const latency = useMemo(() => ({
    apify: '420 ms',
    helius: '180 ms',
    filters: '250 ms'
  }), [])
  const usage = useMemo(() => ({
    apify_used: '56% / 24h',
    groq_used: '73% / 24h',
    rate_left: '44 req'
  }), [])

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <h1 className="text-2xl font-semibold">Super Parser AI — Control Center</h1>
          <p className="text-sm text-slate-400">Scout → Analyst → Judge orchestration preview UI</p>
        </div>
      </header>
      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8">
        <section className="grid gap-6 md:grid-cols-2">
          <SafetyRulesPanel
            checked={selectedServices}
            services={{goplus: true, rugcheck: false, sniffer: false}}
            onLoadRules={() => setSelectedServices(prev => prev.length === 3 ? ['goplus'] : ['goplus','rugcheck','sniffer'])}
          />
          <RateLimitControls
            initial={limits}
            onSave={(next) => setLimits(next)}
          />
        </section>
        <section className="grid gap-6 md:grid-cols-2">
          <LatencyUsagePanel
            latency={latency}
            limits={usage}
            tips={[
              'Уменьшите обновление Scout до 45 сек на новых токенах',
              'Analyst может отложить Groq запрос если rate_left < 20'
            ]}
          />
          <SocialMetricsPanel
            x={{posts: 128, likes: 960, delta: '+36%'}}
            tg={{members: 5420, online: 1870, delta: '+12%'}}
          />
        </section>
        <section className="grid gap-6 md:grid-cols-[2fr,1fr]">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-200">CEX Radar Lookup</h2>
              <CopyMintButton text="So11111111111111111111111111111111111111112" />
            </div>
            <div className="mt-4 space-y-3">
              <CexRadarSearchBar onResults={(rows) => setCexResults(rows)} />
              {cexResults.length > 0 && (
                <ul className="space-y-2 text-sm text-slate-200">
                  {cexResults.map((row, idx) => (
                    <li key={idx} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2">
                      <span className="font-semibold">{row.symbol}</span>
                      <span className="text-xs text-slate-400">{row.exchange}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          <WhalesFilters
            onStart={(payload) => console.debug('whales-start', payload)}
            onStop={() => console.debug('whales-stop')}
            onOpen={(row) => console.debug('open', row)}
          />
        </section>
      </main>
    </div>
  )
}
