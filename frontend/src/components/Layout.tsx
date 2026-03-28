import { Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { api } from '@/api/client'
import type { AlertItem } from '@/api/types'
import {
  Brain,
  FileText,
  AlertTriangle,
  ShieldAlert,
  ClipboardCheck,
  Bell,
  BarChart3,
  LayoutDashboard,
} from 'lucide-react'

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/policies', label: 'Policies', icon: FileText },
  { path: '/events', label: 'Events', icon: AlertTriangle },
  { path: '/risks', label: 'Risk Register', icon: ShieldAlert },
  { path: '/compliance', label: 'Compliance', icon: ClipboardCheck },
  { path: '/alerts', label: 'Alerts', icon: Bell },
  { path: '/evidence', label: 'Evidence', icon: BarChart3 },
]

export function Layout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const location = useLocation()

  const { data: pendingAlerts } = useQuery({
    queryKey: ['pending-alerts'],
    queryFn: () => api<AlertItem[]>('/alerts/my/pending'),
    refetchInterval: 60_000, // poll every minute
  })
  const pendingCount = pendingAlerts?.length ?? 0

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-sgmc-900 text-white flex flex-col">
        <div className="p-4 border-b border-sgmc-700">
          <div className="flex items-center gap-2">
            <Brain className="w-8 h-8 text-sgmc-300" />
            <div>
              <h1 className="font-bold text-lg leading-tight">SGMC Brain</h1>
              <p className="text-sgmc-400 text-xs">Governance Hub</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 py-4">
          {NAV_ITEMS.map(({ path, label, icon: Icon }) => {
            const active = path === '/' ? location.pathname === '/' : location.pathname.startsWith(path)
            const showBadge = path === '/alerts' && pendingCount > 0
            return (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                  active
                    ? 'bg-sgmc-700 text-white border-r-2 border-sgmc-300'
                    : 'text-sgmc-300 hover:bg-sgmc-800 hover:text-white'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
                {showBadge && (
                  <span className="ml-auto bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full leading-none">
                    {pendingCount}
                  </span>
                )}
              </Link>
            )
          })}
        </nav>

        {user && (
          <div className="p-4 border-t border-sgmc-700 text-sm">
            <p className="text-sgmc-300 truncate">{user.name}</p>
            <p className="text-sgmc-500 text-xs truncate">{user.email}</p>
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
