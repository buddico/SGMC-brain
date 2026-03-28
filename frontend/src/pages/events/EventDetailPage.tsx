import { useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { LinkSelector } from '@/components/LinkSelector'
import {
  ArrowLeft, FileText, ShieldAlert, History, Save, Loader2,
  Plus, Check, UserPlus, MessageSquare, BookOpen, Lock, Sparkles, X, Users,
  Search, ListChecks,
} from 'lucide-react'

interface StaffMember { id: string; name: string; email: string; job_title: string | null; is_clinical: boolean; roles: string[] }
interface SuggestedAction { description: string; assign: string; reason: string; source: string; deadline: string }

const STATUS_FLOW = ['draft', 'submitted', 'under_investigation', 'discussed', 'actions_assigned', 'closed']
const STATUS_LABELS: Record<string, string> = {
  draft: 'Draft', submitted: 'Submitted', under_investigation: 'Under Investigation',
  discussed: 'Discussed', actions_assigned: 'Actions Assigned', closed: 'Closed',
}
const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-200 text-gray-700', submitted: 'bg-blue-200 text-blue-800',
  under_investigation: 'bg-amber-200 text-amber-800', discussed: 'bg-purple-200 text-purple-800',
  actions_assigned: 'bg-orange-200 text-orange-800', closed: 'bg-green-200 text-green-800',
}

function parseSuggestedActions(text: string): SuggestedAction[] {
  const actions: SuggestedAction[] = []
  // Match with optional SOURCE field for backwards compatibility
  const regex = /SUGGESTED_ACTION:\s*(.+?)\s*\|\s*ASSIGN:\s*(.+?)\s*\|\s*REASON:\s*(.+?)\s*\|\s*(?:SOURCE:\s*(.+?)\s*\|\s*)?DEADLINE:\s*(\d+)/g
  let match
  while ((match = regex.exec(text)) !== null) {
    actions.push({
      description: match[1].trim(),
      assign: match[2].trim(),
      reason: match[3].trim(),
      source: match[4]?.trim() || '',
      deadline: match[5].trim(),
    })
  }
  return actions
}

export function EventDetailPage() {
  const { eventId } = useParams<{ eventId: string }>()
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['event', eventId] })

  const [ixNotes, setIxNotes] = useState('')
  const [meetingDate, setMeetingDate] = useState('')
  const [meetingNotes, setMeetingNotes] = useState('')
  const [newAction, setNewAction] = useState('')
  const [actionAssignee, setActionAssignee] = useState('')
  const [actionDeadline, setActionDeadline] = useState('')
  const [learning, setLearning] = useState('')
  const [linkedPolicies, setLinkedPolicies] = useState<string[] | null>(null)
  const [linkedRisks, setLinkedRisks] = useState<string[] | null>(null)

  // AI Triage state (links only)
  const [triageResult, setTriageResult] = useState<string | null>(null)
  const [triageError, setTriageError] = useState<string | null>(null)
  const [triaging, setTriaging] = useState(false)

  // AI Investigation state
  const [investigationSuggestion, setInvestigationSuggestion] = useState<string | null>(null)
  const [investigationError, setInvestigationError] = useState<string | null>(null)
  const [suggestingInvestigation, setSuggestingInvestigation] = useState(false)

  // AI Actions state
  const [suggestedActions, setSuggestedActions] = useState<SuggestedAction[]>([])
  const [actionsResult, setActionsResult] = useState<string | null>(null)
  const [actionsError, setActionsError] = useState<string | null>(null)
  const [suggestingActions, setSuggestingActions] = useState(false)

  const { data: event, isLoading } = useQuery({
    queryKey: ['event', eventId],
    queryFn: () => api<any>(`/events/${eventId}`),
    enabled: !!eventId,
  })
  const { data: staffList } = useQuery({
    queryKey: ['staff'],
    queryFn: () => api<StaffMember[]>('/staff'),
  })

  // Compute prioritised staff list for action assignment
  const prioritisedStaff = useMemo(() => {
    if (!staffList || !event) return { involved: [] as StaffMember[], policyLeads: [] as StaffMember[], other: [] as StaffMember[] }

    const involvedEmails = new Set((event.involved_staff || []).map((s: any) => s.email))
    const policyLeadEmails = new Set(
      (event.linked_policies || []).map((p: any) => p.policy_lead_email).filter(Boolean)
    )
    // Reporter
    involvedEmails.add(event.reported_by_email)

    const involved: StaffMember[] = []
    const policyLeads: StaffMember[] = []
    const other: StaffMember[] = []

    for (const s of staffList) {
      if (involvedEmails.has(s.email)) {
        involved.push(s)
      } else if (policyLeadEmails.has(s.email)) {
        policyLeads.push(s)
      } else {
        other.push(s)
      }
    }
    return { involved, policyLeads, other }
  }, [staffList, event])

  const investigateMut = useMutation({
    mutationFn: (data: any) => api(`/events/${eventId}/investigate`, { method: 'PATCH', body: JSON.stringify(data) }),
    onSuccess: () => { invalidate(); setIxNotes('') },
  })
  const discussMut = useMutation({
    mutationFn: (data: any) => api(`/events/${eventId}/discussion`, { method: 'PATCH', body: JSON.stringify(data) }),
    onSuccess: () => { invalidate(); setMeetingDate(''); setMeetingNotes('') },
  })
  const addActionMut = useMutation({
    mutationFn: (data: any) => api(`/events/${eventId}/actions`, { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => { invalidate(); setNewAction(''); setActionAssignee(''); setActionDeadline('') },
  })
  const completeActionMut = useMutation({
    mutationFn: (actionId: string) => api(`/events/${eventId}/actions/${actionId}/complete`, { method: 'PATCH', body: '{}' }),
    onSuccess: invalidate,
  })
  const closeMut = useMutation({
    mutationFn: (data: any) => api(`/events/${eventId}/close`, { method: 'PATCH', body: JSON.stringify(data) }),
    onSuccess: invalidate,
  })
  const linkMut = useMutation({
    mutationFn: (data: any) => api(`/events/${eventId}/links`, { method: 'PUT', body: JSON.stringify(data) }),
    onSuccess: () => { invalidate(); setLinkedPolicies(null); setLinkedRisks(null) },
  })
  const involvedMut = useMutation({
    mutationFn: (data: any) => api(`/events/${eventId}/involved-staff`, { method: 'PUT', body: JSON.stringify(data) }),
    onSuccess: invalidate,
  })

  // AI Triage — links policies and risks only
  const handleTriage = async () => {
    setTriaging(true); setTriageError(null); setTriageResult(null)
    try {
      const res = await api<any>(`/events/${eventId}/triage`, { method: 'POST' })
      setTriageResult(res.summary || 'Triage complete — policies and risks linked.')
      invalidate()
    } catch (err: any) {
      setTriageError(err.message || 'Agent unavailable')
    } finally {
      setTriaging(false)
    }
  }

  // AI Suggest Investigation
  const handleSuggestInvestigation = async () => {
    setSuggestingInvestigation(true); setInvestigationError(null); setInvestigationSuggestion(null)
    try {
      const res = await api<any>(`/events/${eventId}/suggest-investigation`, { method: 'POST' })
      const summary = res.summary || ''
      // Strip the cost line from the suggestion
      const cleaned = summary.replace(/\[Cost:.*?\]/g, '').trim()
      setInvestigationSuggestion(cleaned)
    } catch (err: any) {
      setInvestigationError(err.message || 'Agent unavailable')
    } finally {
      setSuggestingInvestigation(false)
    }
  }

  // AI Suggest Actions
  const handleSuggestActions = async () => {
    setSuggestingActions(true); setActionsError(null); setActionsResult(null); setSuggestedActions([])
    try {
      const res = await api<any>(`/events/${eventId}/suggest-actions`, { method: 'POST' })
      const summary = res.summary || ''
      setActionsResult(summary)
      setSuggestedActions(parseSuggestedActions(summary))
    } catch (err: any) {
      setActionsError(err.message || 'Agent unavailable')
    } finally {
      setSuggestingActions(false)
    }
  }

  const addSuggestedAction = (sa: SuggestedAction) => {
    const deadlineDate = new Date()
    deadlineDate.setDate(deadlineDate.getDate() + parseInt(sa.deadline || '7'))
    addActionMut.mutate({
      description: sa.description,
      assigned_to_name: sa.assign,
      assigned_to_email: staffList?.find(s => s.name === sa.assign)?.email,
      deadline: deadlineDate.toISOString().slice(0, 10),
    })
    setSuggestedActions(prev => prev.filter(a => a.description !== sa.description))
  }

  if (isLoading) return <div className="text-gray-500">Loading event...</div>
  if (!event) return <div className="text-red-500">Event not found</div>

  const currentIdx = STATUS_FLOW.indexOf(event.status)
  const isClosed = event.status === 'closed'
  const currentPolicies = linkedPolicies ?? event.linked_policy_ids ?? []
  const currentRisks = linkedRisks ?? event.linked_risk_ids ?? []
  const hasLinkChanges = linkedPolicies !== null || linkedRisks !== null
  const openActions = (event.actions || []).filter((a: any) => !a.completed_at)

  return (
    <div>
      <Link to="/events" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to events
      </Link>

      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <div className="flex items-center gap-3 mb-2">
          <span className="font-mono text-sm text-gray-500">{event.reference}</span>
          <span className="text-sm text-gray-400">{event.event_type_name}</span>
          {event.severity && (
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              event.severity === 'severe' || event.severity === 'catastrophic' ? 'bg-red-100 text-red-700'
              : event.severity === 'moderate' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'
            }`}>{event.severity}</span>
          )}
          <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${STATUS_COLORS[event.status] ?? ''}`}>
            {STATUS_LABELS[event.status]}
          </span>
        </div>
        <h1 className="text-2xl font-bold text-gray-900">{event.title}</h1>
        <p className="text-sm text-gray-500 mt-1">Reported by {event.reported_by_name} on {event.created_at?.slice(0, 10)}</p>
        <div className="flex items-center gap-0.5 mt-4">
          {STATUS_FLOW.map((s, i) => (
            <div key={s} className={`flex-1 text-center py-1.5 text-xs font-medium rounded ${i <= currentIdx ? STATUS_COLORS[s] : 'bg-gray-100 text-gray-400'}`}>
              {STATUS_LABELS[s]}
            </div>
          ))}
        </div>
      </div>

      {/* AI Triage banner — links policies and risks only */}
      {event.status === 'submitted' && (
        <div className="bg-purple-50 border-2 border-purple-300 rounded-lg p-5 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-purple-900 text-lg flex items-center gap-2">
                <Sparkles className="w-5 h-5" /> Ready for AI Triage
              </h2>
              <p className="text-sm text-purple-700 mt-1">
                The event has been submitted. Click to let the AI identify and link relevant policies and risks.
              </p>
              {(event.involved_staff || []).length > 0 && (
                <p className="text-xs text-purple-600 mt-2">
                  Staff involved: {(event.involved_staff || []).map((s: any) => s.name).join(', ')}
                </p>
              )}
            </div>
            <button onClick={handleTriage} disabled={triaging}
              className="flex items-center gap-2 bg-purple-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50 shrink-0 ml-4">
              {triaging ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
              {triaging ? 'Triaging...' : 'Run AI Triage'}
            </button>
          </div>
          {triageError && <p className="text-sm text-red-600 mt-3">{triageError}</p>}
          {triageResult && (
            <div className="bg-white border border-purple-200 rounded-lg p-3 mt-3 text-sm">
              <p className="text-xs font-medium text-purple-700 mb-1">Triage Result:</p>
              <p className="text-gray-700 whitespace-pre-wrap text-xs">{triageResult.replace(/\[Cost:.*?\]/g, '').trim()}</p>
            </div>
          )}
        </div>
      )}

      {/* Involved staff (read-only after submission) */}
      {(event.involved_staff || []).length > 0 && event.status !== 'submitted' && (
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <span className="text-xs text-gray-500">Involved:</span>
          {(event.involved_staff || []).map((s: any) => (
            <span key={s.email} className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 text-xs px-2 py-1 rounded-full">
              {s.name} <span className="text-blue-400">({s.job_title})</span>
            </span>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">

          {/* Event Details */}
          {event.payload && Object.keys(event.payload).length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-5">
              <h2 className="font-semibold text-gray-900 mb-3">Event Details</h2>
              <dl className="space-y-2">
                {Object.entries(event.payload).map(([key, value]) => {
                  if (value === null || value === undefined || value === '' || typeof value === 'object') return null
                  return (
                    <div key={key}>
                      <dt className="text-xs font-medium text-gray-500 uppercase tracking-wide">{key.replace(/_/g, ' ')}</dt>
                      <dd className="text-sm text-gray-900 whitespace-pre-wrap">{String(value)}</dd>
                    </div>
                  )
                })}
              </dl>
            </div>
          )}

          {/* Investigation */}
          <div className={`bg-white rounded-lg shadow-sm border p-5 ${isClosed ? 'opacity-75' : ''}`}>
            <div className="flex items-center justify-between mb-3">
              <h2 className="flex items-center gap-2 font-semibold text-gray-900">
                <UserPlus className="w-4 h-4" /> Investigation
              </h2>
              {!isClosed && (
                <button onClick={handleSuggestInvestigation} disabled={suggestingInvestigation}
                  className="flex items-center gap-1 text-xs bg-purple-50 text-purple-700 px-3 py-1.5 rounded-lg hover:bg-purple-100 disabled:opacity-50">
                  {suggestingInvestigation ? <Loader2 className="w-3 h-3 animate-spin" /> : <Search className="w-3 h-3" />}
                  AI Suggest Investigation
                </button>
              )}
            </div>
            {event.investigation_notes && (
              <div className="bg-gray-50 rounded p-3 mb-3 text-sm">
                <p className="text-xs text-gray-500 mb-1">Notes recorded:</p>
                <p className="whitespace-pre-wrap">{event.investigation_notes}</p>
              </div>
            )}

            {investigationError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-3 text-sm">
                <p className="text-red-600">{investigationError}</p>
              </div>
            )}

            {/* AI investigation suggestion */}
            {investigationSuggestion && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-3">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-purple-800">AI Suggested Investigation</p>
                  <div className="flex gap-2">
                    <button onClick={() => { setIxNotes(investigationSuggestion); setInvestigationSuggestion(null) }}
                      className="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700">
                      Use as Notes
                    </button>
                    <button onClick={() => setInvestigationSuggestion(null)}
                      className="text-xs bg-gray-200 text-gray-700 px-3 py-1 rounded hover:bg-gray-300">
                      Dismiss
                    </button>
                  </div>
                </div>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{investigationSuggestion}</p>
              </div>
            )}

            {!isClosed && (
              <div className="space-y-2">
                <textarea className="w-full rounded-lg border px-3 py-2 text-sm" rows={3}
                  placeholder="Investigation findings, root cause analysis, contributing factors..."
                  value={ixNotes} onChange={e => setIxNotes(e.target.value)} />
                <button onClick={() => investigateMut.mutate({ investigation_notes: ixNotes })}
                  disabled={!ixNotes || investigateMut.isPending}
                  className="text-sm bg-sgmc-600 text-white px-4 py-2 rounded-lg hover:bg-sgmc-700 disabled:opacity-50">
                  {investigateMut.isPending ? 'Saving...' : 'Save Investigation Notes'}
                </button>
              </div>
            )}
          </div>

          {/* Discussion */}
          <div className={`bg-white rounded-lg shadow-sm border p-5 ${isClosed ? 'opacity-75' : ''}`}>
            <h2 className="flex items-center gap-2 font-semibold text-gray-900 mb-3">
              <MessageSquare className="w-4 h-4" /> Meeting Discussion
            </h2>
            {event.discussed_at_meeting && (
              <div className="bg-gray-50 rounded p-3 mb-3 text-sm">
                <p className="text-xs text-gray-500">Discussed: {event.meeting_date?.slice(0, 10) ?? 'Yes'}</p>
                {event.meeting_notes && <p className="mt-1 whitespace-pre-wrap">{event.meeting_notes}</p>}
              </div>
            )}
            {!isClosed && (
              <div className="space-y-2">
                <div className="flex gap-3">
                  <div>
                    <label className="text-xs text-gray-500">Meeting Date</label>
                    <input type="date" className="block rounded-lg border px-3 py-2 text-sm" value={meetingDate} onChange={e => setMeetingDate(e.target.value)} />
                  </div>
                </div>
                <textarea className="w-full rounded-lg border px-3 py-2 text-sm" rows={2}
                  placeholder="Key discussion points, decisions made..." value={meetingNotes} onChange={e => setMeetingNotes(e.target.value)} />
                <button onClick={() => discussMut.mutate({ meeting_date: meetingDate || undefined, meeting_notes: meetingNotes || undefined })}
                  disabled={(!meetingDate && !meetingNotes) || discussMut.isPending}
                  className="text-sm bg-sgmc-600 text-white px-4 py-2 rounded-lg hover:bg-sgmc-700 disabled:opacity-50">Record Discussion</button>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className={`bg-white rounded-lg shadow-sm border p-5 ${isClosed ? 'opacity-75' : ''}`}>
            <div className="flex items-center justify-between mb-3">
              <h2 className="flex items-center gap-2 font-semibold text-gray-900">
                <Check className="w-4 h-4" /> Actions
                {event.actions?.length > 0 && (
                  <span className="text-xs text-gray-500 font-normal">
                    ({(event.actions || []).filter((a: any) => a.completed_at).length}/{event.actions.length} complete)
                  </span>
                )}
              </h2>
              {!isClosed && (
                <button onClick={handleSuggestActions} disabled={suggestingActions}
                  className="flex items-center gap-1 text-xs bg-purple-50 text-purple-700 px-3 py-1.5 rounded-lg hover:bg-purple-100 disabled:opacity-50">
                  {suggestingActions ? <Loader2 className="w-3 h-3 animate-spin" /> : <ListChecks className="w-3 h-3" />}
                  AI Suggest Actions
                </button>
              )}
            </div>

            {actionsError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-3 text-sm">
                <p className="text-red-600">{actionsError}</p>
              </div>
            )}

            {/* AI suggested actions — confirm / edit / reject */}
            {suggestedActions.length > 0 && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-medium text-purple-800">AI Suggested Actions</p>
                  <div className="flex gap-2">
                    <button onClick={() => { suggestedActions.forEach(sa => addSuggestedAction(sa)) }}
                      className="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700">
                      Accept All
                    </button>
                    <button onClick={() => setSuggestedActions([])}
                      className="text-xs bg-gray-200 text-gray-700 px-3 py-1 rounded hover:bg-gray-300">
                      Dismiss All
                    </button>
                  </div>
                </div>
                {suggestedActions.map((sa, i) => (
                  <div key={i} className="bg-white rounded-lg border border-purple-200 p-3 mb-2">
                    <p className="text-sm font-medium text-gray-900">{sa.description}</p>
                    <p className="text-xs text-purple-600 mt-1">
                      Assign: <strong>{sa.assign}</strong> — {sa.reason}
                    </p>
                    {sa.source && (
                      <p className="text-xs mt-1">
                        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded ${
                          sa.source.startsWith('POLICY:') ? 'bg-blue-50 text-blue-700'
                          : sa.source.startsWith('NICE:') ? 'bg-green-50 text-green-700'
                          : sa.source.startsWith('NHS England:') ? 'bg-indigo-50 text-indigo-700'
                          : sa.source.startsWith('MHRA:') ? 'bg-red-50 text-red-700'
                          : sa.source.startsWith('CQC:') ? 'bg-amber-50 text-amber-700'
                          : 'bg-gray-50 text-gray-600'
                        }`}>
                          {sa.source}
                        </span>
                      </p>
                    )}
                    <p className="text-xs text-gray-500 mt-1">Deadline: {sa.deadline} days from now</p>
                    <div className="flex gap-2 mt-2">
                      <button onClick={() => addSuggestedAction(sa)}
                        className="flex items-center gap-1 text-xs bg-green-600 text-white px-3 py-1.5 rounded hover:bg-green-700">
                        <Check className="w-3 h-3" /> Accept
                      </button>
                      <button onClick={() => {
                        setNewAction(sa.description)
                        setActionAssignee(sa.assign)
                        const d = new Date(); d.setDate(d.getDate() + parseInt(sa.deadline || '7'))
                        setActionDeadline(d.toISOString().slice(0, 10))
                        setSuggestedActions(prev => prev.filter((_, idx) => idx !== i))
                      }}
                        className="text-xs bg-amber-100 text-amber-800 px-3 py-1.5 rounded hover:bg-amber-200">
                        Edit
                      </button>
                      <button onClick={() => setSuggestedActions(prev => prev.filter((_, idx) => idx !== i))}
                        className="text-xs bg-gray-100 text-gray-600 px-3 py-1.5 rounded hover:bg-gray-200">
                        Reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {actionsResult && !suggestedActions.length && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-3 text-sm">
                <p className="text-xs font-medium text-purple-700 mb-1">AI Result:</p>
                <p className="text-gray-700 whitespace-pre-wrap text-xs">{actionsResult.replace(/\[Cost:.*?\]/g, '').trim().slice(0, 600)}</p>
              </div>
            )}

            {/* Existing actions */}
            {event.actions?.length > 0 && (
              <div className="space-y-2 mb-4">
                {event.actions.map((a: any) => (
                  <div key={a.id} className={`flex items-start justify-between rounded-lg border p-3 ${a.completed_at ? 'bg-green-50 border-green-200' : 'bg-white'}`}>
                    <div className="flex-1">
                      <p className={`text-sm ${a.completed_at ? 'line-through text-gray-500' : 'text-gray-900'}`}>{a.description}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {a.assigned_to_name ? `Assigned: ${a.assigned_to_name}` : 'Unassigned'}
                        {a.deadline && ` | Due: ${a.deadline.slice(0, 10)}`}
                        {a.completed_at && ` | Done: ${a.completed_at.slice(0, 10)}`}
                      </p>
                    </div>
                    {!a.completed_at && !isClosed && (
                      <button onClick={() => completeActionMut.mutate(a.id)}
                        className="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 ml-2 shrink-0">Done</button>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Add action form with prioritised staff dropdown */}
            {!isClosed && (
              <div className="border-t pt-3 space-y-2">
                <input type="text" className="w-full rounded-lg border px-3 py-2 text-sm"
                  placeholder="Action description..." value={newAction} onChange={e => setNewAction(e.target.value)} />
                <div className="flex gap-2">
                  <select className="flex-1 rounded-lg border px-3 py-2 text-sm"
                    value={actionAssignee} onChange={e => setActionAssignee(e.target.value)}>
                    <option value="">Assign to...</option>
                    {prioritisedStaff.involved.length > 0 && (
                      <optgroup label="Involved in Event">
                        {prioritisedStaff.involved.map(s => (
                          <option key={s.id} value={s.name}>{s.name} — {s.job_title}</option>
                        ))}
                      </optgroup>
                    )}
                    {prioritisedStaff.policyLeads.length > 0 && (
                      <optgroup label="Policy Leads (linked)">
                        {prioritisedStaff.policyLeads.map(s => (
                          <option key={s.id} value={s.name}>{s.name} — {s.job_title}</option>
                        ))}
                      </optgroup>
                    )}
                    <optgroup label="All Staff">
                      {prioritisedStaff.other.map(s => (
                        <option key={s.id} value={s.name}>{s.name} — {s.job_title}</option>
                      ))}
                    </optgroup>
                  </select>
                  <input type="date" className="rounded-lg border px-3 py-2 text-sm"
                    value={actionDeadline} onChange={e => setActionDeadline(e.target.value)} />
                  <button
                    onClick={() => addActionMut.mutate({
                      description: newAction, assigned_to_name: actionAssignee || undefined,
                      assigned_to_email: staffList?.find(s => s.name === actionAssignee)?.email,
                      deadline: actionDeadline || undefined,
                    })}
                    disabled={!newAction || addActionMut.isPending}
                    className="flex items-center gap-1 bg-sgmc-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-sgmc-700 disabled:opacity-50 shrink-0">
                    <Plus className="w-3.5 h-3.5" /> Add
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Learning & Close */}
          <div className={`bg-white rounded-lg shadow-sm border p-5 ${isClosed ? 'opacity-75' : ''}`}>
            <h2 className="flex items-center gap-2 font-semibold text-gray-900 mb-3"><BookOpen className="w-4 h-4" /> Learning & Closure</h2>
            {event.learning_outcomes && (
              <div className="bg-gray-50 rounded p-3 mb-3 text-sm">
                <p className="text-xs text-gray-500 mb-1">Learning outcomes:</p>
                <p className="whitespace-pre-wrap">{event.learning_outcomes}</p>
              </div>
            )}
            {!isClosed ? (
              <div className="space-y-3">
                <textarea className="w-full rounded-lg border px-3 py-2 text-sm" rows={3}
                  placeholder="What did we learn? What changes will be made?" value={learning} onChange={e => setLearning(e.target.value)} />
                <div className="flex gap-2">
                  <button onClick={() => closeMut.mutate({ learning_outcomes: learning || undefined })}
                    disabled={openActions.length > 0 || closeMut.isPending}
                    className="flex items-center gap-1.5 bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50">
                    <Lock className="w-4 h-4" /> Close Event</button>
                  {openActions.length > 0 && <span className="text-xs text-amber-600 self-center">{openActions.length} action(s) still open</span>}
                </div>
                {closeMut.isError && <p className="text-sm text-red-600">{(closeMut.error as Error).message}</p>}
              </div>
            ) : (
              <div className="flex items-center gap-2 text-green-700 text-sm"><Check className="w-4 h-4" /> Event closed</div>
            )}
          </div>

          {/* Audit trail */}
          {event.history?.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-5">
              <h2 className="flex items-center gap-2 font-semibold text-gray-900 mb-3"><History className="w-4 h-4" /> Audit Trail</h2>
              <div className="space-y-1">
                {event.history.map((h: any) => (
                  <div key={h.id} className="flex items-center gap-3 py-1.5 border-b last:border-0 text-sm">
                    <span className="text-xs text-gray-400 w-36 shrink-0">{h.timestamp?.slice(0, 19).replace('T', ' ')}</span>
                    <span className="font-medium capitalize text-gray-700">{h.action.replace(/_/g, ' ')}</span>
                    <span className="text-gray-500 text-xs">{h.actor_name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow-sm border p-5">
            <h2 className="flex items-center gap-2 font-semibold text-gray-900 mb-3"><FileText className="w-4 h-4" /> Linked Policies</h2>
            {event.linked_policies?.map((p: any) => (
              <div key={p.id} className="flex items-center justify-between py-1.5 group">
                <div className="min-w-0">
                  <Link to={`/policies/${p.id}`} className="text-sm text-sgmc-600 hover:underline">{p.title}</Link>
                  {p.policy_lead_name && <p className="text-[10px] text-gray-400">Lead: {p.policy_lead_name}</p>}
                </div>
                {!isClosed && (
                  <button
                    onClick={() => {
                      const newIds = currentPolicies.filter((id: string) => id !== p.id)
                      setLinkedPolicies(newIds)
                    }}
                    className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-500 ml-2 shrink-0 transition-opacity"
                    title="Remove link"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
            <div className="mt-2">
              <LinkSelector type="policy" selectedIds={currentPolicies} onChange={ids => setLinkedPolicies(ids)} />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border p-5">
            <h2 className="flex items-center gap-2 font-semibold text-gray-900 mb-3"><ShieldAlert className="w-4 h-4" /> Linked Risks</h2>
            {event.linked_risks?.map((r: any) => (
              <div key={r.id} className="flex items-center justify-between py-1.5 group">
                <Link to={`/risks/${r.id}`} className="text-sm min-w-0">
                  <span className="text-sgmc-600 hover:underline">{r.reference}: {r.title}</span>
                  <span className={`ml-2 text-xs px-1.5 py-0.5 rounded ${r.risk_score >= 15 ? 'bg-red-100 text-red-700' : r.risk_score >= 8 ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>{r.risk_score}</span>
                </Link>
                {!isClosed && (
                  <button
                    onClick={() => {
                      const newIds = currentRisks.filter((id: string) => id !== r.id)
                      setLinkedRisks(newIds)
                    }}
                    className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-500 ml-2 shrink-0 transition-opacity"
                    title="Remove link"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
            <div className="mt-2">
              <LinkSelector type="risk" selectedIds={currentRisks} onChange={ids => setLinkedRisks(ids)} />
            </div>
          </div>

          {hasLinkChanges && (
            <button onClick={() => linkMut.mutate({ linked_policy_ids: linkedPolicies ?? undefined, linked_risk_ids: linkedRisks ?? undefined })}
              disabled={linkMut.isPending}
              className="w-full flex items-center justify-center gap-2 bg-sgmc-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-sgmc-700 disabled:opacity-50">
              {linkMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Save Links
            </button>
          )}

          {event.duty_of_candour_required && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 className="font-medium text-red-800 text-sm">Duty of Candour</h3>
              <p className="text-xs text-red-600 mt-1">{event.duty_of_candour_completed ? 'Completed' : 'Required — not yet completed'}</p>
            </div>
          )}

          {/* Staff Directory */}
          <div className="bg-white rounded-lg shadow-sm border p-5">
            <h2 className="flex items-center gap-2 font-semibold text-gray-900 mb-3"><Users className="w-4 h-4" /> Staff Directory</h2>
            <div className="space-y-0.5 max-h-64 overflow-y-auto">
              {staffList?.map(s => (
                <div key={s.id} className="flex items-center justify-between py-1 text-xs">
                  <div>
                    <span className="font-medium text-gray-900">{s.name}</span>
                    <span className="text-gray-400 ml-1">{s.job_title}</span>
                  </div>
                  {s.is_clinical && <span className="bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded text-[10px]">Clinical</span>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
