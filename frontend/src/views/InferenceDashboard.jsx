import ThemeToggle from '../components/ThemeToggle.jsx'

export default function InferenceDashboardView() {
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
            <div className="mt-4 text-3xl font-bold text-slate-900 dark:text-white">1,234</div>
            <div className="mt-2 flex items-center text-xs">
              <span className="rounded-full bg-green-100 px-2 py-0.5 text-green-700 dark:bg-green-900/30 dark:text-green-400">+12%</span>
              <span className="ml-2 text-slate-500 dark:text-slate-400">from last hour</span>
            </div>
          </div>

          <div className="metric-card blue card-hover rounded-xl border border-slate-200 bg-white p-6 shadow-lg dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-slate-600 dark:text-slate-400">Ripe & Healthy</div>
              <div className="rounded-lg bg-blue-100 p-2 dark:bg-blue-900/30">
                <svg className="h-5 w-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>
            <div className="mt-4 text-3xl font-bold text-green-600 dark:text-green-400">856</div>
            <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">69% of total detections</div>
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
            <div className="mt-4 text-3xl font-bold text-slate-900 dark:text-white">94.2%</div>
            <div className="mt-2 flex items-center text-xs">
              <span className="rounded-full bg-green-100 px-2 py-0.5 text-green-700 dark:bg-green-900/30 dark:text-green-400">+2.1%</span>
              <span className="ml-2 text-slate-500 dark:text-slate-400">improvement</span>
            </div>
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
            <div className="mt-4 text-3xl font-bold text-slate-900 dark:text-white">45ms</div>
            <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">Average per image</div>
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
            <div className="mt-4 h-64 rounded-xl bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 flex items-center justify-center">
              <div className="text-center">
                <div className="text-5xl mb-3 animate-pulse-slow">📊</div>
                <div className="text-sm font-medium text-slate-600 dark:text-slate-400">Chart placeholder</div>
                <div className="text-xs mt-1 text-slate-500 dark:text-slate-500">Real-time detection graph</div>
              </div>
            </div>
          </div>

          <div className="card-hover rounded-xl border border-slate-200 bg-white p-6 shadow-lg dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Ripeness Distribution</h3>
              <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                Current batch
              </div>
            </div>
            <div className="mt-4 h-64 rounded-xl bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 flex items-center justify-center">
              <div className="text-center">
                <div className="text-5xl mb-3 animate-pulse-slow">🍅</div>
                <div className="text-sm font-medium text-slate-600 dark:text-slate-400">Pie chart placeholder</div>
                <div className="text-xs mt-1 text-slate-500 dark:text-slate-500">Ripe vs Unripe vs Half-Ripe</div>
              </div>
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
                <tr className="table-row border-b border-slate-100 dark:border-slate-800">
                  <td className="py-4 text-slate-900 dark:text-white">2 min ago</td>
                  <td className="py-4 text-slate-900 dark:text-white">tomato_001.jpg</td>
                  <td className="py-4">
                    <span className="status-badge rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-800 dark:bg-green-900/30 dark:text-green-400">
                      Ripe
                    </span>
                  </td>
                  <td className="py-4">
                    <span className="status-badge rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                      Healthy
                    </span>
                  </td>
                  <td className="py-4 font-medium text-slate-900 dark:text-white">96.5%</td>
                  <td className="py-4">
                    <span className="status-badge rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
                      Pick
                    </span>
                  </td>
                </tr>
                <tr className="table-row border-b border-slate-100 dark:border-slate-800">
                  <td className="py-4 text-slate-900 dark:text-white">5 min ago</td>
                  <td className="py-4 text-slate-900 dark:text-white">tomato_002.jpg</td>
                  <td className="py-4">
                    <span className="status-badge rounded-full bg-yellow-100 px-3 py-1 text-xs font-medium text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
                      Half-Ripe
                    </span>
                  </td>
                  <td className="py-4">
                    <span className="status-badge rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                      Healthy
                    </span>
                  </td>
                  <td className="py-4 font-medium text-slate-900 dark:text-white">89.2%</td>
                  <td className="py-4">
                    <span className="status-badge rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-800 dark:bg-slate-700 dark:text-slate-300">
                      Wait
                    </span>
                  </td>
                </tr>
                <tr className="table-row">
                  <td className="py-4 text-slate-900 dark:text-white">8 min ago</td>
                  <td className="py-4 text-slate-900 dark:text-white">tomato_003.jpg</td>
                  <td className="py-4">
                    <span className="status-badge rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-800 dark:bg-green-900/30 dark:text-green-400">
                      Ripe
                    </span>
                  </td>
                  <td className="py-4">
                    <span className="status-badge rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-800 dark:bg-red-900/30 dark:text-red-400">
                      Damaged
                    </span>
                  </td>
                  <td className="py-4 font-medium text-slate-900 dark:text-white">92.1%</td>
                  <td className="py-4">
                    <span className="status-badge rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-800 dark:bg-slate-700 dark:text-slate-300">
                      Skip
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  )
}