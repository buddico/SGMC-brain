import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { AlertItem } from '@/api/types'
import { Bell, ExternalLink } from 'lucide-react'

const SOURCE_LABELS: Record<string, string> = {
  mhra_drug: 'MHRA Drug',
  mhra_device: 'MHRA Device',
  drug_safety_update: 'Drug Safety Update',
  natpsa: 'NatPSA',
  cas: 'CAS',
}

const STATUS_STYLES: Record<string, string> = {
  new: 'bg-red-100 text-red-700',
  in_progress: 'bg-amber-100 text-amber-700',
  complete: 'bg-green-100 text-green-700',
  not_applicable: 'bg-gray-100 text-gray-500',
}

const PRIORITY_STYLES: Record<string, string> = {
  p1_urgent: 'bg-red-500 text-white',
  p2_important: 'bg-amber-400 text-black',
  p3_routine: 'bg-blue-100 text-blue-700',
}

export function AlertsPage() {
  const { data: alerts, isLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api<AlertItem[]>('/alerts'),
  })

  if (isLoading) return <div className="text-gray-500">Loading alerts...</div>

  const newCount = alerts?.filter(a => a.status === 'new').length ?? 0

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Safety Alerts</h1>
          <p className="text-sm text-gray-500 mt-1">MHRA, NatPSA, and CAS alerts</p>
        </div>
        {newCount > 0 && (
          <span className="bg-red-500 text-white px-3 py-1 rounded-full text-sm font-medium">
            {newCount} new
          </span>
        )}
      </div>

      {!alerts?.length ? (
        <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
          <Bell className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p>No alerts yet.</p>
          <p className="text-sm mt-1">Alerts will appear here when the MHRA/NatPSA ingestion agent is configured.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-3 font-medium text-gray-600">Source</th>
                <th className="text-left p-3 font-medium text-gray-600">Alert</th>
                <th className="text-left p-3 font-medium text-gray-600">Issued</th>
                <th className="text-left p-3 font-medium text-gray-600">Priority</th>
                <th className="text-left p-3 font-medium text-gray-600">Status</th>
                <th className="text-left p-3 font-medium text-gray-600">Actions</th>
                <th className="text-left p-3 font-medium text-gray-600"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {alerts.map(alert => (
                <tr key={alert.id} className="hover:bg-gray-50">
                  <td className="p-3">
                    <span className="text-xs bg-gray-100 px-2 py-1 rounded-full">
                      {SOURCE_LABELS[alert.source] ?? alert.source}
                    </span>
                  </td>
                  <td className="p-3 font-medium max-w-md">
                    <p className="truncate">{alert.title}</p>
                    {alert.summary && <p className="text-xs text-gray-500 truncate mt-0.5">{alert.summary}</p>}
                  </td>
                  <td className="p-3 text-gray-600">{alert.issued_date ?? '-'}</td>
                  <td className="p-3">
                    {alert.priority && (
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${PRIORITY_STYLES[alert.priority] ?? ''}`}>
                        {alert.priority.replace('_', ' ').toUpperCase()}
                      </span>
                    )}
                  </td>
                  <td className="p-3">
                    <span className={`text-xs px-2 py-1 rounded-full ${STATUS_STYLES[alert.status] ?? ''}`}>
                      {alert.status}
                    </span>
                  </td>
                  <td className="p-3 text-gray-600">{alert.actions_count}</td>
                  <td className="p-3">
                    {alert.url && (
                      <a href={alert.url} target="_blank" rel="noopener noreferrer" className="text-sgmc-600 hover:text-sgmc-800">
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
