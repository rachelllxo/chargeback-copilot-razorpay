import { Link } from 'react-router-dom'
import { AppShell } from '../components/AppShell'
import { EmptyBlock, ErrorBlock, LoadingBlock, Meter, Pill, Section } from '../components/ui'
import { useApi } from '../lib/api'
import type { DisputeSummary } from '../lib/types'
import { recommendationTone } from '../lib/format'

const PIPELINE = [
  'Retrieve evidence',
  'Investigate sources',
  'Correlate evidence',
  'Reconstruct timeline',
  'Detect contradictions',
  'Identify gaps',
  'Assess case',
  'Recommend action',
  'Human approval',
]

export default function Investigations() {
  const { data, loading, error, reload } = useApi<{ results: DisputeSummary[] }>('/api/disputes')

  const rows = (data?.results ?? []).filter((r) => !r.closed)
  const awaiting = rows.filter((r) => !r.human_decision)
  const decided = (data?.results ?? []).filter((r) => r.human_decision)

  return (
    <AppShell
      title="Investigations"
      subtitle="Investigation state of every case in the queue, from retrieval through to human approval."
    >
      {loading && <LoadingBlock label="Loading investigations" />}
      {error && <ErrorBlock message={error} onRetry={reload} />}

      {data && (
        <div className="space-y-9">
          <div>
            <p className="label mb-3">Pipeline</p>
            <ol className="flex flex-wrap items-center gap-x-2 gap-y-2 text-xs text-ink-2">
              {PIPELINE.map((step, i) => (
                <li key={step} className="flex items-center gap-2">
                  <span className="rounded-sm border border-line bg-surface px-2 py-1">{step}</span>
                  {i < PIPELINE.length - 1 && (
                    <span className="text-ink-3" aria-hidden>
                      →
                    </span>
                  )}
                </li>
              ))}
            </ol>
            <p className="mt-3 max-w-3xl text-sm text-ink-3">
              Twelve functional modules run per case — transaction, order, fulfilment, delivery, customer
              interaction, refund, historical and policy investigation, followed by evidence correlation,
              timeline reconstruction, contradiction detection and risk assessment. Each returns structured
              findings; the assessment is assembled from those findings, not from a chat.
            </p>
          </div>

          <Section
            title="Awaiting human approval"
            description="Investigation complete; a decision has not yet been recorded."
          >
            {awaiting.length === 0 ? (
              <EmptyBlock title="Every investigated case has a recorded decision" />
            ) : (
              <ul className="divide-y divide-line border-y border-line">
                {awaiting.map((r) => (
                  <li key={r.dispute_id}>
                    <Link
                      to={`/disputes/${r.dispute_id}`}
                      className="grid items-center gap-x-6 gap-y-2 px-1 py-3.5 transition-colors hover:bg-raised/60 md:grid-cols-[10rem_1fr_9rem_11rem_7rem]"
                    >
                      <span className="num text-sm font-medium text-ink">{r.dispute_id}</span>
                      <span className="text-sm text-ink-2">
                        {r.customer_name} · {r.reason}
                        {r.conflicts > 0 && (
                          <span className="ml-2 text-2xs text-caution">
                            {r.conflicts} contradiction{r.conflicts > 1 ? 's' : ''}
                          </span>
                        )}
                        {r.gaps > 0 && <span className="ml-2 text-2xs text-ink-3">{r.gaps} gaps</span>}
                      </span>
                      <Pill tone={recommendationTone(r.recommendation)}>{r.recommendation_label}</Pill>
                      <span className="flex items-center gap-2">
                        <Meter
                          value={r.evidence_completeness}
                          tone={r.evidence_completeness >= 85 ? 'positive' : 'caution'}
                        />
                        <span className="num text-2xs text-ink-3">{r.evidence_completeness}%</span>
                      </span>
                      <span className="num text-right text-sm">{r.amount_label}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section title="Decisions recorded" description="Cases where an operator has already acted.">
            {decided.length === 0 ? (
              <EmptyBlock
                title="No decisions recorded yet"
                hint="Approve, edit or escalate a case from its investigation page and it will appear here."
              />
            ) : (
              <ul className="divide-y divide-line border-y border-line">
                {decided.map((r) => (
                  <li key={r.dispute_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                    <Link to={`/disputes/${r.dispute_id}`} className="num text-sm font-medium text-ink hover:underline">
                      {r.dispute_id}
                    </Link>
                    <span className="text-sm text-ink-2">{r.reason}</span>
                    <Pill tone="accent">{r.status}</Pill>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </div>
      )}
    </AppShell>
  )
}
