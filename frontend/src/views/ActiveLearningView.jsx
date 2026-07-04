import ThemeToggle from '../components/ThemeToggle.jsx'

export default function ActiveLearningView() {
  return (
    <section className="relative">
      <div className="absolute right-0 top-0">
        <ThemeToggle />
      </div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold">Active Learning</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Intelligent sample selection for efficient model training.
        </p>

        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Learning Strategy</h3>
            <div className="mt-4 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">Strategy</span>
                <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800 dark:bg-blue-900 dark:text-blue-200">Uncertainty Sampling</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">Batch Size</span>
                <span className="text-sm font-medium text-slate-900 dark:text-slate-100">32 samples</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">Confidence Threshold</span>
                <span className="text-sm font-medium text-slate-900 dark:text-slate-100">0.70</span>
              </div>
            </div>
          </div>

          <div className="rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Pending Samples</h3>
            <div className="mt-4 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">Total Pending</span>
                <span className="text-sm font-medium text-slate-900 dark:text-slate-100">156 samples</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">High Priority</span>
                <span className="text-sm font-medium text-red-600">23 samples</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">Medium Priority</span>
                <span className="text-sm font-medium text-yellow-600">45 samples</span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Sample Queue</h3>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b dark:border-slate-800">
                  <th className="pb-3 text-left font-medium text-slate-600 dark:text-slate-400">ID</th>
                  <th className="pb-3 text-left font-medium text-slate-600 dark:text-slate-400">Image</th>
                  <th className="pb-3 text-left font-medium text-slate-600 dark:text-slate-400">Uncertainty</th>
                  <th className="pb-3 text-left font-medium text-slate-600 dark:text-slate-400">Priority</th>
                  <th className="pb-3 text-left font-medium text-slate-600 dark:text-slate-400">Action</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b dark:border-slate-800">
                  <td className="py-3 text-slate-900 dark:text-slate-100">#001</td>
                  <td className="py-3 text-slate-900 dark:text-slate-100">sample_001.jpg</td>
                  <td className="py-3"><span className="text-red-600 font-medium">0.95</span></td>
                  <td className="py-3"><span className="rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-800 dark:bg-red-900 dark:text-red-200">High</span></td>
                  <td className="py-3"><button className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700">Review</button></td>
                </tr>
                <tr className="border-b dark:border-slate-800">
                  <td className="py-3 text-slate-900 dark:text-slate-100">#002</td>
                  <td className="py-3 text-slate-900 dark:text-slate-100">sample_002.jpg</td>
                  <td className="py-3"><span className="text-yellow-600 font-medium">0.78</span></td>
                  <td className="py-3"><span className="rounded-full bg-yellow-100 px-2 py-1 text-xs font-medium text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">Medium</span></td>
                  <td className="py-3"><button className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700">Review</button></td>
                </tr>
                <tr>
                  <td className="py-3 text-slate-900 dark:text-slate-100">#003</td>
                  <td className="py-3 text-slate-900 dark:text-slate-100">sample_003.jpg</td>
                  <td className="py-3"><span className="text-green-600 font-medium">0.45</span></td>
                  <td className="py-3"><span className="rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-200">Low</span></td>
                  <td className="py-3"><button className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700">Review</button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-8 flex gap-4">
          <button className="rounded-lg bg-green-600 px-6 py-2 text-sm font-medium text-white hover:bg-green-700">
            Start Active Learning Cycle
          </button>
          <button className="rounded-lg border border-slate-300 px-6 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
            Export Sample Queue
          </button>
        </div>
      </div>
    </section>
  )
}