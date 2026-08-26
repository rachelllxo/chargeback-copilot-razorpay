"""API and investigation-engine tests.

These lock down the behaviour that matters: that assessments are derived from
evidence, that cases behave differently from one another, that the copilot
refuses to answer beyond the record, and that nothing sensitive is exposed.

    .venv/bin/python -m pytest backend/tests -q
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("CHARGEBACK_COPILOT_DB", str(Path(tempfile.gettempdir()) / "cc-test.db"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


# --------------------------------------------------------------- endpoints

@pytest.mark.parametrize(
    "path",
    [
        "/health",
        "/api/meta",
        "/api/dashboard",
        "/api/disputes",
        "/api/disputes/CB-2026-89101",
        "/api/disputes/CB-2026-89101/timeline",
        "/api/disputes/CB-2026-89101/evidence",
        "/api/disputes/CB-2026-89101/assessment",
        "/api/analytics",
        "/api/policies",
        "/api/settings",
    ],
)
def test_endpoints_ok(path: str) -> None:
    assert client.get(path).status_code == 200


def test_unknown_dispute_is_404() -> None:
    assert client.get("/api/disputes/CB-0000-00000").status_code == 404


# ------------------------------------------------------- derived assessment

def test_flagship_case_assessment_is_derived_from_evidence() -> None:
    a = client.get("/api/disputes/CB-2026-89101").json()["assessment"]
    assert a["recommendation"] == "CONTEST"
    assert a["confidence"] == 94
    assert a["evidence_completeness"] == 91
    assert a["case_strength"] == "Strong"
    # every cited factor points at a real evidence record
    evidence = {e["evidence_id"] for e in client.get("/api/disputes/CB-2026-89101/evidence").json()["items"]}
    for f in a["supporting_factors"] + a["contradicting_factors"]:
        assert f["evidence_id"] in evidence


def test_completeness_equals_available_over_available_plus_gaps() -> None:
    """The headline completeness figure must reconcile with the evidence weights."""
    from app.engine import RELEVANCE_WEIGHT, state_for  # noqa: PLC0415

    factor = {"available": 1.0, "partial": 0.6, "unavailable": 0.0}
    state = state_for("CB-2026-89101")
    avail = sum(
        RELEVANCE_WEIGHT[e["relevance"]] * factor[e["availability"]] for e in state["evidence"]
    )
    gaps = sum(g["weight"] for g in state["gaps"])
    assert round(100 * avail / (avail + gaps)) == state["assessment"]["evidence_completeness"]


def test_cases_reach_different_recommendations() -> None:
    rows = client.get("/api/disputes").json()["results"]
    recs = {r["recommendation"] for r in rows}
    assert {"CONTEST", "ACCEPT", "HUMAN_REVIEW"} <= recs
    # and they are not clones of one another
    assert len({(r["confidence"], r["evidence_completeness"]) for r in rows}) > 6


def test_missing_mandatory_artefact_forces_human_review() -> None:
    detail = client.get("/api/disputes/CB-2026-89104").json()
    assert detail["assessment"]["recommendation"] == "HUMAN_REVIEW"
    assert detail["assessment"]["blocking_gap"] is True
    assert any("delivery" in g["missing"].lower() for g in detail["gaps"])


# ------------------------------------------------------------- contradictions

def test_contradiction_is_raised_only_where_records_disagree() -> None:
    conflicted = client.get("/api/disputes/CB-2026-89101").json()["conflicts"]
    assert len(conflicted) == 1
    assert conflicted[0]["severity"] == "high"
    assert conflicted[0]["evidence_ids"]

    clean = client.get("/api/disputes/CB-2026-89112").json()["conflicts"]
    assert clean == []


def test_internal_record_conflict_is_detected() -> None:
    conflicts = client.get("/api/disputes/CB-2026-89103").json()["conflicts"]
    assert any(c["type"] == "Conflicting internal records" for c in conflicts)


def test_conflict_is_cited_and_interpreted() -> None:
    c = client.get("/api/disputes/CB-2026-89101").json()["conflicts"][0]
    assert c["claim"] == "I never received the product."
    assert c["confidence"] > 0
    assert "EVD-1042" in c["interpretation"]
    assert "EVD-1044" in c["interpretation"]
    assert "EVD-1042" in c["evidence_ids"] and "EVD-1044" in c["evidence_ids"]


def test_completeness_detail_explains_the_score() -> None:
    detail = client.get("/api/disputes/CB-2026-89101").json()
    cd = detail["assessment"]["completeness_detail"]
    assert cd["score"] == detail["assessment"]["evidence_completeness"] == 91
    names = {x["name"] for x in cd["available"]}
    assert "Delivery record" in names and "Payment authorisation" in names
    assert any("Signed delivery confirmation" in x["name"] for x in cd["missing"])
    # every "available" row points at a real record on the case
    evidence = {e["evidence_id"] for e in client.get("/api/disputes/CB-2026-89101/evidence").json()["items"]}
    assert all(x["evidence_id"] in evidence for x in cd["available"])


def test_timeline_flags_contradiction_events() -> None:
    events = {e["title"]: e["conflicting"] for e in
              client.get("/api/disputes/CB-2026-89101/timeline").json()["events"]}
    assert events.get("Order delivered") is True
    assert events.get("Customer contacted support") is True
    assert events.get("Payment captured") is False
    assert events.get("Chargeback initiated") is False


def test_evidence_is_linked_to_related_records() -> None:
    items = {e["evidence_id"]: e for e in
             client.get("/api/disputes/CB-2026-89101/evidence").json()["items"]}
    related = {r["evidence_id"]: r["relationship"] for r in items["EVD-1042"]["related"]}
    assert related.get("EVD-1044") == "contradiction"
    assert items["EVD-1042"]["referenced_by"]
    assert items["EVD-1042"]["linked_events"]


def test_module_labels_reflect_spec_pipeline() -> None:
    labels = [m["label"] for m in
              client.get("/api/disputes/CB-2026-89101").json()["modules"]]
    for expected in ["Customer Interaction Analysis", "Historical Case Analysis", "Evidence Correlation",
                     "Timeline Reconstruction", "Contradiction Detection", "Risk Assessment",
                     "Policy Analysis"]:
        assert expected in labels


def test_copilot_why_answer_cites_conflict_records() -> None:
    answer = client.post("/api/disputes/CB-2026-89101/copilot",
                         json={"question": "Why are you recommending contest?"}).json()
    assert "EVD-1042" in answer["evidence_ids"]
    assert any("conflicts with the stated claim" in l for l in answer["lines"])


# ---------------------------------------------------------- traceability audit

def test_gaps_link_to_the_records_that_document_them() -> None:
    """A gap must carry the evidence_id of the record that proves it is missing."""
    flagship = {g["missing"]: g for g in client.get("/api/disputes/CB-2026-89101").json()["gaps"]}
    assert flagship["Signed delivery confirmation"]["evidence_id"] == "EVD-1049"

    blocked = {g["missing"]: g for g in client.get("/api/disputes/CB-2026-89104").json()["gaps"]}
    assert blocked["Proof of delivery from the courier"]["evidence_id"] == "EVD-4012"
    assert blocked["Courier trace investigation report"]["evidence_id"] == "EVD-4013"

    # linked gaps are never duplicated as extra entries
    assert len(client.get("/api/disputes/CB-2026-89104").json()["gaps"]) == 3
    other = {g["missing"]: g for g in client.get("/api/disputes/CB-2026-89103").json()["gaps"]}
    assert other["Packing-bench photograph"]["evidence_id"] == "EVD-3013"
    assert "Dispatch imagery" not in other


def test_missing_evidence_answer_cites_the_gap_records() -> None:
    answer = client.post("/api/disputes/CB-2026-89101/copilot",
                         json={"question": "What evidence is missing?"}).json()
    assert "EVD-1049" in answer["evidence_ids"]
    assert any("Signed delivery confirmation" in l and "EVD-1049" in l for l in answer["lines"])


def test_weaken_answer_cites_gap_records() -> None:
    answer = client.post("/api/disputes/CB-2026-89101/copilot",
                         json={"question": "What could weaken this case?"}).json()
    assert "EVD-1049" in answer["evidence_ids"]


def test_response_citations_follow_the_recommendation() -> None:
    contest = client.post("/api/disputes/CB-2026-89101/copilot",
                          json={"question": "Generate my response."}).json()
    assert set(contest["evidence_ids"]) >= {"EVD-1040", "EVD-1039", "EVD-1042"}
    assert "EVD-1049" in contest["evidence_ids"]

    accept = client.post("/api/disputes/CB-2026-89102/copilot",
                         json={"question": "Generate my response."}).json()
    assert "EVD-2013" in accept["evidence_ids"]
    assert "EVD-2010" not in accept["evidence_ids"][:3] or "EVD-2013" in accept["evidence_ids"][:3]

    human = client.post("/api/disputes/CB-2026-89104/copilot",
                        json={"question": "Generate my response."}).json()
    assert "EVD-4012" in human["evidence_ids"] and "EVD-4013" in human["evidence_ids"]


def test_recommended_response_is_case_specific_not_template() -> None:
    def response(did: str) -> str:
        return client.post(f"/api/disputes/{did}/evidence-package", json={}).json()[
            "sections"][-1]["body"][0]

    assert "EVD-2013" in response("CB-2026-89102")
    assert "EVD-4012" in response("CB-2026-89104")
    assert "EVD-1049" in response("CB-2026-89101")


def test_three_cases_have_distinct_investigation_outcomes() -> None:
    """Three dispute types must produce meaningfully different, case-derived results."""
    rows = {r["dispute_id"]: r for r in client.get("/api/disputes").json()["results"]}
    a = {did: client.get(f"/api/disputes/{did}").json() for did in
         ["CB-2026-89101", "CB-2026-89102", "CB-2026-89104"]}

    recs = {did: d["assessment"]["recommendation"] for did, d in a.items()}
    assert recs == {"CB-2026-89101": "CONTEST", "CB-2026-89102": "ACCEPT",
                    "CB-2026-89104": "HUMAN_REVIEW"}

    signatures = {
        did: (d["assessment"]["confidence"], d["assessment"]["evidence_completeness"],
              len(d["conflicts"]), tuple(d["dispute"]["reason"] for _ in [0]),
              tuple(g["missing"] for g in d["gaps"]),
              tuple(m["finding"] for m in d["modules"]))
        for did, d in a.items()
    }
    assert len(set(signatures.values())) == 3

    # evidence actually differs and the copilot reads it
    ev_counts = {did: len(d["gaps"]) for did, d in a.items()}
    assert ev_counts == {"CB-2026-89101": 2, "CB-2026-89102": 2, "CB-2026-89104": 3}
    answers = {
        did: client.post(f"/api/disputes/{did}/copilot",
                         json={"question": "What is the strongest evidence?"}).json()["evidence_ids"]
        for did in a
    }
    assert all(set(v) for v in answers.values())
    assert len(set(tuple(v) for v in answers.values())) == 3

    pkg_responses = {
        did: client.post(f"/api/disputes/{did}/evidence-package", json={}).json()["sections"][-1]["body"][0]
        for did in a
    }
    assert len(set(pkg_responses.values())) == 3


def test_analytics_metrics_are_derived_not_hardcoded() -> None:
    analytics = client.get("/api/analytics").json()
    labels = {m["label"] for m in analytics["metrics"]}
    assert "Avg. investigation time" not in labels
    records = next(m for m in analytics["metrics"] if m["label"] == "Evidence records correlated")
    rows = client.get("/api/disputes").json()["results"]
    assert records["value"] == str(sum(r["evidence_count"] for r in rows))


# -------------------------------------------------------------------- copilot

def test_copilot_answers_are_grounded_in_case_evidence() -> None:
    body = {"question": "What contradicts the customer's claim?"}
    answer = client.post("/api/disputes/CB-2026-89101/copilot", json=body).json()
    assert answer["evidence_ids"]
    assert "EVD-1042" in answer["evidence_ids"]


def test_copilot_refuses_what_it_cannot_evidence() -> None:
    body = {"question": "What is the courier CEO's home address?"}
    answer = client.post("/api/disputes/CB-2026-89101/copilot", json=body).json()
    assert answer["headline"] == "That evidence is not available in this case."
    assert answer["evidence_ids"] == []


# ------------------------------------------------------- package and approval

def test_evidence_package_has_all_sections() -> None:
    pkg = client.post("/api/disputes/CB-2026-89101/evidence-package", json={}).json()
    assert len(pkg["sections"]) == 15
    assert pkg["sections"][0]["title"].startswith("1. Case summary")
    assert "synthetic" in pkg["disclaimer"].lower()


def test_human_decision_is_recorded_and_reflected() -> None:
    res = client.post(
        "/api/disputes/CB-2026-89109/decision", json={"action": "approve", "note": "settlement report attached"}
    )
    assert res.status_code == 200
    assert res.json()["summary"]["status"] == "Response approved"
    assert client.post("/api/disputes/CB-2026-89109/decision", json={"action": "delete"}).status_code == 400


# --------------------------------------------------------------------- safety

def test_no_secrets_or_env_values_are_exposed() -> None:
    blob = " ".join(
        client.get(p).text
        for p in ["/api/meta", "/api/settings", "/api/dashboard", "/api/disputes/CB-2026-89101"]
    ).lower()
    for banned in ["secret", "api_key", "apikey", "password", "token", "database_url", "authorization"]:
        assert banned not in blob


def test_search_and_filters_narrow_results() -> None:
    everything = client.get("/api/disputes").json()
    by_id = client.get("/api/disputes?q=CB-2026-89101").json()
    assert by_id["filtered"] == 1
    by_order = client.get("/api/disputes?q=ORD-728491").json()
    assert by_order["results"][0]["dispute_id"] == "CB-2026-89101"
    contested = client.get("/api/disputes?recommendation=CONTEST").json()
    assert 0 < contested["filtered"] < everything["total"]
    assert all(r["recommendation"] == "CONTEST" for r in contested["results"])
