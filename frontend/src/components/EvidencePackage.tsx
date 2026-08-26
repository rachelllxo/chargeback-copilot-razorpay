import { createContext, useContext, useState, type ReactNode } from 'react'
import { api, ApiError } from '../lib/api'
import type { EvidencePackage, PackageSection } from '../lib/types'
import { ErrorBlock, Modal, Pill, Spinner, useToast } from './ui'

interface PackageCtx {
  open: () => void
}

const Ctx = createContext<PackageCtx>({ open: () => {} })

export const usePackage = () => useContext(Ctx)

function SectionBody({ section }: { section: PackageSection }) {
  if (section.kind === 'fields') {
    const rows = section.body as string[][]
    return (
      <dl className="divide-y divide-line rounded border border-line">
        {rows.map(([k, v]) => (
          <div key={k} className="grid grid-cols-[12rem_1fr] gap-3 px-3 py-2">
            <dt className="text-xs text-ink-3">{k}</dt>
            <dd className="num text-xs text-ink">{v}</dd>
          </div>
        ))}
      </dl>
    )
  }
  if (section.kind === 'quote') {
    const [claim, ...rest] = section.body as string[]
    return (
      <blockquote className="border-l-2 border-line-strong pl-3">
        <p className="text-sm italic text-ink">“{claim}”</p>
        {rest.map((r) => (
          <p key={r} className="mt-1.5 text-xs text-ink-2">
            {r}
          </p>
        ))}
      </blockquote>
    )
  }
  if (section.kind === 'list') {
    return (
      <ul className="space-y-1.5">
        {(section.body as string[]).map((line, i) => (
          <li key={i} className="flex gap-2 text-xs leading-relaxed text-ink-2">
            <span className="text-ink-3" aria-hidden>
              ·
            </span>
            <span>{line}</span>
          </li>
        ))}
      </ul>
    )
  }
  return (
    <div className="space-y-2">
      {(section.body as string[]).map((p, i) => (
        <p key={i} className="text-sm leading-relaxed text-ink-2">
          {p}
        </p>
      ))}
    </div>
  )
}

function toPlainText(pkg: EvidencePackage): string {
  const lines: string[] = [
    pkg.document_title,
    `Merchant: ${pkg.merchant.name} (${pkg.merchant.merchant_id})`,
    `Generated: ${new Date(pkg.generated_at).toLocaleString('en-IN')}`,
    `Recommendation: ${pkg.recommendation}`,
    '',
  ]
  for (const s of pkg.sections) {
    lines.push(s.title.toUpperCase(), '-'.repeat(s.title.length))
    if (s.kind === 'fields') {
      for (const [k, v] of s.body as string[][]) lines.push(`${k}: ${v}`)
    } else {
      for (const line of s.body as string[]) lines.push(s.kind === 'list' ? `- ${line}` : line)
    }
    lines.push('')
  }
  lines.push(pkg.disclaimer)
  return lines.join('\n')
}

export function EvidencePackageButton() {
  const { open } = usePackage()
  return (
    <button type="button" className="btn-primary" onClick={open}>
      Generate evidence package
    </button>
  )
}

export function PackageProvider({ disputeId, children }: { disputeId: string; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [pkg, setPkg] = useState<EvidencePackage | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const toast = useToast()

  const generate = async () => {
    setOpen(true)
    setLoading(true)
    setError(null)
    setPkg(null)
    try {
      const result = await api.post<EvidencePackage>(`/api/disputes/${disputeId}/evidence-package`, {
        include_gaps: true,
      })
      setPkg(result)
      toast(`Evidence package generated · ${result.sections.length} sections`, 'positive')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Package generation failed.')
    } finally {
      setLoading(false)
    }
  }

  const download = () => {
    if (!pkg) return
    const blob = new Blob([toPlainText(pkg)], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `evidence-package-${pkg.dispute_id}.txt`
    a.click()
    URL.revokeObjectURL(url)
    toast('Evidence package downloaded', 'accent')
  }

  return (
    <Ctx.Provider value={{ open: () => setOpen(true) }}>
      {children}
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        wide
        title={pkg ? pkg.document_title : `Evidence package — ${disputeId}`}
        subtitle={
          pkg
            ? `${pkg.sections.length} sections · ${pkg.evidence_count} evidence records · generated ${new Date(
                pkg.generated_at,
              ).toLocaleString('en-IN')}`
            : 'Assembling the case record'
        }
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setOpen(false)}>
              Close
            </button>
            <button type="button" className="btn-secondary" onClick={generate} disabled={loading}>
              Regenerate
            </button>
            <button type="button" className="btn-primary" onClick={download} disabled={!pkg}>
              Download
            </button>
          </>
        }
      >
        {loading && (
          <p className="flex items-center gap-2 py-8 text-sm text-ink-3">
            <Spinner /> Assembling case summary, evidence, timeline and assessment…
          </p>
        )}
        {error && <ErrorBlock message={error} onRetry={generate} />}
        {pkg && (
          <article className="space-y-6">
            <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
              <div>
                <p className="text-sm font-semibold text-ink">{pkg.merchant.name}</p>
                <p className="num text-xs text-ink-3">{pkg.merchant.merchant_id}</p>
              </div>
              <Pill tone={pkg.recommendation === 'CONTEST' ? 'positive' : pkg.recommendation === 'ACCEPT' ? 'caution' : 'info'}>
                Recommendation: {pkg.recommendation.replace('_', ' ')}
              </Pill>
            </header>
            {pkg.sections.map((s) => (
              <section key={s.title}>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-label text-ink-2">{s.title}</h3>
                <SectionBody section={s} />
              </section>
            ))}
            <p className="border-t border-line pt-4 text-2xs text-ink-3">{pkg.disclaimer}</p>
          </article>
        )}
      </Modal>
    </Ctx.Provider>
  )
}
