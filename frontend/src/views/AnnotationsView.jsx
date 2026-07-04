import ThemeToggle from '../components/ThemeToggle.jsx'

export default function AnnotationsView() {
  return (
    <section className="relative">
      <div className="absolute right-0 top-0">
        <ThemeToggle />
      </div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold">Annotations</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Review and correct model predictions for improved accuracy.
        </p>

        <div className="mt-8 rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Pending Reviews</h3>
          <div className="mt-4 text-center text-slate-500 dark:text-slate-400">
            <div className="text-4xl mb-2">📝</div>
            <div className="text-sm">No pending annotations</div>
            <div className="text-xs mt-1">Start detection to generate annotations</div>
          </div>
        </div>
      </div>
    </section>
  )
}