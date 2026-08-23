import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

/* ------------------------------------------------------------------ pills */

type Tone = 'neutral' | 'positive' | 'caution' | 'critical' | 'info' | 'accent'

const toneClass: Record<Tone, string> = {
  neutral: 'border-line-strong bg-raised text-ink-2',
  positive: 'border-positive/25 bg-positive-soft text-positive',
  caution: 'border-caution/25 bg-caution-soft text-caution',
  critical: 'border-critical/25 bg-critical-soft text-critical',
  info: 'border-info/25 bg-info-soft text-info',
  accent: 'border-accent/25 bg-accent-soft text-accent',
}

export function Pill({
  children,
  tone = 'neutral',
  dot = false,
}: {
  children: ReactNode
  tone?: Tone
  dot?: boolean
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-sm border px-1.5 py-0.5 text-2xs font-medium ${toneClass[tone]}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />}
      {children}
    </span>
  )
}

export function StatusDot({ tone }: { tone: Tone }) {
  const bg: Record<Tone, string> = {
    neutral: 'bg-ink-3',
    positive: 'bg-positive',
    caution: 'bg-caution',
    critical: 'bg-critical',
    info: 'bg-info',
    accent: 'bg-accent',
  }
  return <span className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${bg[tone]}`} aria-hidden />
}

/* --------------------------------------------------------------- sections */

export function Section({
  title,
  description,
  actions,
  children,
  id,
}: {
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  id?: string
}) {
  return (
    <section id={id} className="border-t border-line pt-7">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h2 className="section-title">{title}</h2>
          {description && <p className="mt-1.5 max-w-2xl text-sm text-ink-3">{description}</p>}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      {children}
    </section>
  )
}

/* ----------------------------------------------------------------- meters */

export function Meter({ value, tone = 'accent' }: { value: number; tone?: Tone }) {
  const bar: Record<Tone, string> = {
    neutral: 'bg-ink-3',
    positive: 'bg-positive',
    caution: 'bg-caution',
    critical: 'bg-critical',
    info: 'bg-info',
    accent: 'bg-accent',
  }
  return (
    <div className="meter" role="presentation">
      <div className={`h-full rounded-full ${bar[tone]}`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  )
}

/* ----------------------------------------------------- async state blocks */

export function LoadingBlock({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-10 text-sm text-ink-3" role="status" aria-live="polite">
      <Spinner />
      {label}…
    </div>
  )
}

export function Spinner({ className = '' }: { className?: string }) {
  return (
    <span
      className={`inline-block h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-line-strong border-t-accent ${className}`}
      aria-hidden
    />
  )
}

export function ErrorBlock({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card border-critical/30 bg-critical-soft/40 p-5" role="alert">
      <p className="text-sm font-medium text-critical">Something went wrong</p>
      <p className="mt-1 text-sm text-ink-2">{message}</p>
      {onRetry && (
        <button type="button" className="btn-secondary mt-3" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}

export function EmptyBlock({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-md border border-dashed border-line-strong px-5 py-10 text-center">
      <p className="text-sm font-medium text-ink-2">{title}</p>
      {hint && <p className="mx-auto mt-1 max-w-md text-sm text-ink-3">{hint}</p>}
    </div>
  )
}

/* ------------------------------------------------------------------ toast */

interface Toast {
  id: number
  message: string
  tone: Tone
}

const ToastContext = createContext<(message: string, tone?: Tone) => void>(() => {})

export const useToast = () => useContext(ToastContext)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const seq = useRef(0)

  const push = useCallback((message: string, tone: Tone = 'accent') => {
    const id = ++seq.current
    setToasts((t) => [...t, { id, message, tone }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200)
  }, [])

  const value = useMemo(() => push, [push])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-5 right-5 z-50 flex w-80 flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className="animate-in pointer-events-auto rounded border border-line bg-surface px-3.5 py-2.5 text-sm text-ink shadow-panel"
          >
            <div className="flex items-start gap-2">
              <StatusDot tone={t.tone} />
              <span className="pt-px">{t.message}</span>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

/* ------------------------------------------------------------------ modal */

export function Modal({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
  wide = false,
}: {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children: ReactNode
  footer?: ReactNode
  wide?: boolean
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    ref.current?.focus()
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-ink/25 p-4 sm:p-8">
      <div
        className={`animate-in card my-auto w-full ${wide ? 'max-w-4xl' : 'max-w-xl'} shadow-panel`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        ref={ref}
      >
        <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-ink">{title}</h2>
            {subtitle && <p className="mt-0.5 text-xs text-ink-3">{subtitle}</p>}
          </div>
          <button type="button" className="btn-ghost -mr-1 px-2 py-1" onClick={onClose} aria-label="Close dialog">
            ✕
          </button>
        </header>
        <div className="max-h-[65vh] overflow-y-auto px-5 py-4">{children}</div>
        {footer && <footer className="flex flex-wrap justify-end gap-2 border-t border-line px-5 py-3">{footer}</footer>}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------ mini charts */

export function BarList({
  items,
  tone = 'accent',
}: {
  items: { label: string; count: number }[]
  tone?: Tone
}) {
  const max = Math.max(1, ...items.map((i) => i.count))
  const bar: Record<Tone, string> = {
    neutral: 'bg-ink-3',
    positive: 'bg-positive',
    caution: 'bg-caution',
    critical: 'bg-critical',
    info: 'bg-info',
    accent: 'bg-accent',
  }
  if (!items.length) return <EmptyBlock title="No data in this period" />
  return (
    <ul className="space-y-2.5">
      {items.map((i) => (
        <li key={i.label} className="grid grid-cols-[minmax(9rem,14rem)_1fr_2.5rem] items-center gap-3 text-sm">
          <span className="truncate text-ink-2">{i.label}</span>
          <span className="h-2 rounded-sm bg-line/70">
            <span
              className={`block h-full rounded-sm ${bar[tone]}`}
              style={{ width: `${(i.count / max) * 100}%` }}
            />
          </span>
          <span className="num text-right text-ink-2">{i.count}</span>
        </li>
      ))}
    </ul>
  )
}

export function ColumnChart({ items }: { items: { label: string; count: number }[] }) {
  const max = Math.max(1, ...items.map((i) => i.count))
  return (
    <div className="flex items-end gap-1.5 overflow-x-auto pb-1" style={{ height: 132 }}>
      {items.map((i) => (
        <div key={i.label} className="flex min-w-[2.25rem] flex-1 flex-col items-center justify-end gap-2">
          <span className="num text-2xs text-ink-3">{i.count}</span>
          <div
            className="w-full rounded-sm bg-accent/80"
            style={{ height: `${Math.max(4, (i.count / max) * 92)}px` }}
            title={`${i.label}: ${i.count}`}
          />
          <span className="text-2xs text-ink-3">{i.label}</span>
        </div>
      ))}
    </div>
  )
}
