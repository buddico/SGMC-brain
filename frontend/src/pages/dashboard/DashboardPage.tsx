import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import type { Event, Risk, DashboardStats } from '@/api/types'
import { FileText, AlertTriangle, ShieldAlert, Bell, ClipboardCheck, BarChart3, Plus } from 'lucide-react'

function StatCard({ label, value, sublabel, icon: Icon, color, to }: {
  label: string; value: number | string; sublabel?: string; icon: React.ElementType; color: string; to?: string
}) {
  const content = (
    <div className="bg-white rounded-lg shadow-sm border p-5 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
          {sublabel && <p className="text-xs text-gray-400 mt-0.5">{sublabel}</p>}
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </div>
  )
  return to ? <Link to={to}>{content}</Link> : content
}

export function DashboardPage() {
  const { data: stats } = useQuery({
    queryKey: ['evidence-dashboard'],
    queryFn: () => api<DashboardStats>('/evidence/dashboard'),
  })
  const { data: events } = useQuery({
    queryKey: ['events'],
    queryFn: () => api<Event[]>('/events'),
  })
  const { data: risks } = useQuery({
    queryKey: ['risks'],
    queryFn: () => api<Risk[]>('/risks'),
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <Link
          to="/events/report"
          className="flex items-center gap-2 bg-sgmc-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-sgmc-700 transition-colors"
        >
          <Plus className="w-4 h-4" /> Report Event
        </Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <StatCard label="Policies" value={stats?.policies_active ?? '-'} sublabel={stats?.policies_review_due ? `${stats.policies_review_due} review due` : undefined} icon={FileText} color="bg-blue-500" to="/policies" />
        <StatCard label="Open Events" value={stats?.events_open ?? 0} sublabel={`${stats?.events_total ?? 0} total`} icon={AlertTriangle} color="bg-amber-500" to="/events" />
        <StatCard label="Open Risks" value={stats?.risks_open ?? 0} sublabel={stats?.risks_high ? `${stats.risks_high} high` : undefined} icon={ShieldAlert} color="bg-red-500" to="/risks" />
        <StatCard label="Compliance" value={stats?.checks_overdue ?? 0} sublabel="overdue checks" icon={ClipboardCheck} color="bg-purple-500" to="/compliance" />
        <StatCard label="New Alerts" value={stats?.alerts_new ?? 0} icon={Bell} color="bg-orange-500" to="/alerts" />
        <StatCard label="Evidence" value="-" sublabel="Generate packs" icon={BarChart3} color="bg-green-500" to="/evidence" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-sm border p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Recent Events</h2>
            <Link to="/events" className="text-xs text-sgmc-600 hover:underline">View all</Link>
          </div>
          {events?.length ? events.slice(0, 5).map(event => (
            <div key={event.id} className="flex items-center justify-between py-2 border-b last:border-0">
              <div>
                <p className="text-sm font-medium">{event.title}</p>
                <p className="text-xs text-gray-500">{event.reference} - {event.reported_by_name}</p>
              </div>
              <span className={`text-xs px-2 py-1 rounded-full ${
                event.severity === 'severe' || event.severity === 'catastrophic'
                  ? 'bg-red-100 text-red-700'
                  : event.severity === 'moderate'
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-green-100 text-green-700'
              }`}>
                {event.severity ?? 'unset'}
              </span>
            </div>
          )) : (
            <p className="text-sm text-gray-500 py-4 text-center">No events reported yet. <Link to="/events/report" className="text-sgmc-600 hover:underline">Report one now</Link>.</p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Top Risks</h2>
            <Link to="/risks" className="text-xs text-sgmc-600 hover:underline">View all</Link>
          </div>
          {risks?.length ? risks.slice(0, 5).map(risk => (
            <div key={risk.id} className="flex items-center justify-between py-2 border-b last:border-0">
              <div>
                <p className="text-sm font-medium">{risk.title}</p>
                <p className="text-xs text-gray-500">{risk.reference} - {risk.owner_name}</p>
              </div>
              <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                risk.risk_score >= 15 ? 'bg-red-100 text-red-700'
                : risk.risk_score >= 8 ? 'bg-amber-100 text-amber-700'
                : 'bg-green-100 text-green-700'
              }`}>
                {risk.risk_score}
              </span>
            </div>
          )) : (
            <p className="text-sm text-gray-500 py-4 text-center">No risks in register yet.</p>
          )}
        </div>
      </div>
    </div>
  )
}
