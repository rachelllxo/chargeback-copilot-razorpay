import { AppShell } from '../components/AppShell'
import { BarList, ColumnChart, ErrorBlock, LoadingBlock, Section } from '../components/ui'
import { useApi } from '../lib/api'
import type { Analytics as AnalyticsData } from '../lib/types'

export default function Analytics() {
  const { data, loading, error, reload } = useApi<AnalyticsData>('/api/analytics')

  return (
    <AppShell
      title="Analytics"
      subtitle="Dispute volume, investigation quality and outcomes across the portfolio."
    >
      {loading && <LoadingBlock label="Loading analytics" />}
      {error && <ErrorBlock message={error} onRetry={reload} />}

      {data && (
        <div className="space-y-9">
          <div className="grid grid-cols-2 gap-x-8 gap-y-6 border-b border-line pb-7 md:grid-cols-4 xl:grid-cols-7">
            {data.metrics.map((m) => (
              <div key={m.label}>
                <p className="label">{m.label}</p>
                <p className="num mt-1.5 text-xl font-semibold tracking-tight text-ink">{m.value}</p>
                <p className="mt-1 text-2xs text-ink-3">{m.sub}</p>
              </div>
            ))}
          </div>

          <Section title="Disputes over time" description="By date the chargeback was raised.">
            <ColumnChart items={data.volume.map((v) => ({ label: v.label, count: v.count }))} />
          </Section>

          <div className="grid gap-9 lg:grid-cols-2">
            <Section title="Disputes by reason">
              <BarList items={data.by_reason} />
            </Section>
            <Section title="Recommendation distribution" description="Open cases only.">
              <BarList
                items={data.by_recommendation.map((r) => ({
                  label:
                    r.label === 'HUMAN_REVIEW'
                      ? 'Human review'
                      : r.label === 'CONTEST'
                        ? 'Contest'
                        : 'Accept / refund',
                  count: r.count,
                }))}
                tone="info"
              />
            </Section>
          </div>

          <div className="grid gap-9 lg:grid-cols-2">
            <Section title="Outcome distribution" description="Closed cases in the reporting window.">
              <BarList items={data.outcomes} tone="positive" />
            </Section>
            <Section title="Evidence completeness" description="Open cases grouped by completeness band.">
              <BarList items={data.completeness} tone="caution" />
            </Section>
          </div>

          <p className="border-t border-line pt-5 text-2xs text-ink-3">
            Figures are computed from the synthetic demo dataset. Investigation time is measured from evidence
            retrieval to assessment.
          </p>
        </div>
      )}
    </AppShell>
  )
}
