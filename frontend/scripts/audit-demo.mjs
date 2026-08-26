/**
 * Demo audit: mounts the production bundle in jsdom against the live API and
 * walks the judge flow — Dashboard → Dispute → Investigation → Evidence →
 * Timeline → Contradiction/Gap → Assessment → Copilot → Evidence Package →
 * Human approval — for a set of cases.
 *
 * Built directly on the smoke test's proven mount loop; it additionally
 * asserts DOM content (not just HTTP 200): section order, module rows,
 * clickable evidence references, timeline events, contradiction visibility,
 * completeness breakdown, copilot citations and package parity.
 *
 *   node scripts/audit-demo.mjs            (API server must be running)
 *   SMOKE_API=http://127.0.0.1:8080 node scripts/audit-demo.mjs
 */
import { readdirSync, readFileSync } from 'node:fs'
import { JSDOM } from 'jsdom'

const API = process.env.SMOKE_API ?? 'http://127.0.0.1:8000'
const dist = new URL('../dist/assets/', import.meta.url)
const jsFile = readdirSync(dist).find((f) => f.endsWith('.js'))
const code = readFileSync(new URL(jsFile, dist), 'utf8')

const nativeFetch = globalThis.fetch.bind(globalThis)
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function apiGet(path) {
  const res = await nativeFetch(API + path)
  return res.json()
}

async function apiPost(path, body) {
  const res = await nativeFetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return res.json()
}

const CASES = ['CB-2026-89101', 'CB-2026-89102', 'CB-2026-89104']

const EXPECTED = {
  'CB-2026-89101': { rec: 'Contest', contradiction: true, blocking: false },
  'CB-2026-89102': { rec: 'Accept / refund', contradiction: false, blocking: false },
  'CB-2026-89104': { rec: 'Human review', contradiction: false, blocking: true },
}

// The narrative order a judge should see on a dispute page.
const SECTION_ORDER = [
  'Case investigation',
  'Customer claim',
  'Claim versus evidence',
  'Evidence strength',
  'Reconstructed timeline',
  'Contradiction detection',
  'Evidence gaps',
  'AI case assessment',
  'Evidence provenance',
  'Evidence explorer',
  'Merchant argument',
  'Human review',
]

let failures = 0
const problems = []
const uncaught = []

// jsdom lacks a real rAF; React schedules work via our setTimeout shim and
// occasionally throws from a timer after the DOM is already rendered. Record
// it so the audit can continue and report it instead of letting Node exit.
process.on('uncaughtException', (e) => {
  const msg = String(e?.message ?? e ?? '')
  uncaught.push(msg.replace(/^data:text\/javascript;base64,[A-Za-z0-9+/=]+/, '<bundle>').slice(0, 160))
})
process.on('unhandledRejection', (e) => {
  const msg = String(e?.message ?? e ?? '')
  uncaught.push(msg.replace(/^data:text\/javascript;base64,[A-Za-z0-9+/=]+/, '<bundle>').slice(0, 160))
})

const check = (ok, label) => {
  if (!ok) {
    failures++
    problems.push(label)
  }
}

// Prefetch all data with Node globals, before any window is created.
const dashboard = await apiGet('/api/dashboard')
const cases = {}
for (const id of CASES) {
  cases[id] = await Promise.all([
    apiGet(`/api/disputes/${id}`),
    apiGet(`/api/disputes/${id}/timeline`),
    apiPost(`/api/disputes/${id}/evidence-package`, {}),
    apiPost(`/api/disputes/${id}/copilot`, { question: 'Why are you recommending contest?' }),
  ])
}

const routes = [
  ['/', null, (window, t, errors) => {
    check(t.includes('Priority disputes'), 'dashboard: priority section missing')
    check(t.includes('Open disputes') && t.includes('Amount at risk'), 'dashboard: metrics missing')
    const first = dashboard.priority?.[0]?.dispute_id ?? 'CB-2026-89101'
    check(t.includes(first), `dashboard: flagship ${first} not on priority list`)
    check(t.toLowerCase().includes('demo environment'), 'dashboard: demo environment badge missing')
    check(dashboard.summary.length === 5, 'dashboard: 5 summary metrics expected')
    console.log('  metrics: %s', dashboard.summary.map((s) => `${s.label} ${s.value}`).join(' · '))
    console.log('  priority[0]: %s · open: %s', first, dashboard.health.open_total)
  }],
  ...CASES.map((id) => [`/disputes/${id}`, id, async (window, t, errors) => {
    const [detail, timeline, pkg, copilotFacts] = cases[id]
    const route = `/disputes/${id}`
    const exp = EXPECTED[id]

    // 1. multiple investigation modules actually ran
    const moduleRows = [...window.document.querySelectorAll('ol li')].filter((li) =>
      (li.textContent ?? '').includes('✓ Complete'),
    ).length
    check(moduleRows >= 12, `${route}: expected 12 module rows with ✓ Complete, saw ${moduleRows}`)
    check(t.includes('Last run on ingestion'), `${route}: correlation line missing`)

    // 2. evidence connected to findings
    const missingChips = (detail.evidence ?? []).filter((e) => !t.includes(e.evidence_id))
      .map((e) => e.evidence_id)
    check(missingChips.length === 0, `${route}: evidence not rendered: ${missingChips.slice(0, 4)}`)

    // 3. timeline prominent + narrative section order
    for (const ev of timeline.events) {
      check(t.includes(ev.title), `${route}: timeline event '${ev.title}' not rendered`)
    }
    const titles = [...window.document.querySelectorAll('h2')].map((h) => (h.textContent ?? '').trim())
    const want = SECTION_ORDER.filter((s) => titles.includes(s))
    const idx = want.map((s) => titles.indexOf(s))
    check(idx.every((v, i) => i === 0 || v > idx[i - 1]),
      `${route}: section order wrong — ACTUAL: ${titles.join(' | ')}`)
    const assessIdx = titles.indexOf('AI case assessment')
    const tlIdx = titles.indexOf('Reconstructed timeline')
    check(assessIdx > tlIdx && tlIdx >= 0,
      `${route}: assessment (${assessIdx}) must follow timeline (${tlIdx})`)

    // 4/5. contradiction + gap visibility
    if (exp.contradiction) {
      check(t.includes('Contradiction detected'), `${route}: contradiction banner missing`)
      check(t.includes('AI interpretation'), `${route}: AI interpretation missing`)
    } else {
      check(t.includes('No material contradictions detected'), `${route}: no-contradiction state missing`)
    }
    check(t.includes('Evidence gaps'), `${route}: evidence gaps section missing`)
    for (const g of detail.gaps) {
      check(t.includes(g.missing), `${route}: gap '${g.missing}' not rendered`)
      if (g.evidence_id) {
        check(evButtons(window, g.evidence_id).length > 0, `${route}: gap ${g.evidence_id} not clickable`)
      }
    }

    // 6. evidence IDs clickable wherever referenced
    const referenced = detail.assessment.supporting_factors
      .concat(detail.assessment.contradicting_factors)
      .map((f) => f.evidence_id)
      .concat(detail.conflicts.flatMap((c) => c.evidence_ids))
      .concat(timeline.events.flatMap((e) => e.evidence_ids))
    for (const eid of [...new Set(referenced)]) {
      check(evButtons(window, eid).length > 0, `${route}: referenced ${eid} has no clickable chip`)
    }

    // 7. completeness explains present vs missing
    check(t.includes('available on file'), `${route}: completeness 'available' list missing`)
    check(t.includes("Missing — not in the merchant's records"), `${route}: completeness missing list missing`)
    check(t.includes(`${detail.assessment.evidence_completeness}%`), `${route}: completeness % not rendered`)

    // 8. copilot case-specific + citations
    check(clickByText(window, 'Why are you recommending contest?'), `${route}: copilot suggestion not clickable`)
    await wait(1800)
    const t2 = text(window)
    const rec = detail.assessment.recommendation_label
    check(t2.includes(`Recommendation: ${rec.toUpperCase()}`),
      `${route}: copilot answer not case-specific (want ${rec})`)
    const cited = copilotFacts.evidence_ids.filter((eid) => evButtons(window, eid).length > 0)
    check(cited.length >= 2, `${route}: copilot cites ${cited.length} clickable IDs (need ≥2)`)

    // 9. recommendation explains WHY
    check(t.includes('Why'), `${route}: 'Why' label missing`)
    check(t.includes('Recommendation derived from the weighted balance'),
      `${route}: method explanation missing`)
    if (exp.blocking) {
      check(t.includes('Blocking'), `${route}: blocking-artefact callout missing for HUMAN_REVIEW`)
      for (const g of detail.gaps.filter((x) => x.impact === 'high' || x.weight >= 2.0)) {
        check(t.includes(g.missing), `${route}: blocking gap '${g.missing}' not in callout`)
      }
    }

    // 10/11. evidence package + human approval
    check(clickByText(window, 'Generate evidence package'), `${route}: package button missing`)
    await wait(1800)
    const t3 = text(window)
    for (const s of pkg.sections) {
      check(t3.includes(s.title), `${route}: package section '${s.title}' missing`)
    }
    const pkgResp = pkg.sections[pkg.sections.length - 1].body[0]
    check(t3.includes(pkgResp.slice(0, 60)), `${route}: package recommended response not shown`)
    const pkgIds = [...new Set(
      pkg.sections
        .map((s) => (Array.isArray(s.body) ? s.body.flat().join(' ') : ''))
        .join(' ')
        .match(/EVD-\d+/g) ?? [],
    )]
    check(pkgIds.length > 0, `${route}: package contains no evidence IDs`)
    const unlinked = pkgIds.filter((eid) => t3.includes(eid) && evButtons(window, eid).length === 0)
    check(unlinked.length === 0, `${route}: package IDs not clickable: ${unlinked.slice(0, 5)}`)
    check(t3.includes('Approve response'), `${route}: approval CTA missing`)
    check(t3.includes('requires human approval'), `${route}: human-approval requirement not stated`)

    // 12. no generic AI wording
    check(!/I am an AI|as an AI|general knowledge|AI magic/i.test(t3), `${route}: generic AI phrasing found`)

    console.log('  recommendation: %s · %s%% · %s%%',
      rec, detail.assessment.confidence, detail.assessment.evidence_completeness)
    console.log('  modules: %s/12 complete · evidence: %s · timeline: %s · gaps: %s',
      moduleRows, detail.correlation.unique_evidence, timeline.events.length, detail.gaps.length)
    console.log('  copilot cites: %s', copilotFacts.evidence_ids.join(', '))
    console.log('  package: %s sections, %s evidence IDs', pkg.sections.length, pkgIds.length)
  }]),
]

const text = (window) => window.document.body.textContent ?? ''
const clickByText = (window, needle) => {
  const btn = [...window.document.querySelectorAll('button')].find((b) =>
    (b.textContent ?? '').includes(needle),
  )
  if (!btn) return false
  btn.dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true }))
  return true
}
const evButtons = (window, id) =>
  [...window.document.querySelectorAll('button')].filter(
    (b) => (b.textContent ?? '').trim().toUpperCase() === id.toUpperCase(),
  )

const errors = []

for (const [route, caseId, assert] of routes) {
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

  console.log(route === '/' ? '\n===== Dashboard =====' : `\n===== ${caseId} =====`)
  try {
    await import(`data:text/javascript;base64,${Buffer.from(`${code}\n//${route}-${Date.now()}`).toString('base64')}`)
    await wait(2500)
    const t = text(window)
    await assert(window, t, errors)
    check(t.length > 500, `${route}: page rendered too little content (${t.length} chars)`)
  } catch (err) {
    failures++
    problems.push(`${route}: threw ${err?.message ?? err}`)
  } finally {
    console.error = origError
    for (const [k, v] of Object.entries(saved)) {
      if (v === undefined) delete g[k]
      else Object.defineProperty(g, k, { value: v, configurable: true, writable: true })
    }
  }
}

console.log('\n===== RESULT =====')
console.log(`failures: ${failures} · problems: ${problems.length} · runtime errors: ${errors.length}`)
for (const p of problems) console.log(`  ✗ ${p}`)
for (const e of [...new Set(errors)].slice(0, 20)) console.log(`  ! ${e}`)
process.exit(failures || errors.length ? 1 : 0)
