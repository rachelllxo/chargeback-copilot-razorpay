"""
AIService — the single abstraction the API talks to.

If a live LLM is configured (CHARGEBACK_COPILOT_LLM=on plus a provider key held
outside the application), the service may enrich phrasing. It never invents
facts: every answer is assembled from the investigation state produced by the
deterministic engine, so the product works identically with no model available.

No API key, secret or environment value is ever returned to the client.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any

from . import engine
from .data import CASE_INDEX, MERCHANT
from .engine import fmt_amount

LLM_ENABLED = os.getenv("CHARGEBACK_COPILOT_LLM", "off").lower() == "on"

NOT_AVAILABLE = "That evidence is not available in this case."


class AIService:
    """Investigation intelligence. Deterministic by default."""

    mode = "deterministic (no external model configured)" if not LLM_ENABLED else "assisted"

    # -- pipeline ---------------------------------------------------------
    def investigate_case(self, dispute_id: str) -> dict:
        return engine.state_for(dispute_id)

    def correlate_evidence(self, dispute_id: str) -> dict:
        return self.investigate_case(dispute_id)["correlation"]

    def reconstruct_timeline(self, dispute_id: str) -> list[dict]:
        return self.investigate_case(dispute_id)["timeline"]

    def detect_conflicts(self, dispute_id: str) -> list[dict]:
        return self.investigate_case(dispute_id)["conflicts"]

    def identify_missing_evidence(self, dispute_id: str) -> list[dict]:
        return self.investigate_case(dispute_id)["gaps"]

    def assess_case(self, dispute_id: str) -> dict:
        return self.investigate_case(dispute_id)["assessment"]

    def explain_decision(self, dispute_id: str) -> dict:
        return self.investigate_case(dispute_id)["explanation"]

    # -- evidence package -------------------------------------------------
    def generate_evidence_package(self, dispute_id: str) -> dict:
        state = self.investigate_case(dispute_id)
        d = state["dispute"]
        txn = state["transaction"]
        order = state["order"]
        a = state["assessment"]
        case = CASE_INDEX[dispute_id]

        def ev_line(e: dict) -> str:
            when = (datetime.fromisoformat(e["timestamp"]).strftime("%d %b %Y, %H:%M")
                    if e["timestamp"] else "No timestamp")
            return f"{e['evidence_id']} — {e['evidence_type']} ({e['source']}, {when}): {e['finding']}"

        by_cat = lambda *c: [e for e in state["evidence"] if e["category"] in c]

        sections: list[dict[str, Any]] = [
            {"title": "1. Case summary", "kind": "text", "body": [
                f"Dispute {d['dispute_id']} was raised on "
                f"{datetime.fromisoformat(d['created_at']).strftime('%d %b %Y')} against transaction "
                f"{d['transaction_id']} for {fmt_amount(d['amount'])} under reason code "
                f"{d['reason_code']}.",
                state["argument"],
            ]},
            {"title": "2. Dispute details", "kind": "fields", "body": [
                ["Dispute ID", d["dispute_id"]], ["Network", d["network"]],
                ["Reason", d["reason"]], ["Reason code", d["reason_code"]],
                ["Disputed amount", fmt_amount(d["amount"])],
                ["Raised", datetime.fromisoformat(d["created_at"]).strftime("%d %b %Y, %H:%M")],
                ["Response deadline",
                 datetime.fromisoformat(d["response_deadline"]).strftime("%d %b %Y, %H:%M")],
                ["Merchant", f"{MERCHANT['name']} ({MERCHANT['merchant_id']})"],
            ]},
            {"title": "3. Customer claim", "kind": "quote", "body": [
                d["claim"], d["claim_detail"],
            ]},
            {"title": "4. Transaction evidence", "kind": "list",
             "body": [ev_line(e) for e in by_cat("payment")] or ["No transaction evidence retrieved."]},
            {"title": "5. Order evidence", "kind": "list",
             "body": [ev_line(e) for e in by_cat("order")] or ["No order evidence retrieved."]},
            {"title": "6. Fulfillment evidence", "kind": "list",
             "body": [ev_line(e) for e in by_cat("fulfillment")] or ["No fulfilment evidence retrieved."]},
            {"title": "7. Delivery evidence", "kind": "list",
             "body": [ev_line(e) for e in by_cat("delivery")] or ["No delivery evidence retrieved."]},
            {"title": "8. Customer communications", "kind": "list",
             "body": [
                 f"{datetime.fromisoformat(i['timestamp']).strftime('%d %b %Y, %H:%M')} — "
                 f"{i['channel']}: “{i['message']}”" for i in state["interactions"]
             ] or ["No customer communications are recorded for this order."]},
            {"title": "9. Timeline", "kind": "list", "body": [
                f"{t['date_label']} {t['time_label']} — {t['title']}"
                + (f" ({t['detail']})" if t["detail"] else "")
                + f" · source: {t['source']}"
                for t in state["timeline"]
            ]},
            {"title": "10. Supporting evidence", "kind": "list",
             "body": [ev_line(e) for e in state["evidence"] if e["impact"] == "merchant"
                      and e["availability"] != "unavailable"] or ["None."]},
            {"title": "11. Contradicting evidence", "kind": "list",
             "body": [ev_line(e) for e in state["evidence"] if e["impact"] == "customer"
                      and e["availability"] != "unavailable"] or ["None."]},
            {"title": "12. Evidence gaps", "kind": "list",
             "body": [f"{g['missing']} — {g['why_it_matters']} ({g['availability']})"
                      + (f" [record: {g['evidence_id']}]" if g.get("evidence_id") else "")
                      for g in state["gaps"]] or ["No material gaps identified."]},
            {"title": "13. Case assessment", "kind": "fields", "body": [
                ["Recommendation", a["recommendation_label"].upper()],
                ["Confidence", f"{a['confidence']}%"],
                ["Evidence completeness", f"{a['evidence_completeness']}%"],
                ["Case strength", a["case_strength"]],
                ["Contradictions detected", str(len(state["conflicts"]))],
                ["Evidence records correlated", str(state["correlation"]["unique_evidence"])],
            ]},
            {"title": "14. Merchant argument", "kind": "text", "body": [state["argument"]]},
            {"title": "15. Recommended response", "kind": "text", "body": [
                self._recommended_response(state),
                "AI recommendation is advisory. Final action requires human approval before submission.",
            ]},
        ]

        return {
            "dispute_id": dispute_id,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "document_title": f"Evidence package — {d['dispute_id']}",
            "merchant": MERCHANT,
            "recommendation": a["recommendation"],
            "sections": sections,
            "evidence_count": len(state["evidence"]),
            "disclaimer": (
                "Demo environment. Synthetic data. This document is generated from the case records held "
                "in this prototype and is not connected to a live payment processor or card network."
            ),
        }

    def _recommended_response(self, state: dict) -> str:
        a = state["assessment"]
        d = state["dispute"]
        gaps = state["gaps"]
        if a["recommendation"] == "CONTEST":
            lead = a["supporting_factors"][:3]
            parts = [
                f"Submit a representment for {fmt_amount(d['amount'])} citing the records that establish "
                "the disputed facts."
            ]
            if lead:
                parts.append(
                    "Lead with " + "; ".join(
                        f"{f['evidence_id']} ({f['text']})" for f in lead
                    ) + "."
                )
            if state["conflicts"]:
                c = state["conflicts"][0]
                parts.append(
                    f"Address the contradiction directly: the cardholder claim is not supported by the "
                    f"record — {c['interpretation']}"
                )
            if gaps:
                parts.append(
                    "Disclose the gaps rather than omitting them: "
                    + "; ".join(
                        f"{g['missing']}"
                        + (f" ({g['evidence_id']})" if g.get("evidence_id") else "")
                        for g in gaps
                    )
                    + ". The response must not claim a record exists when it does not."
                )
            return " ".join(parts)
        if a["recommendation"] == "ACCEPT":
            against = a["contradicting_factors"][:3]
            parts = [f"Accept the dispute for {fmt_amount(d['amount'])} and process the credit."]
            if against:
                parts.append(
                    "The case record supports the cardholder: "
                    + "; ".join(f"{f['evidence_id']} ({f['text']})" for f in against)
                    + "."
                )
            if gaps:
                parts.append(
                    "No representment should be filed while the following evidence is missing: "
                    + ", ".join(
                        f"{g['missing']}"
                        + (f" ({g['evidence_id']})" if g.get("evidence_id") else "")
                        for g in gaps
                    )
                    + "."
                )
            return " ".join(parts)
        blockers = [g for g in gaps if g["weight"] >= 2.0] or gaps[:2]
        parts = [
            "Hold for operator decision before submission — the evidence is not conclusive and the "
            "missing artefacts prevent a defensible response."
        ]
        if blockers:
            parts.append(
                "Request the outstanding records: "
                + "; ".join(
                    f"{g['missing']}"
                    + (f" ({g['evidence_id']})" if g.get("evidence_id") else "")
                    for g in blockers
                )
                + "."
            )
        parts.append(
            "Re-run the investigation when they arrive; do not submit a response on the current record."
        )
        return " ".join(parts)

    # -- copilot ----------------------------------------------------------
    SUGGESTIONS = [
        "Why are you recommending contest?",
        "What is the strongest evidence?",
        "What contradicts the customer's claim?",
        "What evidence is missing?",
        "Show me the case timeline.",
        "Generate my response.",
        "What could weaken this case?",
    ]

    def answer_copilot(self, dispute_id: str, question: str) -> dict:
        state = self.investigate_case(dispute_id)
        q = question.lower().strip()
        a = state["assessment"]
        d = state["dispute"]

        def cite(items, key="evidence_id"):
            return [i[key] for i in items if i.get(key)]

        # recommendation rationale
        if re.search(r"why|recommend|contest this|accept|reason for", q) and not re.search(r"weaken|missing|gap", q):
            rec = a["recommendation_label"]
            # Lead with the evidence that actually drives the recommendation.
            primary, secondary = (
                (a["contradicting_factors"], a["supporting_factors"])
                if a["recommendation"] == "ACCEPT"
                else (a["supporting_factors"], a["contradicting_factors"])
            )
            lines = [state["explanation"]["headline"]]
            if a["recommendation"] == "CONTEST" and state["conflicts"]:
                conflict = state["conflicts"][0]
                lines.append(conflict.get("interpretation") or conflict["why_it_matters"])
            for f in primary[:4]:
                lines.append(f"• {f['text']} [{f['evidence_id']}]")
            if secondary:
                lines.append("Set against that:")
                for f in secondary[:2]:
                    lines.append(f"• {f['text']} [{f['evidence_id']}]")
            for g in state["gaps"][:2]:
                lines.append(
                    f"• Gap: {g['missing']}"
                    + (f" [{g['evidence_id']}]" if g.get("evidence_id") else "")
                    + f" — {g['why_it_matters']}"
                )
            gap_evidence = [g["evidence_id"] for g in state["gaps"] if g.get("evidence_id")]
            return self._answer(
                f"Recommendation: {rec.upper()} — {a['confidence']}% confidence, "
                f"{a['evidence_completeness']}% evidence completeness.",
                lines, cite(a["supporting_factors"]) + cite(a["contradicting_factors"]) + gap_evidence, state)

        if re.search(r"strongest|best evidence|strong evidence|key evidence", q):
            top = [e for e in state["evidence"] if e["availability"] != "unavailable"][:4]
            return self._answer(
                "Strongest available evidence, ranked by relevance and availability:",
                [f"• {e['evidence_id']} — {e['evidence_type']} ({e['source']}): {e['finding']}" for e in top],
                [e["evidence_id"] for e in top], state)

        if re.search(r"contradict|conflict|inconsisten", q):
            if not state["conflicts"]:
                return self._answer("No material contradictions were detected in this case.",
                                    ["Every retrieved record is consistent with the others. The evidence "
                                     "points in one direction, which is reflected in the assessment."],
                                    [], state)
            lines = []
            for c in state["conflicts"]:
                lines.append(
                    f"{c['type']} — severity {c['severity']}, "
                    f"confidence {c.get('confidence', 'n/a')}%: {c['summary']}"
                )
                if c.get("interpretation"):
                    lines.append(f"Interpretation: {c['interpretation']}")
                for l in c["lines"]:
                    tag = f" [{l['evidence_id']}]" if l["evidence_id"] else ""
                    lines.append(f"• {l['label']}: {l['value']}{tag}")
                lines.append(f"Why it matters: {c['why_it_matters']}")
            return self._answer(f"{len(state['conflicts'])} contradiction(s) detected.", lines,
                                [e for c in state["conflicts"] for e in c["evidence_ids"]], state)

        if re.search(r"missing|gap|don't have|do not have|unavailable", q):
            if not state["gaps"]:
                return self._answer("No material evidence gaps were identified for this case.", [], [], state)
            gap_evidence = [g["evidence_id"] for g in state["gaps"] if g.get("evidence_id")]
            return self._answer(
                f"{len(state['gaps'])} evidence gap(s) identified:",
                [f"• {g['missing']} — {g['why_it_matters']} (Availability: {g['availability']})"
                 + (f" [{g['evidence_id']}]" if g.get("evidence_id") else "")
                 for g in state["gaps"]], gap_evidence, state)

        if re.search(r"timeline|chronolog|sequence|what happened|when", q):
            return self._answer(
                f"Reconstructed timeline — {len(state['timeline'])} events across "
                f"{len({t['source'] for t in state['timeline']})} systems:",
                [f"• {t['date_label']} {t['time_label']} — {t['title']}"
                 + (f" ({t['detail']})" if t["detail"] else "") + f" · {t['source']}"
                 for t in state["timeline"]],
                [e for t in state["timeline"] for e in t["evidence_ids"]], state)

        if re.search(r"include|response|package|submit|what should i", q):
            if a["recommendation"] == "CONTEST":
                cited = [f["evidence_id"] for f in a["supporting_factors"][:3]]
            elif a["recommendation"] == "ACCEPT":
                cited = [f["evidence_id"] for f in a["contradicting_factors"][:3]]
            else:
                cited = [g["evidence_id"] for g in state["gaps"] if g.get("evidence_id")]
            cited += [g["evidence_id"] for g in state["gaps"] if g.get("evidence_id")]
            return self._answer(
                "Recommended response content:",
                [self._recommended_response(state),
                 "The generated evidence package assembles this into 15 sections, including the gaps."],
                cited, state)

        if re.search(r"weaken|risk|against us|lose|downside|counter", q):
            lines = [f"• {f['text']} [{f['evidence_id']}]" for f in a["contradicting_factors"]]
            lines += [
                f"• Gap: {g['missing']}"
                + (f" [{g['evidence_id']}]" if g.get("evidence_id") else "")
                + f" — {g['why_it_matters']}"
                for g in state["gaps"]
            ]
            gap_evidence = [g["evidence_id"] for g in state["gaps"] if g.get("evidence_id")]
            if not lines:
                lines = ["No contradicting evidence and no material gaps are recorded for this case."]
            return self._answer("Factors that could weaken this case:", lines,
                                cite(a["contradicting_factors"]) + gap_evidence, state)

        if re.search(r"claim|customer say|cardholder", q):
            return self._answer(
                "Customer claim on file:",
                [f"“{d['claim']}”", d["claim_detail"],
                 f"Reason code {d['reason_code']}, raised "
                 f"{datetime.fromisoformat(d['created_at']).strftime('%d %b %Y')}."], [], state)

        if re.search(r"amount|value|how much", q):
            return self._answer("Amount in dispute:", [
                f"{fmt_amount(d['amount'])} disputed against transaction {d['transaction_id']}.",
                (f"Refunds already issued: "
                 f"{fmt_amount(sum(r['amount'] for r in state['refunds']))}."
                 if state["refunds"] else "No refunds have been issued against this transaction."),
            ], [], state)

        if re.search(r"deadline|due|time left", q):
            return self._answer("Response deadline:", [
                datetime.fromisoformat(d["response_deadline"]).strftime(
                    "Response is due by %d %b %Y at %H:%M."),
            ], [], state)

        if re.search(r"polic", q):
            pols = state["policies"]
            if not pols:
                return self._answer(NOT_AVAILABLE,
                                    ["No policy record in the knowledge base matches this dispute type."],
                                    [], state)
            return self._answer("Applicable policy knowledge (not case evidence):", [
                f"• {p['policy_id']} {p['name']} — {p['response_requirements']}" for p in pols], [], state)

        return self._answer(
            NOT_AVAILABLE,
            ["This copilot answers only from the records retrieved for this investigation. Try one of the "
             "suggested questions, or ask about the claim, evidence, contradictions, gaps, timeline, "
             "deadline or policy."],
            [], state)

    def _answer(self, headline: str, lines: list[str], evidence_ids: list[str], state: dict) -> dict:
        seen: list[str] = []
        for e in evidence_ids:
            if e and e not in seen:
                seen.append(e)
        return {
            "headline": headline,
            "lines": lines,
            "evidence_ids": seen[:8],
            "grounded_in": {
                "dispute_id": state["dispute"]["dispute_id"],
                "evidence_records": len(state["evidence"]),
                "mode": self.mode,
            },
        }


ai_service = AIService()
