import { NavLink, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useState } from 'react'

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/disputes', label: 'Disputes' },
  { to: '/investigations', label: 'Investigations' },
  { to: '/evidence', label: 'Evidence' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/policies', label: 'Policies' },
  { to: '/settings', label: 'Settings' },
]

function Wordmark() {
  return (
    <div className="flex items-center gap-2.5">
      <span
        aria-hidden
        className="grid h-7 w-7 shrink-0 place-items-center rounded-[5px] border border-accent/30 bg-accent text-[0.7rem] font-semibold tracking-tight text-white"
      >
        CC
      </span>
      <span className="leading-tight">
        <span className="block text-[0.9375rem] font-semibold tracking-tight text-ink">Chargeback Copilot</span>
        <span className="block text-2xs text-ink-3">Dispute intelligence</span>
      </span>
    </div>
  )
}

export function AppShell({
  children,
  title,
  subtitle,
  actions,
  breadcrumb,
}: {
  children: ReactNode
  title: string
  subtitle?: string
  actions?: ReactNode
  breadcrumb?: ReactNode
}) {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()

  const nav = (
    <nav aria-label="Primary" className="flex-1 space-y-0.5 px-3">
      {NAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={() => setOpen(false)}
          className={({ isActive }) =>
            `block rounded px-2.5 py-1.5 text-sm transition-colors ${
              isActive || (!item.end && pathname.startsWith(item.to))
                ? 'bg-raised font-medium text-ink'
                : 'text-ink-2 hover:bg-raised/60 hover:text-ink'
            }`
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  )

  return (
    <div className="flex min-h-screen bg-canvas">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2 focus:text-sm"
      >
        Skip to content
      </a>

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-60 flex-col border-r border-line bg-surface transition-transform duration-200 lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="px-4 py-5">
          <Wordmark />
        </div>
        {nav}
        <div className="m-3 rounded border border-line bg-raised/60 px-3 py-2.5">
          <p className="label">Demo environment</p>
          <p className="mt-1 text-xs text-ink-2">Synthetic data</p>
          <p className="mt-1.5 text-2xs leading-relaxed text-ink-3">
            Not connected to a live payment processor or card network.
          </p>
        </div>
      </aside>

      {open && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-20 bg-ink/20 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col lg:pl-60">
        <header className="sticky top-0 z-10 border-b border-line bg-canvas/95 backdrop-blur-[2px]">
          <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-4 gap-y-2 px-5 py-4 xl:px-10">
            <button
              type="button"
              className="btn-secondary px-2 py-1 lg:hidden"
              onClick={() => setOpen((o) => !o)}
              aria-label="Toggle navigation"
            >
              ☰
            </button>
            <div className="min-w-0 flex-1">
              {breadcrumb && <div className="mb-1 text-2xs text-ink-3">{breadcrumb}</div>}
              <h1 className="truncate text-lg font-semibold tracking-tight text-ink">{title}</h1>
              {subtitle && <p className="mt-0.5 text-sm text-ink-3">{subtitle}</p>}
            </div>
            {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-[1400px] flex-1 px-5 py-8 xl:px-10">
          {children}
        </main>
        <footer className="mx-auto w-full max-w-[1400px] px-5 pb-8 text-2xs text-ink-3 xl:px-10">
          Chargeback Copilot · Demo environment · Synthetic data · AI assessments are advisory and require
          human approval.
        </footer>
      </div>
    </div>
  )
}
