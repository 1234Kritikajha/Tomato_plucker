import ThemeToggle from '../components/ThemeToggle.jsx'

export default function ModelManagementView() {
  return (
    <section className="relative">
      <div className="absolute right-0 top-0">
        <ThemeToggle />
      </div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold">Model Management</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Manage model versions and deployment.
        </p>

        <div className="mt-8 rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Current Model</h3>
          <div className="mt-4 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Model Name</span>
              <span className="text-sm font-medium text-slate-900 dark:text-slate-100">tomato_model.keras</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Status</span>
              <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-200">Active</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Type</span>
              <span className="text-sm font-medium text-slate-900 dark:text-slate-100">OpenCV Fallback</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}