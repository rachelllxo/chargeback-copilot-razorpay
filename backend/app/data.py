"""
Synthetic demo dataset for Chargeback Copilot.

DEMO ENVIRONMENT — every record in this module is synthetic. Nothing here is
connected to a real payment processor, bank, or courier network.

The dataset is intentionally hand-authored: each case has a *different*
evidence relationship (complete chain, broken chain, missing records,
contradicting communications, partial refunds, fraud signals ...) so the
investigation engine produces genuinely different findings per case.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

# The demo world clock. Deadlines are rendered relative to this instant so the
# dashboard always shows a believable "due in 6 hours" state.
NOW = datetime(2026, 8, 18, 11, 30)

MERCHANT = {
    "merchant_id": "MRCH-IN-4417",
    "name": "Northline Retail Pvt Ltd",
    "category": "Consumer electronics & lifestyle",
    "environment": "Demo environment — synthetic data",
}

# Relevance weighting used by the investigation engine.
RELEVANCE_WEIGHT = {"high": 3.0, "medium": 2.0, "low": 1.0}

# Evidence categories the engine expects to reason about.
CATEGORIES = [
    "payment",
    "order",
    "fulfillment",
    "delivery",
    "refund",
    "customer",
    "communication",
    "historical",
    "policy",
]

CATEGORY_LABEL = {
    "payment": "Payment",
    "order": "Order",
    "fulfillment": "Fulfillment",
    "delivery": "Delivery",
    "refund": "Refund",
    "customer": "Customer",
    "communication": "Communication",
    "historical": "Historical",
    "policy": "Policy",
}


def ev(
    eid: str,
    etype: str,
    category: str,
    source: str,
    ts: str | None,
    description: str,
    finding: str,
    impact: str,
    relevance: str,
    availability: str = "available",
    fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one evidence record.

    impact: merchant | customer | neutral
    availability: available | partial | unavailable
    """
    return {
        "evidence_id": eid,
        "evidence_type": etype,
        "category": category,
        "source": source,
        "timestamp": ts,
        "description": description,
        "finding": finding,
        "impact": impact,
        "relevance": relevance,
        "availability": availability,
        "fields": fields or {},
    }


def gap(title: str, why: str, weight: float, availability: str = "Not available") -> dict[str, Any]:
    return {"missing": title, "why_it_matters": why, "weight": weight, "availability": availability}


def event(date: str, time: str | None, title: str, source: str, evidence_ids: list[str],
          detail: str = "", actor: str = "system") -> dict[str, Any]:
    return {
        "date": date,
        "time": time,
        "title": title,
        "detail": detail,
        "source": source,
        "actor": actor,
        "evidence_ids": evidence_ids,
    }


# ---------------------------------------------------------------------------
# CASES
# ---------------------------------------------------------------------------

CASES: list[dict[str, Any]] = []


# ── CASE 1 (flagship) — strong merchant case with a contradiction ──────────
CASES.append({
    "dispute": {
        "dispute_id": "CB-2026-89101",
        "transaction_id": "TXN-928184",
        "order_id": "ORD-728491",
        "customer_id": "CUST-40881",
        "customer_name": "Aarav Sharma",
        "customer_email": "aarav.sharma@example.in",
        "reason": "Product not received",
        "reason_code": "13.1 — Merchandise / services not received",
        "network": "Visa",
        "amount": 8499,
        "created_at": "2026-08-18T08:40:00",
        "response_deadline": "2026-08-18T17:30:00",
        "status": "Needs review",
        "priority": "high",
        "claim": "I never received the product.",
        "claim_detail": (
            "Cardholder states the order was never delivered to the registered address and "
            "requests a full reversal of the transaction."
        ),
    },
    "transaction": {
        "transaction_id": "TXN-928184", "order_id": "ORD-728491", "customer_id": "CUST-40881",
        "merchant_id": MERCHANT["merchant_id"], "amount": 8499, "currency": "INR",
        "payment_method": "Card • HDFC Visa credit •••• 4412",
        "timestamp": "2026-08-12T10:31:00", "status": "captured",
        "auth_code": "A83MK2", "avs_match": True, "cvv_match": True, "three_ds": "Authenticated",
    },
    "order": {
        "order_id": "ORD-728491", "customer_id": "CUST-40881",
        "product": "Noise-cancelling headphones — Model NX70",
        "order_timestamp": "2026-08-12T10:33:00",
        "fulfillment_status": "fulfilled", "delivery_status": "delivered",
        "delivery_timestamp": "2026-08-15T15:47:00",
        "shipping_address": "Flat 1204, Ashwin Residency, Powai, Mumbai 400076",
        "courier": "BlueDart", "awb": "BD-771290348",
    },
    "refunds": [],
    "interactions": [
        {"interaction_id": "INT-5521", "customer_id": "CUST-40881", "order_id": "ORD-728491",
         "timestamp": "2026-08-16T11:20:00", "channel": "Email", "category": "product_condition",
         "message": "Package arrived damaged. The outer box was crushed — can I get a replacement?"},
        {"interaction_id": "INT-5528", "customer_id": "CUST-40881", "order_id": "ORD-728491",
         "timestamp": "2026-08-16T14:05:00", "channel": "Email", "category": "support_response",
         "message": "Support offered a replacement unit or a return pickup. No reply received."},
    ],
    "evidence": [
        ev("EVD-1040", "Payment authorisation", "payment", "Payment gateway", "2026-08-12T10:31:00",
           "Card payment authorised and captured for ₹8,499.",
           "Payment successfully captured with 3-D Secure authentication.",
           "merchant", "high", fields={"Auth code": "A83MK2", "3-D Secure": "Authenticated",
                                       "AVS": "Match", "CVV": "Match", "Amount": "₹8,499"}),
        ev("EVD-1041", "Order record", "order", "Order system", "2026-08-12T10:33:00",
           "Order ORD-728491 created against transaction TXN-928184.",
           "Order created two minutes after capture and linked to the disputed transaction.",
           "merchant", "medium", fields={"Order": "ORD-728491", "SKU": "NX70-BLK",
                                         "Ship to": "Powai, Mumbai 400076"}),
        ev("EVD-1039", "Dispatch manifest", "fulfillment", "Fulfilment system", "2026-08-13T09:12:00",
           "Parcel handed to BlueDart, AWB BD-771290348.",
           "Order was picked, packed and dispatched within one business day.",
           "merchant", "high", fields={"Courier": "BlueDart", "AWB": "BD-771290348",
                                       "Weight": "0.84 kg", "Warehouse": "MUM-2"}),
        ev("EVD-1042", "Delivery record", "delivery", "Delivery system", "2026-08-15T15:47:00",
           "Courier marked the shipment delivered at the registered shipping address.",
           "Order marked delivered.",
           "merchant", "high", fields={"Status": "Delivered", "Received by": "Recipient (name not captured)",
                                       "Geo-stamp": "19.1176° N, 72.9060° E", "Scan device": "BD-HH-2210"}),
        ev("EVD-1047", "Tracking access log", "customer", "Customer activity", "2026-08-15T16:02:00",
           "Customer account opened the tracking page 15 minutes after the delivery scan.",
           "Customer viewed tracking showing delivered status shortly after delivery.",
           "merchant", "medium", fields={"Session": "SES-90124", "Device": "iOS app 8.2",
                                         "Page": "Order tracking — ORD-728491"}),
        ev("EVD-1044", "Support email", "communication", "Customer support", "2026-08-16T11:20:00",
           "Customer emailed support about the condition of the received package.",
           "Customer reported the package arrived damaged — implying physical receipt.",
           "merchant", "high", fields={"Channel": "Email", "Category": "Product condition",
                                       "Message": "Package arrived damaged. The outer box was crushed — can I get a replacement?"}),
        ev("EVD-1045", "Support resolution log", "communication", "Customer support", "2026-08-16T14:05:00",
           "Replacement or return pickup offered; customer did not respond.",
           "Merchant offered remedy before the chargeback was raised.",
           "merchant", "medium", fields={"Offer": "Replacement or return pickup", "Response": "None"}),
        ev("EVD-1051", "Refund ledger", "refund", "Refund system", None,
           "No refund or partial credit was issued against TXN-928184 prior to the dispute.",
           "No pre-dispute refund exists, so the disputed amount is not duplicated.",
           "merchant", "medium", fields={"Refunds found": "0", "Ledger": "Clean"}),
        ev("EVD-1053", "Customer dispute history", "historical", "Dispute system", None,
           "One earlier dispute on this customer profile in the last 24 months, resolved in the merchant's favour.",
           "Limited history; a single prior dispute closed in the merchant's favour.",
           "merchant", "low", availability="partial",
           fields={"Prior disputes": "1", "Outcome": "Merchant favour", "Window": "24 months"}),
        ev("EVD-1056", "Policy reference", "policy", "Policy knowledge base", None,
           "Network policy 13.1 — merchandise not received: proof of delivery to the cardholder address rebuts the claim.",
           "Delivery confirmation to the registered address is the required rebuttal artefact.",
           "neutral", "medium", fields={"Policy": "PL-013 Non-receipt disputes", "Network": "Visa 13.1"}),
        ev("EVD-1049", "Signed delivery confirmation", "delivery", "Delivery system", None,
           "Courier did not capture a signature or OTP for this delivery.",
           "Signed proof of delivery was not captured by the courier.",
           "neutral", "medium", availability="unavailable",
           fields={"Signature": "Not captured", "OTP": "Not captured"}),
    ],
    "claim_vs_evidence": [
        ("Payment", "Captured", "EVD-1040"),
        ("Order", "Fulfilled", "EVD-1041"),
        ("Shipment", "Dispatched", "EVD-1039"),
        ("Delivery", "Delivered", "EVD-1042"),
        ("Customer communication", "Package reported damaged", "EVD-1044"),
    ],
    "events": [
        event("2026-08-12", "10:31", "Payment captured", "Transaction system", ["EVD-1040"], "₹8,499"),
        event("2026-08-12", "10:33", "Order created", "Order system", ["EVD-1041"], "ORD-728491"),
        event("2026-08-13", "09:12", "Order dispatched", "Fulfilment system", ["EVD-1039"], "AWB BD-771290348"),
        event("2026-08-15", "15:47", "Order delivered", "Delivery system", ["EVD-1042"], "Delivered at Powai, Mumbai"),
        event("2026-08-15", "16:02", "Customer accessed tracking", "Customer activity", ["EVD-1047"],
              "Tracking page opened 15 minutes after delivery", actor="customer"),
        event("2026-08-16", "11:20", "Customer contacted support", "Customer support", ["EVD-1044"],
              "\u201cPackage arrived damaged.\u201d", actor="customer"),
        event("2026-08-16", "14:05", "Replacement offered", "Customer support", ["EVD-1045"],
              "No customer response recorded"),
        event("2026-08-18", "08:40", "Chargeback initiated", "Dispute system", [],
              "Reason: product not received", actor="issuer"),
    ],
    "gaps": [
        gap("Signed delivery confirmation",
            "Could provide additional support for the merchant's delivery claim.", 1.2),
        gap("Complete customer communication history",
            "Could clarify the chronology of the dispute between delivery and chargeback.", 1.0,
            "Partially available"),
    ],
    "argument": (
        "The transaction was authenticated and captured, the order was fulfilled and dispatched within one "
        "business day, and the courier recorded delivery to the cardholder's registered address. Fifteen "
        "minutes after the delivery scan the customer's own account opened the tracking page, and the "
        "following morning the customer emailed support describing the condition of the delivered package. "
        "Those records are inconsistent with a non-receipt claim. A replacement was offered before the "
        "chargeback was raised and no refund has been issued."
    ),
})


# ── CASE 2 — strong customer case, merchant failed to fulfil ───────────────
CASES.append({
    "dispute": {
        "dispute_id": "CB-2026-89102",
        "transaction_id": "TXN-928402", "order_id": "ORD-728655", "customer_id": "CUST-41220",
        "customer_name": "Meera Iyer", "customer_email": "meera.iyer@example.in",
        "reason": "Services not rendered",
        "reason_code": "13.2 — Cancelled recurring / services not provided",
        "network": "Mastercard", "amount": 15750,
        "created_at": "2026-08-16T09:15:00", "response_deadline": "2026-08-21T18:00:00",
        "status": "Investigated", "priority": "medium",
        "claim": "I paid for an installation service that was never provided.",
        "claim_detail": "Cardholder booked a paid appliance installation slot which the merchant never attended.",
    },
    "transaction": {
        "transaction_id": "TXN-928402", "order_id": "ORD-728655", "customer_id": "CUST-41220",
        "merchant_id": MERCHANT["merchant_id"], "amount": 15750, "currency": "INR",
        "payment_method": "UPI • meera@okhdfcbank", "timestamp": "2026-08-04T18:22:00",
        "status": "captured", "auth_code": "U22PQ8", "avs_match": None, "cvv_match": None,
        "three_ds": "Not applicable (UPI)",
    },
    "order": {
        "order_id": "ORD-728655", "customer_id": "CUST-41220",
        "product": "Split AC installation & commissioning service",
        "order_timestamp": "2026-08-04T18:23:00", "fulfillment_status": "not_fulfilled",
        "delivery_status": "not_applicable", "delivery_timestamp": None,
        "shipping_address": "22 Lake View Road, Bengaluru 560034", "courier": None, "awb": None,
    },
    "refunds": [],
    "interactions": [
        {"interaction_id": "INT-5602", "customer_id": "CUST-41220", "order_id": "ORD-728655",
         "timestamp": "2026-08-08T10:40:00", "channel": "Phone", "category": "service_missed",
         "message": "Technician did not arrive for the scheduled slot on 7 Aug."},
        {"interaction_id": "INT-5611", "customer_id": "CUST-41220", "order_id": "ORD-728655",
         "timestamp": "2026-08-12T16:10:00", "channel": "Email", "category": "refund_request",
         "message": "Second missed appointment. Please refund the installation charge."},
    ],
    "evidence": [
        ev("EVD-2010", "Payment authorisation", "payment", "Payment gateway", "2026-08-04T18:22:00",
           "UPI collect of ₹15,750 completed.", "Payment captured successfully.",
           "merchant", "high", fields={"VPA": "meera@okhdfcbank", "Amount": "₹15,750"}),
        ev("EVD-2011", "Service booking", "order", "Order system", "2026-08-04T18:23:00",
           "Installation slot booked for 7 Aug 2026, 10:00–13:00.",
           "A service obligation was created and accepted by the merchant.",
           "customer", "high", fields={"Slot": "7 Aug 2026, 10:00–13:00", "Engineer": "Unassigned"}),
        ev("EVD-2013", "Field service log", "fulfillment", "Fulfilment system", "2026-08-07T13:00:00",
           "No technician was assigned; slot auto-closed as 'unattended'.",
           "Merchant did not perform the booked service.",
           "customer", "high", fields={"Assignment": "None", "Slot outcome": "Unattended",
                                       "Rescheduled": "No"}),
        ev("EVD-2014", "Support call record", "communication", "Customer support", "2026-08-08T10:40:00",
           "Customer reported the missed appointment by phone.",
           "Customer escalated the missed service four days before the dispute.",
           "customer", "medium", fields={"Channel": "Phone", "Duration": "6m 12s",
                                         "Outcome": "Promised callback"}),
        ev("EVD-2015", "Refund request", "communication", "Customer support", "2026-08-12T16:10:00",
           "Written refund request after a second missed appointment.",
           "Customer requested a refund which the merchant did not action.",
           "customer", "high", fields={"Channel": "Email", "Merchant action": "None recorded"}),
        ev("EVD-2016", "Refund ledger", "refund", "Refund system", None,
           "No refund issued against TXN-928402 despite an open refund request.",
           "The service was not delivered and the amount was not returned.",
           "customer", "high", fields={"Refunds found": "0", "Open request": "Yes"}),
        ev("EVD-2018", "Customer dispute history", "historical", "Dispute system", None,
           "No prior disputes on this customer profile.",
           "Clean customer history; no pattern of dispute abuse.",
           "customer", "low", fields={"Prior disputes": "0"}),
        ev("EVD-2019", "Policy reference", "policy", "Policy knowledge base", None,
           "Policy PL-021: services not rendered require proof of service completion signed by the customer.",
           "No completion artefact exists, so the claim cannot be rebutted.",
           "neutral", "medium", fields={"Policy": "PL-021 Services not rendered"}),
    ],
    "claim_vs_evidence": [
        ("Payment", "Captured", "EVD-2010"),
        ("Service booking", "Confirmed for 7 Aug", "EVD-2011"),
        ("Fulfillment", "No technician assigned", "EVD-2013"),
        ("Customer communication", "Two missed-appointment reports", "EVD-2015"),
        ("Refund", "Not issued", "EVD-2016"),
    ],
    "events": [
        event("2026-08-04", "18:22", "Payment captured", "Transaction system", ["EVD-2010"], "₹15,750"),
        event("2026-08-04", "18:23", "Service slot booked", "Order system", ["EVD-2011"], "7 Aug, 10:00–13:00"),
        event("2026-08-07", "13:00", "Service slot closed unattended", "Fulfilment system", ["EVD-2013"],
              "No engineer assigned"),
        event("2026-08-08", "10:40", "Customer reported missed appointment", "Customer support", ["EVD-2014"],
              "Phone call, callback promised", actor="customer"),
        event("2026-08-12", "16:10", "Customer requested refund", "Customer support", ["EVD-2015"],
              "No merchant action recorded", actor="customer"),
        event("2026-08-16", "09:15", "Chargeback initiated", "Dispute system", [],
              "Reason: services not rendered", actor="issuer"),
    ],
    "gaps": [
        gap("Proof of service completion", "Would be required to contest a services-not-rendered claim.", 2.0),
        gap("Reschedule offer sent to the customer", "Could show a remedy attempt before the dispute.", 1.0),
    ],
    "argument": (
        "Records do not support contesting this dispute. The payment was captured but the booked installation "
        "slot closed unattended with no engineer assigned, the customer escalated twice, and no refund was "
        "issued against an open refund request. Accepting the dispute avoids representment costs and an "
        "almost certain loss at pre-arbitration."
    ),
})


# ── CASE 3 — conflicting evidence, genuinely balanced ──────────────────────
CASES.append({
    "dispute": {
        "dispute_id": "CB-2026-89103",
        "transaction_id": "TXN-929015", "order_id": "ORD-729110", "customer_id": "CUST-41855",
        "customer_name": "Rohan Verma", "customer_email": "rohan.verma@example.in",
        "reason": "Product not as described",
        "reason_code": "13.3 — Not as described or defective",
        "network": "Visa", "amount": 4299,
        "created_at": "2026-08-17T14:05:00", "response_deadline": "2026-08-22T18:00:00",
        "status": "Needs review", "priority": "medium",
        "claim": "The item delivered was a different model from the one I ordered.",
        "claim_detail": "Cardholder states a lower-specification variant was shipped instead of the ordered SKU.",
    },
    "transaction": {
        "transaction_id": "TXN-929015", "order_id": "ORD-729110", "customer_id": "CUST-41855",
        "merchant_id": MERCHANT["merchant_id"], "amount": 4299, "currency": "INR",
        "payment_method": "Card • ICICI Visa debit •••• 8830", "timestamp": "2026-08-09T20:14:00",
        "status": "captured", "auth_code": "V19LT4", "avs_match": True, "cvv_match": True,
        "three_ds": "Authenticated",
    },
    "order": {
        "order_id": "ORD-729110", "customer_id": "CUST-41855",
        "product": "Smart fitness band — Model FB3 Pro",
        "order_timestamp": "2026-08-09T20:15:00", "fulfillment_status": "fulfilled",
        "delivery_status": "delivered", "delivery_timestamp": "2026-08-12T12:20:00",
        "shipping_address": "B-14 Sector 62, Noida 201301", "courier": "Delhivery", "awb": "DL-559102773",
    },
    "refunds": [],
    "interactions": [
        {"interaction_id": "INT-5710", "customer_id": "CUST-41855", "order_id": "ORD-729110",
         "timestamp": "2026-08-12T19:44:00", "channel": "Chat", "category": "wrong_item",
         "message": "This is the FB3 base model, not the Pro. Serial on the box ends 7741."},
        {"interaction_id": "INT-5716", "customer_id": "CUST-41855", "order_id": "ORD-729110",
         "timestamp": "2026-08-14T10:02:00", "channel": "Chat", "category": "return",
         "message": "Return pickup scheduled but courier did not arrive."},
    ],
    "evidence": [
        ev("EVD-3001", "Payment authorisation", "payment", "Payment gateway", "2026-08-09T20:14:00",
           "Card payment authorised and captured for ₹4,299.", "Payment captured with 3-D Secure.",
           "merchant", "high", fields={"Auth code": "V19LT4", "3-D Secure": "Authenticated"}),
        ev("EVD-3002", "Order record", "order", "Order system", "2026-08-09T20:15:00",
           "Order placed for SKU FB3-PRO-BLK.", "Ordered SKU was the Pro variant.",
           "customer", "high", fields={"Ordered SKU": "FB3-PRO-BLK", "Price": "₹4,299"}),
        ev("EVD-3003", "Pick & pack log", "fulfillment", "Fulfilment system", "2026-08-10T08:40:00",
           "Warehouse scan records SKU FB3-BASE-BLK leaving the pick face for this order.",
           "The dispatched SKU does not match the ordered SKU.",
           "customer", "high", fields={"Scanned SKU": "FB3-BASE-BLK", "Ordered SKU": "FB3-PRO-BLK",
                                       "Picker": "WH-Noida-07"}) | {
               "conflicts_with": ["EVD-3002"],
               "conflict_severity": "high",
               "conflict_summary": "The dispatched SKU does not match the ordered SKU.",
               "conflict_why": (
                   "The merchant's own warehouse scan corroborates the cardholder on the material point of "
                   "the dispute, so a representment based on the delivery scan alone is unlikely to succeed."
               )},
        ev("EVD-3004", "Delivery record", "delivery", "Delivery system", "2026-08-12T12:20:00",
           "Shipment delivered and OTP verified at the door.",
           "Delivery itself is proven; the dispute is about the item shipped.",
           "merchant", "medium", fields={"OTP": "Verified", "Received by": "R. Verma"}),
        ev("EVD-3006", "Support chat transcript", "communication", "Customer support", "2026-08-12T19:44:00",
           "Customer reported the wrong variant within seven hours of delivery, quoting a serial number.",
           "Customer complaint is specific, prompt and consistent with the pick log.",
           "customer", "high", fields={"Quoted serial": "…7741",
                                       "Serial range": "FB3-BASE stock block 7700–7799"}),
        ev("EVD-3007", "Return pickup log", "fulfillment", "Fulfilment system", "2026-08-14T10:02:00",
           "Return pickup was scheduled but the courier task expired unattempted.",
           "Merchant-side return process failed, leaving the customer without remedy.",
           "customer", "medium", fields={"Pickup status": "Expired", "Attempts": "0"}),
        ev("EVD-3009", "Refund ledger", "refund", "Refund system", None,
           "No refund issued.", "No credit was returned to the cardholder before the dispute.",
           "customer", "medium", fields={"Refunds found": "0"}),
        ev("EVD-3011", "Customer dispute history", "historical", "Dispute system", None,
           "Two prior disputes in 18 months, both closed in the merchant's favour.",
           "Some dispute history exists, which slightly weakens the cardholder's position.",
           "merchant", "medium", fields={"Prior disputes": "2", "Both outcomes": "Merchant favour"}),
        ev("EVD-3012", "Policy reference", "policy", "Policy knowledge base", None,
           "Policy PL-034: not-as-described claims require dispatch imagery or serial-level scan proof.",
           "Serial-level proof of the dispatched unit is the deciding artefact.",
           "neutral", "medium", fields={"Policy": "PL-034 Not as described"}),
        ev("EVD-3013", "Dispatch imagery", "fulfillment", "Fulfilment system", None,
           "Packing-bench photograph for this consignment was not retained.",
           "No visual proof of the packed unit is available.",
           "neutral", "medium", availability="unavailable", fields={"Retention": "Expired at 3 days"}),
    ],
    "claim_vs_evidence": [
        ("Payment", "Captured", "EVD-3001"),
        ("Ordered SKU", "FB3-PRO-BLK", "EVD-3002"),
        ("Dispatched SKU", "FB3-BASE-BLK", "EVD-3003"),
        ("Delivery", "Delivered, OTP verified", "EVD-3004"),
        ("Customer communication", "Wrong variant reported in 7 hours", "EVD-3006"),
    ],
    "events": [
        event("2026-08-09", "20:14", "Payment captured", "Transaction system", ["EVD-3001"], "₹4,299"),
        event("2026-08-09", "20:15", "Order created", "Order system", ["EVD-3002"], "SKU FB3-PRO-BLK"),
        event("2026-08-10", "08:40", "Order picked and packed", "Fulfilment system", ["EVD-3003"],
              "Scanned SKU FB3-BASE-BLK"),
        event("2026-08-12", "12:20", "Order delivered", "Delivery system", ["EVD-3004"], "OTP verified"),
        event("2026-08-12", "19:44", "Customer reported wrong variant", "Customer support", ["EVD-3006"],
              "Serial quoted: …7741", actor="customer"),
        event("2026-08-14", "10:02", "Return pickup expired", "Fulfilment system", ["EVD-3007"],
              "Courier task unattempted"),
        event("2026-08-17", "14:05", "Chargeback initiated", "Dispute system", [],
              "Reason: product not as described", actor="issuer"),
    ],
    "gaps": [
        gap("Packing-bench photograph", "Would show which unit was actually packed for this consignment.", 2.0),
        gap("Returned-unit inspection report", "No unit was collected, so its condition cannot be verified.", 1.5),
    ],
    "argument": (
        "Delivery is proven, but the warehouse pick log records a different SKU from the one ordered and the "
        "customer's complaint quotes a serial number inside the base-model stock block. The merchant's own "
        "records therefore corroborate the cardholder on the material point. Dispatch imagery is unavailable, "
        "so a representment would rest on the delivery scan alone."
    ),
})


# ── CASE 4 — missing evidence, cannot be resolved from records ─────────────
CASES.append({
    "dispute": {
        "dispute_id": "CB-2026-89104",
        "transaction_id": "TXN-929440", "order_id": "ORD-729502", "customer_id": "CUST-42077",
        "customer_name": "Ananya Nair", "customer_email": "ananya.nair@example.in",
        "reason": "Product not received",
        "reason_code": "13.1 — Merchandise / services not received",
        "network": "RuPay", "amount": 22000,
        "created_at": "2026-08-17T07:50:00", "response_deadline": "2026-08-20T18:00:00",
        "status": "Needs review", "priority": "high",
        "claim": "The order never arrived and tracking stopped updating.",
        "claim_detail": "Cardholder states the consignment stopped scanning after leaving the regional hub.",
    },
    "transaction": {
        "transaction_id": "TXN-929440", "order_id": "ORD-729502", "customer_id": "CUST-42077",
        "merchant_id": MERCHANT["merchant_id"], "amount": 22000, "currency": "INR",
        "payment_method": "Card • SBI RuPay credit •••• 2201", "timestamp": "2026-08-06T13:05:00",
        "status": "captured", "auth_code": "R71ZC9", "avs_match": True, "cvv_match": True,
        "three_ds": "Authenticated",
    },
    "order": {
        "order_id": "ORD-729502", "customer_id": "CUST-42077",
        "product": "Robotic vacuum cleaner — Model RV900",
        "order_timestamp": "2026-08-06T13:06:00", "fulfillment_status": "fulfilled",
        "delivery_status": "in_transit", "delivery_timestamp": None,
        "shipping_address": "Villa 8, Marine Enclave, Kochi 682016", "courier": "Regional Logistics Co",
        "awb": "RL-330928114",
    },
    "refunds": [],
    "interactions": [
        {"interaction_id": "INT-5820", "customer_id": "CUST-42077", "order_id": "ORD-729502",
         "timestamp": "2026-08-13T09:30:00", "channel": "Email", "category": "delivery_delay",
         "message": "Tracking has not moved since 9 Aug. Where is my order?"},
    ],
    "evidence": [
        ev("EVD-4001", "Payment authorisation", "payment", "Payment gateway", "2026-08-06T13:05:00",
           "Card payment authorised and captured for ₹22,000.", "Payment captured and authenticated.",
           "merchant", "high", fields={"Auth code": "R71ZC9", "3-D Secure": "Authenticated"}),
        ev("EVD-4002", "Order record", "order", "Order system", "2026-08-06T13:06:00",
           "Order created for SKU RV900-WHT.", "Order exists and matches the disputed amount.",
           "merchant", "medium", fields={"SKU": "RV900-WHT", "Amount": "₹22,000"}),
        ev("EVD-4003", "Dispatch manifest", "fulfillment", "Fulfilment system", "2026-08-08T11:25:00",
           "Consignment handed to Regional Logistics Co, AWB RL-330928114.",
           "Merchant dispatched the goods to the courier.",
           "merchant", "high", fields={"Courier": "Regional Logistics Co", "AWB": "RL-330928114"}),
        ev("EVD-4004", "Courier scan history", "delivery", "Delivery system", "2026-08-09T18:40:00",
           "Last recorded scan: 'departed Ernakulam hub'. No further scans and no delivery event.",
           "Tracking stops in transit; there is no proof of delivery.",
           "customer", "high", availability="partial",
           fields={"Last scan": "9 Aug 2026, 18:40 — departed Ernakulam hub", "Delivery scan": "None"}),
        ev("EVD-4006", "Support email", "communication", "Customer support", "2026-08-13T09:30:00",
           "Customer chased the shipment four days before raising the dispute.",
           "Customer attempted resolution before disputing.",
           "customer", "medium", fields={"Channel": "Email", "Merchant reply": "Auto-acknowledgement only"}),
        ev("EVD-4008", "Refund ledger", "refund", "Refund system", None,
           "No refund issued and no goodwill credit applied.",
           "The amount remains fully with the merchant.",
           "customer", "medium", fields={"Refunds found": "0"}),
        ev("EVD-4010", "Customer dispute history", "historical", "Dispute system", None,
           "No prior disputes recorded for this customer.", "Clean dispute history.",
           "customer", "low", fields={"Prior disputes": "0"}),
        ev("EVD-4011", "Policy reference", "policy", "Policy knowledge base", None,
           "Policy PL-013: a delivery scan to the cardholder address is mandatory to contest non-receipt.",
           "Without a delivery scan the required rebuttal artefact does not exist.",
           "neutral", "medium", fields={"Policy": "PL-013 Non-receipt disputes"}),
        ev("EVD-4012", "Proof of delivery", "delivery", "Delivery system", None,
           "Courier has not returned a POD document for this AWB.",
           "Proof of delivery is unavailable.",
           "neutral", "high", availability="unavailable", fields={"POD": "Not returned", "Requested": "2 times"}),
        ev("EVD-4013", "Courier investigation report", "fulfillment", "Fulfilment system", None,
           "A trace request was raised with the courier; no report has been returned.",
           "The courier trace is still open.",
           "neutral", "medium", availability="unavailable",
           fields={"Trace ref": "TR-88120", "Status": "Open since 14 Aug"}),
    ],
    "claim_vs_evidence": [
        ("Payment", "Captured", "EVD-4001"),
        ("Order", "Created and picked", "EVD-4002"),
        ("Shipment", "Dispatched to courier", "EVD-4003"),
        ("Delivery", "No delivery scan — last seen in transit", "EVD-4004"),
        ("Refund", "Not issued", "EVD-4008"),
    ],
    "events": [
        event("2026-08-06", "13:05", "Payment captured", "Transaction system", ["EVD-4001"], "₹22,000"),
        event("2026-08-06", "13:06", "Order created", "Order system", ["EVD-4002"], "ORD-729502"),
        event("2026-08-08", "11:25", "Order dispatched", "Fulfilment system", ["EVD-4003"], "AWB RL-330928114"),
        event("2026-08-09", "18:40", "Last courier scan", "Delivery system", ["EVD-4004"],
              "Departed Ernakulam hub — no further scans"),
        event("2026-08-13", "09:30", "Customer chased shipment", "Customer support", ["EVD-4006"],
              "Auto-acknowledgement only", actor="customer"),
        event("2026-08-14", "10:00", "Courier trace raised", "Fulfilment system", ["EVD-4013"],
              "Trace TR-88120 still open"),
        event("2026-08-17", "07:50", "Chargeback initiated", "Dispute system", [],
              "Reason: product not received", actor="issuer"),
    ],
    "gaps": [
        gap("Proof of delivery from the courier", "Mandatory artefact to contest a non-receipt claim.", 3.0),
        gap("Courier trace investigation report", "Would establish whether the parcel was lost in transit.", 2.5),
        gap("Recipient confirmation (signature or OTP)", "No recipient acknowledgement exists.", 1.5),
    ],
    "argument": (
        "The merchant can prove payment, order creation and dispatch, but the evidence chain stops at the "
        "regional hub. There is no delivery scan, no POD and no courier trace report. A representment filed "
        "today would not meet the network's evidentiary requirement, so the case should be held for a human "
        "decision pending the courier trace, and re-assessed if the POD arrives before the deadline."
    ),
})


# ── CASE 5 — unauthorised transaction with fraud signals ───────────────────
CASES.append({
    "dispute": {
        "dispute_id": "CB-2026-89105",
        "transaction_id": "TXN-930188", "order_id": "ORD-730044", "customer_id": "CUST-42610",
        "customer_name": "Vikram Rao", "customer_email": "vikram.rao@example.in",
        "reason": "Unauthorized transaction",
        "reason_code": "10.4 — Card-absent fraud",
        "network": "Mastercard", "amount": 31499,
        "created_at": "2026-08-15T20:10:00", "response_deadline": "2026-08-19T18:00:00",
        "status": "Needs review", "priority": "high",
        "claim": "I did not authorise this purchase and my card was in my possession.",
        "claim_detail": "Cardholder reports a card-absent purchase they did not make, shipped to an unknown address.",
    },
    "transaction": {
        "transaction_id": "TXN-930188", "order_id": "ORD-730044", "customer_id": "CUST-42610",
        "merchant_id": MERCHANT["merchant_id"], "amount": 31499, "currency": "INR",
        "payment_method": "Card • Axis Mastercard credit •••• 6690", "timestamp": "2026-08-11T02:47:00",
        "status": "captured", "auth_code": "M40XB1", "avs_match": False, "cvv_match": True,
        "three_ds": "Frictionless — not challenged",
    },
    "order": {
        "order_id": "ORD-730044", "customer_id": "CUST-42610",
        "product": "Flagship smartphone — 512 GB",
        "order_timestamp": "2026-08-11T02:48:00", "fulfillment_status": "fulfilled",
        "delivery_status": "delivered", "delivery_timestamp": "2026-08-12T17:05:00",
        "shipping_address": "Shop 3, Transit Road, Hyderabad 500003 (new address)",
        "courier": "Ekart", "awb": "EK-901223764",
    },
    "refunds": [],
    "interactions": [
        {"interaction_id": "INT-5905", "customer_id": "CUST-42610", "order_id": "ORD-730044",
         "timestamp": "2026-08-14T08:15:00", "channel": "Phone", "category": "fraud_report",
         "message": "Customer called to report an unrecognised order and requested cancellation."},
    ],
    "evidence": [
        ev("EVD-5001", "Payment authorisation", "payment", "Payment gateway", "2026-08-11T02:47:00",
           "Card-absent authorisation at 02:47 with an AVS mismatch and no 3-D Secure challenge.",
           "Authentication was frictionless and the billing address did not match.",
           "customer", "high", fields={"3-D Secure": "Frictionless, no challenge", "AVS": "Mismatch",
                                       "CVV": "Match", "Time": "02:47 local"}),
        ev("EVD-5002", "Device & session log", "customer", "Risk platform", "2026-08-11T02:41:00",
           "Order placed from a device and IP never previously seen on this account; account e-mail "
           "changed 20 minutes before checkout.",
           "Account takeover indicators are present around the transaction.",
           "customer", "high", fields={"Device": "New (Android, first seen)", "IP city": "Hyderabad",
                                       "Usual city": "Pune", "Email changed": "02:27 same night"}),
        ev("EVD-5003", "Order record", "order", "Order system", "2026-08-11T02:48:00",
           "Order shipped to a newly added address that had never been used on this account.",
           "Shipping address was created minutes before the order.",
           "customer", "high", fields={"Address age at order": "6 minutes",
                                       "Prior orders to address": "0"}),
        ev("EVD-5004", "Delivery record", "delivery", "Delivery system", "2026-08-12T17:05:00",
           "Delivered to the new address; recipient name recorded does not match the cardholder.",
           "Goods were delivered, but not to the cardholder.",
           "merchant", "medium", fields={"Received by": "\u201cS. Kumar\u201d", "Cardholder": "Vikram Rao"}),
        ev("EVD-5006", "Fraud report call", "communication", "Customer support", "2026-08-14T08:15:00",
           "Cardholder reported the order as unrecognised before the chargeback.",
           "Cardholder raised the alarm directly with the merchant first.",
           "customer", "medium", fields={"Channel": "Phone", "Outcome": "Order already delivered"}),
        ev("EVD-5008", "Refund ledger", "refund", "Refund system", None,
           "No refund issued.", "Funds remain with the merchant.",
           "customer", "low", fields={"Refunds found": "0"}),
        ev("EVD-5009", "Customer dispute history", "historical", "Dispute system", None,
           "No prior disputes; 14 successful orders over three years, all to the Pune address.",
           "Long clean history inconsistent with first-party misuse.",
           "customer", "medium", fields={"Prior disputes": "0", "Orders": "14", "Usual address": "Pune"}),
        ev("EVD-5010", "Policy reference", "policy", "Policy knowledge base", None,
           "Policy PL-045: card-absent fraud can only be contested with AVS match plus delivery to the "
           "cardholder's verified address, or a 3-D Secure liability shift.",
           "Neither rebuttal condition is met.",
           "neutral", "high", fields={"Policy": "PL-045 Card-absent fraud"}),
    ],
    "claim_vs_evidence": [
        ("Payment", "Captured — AVS mismatch, no 3DS challenge", "EVD-5001"),
        ("Device", "First-seen device, e-mail changed pre-checkout", "EVD-5002"),
        ("Order", "Shipped to a 6-minute-old address", "EVD-5003"),
        ("Delivery", "Delivered to a different recipient", "EVD-5004"),
        ("Customer history", "No prior disputes in 3 years", "EVD-5009"),
    ],
    "events": [
        event("2026-08-11", "02:27", "Account e-mail changed", "Risk platform", ["EVD-5002"],
              "From a first-seen device", actor="customer"),
        event("2026-08-11", "02:41", "New shipping address added", "Order system", ["EVD-5003"],
              "Never used before", actor="customer"),
        event("2026-08-11", "02:47", "Payment captured", "Transaction system", ["EVD-5001"],
              "₹31,499 — AVS mismatch"),
        event("2026-08-12", "17:05", "Order delivered", "Delivery system", ["EVD-5004"],
              "Received by \u201cS. Kumar\u201d"),
        event("2026-08-14", "08:15", "Cardholder reported fraud", "Customer support", ["EVD-5006"],
              "Order already delivered", actor="customer"),
        event("2026-08-15", "20:10", "Chargeback initiated", "Dispute system", [],
              "Reason: unauthorized transaction", actor="issuer"),
    ],
    "gaps": [
        gap("3-D Secure liability shift", "A challenged authentication would move liability to the issuer.", 2.0),
        gap("Delivery signature matching the cardholder", "Delivery was accepted by a different name.", 1.5),
    ],
    "argument": (
        "The authorisation carries an AVS mismatch with no 3-D Secure challenge, the order was placed at "
        "02:47 from a first-seen device minutes after the account e-mail was changed, and the goods went to "
        "an address created six minutes before checkout and accepted by someone other than the cardholder. "
        "This pattern points to account takeover rather than first-party misuse. Accept the dispute and "
        "raise a fraud review of the shipping address."
    ),
})


# ── CASE 6 — merchant error, order cancelled but charged ───────────────────
CASES.append({
    "dispute": {
        "dispute_id": "CB-2026-89106",
        "transaction_id": "TXN-930510", "order_id": "ORD-730288", "customer_id": "CUST-42988",
        "customer_name": "Sanya Kapoor", "customer_email": "sanya.kapoor@example.in",
        "reason": "Credit not processed",
        "reason_code": "13.6 — Credit not processed",
        "network": "Visa", "amount": 6999,
        "created_at": "2026-08-14T11:40:00", "response_deadline": "2026-08-19T18:00:00",
        "status": "Investigated", "priority": "medium",
        "claim": "The order was cancelled by the seller but I was still charged.",
        "claim_detail": "Cardholder states the merchant cancelled an out-of-stock order without refunding.",
    },
    "transaction": {
        "transaction_id": "TXN-930510", "order_id": "ORD-730288", "customer_id": "CUST-42988",
        "merchant_id": MERCHANT["merchant_id"], "amount": 6999, "currency": "INR",
        "payment_method": "Card • Kotak Visa debit •••• 1177", "timestamp": "2026-08-02T15:58:00",
        "status": "captured", "auth_code": "V55DQ0", "avs_match": True, "cvv_match": True,
        "three_ds": "Authenticated",
    },
    "order": {
        "order_id": "ORD-730288", "customer_id": "CUST-42988",
        "product": "Espresso machine — Model EM12",
        "order_timestamp": "2026-08-02T15:59:00", "fulfillment_status": "cancelled",
        "delivery_status": "not_applicable", "delivery_timestamp": None,
        "shipping_address": "31 Rose Lane, Pune 411001", "courier": None, "awb": None,
    },
    "refunds": [],
    "interactions": [
        {"interaction_id": "INT-6002", "customer_id": "CUST-42988", "order_id": "ORD-730288",
         "timestamp": "2026-08-05T09:12:00", "channel": "Email", "category": "cancellation_notice",
         "message": "Merchant notice: item out of stock, order cancelled, refund in 5–7 working days."},
        {"interaction_id": "INT-6009", "customer_id": "CUST-42988", "order_id": "ORD-730288",
         "timestamp": "2026-08-12T17:30:00", "channel": "Email", "category": "refund_chase",
         "message": "It has been a week and the refund has not arrived."},
    ],
    "evidence": [
        ev("EVD-6001", "Payment authorisation", "payment", "Payment gateway", "2026-08-02T15:58:00",
           "Payment of ₹6,999 captured.", "Payment captured and never reversed.",
           "customer", "high", fields={"Amount": "₹6,999", "Reversal": "None"}),
        ev("EVD-6002", "Order cancellation record", "order", "Order system", "2026-08-05T09:10:00",
           "Order cancelled by the merchant with reason 'stock unavailable'.",
           "Merchant cancelled the order; no goods were owed or shipped.",
           "customer", "high", fields={"Cancelled by": "Merchant ops", "Reason": "Stock unavailable"}),
        ev("EVD-6003", "Cancellation e-mail", "communication", "Customer support", "2026-08-05T09:12:00",
           "Merchant told the customer a refund would be issued within 5–7 working days.",
           "Merchant committed in writing to a refund.",
           "customer", "high", fields={"Promise": "Refund in 5–7 working days"}),
        ev("EVD-6004", "Refund ledger", "refund", "Refund system", None,
           "A refund of ₹6,999 was created on 6 Aug but failed at the gateway and was never retried.",
           "The promised refund failed and was not re-attempted.",
           "customer", "high", availability="partial",
           fields={"Refund ID": "RFN-30122", "Status": "Failed", "Gateway error": "Card token expired",
                   "Retries": "0"}),
        ev("EVD-6006", "Refund chase e-mail", "communication", "Customer support", "2026-08-12T17:30:00",
           "Customer chased the refund; ticket auto-closed without a response.",
           "The customer escalated and received no remedy.",
           "customer", "medium", fields={"Ticket": "TCK-77120", "Closure": "Auto-closed, no reply"}),
        ev("EVD-6008", "Fulfilment record", "fulfillment", "Fulfilment system", None,
           "No pick, pack or dispatch activity exists for this order.",
           "Nothing was ever shipped.",
           "customer", "medium", fields={"Dispatch": "None"}),
        ev("EVD-6010", "Customer dispute history", "historical", "Dispute system", None,
           "No prior disputes.", "Clean customer history.",
           "customer", "low", fields={"Prior disputes": "0"}),
        ev("EVD-6011", "Policy reference", "policy", "Policy knowledge base", None,
           "Policy PL-052: where a merchant-initiated cancellation is recorded, the credit must be issued "
           "before the dispute window closes.",
           "Internal policy required the credit that was never completed.",
           "neutral", "medium", fields={"Policy": "PL-052 Credit not processed"}),
    ],
    "claim_vs_evidence": [
        ("Payment", "Captured", "EVD-6001"),
        ("Order", "Cancelled by merchant", "EVD-6002"),
        ("Fulfillment", "Nothing dispatched", "EVD-6008"),
        ("Refund", "Created 6 Aug, failed, never retried", "EVD-6004"),
        ("Customer communication", "Refund promised, then chased", "EVD-6003"),
    ],
    "events": [
        event("2026-08-02", "15:58", "Payment captured", "Transaction system", ["EVD-6001"], "₹6,999"),
        event("2026-08-05", "09:10", "Order cancelled by merchant", "Order system", ["EVD-6002"],
              "Stock unavailable"),
        event("2026-08-05", "09:12", "Refund promised to customer", "Customer support", ["EVD-6003"],
              "5–7 working days"),
        event("2026-08-06", "12:00", "Refund attempt failed", "Refund system", ["EVD-6004"],
              "Card token expired — no retry"),
        event("2026-08-12", "17:30", "Customer chased refund", "Customer support", ["EVD-6006"],
              "Ticket auto-closed", actor="customer"),
        event("2026-08-14", "11:40", "Chargeback initiated", "Dispute system", [],
              "Reason: credit not processed", actor="issuer"),
    ],
    "gaps": [
        gap("Evidence of a refund retry", "No second attempt was made after the gateway failure.", 1.5),
        gap("Response to the customer's refund chase", "The ticket was closed without a reply.", 1.0),
    ],
    "argument": (
        "This is a merchant-side processing failure. The order was cancelled by the merchant, nothing was "
        "dispatched, a refund was promised in writing and the single refund attempt failed on an expired card "
        "token with no retry. The dispute should be accepted and the credit reconciled so the customer is "
        "not credited twice."
    ),
})


# ── CASE 7 — partial refund dispute ────────────────────────────────────────
CASES.append({
    "dispute": {
        "dispute_id": "CB-2026-89107",
        "transaction_id": "TXN-930977", "order_id": "ORD-730611", "customer_id": "CUST-43301",
        "customer_name": "Kabir Menon", "customer_email": "kabir.menon@example.in",
        "reason": "Partial refund not received",
        "reason_code": "13.6 — Credit not processed",
        "network": "Mastercard", "amount": 9600,
        "created_at": "2026-08-16T15:25:00", "response_deadline": "2026-08-23T18:00:00",
        "status": "Investigated", "priority": "low",
        "claim": "I returned two of the three items and was refunded far less than I should have been.",
        "claim_detail": "Cardholder disputes the full order value after a partial return was credited.",
    },
    "transaction": {
        "transaction_id": "TXN-930977", "order_id": "ORD-730611", "customer_id": "CUST-43301",
        "merchant_id": MERCHANT["merchant_id"], "amount": 9600, "currency": "INR",
        "payment_method": "Card • HDFC Mastercard credit •••• 3390", "timestamp": "2026-07-28T12:10:00",
        "status": "captured", "auth_code": "M62NN7", "avs_match": True, "cvv_match": True,
        "three_ds": "Authenticated",
    },
    "order": {
        "order_id": "ORD-730611", "customer_id": "CUST-43301",
        "product": "Cookware set (3 items) — CW Series",
        "order_timestamp": "2026-07-28T12:11:00", "fulfillment_status": "fulfilled",
        "delivery_status": "delivered", "delivery_timestamp": "2026-07-31T11:15:00",
        "shipping_address": "5 Palm Court, Chennai 600028", "courier": "BlueDart", "awb": "BD-880114523",
    },
    "refunds": [
        {"refund_id": "RFN-30455", "transaction_id": "TXN-930977", "amount": 4600,
         "timestamp": "2026-08-09T10:20:00", "status": "processed",
         "reason": "Return of 2 of 3 items (received & inspected)"},
    ],
    "interactions": [
        {"interaction_id": "INT-6110", "customer_id": "CUST-43301", "order_id": "ORD-730611",
         "timestamp": "2026-08-10T18:00:00", "channel": "Email", "category": "refund_amount_query",
         "message": "I expected ₹6,400 back, not ₹4,600. Why was a restocking fee applied?"},
    ],
    "evidence": [
        ev("EVD-7001", "Payment authorisation", "payment", "Payment gateway", "2026-07-28T12:10:00",
           "Payment of ₹9,600 captured for a three-item order.", "Full order value was captured once.",
           "merchant", "high", fields={"Amount": "₹9,600", "Items": "3"}),
        ev("EVD-7002", "Delivery record", "delivery", "Delivery system", "2026-07-31T11:15:00",
           "All three items delivered and OTP verified.", "The full order was received by the customer.",
           "merchant", "high", fields={"OTP": "Verified", "Items delivered": "3 of 3"}),
        ev("EVD-7003", "Return inspection report", "fulfillment", "Fulfilment system", "2026-08-07T14:30:00",
           "Two items returned; one item retained by the customer and confirmed in use.",
           "Only two of three items came back to the warehouse.",
           "merchant", "high", fields={"Returned": "2 items", "Retained": "1 item (CW-SKILLET)",
                                       "Condition": "Opened, resaleable"}),
        ev("EVD-7004", "Refund record", "refund", "Refund system", "2026-08-09T10:20:00",
           "Refund RFN-30455 of ₹4,600 processed for the two returned items less a ₹1,800 restocking fee.",
           "A partial credit was issued and settled to the card.",
           "merchant", "high", fields={"Refund": "₹4,600", "Item value": "₹6,400",
                                       "Restocking fee": "₹1,800", "Settled": "9 Aug 2026"}),
        ev("EVD-7005", "Refund amount query", "communication", "Customer support", "2026-08-10T18:00:00",
           "Customer questioned the restocking deduction; merchant did not reply before the dispute.",
           "The deduction was disputed by the customer and left unanswered.",
           "customer", "medium", fields={"Expected": "₹6,400", "Received": "₹4,600", "Reply": "None"}),
        ev("EVD-7006", "Returns policy acceptance", "policy", "Policy knowledge base", "2026-07-28T12:11:00",
           "Checkout captured acceptance of the returns policy including a restocking fee on opened items.",
           "Restocking terms were shown and accepted at checkout.",
           "merchant", "medium", fields={"Policy": "PL-067 Returns & restocking",
                                         "Accepted at": "28 Jul 2026, 12:11", "Version": "v4.2"}),
        ev("EVD-7008", "Customer dispute history", "historical", "Dispute system", None,
           "One prior partial-refund dispute in the last 12 months, closed in the customer's favour.",
           "Repeat pattern of partial-refund disputes on this profile.",
           "neutral", "medium", fields={"Prior disputes": "1", "Outcome": "Customer favour"}),
        ev("EVD-7010", "Dispute amount reconciliation", "payment", "Dispute system", "2026-08-16T15:25:00",
           "Dispute was raised for ₹9,600 although ₹4,600 had already been credited on 9 Aug.",
           "The disputed amount overstates the customer's exposure by the credit already issued.",
           "merchant", "high", fields={"Disputed": "₹9,600", "Already credited": "₹4,600",
                                       "Net exposure": "₹5,000"}) | {
               "mismatch": {
                   "severity": "high",
                   "summary": "The disputed amount does not reconcile with the credit already issued.",
                   "why": (
                       "₹4,600 settled to the cardholder on 9 August, so ₹9,600 overstates the amount at "
                       "risk by that credit. The reconciliation is the strongest element of a representment."
                   )}},
        ev("EVD-7011", "Restocking fee disclosure at item level", "policy", "Policy knowledge base", None,
           "Item-level fee disclosure on the product page could not be reproduced for the July catalogue version.",
           "Item-level disclosure of the fee is unavailable.",
           "neutral", "low", availability="unavailable", fields={"Catalogue snapshot": "Not retained"}),
    ],
    "claim_vs_evidence": [
        ("Payment", "₹9,600 captured", "EVD-7001"),
        ("Delivery", "3 of 3 items delivered", "EVD-7002"),
        ("Return", "2 items returned, 1 retained", "EVD-7003"),
        ("Refund", "₹4,600 already credited", "EVD-7004"),
        ("Dispute amount", "₹9,600 disputed vs ₹5,000 net exposure", "EVD-7010"),
    ],
    "events": [
        event("2026-07-28", "12:10", "Payment captured", "Transaction system", ["EVD-7001"], "₹9,600"),
        event("2026-07-31", "11:15", "Order delivered", "Delivery system", ["EVD-7002"], "3 of 3 items"),
        event("2026-08-07", "14:30", "Return received and inspected", "Fulfilment system", ["EVD-7003"],
              "2 items returned, 1 retained"),
        event("2026-08-09", "10:20", "Partial refund processed", "Refund system", ["EVD-7004"],
              "₹4,600 credited"),
        event("2026-08-10", "18:00", "Customer queried refund amount", "Customer support", ["EVD-7005"],
              "Expected ₹6,400", actor="customer"),
        event("2026-08-16", "15:25", "Chargeback initiated", "Dispute system", ["EVD-7010"],
              "Raised for the full ₹9,600", actor="issuer"),
    ],
    "gaps": [
        gap("Item-level restocking fee disclosure", "Would strengthen the basis for the ₹1,800 deduction.", 1.5),
        gap("Merchant reply to the refund query", "No response was sent before the dispute was raised.", 1.0),
    ],
    "argument": (
        "Delivery of all three items is proven, only two were returned, and ₹4,600 has already been credited "
        "against the disputed ₹9,600. The chargeback therefore double-counts a credit that has settled. "
        "Contest on the reconciliation and the accepted returns policy, while acknowledging that the "
        "₹1,800 restocking deduction is the weaker element and may be conceded to close the case."
    ),
})


# ── CASE 8 — non-receipt with airtight delivery evidence, no contradiction ─
CASES.append({
    "dispute": {
        "dispute_id": "CB-2026-89108",
        "transaction_id": "TXN-931204", "order_id": "ORD-730902", "customer_id": "CUST-43744",
        "customer_name": "Ishaan Gupta", "customer_email": "ishaan.gupta@example.in",
        "reason": "Product not received",
        "reason_code": "13.1 — Merchandise / services not received",
        "network": "Visa", "amount": 12200,
        "created_at": "2026-08-17T10:05:00", "response_deadline": "2026-08-19T12:00:00",
        "status": "Needs review", "priority": "high",
        "claim": "The parcel was never delivered to me.",
        "claim_detail": "Cardholder denies receipt of a consignment recorded as delivered with OTP and signature.",
    },
    "transaction": {
        "transaction_id": "TXN-931204", "order_id": "ORD-730902", "customer_id": "CUST-43744",
        "merchant_id": MERCHANT["merchant_id"], "amount": 12200, "currency": "INR",
        "payment_method": "Card • Yes Bank Visa credit •••• 5521", "timestamp": "2026-08-08T09:02:00",
        "status": "captured", "auth_code": "V88RT3", "avs_match": True, "cvv_match": True,
        "three_ds": "Authenticated",
    },
    "order": {
        "order_id": "ORD-730902", "customer_id": "CUST-43744",
        "product": "Air purifier — Model AP40",
        "order_timestamp": "2026-08-08T09:03:00", "fulfillment_status": "fulfilled",
        "delivery_status": "delivered", "delivery_timestamp": "2026-08-11T14:22:00",
        "shipping_address": "Flat 7B, Green Meadows, Gurugram 122002", "courier": "BlueDart",
        "awb": "BD-902337411",
    },
    "refunds": [],
    "interactions": [
        {"interaction_id": "INT-6220", "customer_id": "CUST-43744", "order_id": "ORD-730902",
         "timestamp": "2026-08-11T14:40:00", "channel": "App", "category": "delivery_feedback",
         "message": "Customer rated the delivery 5 stars in the app 18 minutes after the delivery scan."},
    ],
    "evidence": [
        ev("EVD-8001", "Payment authorisation", "payment", "Payment gateway", "2026-08-08T09:02:00",
           "Payment of ₹12,200 authorised and captured with 3-D Secure.",
           "Payment captured with a full liability shift.",
           "merchant", "high", fields={"3-D Secure": "Authenticated", "AVS": "Match", "CVV": "Match"}),
        ev("EVD-8002", "Order record", "order", "Order system", "2026-08-08T09:03:00",
           "Order created for the cardholder's long-standing default address.",
           "Shipping address has been used on six previous delivered orders.",
           "merchant", "medium", fields={"Address age": "3 years", "Prior deliveries here": "6"}),
        ev("EVD-8003", "Dispatch manifest", "fulfillment", "Fulfilment system", "2026-08-09T07:55:00",
           "Consignment dispatched via BlueDart, AWB BD-902337411.", "Dispatch recorded next morning.",
           "merchant", "medium", fields={"Courier": "BlueDart", "AWB": "BD-902337411"}),
        ev("EVD-8004", "Delivery record with OTP", "delivery", "Delivery system", "2026-08-11T14:22:00",
           "Delivered with a one-time password verified against the cardholder's registered mobile.",
           "Delivery was OTP-verified to the cardholder's own phone number.",
           "merchant", "high", fields={"OTP": "Verified", "Mobile": "•••• 3312 (registered)",
                                       "Geo-stamp": "28.4595° N, 77.0266° E"}),
        ev("EVD-8005", "Signed proof of delivery", "delivery", "Delivery system", "2026-08-11T14:23:00",
           "Digital signature captured at the door, name recorded as I. Gupta.",
           "Signed POD matches the cardholder's name.",
           "merchant", "high", fields={"Signature": "Captured", "Name": "I. Gupta",
                                       "Photo": "Doorstep photo on file"}),
        ev("EVD-8007", "In-app delivery rating", "customer", "Customer activity", "2026-08-11T14:40:00",
           "Customer submitted a 5-star delivery rating 18 minutes after the delivery scan.",
           "Customer positively acknowledged the delivery in-app.",
           "merchant", "high", fields={"Rating": "5 stars", "Session": "SES-99841",
                                       "Device": "Registered device"}),
        ev("EVD-8009", "Refund ledger", "refund", "Refund system", None,
           "No refund or credit issued.", "No duplicate credit exists.",
           "merchant", "low", fields={"Refunds found": "0"}),
        ev("EVD-8010", "Customer dispute history", "historical", "Dispute system", None,
           "Three non-receipt disputes raised on this profile in 11 months across different merchants "
           "recorded in the shared network report.",
           "A repeated non-receipt pattern is present on this profile.",
           "merchant", "medium", fields={"Prior non-receipt disputes": "3", "Window": "11 months"}),
        ev("EVD-8011", "Policy reference", "policy", "Policy knowledge base", None,
           "Policy PL-013: OTP-verified delivery plus signed POD satisfies the non-receipt rebuttal standard.",
           "The available artefacts meet the network's rebuttal standard in full.",
           "neutral", "high", fields={"Policy": "PL-013 Non-receipt disputes"}),
    ],
    "claim_vs_evidence": [
        ("Payment", "Captured, 3-D Secure authenticated", "EVD-8001"),
        ("Order", "Shipped to a 3-year-old default address", "EVD-8002"),
        ("Delivery", "OTP verified to the registered mobile", "EVD-8004"),
        ("Proof of delivery", "Signed, name matches cardholder", "EVD-8005"),
        ("Customer activity", "5-star delivery rating 18 minutes later", "EVD-8007"),
    ],
    "events": [
        event("2026-08-08", "09:02", "Payment captured", "Transaction system", ["EVD-8001"], "₹12,200"),
        event("2026-08-08", "09:03", "Order created", "Order system", ["EVD-8002"], "Default address"),
        event("2026-08-09", "07:55", "Order dispatched", "Fulfilment system", ["EVD-8003"], "AWB BD-902337411"),
        event("2026-08-11", "14:22", "Order delivered — OTP verified", "Delivery system", ["EVD-8004"],
              "OTP sent to registered mobile"),
        event("2026-08-11", "14:23", "Signed POD captured", "Delivery system", ["EVD-8005"], "Signed I. Gupta"),
        event("2026-08-11", "14:40", "Customer rated delivery 5 stars", "Customer activity", ["EVD-8007"],
              "In-app, registered device", actor="customer"),
        event("2026-08-17", "10:05", "Chargeback initiated", "Dispute system", [],
              "Reason: product not received", actor="issuer"),
    ],
    "gaps": [
        gap("Post-delivery support contact", "No conversation with the customer exists before the dispute.", 0.8,
            "Not available"),
    ],
    "argument": (
        "Delivery was verified by a one-time password sent to the cardholder's registered mobile, a signed "
        "proof of delivery in the cardholder's name and a doorstep photograph, and the customer rated the "
        "delivery five stars from a registered device eighteen minutes later. The address has received six "
        "previous orders. The evidence meets the network rebuttal standard for non-receipt in full."
    ),
})


# ── CASE 9 — duplicate processing ──────────────────────────────────────────
CASES.append({
    "dispute": {
        "dispute_id": "CB-2026-89109",
        "transaction_id": "TXN-931688", "order_id": "ORD-731255", "customer_id": "CUST-44012",
        "customer_name": "Priya Deshmukh", "customer_email": "priya.deshmukh@example.in",
        "reason": "Duplicate processing",
        "reason_code": "12.6 — Duplicate processing",
        "network": "Visa", "amount": 48000,
        "created_at": "2026-08-15T12:00:00", "response_deadline": "2026-08-20T12:00:00",
        "status": "Investigated", "priority": "medium",
        "claim": "I was charged twice for the same order.",
        "claim_detail": "Cardholder reports two identical charges for one order placed on the same day.",
    },
    "transaction": {
        "transaction_id": "TXN-931688", "order_id": "ORD-731255", "customer_id": "CUST-44012",
        "merchant_id": MERCHANT["merchant_id"], "amount": 48000, "currency": "INR",
        "payment_method": "Card • HDFC Visa credit •••• 7712", "timestamp": "2026-08-03T19:41:00",
        "status": "captured", "auth_code": "V90KK5", "avs_match": True, "cvv_match": True,
        "three_ds": "Authenticated",
    },
    "order": {
        "order_id": "ORD-731255", "customer_id": "CUST-44012",
        "product": "55-inch 4K television — Model TV55U",
        "order_timestamp": "2026-08-03T19:39:00", "fulfillment_status": "fulfilled",
        "delivery_status": "delivered", "delivery_timestamp": "2026-08-07T13:10:00",
        "shipping_address": "12 Hill Road, Nagpur 440010", "courier": "SafeExpress", "awb": "SE-771093300",
    },
    "refunds": [],
    "interactions": [
        {"interaction_id": "INT-6301", "customer_id": "CUST-44012", "order_id": "ORD-731255",
         "timestamp": "2026-08-04T08:20:00", "channel": "Chat", "category": "duplicate_charge",
         "message": "Two charges of ₹48,000 appear on my statement for one TV."},
    ],
    "evidence": [
        ev("EVD-9001", "Authorisation history", "payment", "Payment gateway", "2026-08-03T19:39:00",
           "First authorisation TXN-931684 at 19:39 failed with issuer response 'do not honour' and was voided.",
           "The first attempt never settled; only one capture exists.",
           "merchant", "high", fields={"TXN-931684": "Failed / voided", "Settled": "No"}),
        ev("EVD-9002", "Payment authorisation", "payment", "Payment gateway", "2026-08-03T19:41:00",
           "Second attempt TXN-931688 authorised and captured for ₹48,000.",
           "Exactly one successful capture is present for this order.",
           "merchant", "high", fields={"Captured": "₹48,000", "Settlement batch": "BATCH-08-04A"}),
        ev("EVD-9003", "Settlement report", "payment", "Payment gateway", "2026-08-04T02:00:00",
           "Settlement file for 4 Aug contains a single ₹48,000 entry for this order.",
           "Merchant received the amount once.",
           "merchant", "high", fields={"Entries for order": "1", "Amount settled": "₹48,000"}),
        ev("EVD-9004", "Order record", "order", "Order system", "2026-08-03T19:39:00",
           "A single order exists; no duplicate order record was created.",
           "One order, one fulfilment.",
           "merchant", "medium", fields={"Orders for customer that day": "1"}),
        ev("EVD-9005", "Delivery record", "delivery", "Delivery system", "2026-08-07T13:10:00",
           "One television delivered and installed; installation sheet signed.",
           "A single unit was delivered.",
           "merchant", "medium", fields={"Units": "1", "Installation": "Completed"}),
        ev("EVD-9006", "Support chat transcript", "communication", "Customer support", "2026-08-04T08:20:00",
           "Support explained that the first authorisation was a hold that would drop off in 5–7 days.",
           "The customer was informed of the pending authorisation hold.",
           "merchant", "medium", fields={"Explanation given": "Yes", "Hold release quoted": "5–7 days"}),
        ev("EVD-9007", "Issuer hold release confirmation", "payment", "Payment gateway", None,
           "Confirmation that the issuer released the failed authorisation hold could not be retrieved.",
           "Whether the hold visibly dropped off the cardholder's statement is unknown.",
           "neutral", "medium", availability="unavailable", fields={"Issuer file": "Not received"}),
        ev("EVD-9009", "Customer dispute history", "historical", "Dispute system", None,
           "No prior disputes.", "Clean history; likely a genuine statement misreading.",
           "neutral", "low", fields={"Prior disputes": "0"}),
        ev("EVD-9010", "Policy reference", "policy", "Policy knowledge base", None,
           "Policy PL-071: duplicate-processing disputes are rebutted with the settlement report showing a "
           "single capture.",
           "The settlement report is the required artefact and it is available.",
           "neutral", "medium", fields={"Policy": "PL-071 Duplicate processing"}),
    ],
    "claim_vs_evidence": [
        ("First attempt", "Failed and voided — never settled", "EVD-9001"),
        ("Capture", "One capture of ₹48,000", "EVD-9002"),
        ("Settlement", "Single entry in the 4 Aug file", "EVD-9003"),
        ("Order", "One order, one unit delivered", "EVD-9005"),
        ("Customer communication", "Hold explained on 4 Aug", "EVD-9006"),
    ],
    "events": [
        event("2026-08-03", "19:39", "First authorisation failed", "Transaction system", ["EVD-9001"],
              "Do not honour — voided"),
        event("2026-08-03", "19:41", "Payment captured", "Transaction system", ["EVD-9002"], "₹48,000"),
        event("2026-08-04", "02:00", "Settlement file generated", "Transaction system", ["EVD-9003"],
              "Single entry for this order"),
        event("2026-08-04", "08:20", "Customer reported duplicate charge", "Customer support", ["EVD-9006"],
              "Authorisation hold explained", actor="customer"),
        event("2026-08-07", "13:10", "Television delivered and installed", "Delivery system", ["EVD-9005"],
              "Installation sheet signed"),
        event("2026-08-15", "12:00", "Chargeback initiated", "Dispute system", [],
              "Reason: duplicate processing", actor="issuer"),
    ],
    "gaps": [
        gap("Issuer confirmation that the authorisation hold was released",
            "Would show the second amount left the cardholder's statement.", 1.2),
    ],
    "argument": (
        "The gateway records two authorisation attempts but only one capture: the 19:39 attempt was declined "
        "and voided, and the 19:41 attempt settled once in the 4 August file. One order was created, one "
        "television was delivered and installed, and support explained the pending hold to the customer the "
        "next morning. The settlement report meets the rebuttal standard for duplicate processing."
    ),
})


# ── CASE 10 — cancelled subscription still billed ──────────────────────────
CASES.append({
    "dispute": {
        "dispute_id": "CB-2026-89110",
        "transaction_id": "TXN-932011", "order_id": "ORD-731490", "customer_id": "CUST-44398",
        "customer_name": "Neha Bansal", "customer_email": "neha.bansal@example.in",
        "reason": "Cancelled recurring transaction",
        "reason_code": "13.2 — Cancelled recurring",
        "network": "Mastercard", "amount": 18400,
        "created_at": "2026-08-16T18:30:00", "response_deadline": "2026-08-24T18:00:00",
        "status": "Needs review", "priority": "low",
        "claim": "I cancelled the annual plan before renewal but was charged anyway.",
        "claim_detail": "Cardholder states an annual care plan was cancelled in-app before the renewal date.",
    },
    "transaction": {
        "transaction_id": "TXN-932011", "order_id": "ORD-731490", "customer_id": "CUST-44398",
        "merchant_id": MERCHANT["merchant_id"], "amount": 18400, "currency": "INR",
        "payment_method": "Card on file • Mastercard •••• 4408", "timestamp": "2026-08-10T00:05:00",
        "status": "captured", "auth_code": "M31YY2", "avs_match": True, "cvv_match": None,
        "three_ds": "Merchant-initiated transaction",
    },
    "order": {
        "order_id": "ORD-731490", "customer_id": "CUST-44398",
        "product": "Northline Care — annual protection plan renewal",
        "order_timestamp": "2026-08-10T00:05:00", "fulfillment_status": "active_service",
        "delivery_status": "not_applicable", "delivery_timestamp": None,
        "shipping_address": "Digital service — no shipment", "courier": None, "awb": None,
    },
    "refunds": [],
    "interactions": [
        {"interaction_id": "INT-6402", "customer_id": "CUST-44398", "order_id": "ORD-731490",
         "timestamp": "2026-08-09T21:12:00", "channel": "App", "category": "cancellation_attempt",
         "message": "Customer opened the plan management screen and tapped 'Cancel plan'."},
        {"interaction_id": "INT-6409", "customer_id": "CUST-44398", "order_id": "ORD-731490",
         "timestamp": "2026-08-10T09:40:00", "channel": "Email", "category": "billing_dispute",
         "message": "I cancelled last night and was still billed at midnight."},
    ],
    "evidence": [
        ev("EVD-1101", "Recurring billing record", "payment", "Payment gateway", "2026-08-10T00:05:00",
           "Merchant-initiated renewal of ₹18,400 charged against the stored credential.",
           "Renewal was charged on the scheduled date.",
           "merchant", "high", fields={"Type": "MIT recurring", "Mandate": "MND-55210"}),
        ev("EVD-1102", "Subscription state log", "order", "Order system", "2026-08-09T21:12:00",
           "Cancellation flow was started at 21:12 but the state remained 'active' — the confirmation step "
           "was never completed.",
           "A cancellation attempt is recorded but never finalised in the subscription state.",
           "neutral", "high", availability="partial",
           fields={"Flow started": "9 Aug 21:12", "Confirmation": "Not recorded",
                   "State at renewal": "Active"}),
        ev("EVD-1103", "App session trace", "customer", "Customer activity", "2026-08-09T21:12:00",
           "Session shows the 'Cancel plan' tap followed by an app crash 4 seconds later.",
           "The customer's cancellation attempt was interrupted by a client error.",
           "customer", "high", fields={"Event": "cancel_plan_tap", "Next event": "app_crash (+4s)",
                                       "App version": "8.1.3"}) | {
               "conflicts_with": ["EVD-1102"],
               "conflict_severity": "medium",
               "conflict_summary": "The subscription state and the customer's session trace disagree.",
               "conflict_why": (
                   "Billing systems saw an active plan while the customer's device recorded a cancellation "
                   "attempt that a client crash prevented from completing. Neither record is conclusive on "
                   "its own."
               )},
        ev("EVD-1104", "Renewal reminder e-mail", "communication", "Customer support", "2026-08-03T10:00:00",
           "Renewal reminder sent seven days before the charge, as required.",
           "Advance notice of the renewal was given.",
           "merchant", "medium", fields={"Sent": "3 Aug 2026", "Opened": "Yes, 3 Aug"}),
        ev("EVD-1105", "Billing dispute e-mail", "communication", "Customer support", "2026-08-10T09:40:00",
           "Customer reported the charge the morning after the renewal.",
           "Customer objected immediately after being billed.",
           "customer", "medium", fields={"Sent": "10 Aug 09:40", "Merchant reply": "Standard policy reply"}),
        ev("EVD-1106", "Service usage log", "fulfillment", "Fulfilment system", None,
           "No claims, service visits or plan benefits were used in the renewed term.",
           "The customer has drawn no benefit from the renewed plan.",
           "customer", "medium", fields={"Usage since renewal": "None"}),
        ev("EVD-1107", "Refund ledger", "refund", "Refund system", None,
           "No refund or pro-rata credit issued.", "The renewal amount is still held by the merchant.",
           "customer", "medium", fields={"Refunds found": "0"}),
        ev("EVD-1108", "Customer dispute history", "historical", "Dispute system", None,
           "No prior disputes across four years of subscription billing.", "Clean long-term customer.",
           "customer", "low", fields={"Prior disputes": "0", "Tenure": "4 years"}),
        ev("EVD-1109", "Policy reference", "policy", "Policy knowledge base", None,
           "Policy PL-029: a cancellation is effective when the customer completes the documented "
           "cancellation flow; incomplete flows are reviewed case by case.",
           "Policy places this scenario in the discretionary review band.",
           "neutral", "medium", fields={"Policy": "PL-029 Recurring cancellations"}),
        ev("EVD-1110", "Cancellation confirmation record", "order", "Order system", None,
           "No cancellation confirmation e-mail or in-app receipt was generated.",
           "There is no confirmation artefact either way.",
           "neutral", "medium", availability="unavailable", fields={"Confirmation": "None generated"}),
    ],
    "claim_vs_evidence": [
        ("Renewal charge", "₹18,400 charged 10 Aug 00:05", "EVD-1101"),
        ("Subscription state", "Still active at renewal — flow not completed", "EVD-1102"),
        ("Customer activity", "Cancel tapped 21:12, app crashed 4s later", "EVD-1103"),
        ("Service usage", "No benefits used since renewal", "EVD-1106"),
        ("Refund", "Not issued", "EVD-1107"),
    ],
    "events": [
        event("2026-08-03", "10:00", "Renewal reminder sent", "Customer support", ["EVD-1104"], "7 days notice"),
        event("2026-08-09", "21:12", "Customer tapped 'Cancel plan'", "Customer activity", ["EVD-1103"],
              "App crashed 4 seconds later", actor="customer"),
        event("2026-08-10", "00:05", "Renewal charged", "Transaction system", ["EVD-1101"], "₹18,400 MIT"),
        event("2026-08-10", "09:40", "Customer disputed the charge with support", "Customer support",
              ["EVD-1105"], "Standard policy reply sent", actor="customer"),
        event("2026-08-16", "18:30", "Chargeback initiated", "Dispute system", [],
              "Reason: cancelled recurring", actor="issuer"),
    ],
    "gaps": [
        gap("Cancellation confirmation record", "No confirmation artefact exists for either party.", 1.5),
        gap("Client crash report for the 9 Aug session",
            "Would confirm whether the failure was merchant-side.", 1.5),
    ],
    "argument": (
        "The renewal was properly noticed and charged against a valid mandate while the subscription state "
        "was still active, so the charge was technically correct. However the customer's session trace shows "
        "a cancellation tap four seconds before an app crash, no confirmation artefact was generated and no "
        "plan benefits have been used. The technical position favours the merchant while the customer "
        "experience evidence does not; this needs an operator decision on goodwill."
    ),
})


# ── CASE 11 & 12 — additional open cases (lighter, still distinct) ─────────
CASES.append({
    "dispute": {
        "dispute_id": "CB-2026-89111",
        "transaction_id": "TXN-932455", "order_id": "ORD-731820", "customer_id": "CUST-44701",
        "customer_name": "Arjun Pillai", "customer_email": "arjun.pillai@example.in",
        "reason": "Product not received",
        "reason_code": "13.1 — Merchandise / services not received",
        "network": "Visa", "amount": 57300,
        "created_at": "2026-08-18T06:20:00", "response_deadline": "2026-08-18T20:00:00",
        "status": "Needs review", "priority": "high",
        "claim": "The high-value item was marked delivered but left with a neighbour I do not know.",
        "claim_detail": "Cardholder states the parcel was handed to a third party without authorisation.",
    },
    "transaction": {
        "transaction_id": "TXN-932455", "order_id": "ORD-731820", "customer_id": "CUST-44701",
        "merchant_id": MERCHANT["merchant_id"], "amount": 57300, "currency": "INR",
        "payment_method": "Card • Amex •••• 1008", "timestamp": "2026-08-09T11:14:00",
        "status": "captured", "auth_code": "A12WQ6", "avs_match": True, "cvv_match": True,
        "three_ds": "Authenticated",
    },
    "order": {
        "order_id": "ORD-731820", "customer_id": "CUST-44701",
        "product": "Professional camera body — Model PX9",
        "order_timestamp": "2026-08-09T11:15:00", "fulfillment_status": "fulfilled",
        "delivery_status": "delivered", "delivery_timestamp": "2026-08-13T16:30:00",
        "shipping_address": "Apt 902, Sea Breeze Towers, Mumbai 400050", "courier": "BlueDart",
        "awb": "BD-913402288",
    },
    "refunds": [],
    "interactions": [
        {"interaction_id": "INT-6510", "customer_id": "CUST-44701", "order_id": "ORD-731820",
         "timestamp": "2026-08-13T20:05:00", "channel": "Email", "category": "delivery_issue",
         "message": "Courier says it was left at flat 903. Nobody there is returning it."},
    ],
    "evidence": [
        ev("EVD-1201", "Payment authorisation", "payment", "Payment gateway", "2026-08-09T11:14:00",
           "Payment of ₹57,300 authorised and captured.", "Payment captured with 3-D Secure.",
           "merchant", "high", fields={"3-D Secure": "Authenticated", "Amount": "₹57,300"}),
        ev("EVD-1202", "Dispatch manifest", "fulfillment", "Fulfilment system", "2026-08-10T08:30:00",
           "High-value consignment dispatched with tamper-evident packaging.",
           "Dispatch is fully documented.",
           "merchant", "medium", fields={"Courier": "BlueDart", "Handling": "High value"}),
        ev("EVD-1203", "Delivery record", "delivery", "Delivery system", "2026-08-13T16:30:00",
           "Delivered and signed at flat 903 — the shipping address on the order is flat 902.",
           "The delivery scan records a different flat number from the order.",
           "customer", "high", fields={"Delivered to": "Flat 903", "Order address": "Apt 902",
                                       "Signature": "Illegible"}) | {
               "mismatch": {
                   "severity": "high",
                   "summary": "The delivery scan address differs from the order shipping address.",
                   "why": (
                       "A consignment signed for at a different flat, with an illegible signature and no OTP, "
                       "does not evidence delivery to the cardholder."
                   )}},
        ev("EVD-1204", "High-value delivery protocol", "policy", "Policy knowledge base", None,
           "Policy PL-058: consignments above ₹25,000 require OTP verification with the named recipient.",
           "Required OTP verification was not performed for this consignment.",
           "customer", "high", fields={"Policy": "PL-058 High-value delivery", "OTP required": "Yes",
                                       "OTP captured": "No"}),
        ev("EVD-1205", "Support email", "communication", "Customer support", "2026-08-13T20:05:00",
           "Customer reported the misdelivery within four hours of the scan.",
           "Prompt and specific report of misdelivery.",
           "customer", "medium", fields={"Reported": "13 Aug 20:05", "Recovery attempt": "None logged"}),
        ev("EVD-1207", "Refund ledger", "refund", "Refund system", None, "No refund issued.",
           "No credit has been returned.", "customer", "low", fields={"Refunds found": "0"}),
        ev("EVD-1208", "Customer dispute history", "historical", "Dispute system", None,
           "No prior disputes in five years.", "Clean long-term customer.",
           "customer", "low", fields={"Prior disputes": "0"}),
        ev("EVD-1209", "Courier misdelivery investigation", "delivery", "Delivery system", None,
           "Recovery request raised with the courier; no outcome returned yet.",
           "The recovery investigation is unresolved.",
           "neutral", "medium", availability="unavailable", fields={"Raised": "14 Aug", "Status": "Open"}),
    ],
    "claim_vs_evidence": [
        ("Payment", "Captured", "EVD-1201"),
        ("Order address", "Apt 902", "EVD-1203"),
        ("Delivery scan", "Signed at flat 903", "EVD-1203"),
        ("OTP protocol", "Required above ₹25,000, not captured", "EVD-1204"),
        ("Customer communication", "Misdelivery reported in 4 hours", "EVD-1205"),
    ],
    "events": [
        event("2026-08-09", "11:14", "Payment captured", "Transaction system", ["EVD-1201"], "₹57,300"),
        event("2026-08-10", "08:30", "Order dispatched", "Fulfilment system", ["EVD-1202"], "High-value handling"),
        event("2026-08-13", "16:30", "Delivered to flat 903", "Delivery system", ["EVD-1203"],
              "Order address is apt 902"),
        event("2026-08-13", "20:05", "Customer reported misdelivery", "Customer support", ["EVD-1205"],
              "No recovery logged", actor="customer"),
        event("2026-08-18", "06:20", "Chargeback initiated", "Dispute system", [],
              "Reason: product not received", actor="issuer"),
    ],
    "gaps": [
        gap("OTP verification for a high-value delivery", "Merchant policy required it and it is absent.", 2.5),
        gap("Courier recovery outcome", "Would show whether the parcel was retrieved.", 1.5),
    ],
    "argument": (
        "Delivery was recorded at flat 903 while the order address is apartment 902, and the merchant's own "
        "high-value protocol required OTP verification that was never captured. The customer reported the "
        "misdelivery within four hours. The delivery scan alone will not rebut the claim."
    ),
})

CASES.append({
    "dispute": {
        "dispute_id": "CB-2026-89112",
        "transaction_id": "TXN-932790", "order_id": "ORD-732104", "customer_id": "CUST-45120",
        "customer_name": "Devika Menon", "customer_email": "devika.menon@example.in",
        "reason": "Product not as described",
        "reason_code": "13.3 — Not as described or defective",
        "network": "Mastercard", "amount": 49000,
        "created_at": "2026-08-13T09:00:00", "response_deadline": "2026-08-19T09:00:00",
        "status": "Evidence ready", "priority": "medium",
        "claim": "The furniture set delivered was not the fabric I selected.",
        "claim_detail": "Cardholder states an alternate upholstery finish was delivered.",
    },
    "transaction": {
        "transaction_id": "TXN-932790", "order_id": "ORD-732104", "customer_id": "CUST-45120",
        "merchant_id": MERCHANT["merchant_id"], "amount": 49000, "currency": "INR",
        "payment_method": "Card • ICICI Mastercard credit •••• 9034", "timestamp": "2026-07-25T16:45:00",
        "status": "captured", "auth_code": "M77PL1", "avs_match": True, "cvv_match": True,
        "three_ds": "Authenticated",
    },
    "order": {
        "order_id": "ORD-732104", "customer_id": "CUST-45120",
        "product": "Three-seat sofa — Linen Grey configuration",
        "order_timestamp": "2026-07-25T16:46:00", "fulfillment_status": "fulfilled",
        "delivery_status": "delivered", "delivery_timestamp": "2026-08-04T12:00:00",
        "shipping_address": "44 Coral Street, Kochi 682020", "courier": "SafeExpress", "awb": "SE-882201990",
    },
    "refunds": [],
    "interactions": [
        {"interaction_id": "INT-6602", "customer_id": "CUST-45120", "order_id": "ORD-732104",
         "timestamp": "2026-08-04T12:35:00", "channel": "App", "category": "delivery_acceptance",
         "message": "Customer completed the in-app delivery checklist and confirmed the configuration."},
    ],
    "evidence": [
        ev("EVD-1301", "Payment authorisation", "payment", "Payment gateway", "2026-07-25T16:45:00",
           "Payment of ₹49,000 captured.", "Payment captured with 3-D Secure.",
           "merchant", "high", fields={"3-D Secure": "Authenticated"}),
        ev("EVD-1302", "Configured order sheet", "order", "Order system", "2026-07-25T16:46:00",
           "Order configurator recorded 'Linen Grey' with a signed digital configuration confirmation.",
           "The ordered configuration is documented and was confirmed by the customer.",
           "merchant", "high", fields={"Fabric": "Linen Grey", "Confirmation": "Signed at checkout"}),
        ev("EVD-1303", "Production QC record", "fulfillment", "Fulfilment system", "2026-08-01T10:00:00",
           "QC photographs of the finished unit show the Linen Grey fabric with a matching batch code.",
           "The manufactured unit matches the ordered configuration.",
           "merchant", "high", fields={"Batch": "LG-2214", "Photos": "4 on file"}),
        ev("EVD-1304", "Delivery acceptance checklist", "delivery", "Delivery system", "2026-08-04T12:35:00",
           "Customer completed the in-app delivery checklist confirming fabric and configuration on delivery.",
           "The customer verified the configuration at the point of delivery.",
           "merchant", "high", fields={"Checklist": "Completed", "Fabric confirmed": "Yes",
                                       "Signed": "D. Menon"}),
        ev("EVD-1305", "Post-delivery complaint", "communication", "Customer support", "2026-08-11T15:20:00",
           "Complaint raised seven days after the accepted delivery.",
           "The objection came a week after an accepted delivery checklist.",
           "merchant", "medium", fields={"Days after delivery": "7"}),
        ev("EVD-1307", "Refund ledger", "refund", "Refund system", None, "No refund issued.",
           "No credit was issued before the dispute.", "merchant", "low", fields={"Refunds found": "0"}),
        ev("EVD-1308", "Customer dispute history", "historical", "Dispute system", None,
           "No prior disputes.", "Clean history.", "neutral", "low", fields={"Prior disputes": "0"}),
        ev("EVD-1309", "Policy reference", "policy", "Policy knowledge base", None,
           "Policy PL-034: a completed delivery acceptance checklist is strong evidence for "
           "not-as-described disputes on configured goods.",
           "The acceptance checklist is the deciding artefact and it is available.",
           "neutral", "medium", fields={"Policy": "PL-034 Not as described"}),
    ],
    "claim_vs_evidence": [
        ("Payment", "Captured", "EVD-1301"),
        ("Configuration ordered", "Linen Grey, signed at checkout", "EVD-1302"),
        ("Production QC", "Linen Grey batch LG-2214 photographed", "EVD-1303"),
        ("Delivery acceptance", "Checklist completed and signed", "EVD-1304"),
        ("Complaint", "Raised 7 days after acceptance", "EVD-1305"),
    ],
    "events": [
        event("2026-07-25", "16:45", "Payment captured", "Transaction system", ["EVD-1301"], "₹49,000"),
        event("2026-07-25", "16:46", "Configuration confirmed at checkout", "Order system", ["EVD-1302"],
              "Linen Grey"),
        event("2026-08-01", "10:00", "Production QC passed", "Fulfilment system", ["EVD-1303"], "Batch LG-2214"),
        event("2026-08-04", "12:35", "Delivery accepted by customer", "Delivery system", ["EVD-1304"],
              "In-app checklist signed", actor="customer"),
        event("2026-08-11", "15:20", "Complaint raised", "Customer support", ["EVD-1305"],
              "Seven days after acceptance", actor="customer"),
        event("2026-08-13", "09:00", "Chargeback initiated", "Dispute system", [],
              "Reason: product not as described", actor="issuer"),
    ],
    "gaps": [
        gap("Photographs of the delivered unit in situ",
            "Would remove any doubt about the fabric actually installed.", 1.2),
    ],
    "argument": (
        "The configuration was signed at checkout, QC photographs record the correct fabric batch, and the "
        "customer completed and signed the in-app delivery acceptance checklist confirming the configuration "
        "on arrival. The complaint followed seven days later. The acceptance checklist is the deciding "
        "artefact under policy PL-034."
    ),
})


# ── Two closed cases, for analytics history ────────────────────────────────
CASES.append({
    "dispute": {
        "dispute_id": "CB-2026-89094",
        "transaction_id": "TXN-927110", "order_id": "ORD-727330", "customer_id": "CUST-39902",
        "customer_name": "Farhan Qureshi", "customer_email": "farhan.q@example.in",
        "reason": "Product not received",
        "reason_code": "13.1 — Merchandise / services not received",
        "network": "Visa", "amount": 7250,
        "created_at": "2026-07-28T10:00:00", "response_deadline": "2026-08-04T18:00:00",
        "status": "Won", "priority": "low",
        "claim": "The order did not arrive.",
        "claim_detail": "Closed case retained for reporting.",
    },
    "transaction": {
        "transaction_id": "TXN-927110", "order_id": "ORD-727330", "customer_id": "CUST-39902",
        "merchant_id": MERCHANT["merchant_id"], "amount": 7250, "currency": "INR",
        "payment_method": "Card • Visa •••• 2214", "timestamp": "2026-07-18T14:00:00",
        "status": "captured", "auth_code": "V11AA1", "avs_match": True, "cvv_match": True,
        "three_ds": "Authenticated",
    },
    "order": {
        "order_id": "ORD-727330", "customer_id": "CUST-39902", "product": "Bluetooth speaker — BS20",
        "order_timestamp": "2026-07-18T14:01:00", "fulfillment_status": "fulfilled",
        "delivery_status": "delivered", "delivery_timestamp": "2026-07-21T10:40:00",
        "shipping_address": "9 Station Road, Lucknow 226001", "courier": "Delhivery", "awb": "DL-441029900",
    },
    "refunds": [], "interactions": [],
    "evidence": [
        ev("EVD-0901", "Payment authorisation", "payment", "Payment gateway", "2026-07-18T14:00:00",
           "Payment captured.", "Payment captured with 3-D Secure.", "merchant", "high"),
        ev("EVD-0902", "Delivery record with OTP", "delivery", "Delivery system", "2026-07-21T10:40:00",
           "Delivered, OTP verified.", "OTP-verified delivery to the registered address.",
           "merchant", "high"),
        ev("EVD-0903", "Policy reference", "policy", "Policy knowledge base", None,
           "Policy PL-013 satisfied.", "Rebuttal standard met.", "neutral", "medium"),
    ],
    "claim_vs_evidence": [("Delivery", "OTP verified", "EVD-0902")],
    "events": [
        event("2026-07-18", "14:00", "Payment captured", "Transaction system", ["EVD-0901"], "₹7,250"),
        event("2026-07-21", "10:40", "Order delivered — OTP verified", "Delivery system", ["EVD-0902"], ""),
        event("2026-07-28", "10:00", "Chargeback initiated", "Dispute system", [], "", actor="issuer"),
        event("2026-08-02", "16:00", "Representment submitted", "Dispute system", [], "Evidence package sent"),
        event("2026-08-09", "12:00", "Dispute won", "Dispute system", [], "Issuer accepted the evidence"),
    ],
    "gaps": [],
    "argument": "Closed — representment accepted.",
})

CASES.append({
    "dispute": {
        "dispute_id": "CB-2026-89088",
        "transaction_id": "TXN-926540", "order_id": "ORD-726880", "customer_id": "CUST-39511",
        "customer_name": "Latha Krishnan", "customer_email": "latha.k@example.in",
        "reason": "Credit not processed",
        "reason_code": "13.6 — Credit not processed",
        "network": "RuPay", "amount": 3900,
        "created_at": "2026-07-22T09:00:00", "response_deadline": "2026-07-29T18:00:00",
        "status": "Accepted", "priority": "low",
        "claim": "Refund for a cancelled order never arrived.",
        "claim_detail": "Closed case retained for reporting.",
    },
    "transaction": {
        "transaction_id": "TXN-926540", "order_id": "ORD-726880", "customer_id": "CUST-39511",
        "merchant_id": MERCHANT["merchant_id"], "amount": 3900, "currency": "INR",
        "payment_method": "UPI • latha@okaxis", "timestamp": "2026-07-10T11:20:00",
        "status": "captured", "auth_code": "U09BB4", "avs_match": None, "cvv_match": None,
        "three_ds": "Not applicable (UPI)",
    },
    "order": {
        "order_id": "ORD-726880", "customer_id": "CUST-39511", "product": "Table lamp — TL7",
        "order_timestamp": "2026-07-10T11:21:00", "fulfillment_status": "cancelled",
        "delivery_status": "not_applicable", "delivery_timestamp": None,
        "shipping_address": "3 Anna Nagar, Chennai 600040", "courier": None, "awb": None,
    },
    "refunds": [], "interactions": [],
    "evidence": [
        ev("EVD-0801", "Order cancellation record", "order", "Order system", "2026-07-12T09:00:00",
           "Order cancelled by merchant.", "Merchant cancelled the order.", "customer", "high"),
        ev("EVD-0802", "Refund ledger", "refund", "Refund system", None,
           "No refund processed.", "The promised credit was never issued.", "customer", "high"),
    ],
    "claim_vs_evidence": [("Refund", "Never issued", "EVD-0802")],
    "events": [
        event("2026-07-10", "11:20", "Payment captured", "Transaction system", [], "₹3,900"),
        event("2026-07-12", "09:00", "Order cancelled by merchant", "Order system", ["EVD-0801"], ""),
        event("2026-07-22", "09:00", "Chargeback initiated", "Dispute system", [], "", actor="issuer"),
        event("2026-07-25", "11:00", "Dispute accepted", "Dispute system", [], "Credit issued to cardholder"),
    ],
    "gaps": [],
    "argument": "Closed — accepted, credit issued.",
})


CASE_INDEX = {c["dispute"]["dispute_id"]: c for c in CASES}
CLOSED_STATUSES = {"Won", "Lost", "Accepted", "Closed"}


# ---------------------------------------------------------------------------
# Policy knowledge base (distinct from case evidence)
# ---------------------------------------------------------------------------

POLICIES: list[dict[str, Any]] = [
    {
        "policy_id": "PL-013", "name": "Non-receipt disputes",
        "dispute_type": "Product not received",
        "networks": "Visa 13.1 · Mastercard 4855",
        "relevant_evidence": ["Delivery scan to the cardholder address", "Signed POD or verified OTP",
                              "Dispatch manifest with AWB", "Tracking access by the customer"],
        "response_requirements": (
            "Submit a delivery record showing the consignment reached the address on file, ideally with an "
            "OTP or signature. Tracking activity from the customer's own account may be included as "
            "corroboration but is not sufficient on its own."
        ),
        "response_window_days": 7, "last_updated": "2026-06-14",
    },
    {
        "policy_id": "PL-021", "name": "Services not rendered",
        "dispute_type": "Services not rendered",
        "networks": "Visa 13.2 · Mastercard 4859",
        "relevant_evidence": ["Signed service completion sheet", "Engineer assignment log",
                              "Appointment history", "Reschedule communications"],
        "response_requirements": (
            "A completion artefact signed or acknowledged by the customer is required. Booking records alone "
            "do not establish that the service was performed."
        ),
        "response_window_days": 7, "last_updated": "2026-05-30",
    },
    {
        "policy_id": "PL-029", "name": "Recurring cancellations",
        "dispute_type": "Cancelled recurring transaction",
        "networks": "Visa 13.2 · Mastercard 4841",
        "relevant_evidence": ["Subscription state log", "Cancellation confirmation", "Renewal notice",
                              "Post-renewal usage"],
        "response_requirements": (
            "Show a valid mandate, advance renewal notice and an active subscription state at the billing "
            "instant. Incomplete customer cancellation attempts are reviewed case by case by an operator."
        ),
        "response_window_days": 8, "last_updated": "2026-07-02",
    },
    {
        "policy_id": "PL-034", "name": "Not as described",
        "dispute_type": "Product not as described",
        "networks": "Visa 13.3 · Mastercard 4853",
        "relevant_evidence": ["Serial-level pick scan", "Packing-bench imagery", "Delivery acceptance checklist",
                              "Return inspection report"],
        "response_requirements": (
            "Establish which unit left the warehouse and, where available, that the customer accepted the "
            "configuration at delivery. Marketing copy is not evidence of what was shipped."
        ),
        "response_window_days": 7, "last_updated": "2026-06-28",
    },
    {
        "policy_id": "PL-045", "name": "Card-absent fraud",
        "dispute_type": "Unauthorized transaction",
        "networks": "Visa 10.4 · Mastercard 4837",
        "relevant_evidence": ["3-D Secure authentication result", "AVS / CVV result", "Device and session history",
                              "Delivery to a verified cardholder address"],
        "response_requirements": (
            "Contest only where a liability shift exists or the goods went to an address previously verified "
            "for the cardholder. AVS mismatch combined with a first-seen device is not contestable."
        ),
        "response_window_days": 5, "last_updated": "2026-07-19",
    },
    {
        "policy_id": "PL-052", "name": "Credit not processed",
        "dispute_type": "Credit not processed",
        "networks": "Visa 13.6 · Mastercard 4860",
        "relevant_evidence": ["Refund ledger entry", "Cancellation record", "Refund gateway response",
                              "Customer communications"],
        "response_requirements": (
            "Where a merchant-initiated cancellation exists, the credit must be issued before the dispute "
            "window closes. Failed refunds must be retried and evidenced."
        ),
        "response_window_days": 7, "last_updated": "2026-04-11",
    },
    {
        "policy_id": "PL-058", "name": "High-value delivery protocol",
        "dispute_type": "Product not received",
        "networks": "Internal control",
        "relevant_evidence": ["OTP verification", "Named recipient", "High-value handling manifest"],
        "response_requirements": (
            "Consignments above ₹25,000 must be OTP-verified with the named recipient. Deliveries without "
            "OTP capture are not contested by default."
        ),
        "response_window_days": None, "last_updated": "2026-03-22",
    },
    {
        "policy_id": "PL-067", "name": "Returns & restocking",
        "dispute_type": "Partial refund not received",
        "networks": "Internal control",
        "relevant_evidence": ["Checkout policy acceptance", "Return inspection report", "Refund record"],
        "response_requirements": (
            "Restocking deductions may only be applied where the policy version accepted at checkout "
            "disclosed the fee. Retain the catalogue snapshot for the disclosure."
        ),
        "response_window_days": None, "last_updated": "2026-05-08",
    },
    {
        "policy_id": "PL-071", "name": "Duplicate processing",
        "dispute_type": "Duplicate processing",
        "networks": "Visa 12.6 · Mastercard 4834",
        "relevant_evidence": ["Authorisation history", "Settlement report", "Order record"],
        "response_requirements": (
            "Submit the settlement report showing a single capture for the order, plus the authorisation "
            "history explaining any voided attempts."
        ),
        "response_window_days": 7, "last_updated": "2026-06-01",
    },
]
