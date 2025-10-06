import React, { useState } from 'react'
import { useAppContext } from '../context/AppContext.jsx'
import { exportAlerts } from '../lib/api.js'

export function ExportPanel() {
  const { apiBase } = useAppContext()
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState(null)

  const handleExport = async () => {
    setDownloading(true)
    setError(null)
    try {
      const data = await exportAlerts(apiBase)
      const blob = new Blob([data], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `alerts-${Date.now()}.json`
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <p className="text-sm text-slate-300">
        Экспортируйте актуальную выборку алертов в формате JSON. Файл содержит все,
        что возвращает `/api/alerts`, и подходит для анализа или отчётности.
      </p>
      <button
        type="button"
        onClick={handleExport}
        disabled={downloading}
        className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {downloading ? 'Готовим файл…' : 'Экспорт JSON'}
      </button>
      {error && <p className="text-sm text-rose-300">{error}</p>}
    </div>
  )
}
