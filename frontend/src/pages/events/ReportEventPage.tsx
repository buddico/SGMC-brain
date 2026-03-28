import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import type { EventType } from '@/api/types'
import {
  ArrowLeft, Send, ChevronDown, ChevronRight, X, Users, Search,
  Shield, Heart, Building2, Scale, AlertTriangle,
} from 'lucide-react'

interface StaffMember { id: string; name: string; email: string; job_title: string | null; is_clinical: boolean; roles: string[] }

interface SchemaFieldProps {
  name: string
  schema: Record<string, unknown>
  uiSchema?: Record<string, unknown>
  value: unknown
  onChange: (name: string, value: unknown) => void
  required?: boolean
}

function SchemaField({ name, schema, uiSchema, value, onChange, required }: SchemaFieldProps) {
  const title = (schema.title as string) || name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  const description = schema.description as string | undefined
  const type = schema.type as string
  const widget = (uiSchema as Record<string, unknown>)?.['ui:widget'] as string | undefined
  const rows = ((uiSchema as Record<string, unknown>)?.['ui:options'] as Record<string, unknown>)?.rows as number | undefined

  const labelClass = "block text-sm font-medium text-gray-700 mb-1"
  const inputClass = "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sgmc-500 focus:border-transparent"

  if (schema.enum) {
    const options = schema.enum as string[]
    const names = (schema.enumNames as string[]) || options
    return (
      <div>
        <label className={labelClass}>{title}{required && <span className="text-red-500 ml-1">*</span>}</label>
        {description && <p className="text-xs text-gray-500 mb-1">{description}</p>}
        <div className="relative">
          <select className={`${inputClass} appearance-none pr-8`} value={(value as string) || ''} onChange={e => onChange(name, e.target.value)}>
            <option value="">Select...</option>
            {options.map((opt, i) => <option key={opt} value={opt}>{names[i]}</option>)}
          </select>
          <ChevronDown className="absolute right-2.5 top-2.5 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
      </div>
    )
  }
  if (type === 'boolean') {
    return (
      <div className="flex items-center gap-2">
        <input type="checkbox" className="rounded border-gray-300 text-sgmc-600" checked={!!value} onChange={e => onChange(name, e.target.checked)} />
        <label className="text-sm font-medium text-gray-700">{title}</label>
      </div>
    )
  }
  if (type === 'integer' || type === 'number') {
    return (
      <div>
        <label className={labelClass}>{title}{required && <span className="text-red-500 ml-1">*</span>}</label>
        <input type="number" className={inputClass} value={(value as number) ?? ''} onChange={e => onChange(name, e.target.value ? Number(e.target.value) : null)} />
      </div>
    )
  }
  if (schema.format === 'date' || schema.format === 'date-time') {
    return (
      <div>
        <label className={labelClass}>{title}{required && <span className="text-red-500 ml-1">*</span>}</label>
        <input type={schema.format === 'date' ? 'date' : 'datetime-local'} className={inputClass} value={(value as string) || ''} onChange={e => onChange(name, e.target.value)} />
      </div>
    )
  }
  if (widget === 'textarea' || (schema.minLength && (schema.minLength as number) > 10)) {
    return (
      <div>
        <label className={labelClass}>{title}{required && <span className="text-red-500 ml-1">*</span>}</label>
        {description && <p className="text-xs text-gray-500 mb-1">{description}</p>}
        <textarea className={`${inputClass} resize-y`} rows={rows || 4} value={(value as string) || ''} onChange={e => onChange(name, e.target.value)} />
      </div>
    )
  }
  return (
    <div>
      <label className={labelClass}>{title}{required && <span className="text-red-500 ml-1">*</span>}</label>
      {description && <p className="text-xs text-gray-500 mb-1">{description}</p>}
      <input type="text" className={inputClass} value={(value as string) || ''} onChange={e => onChange(name, e.target.value)} />
    </div>
  )
}

// --- Super-groups for category browser ---
const SUPER_GROUPS = [
  {
    label: 'Patient Care',
    icon: Heart,
    categories: ['Patient Safety Events', 'Prescribing & Medicines', 'Infection Control & Outbreaks', 'Safeguarding'],
  },
  {
    label: 'Operational',
    icon: Building2,
    categories: ['Infrastructure & IT', 'Staffing & HR Events', 'Premises, Environment & Facilities', 'External Service Disruptions'],
  },
  {
    label: 'Governance & Compliance',
    icon: Scale,
    categories: ['Governance, Complaints & Feedback', 'Information Governance', 'Access & Equality', 'External Alerts & Guidance'],
  },
  {
    label: 'Security',
    icon: Shield,
    categories: ['Security & Violence'],
  },
]

// Quick report defaults by role
const ROLE_DEFAULTS: Record<string, string[]> = {
  reception: ['significant-event', 'near-miss', 'violent-abusive-patient-incident', 'formal-complaints', 'appointment-access-barrier', 'phone-system-outage'],
  clinical: ['significant-event', 'near-miss', 'medication-errors', 'child-protection-concern', 'needlestick-injury', 'formal-complaints'],
  gp: ['significant-event', 'near-miss', 'medication-errors', 'child-protection-concern', 'duty-of-candour', 'coroner-inquests'],
  manager: ['significant-event', 'formal-complaints', 'staff-injury-at-work', 'data-breach', 'near-miss', 'staffing-shortage-unsafe-staffing'],
  partner: ['significant-event', 'formal-complaints', 'claims-litigation', 'whistleblowing', 'cqc-concerns', 'coroner-inquests'],
}

// Synonym map for fuzzy search
const SYNONYMS: Record<string, string[]> = {
  'medication': ['prescribing', 'drug', 'medicine', 'prescription'],
  'drug': ['medication', 'prescribing', 'medicine'],
  'violent': ['aggressive', 'assault', 'attack', 'abuse'],
  'aggressive': ['violent', 'threatening', 'abuse'],
  'complaint': ['unhappy', 'dissatisfied', 'feedback'],
  'data': ['breach', 'gdpr', 'information', 'privacy'],
  'breach': ['data', 'gdpr', 'leak'],
  'needle': ['sharps', 'needlestick', 'injury'],
  'safeguarding': ['child', 'vulnerable', 'adult', 'protection'],
  'child': ['safeguarding', 'protection', 'minor'],
  'fall': ['slip', 'trip', 'hazard'],
  'fire': ['alarm', 'evacuation', 'emergency'],
  'fridge': ['vaccine', 'temperature', 'cold-chain'],
  'phone': ['telephony', 'outage', 'lines'],
  'emis': ['system', 'downtime', 'clinical-system'],
}

function searchScore(et: EventType, query: string): number {
  const q = query.toLowerCase()
  const words = q.split(/\s+/).filter(w => w.length >= 2)
  let score = 0

  const name = et.name.toLowerCase()
  const desc = (et.description || '').toLowerCase()
  const tags = (et.tags || []).join(' ').toLowerCase()
  const examples = (et.examples || []).join(' ').toLowerCase()
  const category = (et.category || '').toLowerCase()

  // Exact phrase match in name
  if (name.includes(q)) score += 20
  // Exact phrase match in description/examples
  if (desc.includes(q)) score += 8
  if (examples.includes(q)) score += 8

  for (const w of words) {
    if (name.includes(w)) score += 10
    if (desc.includes(w)) score += 3
    if (tags.includes(w)) score += 5
    if (examples.includes(w)) score += 4
    if (category.includes(w)) score += 2

    // Check synonyms
    const syns = SYNONYMS[w]
    if (syns) {
      for (const syn of syns) {
        if (name.includes(syn)) score += 6
        if (tags.includes(syn)) score += 3
        if (examples.includes(syn)) score += 2
      }
    }
  }
  return score
}


export function ReportEventPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [selectedTypeId, setSelectedTypeId] = useState<string | null>(null)
  const [formData, setFormData] = useState<Record<string, unknown>>({})
  const [involvedStaff, setInvolvedStaff] = useState<Array<{ name: string; email: string; job_title: string | null }>>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null)

  const { data: eventTypes, isLoading } = useQuery({
    queryKey: ['event-types'],
    queryFn: () => api<EventType[]>('/events/types'),
  })
  const { data: staffList } = useQuery({
    queryKey: ['staff'],
    queryFn: () => api<StaffMember[]>('/staff'),
  })

  const submitMutation = useMutation({
    mutationFn: (data: any) => api<any>('/events', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['events'] })
      navigate(`/events/${result.id}`)
    },
  })

  const selectedType = eventTypes?.find(t => t.id === selectedTypeId)

  // Search results
  const searchResults = useMemo(() => {
    if (!eventTypes || searchQuery.length < 2) return []
    return eventTypes
      .map(et => ({ et, score: searchScore(et, searchQuery) }))
      .filter(r => r.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 8)
  }, [eventTypes, searchQuery])

  // Group types by category
  const byCategory = useMemo(() => {
    if (!eventTypes) return new Map<string, EventType[]>()
    const map = new Map<string, EventType[]>()
    for (const et of eventTypes) {
      const cat = et.category || 'Other'
      if (!map.has(cat)) map.set(cat, [])
      map.get(cat)!.push(et)
    }
    return map
  }, [eventTypes])

  // Quick report types (role-based defaults)
  const quickTypes = useMemo(() => {
    if (!eventTypes) return []
    // TODO: use actual user role when available
    const defaultSlugs = ROLE_DEFAULTS['reception']

    // Get recently used from localStorage
    const recentIds: string[] = JSON.parse(localStorage.getItem('sgmc-recent-event-types') || '[]').slice(0, 2)
    const seen = new Set<string>()
    const result: EventType[] = []

    for (const id of recentIds) {
      const et = eventTypes.find(t => t.id === id)
      if (et && !seen.has(et.id)) { result.push(et); seen.add(et.id) }
    }
    for (const slug of defaultSlugs) {
      const et = eventTypes.find(t => t.slug === slug)
      if (et && !seen.has(et.id)) { result.push(et); seen.add(et.id) }
    }
    return result.slice(0, 6)
  }, [eventTypes])

  const handleSelectType = (et: EventType) => {
    setSelectedTypeId(et.id)
    setSearchQuery('')
    // Save to recent
    const recent: string[] = JSON.parse(localStorage.getItem('sgmc-recent-event-types') || '[]')
    const updated = [et.id, ...recent.filter(id => id !== et.id)].slice(0, 5)
    localStorage.setItem('sgmc-recent-event-types', JSON.stringify(updated))
  }

  const handleChange = (name: string, value: unknown) => {
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedType) return
    const title = (formData.event_title as string) || (formData.title as string) || (formData.incident_title as string) || selectedType.name
    const severity = (formData.severity as string) || null
    submitMutation.mutate({
      event_type_id: selectedType.id,
      title,
      severity,
      payload: formData,
      involved_staff: involvedStaff,
    })
  }

  const addStaff = (email: string) => {
    const s = staffList?.find(st => st.email === email)
    if (s && !involvedStaff.find(is => is.email === s.email)) {
      setInvolvedStaff(prev => [...prev, { name: s.name, email: s.email, job_title: s.job_title }])
    }
  }

  const removeStaff = (email: string) => {
    setInvolvedStaff(prev => prev.filter(s => s.email !== email))
  }

  if (isLoading) return <div className="text-gray-500">Loading event types...</div>

  // ============================================================
  // Step 1: Select event type (search + quick report + browser)
  // ============================================================
  if (!selectedTypeId) {
    return (
      <div>
        <button onClick={() => navigate('/events')} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
          <ArrowLeft className="w-4 h-4" /> Back to events
        </button>
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Report an Event</h1>

        {/* Path 1: Search bar */}
        <div className="relative mb-8">
          <Search className="absolute left-3.5 top-3.5 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Describe what happened, e.g. 'wrong medication' or 'aggressive patient'..."
            className="w-full pl-11 pr-4 py-3 text-base rounded-xl border-2 border-gray-200 focus:border-sgmc-500 focus:ring-2 focus:ring-sgmc-200 focus:outline-none"
            autoFocus
          />
          {searchResults.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white rounded-xl shadow-lg border max-h-96 overflow-y-auto">
              {searchResults.map(({ et }) => (
                <button key={et.id} onClick={() => handleSelectType(et)}
                  className="w-full text-left px-4 py-3 hover:bg-sgmc-50 border-b last:border-0 transition-colors">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-900">{et.name}</span>
                    <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full shrink-0 ml-2">
                      {et.category}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5 line-clamp-1">{et.description}</p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Path 2: Quick report grid */}
        {quickTypes.length > 0 && (
          <div className="mb-8">
            <h2 className="text-sm font-medium text-gray-500 mb-3">Quick Report</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {quickTypes.map(et => (
                <button key={et.id} onClick={() => handleSelectType(et)}
                  className="bg-white rounded-lg border-2 border-transparent shadow-sm p-4 text-left hover:border-sgmc-400 hover:shadow-md transition-all">
                  <h3 className="font-semibold text-sm text-gray-900">{et.name}</h3>
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{et.description}</p>
                  <span className="text-[10px] text-gray-400 mt-2 block">{et.category}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Path 3: Category browser */}
        <div>
          <h2 className="text-sm font-medium text-gray-500 mb-3">Browse All Categories</h2>
          {SUPER_GROUPS.map(group => {
            const Icon = group.icon
            return (
              <div key={group.label} className="mb-5">
                <h3 className="flex items-center gap-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                  <Icon className="w-3.5 h-3.5" /> {group.label}
                </h3>
                <div className="space-y-1">
                  {group.categories.map(catName => {
                    const types = byCategory.get(catName) || []
                    const isOpen = expandedCategory === catName
                    return (
                      <div key={catName} className="border rounded-lg overflow-hidden bg-white">
                        <button
                          onClick={() => setExpandedCategory(isOpen ? null : catName)}
                          className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
                        >
                          <span className="font-medium text-sm text-gray-900">{catName}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-400">{types.length}</span>
                            <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                          </div>
                        </button>
                        {isOpen && (
                          <div className="border-t bg-gray-50">
                            {types.map(et => (
                              <button key={et.id} onClick={() => handleSelectType(et)}
                                className="w-full text-left px-4 py-2.5 hover:bg-sgmc-50 border-b last:border-0 flex items-center justify-between transition-colors">
                                <div className="min-w-0">
                                  <span className="text-sm font-medium text-gray-800">{et.name}</span>
                                  <p className="text-xs text-gray-500 line-clamp-1">{et.description}</p>
                                </div>
                                <ChevronRight className="w-4 h-4 text-gray-300 shrink-0 ml-2" />
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>

        {/* Not sure fallback */}
        <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-700">Not sure which type to choose?</p>
              <p className="text-xs text-gray-500 mt-1">
                Pick the closest match — after you submit, the AI triage will link the right policies and risks regardless.
                You can also use the search bar above to describe what happened in your own words.
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ============================================================
  // Step 2: Fill in the form
  // ============================================================
  if (!selectedType) return null

  const schema = selectedType.json_schema as { properties?: Record<string, Record<string, unknown>>; required?: string[] }
  const uiSchema = (selectedType.ui_schema || {}) as Record<string, Record<string, unknown>>
  const properties = schema.properties || {}
  const requiredFields = new Set(schema.required || [])
  const fieldEntries = Object.entries(properties).filter(([, fs]) => {
    const t = fs.type as string
    return t !== 'object' && t !== 'array'
  })

  return (
    <div>
      <button onClick={() => { setSelectedTypeId(null); setFormData({}); setInvolvedStaff([]) }}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft className="w-4 h-4" /> Choose different type
      </button>

      <h1 className="text-2xl font-bold text-gray-900 mb-6">Report an Event</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main form */}
        <form onSubmit={handleSubmit} className="lg:col-span-2 bg-white rounded-lg shadow-sm border p-6">
          <div className="mb-6 pb-4 border-b">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-gray-900">{selectedType.name}</h2>
              {selectedType.category && (
                <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">{selectedType.category}</span>
              )}
            </div>
            <p className="text-sm text-gray-500 mt-1">{selectedType.description}</p>
            {selectedType.examples && selectedType.examples.length > 0 && (
              <p className="text-xs text-gray-400 mt-2">
                Examples: {selectedType.examples.join(', ')}
              </p>
            )}
          </div>

          <div className="space-y-4">
            {fieldEntries.map(([fieldName, fieldSchema]) => (
              <SchemaField key={fieldName} name={fieldName} schema={fieldSchema}
                uiSchema={uiSchema[fieldName]} value={formData[fieldName]}
                onChange={handleChange} required={requiredFields.has(fieldName)} />
            ))}
          </div>

          <div className="pt-4 mt-4 border-t flex justify-end gap-3">
            <button type="submit" disabled={submitMutation.isPending}
              className="flex items-center gap-2 bg-sgmc-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-sgmc-700 disabled:opacity-50">
              <Send className="w-4 h-4" />
              {submitMutation.isPending ? 'Submitting...' : 'Submit Event'}
            </button>
          </div>

          {submitMutation.isError && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {(submitMutation.error as Error).message}
            </div>
          )}
        </form>

        {/* Sidebar: involved staff + info */}
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow-sm border p-5">
            <h2 className="flex items-center gap-2 font-semibold text-gray-900 mb-2">
              <Users className="w-4 h-4" /> Staff Involved
            </h2>
            <p className="text-xs text-gray-500 mb-3">
              Select staff who were involved in or witnessed this event.
            </p>

            <div className="space-y-1.5 mb-3">
              {involvedStaff.map(s => (
                <div key={s.email} className="flex items-center justify-between bg-blue-50 rounded-lg px-3 py-2">
                  <div>
                    <p className="text-sm font-medium text-blue-900">{s.name}</p>
                    <p className="text-xs text-blue-600">{s.job_title}</p>
                  </div>
                  <button onClick={() => removeStaff(s.email)} className="text-blue-400 hover:text-red-500">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
              {!involvedStaff.length && (
                <p className="text-xs text-gray-400 italic">No staff selected</p>
              )}
            </div>

            <select className="w-full rounded-lg border px-3 py-2 text-sm" value=""
              onChange={e => { if (e.target.value) addStaff(e.target.value) }}>
              <option value="">+ Add staff member...</option>
              <optgroup label="Clinical Staff">
                {staffList?.filter(s => s.is_clinical && !involvedStaff.find(is => is.email === s.email)).map(s => (
                  <option key={s.id} value={s.email}>{s.name} — {s.job_title}</option>
                ))}
              </optgroup>
              <optgroup label="Management">
                {staffList?.filter(s => (s.roles.includes('manager') || s.roles.includes('partner')) && !s.is_clinical && !involvedStaff.find(is => is.email === s.email)).map(s => (
                  <option key={s.id} value={s.email}>{s.name} — {s.job_title}</option>
                ))}
              </optgroup>
              <optgroup label="Admin / Reception">
                {staffList?.filter(s => !s.is_clinical && !s.roles.includes('manager') && !s.roles.includes('partner') && !involvedStaff.find(is => is.email === s.email)).map(s => (
                  <option key={s.id} value={s.email}>{s.name} — {s.job_title}</option>
                ))}
              </optgroup>
            </select>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm">
            <p className="font-medium text-amber-800">What happens next?</p>
            <p className="text-amber-700 mt-1">
              After you submit, you can use AI to:
            </p>
            <ul className="text-amber-700 mt-1 space-y-0.5 list-disc list-inside text-xs">
              <li><strong>AI Triage</strong> — link relevant policies and risks</li>
              <li><strong>AI Suggest Investigation</strong> — suggest investigation notes with best practice references</li>
              <li><strong>AI Suggest Actions</strong> — propose actions with staff assignments</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
