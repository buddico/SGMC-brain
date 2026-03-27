import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { CheckTemplate, StaffCheck } from '@/api/types'
import { ClipboardCheck, Users } from 'lucide-react'

const CATEGORY_LABELS: Record<string, string> = {
  mandatory_compliance: 'Mandatory Compliance',
  training: 'Training',
  it_access: 'IT Access',
  onboarding: 'Onboarding',
  hr: 'HR',
  clinical: 'Clinical',
  equipment: 'Equipment',
  premises: 'Premises',
}

const STATUS_STYLES: Record<string, string> = {
  completed: 'bg-green-100 text-green-700',
  pending: 'bg-gray-100 text-gray-600',
  due_soon: 'bg-amber-100 text-amber-700',
  overdue: 'bg-red-100 text-red-700',
}

export function CompliancePage() {
  const { data: templates, isLoading: loadingTemplates } = useQuery({
    queryKey: ['compliance-templates'],
    queryFn: () => api<CheckTemplate[]>('/compliance/templates'),
  })
  const { data: checks, isLoading: loadingChecks } = useQuery({
    queryKey: ['compliance-checks'],
    queryFn: () => api<StaffCheck[]>('/compliance/checks'),
  })

  if (loadingTemplates || loadingChecks) return <div className="text-gray-500">Loading compliance data...</div>

  const overdue = checks?.filter(c => c.status === 'overdue').length ?? 0
  const dueSoon = checks?.filter(c => c.status === 'due_soon').length ?? 0
  const completed = checks?.filter(c => c.status === 'completed').length ?? 0
  const total = checks?.length ?? 0

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Compliance & Training</h1>
        <button className="bg-sgmc-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-sgmc-700 transition-colors">
          Add Check Template
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Total Checks</p>
          <p className="text-2xl font-bold">{total}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-green-600">Completed</p>
          <p className="text-2xl font-bold text-green-700">{completed}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-amber-600">Due Soon</p>
          <p className="text-2xl font-bold text-amber-700">{dueSoon}</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-red-600">Overdue</p>
          <p className="text-2xl font-bold text-red-700">{overdue}</p>
        </div>
      </div>

      {/* Templates */}
      <h2 className="text-lg font-semibold text-gray-800 mb-3">Check Templates</h2>
      {!templates?.length ? (
        <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
          <ClipboardCheck className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p>No check templates configured yet.</p>
          <p className="text-sm mt-1">Create templates for mandatory training, DBS checks, appraisals, and more.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border divide-y">
          {templates.map(tmpl => (
            <div key={tmpl.id} className="p-4 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">{tmpl.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {CATEGORY_LABELS[tmpl.category] ?? tmpl.category}
                    {tmpl.frequency_months > 0 ? ` | Every ${tmpl.frequency_months} months` : ' | One-off'}
                    {tmpl.cqc_relevant && ' | CQC relevant'}
                  </p>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <Users className="w-4 h-4" />
                  {tmpl.staff_checks_count} checks
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Staff checks */}
      {checks && checks.length > 0 && (
        <>
          <h2 className="text-lg font-semibold text-gray-800 mb-3 mt-8">Staff Checks</h2>
          <div className="bg-white rounded-lg shadow-sm border">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3 font-medium text-gray-600">Staff Member</th>
                  <th className="text-left p-3 font-medium text-gray-600">Check</th>
                  <th className="text-left p-3 font-medium text-gray-600">Category</th>
                  <th className="text-left p-3 font-medium text-gray-600">Completed</th>
                  <th className="text-left p-3 font-medium text-gray-600">Expiry</th>
                  <th className="text-left p-3 font-medium text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {checks.map(check => (
                  <tr key={check.id} className="hover:bg-gray-50">
                    <td className="p-3 font-medium">{check.staff_name}</td>
                    <td className="p-3">{check.template_name}</td>
                    <td className="p-3 text-gray-600 capitalize">{check.template_category?.replace(/_/g, ' ')}</td>
                    <td className="p-3 text-gray-600">{check.completed_date ?? '-'}</td>
                    <td className="p-3 text-gray-600">{check.expiry_date ?? '-'}</td>
                    <td className="p-3">
                      <span className={`text-xs px-2 py-1 rounded-full ${STATUS_STYLES[check.status] ?? ''}`}>
                        {check.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
