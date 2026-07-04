import { Bell, Download } from 'lucide-react'
import DateRangePicker from '../layout/DateRangePicker.jsx'
import ThemeToggle from '../ThemeToggle.jsx'

export default function TopBar() {
  return (
    <div className="top-bar">
      <div className="mx-auto flex h-full max-w-[1400px] items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-[var(--text-primary)]">
            Welcome back, Admin! 👋
          </div>
          <div className="mt-0.5 text-xs text-[var(--text-muted)]">
            Monitoring live camera feeds and real-time detection analysis.
          </div>
        </div>

        <div className="flex flex-1 items-center justify-center">
          <DateRangePicker />
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            className="btn btn-primary"
          >
            <Download className="h-4 w-4" />
            Export Report
          </button>

          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--border-color)] bg-[var(--bg-card-hover)] transition-colors hover:bg-[var(--border-color)]"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4 text-[var(--neon-orange)]" />
          </button>

          <div className="ml-1">
            <ThemeToggle />
          </div>
        </div>
      </div>
    </div>
  )
}

