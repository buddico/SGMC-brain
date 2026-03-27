import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import {
  ArrowLeft, Download, FileText, ShieldAlert, AlertTriangle,
  Bell, Activity, BookOpen, ChevronDown, ChevronRight, CheckCircle2, XCircle,
} from 'lucide-react'
import { useState } from 'react'

const ITEM_ICONS: Record<string, React.ElementType> = {
  policy: FileText,
  risk: ShieldAlert,
  event: AlertTriangle,
  alert: Bell,
  subsection: BookOpen,
  learning_loop_summary: Activity,
  governance_activity: Activity,
}

const CQC_COLORS: Record<string, string> = {
  safe: 'border-l-red-500 bg-red-50',
  effective: 'border-l-blue-500 bg-blue-50',
  caring: 'border-l-purple-500 bg-purple-50',
  responsive: 'border-l-green-500 bg-green-50',
  well_led: 'border-l-amber-500 bg-amber-50',
}

function SummaryCards({ summary }: { summary: Record<string, number> }) {
  const cards = [
    { label: 'Policies', value: summary.policies_count, sub: summary.policies_reviewed ? `${summary.policies_reviewed} reviewed` : undefined, color: 'text-blue-700' },
    { label: 'Events', value: summary.events_count, sub: summary.events_with_learning ? `${summary.events_with_learning} with learning` : undefined, color: 'text-amber-700' },
    { label: 'Risks', value: summary.risks_count, sub: summary.risks_high ? `${summary.risks_high} high-rated` : undefined, color: 'text-red-700' },
    { label: 'Alerts', value: summary.alerts_count, sub: summary.alerts_actioned ? `${summary.alerts_actioned} actioned` : undefined, color: 'text-orange-700' },
    { label: 'Governance Actions', value: summary.audit_actions ?? 0, color: 'text-gray-700' },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
      {cards.map(c => (
        <div key={c.label} className="bg-white rounded-lg border p-3">
          <p className="text-xs text-gray-500">{c.label}</p>
          <p className={`text-xl font-bold ${c.color}`}>{c.value}</p>
          {c.sub && <p className="text-xs text-gray-400">{c.sub}</p>}
        </div>
      ))}
    </div>
  )
}

function LearningLoopCard({ data }: { data: Record<string, unknown> }) {
  const d = data as Record<string, number>
  const stages = [
    { label: 'Reported', value: d.reported, ok: d.reported > 0 },
    { label: 'Discussed', value: d.discussed, ok: d.discussed > 0 },
    { label: 'Learning Recorded', value: d.with_learning, ok: d.with_learning > 0 },
    { label: 'Actions Raised', value: d.actions_total, ok: d.actions_total > 0 },
    { label: 'Actions Complete', value: d.actions_completed, ok: d.actions_completed > 0 },
  ]
  return (
    <div className="bg-white rounded-lg border p-4 mb-4">
      <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
        <Activity className="w-4 h-4 text-sgmc-600" /> CQC Learning Loop
      </h3>
      <div className="flex items-center gap-1">
        {stages.map((s, i) => (
          <div key={s.label} className="flex items-center gap-1">
            <div className={`flex-1 text-center p-2 rounded text-xs font-medium ${s.ok ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'}`}>
              <div className="flex items-center justify-center gap-1">
                {s.ok ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                {s.value}
              </div>
              <div className="mt-0.5">{s.label}</div>
            </div>
            {i < stages.length - 1 && <span className="text-gray-300">→</span>}
          </div>
        ))}
      </div>
      {d.completion_rate !== undefined && (
        <div className="mt-3">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Action completion rate</span>
            <span className="font-medium">{d.completion_rate}%</span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full">
            <div className="h-2 bg-green-500 rounded-full" style={{ width: `${d.completion_rate}%` }} />
          </div>
        </div>
      )}
    </div>
  )
}

function EvidenceSection({ section }: { section: { title: string; key: string; items: any[] } }) {
  const [expanded, setExpanded] = useState(true)
  const cqcColor = CQC_COLORS[section.key] || 'border-l-gray-300 bg-gray-50'
  const hasLearningLoop = section.items.some((i: any) => i.item_type === 'learning_loop_summary')

  return (
    <div className={`border-l-4 rounded-lg mb-4 ${cqcColor}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 text-left"
      >
        <h2 className="font-semibold text-gray-900">{section.title}</h2>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">{section.items.length} items</span>
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4">
          {section.items.map((item: any) => {
            if (item.item_type === 'learning_loop_summary') {
              return <LearningLoopCard key={item.id} data={item.evidence_data || {}} />
            }

            if (item.item_type === 'subsection') {
              return (
                <h3 key={item.id} className="font-medium text-gray-700 mt-4 mb-2 pt-3 border-t text-sm">
                  {item.title}
                  {item.summary && <span className="text-xs text-gray-400 ml-2">{item.summary}</span>}
                </h3>
              )
            }

            if (item.item_type === 'governance_activity') {
              return (
                <div key={item.id} className="bg-white rounded border p-3 mb-2">
                  <p className="text-sm font-medium">{item.title}</p>
                  <p className="text-xs text-gray-500 mt-1">{item.summary}</p>
                </div>
              )
            }

            const Icon = ITEM_ICONS[item.item_type] || FileText
            const linkTo = item.item_type === 'policy' ? `/policies/${item.item_id}`
              : item.item_type === 'event' ? `/events/${item.item_id}`
              : item.item_type === 'risk' ? `/risks/${item.item_id}`
              : null

            const content = (
              <div className="bg-white rounded border p-3 mb-1.5 hover:shadow-sm transition-shadow">
                <div className="flex items-start gap-2">
                  <Icon className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 truncate">{item.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{item.summary}</p>
                  </div>
                </div>
              </div>
            )

            return linkTo ? (
              <Link key={item.id} to={linkTo} className="block">{content}</Link>
            ) : (
              <div key={item.id}>{content}</div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function EvidencePackPage() {
  const { packId } = useParams<{ packId: string }>()

  const { data: pack, isLoading } = useQuery({
    queryKey: ['evidence-pack', packId],
    queryFn: () => api<any>(`/evidence/packs/${packId}`),
    enabled: !!packId,
  })

  if (isLoading) return <div className="text-gray-500">Loading evidence pack...</div>
  if (!pack) return <div className="text-red-500">Evidence pack not found</div>

  return (
    <div>
      <Link to="/evidence" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to evidence
      </Link>

      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{pack.title}</h1>
            <p className="text-sm text-gray-500 mt-1">
              Period: {pack.period_start} to {pack.period_end} | {pack.total_items} evidence items |
              Generated by {pack.generated_by} on {pack.created_at?.slice(0, 10)}
            </p>
          </div>
          <a
            href={`/api/evidence/packs/${packId}/export.csv`}
            className="flex items-center gap-2 bg-sgmc-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-sgmc-700"
          >
            <Download className="w-4 h-4" /> Export CSV
          </a>
        </div>
      </div>

      {/* Summary */}
      {pack.summary && <SummaryCards summary={pack.summary} />}

      {/* Sections */}
      {pack.sections?.map((section: any) => (
        <EvidenceSection key={section.key} section={section} />
      ))}
    </div>
  )
}
