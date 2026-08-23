import { useRef, useState } from 'react'
import { api, ApiError } from '../lib/api'
import type { CopilotAnswer } from '../lib/types'
import { EvidenceRef } from './EvidenceDrawer'
import { Spinner } from './ui'

interface Entry {
  question: string
  answer: CopilotAnswer | null
  error?: string
}

export function Copilot({
  disputeId,
  suggestions,
}: {
  disputeId: string
  suggestions: string[]
}) {
  const [entries, setEntries] = useState<Entry[]>([])
  const [value, setValue] = useState('')
  const [busy, setBusy] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  const ask = async (question: string) => {
    const q = question.trim()
    if (!q || busy) return
    setBusy(true)
    setValue('')
    setEntries((e) => [...e, { question: q, answer: null }])
    try {
      const answer = await api.post<CopilotAnswer>(`/api/disputes/${disputeId}/copilot`, { question: q })
      setEntries((e) => e.map((x, i) => (i === e.length - 1 ? { ...x, answer } : x)))
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Copilot is unavailable.'
      setEntries((e) => e.map((x, i) => (i === e.length - 1 ? { ...x, error: message } : x)))
    } finally {
      setBusy(false)
      requestAnimationFrame(() => listRef.current?.scrollTo({ top: 1e6, behavior: 'smooth' }))
    }
  }

  return (
    <div className="card flex h-full flex-col">
      <header className="border-b border-line px-4 py-3">
        <h2 className="section-title">Copilot</h2>
        <p className="mt-1 text-xs text-ink-3">Ask about this investigation</p>
      </header>

      <div ref={listRef} className="max-h-[28rem] flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {entries.length === 0 && (
          <p className="text-xs leading-relaxed text-ink-3">
            Answers are assembled only from the records retrieved for {disputeId}. If a record does not exist,
            the copilot says so rather than guessing.
          </p>
        )}

        {entries.map((entry, i) => (
          <div key={i} className="space-y-2">
            <p className="text-sm font-medium text-ink">{entry.question}</p>
            {!entry.answer && !entry.error && (
              <p className="flex items-center gap-2 text-xs text-ink-3">
                <Spinner /> Reading the investigation state…
              </p>
            )}
            {entry.error && (
              <p className="rounded border border-critical/25 bg-critical-soft/50 px-2.5 py-2 text-xs text-critical">
                {entry.error}
              </p>
            )}
            {entry.answer && (
              <div className="rounded border border-line bg-raised/40 px-3 py-2.5">
                <p className="text-sm text-ink">{entry.answer.headline}</p>
                {entry.answer.lines.length > 0 && (
                  <ul className="mt-2 space-y-1.5">
                    {entry.answer.lines.map((line, j) => (
                      <li key={j} className="text-xs leading-relaxed text-ink-2">
                        {line}
                      </li>
                    ))}
                  </ul>
                )}
                {entry.answer.evidence_ids.length > 0 && (
                  <div className="mt-2.5 flex flex-wrap items-center gap-1.5 border-t border-line pt-2">
                    <span className="label">Evidence</span>
                    {entry.answer.evidence_ids.map((id) => (
                      <EvidenceRef key={id} id={id} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="border-t border-line px-4 py-3">
        <div className="mb-2.5 flex flex-wrap gap-1.5">
          {suggestions.slice(0, entries.length ? 3 : 7).map((s) => (
            <button
              key={s}
              type="button"
              className="rounded-sm border border-line bg-surface px-2 py-1 text-2xs text-ink-2 transition-colors hover:border-line-strong hover:bg-raised hover:text-ink"
              onClick={() => ask(s)}
              disabled={busy}
            >
              {s}
            </button>
          ))}
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            ask(value)
          }}
        >
          <label className="sr-only" htmlFor="copilot-input">
            Ask about this investigation
          </label>
          <input
            id="copilot-input"
            className="field"
            placeholder="Ask about this case…"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={busy}
          />
          <button type="submit" className="btn-primary" disabled={busy || !value.trim()}>
            Ask
          </button>
        </form>
      </div>
    </div>
  )
}
