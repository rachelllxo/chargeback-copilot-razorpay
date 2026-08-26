# Chargeback Copilot

**Evidence-backed chargeback investigation & dispute intelligence.**

A merchant-side dispute investigation workspace. When a chargeback arrives, the information needed to
answer it is scattered across payments, orders, fulfilment, delivery, refunds, customer conversations and
prior disputes. Chargeback Copilot retrieves those records, correlates them, reconstructs what actually
happened, flags contradictions and missing artefacts, and produces an explainable recommendation plus a
submission-ready evidence package — with a human making the final call.

> **Demo environment · synthetic data.** This prototype is not connected to any real payment processor,
> acquirer or card network. No evidence is fabricated and no financial action is irreversible.

---

## The workflow

```
CASE → RETRIEVE → INVESTIGATE → CORRELATE → RECONSTRUCT → DETECT
     → ASSESS → EXPLAIN → RECOMMEND → GENERATE → HUMAN APPROVAL
```

## Running it

One command — builds the app and serves it, API included, on a single port:

```bash
./run.sh                 # → http://localhost:8080
PORT=3000 ./run.sh       # or pick your own port
```

<details>
<summary>Manual setup, or two-process development with hot reload</summary>


```bash
# backend  (http://localhost:8000)
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend && ../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# frontend (http://localhost:5173)
cd frontend && npm install && npm run dev
```

</details>

Interactive API docs are served at `/docs` on whichever port the API is running.

## Deploying

The production image is a **single service**: the SPA is built and served by the FastAPI app, so there is
one port, one process and no CORS to configure.

```bash
docker build -t chargeback-copilot .
docker run -p 8080:8080 -v cc-data:/data chargeback-copilot   # → http://localhost:8080
```

Ready-made configs are committed for the common platforms — all of them build the same `Dockerfile`:

| Platform | Command | Config |
| --- | --- | --- |
| Render | New → Blueprint, point at this repo (free plan) | `render.yaml` |
| Fly.io | `fly launch --copy-config --now` | `fly.toml` |
| Railway / Heroku | detected automatically | `Procfile` |
| Any container host | `docker build . && docker run -p 8080:8080` | `Dockerfile` |

**Environment variables** (all optional):

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8080` | Listen port |
| `STATIC_DIR` | `frontend/dist` | Built SPA to serve; unset it to run API-only |
| `CHARGEBACK_COPILOT_DB` | `backend/copilot.db` | SQLite decision store — put it on a mounted volume to persist approvals |
| `DATABASE_URL` | — | Set a `postgres://…` URL to report PostgreSQL as the decision store |
| `ALLOWED_ORIGINS` | `*` | Comma-separated origins, for split frontend/backend deploys |

There are no secrets to configure: the app holds no keys and talks to no third-party service.
Approvals recorded in the demo live in SQLite, so mount `/data` if you want them to survive a restart.

Running without Docker (single service):

```bash
cd frontend && npm ci && npm run build && cd ..
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8080
```

## Architecture

```
backend/app/
  data.py        Synthetic dataset: 14 cases, each with its own evidence relationships
  engine.py      Investigation orchestrator + 12 functional modules, correlation,
                 timeline reconstruction, contradiction detection, gap analysis, scoring
  ai_service.py  AIService abstraction: investigate / correlate / assess / explain /
                 package / copilot. Deterministic; degrades gracefully with no LLM
  store.py       SQLite (PostgreSQL when DATABASE_URL is set) for operator decisions
  main.py        FastAPI routes

frontend/src/
  pages/         Dashboard, Disputes, DisputeDetail, Investigations, Evidence,
                 Analytics, Policies, Settings
  components/    AppShell, EvidenceDrawer (provenance), Copilot, EvidencePackage, ui
  lib/           API client with loading/error/empty handling, types, formatters
```

### Investigation modules

`Transaction · Order · Fulfillment · Delivery · Customer interaction · Refund · Historical · Policy`
followed by `Evidence Correlation · Timeline Reconstruction · Contradiction Detection · Risk Assessment`.

Every conclusion the UI shows is traceable: each module returns the evidence IDs it used,
each conflict carries an auditable interpretation with cited records, and each evidence
record links back to the modules and timeline events that used it.

Each module returns a structured finding:

```json
{
  "finding": "Order marked delivered.",
  "evidence_ids": ["EVD-1042"],
  "relevance": "high",
  "supports": "merchant"
}
```

### How the numbers are derived

Nothing is hard-coded per case. Every evidence record carries a relevance (high/medium/low) and an
availability (available/partial/unavailable) that produce a weight, plus an impact direction
(merchant / cardholder / contextual).

- **Evidence completeness** = available weight ÷ (available weight + weight of identified gaps)
- **Net direction** = (merchant weight − cardholder weight) ÷ total directional weight
- **Recommendation** — `CONTEST` above +0.35, `ACCEPT` below −0.35, otherwise `HUMAN_REVIEW`;
  a missing mandatory artefact or completeness under 62% always forces `HUMAN_REVIEW`
- **Confidence** = 0.60 × |net direction| + 0.40 × completeness − gap penalty (a different formula
  expresses confidence that human judgement is required for `HUMAN_REVIEW` cases)

The flagship case CB-2026-89101 therefore computes to **CONTEST · 94% confidence · 91% completeness**
from its evidence alone. Change the evidence and the recommendation changes with it.

### Contradiction detection

Contradictions are only raised from the records themselves, never invented:

1. **Claim versus recorded event** — the cardholder denies an event that high-relevance merchant
   evidence proves occurred (non-receipt against an OTP-verified delivery, for example).
2. **Conflicting internal records** — an explicit contradiction edge between two evidence records
   (ordered SKU versus the SKU the warehouse actually scanned).
3. **Record mismatch** — an inconsistency inside a single record (delivery scanned at flat 903 for an
   order addressed to apartment 902).

Where no contradiction exists the case says so: *No material contradictions detected.*

## The demo cases

| Case | Scenario | Computed outcome |
| --- | --- | --- |
| CB-2026-89101 | Non-receipt, delivered, customer then reports damage | Contest · 94% · contradiction |
| CB-2026-89102 | Booked installation never performed | Accept / refund |
| CB-2026-89103 | Ordered SKU ≠ dispatched SKU | Human review · internal conflict |
| CB-2026-89104 | Tracking stops at the hub, no POD | Human review · blocking gap |
| CB-2026-89105 | Card-absent fraud, AVS mismatch, new device | Accept / refund |
| CB-2026-89106 | Merchant cancelled, refund failed and never retried | Accept / refund |
| CB-2026-89107 | Partial return, ₹4,600 already credited | Contest on reconciliation |
| CB-2026-89108 | Non-receipt against OTP + signed POD + 5★ rating | Contest · 96% |
| CB-2026-89109 | "Charged twice" — one settled capture, one void | Contest |
| CB-2026-89110 | Cancellation tap, app crash, renewal billed | Human review |
| CB-2026-89111 | High-value parcel signed for at the wrong flat | Human review |
| CB-2026-89112 | Configured sofa, signed delivery acceptance | Contest · no contradictions |
| CB-2026-89094 / 89088 | Closed cases retained for analytics | Won / Accepted |

## API

| Method | Endpoint |
| --- | --- |
| GET | `/api/dashboard` |
| GET | `/api/disputes` (search + status, reason, recommendation, amount, completeness, deadline filters) |
| GET | `/api/disputes/{id}` |
| GET | `/api/disputes/{id}/timeline` |
| GET | `/api/disputes/{id}/evidence` |
| POST | `/api/disputes/{id}/investigate` |
| GET | `/api/disputes/{id}/assessment` |
| POST | `/api/disputes/{id}/evidence-package` |
| POST | `/api/disputes/{id}/copilot` |
| POST | `/api/disputes/{id}/decision` |
| GET | `/api/analytics` · `/api/policies` · `/api/settings` · `/api/meta` · `/health` |

## Copilot

The copilot is contextual to the open case and answers strictly from its investigation state — the
assessment, evidence records, conflicts, gaps, timeline, deadline and applicable policy. Anything outside
that returns *"That evidence is not available in this case."* It cites evidence IDs, and every citation is
clickable through to the underlying record.

## Verification

```bash
.venv/bin/python -m pytest backend/tests -q   # 24 API + engine tests
cd frontend && npm run build                  # type-check + production build
cd frontend && npm run smoke                  # renders every route in jsdom against the API
```

The backend suite asserts the things that matter: that assessments are derived from evidence weights
rather than hard-coded, that a missing mandatory artefact forces human review, that contradictions appear
only where records disagree, that the copilot refuses questions it cannot evidence, and that no secret-like
key is ever present in an API response. `npm run smoke` needs both servers running and checks that all
nine routes render real content with no runtime errors.

A ready-to-use GitHub Actions pipeline lives at `ci/github-actions-ci.yml` — it runs the backend suite,
the type-check and build, then builds the production Docker image and curls the running container.
Enable it with:

```bash
mkdir -p .github/workflows && cp ci/github-actions-ci.yml .github/workflows/ci.yml
git add .github && git commit -m "Enable CI" && git push
```

(It ships outside `.github/` because the agent token that created this branch is not permitted to add
workflow files to the repository.)

## Notes on data & safety

- Policy knowledge is kept visually and structurally distinct from case evidence; a policy never
  evidences that an event occurred.
- Recommendations are advisory. Approve / edit / escalate is recorded against the case and no submission
  or refund is executed.
- No API keys, secrets or environment values are returned by the API or rendered in the client.
