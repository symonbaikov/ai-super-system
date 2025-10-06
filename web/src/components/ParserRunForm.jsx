import React, { useState } from 'react'
import { useAppContext } from '../context/AppContext.jsx'

const DEFAULT_SOURCES = ['twitter', 'telegram', 'discord']

export function ParserRunForm() {
  const { actions, state } = useAppContext()
  const [symbol, setSymbol] = useState('DEGEN')
  const [sources, setSources] = useState(() => new Set(DEFAULT_SOURCES))
  const [priority, setPriority] = useState(5)

  const toggleSource = (source) => {
    setSources((prev) => {
      const next = new Set(prev)
      if (next.has(source)) {
        next.delete(source)
      } else {
        next.add(source)
      }
      return next
    })
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!symbol.trim()) return
    await actions.runParser({
      symbol: symbol.trim().toUpperCase(),
      sources: Array.from(sources),
      filters: [],
      priority,
      metadata: {},
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-2">
        <label className="text-xs uppercase tracking-wide text-slate-400">Тикер/символ</label>
        <input
          value={symbol}
          onChange={(event) => setSymbol(event.target.value)}
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
          placeholder="Например, DEGEN"
        />
      </div>
      <div className="grid gap-2">
        <span className="text-xs uppercase tracking-wide text-slate-400">Источники</span>
        <div className="flex flex-wrap gap-2">
          {DEFAULT_SOURCES.map((source) => {
            const active = sources.has(source)
            const className = active
              ? 'rounded-md border px-3 py-1 text-xs border-emerald-500 text-emerald-200 bg-emerald-500/10'
              : 'rounded-md border px-3 py-1 text-xs border-slate-700 text-slate-300'
            return (
              <button
                key={source}
                type="button"
                onClick={() => toggleSource(source)}
                className={className}
              >
                {source}
              </button>
            )
          })}
        </div>
      </div>
      <div className="grid gap-2">
        <label className="text-xs uppercase tracking-wide text-slate-400">Приоритет</label>
        <input
          type="range"
          min={1}
          max={10}
          value={priority}
          onChange={(event) => setPriority(Number(event.target.value))}
        />
        <span className="text-xs text-slate-400">{priority}</span>
      </div>
      <button
        type="submit"
        disabled={state.loading.parser}
        className="w-full rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {state.loading.parser ? 'Отправляем...' : 'Запустить парсер'}
      </button>
    </form>
  )
}
