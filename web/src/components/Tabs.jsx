import React from 'react'

export function Tabs({ tabs, current, onChange }) {
  return (
    <div className="flex flex-wrap gap-2 border-b border-slate-800 bg-slate-900/60 px-4 py-2">
      {tabs.map((tab) => {
        const isActive = tab.id === current
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={
              'rounded-md px-3 py-2 text-sm font-medium transition-colors ' +
              (isActive
                ? 'bg-slate-800 text-white border border-slate-600'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60 border border-transparent')
            }
            type="button"
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
