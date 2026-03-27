import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import {
  ArrowLeft, CheckCircle, Clock, FileText, History, Users,
  PlayCircle, PauseCircle, Archive, RotateCcw, Loader2, ThumbsUp,
} from 'lucide-react'

interface PolicyDetail {
  id: string
  title: string
  slug: string
  domain: string
  status: string
  policy_lead_email: string | null
  policy_lead_name: string | null
  review_frequency_months: number
  last_reviewed: string | null
  next_review_due: string | null
  summary: string | null
  scope: string | null
  tags: string[]
  applicable_roles: string[]
  key_workflows: Record<string, unknown> | null
  audit_checkpoints: Array<Record<string, unknown>> | null
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
  versions: Array<{
    id: string; version: string; change_summary: string | null;
    created_at: string; created_by: string | null
  }>
  cqc_mappings: Array<{
    id: string; key_question: string; quality_statement: string;
    evidence_description: string | null
  }>
  acknowledgments_count: number
  allowed_transitions: string[]
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  draft: { label: 'Draft', color: 'bg-gray-100 text-gray-700', icon: FileText },
  active: { label: 'Active', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  under_review: { label: 'Under Review', color: 'bg-amber-100 text-amber-700', icon: Clock },
  superseded: { label: 'Superseded', color: 'bg-red-100 text-red-700', icon: RotateCcw },
  archived: { label: 'Archived', color: 'bg-gray-100 text-gray-500', icon: Archive },
}

const TRANSITION_CONFIG: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  under_review: { label: 'Start Review', color: 'bg-amber-500 hover:bg-amber-600', icon: Clock },
  active: { label: 'Activate', color: 'bg-green-600 hover:bg-green-700', icon: PlayCircle },
  draft: { label: 'Return to Draft', color: 'bg-gray-500 hover:bg-gray-600', icon: RotateCcw },
  archived: { label: 'Archive', color: 'bg-red-500 hover:bg-red-600', icon: Archive },
}

const DOMAIN_LABELS: Record<string, string> = {
  patient_access: 'Patient Access',
  clinical_safety: 'Clinical Safety',
  clinical_quality: 'Clinical Quality',
  information_governance: 'Information Governance',
  patient_experience: 'Patient Experience',
  ipc_health_safety: 'IPC & Health Safety',
  workforce: 'Workforce',
  business_resilience: 'Business Resilience',
  governance: 'Governance',
}

export function PolicyDetailPage() {
  const { policyId } = useParams<{ policyId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showReviewForm, setShowReviewForm] = useState(false)
  const [changeSummary, setChangeSummary] = useState('')

  const { data: policy, isLoading } = useQuery({
    queryKey: ['policy', policyId],
    queryFn: () => api<PolicyDetail>(`/policies/${policyId}`),
    enabled: !!policyId,
  })

  const transitionMutation = useMutation({
    mutationFn: (data: { status: string; change_summary?: string }) =>
      api(`/policies/${policyId}/transition`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policy', policyId] })
      queryClient.invalidateQueries({ queryKey: ['policies'] })
    },
  })

  const reviewMutation = useMutation({
    mutationFn: (data: { change_summary?: string }) =>
      api(`/policies/${policyId}/complete-review`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policy', policyId] })
      queryClient.invalidateQueries({ queryKey: ['policies'] })
      setShowReviewForm(false)
      setChangeSummary('')
    },
  })

  const acknowledgeMutation = useMutation({
    mutationFn: () =>
      api(`/policies/${policyId}/acknowledge`, {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['policy', policyId] }),
  })

  if (isLoading) return <div className="text-gray-500">Loading policy...</div>
  if (!policy) return <div className="text-red-500">Policy not found</div>

  const statusCfg = STATUS_CONFIG[policy.status] || STATUS_CONFIG.draft
  const StatusIcon = statusCfg.icon
  const isReviewable = policy.status === 'under_review' || policy.status === 'active'

  return (
    <div>
      <Link to="/policies" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to policies
      </Link>

      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <span className={`inline-flex items-center gap-1.5 text-sm px-3 py-1 rounded-full font-medium ${statusCfg.color}`}>
                <StatusIcon className="w-3.5 h-3.5" />
                {statusCfg.label}
              </span>
              <span className="text-sm text-gray-500">{DOMAIN_LABELS[policy.domain] ?? policy.domain}</span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">{policy.title}</h1>
            {policy.summary && <p className="text-gray-600 mt-2">{policy.summary}</p>}
          </div>
        </div>

        {/* Meta row */}
        <div className="flex flex-wrap gap-6 mt-4 pt-4 border-t text-sm text-gray-600">
          <div>
            <span className="text-gray-400">Lead:</span>{' '}
            <span className="font-medium">{policy.policy_lead_name || 'Unassigned'}</span>
          </div>
          <div>
            <span className="text-gray-400">Review cycle:</span>{' '}
            <span className="font-medium">Every {policy.review_frequency_months} months</span>
          </div>
          <div>
            <span className="text-gray-400">Last reviewed:</span>{' '}
            <span className="font-medium">{policy.last_reviewed || 'Never'}</span>
          </div>
          <div>
            <span className="text-gray-400">Next review:</span>{' '}
            <span className={`font-medium ${policy.next_review_due && policy.next_review_due <= new Date().toISOString().slice(0, 10) ? 'text-red-600' : ''}`}>
              {policy.next_review_due || 'Not set'}
            </span>
          </div>
          <div>
            <span className="text-gray-400">Acknowledgments:</span>{' '}
            <span className="font-medium">{policy.acknowledgments_count}</span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t">
          {/* Status transitions */}
          {policy.allowed_transitions.map(targetStatus => {
            const cfg = TRANSITION_CONFIG[targetStatus]
            if (!cfg) return null
            const Icon = cfg.icon
            return (
              <button
                key={targetStatus}
                onClick={() => transitionMutation.mutate({ status: targetStatus })}
                disabled={transitionMutation.isPending}
                className={`flex items-center gap-1.5 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors ${cfg.color} disabled:opacity-50`}
              >
                <Icon className="w-4 h-4" />
                {cfg.label}
              </button>
            )
          })}

          {/* Complete review button */}
          {isReviewable && (
            <button
              onClick={() => setShowReviewForm(!showReviewForm)}
              className="flex items-center gap-1.5 bg-sgmc-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-sgmc-700"
            >
              <CheckCircle className="w-4 h-4" />
              Complete Review
            </button>
          )}

          {/* Acknowledge button */}
          {policy.status === 'active' && (
            <button
              onClick={() => acknowledgeMutation.mutate()}
              disabled={acknowledgeMutation.isPending}
              className="flex items-center gap-1.5 border border-sgmc-300 text-sgmc-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-sgmc-50 disabled:opacity-50"
            >
              <ThumbsUp className="w-4 h-4" />
              {acknowledgeMutation.isPending ? 'Acknowledging...' : 'Acknowledge'}
            </button>
          )}
        </div>

        {/* Review form */}
        {showReviewForm && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h3 className="font-medium text-gray-900 mb-2">Complete Policy Review</h3>
            <p className="text-sm text-gray-600 mb-3">
              This will create a new version, set the review date to today, and schedule the next review.
            </p>
            <textarea
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm mb-3"
              rows={3}
              placeholder="What changed in this review? (or 'Reviewed - no changes')"
              value={changeSummary}
              onChange={e => setChangeSummary(e.target.value)}
            />
            <div className="flex gap-2">
              <button
                onClick={() => reviewMutation.mutate({ change_summary: changeSummary || undefined })}
                disabled={reviewMutation.isPending}
                className="flex items-center gap-1.5 bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
              >
                {reviewMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                Confirm Review Complete
              </button>
              <button
                onClick={() => { setShowReviewForm(false); setChangeSummary('') }}
                className="text-gray-600 px-4 py-2 rounded-lg text-sm hover:bg-gray-100"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {transitionMutation.isError && (
          <p className="mt-3 text-sm text-red-600">{(transitionMutation.error as Error).message}</p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scope & Workflows */}
        <div className="lg:col-span-2 space-y-6">
          {policy.scope && (
            <div className="bg-white rounded-lg shadow-sm border p-5">
              <h2 className="font-semibold text-gray-900 mb-3">Scope</h2>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{policy.scope}</p>
            </div>
          )}

          {policy.audit_checkpoints && policy.audit_checkpoints.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-5">
              <h2 className="font-semibold text-gray-900 mb-3">Audit Checkpoints</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left p-2 font-medium text-gray-600">Checkpoint</th>
                      <th className="text-left p-2 font-medium text-gray-600">Frequency</th>
                      <th className="text-left p-2 font-medium text-gray-600">Method</th>
                      <th className="text-left p-2 font-medium text-gray-600">Target</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {policy.audit_checkpoints.map((cp, i) => (
                      <tr key={i}>
                        <td className="p-2">{String(cp.checkpoint || '')}</td>
                        <td className="p-2 text-gray-600">{String(cp.frequency || '')}</td>
                        <td className="p-2 text-gray-600">{String(cp.method || '')}</td>
                        <td className="p-2 text-gray-600">{String(cp.target || '')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {policy.cqc_mappings.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-5">
              <h2 className="font-semibold text-gray-900 mb-3">CQC Mappings</h2>
              {policy.cqc_mappings.map(m => (
                <div key={m.id} className="py-2 border-b last:border-0">
                  <p className="text-sm font-medium capitalize">{m.key_question}: {m.quality_statement}</p>
                  {m.evidence_description && <p className="text-xs text-gray-500 mt-1">{m.evidence_description}</p>}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar: Version history */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm border p-5">
            <h2 className="flex items-center gap-2 font-semibold text-gray-900 mb-3">
              <History className="w-4 h-4" /> Version History
            </h2>
            {policy.versions.length > 0 ? (
              <div className="space-y-3">
                {policy.versions.map((v, i) => (
                  <div key={v.id} className={`text-sm ${i === 0 ? 'pb-3 border-b' : ''}`}>
                    <div className="flex items-center gap-2">
                      <span className={`font-mono font-bold ${i === 0 ? 'text-green-700' : 'text-gray-500'}`}>
                        v{v.version}
                      </span>
                      {i === 0 && <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">latest</span>}
                    </div>
                    <p className="text-gray-600 mt-0.5">{v.change_summary || 'No description'}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {v.created_at?.slice(0, 10)} by {v.created_by || 'system'}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No versions recorded yet.</p>
            )}
          </div>

          {policy.tags && policy.tags.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-5">
              <h2 className="font-semibold text-gray-900 mb-3">Tags</h2>
              <div className="flex flex-wrap gap-2">
                {policy.tags.map(tag => (
                  <span key={tag} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">{tag}</span>
                ))}
              </div>
            </div>
          )}

          {policy.applicable_roles && policy.applicable_roles.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-5">
              <h2 className="flex items-center gap-2 font-semibold text-gray-900 mb-3">
                <Users className="w-4 h-4" /> Applicable Roles
              </h2>
              <div className="flex flex-wrap gap-2">
                {policy.applicable_roles.map(role => (
                  <span key={role} className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-full capitalize">{role}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
