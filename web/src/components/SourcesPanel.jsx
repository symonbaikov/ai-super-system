import React from 'react'
import uiConfig from '../../configs/ui_config.json' assert { type: 'json' }

export function SourcesPanel() {
  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <h3 className="text-sm font-semibold text-slate-200">Страницы</h3>
        <ul className="mt-2 grid gap-2 text-sm text-slate-300 md:grid-cols-2">
          {uiConfig.pages.map((page) => (
            <li key={page.name} className="rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2">
              {page.name}
            </li>
          ))}
        </ul>
      </section>
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <h3 className="text-sm font-semibold text-slate-200">Фильтры</h3>
        <ul className="mt-2 grid gap-2 text-sm text-slate-300 md:grid-cols-2">
          {uiConfig.filters.map((filter) => (
            <li key={filter} className="rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2">
              {filter}
            </li>
          ))}
        </ul>
      </section>
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <h3 className="text-sm font-semibold text-slate-200">Кнопки</h3>
        <div className="mt-2 flex flex-wrap gap-2">
          {uiConfig.buttons.map((button) => (
            <span key={button} className="rounded-full border border-slate-700 bg-slate-950/60 px-3 py-1 text-xs text-slate-300">
              {button}
            </span>
          ))}
        </div>
      </section>
    </div>
  )
}
