import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import type { Policy } from '@/api/types'

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

const STATUS_STYLES: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  draft: 'bg-gray-100 text-gray-700',
  under_review: 'bg-amber-100 text-amber-700',
  superseded: 'bg-red-100 text-red-700',
  archived: 'bg-gray-100 text-gray-500',
}

export function PoliciesPage() {
  const { data: policies, isLoading } = useQuery({
    queryKey: ['policies'],
    queryFn: () => api<Policy[]>('/policies'),
  })

  if (isLoading) return <div className="text-gray-500">Loading policies...</div>

  const grouped = (policies ?? []).reduce<Record<string, Policy[]>>((acc, p) => {
    const domain = p.domain
    if (!acc[domain]) acc[domain] = []
    acc[domain].push(p)
    return acc
  }, {})

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Policies</h1>
        <span className="text-sm text-gray-500">{policies?.length ?? 0} policies</span>
      </div>

      {Object.entries(grouped).map(([domain, domainPolicies]) => (
        <div key={domain} className="mb-8">
          <h2 className="text-lg font-semibold text-gray-800 mb-3 border-b pb-2">
            {DOMAIN_LABELS[domain] ?? domain}
          </h2>
          <div className="bg-white rounded-lg shadow-sm border divide-y">
            {domainPolicies.map(policy => (
              <Link key={policy.id} to={`/policies/${policy.id}`} className="block p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900">{policy.title}</h3>
                    <p className="text-sm text-gray-500 mt-1">
                      Lead: {policy.policy_lead_name ?? 'Unassigned'}
                      {policy.next_review_due && ` | Review due: ${policy.next_review_due}`}
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${STATUS_STYLES[policy.status] ?? ''}`}>
                    {policy.status}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
