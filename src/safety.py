from typing import Optional

# These are unsafe because they ask the customer to provide credentials.
# We intentionally do NOT block safe warnings like "do not share your PIN".
FORBIDDEN_PHRASES = [
    "please share your otp",
    "kindly share your otp",
    "share your otp with us",
    "give your otp",
    "provide your otp",
    "send your otp",
    "tell us your otp",
    "please share your pin",
    "kindly share your pin",
    "share your pin with us",
    "give your pin",
    "provide your pin",
    "send your pin",
    "tell us your pin",
    "please share your password",
    "kindly share your password",
    "share your password with us",
    "give your password",
    "provide your password",
    "send your password",
    "full card number for verification",
    "we will refund",
    "we will reverse",
    "we will recover",
    "your money will be refunded",
    "your transaction has been reversed",
    "your account will be unblocked",
]

SAFE_FALLBACK_EN = (
    "We have received your concern. Our team will review it through official support channels. "
    "Please do not share your PIN, OTP, or password with anyone."
)

SAFE_FALLBACK_BN = (
    "আপনার অভিযোগ আমরা পেয়েছি। আমাদের দল অফিসিয়াল চ্যানেলের মাধ্যমে এটি যাচাই করবে। "
    "অনুগ্রহ করে কারো সাথে আপনার পিন, ওটিপি বা পাসওয়ার্ড শেয়ার করবেন না।"
)


def ensure_safe_text(text: str, language: Optional[str] = "en") -> str:
    candidate = text or ""
    low = candidate.lower()
    if any(phrase in low for phrase in FORBIDDEN_PHRASES):
        return SAFE_FALLBACK_BN if language == "bn" else SAFE_FALLBACK_EN
    return candidate


def credential_warning(language: Optional[str] = "en") -> str:
    if language == "bn":
        return "অনুগ্রহ করে কারো সাথে আপনার পিন, ওটিপি বা পাসওয়ার্ড শেয়ার করবেন না।"
    return "Please do not share your PIN, OTP, or password with anyone."
