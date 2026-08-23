import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { Evidence } from '../lib/types'
import { Pill } from './ui'
import { categoryLabel, dateTime, impactLabel } from '../lib/format'

interface EvidenceCtx {
  open: (id: string) => void
  get: (id: string) => Evidence | undefined
}

const Ctx = createContext<EvidenceCtx>({ open: () => {}, get: () => undefined })

export const useEvidence = () => useContext(Ctx)

export const impactTone = (impact: string) =>
  impact === 'merchant' ? 'positive' : impact === 'customer' ? 'caution' : 'neutral'

export const availabilityTone = (a: string) =>
  a === 'available' ? 'neutral' : a === 'partial' ? 'caution' : 'critical'

/** Inline, clickable provenance reference — every conclusion links to its record. */
export function EvidenceRef({ id }: { id: string }) {
  const { open, get } = useEvidence()
  const known = get(id)
  if (!known) return <span className="num text-2xs text-ink-3">{id}</span>
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation()
        open(id)
      }}
      className="num rounded-sm border border-line bg-raised px-1 py-px text-2xs font-medium text-ink-2 transition-colors hover:border-accent/40 hover:bg-accent-soft hover:text-accent"
      title={`${known.evidence_type} — ${known.source}`}
    >
      {id}
    </button>
  )
}

export function EvidenceProvider({
  evidence,
  children,
}: {
  evidence: Evidence[]
  children: ReactNode
}) {
  const [openId, setOpenId] = useState<string | null>(null)
  const index = useMemo(() => new Map(evidence.map((e) => [e.evidence_id, e])), [evidence])

  const open = useCallback((id: string) => setOpenId(id), [])
  const get = useCallback((id: string) => index.get(id), [index])
  const value = useMemo(() => ({ open, get }), [open, get])
  const current = openId ? index.get(openId) : undefined

  return (
    <Ctx.Provider value={value}>
      {children}
      {current && <EvidenceDrawer evidence={current} onClose={() => setOpenId(null)} />}
    </Ctx.Provider>
  )
}

function EvidenceDrawer({ evidence, onClose }: { evidence: Evidence; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-ink/20" onClick={onClose}>
      <aside
        className="animate-in flex h-full w-full max-w-md flex-col border-l border-line bg-surface shadow-panel"
        role="dialog"
        aria-modal="true"
        aria-label={`Evidence record ${evidence.evidence_id}`}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
          <div>
            <p className="num text-sm font-semibold text-ink">{evidence.evidence_id}</p>
            <p className="mt-0.5 text-sm text-ink-2">{evidence.evidence_type}</p>
          </div>
          <button type="button" className="btn-ghost px-2 py-1" onClick={onClose} aria-label="Close evidence record">
            ✕
          </button>
        </header>

        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-4 text-sm">
          <div className="flex flex-wrap gap-1.5">
            <Pill tone="neutral">{categoryLabel[evidence.category] ?? evidence.category}</Pill>
            <Pill tone={impactTone(evidence.impact)}>{impactLabel[evidence.impact]}</Pill>
            <Pill tone={evidence.relevance === 'high' ? 'accent' : 'neutral'}>
              {evidence.relevance} relevance
            </Pill>
            <Pill tone={availabilityTone(evidence.availability)}>{evidence.availability}</Pill>
          </div>

          <div>
            <p className="label mb-1">Finding</p>
            <p className="text-ink">{evidence.finding}</p>
          </div>

          <div>
            <p className="label mb-1">Description</p>
            <p className="text-ink-2">{evidence.description}</p>
          </div>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 border-t border-line pt-4">
            <div>
              <dt className="label">Source</dt>
              <dd className="mt-0.5 text-ink-2">{evidence.source}</dd>
            </div>
            <div>
              <dt className="label">Timestamp</dt>
              <dd className="num mt-0.5 text-ink-2">{evidence.timestamp ? dateTime(evidence.timestamp) : 'Not time-stamped'}</dd>
            </div>
          </dl>

          {Object.keys(evidence.fields ?? {}).length > 0 && (
            <div className="border-t border-line pt-4">
              <p className="label mb-2">Record fields</p>
              <dl className="divide-y divide-line/70 rounded border border-line">
                {Object.entries(evidence.fields).map(([k, v]) => (
                  <div key={k} className="grid grid-cols-[10rem_1fr] gap-3 px-3 py-2">
                    <dt className="text-xs text-ink-3">{k}</dt>
                    <dd className="text-xs text-ink-2">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}

          {(evidence.referenced_by?.length ?? 0) > 0 && (
            <div className="border-t border-line pt-4">
              <p className="label mb-2">Used by investigation modules</p>
              <ul className="space-y-1 text-xs text-ink-2">
                {evidence.referenced_by!.map((m) => (
                  <li key={m}>· {m}</li>
                ))}
              </ul>
            </div>
          )}

          {(evidence.linked_events?.length ?? 0) > 0 && (
            <div className="border-t border-line pt-4">
              <p className="label mb-2">Linked timeline events</p>
              <ul className="space-y-1 text-xs text-ink-2">
                {evidence.linked_events!.map((m) => (
                  <li key={m}>· {m}</li>
                ))}
              </ul>
            </div>
          )}

          {evidence.availability === 'unavailable' && (
            <p className="rounded border border-critical/25 bg-critical-soft/50 px-3 py-2 text-xs text-critical">
              This record is not available in the merchant's systems. It is listed so the gap is visible, and it
              carries no weight in the assessment.
            </p>
          )}
        </div>

        <footer className="border-t border-line px-5 py-3 text-2xs text-ink-3">
          Synthetic record from the demo dataset.
        </footer>
      </aside>
    </div>
  )
}
