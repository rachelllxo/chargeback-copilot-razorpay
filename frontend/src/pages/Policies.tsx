import { useState } from 'react'
import { AppShell } from '../components/AppShell'
import { EmptyBlock, ErrorBlock, LoadingBlock, Pill } from '../components/ui'
import { useApi } from '../lib/api'
import type { Policy } from '../lib/types'
import { dateOnly } from '../lib/format'

export default function Policies() {
  const [q, setQ] = useState('')
  const { data, loading, error, reload } = useApi<{ policies: Policy[]; note: string }>(
    `/api/policies${q.trim() ? `?q=${encodeURIComponent(q.trim())}` : ''}`,
  )
  const [openId, setOpenId] = useState<string | null>(null)

  return (
    <AppShell
      title="Policies"
      subtitle="Reference knowledge on what a response must contain for each dispute type."
    >
      <div className="space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <label className="flex w-full max-w-md flex-col gap-1">
            <span className="label">Search policies</span>
            <input
              className="field"
              type="search"
              placeholder="Policy name, ID or dispute type"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </label>
          <div className="rounded border border-line bg-raised/50 px-3 py-2">
            <p className="label">Policy knowledge</p>
            <p className="mt-1 max-w-md text-xs text-ink-2">
              Distinct from case evidence. A policy states what a valid response requires — it never evidences
              that an event occurred.
            </p>
          </div>
        </div>

        {loading && <LoadingBlock label="Loading policy knowledge base" />}
        {error && <ErrorBlock message={error} onRetry={reload} />}

        {data && (
          data.policies.length === 0 ? (
            <EmptyBlock title="No policies match that search" hint="Try a dispute type such as “not received”." />
          ) : (
            <ul className="divide-y divide-line border-y border-line">
              {data.policies.map((p) => {
                const open = openId === p.policy_id
                return (
                  <li key={p.policy_id}>
                    <button
                      type="button"
                      className="grid w-full items-baseline gap-x-6 gap-y-1 px-1 py-3.5 text-left transition-colors hover:bg-raised/60 lg:grid-cols-[7rem_1fr_14rem_8rem]"
                      onClick={() => setOpenId(open ? null : p.policy_id)}
                      aria-expanded={open}
                    >
                      <span className="num text-sm font-medium text-ink">{p.policy_id}</span>
                      <span className="text-sm text-ink">
                        {p.name}
                        <span className="mt-0.5 block text-xs text-ink-3">{p.networks}</span>
                      </span>
                      <span className="text-sm text-ink-2">{p.dispute_type}</span>
                      <span className="num text-xs text-ink-3 lg:text-right">
                        Updated {dateOnly(p.last_updated)}
                      </span>
                    </button>
                    {open && (
                      <div className="animate-in grid gap-6 border-t border-line bg-raised/30 px-4 py-4 lg:grid-cols-2">
                        <div>
                          <p className="label mb-2">Relevant evidence</p>
                          <ul className="space-y-1">
                            {p.relevant_evidence.map((e) => (
                              <li key={e} className="text-sm text-ink-2">
                                · {e}
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <p className="label mb-2">Response requirements</p>
                          <p className="text-sm leading-relaxed text-ink-2">{p.response_requirements}</p>
                          <p className="mt-3 flex flex-wrap gap-2">
                            <Pill tone="neutral">
                              Response window:{' '}
                              {p.response_window_days ? `${p.response_window_days} days` : 'Internal control'}
                            </Pill>
                            <Pill tone="accent">Policy knowledge</Pill>
                          </p>
                        </div>
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
          )
        )}

        {data && <p className="text-2xs text-ink-3">{data.note}</p>}
      </div>
    </AppShell>
  )
}
