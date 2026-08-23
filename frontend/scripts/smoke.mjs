/**
 * Headless smoke test: mounts the production bundle in jsdom against the live
 * API and asserts that each route renders real content without runtime errors.
 *
 *   node scripts/smoke.mjs            (requires the dev/API servers to be up)
 */
import { readdirSync, readFileSync } from 'node:fs'
import { JSDOM } from 'jsdom'

const API = process.env.SMOKE_API ?? 'http://127.0.0.1:8000'
const dist = new URL('../dist/assets/', import.meta.url)
const jsFile = readdirSync(dist).find((f) => f.endsWith('.js'))
const code = readFileSync(new URL(jsFile, dist), 'utf8')

const nativeFetch = globalThis.fetch.bind(globalThis)

const routes = [
  ['/', ['Priority disputes', 'Amount at risk', 'CB-2026-89101']],
  ['/disputes', ['Dispute ID', 'Recommendation', 'CB-2026-89108']],
  ['/disputes/CB-2026-89101', ['Customer claim', 'AI assessment', 'Contest', '94%', '91%', 'Copilot',
    'Reconstructed timeline', 'Potential contradiction', 'Evidence gaps', 'Human review']],
  ['/disputes/CB-2026-89112', ['No material contradictions detected']],
  ['/investigations', ['Awaiting human approval', 'Pipeline']],
  ['/evidence', ['Evidence ID', 'Availability']],
  ['/analytics', ['Dispute volume', 'Disputes by reason']],
  ['/policies', ['Policy knowledge', 'PL-013']],
  ['/settings', ['Organization', 'Synthetic data enabled']],
]

const errors = []
let failures = 0

for (const [route, expectations] of routes) {
  const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', {
    url: `http://localhost:5173${route}`,
    pretendToBeVisual: true,
  })
  const { window } = dom
  window.fetch = (input, init) =>
    nativeFetch(typeof input === 'string' && input.startsWith('/') ? API + input : input, init)
  window.requestAnimationFrame = (cb) => setTimeout(() => cb(Date.now()), 0)
  window.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} })
  window.scrollTo = () => {}
  window.addEventListener('error', (e) => errors.push(`${route}: ${e.message}`))

  const g = globalThis
  const saved = {}
  for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'Element', 'Node', 'Event',
    'CustomEvent', 'MutationObserver', 'getComputedStyle', 'requestAnimationFrame', 'location', 'history',
    'localStorage', 'fetch', 'DocumentFragment', 'Text', 'SVGElement', 'matchMedia', 'scrollTo']) {
    saved[k] = g[k]
    if (window[k] !== undefined) {
      Object.defineProperty(g, k, { value: window[k], configurable: true, writable: true })
    }
  }

  const origError = console.error
  console.error = (...args) => {
    const msg = String(args[0] ?? '')
    if (!msg.includes('not wrapped in act')) errors.push(`${route}: console.error ${msg.slice(0, 200)}`)
  }

  try {
    const blob = new Blob([code], { type: 'text/javascript' })
    const url = URL.createObjectURL ? URL.createObjectURL(blob) : null
    // Execute the bundle as a module in this realm.
    await import(`data:text/javascript;base64,${Buffer.from(`${code}\n//${route}-${Date.now()}`).toString('base64')}`)
    if (url) URL.revokeObjectURL(url)
    await new Promise((r) => setTimeout(r, 2500))

    const text = window.document.body.textContent ?? ''
    const missing = expectations.filter((e) => !text.includes(e))
    if (missing.length) {
      failures++
      console.log(`✗ ${route} — missing: ${missing.join(' | ')}`)
      console.log(`  rendered ${text.length} chars: ${text.slice(0, 400).replace(/\s+/g, ' ')}`)
    } else {
      console.log(`✓ ${route} — ${text.length} chars rendered`)
    }
  } catch (err) {
    failures++
    console.log(`✗ ${route} — threw ${err?.message}`)
  } finally {
    console.error = origError
    for (const [k, v] of Object.entries(saved)) {
      if (v === undefined) delete g[k]
      else Object.defineProperty(g, k, { value: v, configurable: true, writable: true })
    }
    window.close()
  }
}

if (errors.length) {
  console.log('\nRuntime errors:')
  for (const e of [...new Set(errors)].slice(0, 20)) console.log('  ' + e)
}
console.log(failures ? `\n${failures} route(s) failed` : '\nAll routes rendered')
process.exit(failures || errors.length ? 1 : 0)
