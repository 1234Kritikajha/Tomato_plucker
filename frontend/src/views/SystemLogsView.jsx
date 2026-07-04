import ThemeToggle from '../components/ThemeToggle.jsx'

export default function SystemLogsView() {
  return (
    <section className="relative">
      <div className="absolute right-0 top-0">
        <ThemeToggle />
      </div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold">System Logs</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          View and search system logs and error messages.
        </p>

        <div className="mt-8 rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Recent Logs</h3>
          <div className="mt-4 space-y-2 font-mono text-sm">
            <div className="rounded bg-slate-50 p-2 dark:bg-slate-900">
              <span className="text-green-600">[INFO]</span> System started successfully
            </div>
            <div className="rounded bg-slate-50 p-2 dark:bg-slate-900">
              <span className="text-blue-600">[DEBUG]</span> Frontend server running on port 5173
            </div>
            <div className="rounded bg-slate-50 p-2 dark:bg-slate-900">
              <span className="text-green-600">[INFO]</span> Backend API connected
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}