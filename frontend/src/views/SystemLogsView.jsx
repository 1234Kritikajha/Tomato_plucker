import { useEffect, useRef, useState } from 'react'
import ThemeToggle from '../components/ThemeToggle.jsx'
import apiClient from '../api/client.js'

const LEVEL_COLORS = {
  ERROR:   'text-red-500',
  WARNING: 'text-yellow-500',
  INFO:    'text-green-500',
  DEBUG:   'text-blue-400',
}

export default function SystemLogsView() {
  const [logs, setLogs] = useState([])
  const [sysInfo, setSysInfo] = useState(null)
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('ALL')
  const bottomRef = useRef(null)

  const fetchAll = async () => {
    setLoading(true)
    setError(null)
    try {
      const [sysRes, healthRes] = await Promise.all([
        apiClient.get('/system/info'),
        apiClient.get('/health'),
      ])
      setSysInfo(sysRes?.system_info ?? null)
      setHealth(healthRes ?? null)

      // Build synthetic log from real API data
      const ts = new Date().toLocaleTimeString()
      const newLogs = [
        { level: 'INFO',  msg: `Backend healthy — DB: ${healthRes?.database?.reachable ? 'OK' : 'ERROR'}`, ts },
        { level: healthRes?.status === 'ok' ? 'INFO' : 'WARNING',
          msg: `System status: ${healthRes?.status ?? 'unknown'}`, ts },
        { level: 'INFO',  msg: `Platform: ${sysRes?.system_info?.platform} ${sysRes?.system_info?.architecture}`, ts },
        { level: 'INFO',  msg: `Python ${sysRes?.system_info?.python_version}`, ts },
        { level: 'DEBUG', msg: `Storage writable: ${sysRes?.storage_info?.storage_writable}`, ts },
        { level: 'DEBUG', msg: `CWD: ${sysRes?.storage_info?.working_directory}`, ts },
      ]
      setLogs(prev => [...prev.slice(-200), ...newLogs])
    } catch (e) {
      setError(e?.message || 'Failed to fetch system info')
      setLogs(prev => [...prev, { level: 'ERROR', msg: e?.message, ts: new Date().toLocaleTimeString() }])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
    const id = setInterval(fetchAll, 10000)
    return () => clearInterval(id)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const displayed = filter === 'ALL' ? logs : logs.filter(l => l.level === filter)

  return (
    <section className="relative">
      <div className="absolute right-0 top-0"><ThemeToggle /></div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold">System Logs</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Live system info and API health — refreshed every 10s.
        </p>

        {error && (
          <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-600 dark:text-red-400 text-sm">{error}</div>
        )}

        {/* Health summary cards */}
        <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
          {[
            ['Status', health?.status ?? '—', health?.status === 'ok' ? 'text-green-600' : 'text-yellow-600'],
            ['DB Reachable', health?.database?.reachable ? 'Yes' : 'No', health?.database?.reachable ? 'text-green-600' : 'text-red-600'],
            ['DB Writable', health?.database?.write_ready ? 'Yes' : 'No', health?.database?.write_ready ? 'text-green-600' : 'text-red-600'],
            ['Uploads Dir', health?.tracking_flags?.uploads_dir ? 'Ready' : 'Missing', health?.tracking_flags?.uploads_dir ? 'text-green-600' : 'text-yellow-600'],
          ].map(([label, val, color]) => (
            <div key={label} className="rounded-lg border bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
              <div className="text-xs text-slate-500 dark:text-slate-400">{label}</div>
              <div className={`mt-1 text-lg font-bold ${color}`}>{loading ? '—' : val}</div>
            </div>
          ))}
        </div>

        {/* Log filter */}
        <div className="mt-6 flex gap-2">
          {['ALL', 'INFO', 'DEBUG', 'WARNING', 'ERROR'].map(lvl => (
            <button key={lvl} onClick={() => setFilter(lvl)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors
                ${filter === lvl
                  ? 'bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900'
                  : 'border border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800'
                }`}>
              {lvl}
            </button>
          ))}
          <button onClick={() => setLogs([])}
            className="ml-auto rounded-full border border-slate-300 px-3 py-1 text-xs text-slate-500 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800">
            Clear
          </button>
        </div>

        {/* Log console */}
        <div className="mt-3 h-80 overflow-y-auto rounded-lg border bg-slate-950 p-4 font-mono text-xs dark:border-slate-800">
          {displayed.length === 0 && (
            <div className="text-slate-500">No logs yet…</div>
          )}
          {displayed.map((l, i) => (
            <div key={i} className="flex gap-2 py-0.5">
              <span className="text-slate-500 shrink-0">{l.ts}</span>
              <span className={`shrink-0 font-bold ${LEVEL_COLORS[l.level] ?? 'text-slate-300'}`}>[{l.level}]</span>
              <span className="text-slate-200">{l.msg}</span>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>
    </section>
  )
}