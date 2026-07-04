import { useDispatch, useSelector } from 'react-redux'
import { Moon, Sun } from 'lucide-react'
import { toggleTheme } from '../state/slices/uiSlice.js'
import { selectTheme } from '../state/selectors/uiSelectors.js'
import { useEffect } from 'react'

export default function ThemeToggle({ className = '' }) {
  const dispatch = useDispatch()
  const theme = useSelector(selectTheme)

  const isDark = theme === 'dark'

  // Apply dark class to html element
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDark])

  return (
    <button
      type="button"
      onClick={() => dispatch(toggleTheme())}
      aria-label="Toggle theme"
      className={
        'group inline-flex h-10 w-28 items-center justify-between gap-2 rounded-2xl border px-2 transition-all ' +
        'bg-[var(--bg-card-hover)] border-[var(--border-color)] text-[var(--text-primary)] ' +
        'hover:border-[var(--accent-primary)] ' +
        className
      }
    >
      <span
        className={
          'inline-flex h-8 w-8 items-center justify-center rounded-xl transition-all ' +
          (isDark
            ? 'bg-[var(--bg-card)] text-[var(--text-muted)]'
            : 'bg-gradient-to-br from-[var(--accent-primary)] to-[var(--accent-secondary)] text-black')
        }
      >
        <Sun className="h-4 w-4" />
      </span>

      <span
        className={
          'inline-flex h-8 w-8 items-center justify-center rounded-xl transition-all ' +
          (!isDark
            ? 'bg-[var(--bg-card)] text-[var(--text-muted)]'
            : 'bg-gradient-to-br from-[var(--accent-primary)] to-[var(--accent-secondary)] text-black')
        }
      >
        <Moon className="h-4 w-4" />
      </span>
    </button>
  )
}

