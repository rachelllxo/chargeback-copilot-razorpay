import type { Recommendation } from './types'

export const inr = (value: number) => '₹' + value.toLocaleString('en-IN')

export const dateTime = (iso: string | null) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  })
}

export const dateOnly = (iso: string | null) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export const recommendationTone = (rec: Recommendation) =>
  rec === 'CONTEST' ? 'positive' : rec === 'ACCEPT' ? 'caution' : 'info'

export const impactLabel: Record<string, string> = {
  merchant: 'Supports merchant',
  customer: 'Supports cardholder',
  neutral: 'Contextual',
}

export const categoryLabel: Record<string, string> = {
  payment: 'Payment',
  order: 'Order',
  fulfillment: 'Fulfillment',
  delivery: 'Delivery',
  refund: 'Refund',
  customer: 'Customer',
  communication: 'Communication',
  historical: 'Historical',
  policy: 'Policy',
}

export const titleCase = (value: string) =>
  value.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
