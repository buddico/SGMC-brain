import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { EvidencePack, DashboardStats } from '@/api/types'
import { BarChart3, FileDown, Loader2 } from 'lucide-react'

export function EvidencePage() {
  const queryClient = useQueryClient()
  const [periodStart, setPeriodStart] = useState(() => {
    const d = new Date()
    d.setMonth(d.getMonth() - 3)
    return d.toISOString().slice(0, 10)
  })
  const [periodEnd, setPeriodEnd] = useState(() => new Date().toISOString().slice(0, 10))

  const { data: stats } = useQuery({
    queryKey: ['evidence-dashboard'],
    queryFn: () => api<DashboardStats>('/evidence/dashboard'),
  })

  const { data: packs, isLoading } = useQuery({
    queryKey: ['evidence-packs'],
    queryFn: () => api<EvidencePack[]>('/evidence/packs'),
  })

  const generateMutation = useMutation({
    mutationFn: (data: { period_start: string; period_end: string }) =>
      api('/evidence/generate', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['evidence-packs'] }),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">CQC Evidence</h1>

      {/* Governance snapshot */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Active Policies</p>
          <p className="text-2xl font-bold">{stats?.policies_active ?? '-'}</p>
          {(stats?.policies_review_due ?? 0) > 0 && (
            <p className="text-xs text-amber-600 mt-1">{stats!.policies_review_due} review due</p>
          )}
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Events</p>
          <p className="text-2xl font-bold">{stats?.events_total ?? 0}</p>
          {(stats?.events_open ?? 0) > 0 && (
            <p className="text-xs text-amber-600 mt-1">{stats!.events_open} open</p>
          )}
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Open Risks</p>
          <p className="text-2xl font-bold">{stats?.risks_open ?? 0}</p>
          {(stats?.risks_high ?? 0) > 0 && (
            <p className="text-xs text-red-600 mt-1">{stats!.risks_high} high-rated</p>
          )}
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">New Alerts</p>
          <p className="text-2xl font-bold">{stats?.alerts_new ?? 0}</p>
        </div>
      </div>

      {/* Generate pack */}
      <div className="bg-white rounded-lg border p-5 mb-8">
        <h2 className="font-semibold text-gray-900 mb-4">Generate Evidence Pack</h2>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">From</label>
            <input
              type="date"
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
              value={periodStart}
              onChange={e => setPeriodStart(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">To</label>
            <input
              type="date"
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
              value={periodEnd}
              onChange={e => setPeriodEnd(e.target.value)}
            />
          </div>
          <button
            onClick={() => generateMutation.mutate({ period_start: periodStart, period_end: periodEnd })}
            disabled={generateMutation.isPending}
            className="flex items-center gap-2 bg-sgmc-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-sgmc-700 disabled:opacity-50"
          >
            {generateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4" />}
            Generate Pack
          </button>
        </div>
        {generateMutation.isSuccess && (
          <p className="text-sm text-green-600 mt-3">Evidence pack generated successfully.</p>
        )}
      </div>

      {/* Existing packs */}
      <h2 className="text-lg font-semibold text-gray-800 mb-3">Generated Packs</h2>
      {isLoading ? (
        <div className="text-gray-500">Loading...</div>
      ) : !packs?.length ? (
        <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
          <BarChart3 className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p>No evidence packs generated yet.</p>
          <p className="text-sm mt-1">Generate your first pack using the form above.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border divide-y">
          {packs.map(pack => (
            <Link key={pack.id} to={`/evidence/${pack.id}`} className="block p-4 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">{pack.title}</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {pack.period_start} to {pack.period_end}
                    {pack.summary && ` | ${pack.summary.policies_count ?? 0} policies, ${pack.summary.events_count ?? 0} events, ${pack.summary.risks_count ?? 0} risks`}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500">{pack.items_count} items</span>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    pack.status === 'ready' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {pack.status}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
