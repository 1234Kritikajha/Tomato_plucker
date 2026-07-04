import ThemeToggle from '../components/ThemeToggle.jsx'

export default function LearningDatasetView() {
  return (
    <section className="relative">
      <div className="absolute right-0 top-0">
        <ThemeToggle />
      </div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold">Dataset Explorer</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Browse and manage your training dataset.
        </p>

        <div className="mt-8 rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Dataset Statistics</h3>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-900">
              <div className="text-sm text-slate-600 dark:text-slate-400">Total Images</div>
              <div className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">0</div>
            </div>
            <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-900">
              <div className="text-sm text-slate-600 dark:text-slate-400">Annotated</div>
              <div className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">0</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}