import React, { useState } from 'react'
import { useAppContext } from '../context/AppContext.jsx'

export function AdvicePanel() {
  const { state, actions } = useAppContext()
  const [prompt, setPrompt] = useState('Разъясни текущий сигнал')

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!prompt.trim()) return
    await actions.fetchAdvice(prompt.trim(), { requested_at: Date.now() })
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-4">
      <form onSubmit={handleSubmit} className="space-y-2">
        <label className="text-xs uppercase tracking-wide text-slate-400">Запрос к ИИ</label>
        <textarea
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          rows={3}
          className="w-full rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100"
        />
        <button
          type="submit"
          disabled={state.loading.advice}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {state.loading.advice ? 'Получаем совет…' : 'Получить совет'}
        </button>
      </form>
      {state.advice && (
        <div className="space-y-2 text-sm">
          <h4 className="text-slate-200 font-semibold">Ответ ИИ</h4>
          <pre className="whitespace-pre-wrap rounded-lg bg-slate-950/70 p-3 text-xs text-slate-300">
            {JSON.stringify(state.advice, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
