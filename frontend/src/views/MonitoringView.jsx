import { useEffect, useMemo, useState } from 'react'

import ThemeToggle from '../components/ThemeToggle.jsx'
import apiClient from '../api/client.js'

const formatGB = (n) => {
  const v = typeof n === 'number' && Number.isFinite(n) ? n : 0
  return `${v} GB`
}

export default function MonitoringView() {
  const [loading, setLoading] = useState(true)

  const [error, setError] = useState(null)
  const [realtime, setRealtime] = useState(null)
  const [summary, setSummary] = useState(null)

  const fetchAll = async () => {
    setError(null)
    setLoading(true)
    try {
      const [summaryRes, realtimeRes] = await Promise.all([
        apiClient.get('/metrics/summary'),
        apiClient.get('/metrics/realtime'),
      ])

      setSummary(summaryRes?.metrics ?? null)
      setRealtime(realtimeRes?.realtime_metrics ?? null)
    } catch (e) {
      setError(e?.message || 'Failed to load monitoring metrics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
    const id = setInterval(fetchAll, 5000)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const cpu = useMemo(() => {
    const v = realtime?.system?.cpu_percent
    return typeof v === 'number' ? `${Math.round(v)}%` : '—'
  }, [realtime])

  const memory = useMemo(() => {
    const v = realtime?.system?.memory_available_gb
    return Number.isFinite(v) ? formatGB(v) : '—'
  }, [realtime])

  const uptime = useMemo(() => {
    // backend realtime metrics doesn't expose uptime directly.
    // Show recent_predictions as a proxy for liveness.
    const v = realtime?.application?.recent_predictions
    return Number.isFinite(v) ? `${v} jobs` : '—'
  }, [realtime])

  const lowConf = useMemo(() => {
    const v = summary?.low_confidence_count
    return Number.isFinite(v) ? v : null
  }, [summary])

  return (
    <section className="relative">
      <div className="absolute right-0 top-0">
        <ThemeToggle />
      </div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold">Monitoring</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          System performance and health monitoring.
        </p>

        {error && (
          <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <div className="text-sm font-medium text-slate-600 dark:text-slate-400">CPU Usage</div>
            <div className="mt-2 text-3xl font-bold text-slate-900 dark:text-slate-100">
              {loading ? '—' : cpu}
            </div>
          </div>
          <div className="rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <div className="text-sm font-medium text-slate-600 dark:text-slate-400">Memory (available)</div>
            <div className="mt-2 text-3xl font-bold text-slate-900 dark:text-slate-100">{loading ? '—' : memory}</div>
          </div>

          <div className="rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <div className="text-sm font-medium text-slate-600 dark:text-slate-400">Uptime</div>
            <div className="mt-2 text-3xl font-bold text-slate-900 dark:text-slate-100">{loading ? '—' : uptime}</div>
          </div>
        </div>

        <div className="mt-6 rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-medium text-slate-600 dark:text-slate-400">Low confidence detections</div>
              <div className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">
                {loading ? '—' : lowConf ?? '—'}
              </div>
            </div>
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Pulled from <span className="font-semibold">/api/metrics/summary</span> and refreshed every 5s
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

