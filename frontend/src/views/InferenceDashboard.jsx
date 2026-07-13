import { useEffect, useMemo, useState } from 'react'

import ThemeToggle from '../components/ThemeToggle.jsx'
import apiClient from '../api/client.js'

const pct = (n) => {
  if (typeof n !== 'number' || !Number.isFinite(n)) return '—'
  return `${(n * 100).toFixed(1)}%`
}

export default function InferenceDashboardView() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [summary, setSummary] = useState(null)
  const [performance, setPerformance] = useState(null)
  const [historical, setHistorical] = useState(null)
  const [recentPredictions, setRecentPredictions] = useState(null)

  const fetchAll = async () => {
    setError(null)
    setLoading(true)
    try {
      const [summaryRes, perfRes, histRes, predRes] = await Promise.all([
        apiClient.get('/metrics/summary'),
        apiClient.get('/metrics/performance'),
        apiClient.get('/metrics/historical?days=1'),
        apiClient.getPredictionHistory(10)
      ])

      setSummary(summaryRes?.metrics ?? null)
      setPerformance(perfRes?.performance_metrics ?? null)
      setHistorical(histRes?.historical_metrics ?? null)
      setRecentPredictions(predRes?.predictions ?? null)
    } catch (e) {
      setError(e?.message || 'Failed to load dashboard metrics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
    const id = setInterval(fetchAll, 8000)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const totalDetections = useMemo(() => summary?.total_predictions ?? null, [summary])
  const totalPicks = useMemo(() => summary?.total_picks ?? null, [summary])

  const pickRate = useMemo(() => {
    const total = summary?.total_predictions
    const picks = summary?.total_picks
    if (!Number.isFinite(total) || total <= 0) return null
    if (!Number.isFinite(picks)) return null
    return picks / total
  }, [summary])

  const avgOverallConf = useMemo(() => {
    // /metrics/performance provides average_confidence in [0..1]
    const v = performance?.average_confidence
    return typeof v === 'number' && Number.isFinite(v) ? v : null
  }, [performance])

  const ripenessDist = useMemo(() => performance?.ripeness_distribution ?? null, [performance])
  const conditionDist = useMemo(() => performance?.condition_distribution ?? null, [performance])

  const latestPoint = useMemo(() => {
    if (!historical || historical.length === 0) return null
    // historical_metrics comes ordered DESC by backend query
    return historical[0]
  }, [historical])

  return (
    <section className="relative animate-fadeIn">
      <div className="absolute right-0 top-0">
        <ThemeToggle />
      </div>

      <div className="pt-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent dark:from-white dark:to-slate-300">
            Inference Dashboard
          </h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Real-time monitoring and analytics for tomato detection system
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div className="metric-card green card-hover rounded-xl border border-slate-200 bg-white p-6 shadow-lg dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-slate-600 dark:text-slate-400">Total Detections</div>
              <div className="rounded-lg bg-green-100 p-2 dark:bg-green-900/30">
                <svg className="h-5 w-5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
            </div>
            <div className="mt-4 text-3xl font-bold text-slate-900 dark:text-white">
              {loading ? '—' : typeof totalDetections === 'number' ? totalDetections.toLocaleString() : '—'}
            </div>
            <div className="mt-2 flex items-center text-xs">
              <span className="rounded-full bg-green-100 px-2 py-0.5 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                {pickRate == null ? '—' : `Pick ${(pickRate * 100).toFixed(1)}%`}
              </span>
              <span className="ml-2 text-slate-500 dark:text-slate-400">(total)</span>
            </div>
          </div>

          <div className="metric-card blue card-hover rounded-xl border border-slate-200 bg-white p-6 shadow-lg dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-slate-600 dark:text-slate-400">Ripe & Healthy (Pick)</div>
              <div className="rounded-lg bg-blue-100 p-2 dark:bg-blue-900/30">
                <svg className="h-5 w-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>
            <div className="mt-4 text-3xl font-bold text-green-600 dark:text-green-400">
              {loading ? '—' : typeof totalPicks === 'number' ? totalPicks.toLocaleString() : '—'}
            </div>
            <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              {pickRate == null ? '—' : `${(pickRate * 100).toFixed(1)}% of total detections`}
            </div>
          </div>

          <div className="metric-card purple card-hover rounded-xl border border-slate-200 bg-white p-6 shadow-lg dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-slate-600 dark:text-slate-400">Avg Confidence</div>
              <div className="rounded-lg bg-purple-100 p-2 dark:bg-purple-900/30">
                <svg className="h-5 w-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
            </div>
            <div className="mt-4 text-3xl font-bold text-slate-900 dark:text-white">{loading ? '—' : avgOverallConf == null ? '—' : pct(avgOverallConf)}</div>
            <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">from model averages</div>
          </div>

          <div className="metric-card orange card-hover rounded-xl border border-slate-200 bg-white p-6 shadow-lg dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-slate-600 dark:text-slate-400">Processing Time</div>
              <div className="rounded-lg bg-orange-100 p-2 dark:bg-orange-900/30">
                <svg className="h-5 w-5 text-orange-600 dark:text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <div className="mt-4 text-3xl font-bold text-slate-900 dark:text-white">—</div>
            <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">(not exposed by backend yet)</div>
          </div>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="card-hover rounded-xl border border-slate-200 bg-white p-6 shadow-lg dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Detection Activity</h3>
              <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                Last 24h
              </div>
            </div>
            <div className="mt-4 rounded-xl bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 p-4">
              {loading ? (
                <div className="text-center">
                  <div className="text-5xl mb-3 animate-pulse-slow">📊</div>
                  <div className="text-sm font-medium text-slate-600 dark:text-slate-400">Loading chart…</div>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">Latest day total</div>
                    <div className="text-3xl font-bold text-slate-900 dark:text-white">
                      {latestPoint?.total_predictions ?? '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">Latest day picks</div>
                    <div className="text-3xl font-bold text-slate-900 dark:text-white">
                      {latestPoint?.total_picks ?? '—'}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="card-hover rounded-xl border border-slate-200 bg-white p-6 shadow-lg dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Ripeness Distribution</h3>
              <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                Current batch
              </div>
            </div>

            <div className="mt-4 rounded-xl bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 p-4">
              {loading || !ripenessDist ? (
                <div className="text-center">
                  <div className="text-5xl mb-3 animate-pulse-slow">🍅</div>
                  <div className="text-sm font-medium text-slate-600 dark:text-slate-400">Loading distribution…</div>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(ripenessDist).map(([k, v]) => (
                    <div key={k} className="rounded-lg bg-white/70 p-3 border border-slate-200 dark:border-slate-800">
                      <div className="text-xs text-slate-500 dark:text-slate-400">{k}</div>
                      <div className="text-2xl font-bold text-slate-900 dark:text-white">{v}</div>
                    </div>
                  ))}

                  {conditionDist &&
                    Object.entries(conditionDist).slice(0, 2).map(([k, v]) => (
                      <div key={k} className="rounded-lg bg-white/70 p-3 border border-slate-200 dark:border-slate-800 col-span-2">
                        <div className="text-xs text-slate-500 dark:text-slate-400">Condition: {k}</div>
                        <div className="text-2xl font-bold text-slate-900 dark:text-white">{v}</div>
                      </div>
                    ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="mt-8 card-hover rounded-xl border border-slate-200 bg-white p-6 shadow-lg dark:border-slate-700 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Recent Detections</h3>
            <button className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
              View All
            </button>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th className="pb-3 text-left font-medium text-slate-600 dark:text-slate-400">Time</th>
                  <th className="pb-3 text-left font-medium text-slate-600 dark:text-slate-400">Image</th>
                  <th className="pb-3 text-left font-medium text-slate-600 dark:text-slate-400">Ripeness</th>
                  <th className="pb-3 text-left font-medium text-slate-600 dark:text-slate-400">Condition</th>
                  <th className="pb-3 text-left font-medium text-slate-600 dark:text-slate-400">Confidence</th>
                  <th className="pb-3 text-left font-medium text-slate-600 dark:text-slate-400">Action</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td className="py-4 text-slate-500" colSpan={6}>
                      Loading…
                    </td>
                  </tr>
                ) : !recentPredictions || recentPredictions.length === 0 ? (
                  <tr>
                    <td className="py-4 text-slate-500" colSpan={6}>
                      No recent predictions available
                    </td>
                  </tr>
                ) : (
                  recentPredictions.map((pred, index) => (
                    <tr key={index} className="border-b border-slate-100 dark:border-slate-800">
                      <td className="py-3 text-slate-600 dark:text-slate-400">
                        {new Date(pred.timestamp).toLocaleTimeString()}
                      </td>
                      <td className="py-3 text-slate-600 dark:text-slate-400">
                        {pred.filename}
                      </td>
                      <td className="py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          pred.ripeness === 'Ripe' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                          pred.ripeness === 'Unripe' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                          'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200'
                        }`}>
                          {pred.ripeness}
                        </span>
                      </td>
                      <td className="py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          pred.condition === 'Healthy' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
                          'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                        }`}>
                          {pred.condition}
                        </span>
                      </td>
                      <td className="py-3 text-slate-600 dark:text-slate-400">
                        {((pred.ripeness_conf + pred.condition_conf) / 2 * 100).toFixed(1)}%
                      </td>
                      <td className="py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          pred.pick ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                          'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
                        }`}>
                          {pred.pick ? 'Pluck' : 'Skip'}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  )
}

