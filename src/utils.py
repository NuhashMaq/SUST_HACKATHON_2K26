import re
from datetime import datetime
from typing import Any, Dict, List, Optional

BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def normalize_digits(text: str) -> str:
    return (text or "").translate(BN_DIGITS)


def normalize_text(text: str) -> str:
    return normalize_digits(text or "").lower().strip()


def extract_amounts(text: str) -> List[float]:
    """Extract likely BDT amounts from a complaint.

    We intentionally keep this simple and deterministic for reliability.
    Phone numbers are filtered out because they are too long for typical sample amounts.
    """
    text = normalize_digits(text)
    raw_numbers = re.findall(r"(?<!\d)(\d{1,7})(?:\.\d+)?(?!\d)", text)
    amounts: List[float] = []
    for n in raw_numbers:
        try:
            value = float(n)
            # Ignore tiny one-digit time clues like 2pm if no currency context nearby is hard to prove.
            # We still keep >= 10 because amounts in these cases are normally 500+.
            if value >= 10:
                amounts.append(value)
        except ValueError:
            continue
    return amounts


def extract_phone_like_tokens(text: str) -> List[str]:
    text = normalize_digits(text)
    # Supports local BD numbers and +880 style. Kept loose enough for synthetic cases.
    tokens = re.findall(r"(?:\+?8801|01)\d{8,9}", text.replace(" ", ""))
    normalized = []
    for token in tokens:
        if token.startswith("01"):
            normalized.append("+88" + token)
        elif token.startswith("880"):
            normalized.append("+" + token)
        else:
            normalized.append(token)
    return list(dict.fromkeys(normalized))


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def tx_to_dict(tx: Any) -> Dict[str, Any]:
    if hasattr(tx, "model_dump"):
        return tx.model_dump()
    if hasattr(tx, "dict"):
        return tx.dict()
    return dict(tx)


def contains_any(text: str, keywords: List[str]) -> bool:
    return any(k in text for k in keywords)
