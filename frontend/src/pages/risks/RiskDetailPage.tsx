import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { LinkSelector } from '@/components/LinkSelector'
import { ArrowLeft, FileText, AlertTriangle, Save, Loader2, ClipboardCheck, Plus } from 'lucide-react'

function riskColor(score: number): string {
  if (score >= 15) return 'bg-red-500 text-white'
  if (score >= 8) return 'bg-amber-400 text-black'
  if (score >= 4) return 'bg-yellow-300 text-black'
  return 'bg-green-400 text-black'
}

const STATUS_STYLES: Record<string, string> = {
  open: 'bg-red-100 text-red-700',
  mitigated: 'bg-amber-100 text-amber-700',
  closed: 'bg-green-100 text-green-700',
  escalated: 'bg-purple-100 text-purple-700',
}

export function RiskDetailPage() {
  const { riskId } = useParams<{ riskId: string }>()
  const queryClient = useQueryClient()
  const [linkedPolicies, setLinkedPolicies] = useState<string[] | null>(null)
  const [linkedEvents, setLinkedEvents] = useState<string[] | null>(null)
  const [showReview, setShowReview] = useState(false)
  const [reviewNotes, setReviewNotes] = useState('')
  const [reviewL, setReviewL] = useState<number | null>(null)
  const [reviewI, setReviewI] = useState<number | null>(null)

  const { data: risk, isLoading } = useQuery({
    queryKey: ['risk', riskId],
    queryFn: () => api<any>(`/risks/${riskId}`),
    enabled: !!riskId,
  })

  const linkMutation = useMutation({
    mutationFn: (data: any) =>
      api(`/risks/${riskId}/links`, { method: 'PUT', body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk', riskId] })
      setLinkedPolicies(null)
      setLinkedEvents(null)
    },
  })

  const reviewMutation = useMutation({
    mutationFn: (data: any) =>
      api(`/risks/${riskId}/reviews`, { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk', riskId] })
      setShowReview(false)
      setReviewNotes('')
      setReviewL(null)
      setReviewI(null)
    },
  })

  if (isLoading) return <div className="text-gray-500">Loading risk...</div>
  if (!risk) return <div className="text-red-500">Risk not found</div>

  const currentPolicies = linkedPolicies ?? risk.linked_policy_ids ?? []
  const currentEvents = linkedEvents ?? risk.linked_event_ids ?? []
  const hasLinkChanges = linkedPolicies !== null || linkedEvents !== null

  return (
    <div>
      <Link to="/risks" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to risk register
      </Link>

      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <span className="font-mono text-sm text-gray-500">{risk.reference}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_STYLES[risk.status] ?? ''}`}>{risk.status}</span>
              <span className="text-sm text-gray-500 capitalize">{risk.category.replace(/_/g, ' ')}</span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">{risk.title}</h1>
            <p className="text-gray-600 mt-2">{risk.description}</p>
          </div>
          <div className={`w-16 h-16 rounded-lg flex items-center justify-center text-2xl font-bold ${riskColor(risk.risk_score)}`}>
            {risk.risk_score}
          </div>
        </div>

        {/* Risk matrix display */}
        <div className="flex flex-wrap gap-6 mt-4 pt-4 border-t text-sm text-gray-600">
          <div>
            <span className="text-gray-400">Likelihood:</span>{' '}
            <span className="font-medium">{risk.likelihood}/5</span>
          </div>
          <div>
            <span className="text-gray-400">Impact:</span>{' '}
            <span className="font-medium">{risk.impact}/5</span>
          </div>
          <div>
            <span className="text-gray-400">Owner:</span>{' '}
            <span className="font-medium">{risk.owner_name}</span>
          </div>
          <div>
            <span className="text-gray-400">Identified:</span>{' '}
            <span className="font-medium">{risk.date_identified}</span>
          </div>
          <div>
            <span className="text-gray-400">Last reviewed:</span>{' '}
            <span className="font-medium">{risk.last_reviewed ?? 'Never'}</span>
          </div>
          <div>
            <span className="text-gray-400">Next review:</span>{' '}
            <span className={`font-medium ${risk.next_review_due && risk.next_review_due <= new Date().toISOString().slice(0, 10) ? 'text-red-600' : ''}`}>
              {risk.next_review_due ?? 'Not set'}
            </span>
          </div>
        </div>

        {/* Review button */}
        <div className="mt-4 pt-4 border-t">
          <button
            onClick={() => setShowReview(!showReview)}
            className="flex items-center gap-1.5 bg-sgmc-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-sgmc-700"
          >
            <ClipboardCheck className="w-4 h-4" /> Record Review
          </button>
        </div>

        {showReview && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h3 className="font-medium text-gray-900 mb-3">Risk Review</h3>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Likelihood (1-5)</label>
                <input type="number" min={1} max={5} className="w-full rounded border px-3 py-2 text-sm"
                  value={reviewL ?? risk.likelihood} onChange={e => setReviewL(Number(e.target.value))} />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Impact (1-5)</label>
                <input type="number" min={1} max={5} className="w-full rounded border px-3 py-2 text-sm"
                  value={reviewI ?? risk.impact} onChange={e => setReviewI(Number(e.target.value))} />
              </div>
            </div>
            <textarea className="w-full rounded border px-3 py-2 text-sm mb-3" rows={3}
              placeholder="Review notes..." value={reviewNotes} onChange={e => setReviewNotes(e.target.value)} />
            <button
              onClick={() => reviewMutation.mutate({
                likelihood_after: reviewL, impact_after: reviewI, notes: reviewNotes || undefined,
              })}
              disabled={reviewMutation.isPending}
              className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {reviewMutation.isPending ? 'Saving...' : 'Save Review'}
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Controls & Gaps */}
          <div className="bg-white rounded-lg shadow-sm border p-5">
            <h2 className="font-semibold text-gray-900 mb-3">Controls & Gaps</h2>
            {risk.existing_controls && (
              <div className="mb-3">
                <h3 className="text-xs font-medium text-gray-500 uppercase">Existing Controls</h3>
                <p className="text-sm mt-1 whitespace-pre-wrap">{risk.existing_controls}</p>
              </div>
            )}
            {risk.gaps_in_control && (
              <div>
                <h3 className="text-xs font-medium text-red-500 uppercase">Gaps in Control</h3>
                <p className="text-sm mt-1 whitespace-pre-wrap">{risk.gaps_in_control}</p>
              </div>
            )}
            {!risk.existing_controls && !risk.gaps_in_control && (
              <p className="text-sm text-gray-500">No controls or gaps documented yet.</p>
            )}
          </div>

          {/* Actions */}
          <div className="bg-white rounded-lg shadow-sm border p-5">
            <h2 className="font-semibold text-gray-900 mb-3">Mitigation Actions</h2>
            {risk.actions?.length > 0 ? risk.actions.map((a: any) => (
              <div key={a.id} className="flex items-center justify-between py-2 border-b last:border-0">
                <div>
                  <p className="text-sm">{a.description}</p>
                  <p className="text-xs text-gray-500">{a.assigned_to_name ?? 'Unassigned'} | Due: {a.target_date ?? 'N/A'}</p>
                </div>
                {a.completed_at ? (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Done</span>
                ) : (
                  <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">Pending</span>
                )}
              </div>
            )) : (
              <p className="text-sm text-gray-500">No mitigation actions yet.</p>
            )}
          </div>

          {/* Review history */}
          {risk.reviews?.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-5">
              <h2 className="font-semibold text-gray-900 mb-3">Review History</h2>
              {risk.reviews.map((rv: any) => (
                <div key={rv.id} className="py-2 border-b last:border-0 text-sm">
                  <div className="flex items-center gap-3">
                    <span className="text-gray-600">{rv.review_date}</span>
                    <span className="font-medium">Score: {rv.score_after}</span>
                    <span className="text-gray-500">by {rv.reviewed_by_name}</span>
                  </div>
                  {rv.notes && <p className="text-gray-600 mt-1">{rv.notes}</p>}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar: Links */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm border p-5">
            <h2 className="flex items-center gap-2 font-semibold text-gray-900 mb-3">
              <FileText className="w-4 h-4" /> Linked Policies
            </h2>
            {risk.linked_policies?.map((p: any) => (
              <Link key={p.id} to={`/policies/${p.id}`} className="block py-1.5 text-sm text-sgmc-600 hover:underline">
                {p.title}
              </Link>
            ))}
            <div className="mt-2">
              <LinkSelector type="policy" selectedIds={currentPolicies} onChange={ids => setLinkedPolicies(ids)} />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border p-5">
            <h2 className="flex items-center gap-2 font-semibold text-gray-900 mb-3">
              <AlertTriangle className="w-4 h-4" /> Linked Events
            </h2>
            {risk.linked_events?.map((e: any) => (
              <Link key={e.id} to={`/events/${e.id}`} className="block py-1.5 text-sm">
                <span className="text-sgmc-600 hover:underline">{e.reference}: {e.title}</span>
                {e.severity && (
                  <span className={`ml-2 text-xs px-1.5 py-0.5 rounded ${
                    e.severity === 'severe' || e.severity === 'catastrophic' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                  }`}>{e.severity}</span>
                )}
              </Link>
            ))}
            <div className="mt-2">
              <LinkSelector type="event" selectedIds={currentEvents} onChange={ids => setLinkedEvents(ids)} excludeId={riskId} />
            </div>
          </div>

          {hasLinkChanges && (
            <button
              onClick={() => linkMutation.mutate({
                linked_policy_ids: linkedPolicies ?? undefined,
                linked_event_ids: linkedEvents ?? undefined,
              })}
              disabled={linkMutation.isPending}
              className="w-full flex items-center justify-center gap-2 bg-sgmc-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-sgmc-700 disabled:opacity-50"
            >
              {linkMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save Links
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
