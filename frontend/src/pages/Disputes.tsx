import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AppShell } from '../components/AppShell'
import { EmptyBlock, ErrorBlock, LoadingBlock, Meter, Pill } from '../components/ui'
import { useApi } from '../lib/api'
import type { DisputeSummary } from '../lib/types'
import { recommendationTone } from '../lib/format'
import { DeadlineCell, StatusCell } from './Dashboard'

interface DisputeList {
  results: DisputeSummary[]
  total: number
  filtered: number
  facets: { status: string[]; reason: string[]; recommendation: string[]; deadline: string[] }
}

const AMOUNTS = [
  { label: 'Any amount', min: '', max: '' },
  { label: 'Under ₹10,000', min: '', max: '9999' },
  { label: '₹10,000 – ₹25,000', min: '10000', max: '25000' },
  { label: 'Above ₹25,000', min: '25001', max: '' },
]

const COMPLETENESS = [
  { label: 'Any completeness', value: '' },
  { label: '≥ 90%', value: '90' },
  { label: '≥ 80%', value: '80' },
  { label: '≥ 70%', value: '70' },
]

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: { label: string; value: string }[]
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="label">{label}</span>
      <select className="field" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  )
}

export default function Disputes() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('all')
  const [reason, setReason] = useState('all')
  const [rec, setRec] = useState('all')
  const [deadline, setDeadline] = useState('all')
  const [amountIdx, setAmountIdx] = useState('0')
  const [completeness, setCompleteness] = useState('')
  const [sort, setSort] = useState('deadline')

  const path = useMemo(() => {
    const p = new URLSearchParams()
    if (q.trim()) p.set('q', q.trim())
    if (status !== 'all') p.set('status', status)
    if (reason !== 'all') p.set('reason', reason)
    if (rec !== 'all') p.set('recommendation', rec)
    if (deadline !== 'all') p.set('deadline', deadline)
    const amount = AMOUNTS[Number(amountIdx)]
    if (amount.min) p.set('min_amount', amount.min)
    if (amount.max) p.set('max_amount', amount.max)
    if (completeness) p.set('min_completeness', completeness)
    return `/api/disputes${p.toString() ? `?${p}` : ''}`
  }, [q, status, reason, rec, deadline, amountIdx, completeness])

  const { data, loading, error, reload } = useApi<DisputeList>(path)

  const rows = useMemo(() => {
    const list = [...(data?.results ?? [])]
    if (sort === 'amount') list.sort((a, b) => b.amount - a.amount)
    if (sort === 'confidence') list.sort((a, b) => b.confidence - a.confidence)
    if (sort === 'created') list.sort((a, b) => b.created_at.localeCompare(a.created_at))
    return list
  }, [data, sort])

  const clear = () => {
    setQ('')
    setStatus('all')
    setReason('all')
    setRec('all')
    setDeadline('all')
    setAmountIdx('0')
    setCompleteness('')
  }

  const filtersActive =
    Boolean(q) || status !== 'all' || reason !== 'all' || rec !== 'all' || deadline !== 'all' ||
    amountIdx !== '0' || completeness !== ''

  return (
    <AppShell
      title="Disputes"
      subtitle="Every chargeback in the queue with its investigation state."
      actions={
        data && (
          <span className="num text-sm text-ink-3">
            {data.filtered} of {data.total}
          </span>
        )
      }
    >
      <div className="space-y-5">
        <div className="flex flex-col gap-4">
          <label className="relative block max-w-xl">
            <span className="sr-only">Search disputes</span>
            <input
              type="search"
              className="field py-2 pl-8"
              placeholder="Search dispute ID, customer, transaction ID or order ID"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-3" aria-hidden>
              ⌕
            </span>
          </label>

          <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-6">
            <Select
              label="Status"
              value={status}
              onChange={setStatus}
              options={[
                { label: 'All statuses', value: 'all' },
                ...(data?.facets.status ?? []).map((s) => ({ label: s, value: s })),
              ]}
            />
            <Select
              label="Reason"
              value={reason}
              onChange={setReason}
              options={[
                { label: 'All reasons', value: 'all' },
                ...(data?.facets.reason ?? []).map((s) => ({ label: s, value: s })),
              ]}
            />
            <Select
              label="Recommendation"
              value={rec}
              onChange={setRec}
              options={[
                { label: 'All recommendations', value: 'all' },
                { label: 'Contest', value: 'CONTEST' },
                { label: 'Accept / refund', value: 'ACCEPT' },
                { label: 'Human review', value: 'HUMAN_REVIEW' },
              ]}
            />
            <Select
              label="Amount"
              value={amountIdx}
              onChange={setAmountIdx}
              options={AMOUNTS.map((a, i) => ({ label: a.label, value: String(i) }))}
            />
            <Select
              label="Evidence"
              value={completeness}
              onChange={setCompleteness}
              options={COMPLETENESS.map((c) => ({ label: c.label, value: c.value }))}
            />
            <Select
              label="Deadline"
              value={deadline}
              onChange={setDeadline}
              options={[
                { label: 'Any deadline', value: 'all' },
                { label: 'Today', value: 'today' },
                { label: 'Tomorrow', value: 'tomorrow' },
                { label: 'Later', value: 'later' },
                { label: 'Overdue', value: 'overdue' },
              ]}
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Select
              label="Sort by"
              value={sort}
              onChange={setSort}
              options={[
                { label: 'Deadline (soonest)', value: 'deadline' },
                { label: 'Amount (highest)', value: 'amount' },
                { label: 'Confidence (highest)', value: 'confidence' },
                { label: 'Date created (newest)', value: 'created' },
              ]}
            />
            {filtersActive && (
              <button type="button" className="btn-ghost mt-5" onClick={clear}>
                Clear filters
              </button>
            )}
          </div>
        </div>

        {loading && <LoadingBlock label="Loading disputes" />}
        {error && <ErrorBlock message={error} onRetry={reload} />}

        {data && !loading && !error && (
          rows.length === 0 ? (
            <EmptyBlock
              title="No disputes match these filters"
              hint="Try widening the amount range, clearing the deadline filter or searching a different identifier."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[76rem] border-collapse text-sm">
                <caption className="sr-only">Dispute queue</caption>
                <thead>
                  <tr className="border-y border-line text-left">
                    <th scope="col" className="label py-2 pr-4">Dispute ID</th>
                    <th scope="col" className="label py-2 pr-4">Customer</th>
                    <th scope="col" className="label py-2 pr-4 text-right">Amount</th>
                    <th scope="col" className="label py-2 pr-4">Reason</th>
                    <th scope="col" className="label py-2 pr-4">Created</th>
                    <th scope="col" className="label py-2 pr-4">Deadline</th>
                    <th scope="col" className="label py-2 pr-4">Recommendation</th>
                    <th scope="col" className="label py-2 pr-4 text-right">Confidence</th>
                    <th scope="col" className="label py-2 pr-4">Evidence</th>
                    <th scope="col" className="label py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((d) => (
                    <tr
                      key={d.dispute_id}
                      tabIndex={0}
                      className="row-link border-b border-line/70 focus:bg-raised"
                      onClick={() => navigate(`/disputes/${d.dispute_id}`)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') navigate(`/disputes/${d.dispute_id}`)
                      }}
                    >
                      <td className="py-2.5 pr-4">
                        <Link
                          to={`/disputes/${d.dispute_id}`}
                          className="num font-medium text-ink underline-offset-4 hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {d.dispute_id}
                        </Link>
                        {d.conflicts > 0 && (
                          <span className="ml-2 text-2xs text-caution">
                            {d.conflicts} conflict{d.conflicts > 1 ? 's' : ''}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 pr-4 text-ink-2">
                        {d.customer_name}
                        <span className="block text-2xs text-ink-3">{d.order_id}</span>
                      </td>
                      <td className="num py-2.5 pr-4 text-right font-medium">{d.amount_label}</td>
                      <td className="py-2.5 pr-4 text-ink-2">{d.reason}</td>
                      <td className="num py-2.5 pr-4 text-ink-3">{d.created_label}</td>
                      <td className="py-2.5 pr-4 text-ink-2">
                        <DeadlineCell d={d} />
                      </td>
                      <td className="py-2.5 pr-4">
                        <Pill tone={recommendationTone(d.recommendation)}>{d.recommendation_label}</Pill>
                      </td>
                      <td className="num py-2.5 pr-4 text-right text-ink-2">{d.confidence}%</td>
                      <td className="py-2.5 pr-4">
                        <div className="flex w-28 items-center gap-2">
                          <Meter
                            value={d.evidence_completeness}
                            tone={d.evidence_completeness >= 85 ? 'positive' : d.evidence_completeness >= 70 ? 'caution' : 'critical'}
                          />
                          <span className="num text-2xs text-ink-3">{d.evidence_completeness}%</span>
                        </div>
                      </td>
                      <td className="py-2.5">
                        <StatusCell status={d.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>
    </AppShell>
  )
}
