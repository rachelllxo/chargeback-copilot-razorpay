/**
 * Interaction QA: mounts the production bundle and clicks every actionable
 * control in the dispute workspace, asserting real DOM state changes —
 * not just that the button exists.
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

const route = '/disputes/CB-2026-89101'
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
window.addEventListener('error', (e) => problems.push(`runtime: ${e.message}`))

const g = globalThis
const saved = {}
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'Element', 'Node', 'Event',
  'CustomEvent', 'MutationObserver', 'getComputedStyle', 'requestAnimationFrame', 'location', 'history',
  'localStorage', 'fetch', 'DocumentFragment', 'Text', 'SVGElement', 'matchMedia', 'scrollTo']) {
  saved[k] = g[k]
  if (window[k] !== undefined) Object.defineProperty(g, k, { value: window[k], configurable: true, writable: true })
}
const origError = console.error
console.error = (...a) => { const m = String(a[0] ?? ''); if (!m.includes('not wrapped in act')) problems.push(`console: ${m.slice(0, 160)}`) }

await import(`data:text/javascript;base64,${Buffer.from(`${code}\n//interaction`).toString('base64')}`)
await wait(2500)

const $q = (sel) => [...window.document.querySelectorAll(sel)]
const byText = (needle, tag = 'button') => $q(tag).find((b) => (b.textContent ?? '').includes(needle))
const click = (el) => { el.dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true })) }
const txt = () => window.document.body.textContent ?? ''
const evBtns = (id) => $q('button').filter((b) => (b.textContent ?? '').trim().toUpperCase() === id.toUpperCase())

/* 1. evidence chip opens the drawer */
const chip = evBtns('EVD-1042')[0]
check(Boolean(chip), 'EVD-1042 chip missing')
click(chip)
await wait(300)
check(txt().includes('Delivery record') && txt().includes('Used by AI in'), 'evidence drawer did not open with EVD-1042')
check(txt().includes('Timeline reconstruction') || txt().includes('Delivery Investigation'), "drawer missing used-by modules")
const drawerClose = byText('✕')
click(drawerClose)
await wait(200)

/* 2. timeline event expands */
const dlBtn = $q('button').find((b) => (b.textContent ?? '').includes('Order delivered'))
check(Boolean(dlBtn), 'timeline event Order delivered missing')
click(dlBtn)
await wait(300)
check(txt().includes('Order marked delivered.'), 'timeline event did not expand to evidence')
click(dlBtn)
await wait(200)

/* 3. re-run investigation */
const invBtn = byText('Investigate case')
check(Boolean(invBtn), 'Investigate case button missing')
click(invBtn)
await wait(400)
check(txt().includes('Investigating case'), 'investigation running state missing')
await wait(3500)
check(txt().includes('Re-run investigation'), 'investigation did not complete')
check(txt().includes('Completed'), 'completion timestamp missing')

/* 4. Request human review (assessment card) */
const reviewBtn = $q('button').filter((b) => (b.textContent ?? '').includes('Request human review'))[0]
check(Boolean(reviewBtn), 'Request human review button missing')
click(reviewBtn)
await wait(800)
check(txt().includes('Escalated for senior human review'), 'review toast/feedback missing')

/* 5. Approve response records decision */
const approveBtn = byText('Approve response')
check(Boolean(approveBtn), 'Approve response button missing')
click(approveBtn)
await wait(900)
check(txt().includes('Response approved'), 'approve feedback missing')
check(txt().includes('Decision log'), 'decision log missing after approval')

/* 6. Edit response modal opens with prefilled text */
const editBtn = byText('Edit response')
check(Boolean(editBtn), 'Edit response button missing')
click(editBtn)
await wait(300)
const ta = $q('textarea')[0]
check(Boolean(ta), 'edit modal textarea missing')
check((ta?.value ?? '').length > 80, 'edit modal not prefilled with merchant argument')
click(byText('Cancel'))
await wait(200)

/* 7. copilot free-text ask (not just suggestion) */
const input = window.document.getElementById('copilot-input')
check(Boolean(input), 'copilot input missing')
const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
setter.call(input, "What evidence is missing?")
input.dispatchEvent(new window.Event('input', { bubbles: true }))
await wait(100)
const askBtn = byText('Ask')
check(Boolean(askBtn), 'copilot Ask button missing')
click(askBtn)
await wait(1500)
check(txt().includes('evidence gap(s) identified'), 'copilot free-text answer missing')
check(evBtns('EVD-1049').length > 0, 'copilot answer EVD-1049 chip missing')
check(txt().includes('[record: EVD-1049]') || txt().includes('EVD-1049'), 'copilot answer lacks gap citation')

/* 8. package generates (already covered, quick re-check) */
const pkgBtn = byText('Generate evidence package')
click(pkgBtn)
await wait(1800)
const t3 = txt()
check(t3.includes('1. Case summary') && t3.includes('15. Recommended response'),
  'package did not render 15 sections after click')
check(byText('Download') !== undefined, 'package Download button missing')

console.log('INTERACTION QA RESULT')
console.log(`failures: ${failures} · problems: ${problems.length}`)
for (const p of problems) console.log(`  ✗ ${p}`)

console.error = origError
for (const [k, v] of Object.entries(saved)) {
  if (v === undefined) delete g[k]
  else Object.defineProperty(g, k, { value: v, configurable: true, writable: true })
}
process.exit(failures ? 1 : 0)
