import { useEffect, useRef, useState } from 'react'
import ThemeToggle from '../components/ThemeToggle.jsx'
import apiClient from '../api/client.js'

export default function RetrainingView() {
  const [epochs, setEpochs] = useState(100)
  const [triggering, setTriggering] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [elapsed, setElapsed] = useState(0)
  const timerRef = useRef(null)

  const handleTrigger = async () => {
    setTriggering(true)
    setResult(null)
    setError(null)
    setElapsed(0)
    const start = Date.now()
    timerRef.current = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 500)

    try {
      const res = await apiClient.post('/train/trigger', { epochs: Number(epochs) })
      setResult(res)
    } catch (e) {
      setError(e?.message || 'Training trigger failed')
    } finally {
      setTriggering(false)
      clearInterval(timerRef.current)
    }
  }

  useEffect(() => () => clearInterval(timerRef.current), [])

  return (
    <section className="relative">
      <div className="absolute right-0 top-0"><ThemeToggle /></div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold">Training</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Trigger YOLO model retraining via the automated pipeline.
        </p>

        {error && (
          <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-600 dark:text-red-400 text-sm">{error}</div>
        )}

        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Pipeline Config</h3>
            <div className="mt-4 space-y-4">
              <div>
                <label className="text-sm text-slate-600 dark:text-slate-400">Epochs (hint)</label>
                <input
                  type="number"
                  value={epochs}
                  onChange={e => setEpochs(e.target.value)}
                  min={1} max={500}
                  className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                />
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Data source</span>
                <span className="font-medium text-slate-900 dark:text-slate-100">Auto (Roboflow → Kaggle → local)</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Augmentation target</span>
                <span className="font-medium text-slate-900 dark:text-slate-100">50,000 / class</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Export format</span>
                <span className="font-medium text-slate-900 dark:text-slate-100">ONNX (hot-swap)</span>
              </div>
            </div>

            <div className="mt-6 flex items-center gap-3">
              <button
                onClick={handleTrigger}
                disabled={triggering}
                className="rounded-lg bg-green-600 px-6 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {triggering ? `Training… (${elapsed}s)` : 'Start Training'}
              </button>
              {triggering && (
                <span className="text-xs text-slate-500 dark:text-slate-400 animate-pulse">
                  Running in background — this may take minutes
                </span>
              )}
            </div>
          </div>

          {/* Result panel */}
          <div className="rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Last Run Result</h3>
            {!result && !triggering && (
              <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">No training run yet in this session.</p>
            )}
            {triggering && (
              <div className="mt-4 space-y-2">
                <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div className="h-2 rounded-full bg-green-500 animate-pulse" style={{ width: '60%' }} />
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">Training queued in background…</p>
              </div>
            )}
            {result && (
              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600 dark:text-slate-400">Status</span>
                  <span className={`rounded-full px-3 py-1 text-xs font-medium ${result.status === 'success'
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                    : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'}`}>
                    {result.status}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600 dark:text-slate-400">Message</span>
                  <span className="font-medium text-slate-900 dark:text-slate-100 text-right max-w-[200px]">
                    {result.message || '—'}
                  </span>
                </div>
                {result.cycles?.map((c, i) => (
                  <div key={i} className="mt-2 rounded-lg bg-slate-50 dark:bg-slate-900 p-3 text-xs space-y-1">
                    <div className="font-semibold text-slate-700 dark:text-slate-300">Cycle {i + 1}: {c.status}</div>
                    {c.training && (
                      <>
                        <div>Samples: {c.training.samples_used}</div>
                        {c.training.accuracy != null && <div>mAP50: {(c.training.accuracy * 100).toFixed(1)}%</div>}
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}