import { useEffect, useState } from 'react'
import ThemeToggle from '../components/ThemeToggle.jsx'
import apiClient from '../api/client.js'

export default function ModelManagementView() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeModel, setActiveModel] = useState(null)
  const [models, setModels] = useState([])
  const [rollingBack, setRollingBack] = useState(false)
  const [deleting, setDeleting] = useState(null)

  const fetchModelData = async () => {
    setError(null)
    setLoading(true)
    try {
      const [activeRes, modelsRes] = await Promise.all([
        apiClient.getActiveModel(),
        apiClient.getModels()
      ])

      setActiveModel(activeRes?.active_model ?? null)
      setModels(modelsRes?.models ?? [])
    } catch (e) {
      setError(e?.message || 'Failed to load model data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchModelData()
  }, [])

  const handleRollback = async (version) => {
    if (!confirm(`Rollback to version ${version}? This will replace the current active model.`)) {
      return
    }

    setRollingBack(true)
    setError(null)
    try {
      await apiClient.rollbackModel(version)
      await fetchModelData()
      alert('Model rollback successful!')
    } catch (e) {
      setError(e?.message || 'Rollback failed')
    } finally {
      setRollingBack(false)
    }
  }

  const handleDelete = async (modelName) => {
    if (!confirm(`Delete model ${modelName}? This action cannot be undone.`)) {
      return
    }

    setDeleting(modelName)
    setError(null)
    try {
      await apiClient.deleteModel(modelName)
      await fetchModelData()
      alert('Model deleted successfully!')
    } catch (e) {
      setError(e?.message || 'Delete failed')
    } finally {
      setDeleting(null)
    }
  }

  const formatSize = (bytes) => {
    if (!bytes) return '—'
    const mb = bytes / (1024 * 1024)
    return mb < 1 ? `${(bytes / 1024).toFixed(1)} KB` : `${mb.toFixed(2)} MB`
  }

  const formatDate = (isoString) => {
    if (!isoString) return '—'
    return new Date(isoString).toLocaleString()
  }

  return (
    <section className="relative">
      <div className="absolute right-0 top-0">
        <ThemeToggle />
      </div>

      <div className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Model Management</h1>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              Manage model versions and deployment.
            </p>
          </div>
          <button
            onClick={fetchModelData}
            className="btn btn-secondary"
            disabled={loading}
          >
            Refresh
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-600 dark:text-red-400">
            <div className="font-medium">Error</div>
            <div className="text-sm mt-1">{error}</div>
          </div>
        )}

        <div className="mt-8 space-y-6">
          {/* Active Model Section */}
          <div className="card-hover rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Active Model</h3>
            
            {loading ? (
              <div className="text-center py-8">
                <div className="text-sm text-[var(--text-muted)]">Loading model information...</div>
              </div>
            ) : activeModel ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[var(--text-secondary)]">Model Name</span>
                  <span className="text-sm font-medium text-[var(--text-primary)]">{activeModel.name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[var(--text-secondary)]">Size</span>
                  <span className="text-sm font-medium text-[var(--text-primary)]">{formatSize(activeModel.size_bytes)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[var(--text-secondary)]">Created</span>
                  <span className="text-sm font-medium text-[var(--text-primary)]">{formatDate(activeModel.created_at)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[var(--text-secondary)]">Last Modified</span>
                  <span className="text-sm font-medium text-[var(--text-primary)]">{formatDate(activeModel.modified_at)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[var(--text-secondary)]">Status</span>
                  <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-200">
                    Active
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="text-sm text-[var(--text-muted)]">No active model found</div>
              </div>
            )}
          </div>

          {/* Available Models Section */}
          <div className="card-hover rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Available Models</h3>
            
            {loading ? (
              <div className="text-center py-8">
                <div className="text-sm text-[var(--text-muted)]">Loading models...</div>
              </div>
            ) : models.length === 0 ? (
              <div className="text-center py-8">
                <div className="text-sm text-[var(--text-muted)]">No models available</div>
              </div>
            ) : (
              <div className="space-y-3">
                {models.map((model) => (
                  <div
                    key={model.name}
                    className={`p-4 rounded-lg border ${
                      model.is_active
                        ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/10'
                        : 'border-[var(--border-color)] bg-[var(--bg-card-hover)]'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-[var(--text-primary)]">{model.name}</span>
                          {model.is_active && (
                            <span className="rounded-full bg-[var(--accent-primary)] px-2 py-0.5 text-xs font-medium text-black">
                              Active
                            </span>
                          )}
                        </div>
                        <div className="mt-2 text-sm text-[var(--text-muted)]">
                          Size: {formatSize(model.size_bytes)} • Modified: {formatDate(model.modified_at)}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {!model.is_active && (
                          <>
                            <button
                              onClick={() => handleRollback(model.name)}
                              disabled={rollingBack}
                              className="btn btn-secondary text-xs"
                            >
                              {rollingBack ? 'Rolling back...' : 'Rollback'}
                            </button>
                            <button
                              onClick={() => handleDelete(model.name)}
                              disabled={deleting === model.name}
                              className="btn btn-danger text-xs"
                            >
                              {deleting === model.name ? 'Deleting...' : 'Delete'}
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Model Information */}
          <div className="card-hover rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Model Information</h3>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-xs text-[var(--text-muted)]">Total Models</div>
                <div className="font-medium text-[var(--text-primary)]">{models.length}</div>
              </div>
              <div>
                <div className="text-xs text-[var(--text-muted)]">Active Model</div>
                <div className="font-medium text-[var(--text-primary)]">{activeModel?.name || 'None'}</div>
              </div>
              <div>
                <div className="text-xs text-[var(--text-muted)]">Model Framework</div>
                <div className="font-medium text-[var(--text-primary)]">TensorFlow/Keras</div>
              </div>
              <div>
                <div className="text-xs text-[var(--text-muted)]">Input Size</div>
                <div className="font-medium text-[var(--text-primary)]">224x224x3</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}