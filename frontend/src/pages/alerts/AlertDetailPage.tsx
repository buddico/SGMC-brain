import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import {
  ArrowLeft, Bell, ExternalLink, Loader2, Check, Plus,
  ListChecks, CheckCircle, Clock, ShieldCheck, ShieldX,
  FileText, Mail, Users as UsersIcon,
} from 'lucide-react'

interface StaffMember { id: string; name: string; email: string; job_title: string | null; is_clinical: boolean; roles: string[] }
interface SuggestedAction { description: string; assign: string; reason: string; source: string; deadline: string }

function parseSuggestedActions(text: string): SuggestedAction[] {
  const actions: SuggestedAction[] = []
  const regex = /SUGGESTED_ACTION:\s*(.+?)\s*\|\s*ASSIGN:\s*(.+?)\s*\|\s*REASON:\s*(.+?)\s*\|\s*(?:SOURCE:\s*(.+?)\s*\|\s*)?DEADLINE:\s*(\d+)/g
  let match
  while ((match = regex.exec(text)) !== null) {
    actions.push({
      description: match[1].trim(), assign: match[2].trim(), reason: match[3].trim(),
      source: match[4]?.trim() || '', deadline: match[5].trim(),
    })
  }
  return actions
}

const SOURCE_LABELS: Record<string, string> = {
  mhra_drug: 'MHRA Drug', mhra_device: 'MHRA Device',
  drug_safety_update: 'Drug Safety Update', natpsa: 'NatPSA', cas: 'CAS',
}
const STATUS_STYLES: Record<string, string> = {
  new: 'bg-red-100 text-red-700', in_progress: 'bg-amber-100 text-amber-700',
  complete: 'bg-green-100 text-green-700', not_applicable: 'bg-gray-100 text-gray-500',
}
const PRIORITY_STYLES: Record<string, string> = {
  p1_urgent: 'bg-red-500 text-white', p2_important: 'bg-amber-400 text-black', p3_routine: 'bg-blue-100 text-blue-700',
}

export function AlertDetailPage() {
  const { alertId } = useParams<{ alertId: string }>()
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['alert', alertId] })

  const [newActionDesc, setNewActionDesc] = useState('')
  const [newActionNotes, setNewActionNotes] = useState('')
  const [newActionAssignee, setNewActionAssignee] = useState('')
  const [newActionDeadline, setNewActionDeadline] = useState('')
  const [suggestedActions, setSuggestedActions] = useState<SuggestedAction[]>([])
  const [aiResult, setAiResult] = useState<string | null>(null)
  const [aiError, setAiError] = useState<string | null>(null)
  const [suggesting, setSuggesting] = useState(false)
  const [report, setReport] = useState<any | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [pharmNotes, setPharmNotes] = useState<string | null>(null)
  const [pharmNotesEditing, setPharmNotesEditing] = useState(false)

  const { data: alert, isLoading } = useQuery({
    queryKey: ['alert', alertId],
    queryFn: () => api<any>(`/alerts/${alertId}`),
    enabled: !!alertId,
  })
  const { data: staffList } = useQuery({
    queryKey: ['staff'],
    queryFn: () => api<StaffMember[]>('/staff'),
  })

  const triageMut = useMutation({
    mutationFn: (data: { is_relevant: boolean; notes?: string }) =>
      api(`/alerts/${alertId}/triage`, { method: 'PATCH', body: JSON.stringify(data) }),
    onSuccess: () => { invalidate(); queryClient.invalidateQueries({ queryKey: ['alerts'] }) },
  })
  const addActionMut = useMutation({
    mutationFn: (data: any) => api(`/alerts/${alertId}/actions`, { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => { invalidate(); setNewActionDesc(''); setNewActionNotes(''); setNewActionAssignee(''); setNewActionDeadline('') },
  })
  const completeActionMut = useMutation({
    mutationFn: (actionId: string) => api(`/alerts/${alertId}/actions/${actionId}/complete`, { method: 'PATCH', body: '{}' }),
    onSuccess: invalidate,
  })
  const acknowledgeMut = useMutation({
    mutationFn: () => api(`/alerts/${alertId}/acknowledge`, { method: 'POST', body: '{}' }),
    onSuccess: invalidate,
  })
  const saveNotesMut = useMutation({
    mutationFn: (notes: string) => api(`/alerts/${alertId}/notes`, { method: 'PATCH', body: JSON.stringify({ pharmacist_notes: notes }) }),
    onSuccess: () => { invalidate(); setPharmNotesEditing(false) },
  })
  const manualAckMut = useMutation({
    mutationFn: (data: { ackId: string; user_email: string; method: string }) =>
      api(`/alerts/${alertId}/acknowledge/${data.ackId}`, {
        method: 'PATCH', body: JSON.stringify({ user_email: data.user_email, method: data.method }),
      }),
    onSuccess: invalidate,
  })

  const handleSuggestActions = async () => {
    setSuggesting(true); setAiError(null); setAiResult(null); setSuggestedActions([])
    try {
      const res = await api<any>(`/alerts/${alertId}/suggest-actions`, { method: 'POST' })
      const summary = res.summary || ''
      setAiResult(summary)
      setSuggestedActions(parseSuggestedActions(summary))
    } catch (err: any) {
      setAiError(err.message || 'Agent unavailable')
    } finally {
      setSuggesting(false)
    }
  }

  const addSuggestedAction = (sa: SuggestedAction) => {
    const deadlineDate = new Date()
    deadlineDate.setDate(deadlineDate.getDate() + parseInt(sa.deadline || '7'))
    addActionMut.mutate({
      action_type: 'ai_suggested',
      description: sa.description,
      notes: `Reason: ${sa.reason}\nSource: ${sa.source}`,
      assigned_to_name: sa.assign,
      assigned_to_email: staffList?.find(s => s.name === sa.assign)?.email,
      deadline: deadlineDate.toISOString().slice(0, 10),
    })
    setSuggestedActions(prev => prev.filter(a => a.description !== sa.description))
  }

  const handleGenerateReport = async () => {
    setReportLoading(true)
    try {
      const r = await api<any>(`/alerts/${alertId}/report`)
      setReport(r)
    } finally {
      setReportLoading(false)
    }
  }

  if (isLoading) return <div className="text-gray-500">Loading alert...</div>
  if (!alert) return <div className="text-red-500">Alert not found</div>

  const isUntriaged = alert.is_relevant === null
  const isRelevant = alert.is_relevant === true
  const acks = alert.acknowledgments || []
  const ackedCount = acks.filter((a: any) => a.acknowledged_at).length
  const realActions = (alert.actions || []).filter((a: any) => a.action_type !== 'triage_relevance')
  const completedActions = realActions.filter((a: any) => a.completed_at)
  const allActionsComplete = realActions.length > 0 && completedActions.length === realActions.length

  return (
    <div>
      <Link to="/alerts" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to alerts
      </Link>

      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <div className="flex items-center gap-3 mb-2 flex-wrap">
          <span className="text-xs bg-gray-100 px-2 py-1 rounded-full">{SOURCE_LABELS[alert.source] ?? alert.source}</span>
          {alert.severity && <span className="text-xs bg-red-50 text-red-600 px-2 py-0.5 rounded-full">{alert.severity}</span>}
          {alert.priority && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_STYLES[alert.priority] ?? ''}`}>
              {alert.priority.replace('_', ' ').toUpperCase()}
            </span>
          )}
          <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${STATUS_STYLES[alert.status] ?? ''}`}>
            {alert.status.replace('_', ' ')}
          </span>
          {alert.is_relevant === true && <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Relevant</span>}
          {alert.is_relevant === false && <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">Not Relevant</span>}
        </div>
        <h1 className="text-2xl font-bold text-gray-900">{alert.title}</h1>
        <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
          {alert.issued_date && <span>Issued: {alert.issued_date}</span>}
          {alert.message_type && <span>Type: {alert.message_type}</span>}
          {alert.triaged_by_name && <span>Triaged by: {alert.triaged_by_name}</span>}
        </div>
      </div>

      {/* Triage banner */}
      {isUntriaged && (
        <div className="bg-purple-50 border-2 border-purple-300 rounded-lg p-5 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-purple-900 text-lg flex items-center gap-2">
                <Bell className="w-5 h-5" /> Triage Required
              </h2>
              <p className="text-sm text-purple-700 mt-1">
                Is this alert relevant to Stroud Green Medical Clinic? Marking as relevant will notify all clinical staff.
              </p>
            </div>
            <div className="flex gap-3 shrink-0 ml-4">
              <button onClick={() => triageMut.mutate({ is_relevant: true })}
                disabled={triageMut.isPending}
                className="flex items-center gap-2 bg-green-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-green-700 disabled:opacity-50">
                <ShieldCheck className="w-5 h-5" /> Relevant
              </button>
              <button onClick={() => triageMut.mutate({ is_relevant: false })}
                disabled={triageMut.isPending}
                className="flex items-center gap-2 bg-gray-200 text-gray-700 px-5 py-2.5 rounded-lg font-medium hover:bg-gray-300 disabled:opacity-50">
                <ShieldX className="w-5 h-5" /> Not Relevant
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Completion banner */}
      {allActionsComplete && alert.status === 'complete' && (
        <div className="bg-green-50 border-2 border-green-300 rounded-lg p-5 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-green-900 text-lg flex items-center gap-2">
                <CheckCircle className="w-5 h-5" /> All Actions Complete
              </h2>
              <p className="text-sm text-green-700 mt-1">
                All {realActions.length} actions have been completed. Generate a completion report for your records.
              </p>
            </div>
            <button onClick={handleGenerateReport} disabled={reportLoading}
              className="flex items-center gap-2 bg-green-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 shrink-0 ml-4">
              {reportLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <FileText className="w-5 h-5" />}
              Generate Report
            </button>
          </div>
        </div>
      )}

      {/* Report display */}
      {report && (
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Alert Completion Report</h2>
            <button onClick={() => window.print()} className="text-xs text-sgmc-600 hover:underline">Print</button>
          </div>
          <div className="border-b pb-3 mb-3">
            <p className="text-sm"><strong>Alert:</strong> {report.title}</p>
            <p className="text-sm"><strong>Source:</strong> {SOURCE_LABELS[report.source] ?? report.source}</p>
            <p className="text-sm"><strong>Issued:</strong> {report.issued_date || 'N/A'}</p>
            <p className="text-sm"><strong>Triaged by:</strong> {report.triage?.triaged_by} on {report.triage?.triaged_at?.slice(0, 10)}</p>
          </div>
          <div className="border-b pb-3 mb-3">
            <h3 className="font-medium text-sm mb-2">Actions ({report.actions_summary?.completed}/{report.actions_summary?.total} completed)</h3>
            {report.actions?.map((a: any, i: number) => (
              <div key={i} className={`text-sm py-1 ${a.completed_at ? '' : 'text-amber-700'}`}>
                <span className="mr-2">{a.completed_at ? '✓' : '○'}</span>
                {a.description || a.action_type}
                {a.assigned_to && <span className="text-gray-500"> — {a.assigned_to}</span>}
                {a.completed_at && <span className="text-gray-400 text-xs ml-2">completed {a.completed_at.slice(0, 10)} by {a.completed_by}</span>}
              </div>
            ))}
          </div>
          <div>
            <h3 className="font-medium text-sm mb-2">Read Receipts ({report.acknowledgments_summary?.acknowledged}/{report.acknowledgments_summary?.total})</h3>
            {report.acknowledgments?.map((a: any, i: number) => (
              <div key={i} className="text-sm py-0.5">
                <span className="mr-2">{a.acknowledged_at ? '✓' : '○'}</span>
                {a.name}
                {a.acknowledged_at && <span className="text-gray-400 text-xs ml-2">{a.acknowledged_at.slice(0, 10)} via {a.method}</span>}
                {!a.acknowledged_at && <span className="text-amber-600 text-xs ml-2">pending</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">

          {/* Alert content */}
          <div className="bg-white rounded-lg shadow-sm border p-5">
            <h2 className="font-semibold text-gray-900 mb-3">Alert Content</h2>
            {alert.summary && <p className="text-sm text-gray-700 whitespace-pre-wrap mb-3">{alert.summary}</p>}
            {alert.html_content && (
              <div className="prose prose-sm max-w-none text-gray-700" dangerouslySetInnerHTML={{ __html: alert.html_content }} />
            )}
            {alert.url && (
              <a href={alert.url} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-sgmc-600 hover:underline mt-3">
                <ExternalLink className="w-4 h-4" /> View full alert on GOV.UK
              </a>
            )}
          </div>

          {/* Pharmacist Notes */}
          {isRelevant && (
            <div className="bg-white rounded-lg shadow-sm border p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="flex items-center gap-2 font-semibold text-gray-900">
                  <FileText className="w-4 h-4" /> Pharmacist Notes
                </h2>
                {!pharmNotesEditing && (
                  <button onClick={() => { setPharmNotes(alert.pharmacist_notes || ''); setPharmNotesEditing(true) }}
                    className="text-xs text-sgmc-600 hover:underline">
                    {alert.pharmacist_notes ? 'Edit' : 'Add Notes'}
                  </button>
                )}
              </div>
              <p className="text-xs text-gray-500 mb-2">
                Summarise the relevant parts of this alert for the practice. AI suggestions will be based on what you write here.
              </p>
              {alert.pharmacist_notes && !pharmNotesEditing && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">{alert.pharmacist_notes}</p>
                </div>
              )}
              {pharmNotesEditing && (
                <div className="space-y-2">
                  <textarea className="w-full rounded-lg border px-3 py-2 text-sm" rows={5}
                    placeholder="Describe the relevant details of this alert, e.g. which drugs are affected, what action MHRA recommends, which patients might be impacted at our practice..."
                    value={pharmNotes ?? ''} onChange={e => setPharmNotes(e.target.value)} />
                  <div className="flex gap-2">
                    <button onClick={() => saveNotesMut.mutate(pharmNotes || '')}
                      disabled={saveNotesMut.isPending}
                      className="text-sm bg-sgmc-600 text-white px-4 py-2 rounded-lg hover:bg-sgmc-700 disabled:opacity-50">
                      {saveNotesMut.isPending ? 'Saving...' : 'Save Notes'}
                    </button>
                    <button onClick={() => setPharmNotesEditing(false)}
                      className="text-sm text-gray-500 px-4 py-2 rounded-lg hover:bg-gray-100">Cancel</button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="bg-white rounded-lg shadow-sm border p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="flex items-center gap-2 font-semibold text-gray-900">
                <Check className="w-4 h-4" /> Actions
                {realActions.length > 0 && (
                  <span className="text-xs text-gray-500 font-normal">
                    ({completedActions.length}/{realActions.length} complete)
                  </span>
                )}
              </h2>
              {isRelevant && (
                <button onClick={handleSuggestActions} disabled={suggesting}
                  className="flex items-center gap-1 text-xs bg-purple-50 text-purple-700 px-3 py-1.5 rounded-lg hover:bg-purple-100 disabled:opacity-50">
                  {suggesting ? <Loader2 className="w-3 h-3 animate-spin" /> : <ListChecks className="w-3 h-3" />}
                  AI Suggest Actions
                </button>
              )}
            </div>

            {aiError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-3 text-sm">
                <p className="text-red-600">{aiError}</p>
              </div>
            )}

            {/* AI suggested actions */}
            {suggestedActions.length > 0 && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-medium text-purple-800">AI Suggested Actions</p>
                  <div className="flex gap-2">
                    <button onClick={() => suggestedActions.forEach(sa => addSuggestedAction(sa))}
                      className="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700">Accept All</button>
                    <button onClick={() => setSuggestedActions([])}
                      className="text-xs bg-gray-200 text-gray-700 px-3 py-1 rounded hover:bg-gray-300">Dismiss All</button>
                  </div>
                </div>
                {suggestedActions.map((sa, i) => (
                  <div key={i} className="bg-white rounded-lg border border-purple-200 p-3 mb-2">
                    <p className="text-sm font-medium text-gray-900">{sa.description}</p>
                    <p className="text-xs text-purple-600 mt-1">Assign: <strong>{sa.assign}</strong> — {sa.reason}</p>
                    {sa.source && (
                      <p className="text-xs mt-1">
                        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded ${
                          sa.source.startsWith('MHRA:') ? 'bg-red-50 text-red-700'
                          : sa.source.startsWith('POLICY:') ? 'bg-blue-50 text-blue-700'
                          : sa.source.startsWith('NICE:') ? 'bg-green-50 text-green-700'
                          : sa.source.startsWith('BNF:') ? 'bg-indigo-50 text-indigo-700'
                          : sa.source.startsWith('CQC:') ? 'bg-amber-50 text-amber-700'
                          : 'bg-gray-50 text-gray-600'
                        }`}>{sa.source}</span>
                      </p>
                    )}
                    <p className="text-xs text-gray-500 mt-1">Deadline: {sa.deadline} days</p>
                    <div className="flex gap-2 mt-2">
                      <button onClick={() => addSuggestedAction(sa)}
                        className="flex items-center gap-1 text-xs bg-green-600 text-white px-3 py-1.5 rounded hover:bg-green-700">
                        <Check className="w-3 h-3" /> Accept
                      </button>
                      <button onClick={() => setSuggestedActions(prev => prev.filter((_, idx) => idx !== i))}
                        className="text-xs bg-gray-100 text-gray-600 px-3 py-1.5 rounded hover:bg-gray-200">Reject</button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {aiResult && !suggestedActions.length && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-3 text-sm">
                <p className="text-xs font-medium text-purple-700 mb-1">AI Result:</p>
                <p className="text-gray-700 whitespace-pre-wrap text-xs">{aiResult.replace(/\[Cost:.*?\]/g, '').trim().slice(0, 600)}</p>
              </div>
            )}

            {/* Existing actions */}
            {realActions.length > 0 && (
              <div className="space-y-2 mb-4">
                {realActions.map((a: any) => (
                  <div key={a.id} className={`flex items-start justify-between rounded-lg border p-3 ${a.completed_at ? 'bg-green-50 border-green-200' : 'bg-white'}`}>
                    <div className="flex-1">
                      <p className={`text-sm ${a.completed_at ? 'line-through text-gray-500' : 'text-gray-900 font-medium'}`}>
                        {a.description || a.notes || a.action_type}
                      </p>
                      <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                        {a.assigned_to_name && <span>Assigned: {a.assigned_to_name}</span>}
                        {a.deadline && <span>Due: {a.deadline}</span>}
                        {a.completed_at && <span className="text-green-600">Done: {a.completed_at.slice(0, 10)} by {a.completed_by}</span>}
                      </div>
                      {a.notes && a.description && (
                        <p className="text-xs text-gray-500 mt-1 whitespace-pre-wrap">{a.notes}</p>
                      )}
                    </div>
                    {!a.completed_at && (
                      <button onClick={() => completeActionMut.mutate(a.id)}
                        className="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 ml-2 shrink-0">
                        Done
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Add action form */}
            {isRelevant && (
              <div className="border-t pt-3 space-y-2">
                <input type="text" className="w-full rounded-lg border px-3 py-2 text-sm"
                  placeholder="Action description..."
                  value={newActionDesc} onChange={e => setNewActionDesc(e.target.value)} />
                <div className="flex gap-2">
                  <select className="flex-1 rounded-lg border px-3 py-2 text-sm"
                    value={newActionAssignee} onChange={e => setNewActionAssignee(e.target.value)}>
                    <option value="">Assign to...</option>
                    {staffList?.map(s => (
                      <option key={s.id} value={s.name}>{s.name} — {s.job_title}</option>
                    ))}
                  </select>
                  <input type="date" className="rounded-lg border px-3 py-2 text-sm"
                    value={newActionDeadline} onChange={e => setNewActionDeadline(e.target.value)} />
                </div>
                <textarea className="w-full rounded-lg border px-3 py-2 text-sm" rows={2}
                  placeholder="Notes (optional)..." value={newActionNotes} onChange={e => setNewActionNotes(e.target.value)} />
                <button onClick={() => addActionMut.mutate({
                    action_type: 'manual',
                    description: newActionDesc,
                    notes: newActionNotes || undefined,
                    assigned_to_name: newActionAssignee || undefined,
                    assigned_to_email: staffList?.find(s => s.name === newActionAssignee)?.email,
                    deadline: newActionDeadline || undefined,
                  })}
                  disabled={!newActionDesc || addActionMut.isPending}
                  className="flex items-center gap-1 bg-sgmc-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-sgmc-700 disabled:opacity-50">
                  <Plus className="w-3.5 h-3.5" /> Add Action
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Acknowledgments / Read Receipts */}
          {acks.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-5">
              <h2 className="flex items-center gap-2 font-semibold text-gray-900 mb-3">
                <CheckCircle className="w-4 h-4" /> Read Receipts
                <span className="text-xs text-gray-500 font-normal">({ackedCount}/{acks.length})</span>
              </h2>
              <div className="space-y-2">
                {acks.map((ack: any) => (
                  <div key={ack.id} className={`flex items-center justify-between py-1.5 px-2 rounded ${ack.acknowledged_at ? 'bg-green-50' : 'bg-amber-50'}`}>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900">{ack.user_name}</p>
                      {ack.acknowledged_at ? (
                        <p className="text-[10px] text-green-600">{ack.acknowledged_at.slice(0, 10)} via {ack.method || 'in_app'}</p>
                      ) : (
                        <p className="text-[10px] text-amber-600">Pending</p>
                      )}
                    </div>
                    <div className="flex items-center gap-1 shrink-0 ml-2">
                      {ack.acknowledged_at ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : (
                        <>
                          <button onClick={() => manualAckMut.mutate({ ackId: ack.id, user_email: ack.user_email, method: 'email' })}
                            className="text-[10px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded hover:bg-blue-100"
                            title="Mark as read via email">
                            <Mail className="w-3 h-3" />
                          </button>
                          <button onClick={() => manualAckMut.mutate({ ackId: ack.id, user_email: ack.user_email, method: 'clinical_meeting' })}
                            className="text-[10px] bg-purple-50 text-purple-700 px-1.5 py-0.5 rounded hover:bg-purple-100"
                            title="Mark as read at clinical meeting">
                            <UsersIcon className="w-3 h-3" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <button onClick={() => acknowledgeMut.mutate()}
                disabled={acknowledgeMut.isPending}
                className="w-full mt-3 flex items-center justify-center gap-2 bg-sgmc-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-sgmc-700 disabled:opacity-50">
                {acknowledgeMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                I've Read This Alert
              </button>

              {/* Bulk mark at clinical meeting */}
              {acks.some((a: any) => !a.acknowledged_at) && (
                <button onClick={() => {
                  acks.filter((a: any) => !a.acknowledged_at).forEach((ack: any) => {
                    manualAckMut.mutate({ ackId: ack.id, user_email: ack.user_email, method: 'clinical_meeting' })
                  })
                }}
                  className="w-full mt-2 flex items-center justify-center gap-2 bg-purple-50 text-purple-700 py-2 rounded-lg text-sm font-medium hover:bg-purple-100">
                  <UsersIcon className="w-4 h-4" /> Mark All — Clinical Meeting
                </button>
              )}
            </div>
          )}

          {/* Alert metadata */}
          <div className="bg-white rounded-lg shadow-sm border p-5">
            <h2 className="font-semibold text-gray-900 mb-3">Details</h2>
            <dl className="space-y-2 text-sm">
              <div><dt className="text-xs text-gray-500">Source</dt><dd>{SOURCE_LABELS[alert.source] ?? alert.source}</dd></div>
              {alert.message_type && <div><dt className="text-xs text-gray-500">Message Type</dt><dd>{alert.message_type}</dd></div>}
              {alert.issued_date && <div><dt className="text-xs text-gray-500">Issued</dt><dd>{alert.issued_date}</dd></div>}
              {alert.severity && <div><dt className="text-xs text-gray-500">Severity</dt><dd>{alert.severity}</dd></div>}
              <div><dt className="text-xs text-gray-500">First Seen</dt><dd>{alert.created_at?.slice(0, 10)}</dd></div>
            </dl>
            {alert.url && (
              <a href={alert.url} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-sm text-sgmc-600 hover:underline mt-3">
                <ExternalLink className="w-4 h-4" /> GOV.UK Source
              </a>
            )}
          </div>

          {/* Generate report (also available when not all complete) */}
          {isRelevant && !allActionsComplete && realActions.length > 0 && (
            <button onClick={handleGenerateReport} disabled={reportLoading}
              className="w-full flex items-center justify-center gap-2 bg-gray-100 text-gray-700 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-200 disabled:opacity-50">
              {reportLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
              Generate Progress Report
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
