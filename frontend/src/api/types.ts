export interface AuthUser {
  email: string
  name: string
  roles: string[]
}

export interface Policy {
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
  tags: string[]
  applicable_roles: string[]
  created_at: string
  updated_at: string
}

export interface EventType {
  id: string
  name: string
  slug: string
  description: string | null
  version: string
  is_active: boolean
  json_schema: Record<string, unknown>
  ui_schema: Record<string, unknown> | null
  tags: string[] | null
  cqc_category: string | null
}

export interface Event {
  id: string
  event_type_id: string
  event_type_name: string | null
  reference: string | null
  title: string
  severity: string | null
  status: string
  occurred_at: string | null
  reported_by_name: string
  reported_by_email: string
  discussed_at_meeting: boolean
  duty_of_candour_required: boolean
  created_at: string
  actions_count: number
}

export interface Risk {
  id: string
  reference: string | null
  title: string
  description: string
  category: string
  status: string
  likelihood: number
  impact: number
  risk_score: number
  owner_name: string
  owner_email: string
  date_identified: string
  last_reviewed: string | null
  next_review_due: string | null
  linked_policy_ids: string[]
  linked_event_ids: string[]
  reviews_count: number
  actions_count: number
  created_at: string
}

export interface DashboardStats {
  policies_active: number
  policies_review_due: number
  events_open: number
  events_total: number
  risks_open: number
  risks_high: number
  alerts_new: number
  checks_overdue: number
}

export interface CheckTemplate {
  id: string
  name: string
  description: string | null
  category: string
  frequency_months: number
  requires_document: boolean
  document_description: string | null
  applicable_roles: string[] | null
  cqc_relevant: boolean
  cqc_quality_statement: string | null
  is_active: boolean
  staff_checks_count: number
}

export interface StaffCheck {
  id: string
  check_template_id: string
  template_name: string | null
  template_category: string | null
  staff_email: string
  staff_name: string
  completed_date: string | null
  expiry_date: string | null
  status: string
  notes: string | null
  documents_count: number
}

export interface AlertItem {
  id: string
  source: string
  title: string
  summary: string | null
  url: string | null
  issued_date: string | null
  message_type: string | null
  severity: string | null
  status: string
  priority: string | null
  due_date: string | null
  actions_count: number
  created_at: string
}

export interface EvidencePack {
  id: string
  title: string
  description: string | null
  cqc_key_question: string | null
  period_start: string
  period_end: string
  status: string
  summary: Record<string, number> | null
  items_count: number
  generated_by: string | null
  created_at: string
}
