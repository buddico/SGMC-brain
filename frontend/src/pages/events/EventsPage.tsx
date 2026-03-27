import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import type { Event } from '@/api/types'

export function EventsPage() {
  const { data: events, isLoading } = useQuery({
    queryKey: ['events'],
    queryFn: () => api<Event[]>('/events'),
  })

  if (isLoading) return <div className="text-gray-500">Loading events...</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Events</h1>
        <Link to="/events/report" className="bg-sgmc-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-sgmc-700 transition-colors">
          Report Event
        </Link>
      </div>

      <div className="bg-white rounded-lg shadow-sm border">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left p-3 font-medium text-gray-600">Reference</th>
              <th className="text-left p-3 font-medium text-gray-600">Title</th>
              <th className="text-left p-3 font-medium text-gray-600">Type</th>
              <th className="text-left p-3 font-medium text-gray-600">Severity</th>
              <th className="text-left p-3 font-medium text-gray-600">Status</th>
              <th className="text-left p-3 font-medium text-gray-600">Reported By</th>
              <th className="text-left p-3 font-medium text-gray-600">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {(events ?? []).map(event => (
              <tr key={event.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => window.location.href = `/events/${event.id}`}>
                <td className="p-3 font-mono text-xs">{event.reference}</td>
                <td className="p-3 font-medium text-sgmc-700">{event.title}</td>
                <td className="p-3 text-gray-600">{event.event_type_name}</td>
                <td className="p-3">
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    event.severity === 'severe' || event.severity === 'catastrophic'
                      ? 'bg-red-100 text-red-700'
                      : event.severity === 'moderate'
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-green-100 text-green-700'
                  }`}>
                    {event.severity ?? '-'}
                  </span>
                </td>
                <td className="p-3 text-gray-600">{event.status}</td>
                <td className="p-3 text-gray-600">{event.reported_by_name}</td>
                <td className="p-3 text-gray-500">{event.created_at?.slice(0, 10)}</td>
              </tr>
            ))}
            {!events?.length && (
              <tr><td colSpan={7} className="p-8 text-center text-gray-500">No events reported yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
