import Sidebar from './Sidebar.jsx'
import TopBar from './TopBar.jsx'
import { Outlet } from 'react-router-dom'

export default function PageShell({ children }) {
  return (
    <div className="dashboard-layout">
      <Sidebar />

      <div className="main-content">
        <TopBar />

        <main className="main-content-scroll">
          {children ?? <Outlet />}
        </main>
      </div>
    </div>
  )
}