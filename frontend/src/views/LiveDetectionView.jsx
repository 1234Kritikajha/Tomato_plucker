export default function LiveDetectionView() {
  return (
    <section className="animate-fadeIn">
      <div className="mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-[var(--text-primary)] to-[var(--text-secondary)] bg-clip-text text-transparent">
          Live Detection
        </h1>
        <p className="mt-2 text-sm text-[var(--text-muted)]">
          Real-time tomato detection and classification using camera feed
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="card">
            <div className="card-header">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-green-100 p-2 dark:bg-green-900/30">
                  <svg className="h-5 w-5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <h3 className="card-title">Camera Feed</h3>
              </div>
              <div className="flex gap-2">
                <button className="btn btn-primary">Start Camera</button>
                <button className="btn btn-secondary">Stop</button>
              </div>
            </div>
            <div className="card-body">
              <div className="aspect-video rounded-xl bg-[var(--bg-card-hover)] flex items-center justify-center border-2 border-dashed border-[var(--border-color)]">
                <div className="text-center">
                  <div className="text-6xl mb-4 animate-pulse">📷</div>
                  <div className="text-lg font-medium text-[var(--text-secondary)]">Camera Preview</div>
                  <div className="text-sm mt-2 text-[var(--text-muted)]">Click "Start Camera" to begin detection</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="card">
            <div className="card-header">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-blue-100 p-2 dark:bg-blue-900/30">
                  <svg className="h-5 w-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <h3 className="card-title">Detection Status</h3>
              </div>
            </div>
            <div className="card-body space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-secondary)]">Status</span>
                <span className="status-badge neutral">Idle</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-secondary)]">FPS</span>
                <span className="text-sm font-medium text-[var(--text-primary)]">0</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-secondary)]">Detections</span>
                <span className="text-sm font-medium text-[var(--text-primary)]">0</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-secondary)]">Model</span>
                <span className="text-sm font-medium text-[var(--text-primary)]">OpenCV Fallback</span>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-purple-100 p-2 dark:bg-purple-900/30">
                  <svg className="h-5 w-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31-2.37-2.37a1.724 1.724 0 00-2.572 1.065c-.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <h3 className="card-title">Current Settings</h3>
              </div>
            </div>
            <div className="card-body space-y-4">
              <div>
                <label className="text-sm text-[var(--text-secondary)]">Confidence Threshold</label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value="70"
                  className="mt-2 w-full h-2 bg-[var(--bg-secondary)] rounded-lg appearance-none cursor-pointer"
                />
                <div className="mt-1 text-xs text-[var(--text-muted)]">70%</div>
              </div>
              <div>
                <label className="text-sm text-[var(--text-secondary)]">Detection Mode</label>
                <select className="mt-2 w-full rounded-lg border border-[var(--border-color)] px-3 py-2 text-sm dark:bg-[var(--bg-card)] dark:text-white">
                  <option>OpenCV Classic</option>
                  <option disabled>TensorFlow (Unavailable)</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}