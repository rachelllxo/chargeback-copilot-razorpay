import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AppShell } from '../components/AppShell'
import { Copilot } from '../components/Copilot'
import {
  EvidenceProvider,
  EvidenceRef,
  availabilityTone,
  impactTone,
  useEvidence,
} from '../components/EvidenceDrawer'
import { EvidencePackagePanel } from '../components/EvidencePackage'
import {
  EmptyBlock,
  ErrorBlock,
  LoadingBlock,
  Meter,
  Modal,
  Pill,
  Section,
  Spinner,
  StatusDot,
  useToast,
} from '../components/ui'
import { api, ApiError, useApi } from '../lib/api'
import type {
  CaseAction,
  Conflict,
  DisputeDetail as Detail,
  Evidence,
  Gap,
  Module,
  TimelineEvent,
} from '../lib/types'
import { categoryLabel, dateOnly, dateTime, impactLabel, inr, recommendationTone, titleCase } from '../lib/format'

/* ------------------------------------------------------------- case header */

function CaseHeader({ detail }: { detail: Detail }) {
  const d = detail.dispute
  const s = detail.summary
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="label">Chargeback</p>
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <h2 className="num text-2xl font-semibold tracking-tight text-ink">{d.dispute_id}</h2>
            <Pill tone={s.status === 'Needs review' ? 'caution' : 'neutral'}>{s.status}</Pill>
            <Pill tone="neutral">{d.network}</Pill>
          </div>
          <p className="mt-1.5 text-sm text-ink-2">
            {d.reason} · <span className="text-ink-3">{d.reason_code}</span>
          </p>
        </div>
        <div className="text-right">
          <p className="label">Disputed amount</p>
          <p className="num mt-1 text-2xl font-semibold tracking-tight text-ink">{inr(d.amount)}</p>
          <p
            className={`mt-1 text-xs ${
              s.deadline.bucket === 'today' || s.deadline.bucket === 'overdue' ? 'text-critical' : 'text-ink-3'
            }`}
          >
            Response deadline {dateOnly(d.response_deadline)} · {s.deadline.label}
          </p>
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-4 border-y border-line py-4 sm:grid-cols-3 lg:grid-cols-6">
        {[
          ['Customer', d.customer_name],
          ['Customer ID', d.customer_id],
          ['Order', d.order_id],
          ['Transaction', d.transaction_id],
          ['Raised', dateOnly(d.created_at)],
          ['Evidence records', String(detail.correlation.unique_evidence)],
        ].map(([k, v]) => (
          <div key={k}>
            <dt className="label">{k}</dt>
            <dd className="num mt-1 text-sm text-ink">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

/* -------------------------------------------------------------- assessment */

function AssessmentBlock({ detail }: { detail: Detail }) {
  const a = detail.assessment
  const tone = recommendationTone(a.recommendation)
  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,20rem)_1fr]">
      <div>
        <p className="label">Recommendation</p>
        <p
          className={`mt-1.5 text-2xl font-semibold uppercase tracking-tight ${
            tone === 'positive' ? 'text-positive' : tone === 'caution' ? 'text-caution' : 'text-info'
          }`}
        >
          {a.recommendation_label}
        </p>
        <dl className="mt-5 space-y-3.5">
          <div>
            <div className="flex items-baseline justify-between text-sm">
              <dt className="text-ink-2">Confidence</dt>
              <dd className="num font-medium">{a.confidence}%</dd>
            </div>
            <div className="mt-1.5">
              <Meter value={a.confidence} tone={tone} />
            </div>
          </div>
          <div>
            <div className="flex items-baseline justify-between text-sm">
              <dt className="text-ink-2">Evidence completeness</dt>
              <dd className="num font-medium">{a.evidence_completeness}%</dd>
            </div>
            <div className="mt-1.5">
              <Meter value={a.evidence_completeness} tone="accent" />
            </div>
          </div>
          <div className="flex items-baseline justify-between text-sm">
            <dt className="text-ink-2">Case strength</dt>
            <dd className="font-medium">{a.case_strength}</dd>
          </div>
        </dl>
        <p className="mt-4 border-t border-line pt-3 text-2xs leading-relaxed text-ink-3">{detail.explanation.method}</p>
      </div>

      <div>
        <p className="label">Why</p>
        <p className="mt-1.5 max-w-2xl text-sm text-ink-2">{detail.explanation.headline}</p>

        <div className="mt-5 grid gap-6 md:grid-cols-2">
          <div>
            <p className="mb-2 text-xs font-medium text-positive">Supporting factors · merchant position</p>
            <ul className="space-y-2">
              {a.supporting_factors.map((f) => (
                <li key={f.evidence_id} className="flex gap-2 text-sm text-ink-2">
                  <span className="mt-px text-positive" aria-hidden>
                    ✓
                  </span>
                  <span>
                    {f.text} <EvidenceRef id={f.evidence_id} />
                  </span>
                </li>
              ))}
              {a.supporting_factors.length === 0 && (
                <li className="text-sm text-ink-3">No evidence supports the merchant position.</li>
              )}
            </ul>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium text-caution">Contradicting factors · cardholder position</p>
            <ul className="space-y-2">
              {a.contradicting_factors.map((f) => (
                <li key={f.evidence_id} className="flex gap-2 text-sm text-ink-2">
                  <span className="mt-px text-caution" aria-hidden>
                    ⚠
                  </span>
                  <span>
                    {f.text} <EvidenceRef id={f.evidence_id} />
                  </span>
                </li>
              ))}
              {a.contradicting_factors.length === 0 && (
                <li className="text-sm text-ink-3">No evidence contradicts the merchant position.</li>
              )}
            </ul>
          </div>
        </div>

        <div className="mt-6 border-t border-line pt-4">
          <p className="mb-2 text-xs font-medium text-ink-2">Evidence gaps</p>
          <ul className="space-y-1.5">
            {detail.gaps.map((g) => (
              <li key={g.missing} className="flex gap-2 text-sm text-ink-3">
                <span aria-hidden>•</span>
                <span>{g.missing}</span>
              </li>
            ))}
            {detail.gaps.length === 0 && <li className="text-sm text-ink-3">No material gaps identified.</li>}
          </ul>
        </div>
      </div>
    </div>
  )
}

/* --------------------------------------------------- investigation runner */

function InvestigationProgress({ detail, disputeId }: { detail: Detail; disputeId: string }) {
  const [running, setRunning] = useState(false)
  const [hasRun, setHasRun] = useState(false)
  const [done, setDone] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [completedAt, setCompletedAt] = useState<string | null>(null)
  const toast = useToast()
  const modules = detail.modules

  const run = async () => {
    setRunning(true)
    setError(null)
    setDone([])
    setCompletedAt(null)
    try {
      const promise = api.post<{ modules: Module[]; completed_at: string }>(
        `/api/disputes/${disputeId}/investigate`,
      )
      // Reveal each module as the backend result arrives, in pipeline order.
      const result = await promise
      for (const m of result.modules) {
        await new Promise((r) => setTimeout(r, 110))
        setDone((prev) => [...prev, m.module])
      }
      setCompletedAt(result.completed_at)
      setHasRun(true)
      toast(`Investigation complete · ${result.modules.length} modules`, 'positive')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'The investigation service did not respond.')
    } finally {
      setRunning(false)
    }
  }

  const state = (key: string) => {
    if (!running && done.length === 0) return 'complete'
    if (done.includes(key)) return 'complete'
    if (running) return 'pending'
    return 'complete'
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button type="button" className="btn-secondary" onClick={run} disabled={running}>
          {running ? (
            <>
              <Spinner /> Investigating case…
            </>
          ) : (
            hasRun ? 'Re-run investigation' : 'Investigate case'
          )}
        </button>
        {completedAt && <span className="text-xs text-ink-3">Completed {dateTime(completedAt)}</span>}
        {!running && !completedAt && (
          <span className="text-xs text-ink-3">
            Last run on ingestion · {detail.correlation.module_references} module references correlated into{' '}
            {detail.correlation.unique_evidence} unique records
          </span>
        )}
      </div>

      {error && <ErrorBlock message={error} onRetry={run} />}

      <ol className="grid gap-x-8 gap-y-1 sm:grid-cols-2 xl:grid-cols-3">
        {modules.map((m) => {
          const s = state(m.module)
          return (
            <li key={m.module} className="flex items-start justify-between gap-3 border-b border-line/60 py-2">
              <div className="min-w-0">
                <p className="text-sm text-ink">{m.label}</p>
                <p className="mt-0.5 line-clamp-2 text-xs text-ink-3">{m.finding}</p>
                {m.evidence_ids.length > 0 && (
                  <p className="mt-1 flex flex-wrap gap-1">
                    {m.evidence_ids.map((id) => (
                      <EvidenceRef key={id} id={id} />
                    ))}
                  </p>
                )}
              </div>
              <span className="shrink-0 pt-0.5 text-xs">
                {s === 'complete' ? (
                  <span className="text-positive">✓ Complete</span>
                ) : (
                  <span className="flex items-center gap-1.5 text-ink-3">
                    <Spinner className="h-3 w-3" /> Running
                  </span>
                )}
              </span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

/* ----------------------------------------------------------------- timeline */

function Timeline({ disputeId }: { disputeId: string }) {
  const { data, loading, error, reload } = useApi<{ events: TimelineEvent[]; sources: string[] }>(
    `/api/disputes/${disputeId}/timeline`,
  )
  const [openIndex, setOpenIndex] = useState<number | null>(null)

  if (loading) return <LoadingBlock label="Reconstructing timeline" />
  if (error) return <ErrorBlock message={error} onRetry={reload} />
  if (!data || data.events.length === 0) return <EmptyBlock title="No events could be sequenced for this case" />

  return (
    <ol className="relative">
      {data.events.map((e, i) => {
        const expanded = openIndex === i
        const clickable = e.evidence_ids.length > 0
        return (
          <li key={`${e.iso}-${i}`} className="relative grid grid-cols-[5.5rem_1fr] gap-4 sm:grid-cols-[7rem_1fr]">
            <div className="py-3 text-right">
              <p className="num text-xs font-medium text-ink-2">{e.date_label}</p>
              <p className="num text-2xs text-ink-3">{e.time_label}</p>
            </div>
            <div className="relative border-l border-line pb-1 pl-5">
              <span
                className={`absolute -left-[4.5px] top-[1.15rem] h-2 w-2 rounded-full border-2 border-canvas ${
                  e.actor === 'customer' ? 'bg-caution' : e.actor === 'issuer' ? 'bg-critical' : 'bg-accent'
                }`}
                aria-hidden
              />
              <button
                type="button"
                className={`-ml-2 w-full rounded px-2 py-3 text-left transition-colors ${
                  clickable ? 'hover:bg-raised/70' : 'cursor-default'
                }`}
                onClick={() => clickable && setOpenIndex(expanded ? null : i)}
                aria-expanded={clickable ? expanded : undefined}
              >
                <p className="text-sm font-medium text-ink">{e.title}</p>
                {e.detail && <p className="mt-0.5 text-sm text-ink-2">{e.detail}</p>}
                <p className="mt-1 text-xs text-ink-3">
                  Source: {e.source}
                  {clickable && (
                    <span className="ml-2 text-accent">{expanded ? 'Hide evidence' : 'View evidence'}</span>
                  )}
                </p>
              </button>

              {expanded && (
                <div className="animate-in -ml-2 mb-3 space-y-2 rounded border border-line bg-raised/40 px-3 py-2.5">
                  {e.evidence?.map((ev) => (
                    <div key={ev.evidence_id} className="text-xs">
                      <p className="flex flex-wrap items-center gap-2">
                        <EvidenceRef id={ev.evidence_id} />
                        <span className="font-medium text-ink">{ev.evidence_type}</span>
                        <Pill tone={impactTone(ev.impact)}>{impactLabel[ev.impact]}</Pill>
                      </p>
                      <p className="mt-1 text-ink-2">{ev.finding}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

/* -------------------------------------------------------- evidence explorer */

const FILTERS = [
  'all', 'payment', 'order', 'fulfillment', 'delivery', 'refund', 'customer', 'communication', 'historical', 'policy',
]

function EvidenceExplorer({ evidence }: { evidence: Evidence[] }) {
  const [filter, setFilter] = useState('all')
  const { open } = useEvidence()

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: evidence.length }
    for (const e of evidence) c[e.category] = (c[e.category] ?? 0) + 1
    return c
  }, [evidence])

  const items = filter === 'all' ? evidence : evidence.filter((e) => e.category === filter)

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-1.5" role="tablist" aria-label="Evidence categories">
        {FILTERS.filter((f) => counts[f]).map((f) => (
          <button
            key={f}
            role="tab"
            aria-selected={filter === f}
            type="button"
            onClick={() => setFilter(f)}
            className={`rounded-sm border px-2 py-1 text-xs transition-colors ${
              filter === f
                ? 'border-accent bg-accent text-white'
                : 'border-line bg-surface text-ink-2 hover:bg-raised'
            }`}
          >
            {f === 'all' ? 'All' : categoryLabel[f]}
            <span className={`num ml-1.5 ${filter === f ? 'text-white/70' : 'text-ink-3'}`}>{counts[f]}</span>
          </button>
        ))}
      </div>

      {items.length === 0 ? (
        <EmptyBlock title="No evidence in this category" />
      ) : (
        <ul className="divide-y divide-line border-y border-line">
          {items.map((e) => (
            <li key={e.evidence_id}>
              <button
                type="button"
                className="grid w-full grid-cols-1 gap-x-6 gap-y-2 px-1 py-3.5 text-left transition-colors hover:bg-raised/60 md:grid-cols-[9rem_1fr_11rem]"
                onClick={() => open(e.evidence_id)}
              >
                <div>
                  <p className="num text-sm font-medium text-ink">{e.evidence_id}</p>
                  <p className="mt-0.5 text-xs text-ink-3">{categoryLabel[e.category]}</p>
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-ink">{e.evidence_type}</p>
                  <p className="mt-0.5 text-sm text-ink-2">{e.finding}</p>
                  <p className="mt-1 text-2xs text-ink-3">
                    {e.source} · {e.timestamp ? dateTime(e.timestamp) : 'Not time-stamped'}
                  </p>
                </div>
                <div className="flex flex-wrap items-start gap-1.5 md:justify-end">
                  <Pill tone={impactTone(e.impact)}>{impactLabel[e.impact]}</Pill>
                  <Pill tone={e.relevance === 'high' ? 'accent' : 'neutral'}>{e.relevance}</Pill>
                  {e.availability !== 'available' && (
                    <Pill tone={availabilityTone(e.availability)}>{e.availability}</Pill>
                  )}
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/* ------------------------------------------------------------- contradictions */

function Contradictions({ conflicts }: { conflicts: Conflict[] }) {
  if (conflicts.length === 0) {
    return (
      <div className="flex items-center gap-2.5 rounded border border-line bg-positive-soft/40 px-4 py-3">
        <StatusDot tone="positive" />
        <p className="text-sm text-ink-2">
          <span className="font-medium text-ink">No material contradictions detected.</span> Every retrieved
          record is consistent with the others.
        </p>
      </div>
    )
  }
  return (
    <div className="space-y-4">
      {conflicts.map((c) => (
        <article key={c.conflict_id} className="card overflow-hidden">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-caution-soft/40 px-4 py-2.5">
            <p className="text-sm font-medium text-ink">{c.summary}</p>
            <div className="flex items-center gap-2">
              <Pill tone="neutral">{c.type}</Pill>
              <Pill tone={c.severity === 'high' ? 'critical' : 'caution'}>Severity: {c.severity}</Pill>
            </div>
          </header>
          <dl className="divide-y divide-line/70">
            {c.lines.map((l, i) => (
              <div key={i} className="grid gap-1 px-4 py-2.5 sm:grid-cols-[12rem_1fr] sm:gap-4">
                <dt className="text-xs text-ink-3">{l.label}</dt>
                <dd className="text-sm text-ink-2">
                  {l.value} {l.evidence_id && <EvidenceRef id={l.evidence_id} />}
                </dd>
              </div>
            ))}
          </dl>
          <footer className="border-t border-line bg-raised/40 px-4 py-2.5">
            <p className="text-xs text-ink-2">
              <span className="font-medium text-ink">Why it matters: </span>
              {c.why_it_matters}
            </p>
          </footer>
        </article>
      ))}
    </div>
  )
}

/* --------------------------------------------------------------- human review */

function HumanReview({
  detail,
  disputeId,
  onRecorded,
}: {
  detail: Detail
  disputeId: string
  onRecorded: () => void
}) {
  const [busy, setBusy] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [note, setNote] = useState(detail.argument)
  const [actions, setActions] = useState<CaseAction[]>(detail.actions)
  const [error, setError] = useState<string | null>(null)
  const toast = useToast()

  const send = async (action: string, text?: string) => {
    setBusy(action)
    setError(null)
    try {
      const res = await api.post<{ actions: CaseAction[] }>(`/api/disputes/${disputeId}/decision`, {
        action,
        note: text ?? null,
      })
      setActions(res.actions)
      toast(
        action === 'approve'
          ? 'Response approved and queued for submission'
          : action === 'request_review'
            ? 'Escalated for senior human review'
            : action === 'accept'
              ? 'Dispute accepted — credit will be processed'
              : 'Edited response saved',
        action === 'request_review' ? 'caution' : 'positive',
      )
      setEditing(false)
      onRecorded()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not record the decision.')
    } finally {
      setBusy(null)
    }
  }

  const a = detail.assessment
  return (
    <div className="card p-5">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <p className="label">AI recommendation</p>
          <p className="mt-1 text-lg font-semibold text-ink">{a.recommendation_label}</p>
          <p className="mt-1 max-w-xl text-sm text-ink-3">
            AI recommendation is advisory. Final action requires human approval — nothing is submitted to the
            network and no funds move from this screen.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-primary"
            onClick={() => send('approve')}
            disabled={Boolean(busy)}
          >
            {busy === 'approve' && <Spinner className="border-white/40 border-t-white" />} Approve response
          </button>
          <button type="button" className="btn-secondary" onClick={() => setEditing(true)} disabled={Boolean(busy)}>
            Edit response
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => send('request_review')}
            disabled={Boolean(busy)}
          >
            Request human review
          </button>
        </div>
      </div>

      {error && (
        <p className="mt-3 rounded border border-critical/25 bg-critical-soft/50 px-3 py-2 text-xs text-critical">
          {error}
        </p>
      )}

      {actions.length > 0 && (
        <div className="mt-5 border-t border-line pt-4">
          <p className="label mb-2">Decision log</p>
          <ul className="space-y-1.5">
            {actions.map((act) => (
              <li key={act.id} className="flex flex-wrap items-baseline gap-2 text-xs text-ink-2">
                <span className="num text-ink-3">{dateTime(act.created_at)}</span>
                <span className="font-medium text-ink">{titleCase(act.action)}</span>
                <span className="text-ink-3">· {act.actor}</span>
                {act.note && <span className="text-ink-3">· {act.note.slice(0, 90)}…</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      <Modal
        open={editing}
        onClose={() => setEditing(false)}
        title="Edit merchant response"
        subtitle="Your edited argument is stored with the case and used in the evidence package."
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setEditing(false)}>
              Cancel
            </button>
            <button type="button" className="btn-primary" onClick={() => send('edit', note)} disabled={busy === 'edit'}>
              Save response
            </button>
          </>
        }
      >
        <label className="label" htmlFor="response-text">
          Merchant argument
        </label>
        <textarea
          id="response-text"
          className="field mt-2 min-h-[14rem] leading-relaxed"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <p className="mt-2 text-2xs text-ink-3">
          Only statements backed by the evidence listed on this case should be included.
        </p>
      </Modal>
    </div>
  )
}

/* --------------------------------------------------------------------- page */

export default function DisputeDetailPage() {
  const { id = '' } = useParams()
  const { data, loading, error, reload } = useApi<Detail>(`/api/disputes/${id}`)
  const ev = useApi<{ items: Evidence[] }>(`/api/disputes/${id}/evidence`)

  if (loading) {
    return (
      <AppShell title={id} subtitle="Loading case">
        <LoadingBlock label="Retrieving case records" />
      </AppShell>
    )
  }
  if (error || !data) {
    return (
      <AppShell title={id} subtitle="Case unavailable">
        <ErrorBlock message={error ?? 'Case not found.'} onRetry={reload} />
        <p className="mt-4 text-sm">
          <Link to="/disputes" className="text-accent underline-offset-4 hover:underline">
            Back to disputes
          </Link>
        </p>
      </AppShell>
    )
  }

  const detail = data
  const evidence = ev.data?.items ?? []

  return (
    <EvidenceProvider evidence={evidence}>
      <AppShell
        title={`${detail.dispute.dispute_id} · ${detail.dispute.customer_name}`}
        subtitle={`${detail.dispute.reason} · ${inr(detail.dispute.amount)}`}
        breadcrumb={
          <span>
            <Link to="/disputes" className="hover:underline">
              Disputes
            </Link>{' '}
            / {detail.dispute.dispute_id}
          </span>
        }
        actions={<EvidencePackagePanel disputeId={detail.dispute.dispute_id} />}
      >
        <div className="grid gap-10 xl:grid-cols-[minmax(0,1fr)_22rem]">
          <div className="min-w-0 space-y-9">
            <CaseHeader detail={detail} />

            <Section title="Customer claim" description="The cardholder's stated reason for the chargeback.">
              <blockquote className="border-l-2 border-line-strong pl-4">
                <p className="text-lg leading-snug text-ink">“{detail.dispute.claim}”</p>
              </blockquote>
              <dl className="mt-4 grid gap-x-8 gap-y-3 sm:grid-cols-3">
                <div>
                  <dt className="label">Dispute reason</dt>
                  <dd className="mt-1 text-sm text-ink-2">{detail.dispute.reason}</dd>
                </div>
                <div>
                  <dt className="label">Claim submitted</dt>
                  <dd className="num mt-1 text-sm text-ink-2">{dateOnly(detail.dispute.created_at)}</dd>
                </div>
                <div>
                  <dt className="label">Issuer detail</dt>
                  <dd className="mt-1 text-sm text-ink-2">{detail.dispute.claim_detail}</dd>
                </div>
              </dl>
            </Section>

            <Section
              title="AI assessment"
              description="Advisory recommendation derived from the correlated evidence. Every factor links to its record."
            >
              <AssessmentBlock detail={detail} />
            </Section>

            <Section
              title="Claim versus evidence"
              description="What the customer states, set against what the records show."
            >
              <div className="grid gap-6 lg:grid-cols-[minmax(0,18rem)_1fr]">
                <div className="rounded border border-line bg-raised/40 p-4">
                  <p className="label">Customer claim</p>
                  <p className="mt-2 text-sm italic text-ink">“{detail.dispute.claim}”</p>
                </div>
                <div>
                  <p className="label mb-2">Available evidence</p>
                  <dl className="divide-y divide-line border-y border-line">
                    {detail.claim_vs_evidence.map((row) => (
                      <div key={row.aspect} className="grid gap-1 py-2.5 sm:grid-cols-[12rem_1fr] sm:gap-4">
                        <dt className="text-sm text-ink-3">{row.aspect}</dt>
                        <dd className="text-sm text-ink">
                          {row.record} <EvidenceRef id={row.evidence_id} />
                        </dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </div>
            </Section>

            <Section
              title="Contradictions"
              description="Raised only where the records genuinely disagree."
            >
              <Contradictions conflicts={detail.conflicts} />
            </Section>

            <Section
              title="Evidence gaps"
              description="Records that would strengthen the case but are not available."
            >
              {detail.gaps.length === 0 ? (
                <EmptyBlock title="No material evidence gaps" hint="Every artefact required by policy is on file." />
              ) : (
                <ul className="divide-y divide-line border-y border-line">
                  {detail.gaps.map((g: Gap) => (
                    <li key={g.missing} className="grid gap-2 py-3.5 sm:grid-cols-[16rem_1fr_8rem] sm:gap-6">
                      <div>
                        <p className="text-sm font-medium text-ink">{g.missing}</p>
                        <p className="mt-0.5 text-2xs text-ink-3">Missing</p>
                      </div>
                      <p className="text-sm text-ink-2">{g.why_it_matters}</p>
                      <div className="sm:text-right">
                        <Pill tone={g.impact === 'high' ? 'critical' : g.impact === 'medium' ? 'caution' : 'neutral'}>
                          {g.availability}
                        </Pill>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Section>

            <Section
              title="Evidence strength"
              description="Operational completeness indicator per source — not a statistical certainty."
              actions={
                <span className="num text-sm text-ink-2">{detail.assessment.evidence_completeness}% complete</span>
              }
            >
              <ul className="grid gap-x-10 gap-y-2.5 sm:grid-cols-2">
                {detail.evidence_strength.map((s) => (
                  <li key={s.category} className="flex items-center justify-between gap-4 border-b border-line/60 py-1.5">
                    <span className="text-sm text-ink-2">{s.label}</span>
                    <span className="flex items-center gap-3">
                      <span className="w-24">
                        <Meter
                          value={Math.min(100, (s.score / 4) * 100)}
                          tone={s.strength === 'Strong' ? 'positive' : s.strength === 'Moderate' ? 'caution' : 'neutral'}
                        />
                      </span>
                      <span className="w-16 text-right text-sm text-ink">{s.strength}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </Section>

            <Section
              title="Investigation progress"
              description="Functional modules that retrieved and analysed the case records."
            >
              <InvestigationProgress detail={detail} disputeId={detail.dispute.dispute_id} />
            </Section>

            <Section
              title="Reconstructed timeline"
              description="Events sequenced across payment, order, fulfilment, delivery, customer and dispute systems. Select an event to see its evidence."
            >
              <Timeline disputeId={detail.dispute.dispute_id} />
            </Section>

            <Section
              title="Evidence explorer"
              description="Every record retrieved for this case, with its source, impact and availability."
            >
              {ev.loading && <LoadingBlock label="Loading evidence" />}
              {ev.error && <ErrorBlock message={ev.error} onRetry={ev.reload} />}
              {!ev.loading && !ev.error && <EvidenceExplorer evidence={evidence} />}
            </Section>

            <Section
              title="Evidence provenance"
              description="The records the recommendation rests on."
            >
              <div className="rounded border border-line px-4 py-3.5">
                <p className="text-sm text-ink-2">
                  Recommendation{' '}
                  <span className="font-semibold text-ink">{detail.assessment.recommendation_label}</span> is
                  supported by:
                </p>
                <ul className="mt-2.5 space-y-1.5">
                  {detail.assessment.supporting_factors.slice(0, 4).map((f) => (
                    <li key={f.evidence_id} className="flex items-baseline gap-2 text-sm text-ink-2">
                      <EvidenceRef id={f.evidence_id} />
                      <span>{f.text}</span>
                    </li>
                  ))}
                  {detail.assessment.supporting_factors.length === 0 && (
                    <li className="text-sm text-ink-3">
                      No merchant-supporting record exists; the recommendation rests on the cardholder-supporting
                      evidence listed above.
                    </li>
                  )}
                </ul>
              </div>
            </Section>

            <Section title="Merchant argument" description="Drafted from the evidence on file.">
              <p className="max-w-3xl text-sm leading-relaxed text-ink-2">{detail.argument}</p>
              {detail.policies.length > 0 && (
                <div className="mt-5 rounded border border-line bg-raised/40 px-4 py-3">
                  <p className="label">Policy knowledge · reference only</p>
                  {detail.policies.map((p) => (
                    <p key={p.policy_id} className="mt-1.5 text-xs text-ink-2">
                      <span className="num font-medium text-ink">{p.policy_id}</span> {p.name} —{' '}
                      {p.response_requirements}
                    </p>
                  ))}
                  <p className="mt-2 text-2xs text-ink-3">
                    Policy text describes what a response must contain. It never evidences that an event occurred.
                  </p>
                </div>
              )}
            </Section>

            <Section title="Human review" description="The final decision is always taken by an operator.">
              <HumanReview detail={detail} disputeId={detail.dispute.dispute_id} onRecorded={reload} />
            </Section>
          </div>

          {/* Contextual copilot — supporting, not central */}
          <aside className="xl:sticky xl:top-24 xl:self-start">
            <Copilot disputeId={detail.dispute.dispute_id} suggestions={detail.copilot_suggestions} />
            <div className="card mt-4 p-4">
              <p className="label">Case record</p>
              <dl className="mt-2.5 space-y-2 text-xs">
                <div className="flex justify-between gap-3">
                  <dt className="text-ink-3">Payment method</dt>
                  <dd className="text-right text-ink-2">{String(detail.transaction.payment_method)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-ink-3">Authentication</dt>
                  <dd className="text-right text-ink-2">{String(detail.transaction.three_ds)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-ink-3">Product</dt>
                  <dd className="text-right text-ink-2">{detail.order.product}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-ink-3">Fulfilment</dt>
                  <dd className="text-right text-ink-2">{titleCase(String(detail.order.fulfillment_status))}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-ink-3">Delivery</dt>
                  <dd className="text-right text-ink-2">{titleCase(String(detail.order.delivery_status))}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-ink-3">Refunds</dt>
                  <dd className="text-right text-ink-2">
                    {detail.refunds.length
                      ? detail.refunds.map((r) => `${inr(r.amount)} (${r.status})`).join(', ')
                      : 'None issued'}
                  </dd>
                </div>
              </dl>
            </div>
          </aside>
        </div>
      </AppShell>
    </EvidenceProvider>
  )
}
