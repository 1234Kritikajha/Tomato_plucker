import {
  LayoutGrid,
  Upload,
  Image as ImageIcon,
  Layers,
  Settings,
  Users,
  LogIn,
  Database,
  Activity,
  BarChart3,
  FileText,
  Search,
  Target,
  Sparkles,
  Monitor,
  Cpu,
  Zap,
  Shield,
  Bell,
  FileCheck,
  LineChart,
  PieChart,
  TrendingUp,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

const NavGroup = ({ title, children }) => {
  return (
    <div className="sidebar-section">
      <div className="sidebar-section-title">{title}</div>
      <div className="sidebar-nav">{children}</div>
    </div>
  )
}

const NavItem = ({ icon: Icon, label, active, to }) => {
  return (
    <Link
      to={to}
      className={`sidebar-link ${active ? 'active' : ''}`}
    >
      <Icon className="sidebar-link-icon" />
      <span>{label}</span>
    </Link>
  )
}

export default function Sidebar() {
  const location = useLocation()
  const [activeLabel, setActiveLabel] = useState('Dashboard')

  const groups = useMemo(
    () => [
      {
        title: 'NAVIGATION',
        items: [
          { icon: LayoutGrid, label: 'Dashboard', to: '/dashboard' },
        ],
      },
      {
        title: 'DETECTION',
        items: [
          { icon: Monitor, label: 'Live Detection', to: '/live' },
          { icon: Upload, label: 'Upload Image', to: '/upload-image' },
          { icon: ImageIcon, label: 'Batch Processing', to: '/upload-video' },
        ],
      },
      {
        title: 'DATA & LEARNING',
        items: [
          { icon: FileText, label: 'Annotations', to: '/annotations' },
          { icon: Search, label: 'Dataset Explorer', to: '/dataset' },
          { icon: Target, label: 'Active Learning', to: '/active-learning' },
          { icon: Layers, label: 'Training', to: '/retraining' },
        ],
      },
      {
        title: 'MODELS',
        items: [
          { icon: Database, label: 'Model Versions', to: '/models' },
          { icon: BarChart3, label: 'Model Performance', to: '/dashboard' },
        ],
      },
      {
        title: 'ANALYTICS',
        items: [
          { icon: Activity, label: 'Monitoring', to: '/monitoring' },
          { icon: FileCheck, label: 'Reports', to: '/reports' },
          { icon: TrendingUp, label: 'Insights', to: '/dashboard' },
        ],
      },
      {
        title: 'SYSTEM',
        items: [
          { icon: Settings, label: 'Settings', to: '/settings' },
          { icon: Users, label: 'Users', to: '/settings' },
          { icon: LogIn, label: 'Logs', to: '/system-logs' },
        ],
      },
    ],
    []
  )

  // Update active label based on current location
  useMemo(() => {
    const pathToLabel = {}
    groups.forEach(group => {
      group.items.forEach(item => {
        pathToLabel[item.to] = item.label
      })
    })
    const currentLabel = pathToLabel[location.pathname] || 'Dashboard'
    setActiveLabel(currentLabel)
  }, [location.pathname, groups])

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <Sparkles className="h-5 w-5" />
        </div>
        <div>
          <div className="sidebar-title">TomatoPlucker</div>
          <div className="sidebar-subtitle">AI Vision System</div>
        </div>
      </div>

      <div className="flex-1">
        {groups.map((g) => (
          <NavGroup key={g.title} title={g.title}>
            {g.items.map((it) => (
              <NavItem
                key={it.label}
                icon={it.icon}
                label={it.label}
                to={it.to}
                active={activeLabel === it.label}
              />
            ))}
          </NavGroup>
        ))}
      </div>

      <div className="mt-auto pt-4 border-t border-[var(--border-color)]">
        <div className="flex items-center gap-3 p-3 rounded-lg bg-[var(--bg-card-hover)]">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-[var(--accent-primary)] to-[var(--accent-secondary)] text-black font-bold">
            A
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold text-[var(--text-primary)]">Admin User</div>
            <div className="text-xs text-[var(--text-muted)]">Administrator</div>
          </div>
        </div>
      </div>
    </aside>
  )
}
