import { Link, useNavigate } from 'react-router-dom'
import { AppShell } from '../components/AppShell'
import {
  BarList,
  EmptyBlock,
  ErrorBlock,
  LoadingBlock,
  Meter,
  Pill,
  Section,
  StatusDot,
} from '../components/ui'
import { useApi } from '../lib/api'
import type { DashboardData, DisputeSummary } from '../lib/types'
import { recommendationTone } from '../lib/format'

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

export function DeadlineCell({ d }: { d: DisputeSummary }) {
  const tone =
    d.deadline.bucket === 'overdue' || d.deadline.bucket === 'today'
      ? 'critical'
      : d.deadline.bucket === 'tomorrow'
        ? 'caution'
        : 'neutral'
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <StatusDot tone={tone} />
      <span className="num">{d.deadline.date_label}</span>
    </span>
  )
}

export function StatusCell({ status }: { status: string }) {
  const tone =
    status === 'Needs review'
      ? 'caution'
      : status === 'Evidence ready' || status === 'Response approved' || status === 'Won'
        ? 'positive'
        : status === 'Escalated'
          ? 'critical'
          : 'neutral'
  return <Pill tone={tone}>{status}</Pill>
}

export default function Dashboard() {
  const { data, loading, error, reload } = useApi<DashboardData>('/api/dashboard')
  const navigate = useNavigate()

  return (
    <AppShell
      title={`${greeting()} · Risk Operations`}
      subtitle="Monitor active disputes, investigation progress, evidence readiness and upcoming deadlines."
      actions={
        <>
          {data && (
            <span className="text-xs text-ink-3">
              Queue as of{' '}
              {new Date(data.as_of).toLocaleString('en-IN', {
                day: '2-digit',
                month: 'short',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          )}
          <Link to="/disputes" className="btn-secondary">
            All disputes
          </Link>
        </>
      }
    >
      {loading && <LoadingBlock label="Loading operations overview" />}
      {error && <ErrorBlock message={error} onRetry={reload} />}

      {data && (
        <div className="space-y-9">
          {/* Summary strip */}
          <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line sm:grid-cols-3 lg:grid-cols-5">
            {data.summary.map((s) => (
              <div key={s.key} className="bg-surface px-4 py-3.5">
                <p className="label">{s.label}</p>
                <p className="num mt-1.5 text-[1.75rem] font-semibold leading-none tracking-tight text-ink">
                  {s.value}
                </p>
                <p className="mt-1.5 text-xs text-ink-3">{s.sub}</p>
              </div>
            ))}
          </div>

          {/* Priority disputes */}
          <Section
            title="Priority disputes"
            description="Ranked by response deadline, then exposure."
            actions={
              <Link to="/disputes" className="text-sm text-accent underline-offset-4 hover:underline">
                View all
              </Link>
            }
          >
            {data.priority.length === 0 ? (
              <EmptyBlock title="No open disputes" hint="New disputes appear here as they are ingested." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[62rem] border-collapse text-sm">
                  <caption className="sr-only">Priority disputes requiring attention</caption>
                  <thead>
                    <tr className="border-y border-line text-left">
                      <th scope="col" className="label py-2 pr-4">Dispute</th>
                      <th scope="col" className="label py-2 pr-4">Customer</th>
                      <th scope="col" className="label py-2 pr-4 text-right">Amount</th>
                      <th scope="col" className="label py-2 pr-4">Reason</th>
                      <th scope="col" className="label py-2 pr-4">Deadline</th>
                      <th scope="col" className="label py-2 pr-4">AI assessment</th>
                      <th scope="col" className="label py-2 pr-4 text-right">Evidence</th>
                      <th scope="col" className="label py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.priority.map((d) => (
                      <tr
                        key={d.dispute_id}
                        className="row-link border-b border-line/70"
                        onClick={() => navigate(`/disputes/${d.dispute_id}`)}
                      >
                        <td className="py-2.5 pr-4">
                          <Link
                            to={`/disputes/${d.dispute_id}`}
                            className="num font-medium text-ink underline-offset-4 hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {d.dispute_id}
                          </Link>
                        </td>
                        <td className="py-2.5 pr-4 text-ink-2">{d.customer_name}</td>
                        <td className="num py-2.5 pr-4 text-right font-medium">{d.amount_label}</td>
                        <td className="py-2.5 pr-4 text-ink-2">{d.reason}</td>
                        <td className="py-2.5 pr-4 text-ink-2">
                          <DeadlineCell d={d} />
                        </td>
                        <td className="py-2.5 pr-4">
                          <Pill tone={recommendationTone(d.recommendation)}>{d.recommendation_label}</Pill>
                        </td>
                        <td className="num py-2.5 pr-4 text-right text-ink-2">{d.evidence_completeness}%</td>
                        <td className="py-2.5">
                          <StatusCell status={d.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          <div className="grid gap-9 lg:grid-cols-[1.1fr_1fr]">
            {/* Investigation health */}
            <Section title="Investigation health" description="Operational state of the investigation pipeline.">
              <dl className="space-y-4">
                <div>
                  <div className="flex items-baseline justify-between">
                    <dt className="text-sm text-ink-2">Cases investigated this week</dt>
                    <dd className="num text-sm font-medium">{data.health.investigated_this_week}</dd>
                  </div>
                </div>
                <div>
                  <div className="flex items-baseline justify-between">
                    <dt className="text-sm text-ink-2">Evidence completeness</dt>
                    <dd className="num text-sm font-medium">{data.health.evidence_completeness}%</dd>
                  </div>
                  <div className="mt-2">
                    <Meter value={data.health.evidence_completeness} tone="accent" />
                  </div>
                  <p className="mt-1.5 text-xs text-ink-3">Weighted mean across open cases.</p>
                </div>
                <div>
                  <div className="flex items-baseline justify-between">
                    <dt className="text-sm text-ink-2">Cases with contradictions</dt>
                    <dd className="num text-sm font-medium">
                      {data.health.cases_with_contradictions}{' '}
                      <span className="text-ink-3">of {data.health.open_total}</span>
                    </dd>
                  </div>
                  <div className="mt-2">
                    <Meter
                      value={(data.health.cases_with_contradictions / Math.max(1, data.health.open_total)) * 100}
                      tone="caution"
                    />
                  </div>
                </div>
                <div>
                  <div className="flex items-baseline justify-between">
                    <dt className="text-sm text-ink-2">Cases awaiting human approval</dt>
                    <dd className="num text-sm font-medium">{data.health.awaiting_approval}</dd>
                  </div>
                  <div className="mt-2">
                    <Meter
                      value={(data.health.awaiting_approval / Math.max(1, data.health.open_total)) * 100}
                      tone="info"
                    />
                  </div>
                </div>
              </dl>

              <div className="mt-6 border-t border-line pt-4">
                <p className="label mb-3">Recommendation mix · open cases</p>
                <BarList
                  items={Object.entries(data.health.by_recommendation).map(([label, count]) => ({
                    label:
                      label === 'HUMAN_REVIEW'
                        ? 'Human review'
                        : label === 'CONTEST'
                          ? 'Contest'
                          : 'Accept / refund',
                    count,
                  }))}
                />
              </div>
            </Section>

            {/* Deadlines */}
            <Section title="Upcoming deadlines" description="Cases that need a response soon.">
              {data.deadlines.length === 0 ? (
                <EmptyBlock title="No deadlines in the next 72 hours" />
              ) : (
                <ul className="divide-y divide-line">
                  {data.deadlines.map((d) => (
                    <li key={d.dispute_id}>
                      <Link
                        to={`/disputes/${d.dispute_id}`}
                        className="-mx-2 flex items-start justify-between gap-4 rounded px-2 py-3 transition-colors hover:bg-raised/70"
                      >
                        <div className="min-w-0">
                          <p
                            className={`label ${
                              d.deadline.bucket === 'today' || d.deadline.bucket === 'overdue'
                                ? 'text-critical'
                                : d.deadline.bucket === 'tomorrow'
                                  ? 'text-caution'
                                  : ''
                            }`}
                          >
                            {d.deadline.bucket === 'today'
                              ? 'Today'
                              : d.deadline.bucket === 'tomorrow'
                                ? 'Tomorrow'
                                : d.deadline.bucket === 'overdue'
                                  ? 'Overdue'
                                  : d.deadline.date_label}
                          </p>
                          <p className="num mt-1 text-sm font-medium text-ink">{d.dispute_id}</p>
                          <p className="mt-0.5 text-xs text-ink-3">
                            {d.deadline.label} · {d.reason}
                          </p>
                        </div>
                        <span className="num shrink-0 text-sm font-medium">{d.amount_label}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Section>
          </div>
        </div>
      )}
    </AppShell>
  )
}
