import ThemeToggle from '../components/ThemeToggle.jsx'

export default function SettingsView() {
  return (
    <section className="relative">
      <div className="absolute right-0 top-0">
        <ThemeToggle />
      </div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Application settings and configuration.
        </p>

        <div className="mt-8 rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">General Settings</h3>
          <div className="mt-4 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Dark Mode</span>
              <button className="rounded-full bg-slate-200 px-4 py-2 text-sm font-medium text-slate-800 dark:bg-slate-700 dark:text-slate-200">
                Toggle
              </button>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Language</span>
              <span className="text-sm font-medium text-slate-900 dark:text-slate-100">English</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}