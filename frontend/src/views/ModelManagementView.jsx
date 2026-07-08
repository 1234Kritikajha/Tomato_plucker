import { useEffect, useState } from 'react'
import ThemeToggle from '../components/ThemeToggle.jsx'
import apiClient from '../api/client.js'

export default function ModelManagementView() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [sysInfo, setSysInfo] = useState(null)

  const fetchAll = async () => {
    setLoading(true)
    setError(null)
    try {
      const [modelsRes, sysRes] = await Promise.all([
        apiClient.get('/models/list'),
        apiClient.get('/system/info'),
      ])
      setData(modelsRes)
      setSysInfo(sysRes?.system_info ?? null)
    } catch (e) {
      setError(e?.message || 'Failed to load model info')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAll() }, [])

  const modelName = data?.class_names
    ? Object.keys(data.class_names).join(', ')
    : 'tomato_yolo.onnx'

  return (
    <section className="relative">
      <div className="absolute right-0 top-0"><ThemeToggle /></div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold">Model Management</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Manage model versions and deployment.
        </p>

        {error && (
          <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-600 dark:text-red-400 text-sm">{error}</div>
        )}

        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Current Model */}
          <div className="rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Current Model</h3>
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">Model File</span>
                <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                  {loading ? '—' : modelName}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">Total Versions</span>
                <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                  {loading ? '—' : data?.total_models ?? 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">Status</span>
                <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-200">
                  Active (OpenCV fallback)
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">Storage</span>
                <span className="text-xs text-slate-500 dark:text-slate-400 max-w-[180px] truncate text-right">
                  {loading ? '—' : data?.models_dir?.split('/').slice(-3).join('/')}
                </span>
              </div>
            </div>
            <button onClick={fetchAll}
              className="mt-5 rounded-lg border border-slate-300 px-4 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
              Refresh
            </button>
          </div>

          {/* System Info */}
          <div className="rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">System Info</h3>
            <div className="mt-4 space-y-3">
              {[
                ['Platform', sysInfo?.platform],
                ['Architecture', sysInfo?.architecture],
                ['Python', sysInfo?.python_version],
                ['Host', sysInfo?.hostname],
              ].map(([label, val]) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-sm text-slate-600 dark:text-slate-400">{label}</span>
                  <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {loading ? '—' : val ?? '—'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Models list */}
        {!loading && data?.models?.length > 0 && (
          <div className="mt-6 rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <h3 className="text-lg font-semibold mb-4">Saved Checkpoints</h3>
            <div className="space-y-2">
              {data.models.map((m, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-slate-50 dark:bg-slate-900 px-4 py-2 text-sm">
                  <span className="font-mono text-slate-900 dark:text-slate-100">{m.name || m}</span>
                  <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900 dark:text-blue-200">Checkpoint</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}