export type Recommendation = 'CONTEST' | 'ACCEPT' | 'HUMAN_REVIEW'

export interface Deadline {
  iso: string
  date_label: string
  time_label: string
  bucket: 'today' | 'tomorrow' | 'later' | 'overdue'
  label: string
  hours_remaining: number
}

export interface DisputeSummary {
  dispute_id: string
  customer_name: string
  customer_id: string
  transaction_id: string
  order_id: string
  amount: number
  amount_label: string
  reason: string
  reason_code: string
  network: string
  created_at: string
  created_label: string
  deadline: Deadline
  status: string
  priority: string
  recommendation: Recommendation
  recommendation_label: string
  confidence: number
  evidence_completeness: number
  case_strength: string
  conflicts: number
  gaps: number
  evidence_count: number
  closed: boolean
  human_decision: string | null
}

export interface Evidence {
  evidence_id: string
  evidence_type: string
  category: string
  source: string
  timestamp: string | null
  description: string
  finding: string
  impact: 'merchant' | 'customer' | 'neutral'
  relevance: 'high' | 'medium' | 'low'
  availability: 'available' | 'partial' | 'unavailable'
  fields: Record<string, string>
  weight?: number
  referenced_by?: string[]
  linked_events?: string[]
}

export interface TimelineEvent {
  date: string
  time: string | null
  title: string
  detail: string
  source: string
  actor: string
  evidence_ids: string[]
  date_label: string
  time_label: string
  iso: string
  evidence?: Evidence[]
}

export interface ConflictLine {
  label: string
  value: string
  evidence_id: string | null
}

export interface Conflict {
  conflict_id: string
  type: string
  severity: 'high' | 'medium' | 'low'
  summary: string
  lines: ConflictLine[]
  why_it_matters: string
  evidence_ids: string[]
}

export interface Gap {
  missing: string
  why_it_matters: string
  weight: number
  availability: string
  impact: 'high' | 'medium' | 'low'
  evidence_id?: string
}

export interface Factor {
  text: string
  evidence_id: string
  relevance: string
}

export interface Assessment {
  recommendation: Recommendation
  recommendation_label: string
  confidence: number
  evidence_completeness: number
  case_strength: string
  merchant_weight: number
  customer_weight: number
  net_direction: number
  supporting_factors: Factor[]
  contradicting_factors: Factor[]
  conflict_count: number
  gap_count: number
  blocking_gap: boolean
}

export interface Explanation {
  headline: string
  drivers: (Factor & { direction: 'supports' | 'weakens' })[]
  conflicts_considered: string[]
  gaps_considered: string[]
  method: string
}

export interface Module {
  module: string
  label: string
  finding: string
  evidence_ids: string[]
  relevance: string
  supports: string
  detail: string[]
  status: string
}

export interface EvidenceStrength {
  category: string
  label: string
  score: number
  strength: string
  evidence_ids: string[]
  unavailable: string[]
}

export interface Policy {
  policy_id: string
  name: string
  dispute_type: string
  networks: string
  relevant_evidence: string[]
  response_requirements: string
  response_window_days: number | null
  last_updated: string
}

export interface CaseAction {
  id: number
  dispute_id: string
  action: string
  actor: string
  note: string | null
  created_at: string
}

export interface DisputeDetail {
  summary: DisputeSummary
  dispute: {
    dispute_id: string
    transaction_id: string
    order_id: string
    customer_id: string
    customer_name: string
    customer_email: string
    reason: string
    reason_code: string
    network: string
    amount: number
    created_at: string
    response_deadline: string
    status: string
    priority: string
    claim: string
    claim_detail: string
  }
  transaction: Record<string, string | number | boolean | null>
  order: Record<string, string | null>
  refunds: { refund_id: string; amount: number; timestamp: string; status: string; reason: string }[]
  interactions: {
    interaction_id: string
    timestamp: string
    channel: string
    message: string
    category: string
  }[]
  claim_vs_evidence: { aspect: string; record: string; evidence_id: string }[]
  evidence_strength: EvidenceStrength[]
  assessment: Assessment
  explanation: Explanation
  conflicts: Conflict[]
  gaps: Gap[]
  argument: string
  policies: Policy[]
  modules: Module[]
  correlation: {
    unique_evidence: number
    module_references: number
    deduplicated: number
    categories_covered: string[]
    relationships: { from: string; to: string; type: string }[]
  }
  actions: CaseAction[]
  copilot_suggestions: string[]
}

export interface DashboardData {
  as_of: string
  summary: { key: string; label: string; value: string; sub: string }[]
  priority: DisputeSummary[]
  health: {
    investigated_this_week: number
    evidence_completeness: number
    cases_with_contradictions: number
    awaiting_approval: number
    open_total: number
    by_recommendation: Record<string, number>
  }
  deadlines: (DisputeSummary & { group: string })[]
}

export interface CopilotAnswer {
  headline: string
  lines: string[]
  evidence_ids: string[]
  evidence: Evidence[]
  question: string
  grounded_in: { dispute_id: string; evidence_records: number; mode: string }
}

export interface PackageSection {
  title: string
  kind: 'text' | 'fields' | 'list' | 'quote'
  body: string[] | string[][]
}

export interface EvidencePackage {
  dispute_id: string
  generated_at: string
  document_title: string
  merchant: Record<string, string>
  recommendation: Recommendation
  sections: PackageSection[]
  evidence_count: number
  disclaimer: string
}

export interface Analytics {
  metrics: { label: string; value: string; sub: string }[]
  volume: { label: string; count: number; amount: number }[]
  by_reason: { label: string; count: number }[]
  by_recommendation: { label: string; count: number }[]
  outcomes: { label: string; count: number }[]
  completeness: { label: string; count: number }[]
}
