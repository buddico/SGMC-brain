import { Routes, Route } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { PoliciesPage } from '@/pages/policies/PoliciesPage'
import { PolicyDetailPage } from '@/pages/policies/PolicyDetailPage'
import { EventsPage } from '@/pages/events/EventsPage'
import { EventDetailPage } from '@/pages/events/EventDetailPage'
import { ReportEventPage } from '@/pages/events/ReportEventPage'
import { RisksPage } from '@/pages/risks/RisksPage'
import { RiskDetailPage } from '@/pages/risks/RiskDetailPage'
import { CompliancePage } from '@/pages/compliance/CompliancePage'
import { AlertsPage } from '@/pages/alerts/AlertsPage'
import { AlertDetailPage } from '@/pages/alerts/AlertDetailPage'
import { EvidencePage } from '@/pages/evidence/EvidencePage'
import { EvidencePackPage } from '@/pages/evidence/EvidencePackPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/policies" element={<PoliciesPage />} />
        <Route path="/policies/:policyId" element={<PolicyDetailPage />} />
        <Route path="/events" element={<EventsPage />} />
        <Route path="/events/report" element={<ReportEventPage />} />
        <Route path="/events/:eventId" element={<EventDetailPage />} />
        <Route path="/risks" element={<RisksPage />} />
        <Route path="/risks/:riskId" element={<RiskDetailPage />} />
        <Route path="/compliance" element={<CompliancePage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/alerts/:alertId" element={<AlertDetailPage />} />
        <Route path="/evidence" element={<EvidencePage />} />
        <Route path="/evidence/:packId" element={<EvidencePackPage />} />
      </Routes>
    </Layout>
  )
}
