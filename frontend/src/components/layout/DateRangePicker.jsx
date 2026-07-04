import React from 'react'

export default function DateRangePicker() {
  return (
    <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white/70 px-3 py-2 shadow-sm dark:border-slate-800 dark:bg-slate-900/50">
      <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">Date range</div>
      <div className="text-xs text-slate-500 dark:text-slate-400">Last 24h</div>
    </div>
  )
}

