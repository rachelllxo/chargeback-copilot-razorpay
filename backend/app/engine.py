"""
Investigation engine.

The orchestrator runs a set of functional investigation modules over the case
records, correlates the evidence they return, reconstructs a timeline, detects
conflicts, identifies gaps and synthesises an assessment.

Every number the UI shows is computed here from the underlying evidence — no
score is hard-coded per case, and no evidence is invented.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .data import CASE_INDEX, CASES, POLICIES, RELEVANCE_WEIGHT

# Reasons where the cardholder denies that a recorded event happened at all.
# For these, high-relevance merchant evidence proving the event is a direct
# contradiction of the claim.
EVENT_DENIAL_REASONS = {
    "Product not received": ("delivery",),
    "Services not rendered": ("fulfillment",),
    "Duplicate processing": ("payment",),
}

MATERIAL_CATEGORIES = {
    "Product not received": ["delivery", "fulfillment", "customer", "communication"],
    "Services not rendered": ["fulfillment", "communication", "refund"],
    "Product not as described": ["order", "fulfillment", "delivery"],
    "Unauthorized transaction": ["payment", "customer", "delivery"],
    "Credit not processed": ["refund", "order", "communication"],
    "Partial refund not received": ["refund", "fulfillment", "payment"],
    "Duplicate processing": ["payment", "order"],
    "Cancelled recurring transaction": ["order", "customer", "payment"],
}

AVAILABILITY_FACTOR = {"available": 1.0, "partial": 0.6, "unavailable": 0.0}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def weight(e: dict[str, Any]) -> float:
    return RELEVANCE_WEIGHT.get(e["relevance"], 1.0) * AVAILABILITY_FACTOR.get(e["availability"], 1.0)


def by_category(evidence: list[dict], *cats: str) -> list[dict]:
    return [e for e in evidence if e["category"] in cats]


def available(evidence: list[dict]) -> list[dict]:
    return [e for e in evidence if e["availability"] != "unavailable"]


def ids(items: list[dict]) -> list[str]:
    return [e["evidence_id"] for e in items]


def strength_label(score: float) -> str:
    if score >= 3.0:
        return "Strong"
    if score >= 2.0:
        return "Moderate"
    if score > 0:
        return "Limited"
    return "None"


def fmt_amount(value: float | int) -> str:
    return "₹" + f"{int(value):,}"


def parse(ts: str | None) -> datetime | None:
    return datetime.fromisoformat(ts) if ts else None


# ---------------------------------------------------------------------------
# Investigation modules
# ---------------------------------------------------------------------------

def _module(key: str, label: str, finding: str, evidence: list[dict], relevance: str,
            supports: str, detail: list[str] | None = None) -> dict[str, Any]:
    return {
        "module": key,
        "label": label,
        "finding": finding,
        "evidence_ids": ids(evidence),
        "relevance": relevance,
        "supports": supports,
        "detail": detail or [],
        "status": "complete",
    }


def transaction_investigation(case: dict) -> dict:
    txn = case["transaction"]
    e = by_category(case["evidence"], "payment")
    captured = txn["status"] == "captured"
    finding = (
        f"Payment of {fmt_amount(txn['amount'])} was {txn['status']} on "
        f"{parse(txn['timestamp']).strftime('%d %b %Y at %H:%M')} via {txn['payment_method']}."
    )
    detail = [f"Authentication: {txn['three_ds']}"]
    if txn.get("avs_match") is not None:
        detail.append("AVS: " + ("match" if txn["avs_match"] else "mismatch"))
    if txn.get("cvv_match") is not None:
        detail.append("CVV: " + ("match" if txn["cvv_match"] else "mismatch"))
    supports = "merchant" if captured and txn.get("avs_match") is not False else "customer"
    return _module("transaction", "Transaction Investigation", finding, e, "high", supports, detail)


def order_investigation(case: dict) -> dict:
    order = case["order"]
    e = by_category(case["evidence"], "order")
    finding = (
        f"Order {order['order_id']} for “{order['product']}” was created on "
        f"{parse(order['order_timestamp']).strftime('%d %b %Y at %H:%M')} with fulfilment status "
        f"“{order['fulfillment_status'].replace('_', ' ')}”."
    )
    supports = "merchant" if order["fulfillment_status"] in {"fulfilled", "active_service"} else "customer"
    detail = [f"Ship to: {order['shipping_address']}"]
    return _module("order", "Order Investigation", finding, e, "medium", supports, detail)


def fulfillment_investigation(case: dict) -> dict:
    order = case["order"]
    e = by_category(case["evidence"], "fulfillment")
    if not e:
        finding = "No fulfilment activity is recorded against this order."
        return _module("fulfillment", "Fulfillment Investigation", finding, e, "high", "customer")
    finding = e[0]["finding"]
    if len(e) > 1:
        finding = " ".join(x["finding"] for x in e[:2])
    supports = _dominant(e)
    detail = [f"{x['evidence_id']} · {x['description']}" for x in e]
    return _module("fulfillment", "Fulfillment Investigation", finding, e, "high", supports, detail)


def delivery_investigation(case: dict) -> dict:
    order = case["order"]
    e = by_category(case["evidence"], "delivery")
    status = order["delivery_status"]
    if status == "delivered":
        finding = (
            f"Courier records show the consignment delivered on "
            f"{parse(order['delivery_timestamp']).strftime('%d %b %Y at %H:%M')}"
            + (f" via {order['courier']} (AWB {order['awb']})." if order.get("awb") else ".")
        )
    elif status == "in_transit":
        finding = "The consignment was dispatched but no delivery scan exists; tracking stops in transit."
    else:
        finding = "Delivery is not applicable to this dispute — no physical consignment was owed."
    supports = _dominant(e) if e else "neutral"
    detail = [f"{x['evidence_id']} · {x['finding']}" for x in e]
    return _module("delivery", "Delivery Investigation", finding, e, "high", supports, detail)


def customer_investigation(case: dict) -> dict:
    e = by_category(case["evidence"], "customer", "communication")
    interactions = case["interactions"]
    if interactions:
        finding = (
            f"{len(interactions)} customer interaction(s) are recorded between order placement and the "
            f"dispute; the most recent is a {interactions[-1]['channel'].lower()} contact categorised as "
            f"“{interactions[-1]['category'].replace('_', ' ')}”."
        )
    else:
        finding = "No customer interactions are recorded for this order before the dispute was raised."
    supports = _dominant(e) if e else "neutral"
    detail = [f"{parse(i['timestamp']).strftime('%d %b, %H:%M')} · {i['channel']} · {i['message']}"
              for i in interactions]
    return _module("customer", "Customer Interaction Analysis", finding, e, "medium", supports, detail)


def historical_investigation(case: dict) -> dict:
    e = by_category(case["evidence"], "historical")
    finding = e[0]["finding"] if e else "No historical dispute record was retrieved for this customer."
    supports = _dominant(e) if e else "neutral"
    return _module("historical", "Historical Case Analysis", finding, e, "low", supports,
                   [f"{x['evidence_id']} · {x['description']}" for x in e])


def refund_investigation(case: dict) -> dict:
    e = by_category(case["evidence"], "refund")
    refunds = case["refunds"]
    total = sum(r["amount"] for r in refunds if r["status"] == "processed")
    if total:
        finding = (
            f"{fmt_amount(total)} has already been credited against this transaction "
            f"({len(refunds)} refund record(s))."
        )
    else:
        finding = "No refund or credit has been issued against this transaction."
    supports = _dominant(e) if e else "neutral"
    return _module("refund", "Refund Investigation", finding, e, "medium", supports,
                   [f"{r['refund_id']} · {fmt_amount(r['amount'])} · {r['status']} · {r['reason']}"
                    for r in refunds])


def policy_analysis(case: dict) -> dict:
    e = by_category(case["evidence"], "policy")
    reason = case["dispute"]["reason"]
    matched = [p for p in POLICIES if p["dispute_type"] == reason]
    finding = (
        f"{len(matched)} policy record(s) apply to a “{reason}” dispute; they define which artefacts a "
        f"representment must contain."
        if matched else "No specific policy record matches this dispute type; general handling applies."
    )
    return _module("policy", "Policy Analysis", finding, e, "medium", "neutral",
                   [f"{p['policy_id']} · {p['name']}" for p in matched])


def _dominant(evidence: list[dict]) -> str:
    m = sum(weight(e) for e in evidence if e["impact"] == "merchant")
    c = sum(weight(e) for e in evidence if e["impact"] == "customer")
    if m > c:
        return "merchant"
    if c > m:
        return "customer"
    return "neutral"


MODULE_RUNNERS = [
    transaction_investigation,
    order_investigation,
    fulfillment_investigation,
    delivery_investigation,
    customer_investigation,
    refund_investigation,
    historical_investigation,
    policy_analysis,
]


# ---------------------------------------------------------------------------
# Correlation, timeline, conflicts, gaps, assessment
# ---------------------------------------------------------------------------

def correlate_evidence(case: dict, modules: list[dict]) -> dict:
    """Deduplicate evidence across modules, link it to events and rank relevance."""
    evidence = case["evidence"]
    seen: dict[str, dict] = {}
    for e in evidence:
        seen.setdefault(e["evidence_id"], e)

    referenced: dict[str, list[str]] = {}
    for m in modules:
        for eid in m["evidence_ids"]:
            referenced.setdefault(eid, []).append(m["label"])

    event_links: dict[str, list[str]] = {}
    for ev_ in case["events"]:
        for eid in ev_["evidence_ids"]:
            event_links.setdefault(eid, []).append(ev_["title"])

    # Explicit provenance links between records: contradiction edges from the
    # dataset, shared timeline events, and records cited in the same conflict.
    related: dict[str, list[dict[str, str]]] = {}

    def relate(a: str, b: str, kind: str) -> None:
        if not a or not b or a == b:
            return
        if not any(r["evidence_id"] == b for r in related.setdefault(a, [])):
            related[a].append({"evidence_id": b, "relationship": kind})
        if not any(r["evidence_id"] == a for r in related.setdefault(b, [])):
            related[b].append({"evidence_id": a, "relationship": kind})

    for rel in _relationships(case):
        relate(rel["from"], rel["to"], rel["type"])
    for ev_ in case["events"]:
        ids_ = ev_["evidence_ids"]
        for a in ids_:
            for b in ids_:
                relate(a, b, "corroborates")
    for e in evidence:
        for other_id in e.get("conflicts_with", []):
            relate(e["evidence_id"], other_id, "contradicts")

    correlated = []
    for eid, e in seen.items():
        correlated.append({
            **e,
            "weight": round(weight(e), 2),
            "referenced_by": referenced.get(eid, []),
            "linked_events": event_links.get(eid, []),
            "related": related.get(eid, []),
        })
    correlated.sort(key=lambda x: (-x["weight"], x["evidence_id"]))

    duplicates = len([m for m in modules for _ in m["evidence_ids"]]) - len(seen)
    categories = sorted({e["category"] for e in evidence})
    return {
        "evidence": correlated,
        "unique_evidence": len(seen),
        "module_references": sum(len(m["evidence_ids"]) for m in modules),
        "deduplicated": max(duplicates, 0),
        "categories_covered": categories,
        "relationships": _relationships(case),
    }


def _relationships(case: dict) -> list[dict]:
    rels: list[dict] = []
    for e in case["evidence"]:
        for other in e.get("conflicts_with", []):
            rels.append({"from": e["evidence_id"], "to": other, "type": "contradicts"})
    for ev_ in case["events"]:
        if len(ev_["evidence_ids"]) > 1:
            first, *rest = ev_["evidence_ids"]
            for r in rest:
                rels.append({"from": first, "to": r, "type": "corroborates"})
    return rels


def reconstruct_timeline(case: dict) -> list[dict]:
    events = sorted(
        case["events"],
        key=lambda e: (e["date"], e["time"] or "00:00"),
    )
    out = []
    for e in events:
        dt = datetime.fromisoformat(f"{e['date']}T{(e['time'] or '00:00')}:00")
        out.append({
            **e,
            "date_label": dt.strftime("%d %b").upper(),
            "time_label": dt.strftime("%I:%M %p").lstrip("0") if e["time"] else "",
            "iso": dt.isoformat(),
        })
    return out


def _conflict_confidence(severity: str) -> int:
    return {"high": 88, "medium": 72, "low": 55}[severity]


def _cite(e: dict) -> str:
    """One auditable sentence for a record, used inside conflict interpretations."""
    when = ""
    if e.get("timestamp"):
        when = f" on {datetime.fromisoformat(e['timestamp']).strftime('%d %b %Y at %H:%M')}"
    return f"the {e['source']} record {e['evidence_id']}{when} shows “{e['finding']}”"


def _interpret_claim(dispute: dict, proving: list[dict], corroborating: list[dict]) -> str:
    cited_records = proving[:2] + corroborating[:1]
    cited = " while ".join(_cite(e) for e in cited_records)
    cited = cited[0].upper() + cited[1:]
    if len(cited_records) > 1:
        source_note = (
            "These records come from independent systems and are consistent with each other, but not "
            "with the claim as filed"
        )
    else:
        source_note = "This record is consistent with the rest of the case file, but not with the claim as filed"
    return (
        f"The available evidence conflicts with the stated claim. {cited}. {source_note} — so "
        "the cardholder's version of events is not supported by the case record."
    )


def detect_conflicts(case: dict) -> list[dict]:
    """Conflicts come only from the records: claim-vs-proven-event, explicit
    contradiction edges between evidence, and record-level mismatches."""
    dispute = case["dispute"]
    reason = dispute["reason"]
    evidence = {e["evidence_id"]: e for e in case["evidence"]}
    conflicts: list[dict] = []

    # 1. The cardholder denies an event the records show happened.
    cats = EVENT_DENIAL_REASONS.get(reason)
    if cats:
        proving = [e for e in case["evidence"]
                   if e["category"] in cats and e["impact"] == "merchant"
                   and e["relevance"] == "high" and e["availability"] == "available"]
        if proving:
            corroborating = sorted(
                [e for e in case["evidence"]
                 if e["category"] in {"customer", "communication"}
                 and e["impact"] == "merchant" and e["availability"] == "available"],
                key=lambda e: -weight(e),
            )
            lines = [{"label": "Customer claim", "value": dispute["claim"], "evidence_id": None}]
            for e in proving:
                lines.append({"label": e["evidence_type"], "value": e["finding"],
                              "evidence_id": e["evidence_id"]})
            for e in corroborating[:2]:
                lines.append({"label": e["evidence_type"], "value": e["finding"],
                              "evidence_id": e["evidence_id"]})
            severity = "high" if len(proving) + len(corroborating) >= 2 else "medium"
            conflicts.append({
                "conflict_id": f"CFL-{dispute['dispute_id'][-3:]}-1",
                "type": "Claim versus recorded event",
                "severity": severity,
                "confidence": _conflict_confidence(severity),
                "relevance": severity,
                "claim": dispute["claim"],
                "summary": "Potential contradiction detected.",
                "interpretation": _interpret_claim(dispute, proving, corroborating),
                "lines": lines,
                "why_it_matters": (
                    "The evidence indicates the disputed event did occur, which is inconsistent with the "
                    "cardholder's current claim."
                ),
                "evidence_ids": ids(proving + corroborating[:2]),
            })

    # 2. Explicit contradiction edges recorded between two pieces of evidence.
    for e in case["evidence"]:
        for other_id in e.get("conflicts_with", []):
            other = evidence.get(other_id)
            if not other:
                continue
            severity = e.get("conflict_severity", "high")
            conflicts.append({
                "conflict_id": f"CFL-{dispute['dispute_id'][-3:]}-{len(conflicts) + 1}",
                "type": "Conflicting internal records",
                "severity": severity,
                "confidence": _conflict_confidence(severity),
                "relevance": severity,
                "claim": dispute["claim"],
                "summary": e.get("conflict_summary", "Two records of this case disagree."),
                "interpretation": (
                    f"Two merchant records disagree on a material fact: {_cite(other)} while "
                    f"{_cite(e)}. At least one of these records is unreliable, so the response must "
                    "not be built on either record alone."
                ),
                "lines": [
                    {"label": other["evidence_type"], "value": other["finding"],
                     "evidence_id": other["evidence_id"]},
                    {"label": e["evidence_type"], "value": e["finding"], "evidence_id": e["evidence_id"]},
                ],
                "why_it_matters": e.get(
                    "conflict_why",
                    "The merchant's own systems disagree on a material fact, which weakens any "
                    "representment built on either record alone.",
                ),
                "evidence_ids": [other["evidence_id"], e["evidence_id"]],
            })

    # 3. Mismatches inside a single record.
    for e in case["evidence"]:
        mm = e.get("mismatch")
        if mm:
            severity = mm.get("severity", "medium")
            conflicts.append({
                "conflict_id": f"CFL-{dispute['dispute_id'][-3:]}-{len(conflicts) + 1}",
                "type": "Record mismatch",
                "severity": severity,
                "confidence": _conflict_confidence(severity),
                "relevance": severity,
                "claim": dispute["claim"],
                "summary": mm["summary"],
                "interpretation": (
                    f"A single record carries an internal inconsistency: {_cite(e)}. The record needs "
                    "verification before it is relied on."
                ),
                "lines": [{"label": e["evidence_type"], "value": e["finding"],
                           "evidence_id": e["evidence_id"]}],
                "why_it_matters": mm["why"],
                "evidence_ids": [e["evidence_id"]],
            })

    return conflicts


def identify_missing_evidence(case: dict) -> list[dict]:
    """Gaps are the authored missing-artefact list, enriched with the specific
    record that documents the absence when one exists (e.g. an unavailable
    'Signed delivery confirmation' record backs the 'Signed delivery
    confirmation' gap), so every gap is traceable to a record ID."""
    gaps = [dict(g) for g in case["gaps"]]
    for e in case["evidence"]:
        if e["availability"] == "available":
            continue
        matched = None
        for g in gaps:
            if _same_artefact(g["missing"], e["evidence_type"]) or _same_artefact(
                g["missing"], e["description"]
            ):
                matched = g
                break
        if matched is not None:
            if not matched.get("evidence_id"):
                matched["evidence_id"] = e["evidence_id"]
            continue
        # A record that is completely unavailable and has no authored gap yet.
        if e["availability"] == "unavailable":
            gaps.append({
                "missing": e["evidence_type"],
                "why_it_matters": e["finding"],
                "weight": RELEVANCE_WEIGHT[e["relevance"]] * 0.5,
                "availability": "Not available",
                "evidence_id": e["evidence_id"],
            })
    for g in gaps:
        g["impact"] = "high" if g["weight"] >= 2.0 else "medium" if g["weight"] >= 1.2 else "low"
    gaps.sort(key=lambda g: (-g["weight"], g["missing"]))
    return gaps


_GAP_STOPWORDS = {"a", "an", "and", "at", "for", "from", "in", "is", "of", "on", "or", "the", "to", "with"}


def _is_word(ch: str) -> bool:
    return ch.isalnum() or ch.isspace()


def _gap_words(text: str) -> set[str]:
    cleaned = "".join(ch if _is_word(ch) else " " for ch in text.lower())
    return {w for w in cleaned.split() if w and w not in _GAP_STOPWORDS}


def _same_artefact(a: str, b: str) -> bool:
    """Conservative match between a missing-artefact name and an evidence type:
    all non-stop words of the shorter name must appear in the longer one."""
    wa, wb = _gap_words(a), _gap_words(b)
    if not wa or not wb:
        return a.lower() in b.lower() or b.lower() in a.lower()
    shorter, longer = (wa, wb) if len(wa) <= len(wb) else (wb, wa)
    return shorter <= longer


def evidence_strength(case: dict) -> list[dict]:
    out = []
    labels = {
        "payment": "Transaction", "order": "Order", "fulfillment": "Fulfillment",
        "delivery": "Delivery", "refund": "Refund", "customer": "Customer activity",
        "communication": "Customer communication", "historical": "Historical evidence",
        "policy": "Policy coverage",
    }
    for cat, label in labels.items():
        items = by_category(case["evidence"], cat)
        if not items:
            continue
        score = sum(weight(e) for e in items)
        out.append({
            "category": cat,
            "label": label,
            "score": round(score, 2),
            "strength": strength_label(score),
            "evidence_ids": ids(items),
            "unavailable": ids([e for e in items if e["availability"] == "unavailable"]),
        })
    return out


def assess_case(case: dict, conflicts: list[dict], gaps: list[dict]) -> dict:
    evidence = case["evidence"]
    merchant = sum(weight(e) for e in evidence if e["impact"] == "merchant")
    customer = sum(weight(e) for e in evidence if e["impact"] == "customer")
    directional = merchant + customer
    net = (merchant - customer) / directional if directional else 0.0

    avail_weight = sum(weight(e) for e in evidence)
    gap_weight = sum(g["weight"] for g in gaps)
    completeness = avail_weight / (avail_weight + gap_weight) if (avail_weight + gap_weight) else 0.0

    blocking_gap = any(g["weight"] >= 2.5 for g in gaps)

    if blocking_gap or completeness < 0.62:
        recommendation = "HUMAN_REVIEW"
    elif net >= 0.35:
        recommendation = "CONTEST"
    elif net <= -0.35:
        recommendation = "ACCEPT"
    else:
        recommendation = "HUMAN_REVIEW"

    if recommendation == "HUMAN_REVIEW":
        confidence = min(0.90, max(0.50, 0.50 + 0.30 * (1 - abs(net)) + 0.10 * (1 - completeness)))
    else:
        confidence = min(0.96, max(0.35, 0.60 * abs(net) + 0.40 * completeness - 0.01 * gap_weight))

    if abs(net) >= 0.75 and completeness >= 0.80:
        strength = "Strong"
    elif abs(net) >= 0.45 and completeness >= 0.70:
        strength = "Moderate"
    elif abs(net) >= 0.25:
        strength = "Contested"
    else:
        strength = "Limited"

    supporting = sorted(
        [e for e in evidence if e["impact"] == "merchant" and e["availability"] != "unavailable"],
        key=lambda e: -weight(e),
    )
    contradicting = sorted(
        [e for e in evidence if e["impact"] == "customer" and e["availability"] != "unavailable"],
        key=lambda e: -weight(e),
    )

    # What actually makes up the headline completeness figure: the record types
    # that are on file (deduplicated, strongest first) and the ones that are not.
    available_pts = sorted(
        [e for e in evidence if e["availability"] != "unavailable"],
        key=lambda e: -weight(e),
    )
    seen_types: dict[str, dict] = {}
    for e in available_pts:
        seen_types.setdefault(e["evidence_type"], {
            "name": e["evidence_type"], "evidence_id": e["evidence_id"], "source": e["source"],
        })
    completeness_detail = {
        "score": round(completeness * 100),
        "available": list(seen_types.values()),
        "missing": [
            {"name": g["missing"], "evidence_id": g.get("evidence_id"),
             "availability": g["availability"]} for g in gaps
        ],
    }

    return {
        "recommendation": recommendation,
        "recommendation_label": {
            "CONTEST": "Contest", "ACCEPT": "Accept / refund", "HUMAN_REVIEW": "Human review",
        }[recommendation],
        "confidence": round(confidence * 100),
        "evidence_completeness": round(completeness * 100),
        "completeness_detail": completeness_detail,
        "case_strength": strength,
        "merchant_weight": round(merchant, 2),
        "customer_weight": round(customer, 2),
        "net_direction": round(net, 3),
        "supporting_factors": [
            {"text": e["finding"], "evidence_id": e["evidence_id"], "relevance": e["relevance"]}
            for e in supporting[:6]
        ],
        "contradicting_factors": [
            {"text": e["finding"], "evidence_id": e["evidence_id"], "relevance": e["relevance"]}
            for e in contradicting[:5]
        ],
        "conflict_count": len(conflicts),
        "gap_count": len(gaps),
        "blocking_gap": blocking_gap,
    }


def explain_decision(case: dict, assessment: dict, conflicts: list[dict], gaps: list[dict]) -> dict:
    rec = assessment["recommendation"]
    dispute = case["dispute"]
    if rec == "CONTEST":
        headline = (
            f"The records establish the facts the cardholder disputes, so a representment is supported "
            f"for {fmt_amount(dispute['amount'])}."
        )
    elif rec == "ACCEPT":
        headline = (
            "The records corroborate the cardholder rather than the merchant; accepting avoids "
            "representment cost and a likely loss at pre-arbitration."
        )
    else:
        headline = (
            "The evidence does not point clearly in either direction, so an operator decision is required "
            "before responding."
        )
    drivers = []
    for f in assessment["supporting_factors"][:3]:
        drivers.append({"direction": "supports", **f})
    for f in assessment["contradicting_factors"][:3]:
        drivers.append({"direction": "weakens", **f})
    return {
        "headline": headline,
        "drivers": drivers,
        "conflicts_considered": [c["conflict_id"] for c in conflicts],
        "gaps_considered": [g["missing"] for g in gaps],
        "method": (
            "Recommendation derived from the weighted balance of available evidence "
            f"(merchant {assessment['merchant_weight']} vs cardholder {assessment['customer_weight']}), "
            f"evidence completeness {assessment['evidence_completeness']}% and "
            f"{assessment['conflict_count']} detected conflict(s). Advisory only — a human decides."
        ),
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def investigate_case(dispute_id: str) -> dict:
    case = CASE_INDEX[dispute_id]
    modules = [runner(case) for runner in MODULE_RUNNERS]
    correlation = correlate_evidence(case, modules)
    timeline = reconstruct_timeline(case)
    conflicts = detect_conflicts(case)
    gaps = identify_missing_evidence(case)
    assessment = assess_case(case, conflicts, gaps)
    explanation = explain_decision(case, assessment, conflicts, gaps)

    # Link every record that participates in a detected contradiction to the
    # other records in the same conflict, so each record can be traced to its
    # analytical context even when no explicit edge exists in the dataset.
    index = {e["evidence_id"]: e for e in correlation["evidence"]}
    for c in conflicts:
        for a in c["evidence_ids"]:
            for b in c["evidence_ids"]:
                if a != b and b in index:
                    rec = index[a]
                    if not any(r["evidence_id"] == b for r in rec["related"]):
                        rec["related"].append({"evidence_id": b, "relationship": "contradiction"})

    modules = modules + [
        _module("correlation", "Evidence Correlation",
                f"{correlation['unique_evidence']} unique evidence records correlated from "
                f"{correlation['module_references']} module references across "
                f"{len(correlation['categories_covered'])} sources.", [], "high", "neutral"),
        _module("timeline", "Timeline Reconstruction",
                f"{len(timeline)} events sequenced from "
                f"{len({e['source'] for e in timeline})} systems.", [], "high", "neutral"),
        _module("conflict", "Contradiction Detection",
                (f"{len(conflicts)} potential contradiction(s) detected."
                 if conflicts else "No material contradictions detected."), [], "high",
                "merchant" if conflicts and assessment["recommendation"] == "CONTEST" else "neutral"),
        _module("risk", "Risk Assessment",
                f"Recommendation {assessment['recommendation_label']} at {assessment['confidence']}% "
                f"confidence with {assessment['evidence_completeness']}% evidence completeness.",
                [], "high", "neutral"),
    ]

    # Flag timeline events that carry records implicated in a detected
    # contradiction, so the narrative can point at them without hiding the rest.
    conflict_ids = {eid for c in conflicts for eid in c["evidence_ids"]}
    for t in timeline:
        t["conflicting"] = bool(set(t["evidence_ids"]) & conflict_ids)

    return {
        "dispute": case["dispute"],
        "transaction": case["transaction"],
        "order": case["order"],
        "refunds": case["refunds"],
        "interactions": case["interactions"],
        "modules": modules,
        "correlation": correlation,
        "evidence": correlation["evidence"],
        "timeline": timeline,
        "conflicts": conflicts,
        "gaps": gaps,
        "assessment": assessment,
        "explanation": explanation,
        "evidence_strength": evidence_strength(case),
        "claim_vs_evidence": [
            {"aspect": a, "record": r, "evidence_id": eid} for a, r, eid in case["claim_vs_evidence"]
        ],
        "argument": case["argument"],
        "policies": [p for p in POLICIES if p["dispute_type"] == case["dispute"]["reason"]],
    }


def get_state(dispute_id: str) -> dict:
    return investigate_case(dispute_id)


ALL_STATES_CACHE: dict[str, dict] = {}


def state_for(dispute_id: str) -> dict:
    if dispute_id not in ALL_STATES_CACHE:
        ALL_STATES_CACHE[dispute_id] = investigate_case(dispute_id)
    return ALL_STATES_CACHE[dispute_id]


def all_states() -> list[dict]:
    return [state_for(c["dispute"]["dispute_id"]) for c in CASES]
