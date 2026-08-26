/**
 * State QA: verifies loading, error, empty states, filters/search and
 * stale-state when switching between disputes — using the production bundle.
 */
import { readdirSync, readFileSync } from 'node:fs'
import { JSDOM } from 'jsdom'

const API = process.env.SMOKE_API ?? 'http://127.0.0.1:8000'
const dist = new URL('../dist/assets/', import.meta.url)
const jsFile = readdirSync(dist).find((f) => f.endsWith('.js'))
const code = readFileSync(new URL(jsFile, dist), 'utf8')
const nativeFetch = globalThis.fetch.bind(globalThis)
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

let failures = 0
const problems = []
const check = (ok, label) => { if (!ok) { failures++; problems.push(label) } }

function mkWindow(route, fetchImpl) {
  const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', {
    url: `http://localhost:5173${route}`, pretendToBeVisual: true,
  })
  const { window } = dom
  window.fetch = fetchImpl ?? ((input, init) =>
    nativeFetch(typeof input === 'string' && input.startsWith('/') ? API + input : input, init))
  window.requestAnimationFrame = (cb) => setTimeout(() => cb(Date.now()), 0)
  window.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} })
  window.scrollTo = () => {}
  window.addEventListener('error', (e) => problems.push(`runtime: ${e.message}`))
  const g = globalThis, saved = {}
  for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'Element', 'Node', 'Event',
    'CustomEvent', 'MutationObserver', 'getComputedStyle', 'requestAnimationFrame', 'location', 'history',
    'localStorage', 'fetch', 'DocumentFragment', 'Text', 'SVGElement', 'matchMedia', 'scrollTo']) {
    saved[k] = g[k]
    if (window[k] !== undefined) Object.defineProperty(g, k, { value: window[k], configurable: true, writable: true })
  }
  const origError = console.error
  console.error = (...a) => { const m = String(a[0] ?? ''); if (!m.includes('not wrapped in act')) problems.push(`console: ${m.slice(0, 160)}`) }
  return { window, restore: () => { console.error = origError; for (const [k, v] of Object.entries(saved)) { if (v === undefined) delete g[k]; else Object.defineProperty(g, k, { value: v, configurable: true, writable: true }) } } }
}

async function boot(route, fetchImpl, settleMs = 2200) {
  const { window, restore } = mkWindow(route, fetchImpl)
  const errors = []
  window.addEventListener('error', (e) => errors.push(e.message))
  await import(`data:text/javascript;base64,${Buffer.from(`${code}\n//${route}-${Date.now()}`).toString('base64')}`)
  await wait(settleMs)
  return { window, restore, errors: [...errors, ...problems.slice()] }
}

/* 1. ERROR STATE: failing fetch must show ErrorBlock with retry, then recover */
{
  let failNext = true
  const impl = (input, init) => {
    if (failNext && typeof input === 'string' && input.includes('/api/disputes/CB-2026-89101')) {
      failNext = false
      return Promise.reject(new TypeError('network down'))
    }
    return nativeFetch(typeof input === 'string' && input.startsWith('/') ? API + input : input, init)
  }
  const { window, restore } = await boot('/disputes/CB-2026-89101', impl)
  const t = () => window.document.body.textContent ?? ''
  check(t().includes('Could not reach the investigation service'), 'error state: ErrorBlock missing')
  check(t().includes('Try again'), 'error state: retry button missing')
  const retry = [...window.document.querySelectorAll('button')].find((b) => (b.textContent ?? '').includes('Try again'))
  retry?.dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true }))
  await wait(2500)
  check(t().includes('Customer claim'), 'error retry did not recover the case view')
  restore()
  console.log('1. error state + retry: ok')
}

/* 2. LOADING STATE: slow response must show loading, then resolve */
{
  const orig = nativeFetch
  const impl = (input, init) => {
    const url = typeof input === 'string' && input.startsWith('/') ? API + input : input
    if (String(url).includes('/api/disputes/CB-2026-89101/timeline')) {
      return new Promise((res) => setTimeout(() => res(orig(url, init)), 4500))
    }
    return orig(url, init)
  }
  // Sample mid-load (400ms): main case rendered, timeline still pending.
  const { window, restore } = await boot('/disputes/CB-2026-89101', impl, 400)
  const t = () => window.document.body.textContent ?? ''
  check(t().includes('Reconstructing timeline'), 'loading state: timeline loading label missing')
  await wait(5200)
  check(!t().includes('Reconstructing timeline'), 'loading state: never resolved')
  check(t().includes('Order delivered'), 'timeline missing after slow load')
  restore()
  console.log('2. loading state resolves: ok')
}

/* 3. EVIDENCE PAGE: switch case -> no stale evidence from previous case */
{
  const { window, restore } = await boot('/evidence')
  const t = () => window.document.body.textContent ?? ''
  check(t().includes('EVD-1042'), 'evidence page: flagship evidence missing')
  const sel = window.document.querySelector('select')
  check(Boolean(sel), 'evidence page: case selector missing')
  const setVal = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set
  setVal.call(sel, 'CB-2026-89102')
  sel.dispatchEvent(new window.Event('change', { bubbles: true }))
  await wait(2000)
  check(!t().includes('EVD-1042'), 'evidence page: stale EVD-1042 after switching case')
  check(t().includes('EVD-2010') || t().includes('EVD-2013'), 'evidence page: new case evidence missing after switch')
  // category filter narrows
  const cats = [...window.document.querySelectorAll('select')]
  setVal.call(cats[1], 'payment')
  cats[1].dispatchEvent(new window.Event('change', { bubbles: true }))
  await wait(600)
  check(t().includes('EVD-2010'), 'evidence page: payment filter missing expected row')
  check(!t().includes('EVD-2013'), 'evidence page: filter did not narrow (fulfilment leak)')
  restore()
  console.log('3. evidence case-switch + category filter: ok')
}

/* 4. ROUTE NAVIGATION: detail -> detail must not show stale case */
{
  const { window, restore } = await boot('/disputes/CB-2026-89101')
  const t = () => window.document.body.textContent ?? ''
  check(t().includes('Aarav Sharma'), 'nav: flagship customer missing')
  window.history.pushState({}, '', '/disputes/CB-2026-89102')
  window.dispatchEvent(new window.PopStateEvent('popstate'))
  await wait(3000)
  check(t().includes('Meera Iyer'), 'nav: new case not rendered after popstate')
  check(!t().includes('Aarav Sharma'), 'nav: stale flagship customer after navigation')
  check(!t().includes('EVD-1042'), 'nav: stale flagship evidence after navigation')
  restore()
  console.log('4. in-app navigation no stale state: ok')
}

console.log('\nSTATE QA RESULT')
console.log(`failures: ${failures} · problems: ${problems.length}`)
for (const p of problems) console.log(`  ✗ ${p}`)
process.exit(failures ? 1 : 0)
