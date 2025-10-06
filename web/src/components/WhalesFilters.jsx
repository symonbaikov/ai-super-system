import React, { useState } from 'react'
import CopyMintButton from './CopyMintButton'

export default function WhalesFilters({ onStart, onStop, onOpen }) {
  const [minSOL, setMinSOL] = useState(100)
  const [maxSOL, setMaxSOL] = useState(5000)
  const [rules, setRules] = useState({ risk: 'strict', narrative: 'hype', whalesOnly: true })
  const [rows, setRows] = useState([])

  const start = async () => {
    onStart?.({ minSOL, maxSOL, rules })
    setRows([
      {
        name: 'WHALE-ALPHA',
        mint: 'MintAAA',
        whales: 7,
        sol: 1800,
        hype: 82,
        safety: 'OK',
        links: { birdeye: 'https://birdeye.so' },
      },
      {
        name: 'WHALE-OMEGA',
        mint: 'MintBBB',
        whales: 4,
        sol: 950,
        hype: 71,
        safety: 'OK',
        links: { birdeye: 'https://birdeye.so' },
      },
      {
        name: 'WHALE-DELTA',
        mint: 'MintCCC',
        whales: 3,
        sol: 620,
        hype: 63,
        safety: 'WARN',
        links: { birdeye: 'https://birdeye.so' },
      },
    ])
  }

  return (
    <div className="grid gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="grid gap-2 md:grid-cols-3">
        <Field label="Min SOL">
          <input
            type="number"
            value={minSOL}
            onChange={(event) => setMinSOL(Number(event.target.value))}
            className="w-full rounded-xl bg-slate-800/80 border border-slate-700 px-3 py-2 text-slate-100"
          />
        </Field>
        <Field label="Max SOL">
          <input
            type="number"
            value={maxSOL}
            onChange={(event) => setMaxSOL(Number(event.target.value))}
            className="w-full rounded-xl bg-slate-800/80 border border-slate-700 px-3 py-2 text-slate-100"
          />
        </Field>
        <Field label="Правила ИИ">
          <select
            value={rules.risk}
            onChange={(event) => setRules({ ...rules, risk: event.target.value })}
            className="rounded-xl bg-slate-800/80 border border-slate-700 px-2 py-2 text-slate-100"
          >
            <option value="strict">строгие</option>
            <option value="medium">средние</option>
            <option value="hype">хайп</option>
          </select>
        </Field>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={start}
          className="rounded-xl bg-emerald-600 px-3 py-2 text-sm text-white hover:bg-emerald-500"
          type="button"
        >
          Старт
        </button>
        <button
          onClick={() => onStop?.()}
          className="rounded-xl bg-rose-600 px-3 py-2 text-sm text-white hover:bg-rose-500"
          type="button"
        >
          Стоп
        </button>
        <button
          onClick={() => setRules((prev) => ({ ...prev, whalesOnly: !prev.whalesOnly }))}
          className="rounded-xl border border-slate-700 px-3 py-2 text-sm text-slate-100 bg-slate-800/60"
          type="button"
        >
          {rules.whalesOnly ? 'Киты: только' : 'Киты: все'}
        </button>
      </div>
      <div className="overflow-auto rounded-2xl border border-slate-800">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-slate-800/60 text-slate-300">
            <tr>
              <th className="p-3 text-left">Токен</th>
              <th className="p-3 text-left">Mint</th>
              <th className="p-3 text-left">Китов</th>
              <th className="p-3 text-left">SOL</th>
              <th className="p-3 text-left">Хайп</th>
              <th className="p-3 text-left">Безопасность</th>
              <th className="p-3 text-left">Действия</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={`${row.mint}-${index}`} className="border-t border-slate-800 hover:bg-slate-800/30">
                <td className="p-3 text-slate-100">{row.name}</td>
                <td className="p-3 text-slate-300">
                  <span className="font-mono">{row.mint}</span>
                  <span className="ml-2">
                    <CopyMintButton text={row.mint} />
                  </span>
                </td>
                <td className="p-3 text-slate-300">{row.whales}</td>
                <td className="p-3 text-slate-300">{row.sol}</td>
                <td className="p-3 text-slate-300">{row.hype}</td>
                <td className="p-3 text-slate-300">{row.safety}</td>
                <td className="p-3">
                  <button
                    onClick={() => onOpen?.(row)}
                    className="rounded-xl border border-slate-700 px-3 py-2 text-sm text-slate-100 bg-slate-800/60"
                    type="button"
                  >
                    Birdeye
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="text-slate-400">{label}</span>
      {children}
    </label>
  )
}
