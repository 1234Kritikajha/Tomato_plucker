import ThemeToggle from '../components/ThemeToggle.jsx'

export default function RetrainingView() {
  return (
    <section className="relative">
      <div className="absolute right-0 top-0">
        <ThemeToggle />
      </div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold">Training</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Model training and retraining configuration.
        </p>

        <div className="mt-8 rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Training Configuration</h3>
          <div className="mt-4 space-y-4">
            <div>
              <label className="text-sm text-slate-600 dark:text-slate-400">Epochs</label>
              <input
                type="number"
                defaultValue="50"
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
              />
            </div>
            <div>
              <label className="text-sm text-slate-600 dark:text-slate-400">Batch Size</label>
              <input
                type="number"
                defaultValue="32"
                className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
              />
            </div>
          </div>
          <div className="mt-6">
            <button className="rounded-lg bg-green-600 px-6 py-2 text-sm font-medium text-white hover:bg-green-700">
              Start Training
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}