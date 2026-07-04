import ThemeToggle from '../components/ThemeToggle.jsx'

export default function TrainingMonitorView() {
  return (
    <section className="relative">
      <div className="absolute right-0 top-0">
        <ThemeToggle />
      </div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold">Training Monitor</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Real-time training progress monitoring.
        </p>

        <div className="mt-8 rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Training Status</h3>
          <div className="mt-4 text-center text-slate-500 dark:text-slate-400">
            <div className="text-4xl mb-2">📊</div>
            <div className="text-sm">No active training</div>
            <div className="text-xs mt-1">Start a training session to monitor progress</div>
          </div>
        </div>
      </div>
    </section>
  )
}