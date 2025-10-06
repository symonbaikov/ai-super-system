import React from 'react'
import { useAppContext } from '../context/AppContext.jsx'

function severityClass(level) {
  switch (level) {
    case 'critical':
      return 'rounded-md px-2 py-1 text-xs uppercase bg-rose-600/30 text-rose-200'
    case 'warn':
      return 'rounded-md px-2 py-1 text-xs uppercase bg-amber-600/30 text-amber-200'
    default:
      return 'rounded-md px-2 py-1 text-xs uppercase bg-slate-700/50 text-slate-300'
  }
}

export function AlertsPanel() {
  const { state, actions } = useAppContext()

  if (!state.alerts.length) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-6 text-center text-sm text-slate-400">
        Нет активных алертов. Все чисто!
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {state.alerts.map((alert) => (
        <div key={alert.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-slate-100 text-sm font-semibold">{alert.title}</h3>
              <p className="text-xs text-slate-400">Источник: {alert.source}</p>
            </div>
            <span className={severityClass(alert.severity)}>
              {alert.severity}
            </span>
          </div>
          <p className="mt-3 text-sm text-slate-300">{alert.message}</p>
          {alert.payload && (
            <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-slate-950/70 p-3 text-xs text-slate-400">
              {JSON.stringify(alert.payload, null, 2)}
            </pre>
          )}
          <div className="mt-3 flex justify-between text-xs text-slate-500">
            <span>{new Date(alert.created_at || Date.now()).toLocaleString()}</span>
            {!alert.acked && (
              <button
                type="button"
                onClick={() => actions.acknowledgeAlert(alert.id)}
                className="rounded-md border border-slate-700 px-3 py-1 text-xs text-slate-200 hover:bg-slate-800"
              >
                Отметить как прочитанный
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
