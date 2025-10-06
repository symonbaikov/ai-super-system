import React from 'react'

const headers = [
  { id: 'kind', label: 'Тип' },
  { id: 'symbol', label: 'Символ' },
  { id: 'time', label: 'Время' },
  { id: 'meta', label: 'Детали' },
]

function renderMeta(meta) {
  if (!meta) return '-'
  if (typeof meta === 'string') return meta
  try {
    return JSON.stringify(meta)
  } catch (error) {
    return String(meta)
  }
}

export function EventsTable({ events }) {
  if (!events.length) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-10 text-center text-sm text-slate-400">
        Ожидаем события из стрима...
      </div>
    )
  }

  return (
    <div className="overflow-auto rounded-xl border border-slate-800">
      <table className="min-w-full divide-y divide-slate-800">
        <thead className="bg-slate-900/80 text-xs uppercase tracking-wide text-slate-400">
          <tr>
            {headers.map((column) => (
              <th key={column.id} className="px-4 py-3 text-left font-medium">
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800 text-sm">
          {events.map((event, index) => (
            <tr key={`${event?.id || index}-${event?.t || index}`} className="hover:bg-slate-900/70">
              <td className="px-4 py-2 font-medium text-slate-200">{event.kind || 'signal'}</td>
              <td className="px-4 py-2 text-slate-300">{event.symbol || event.meta?.mint || '—'}</td>
              <td className="px-4 py-2 text-slate-300">
                {event.t ? new Date(event.t * 1000).toLocaleTimeString() : '—'}
              </td>
              <td className="px-4 py-2 text-slate-400 break-all">
                {renderMeta(event.meta)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
