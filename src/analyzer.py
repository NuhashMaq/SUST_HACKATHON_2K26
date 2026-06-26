from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from src.models import TicketRequest
from src.safety import credential_warning, ensure_safe_text
from src.utils import (
    contains_any,
    extract_amounts,
    extract_phone_like_tokens,
    normalize_text,
    parse_iso_datetime,
    tx_to_dict,
)

CASE_DEPARTMENTS = {
    "wrong_transfer": "dispute_resolution",
    "payment_failed": "payments_ops",
    "refund_request": "customer_support",
    "duplicate_payment": "payments_ops",
    "merchant_settlement_delay": "merchant_operations",
    "agent_cash_in_issue": "agent_operations",
    "phishing_or_social_engineering": "fraud_risk",
    "other": "customer_support",
}

EXPECTED_TYPES = {
    "wrong_transfer": ["transfer"],
    "payment_failed": ["payment"],
    "refund_request": ["payment", "refund"],
    "duplicate_payment": ["payment"],
    "merchant_settlement_delay": ["settlement"],
    "agent_cash_in_issue": ["cash_in"],
    "phishing_or_social_engineering": [],
    "other": [],
}

PHISHING_KW = [
    "otp", "pin", "password", "passcode", "credential", "scam", "fraud", "suspicious", "blocked", "block",
    "ওটিপি", "otp", "পিন", "পাসওয়ার্ড", "পাসওয়ার্ড", "স্ক্যাম", "প্রতার", "ব্লক",
]
DUPLICATE_KW = ["twice", "duplicate", "double", "deducted twice", "charged twice", "paid twice", "দুইবার", "ডাবল", "দুবার"]
PAYMENT_FAILED_KW = [
    "failed", "fail", "balance deducted", "deducted", "cut", "not successful", "পেমেন্ট ফেইল", "ফেইল", "ব্যর্থ", "কেটে", "কাটা", "ব্যালেন্স", "deduct",
]
WRONG_TRANSFER_KW = [
    "wrong number", "wrong person", "wrong recipient", "mistake", "mistakenly", "typed it wrong",
    "sent", "send money", "didn't get", "did not get", "not received", "not receive",
    "ভুল নাম্বার", "ভুল নম্বর", "ভুল করে", "ভুল মানুষ", "ভুল ব্যক্ত", "পাঠিয়েছি", "পাঠিয়েছি", "পায়নি", "পায়নি",
]
MERCHANT_KW = ["settlement", "sales not settled", "not settled", "settled to my account", "settlement usually", "সেটেলমেন্ট", "বিক্রি"]
AGENT_CASH_IN_KW = ["agent", "cash in", "cash-in", "cashin", "এজেন্ট", "ক্যাশ ইন", "ক্যাশইন"]
REFUND_KW = ["refund", "return my money", "money back", "ফেরত", "রিফান্ড", "টাকা ফেরত"]
VAGUE_KW = ["something is wrong", "please check", "সমস্যা", "চেক", "wrong with my money"]


def detect_case_type(text: str, user_type: Optional[str], channel: Optional[str]) -> str:
    """Priority-based classifier. Safety-sensitive cases come first."""
    if contains_any(text, PHISHING_KW):
        return "phishing_or_social_engineering"
    if contains_any(text, DUPLICATE_KW):
        return "duplicate_payment"
    if contains_any(text, PAYMENT_FAILED_KW):
        # Agent cash-in complaints often mention balance not added; catch agent-specific case first.
        if contains_any(text, AGENT_CASH_IN_KW):
            return "agent_cash_in_issue"
        return "payment_failed"
    if contains_any(text, WRONG_TRANSFER_KW):
        return "wrong_transfer"
    if user_type == "merchant" or channel == "merchant_portal" or contains_any(text, MERCHANT_KW):
        return "merchant_settlement_delay"
    if contains_any(text, AGENT_CASH_IN_KW):
        return "agent_cash_in_issue"
    if contains_any(text, REFUND_KW):
        return "refund_request"
    return "other"


def amount_matches(tx_amount: float, amounts: List[float]) -> bool:
    return any(abs(float(tx_amount) - float(a)) < 0.001 for a in amounts)


def find_duplicate_payment(history: List[Dict[str, Any]], amounts: List[float]) -> Tuple[Optional[Dict[str, Any]], str, List[str]]:
    groups = defaultdict(list)
    for tx in history:
        if tx.get("type") == "payment" and tx.get("status") == "completed":
            if amounts and not amount_matches(float(tx.get("amount", -1)), amounts):
                continue
            key = (float(tx.get("amount", 0)), tx.get("counterparty"))
            groups[key].append(tx)

    best_pair = None
    best_delta = None
    for txs in groups.values():
        if len(txs) < 2:
            continue
        txs_sorted = sorted(txs, key=lambda x: x.get("timestamp", ""))
        for i in range(len(txs_sorted) - 1):
            a, b = txs_sorted[i], txs_sorted[i + 1]
            da, db = parse_iso_datetime(a.get("timestamp")), parse_iso_datetime(b.get("timestamp"))
            if da and db:
                delta = abs((db - da).total_seconds())
            else:
                delta = 999999
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_pair = (a, b)

    if best_pair:
        second = best_pair[1]
        return second, "consistent", ["duplicate_payment", "biller_verification_required"]

    # If a single matching payment exists, evidence is not enough to prove duplicate.
    single_matches = [
        tx for tx in history
        if tx.get("type") == "payment" and (not amounts or amount_matches(float(tx.get("amount", -1)), amounts))
    ]
    if len(single_matches) == 1:
        return single_matches[0], "insufficient_data", ["duplicate_claim", "only_one_matching_payment"]
    return None, "insufficient_data", ["duplicate_claim", "no_duplicate_pair_found"]


def score_transaction(case_type: str, tx: Dict[str, Any], amounts: List[float], phones: List[str]) -> int:
    score = 0
    expected_types = EXPECTED_TYPES.get(case_type, [])

    if expected_types and tx.get("type") in expected_types:
        score += 4
    if amounts and amount_matches(float(tx.get("amount", -1)), amounts):
        score += 5
    if phones and str(tx.get("counterparty")) in phones:
        score += 4

    status = tx.get("status")
    if case_type == "wrong_transfer" and status == "completed":
        score += 3
    elif case_type == "payment_failed" and status in ["failed", "pending"]:
        score += 3
    elif case_type == "refund_request" and status in ["completed", "reversed"]:
        score += 2
    elif case_type == "merchant_settlement_delay" and status == "pending":
        score += 3
    elif case_type == "agent_cash_in_issue" and status in ["pending", "completed"]:
        score += 3

    return score


def find_best_transaction(case_type: str, text: str, history: List[Dict[str, Any]], amounts: List[float]) -> Tuple[Optional[Dict[str, Any]], str, List[str]]:
    phones = extract_phone_like_tokens(text)

    if case_type == "phishing_or_social_engineering":
        return None, "insufficient_data", ["phishing", "credential_protection", "critical_escalation"]

    if case_type == "duplicate_payment":
        return find_duplicate_payment(history, amounts)

    if not history:
        return None, "insufficient_data", ["no_transaction_history"]

    scored: List[Tuple[int, Dict[str, Any]]] = []
    for tx in history:
        score = score_transaction(case_type, tx, amounts, phones)
        if score >= 4:
            scored.append((score, tx))

    if not scored:
        return None, "insufficient_data", ["no_relevant_transaction"]

    scored.sort(key=lambda item: (item[0], item[1].get("timestamp", "")), reverse=True)
    top_score = scored[0][0]
    top_candidates = [tx for score, tx in scored if score == top_score]

    # If multiple equally plausible candidates, do not guess.
    if len(top_candidates) > 1:
        return None, "insufficient_data", ["ambiguous_match", "needs_clarification"]

    tx = scored[0][1]
    verdict = decide_verdict(case_type, text, tx, history, amounts)
    reason_codes = build_reason_codes(case_type, verdict, tx)
    return tx, verdict, reason_codes


def decide_verdict(case_type: str, text: str, tx: Dict[str, Any], history: List[Dict[str, Any]], amounts: List[float]) -> str:
    status = tx.get("status")
    tx_type = tx.get("type")

    if case_type == "wrong_transfer":
        same_counterparty = [
            item for item in history
            if item.get("type") == "transfer"
            and item.get("counterparty") == tx.get("counterparty")
            and item.get("transaction_id") != tx.get("transaction_id")
            and item.get("status") == "completed"
        ]
        if len(same_counterparty) >= 2:
            return "inconsistent"
        if tx_type == "transfer" and status == "completed":
            return "consistent"
        return "inconsistent"

    if case_type == "payment_failed":
        if tx_type == "payment" and status in ["failed", "pending"]:
            return "consistent"
        if tx_type == "payment" and status == "completed":
            return "inconsistent"
        return "insufficient_data"

    if case_type == "refund_request":
        if tx_type in ["payment", "refund"]:
            return "consistent"
        return "insufficient_data"

    if case_type == "merchant_settlement_delay":
        if tx_type == "settlement" and status in ["pending", "failed"]:
            return "consistent"
        if tx_type == "settlement" and status in ["completed", "reversed"]:
            return "inconsistent"
        return "insufficient_data"

    if case_type == "agent_cash_in_issue":
        if tx_type == "cash_in" and status in ["pending", "completed"]:
            return "consistent"
        if tx_type == "cash_in" and status in ["failed", "reversed"]:
            return "inconsistent"
        return "insufficient_data"

    return "insufficient_data"


def build_reason_codes(case_type: str, verdict: str, tx: Optional[Dict[str, Any]]) -> List[str]:
    codes = [case_type]
    if tx:
        codes.append("transaction_match")
    if verdict == "consistent":
        codes.append("evidence_consistent")
    elif verdict == "inconsistent":
        codes.append("evidence_inconsistent")
    else:
        codes.append("insufficient_data")
    return codes


def assign_severity(case_type: str, amounts: List[float], verdict: str) -> str:
    max_amount = max(amounts) if amounts else 0
    if case_type == "phishing_or_social_engineering":
        return "critical"
    # Merchant settlement delays are operational batch issues in the public rubric;
    # keep them medium even when the settlement amount is large.
    if case_type == "merchant_settlement_delay":
        return "medium"
    if case_type in ["wrong_transfer", "duplicate_payment", "agent_cash_in_issue"]:
        return "high" if verdict == "consistent" else "medium"
    if case_type == "payment_failed":
        return "high" if verdict == "consistent" else "medium"
    if case_type == "refund_request":
        return "low" if max_amount <= 1000 else "medium"
    if max_amount >= 10000:
        return "high"
    return "low"


def needs_human_review(case_type: str, severity: str, verdict: str) -> bool:
    if case_type == "phishing_or_social_engineering":
        return True
    if case_type in ["duplicate_payment", "agent_cash_in_issue"]:
        return True
    # Wrong-transfer cases need human review only after a specific transaction is identified
    # or the evidence contradicts the claim. If the match is ambiguous, ask for clarification first.
    if case_type == "wrong_transfer":
        return verdict != "insufficient_data"
    if verdict == "inconsistent":
        return True
    # Clear failed-payment and merchant-settlement cases can be handled by standard ops workflows.
    if case_type in ["payment_failed", "merchant_settlement_delay"] and verdict == "consistent":
        return False
    if severity == "critical":
        return True
    return False


def tx_ref(tx: Optional[Dict[str, Any]]) -> str:
    return tx.get("transaction_id") if tx else "the reported transaction"


def build_agent_summary(request: TicketRequest, case_type: str, tx: Optional[Dict[str, Any]], verdict: str, amounts: List[float]) -> str:
    amount_text = f"{max(amounts):g} BDT" if amounts else "an unspecified amount"
    if case_type == "phishing_or_social_engineering":
        return "Customer reports a suspicious message or call asking for sensitive credentials. Likely social engineering attempt."
    if case_type == "wrong_transfer":
        if tx:
            return f"Customer reports a possible wrong transfer of {tx.get('amount'):g} BDT via {tx.get('transaction_id')} to {tx.get('counterparty')}. Evidence verdict: {verdict}."
        return f"Customer reports a wrong transfer involving {amount_text}, but no single matching transaction can be confirmed from the provided history."
    if case_type == "payment_failed":
        if tx:
            return f"Customer reports failed payment or deducted balance for {tx.get('amount'):g} BDT via {tx.get('transaction_id')}. Transaction status is {tx.get('status')}."
        return f"Customer reports a failed payment or deducted balance involving {amount_text}, but no matching transaction was confirmed."
    if case_type == "duplicate_payment":
        if tx:
            return f"Customer reports a duplicate payment. {tx.get('transaction_id')} is the suspected duplicate transaction."
        return "Customer reports duplicate deduction, but the provided history does not clearly prove a duplicate payment."
    if case_type == "merchant_settlement_delay":
        if tx:
            return f"Merchant reports delayed settlement of {tx.get('amount'):g} BDT via {tx.get('transaction_id')}. Settlement status is {tx.get('status')}."
        return f"Merchant reports settlement delay involving {amount_text}, but no settlement transaction could be confirmed."
    if case_type == "agent_cash_in_issue":
        if tx:
            return f"Customer reports cash-in not reflected in balance. {tx.get('transaction_id')} is a {tx.get('status')} cash-in via {tx.get('counterparty')}."
        return f"Customer reports an agent cash-in issue involving {amount_text}, but no matching cash-in transaction was confirmed."
    if case_type == "refund_request":
        if tx:
            return f"Customer requests refund related to {tx.get('transaction_id')} for {tx.get('amount'):g} BDT. Refund eligibility requires policy review."
        return "Customer requests a refund, but no matching transaction was confirmed from the provided history."
    return "Customer reports a vague or uncategorized money-related issue. More details are needed before a specific transaction can be identified."


def build_next_action(case_type: str, tx: Optional[Dict[str, Any]], verdict: str) -> str:
    ref = tx_ref(tx)
    if case_type == "phishing_or_social_engineering":
        return "Escalate to fraud_risk immediately, log reported suspicious details, and remind the customer that official support never asks for PIN, OTP, or password."
    if verdict == "insufficient_data":
        return "Ask the customer for the transaction ID, amount, counterparty, and approximate time before initiating any dispute or operational workflow."
    if verdict == "inconsistent":
        return f"Flag {ref} for human review and verify the customer's claim against transaction history before taking action."
    if case_type == "wrong_transfer":
        return f"Verify {ref} details with the customer and initiate the wrong-transfer dispute workflow per policy."
    if case_type == "payment_failed":
        return f"Investigate {ref} ledger status. If balance was deducted on a failed payment, process according to the standard reversal workflow."
    if case_type == "duplicate_payment":
        return f"Verify the suspected duplicate {ref} with payments_ops and biller records before any eligible reversal is processed."
    if case_type == "merchant_settlement_delay":
        return f"Route {ref} to merchant_operations to verify settlement batch status and communicate an official ETA."
    if case_type == "agent_cash_in_issue":
        return f"Investigate {ref} with agent_operations and confirm settlement state under the standard cash-in SLA."
    if case_type == "refund_request":
        return f"Review refund eligibility for {ref} according to merchant or service policy without promising a refund before approval."
    return "Ask for clearer details and route to customer_support for first-level triage."


def build_customer_reply(language: Optional[str], case_type: str, tx: Optional[Dict[str, Any]], verdict: str) -> str:
    ref = tx_ref(tx)
    is_bn = language == "bn"

    if is_bn:
        if case_type == "phishing_or_social_engineering":
            return ensure_safe_text(
                "সতর্ক থাকার জন্য ধন্যবাদ। আমরা কখনোই আপনার পিন, ওটিপি বা পাসওয়ার্ড চাই না। "
                "অনুগ্রহ করে এগুলো কারো সাথে শেয়ার করবেন না। আমাদের ফ্রড টিম ঘটনাটি পর্যালোচনা করবে।",
                language,
            )
        if verdict == "insufficient_data":
            return ensure_safe_text(
                "ধন্যবাদ। দ্রুত সাহায্য করার জন্য অনুগ্রহ করে ট্রানজ্যাকশন আইডি, টাকার পরিমাণ, প্রাপকের তথ্য এবং আনুমানিক সময় জানান। "
                + credential_warning(language),
                language,
            )
        return ensure_safe_text(
            f"আপনার লেনদেন {ref} এর বিষয়ে আমরা অবগত হয়েছি। আমাদের সংশ্লিষ্ট দল এটি অফিসিয়াল চ্যানেলের মাধ্যমে যাচাই করবে। "
            + credential_warning(language),
            language,
        )

    if case_type == "phishing_or_social_engineering":
        reply = (
            "Thank you for reaching out before sharing any information. We never ask for your PIN, OTP, or password under any circumstances. "
            "Please do not share these with anyone, even if they claim to be from us. Our fraud team has been notified."
        )
    elif verdict == "insufficient_data":
        reply = (
            "Thank you for reaching out. To help you faster, please share the transaction ID, amount involved, counterparty, and approximate time. "
            "Please do not share your PIN or OTP with anyone."
        )
    elif case_type == "payment_failed":
        reply = (
            f"We have noted that transaction {ref} may have caused an unexpected balance deduction. "
            "Our payments team will review the case and any eligible amount will be returned through official channels. "
            "Please do not share your PIN or OTP with anyone."
        )
    elif case_type == "duplicate_payment":
        reply = (
            f"We have noted the possible duplicate payment for transaction {ref}. "
            "Our payments team will verify it through official records and any eligible amount will be returned through official channels. "
            "Please do not share your PIN or OTP with anyone."
        )
    elif case_type == "refund_request":
        reply = (
            f"We have received your request regarding {ref}. Refund eligibility depends on the applicable merchant or service policy. "
            "Our team will guide you through official support channels. Please do not share your PIN or OTP with anyone."
        )
    elif case_type == "merchant_settlement_delay":
        reply = (
            f"We have noted your concern about settlement {ref}. Our merchant operations team will check the batch status "
            "and update you through official channels."
        )
    else:
        reply = (
            f"We have noted your concern about transaction {ref}. Our team will review the case and contact you through official support channels. "
            "Please do not share your PIN or OTP with anyone."
        )
    return ensure_safe_text(reply, language)


def estimate_confidence(verdict: str, tx: Optional[Dict[str, Any]], case_type: str) -> float:
    if case_type == "phishing_or_social_engineering":
        return 0.95
    if verdict == "consistent" and tx:
        return 0.9
    if verdict == "inconsistent" and tx:
        return 0.75
    return 0.6


def analyze_ticket_rule_based(request: TicketRequest) -> Dict[str, Any]:
    text = normalize_text(request.complaint)
    amounts = extract_amounts(text)
    history = [tx_to_dict(tx) for tx in (request.transaction_history or [])]

    case_type = detect_case_type(text, request.user_type, request.channel)
    tx, verdict, reason_codes = find_best_transaction(case_type, text, history, amounts)
    severity = assign_severity(case_type, amounts, verdict)
    department = CASE_DEPARTMENTS[case_type]
    human_review_required = needs_human_review(case_type, severity, verdict)

    agent_summary = build_agent_summary(request, case_type, tx, verdict, amounts)
    next_action = build_next_action(case_type, tx, verdict)
    customer_reply = build_customer_reply(request.language, case_type, tx, verdict)

    return {
        "ticket_id": request.ticket_id,
        "relevant_transaction_id": tx.get("transaction_id") if tx else None,
        "evidence_verdict": verdict,
        "case_type": case_type,
        "severity": severity,
        "department": department,
        "agent_summary": ensure_safe_text(agent_summary, request.language),
        "recommended_next_action": ensure_safe_text(next_action, request.language),
        "customer_reply": ensure_safe_text(customer_reply, request.language),
        "human_review_required": human_review_required,
        "confidence": estimate_confidence(verdict, tx, case_type),
        "reason_codes": reason_codes,
    }
