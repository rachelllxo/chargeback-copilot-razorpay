import { useEffect, useState } from 'react'
import { AppShell } from '../components/AppShell'
import { ErrorBlock, LoadingBlock, Pill, Section, useToast } from '../components/ui'
import { useApi } from '../lib/api'

interface Toggle {
  key: string
  label: string
  enabled?: boolean
  value?: string
  detail?: string
}

interface SettingsData {
  organization: Record<string, string>
  notifications: Toggle[]
  investigation: Toggle[]
  ai: Toggle[]
  data: Toggle[]
}

function Row({
  item,
  onToggle,
}: {
  item: Toggle
  onToggle?: (key: string, next: boolean) => void
}) {
  return (
    <div className="flex items-start justify-between gap-6 border-b border-line/70 py-3">
      <div>
        <p className="text-sm text-ink">{item.label}</p>
        {item.detail && <p className="mt-0.5 text-xs text-ink-3">{item.detail}</p>}
      </div>
      {typeof item.enabled === 'boolean' && onToggle ? (
        <button
          type="button"
          role="switch"
          aria-checked={item.enabled}
          aria-label={item.label}
          onClick={() => onToggle(item.key, !item.enabled)}
          className={`relative h-5 w-9 shrink-0 rounded-full border transition-colors ${
            item.enabled ? 'border-accent bg-accent' : 'border-line-strong bg-raised'
          }`}
        >
          <span
            className={`absolute top-0.5 h-3.5 w-3.5 rounded-full bg-surface transition-all ${
              item.enabled ? 'left-[1.15rem]' : 'left-0.5'
            }`}
          />
        </button>
      ) : (
        <span className="shrink-0 text-sm text-ink-2">{item.value}</span>
      )}
    </div>
  )
}

export default function Settings() {
  const { data, loading, error, reload } = useApi<SettingsData>('/api/settings')
  const [local, setLocal] = useState<SettingsData | null>(null)
  const toast = useToast()

  useEffect(() => setLocal(data), [data])

  const toggle = (group: keyof SettingsData) => (key: string, next: boolean) => {
    if (!local) return
    setLocal({
      ...local,
      [group]: (local[group] as Toggle[]).map((i) => (i.key === key ? { ...i, enabled: next } : i)),
    })
    toast('Preference updated for this session', 'accent')
  }

  return (
    <AppShell title="Settings" subtitle="Workspace, investigation and data configuration.">
      {loading && <LoadingBlock label="Loading settings" />}
      {error && <ErrorBlock message={error} onRetry={reload} />}

      {local && (
        <div className="max-w-3xl space-y-9">
          <div>
            <h2 className="section-title">Organization</h2>
            <dl className="mt-4 grid grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-3">
              {Object.entries(local.organization).map(([k, v]) => (
                <div key={k}>
                  <dt className="label">{k.replace(/_/g, ' ')}</dt>
                  <dd className="mt-1 text-sm text-ink">{v}</dd>
                </div>
              ))}
            </dl>
          </div>

          <Section title="Notification preferences">
            {local.notifications.map((i) => (
              <Row key={i.key} item={i} onToggle={toggle('notifications')} />
            ))}
          </Section>

          <Section title="Investigation preferences">
            {local.investigation.map((i) => (
              <Row key={i.key} item={i} onToggle={toggle('investigation')} />
            ))}
          </Section>

          <Section
            title="AI settings"
            description="The assessment engine is deterministic over the case records; recommendations are advisory."
          >
            {local.ai.map((i) => (
              <Row key={i.key} item={i} onToggle={toggle('ai')} />
            ))}
          </Section>

          <Section title="Data settings">
            {local.data.map((i) => (
              <Row key={i.key} item={i} />
            ))}
            <div className="mt-4 flex flex-wrap gap-2">
              <Pill tone="accent">Demo environment</Pill>
              <Pill tone="neutral">Synthetic data enabled</Pill>
            </div>
            <p className="mt-3 text-2xs leading-relaxed text-ink-3">
              This prototype is not connected to real merchant payment infrastructure. No credentials, keys or
              environment values are exposed by the application.
            </p>
          </Section>
        </div>
      )}
    </AppShell>
  )
}
