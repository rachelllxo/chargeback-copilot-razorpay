import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AppShell } from '../components/AppShell'
import { EmptyBlock, ErrorBlock, LoadingBlock, Pill } from '../components/ui'
import { EvidenceProvider, availabilityTone, impactTone, useEvidence } from '../components/EvidenceDrawer'
import { useApi } from '../lib/api'
import type { DisputeSummary, Evidence } from '../lib/types'
import { categoryLabel, dateTime, impactLabel } from '../lib/format'

function EvidenceTable({ items }: { items: (Evidence & { dispute_id: string })[] }) {
  const { open } = useEvidence()
  if (items.length === 0) {
    return <EmptyBlock title="No evidence matches this view" hint="Choose a different case or category." />
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[62rem] border-collapse text-sm">
        <caption className="sr-only">Evidence records</caption>
        <thead>
          <tr className="border-y border-line text-left">
            <th scope="col" className="label py-2 pr-4">Evidence ID</th>
            <th scope="col" className="label py-2 pr-4">Type</th>
            <th scope="col" className="label py-2 pr-4">Source</th>
            <th scope="col" className="label py-2 pr-4">Timestamp</th>
            <th scope="col" className="label py-2 pr-4">Finding</th>
            <th scope="col" className="label py-2 pr-4">Impact</th>
            <th scope="col" className="label py-2">Availability</th>
          </tr>
        </thead>
        <tbody>
          {items.map((e) => (
            <tr
              key={e.evidence_id}
              className="row-link border-b border-line/70"
              tabIndex={0}
              onClick={() => open(e.evidence_id)}
              onKeyDown={(ev) => ev.key === 'Enter' && open(e.evidence_id)}
            >
              <td className="num py-2.5 pr-4 font-medium">{e.evidence_id}</td>
              <td className="py-2.5 pr-4 text-ink-2">
                {e.evidence_type}
                <span className="block text-2xs text-ink-3">{categoryLabel[e.category]}</span>
              </td>
              <td className="py-2.5 pr-4 text-ink-2">{e.source}</td>
              <td className="num py-2.5 pr-4 text-ink-3">{e.timestamp ? dateTime(e.timestamp) : '—'}</td>
              <td className="max-w-md py-2.5 pr-4 text-ink-2">{e.finding}</td>
              <td className="py-2.5 pr-4">
                <Pill tone={impactTone(e.impact)}>{impactLabel[e.impact]}</Pill>
              </td>
              <td className="py-2.5">
                <Pill tone={availabilityTone(e.availability)}>{e.availability}</Pill>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function EvidencePage() {
  const disputes = useApi<{ results: DisputeSummary[] }>('/api/disputes')
  const [caseId, setCaseId] = useState<string>('')
  const [category, setCategory] = useState('all')
  const [q, setQ] = useState('')

  const open = (disputes.data?.results ?? []).filter((d) => !d.closed)
  const selected = caseId || open[0]?.dispute_id || ''
  const evidence = useApi<{ items: Evidence[]; counts: Record<string, number> }>(
    selected ? `/api/disputes/${selected}/evidence` : null,
  )

  const items = useMemo(() => {
    let list = (evidence.data?.items ?? []).map((e) => ({ ...e, dispute_id: selected }))
    if (category !== 'all') list = list.filter((e) => e.category === category)
    if (q.trim()) {
      const needle = q.toLowerCase()
      list = list.filter((e) =>
        `${e.evidence_id} ${e.evidence_type} ${e.source} ${e.finding}`.toLowerCase().includes(needle),
      )
    }
    return list
  }, [evidence.data, category, q, selected])

  const counts = evidence.data?.counts ?? {}

  return (
    <AppShell
      title="Evidence"
      subtitle="Every record retrieved by the investigation modules, by case and source."
      actions={
        selected && (
          <Link to={`/disputes/${selected}`} className="btn-secondary">
            Open case
          </Link>
        )
      }
    >
      <EvidenceProvider evidence={evidence.data?.items ?? []}>
        <div className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <label className="flex flex-col gap-1">
              <span className="label">Case</span>
              <select className="field" value={selected} onChange={(e) => setCaseId(e.target.value)}>
                {open.map((d) => (
                  <option key={d.dispute_id} value={d.dispute_id}>
                    {d.dispute_id} — {d.customer_name} ({d.reason})
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="label">Category</span>
              <select className="field" value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="all">All categories ({counts.all ?? 0})</option>
                {Object.entries(counts)
                  .filter(([k]) => k !== 'all')
                  .map(([k, v]) => (
                    <option key={k} value={k}>
                      {categoryLabel[k] ?? k} ({v})
                    </option>
                  ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 xl:col-span-2">
              <span className="label">Search</span>
              <input
                className="field"
                type="search"
                placeholder="Evidence ID, type, source or finding"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </label>
          </div>

          {(disputes.loading || evidence.loading) && <LoadingBlock label="Loading evidence records" />}
          {(disputes.error || evidence.error) && (
            <ErrorBlock message={disputes.error ?? evidence.error ?? ''} onRetry={evidence.reload} />
          )}
          {!evidence.loading && !evidence.error && <EvidenceTable items={items} />}
        </div>
      </EvidenceProvider>
    </AppShell>
  )
}
