import ThemeToggle from '../components/ThemeToggle.jsx'

export default function MonitoringView() {
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

        <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <div className="text-sm font-medium text-slate-600 dark:text-slate-400">CPU Usage</div>
            <div className="mt-2 text-3xl font-bold text-slate-900 dark:text-slate-100">45%</div>
          </div>
          <div className="rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <div className="text-sm font-medium text-slate-600 dark:text-slate-400">Memory</div>
            <div className="mt-2 text-3xl font-bold text-slate-900 dark:text-slate-100">2.4 GB</div>
          </div>
          <div className="rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <div className="text-sm font-medium text-slate-600 dark:text-slate-400">Uptime</div>
            <div className="mt-2 text-3xl font-bold text-slate-900 dark:text-slate-100">2h 34m</div>
          </div>
        </div>
      </div>
    </section>
  )
}