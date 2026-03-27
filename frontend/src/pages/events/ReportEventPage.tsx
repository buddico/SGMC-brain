import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import type { EventType } from '@/api/types'
import { ArrowLeft, Send, ChevronDown, X, Users } from 'lucide-react'

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


export function ReportEventPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [selectedTypeId, setSelectedTypeId] = useState<string | null>(null)
  const [formData, setFormData] = useState<Record<string, unknown>>({})
  const [involvedStaff, setInvolvedStaff] = useState<Array<{ name: string; email: string; job_title: string | null }>>([])

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
      // Navigate to the new event detail page so user can trigger AI triage
      navigate(`/events/${result.id}`)
    },
  })

  const selectedType = eventTypes?.find(t => t.id === selectedTypeId)

  const handleChange = (name: string, value: unknown) => {
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedType) return
    const title = (formData.event_title as string) || (formData.title as string) || selectedType.name
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

  // Step 1: select type
  if (!selectedTypeId) {
    return (
      <div>
        <button onClick={() => navigate('/events')} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
          <ArrowLeft className="w-4 h-4" /> Back to events
        </button>
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Report an Event</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {eventTypes?.map(et => (
            <button key={et.id} onClick={() => setSelectedTypeId(et.id)}
              className="bg-white rounded-lg shadow-sm border p-5 text-left hover:border-sgmc-400 hover:shadow-md transition-all group">
              <h3 className="font-semibold text-gray-900 group-hover:text-sgmc-700">{et.name}</h3>
              <p className="text-sm text-gray-500 mt-1">{et.description}</p>
              <div className="flex gap-2 mt-3">
                {et.tags?.map(tag => <span key={tag} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{tag}</span>)}
                <span className="text-xs text-gray-400">v{et.version}</span>
              </div>
            </button>
          ))}
        </div>
      </div>
    )
  }

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
            <h2 className="text-lg font-semibold text-gray-900">{selectedType.name}</h2>
            <p className="text-sm text-gray-500">{selectedType.description}</p>
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

        {/* Sidebar: involved staff */}
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow-sm border p-5">
            <h2 className="flex items-center gap-2 font-semibold text-gray-900 mb-2">
              <Users className="w-4 h-4" /> Staff Involved
            </h2>
            <p className="text-xs text-gray-500 mb-3">
              Select all staff who were involved in or witnessed this event. This will help the AI suggest the right actions after submission.
            </p>

            {/* Selected staff */}
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
              After you submit, you'll be taken to the event page where you can click <strong>"AI Triage"</strong> to automatically:
            </p>
            <ul className="text-amber-700 mt-1 space-y-0.5 list-disc list-inside text-xs">
              <li>Link relevant policies</li>
              <li>Suggest investigation areas</li>
              <li>Propose actions with staff assignments</li>
              <li>Identify related risks</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
