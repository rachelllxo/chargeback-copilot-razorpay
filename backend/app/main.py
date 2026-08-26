"""Chargeback Copilot API.

Demo environment — all data is synthetic. The service is not connected to any
real payment processor, acquirer or card network.
"""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import store
from .ai_service import ai_service
from .data import CASES, CASE_INDEX, CLOSED_STATUSES, MERCHANT, NOW, POLICIES
from .engine import fmt_amount, state_for

@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init_db()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Chargeback Copilot API",
    description="Evidence-backed chargeback investigation and dispute intelligence. Synthetic demo data.",
    version="1.0.0",
)
# In production the SPA is served by this same app, so no cross-origin access is
# needed. ALLOWED_ORIGINS opts specific origins in (comma separated) for split
# deployments; the default of "*" keeps local development with the Vite dev
# server working. No credentials are ever accepted cross-origin.
_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

api = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def deadline_meta(iso: str) -> dict[str, Any]:
    dt = datetime.fromisoformat(iso)
    delta = dt - NOW
    hours = delta.total_seconds() / 3600
    if hours < 0:
        bucket, label = "overdue", "Overdue"
    elif dt.date() == NOW.date():
        bucket = "today"
        label = f"Response due in {max(int(hours), 1)} hour{'s' if int(hours) != 1 else ''}"
    elif (dt.date() - NOW.date()).days == 1:
        bucket, label = "tomorrow", "Response due tomorrow"
    else:
        days = (dt.date() - NOW.date()).days
        bucket, label = "later", f"Response due in {days} days"
    return {
        "iso": iso,
        "date_label": dt.strftime("%d %b"),
        "time_label": dt.strftime("%H:%M"),
        "bucket": bucket,
        "label": label,
        "hours_remaining": round(hours, 1),
    }


def summarise(state: dict) -> dict[str, Any]:
    d = state["dispute"]
    a = state["assessment"]
    decision = store.decisions().get(d["dispute_id"])
    status = d["status"]
    if decision == "approve":
        status = "Response approved"
    elif decision == "request_review":
        status = "Escalated"
    elif decision == "accept":
        status = "Accepted"
    return {
        "dispute_id": d["dispute_id"],
        "customer_name": d["customer_name"],
        "customer_id": d["customer_id"],
        "transaction_id": d["transaction_id"],
        "order_id": d["order_id"],
        "amount": d["amount"],
        "amount_label": fmt_amount(d["amount"]),
        "reason": d["reason"],
        "reason_code": d["reason_code"],
        "network": d["network"],
        "created_at": d["created_at"],
        "created_label": datetime.fromisoformat(d["created_at"]).strftime("%d %b"),
        "deadline": deadline_meta(d["response_deadline"]),
        "status": status,
        "priority": d["priority"],
        "recommendation": a["recommendation"],
        "recommendation_label": a["recommendation_label"],
        "confidence": a["confidence"],
        "evidence_completeness": a["evidence_completeness"],
        "case_strength": a["case_strength"],
        "conflicts": len(state["conflicts"]),
        "gaps": len(state["gaps"]),
        "evidence_count": len(state["evidence"]),
        "closed": d["status"] in CLOSED_STATUSES,
        "human_decision": decision,
    }


def all_summaries() -> list[dict[str, Any]]:
    return [summarise(state_for(c["dispute"]["dispute_id"])) for c in CASES]


# ---------------------------------------------------------------------------
# endpoints
# ---------------------------------------------------------------------------

@api.get("/meta")
def meta() -> dict[str, Any]:
    return {
        "merchant": MERCHANT,
        "environment": "demo",
        "data": "synthetic",
        "ai_mode": ai_service.mode,
        "storage": store.BACKEND,
        "as_of": NOW.isoformat(),
    }


@api.get("/dashboard")
def dashboard() -> dict[str, Any]:
    rows = all_summaries()
    open_rows = [r for r in rows if not r["closed"]]
    amount_at_risk = sum(r["amount"] for r in open_rows)
    human_review = [r for r in open_rows if r["recommendation"] == "HUMAN_REVIEW"
                    or r["human_decision"] == "request_review"]
    evidence_ready = [r for r in open_rows if r["evidence_completeness"] >= 85]
    upcoming = sorted(
        [r for r in open_rows if r["deadline"]["hours_remaining"] <= 72],
        key=lambda r: r["deadline"]["hours_remaining"],
    )
    with_conflicts = [r for r in open_rows if r["conflicts"] > 0]
    awaiting_approval = [r for r in open_rows if r["human_decision"] is None]
    avg_completeness = (
        round(sum(r["evidence_completeness"] for r in open_rows) / len(open_rows))
        if open_rows else 0
    )

    priority = sorted(
        open_rows,
        key=lambda r: (r["deadline"]["hours_remaining"], -r["amount"]),
    )[:6]

    return {
        "as_of": NOW.isoformat(),
        "summary": [
            {"key": "open", "label": "Open disputes", "value": str(len(open_rows)),
             "sub": f"{len(rows) - len(open_rows)} closed this cycle"},
            {"key": "risk", "label": "Amount at risk",
             "value": f"₹{amount_at_risk / 100000:.2f}L", "sub": fmt_amount(amount_at_risk)},
            {"key": "review", "label": "Human review", "value": str(len(human_review)),
             "sub": "Awaiting operator decision"},
            {"key": "ready", "label": "Evidence ready", "value": str(len(evidence_ready)),
             "sub": "≥85% completeness"},
            {"key": "deadlines", "label": "Upcoming deadlines", "value": str(len(upcoming)),
             "sub": "Next 72 hours"},
        ],
        "priority": priority,
        "health": {
            "investigated_this_week": store.run_count() + len(rows),
            "evidence_completeness": avg_completeness,
            "cases_with_contradictions": len(with_conflicts),
            "awaiting_approval": len(awaiting_approval),
            "open_total": len(open_rows),
            "by_recommendation": dict(Counter(r["recommendation"] for r in open_rows)),
        },
        "deadlines": [
            {**r, "group": r["deadline"]["bucket"]} for r in upcoming[:6]
        ],
    }


@api.get("/disputes")
def disputes(
    q: str | None = None,
    status: str | None = None,
    reason: str | None = None,
    recommendation: str | None = None,
    deadline: str | None = None,
    min_amount: int | None = None,
    max_amount: int | None = None,
    min_completeness: int | None = None,
) -> dict[str, Any]:
    rows = all_summaries()
    if q:
        needle = q.lower().strip()
        rows = [r for r in rows if needle in " ".join([
            r["dispute_id"], r["customer_name"], r["transaction_id"], r["order_id"],
            r["customer_id"], r["reason"],
        ]).lower()]
    if status and status != "all":
        rows = [r for r in rows if r["status"] == status]
    if reason and reason != "all":
        rows = [r for r in rows if r["reason"] == reason]
    if recommendation and recommendation != "all":
        rows = [r for r in rows if r["recommendation"] == recommendation]
    if deadline and deadline != "all":
        rows = [r for r in rows if r["deadline"]["bucket"] == deadline]
    if min_amount is not None:
        rows = [r for r in rows if r["amount"] >= min_amount]
    if max_amount is not None:
        rows = [r for r in rows if r["amount"] <= max_amount]
    if min_completeness is not None:
        rows = [r for r in rows if r["evidence_completeness"] >= min_completeness]

    everything = all_summaries()
    return {
        "results": sorted(rows, key=lambda r: r["deadline"]["hours_remaining"]),
        "total": len(everything),
        "filtered": len(rows),
        "facets": {
            "status": sorted({r["status"] for r in everything}),
            "reason": sorted({r["reason"] for r in everything}),
            "recommendation": ["CONTEST", "ACCEPT", "HUMAN_REVIEW"],
            "deadline": ["today", "tomorrow", "later", "overdue"],
        },
    }


def _require(dispute_id: str) -> dict:
    if dispute_id not in CASE_INDEX:
        raise HTTPException(status_code=404, detail=f"Dispute {dispute_id} not found")
    return state_for(dispute_id)


@api.get("/disputes/{dispute_id}")
def dispute_detail(dispute_id: str) -> dict[str, Any]:
    state = _require(dispute_id)
    return {
        "summary": summarise(state),
        "dispute": state["dispute"],
        "transaction": state["transaction"],
        "order": state["order"],
        "refunds": state["refunds"],
        "interactions": state["interactions"],
        "claim_vs_evidence": state["claim_vs_evidence"],
        "evidence_strength": state["evidence_strength"],
        "assessment": state["assessment"],
        "explanation": state["explanation"],
        "conflicts": state["conflicts"],
        "gaps": state["gaps"],
        "argument": state["argument"],
        "policies": state["policies"],
        "modules": state["modules"],
        "correlation": {k: v for k, v in state["correlation"].items() if k != "evidence"},
        "actions": store.actions_for(dispute_id),
        "copilot_suggestions": ai_service.SUGGESTIONS,
    }


@api.get("/disputes/{dispute_id}/timeline")
def timeline(dispute_id: str) -> dict[str, Any]:
    _require(dispute_id)
    events = ai_service.reconstruct_timeline(dispute_id)
    state = state_for(dispute_id)
    index = {e["evidence_id"]: e for e in state["evidence"]}
    enriched = [
        {**e, "evidence": [index[i] for i in e["evidence_ids"] if i in index]}
        for e in events
    ]
    return {"dispute_id": dispute_id, "events": enriched, "sources": sorted({e["source"] for e in events})}


@api.get("/disputes/{dispute_id}/evidence")
def evidence(dispute_id: str, category: str | None = None) -> dict[str, Any]:
    state = _require(dispute_id)
    items = state["evidence"]
    if category and category != "all":
        items = [e for e in items if e["category"] == category]
    counts = Counter(e["category"] for e in state["evidence"])
    return {
        "dispute_id": dispute_id,
        "items": items,
        "counts": {"all": len(state["evidence"]), **counts},
        "relationships": state["correlation"]["relationships"],
    }


@api.get("/disputes/{dispute_id}/assessment")
def assessment(dispute_id: str) -> dict[str, Any]:
    _require(dispute_id)
    return {
        "dispute_id": dispute_id,
        "assessment": ai_service.assess_case(dispute_id),
        "explanation": ai_service.explain_decision(dispute_id),
        "conflicts": ai_service.detect_conflicts(dispute_id),
        "gaps": ai_service.identify_missing_evidence(dispute_id),
    }


@api.post("/disputes/{dispute_id}/investigate")
def investigate(dispute_id: str) -> dict[str, Any]:
    state = _require(dispute_id)
    result = ai_service.investigate_case(dispute_id)
    store.record_run(dispute_id, len(result["modules"]), len(result["evidence"]),
                     result["assessment"]["recommendation"])
    return {
        "dispute_id": dispute_id,
        "modules": result["modules"],
        "correlation": {k: v for k, v in result["correlation"].items() if k != "evidence"},
        "assessment": result["assessment"],
        "explanation": result["explanation"],
        "conflicts": result["conflicts"],
        "gaps": result["gaps"],
        "timeline_events": len(result["timeline"]),
        "completed_at": datetime.now().isoformat(timespec="seconds"),
    }


class PackageRequest(BaseModel):
    include_gaps: bool = True


@api.post("/disputes/{dispute_id}/evidence-package")
def evidence_package(dispute_id: str, body: PackageRequest | None = None) -> dict[str, Any]:
    _require(dispute_id)
    pkg = ai_service.generate_evidence_package(dispute_id)
    if body and not body.include_gaps:
        pkg["sections"] = [s for s in pkg["sections"] if not s["title"].startswith("12.")]
    store.record_action(dispute_id, "package_generated", "Risk operations",
                        note=f"{len(pkg['sections'])} sections")
    return pkg


class CopilotRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@api.post("/disputes/{dispute_id}/copilot")
def copilot(dispute_id: str, body: CopilotRequest) -> dict[str, Any]:
    state = _require(dispute_id)
    answer = ai_service.answer_copilot(dispute_id, body.question)
    index = {e["evidence_id"]: e for e in state["evidence"]}
    answer["evidence"] = [index[i] for i in answer["evidence_ids"] if i in index]
    answer["question"] = body.question
    return answer


class DecisionRequest(BaseModel):
    action: str
    note: str | None = None
    actor: str = "Risk operations"


@api.post("/disputes/{dispute_id}/decision")
def decision(dispute_id: str, body: DecisionRequest) -> dict[str, Any]:
    _require(dispute_id)
    allowed = {"approve", "edit", "request_review", "accept"}
    if body.action not in allowed:
        raise HTTPException(status_code=400, detail=f"action must be one of {sorted(allowed)}")
    record = store.record_action(dispute_id, body.action, body.actor, body.note)
    return {"recorded": record, "actions": store.actions_for(dispute_id),
            "summary": summarise(state_for(dispute_id))}


@api.get("/analytics")
def analytics() -> dict[str, Any]:
    rows = all_summaries()
    open_rows = [r for r in rows if not r["closed"]]
    closed_rows = [r for r in rows if r["closed"]]

    by_day: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "amount": 0})
    for r in rows:
        key = datetime.fromisoformat(r["created_at"]).strftime("%d %b")
        by_day[key]["count"] += 1
        by_day[key]["amount"] += r["amount"]
    volume = [{"label": k, **v} for k, v in sorted(
        by_day.items(), key=lambda kv: datetime.strptime(kv[0], "%d %b"))]

    reasons = Counter(r["reason"] for r in rows)
    recs = Counter(r["recommendation"] for r in open_rows)
    outcomes = Counter(r["status"] for r in closed_rows)

    completeness_bands = Counter()
    for r in open_rows:
        c = r["evidence_completeness"]
        band = "90–100%" if c >= 90 else "80–89%" if c >= 80 else "70–79%" if c >= 70 else "<70%"
        completeness_bands[band] += 1

    total_amount = sum(r["amount"] for r in rows)
    contest_rate = round(100 * recs.get("CONTEST", 0) / len(open_rows)) if open_rows else 0
    review_rate = round(100 * recs.get("HUMAN_REVIEW", 0) / len(open_rows)) if open_rows else 0
    won = len([r for r in closed_rows if r["status"] == "Won"])
    outcome_rate = round(100 * won / len(closed_rows)) if closed_rows else 0

    return {
        "metrics": [
            {"label": "Dispute volume", "value": str(len(rows)), "sub": "Last 30 days"},
            {"label": "Disputed amount", "value": f"₹{total_amount / 100000:.2f}L",
             "sub": fmt_amount(total_amount)},
            {"label": "Avg. investigation time", "value": "38s",
             "sub": "Retrieval to assessment, median"},
            {"label": "Evidence completeness",
             "value": f"{round(sum(r['evidence_completeness'] for r in rows) / len(rows))}%",
             "sub": "Weighted across all cases"},
            {"label": "Contest recommendation rate", "value": f"{contest_rate}%",
             "sub": "Of open disputes"},
            {"label": "Human review rate", "value": f"{review_rate}%", "sub": "Of open disputes"},
            {"label": "Outcome rate (won)", "value": f"{outcome_rate}%",
             "sub": f"{won} of {len(closed_rows)} closed"},
        ],
        "volume": volume,
        "by_reason": [{"label": k, "count": v} for k, v in reasons.most_common()],
        "by_recommendation": [{"label": k, "count": v} for k, v in recs.most_common()],
        "outcomes": [{"label": k, "count": v} for k, v in outcomes.most_common()],
        "completeness": [{"label": k, "count": completeness_bands[k]}
                         for k in ["90–100%", "80–89%", "70–79%", "<70%"]],
    }


@api.get("/policies")
def policies(q: str | None = None) -> dict[str, Any]:
    items = POLICIES
    if q:
        needle = q.lower()
        items = [p for p in items if needle in (p["name"] + p["dispute_type"] + p["policy_id"]).lower()]
    return {"policies": items, "total": len(POLICIES),
            "note": "Policy knowledge is reference material. It never evidences that an event occurred."}


@api.get("/settings")
def settings() -> dict[str, Any]:
    return {
        "organization": {
            "name": MERCHANT["name"], "merchant_id": MERCHANT["merchant_id"],
            "category": MERCHANT["category"], "region": "India", "currency": "INR",
            "timezone": "Asia/Kolkata (IST)",
        },
        "notifications": [
            {"key": "deadline_6h", "label": "Deadline within 6 hours", "enabled": True,
             "detail": "E-mail and in-app alert to the on-duty analyst"},
            {"key": "new_dispute", "label": "New dispute received", "enabled": True,
             "detail": "In-app only"},
            {"key": "contradiction", "label": "Contradiction detected", "enabled": True,
             "detail": "E-mail to the risk lead"},
            {"key": "weekly_digest", "label": "Weekly outcome digest", "enabled": False,
             "detail": "Monday 09:00 IST"},
        ],
        "investigation": [
            {"key": "auto_investigate", "label": "Investigate on dispute receipt", "enabled": True,
             "detail": "Runs all modules as soon as a dispute is ingested"},
            {"key": "modules", "label": "Active investigation modules", "value": "12 of 12"},
            {"key": "completeness_floor", "label": "Human review below completeness",
             "value": "62%"},
            {"key": "gap_block", "label": "Block contest when a mandatory artefact is missing",
             "enabled": True, "detail": "Applies to POD on non-receipt disputes"},
        ],
        "ai": [
            {"key": "mode", "label": "Assessment engine", "value": ai_service.mode},
            {"key": "advisory", "label": "AI recommendations are advisory only", "enabled": True,
             "detail": "Every response requires human approval before submission"},
            {"key": "provenance", "label": "Require evidence citation on every conclusion",
             "enabled": True},
            {"key": "no_fabrication", "label": "Refuse answers without supporting records",
             "enabled": True, "detail": "Copilot returns “not available in this case” instead"},
        ],
        "data": [
            {"key": "environment", "label": "Environment", "value": "Demo environment"},
            {"key": "dataset", "label": "Dataset", "value": "Synthetic data enabled"},
            {"key": "storage", "label": "Decision store", "value": store.BACKEND},
            {"key": "retention", "label": "Evidence retention", "value": "24 months"},
            {"key": "processor", "label": "Payment processor connection",
             "value": "Not connected — prototype"},
        ],
    }


app.include_router(api)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": "demo", "data": "synthetic"}


# ---------------------------------------------------------------------------
# Single-service production mode: serve the built SPA from this app.
# Falls back cleanly to API-only when the frontend has not been built.
# ---------------------------------------------------------------------------

STATIC_DIR = Path(
    os.getenv("STATIC_DIR", Path(__file__).resolve().parents[2] / "frontend" / "dist")
)

if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        """Serve static files, falling back to index.html for client-side routes."""
        if full_path.startswith(("api/", "health", "docs", "openapi.json")):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (STATIC_DIR / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(STATIC_DIR.resolve()):
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
