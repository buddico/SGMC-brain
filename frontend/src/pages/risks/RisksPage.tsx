import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { Risk } from '@/api/types'

function riskColor(score: number): string {
  if (score >= 15) return 'bg-red-500 text-white'
  if (score >= 8) return 'bg-amber-400 text-black'
  if (score >= 4) return 'bg-yellow-300 text-black'
  return 'bg-green-400 text-black'
}

export function RisksPage() {
  const { data: risks, isLoading } = useQuery({
    queryKey: ['risks'],
    queryFn: () => api<Risk[]>('/risks'),
  })

  if (isLoading) return <div className="text-gray-500">Loading risk register...</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Risk Register</h1>
        <button className="bg-sgmc-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-sgmc-700 transition-colors">
          Add Risk
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-sm border">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left p-3 font-medium text-gray-600">Ref</th>
              <th className="text-left p-3 font-medium text-gray-600">Risk</th>
              <th className="text-left p-3 font-medium text-gray-600">Category</th>
              <th className="text-center p-3 font-medium text-gray-600">L</th>
              <th className="text-center p-3 font-medium text-gray-600">I</th>
              <th className="text-center p-3 font-medium text-gray-600">Score</th>
              <th className="text-left p-3 font-medium text-gray-600">Owner</th>
              <th className="text-left p-3 font-medium text-gray-600">Status</th>
              <th className="text-left p-3 font-medium text-gray-600">Last Reviewed</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {(risks ?? []).map(risk => (
              <tr key={risk.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => window.location.href = `/risks/${risk.id}`}>
                <td className="p-3 font-mono text-xs">{risk.reference}</td>
                <td className="p-3 font-medium max-w-xs truncate">{risk.title}</td>
                <td className="p-3 text-gray-600 capitalize">{risk.category.replace(/_/g, ' ')}</td>
                <td className="p-3 text-center">{risk.likelihood}</td>
                <td className="p-3 text-center">{risk.impact}</td>
                <td className="p-3 text-center">
                  <span className={`inline-block w-8 h-8 leading-8 rounded text-center font-bold text-sm ${riskColor(risk.risk_score)}`}>
                    {risk.risk_score}
                  </span>
                </td>
                <td className="p-3 text-gray-600">{risk.owner_name}</td>
                <td className="p-3 capitalize">{risk.status}</td>
                <td className="p-3 text-gray-500">{risk.last_reviewed ?? 'Never'}</td>
              </tr>
            ))}
            {!risks?.length && (
              <tr><td colSpan={9} className="p-8 text-center text-gray-500">No risks in register</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
