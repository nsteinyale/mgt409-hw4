"""Privacy guards for Campus Customs.

redact_pii() strips personal details out of a shopper's chat message BEFORE the AI model sees it,
before it's saved to chat history, and before it's written to the audit trail. find_leaks() checks
the agent's reply for personal details that must never be shown.
"""

import re

# Order matters: the most specific patterns run first.
PII_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("password", re.compile(r"\b(password|passcode|passwd|pin)\b(\s*(is|was|:|=)\s*|\s+)\S+", re.I), r"\1 [password removed]"),
    ("card number", re.compile(r"\b\d(?:[ -]?\d){12,18}\b"), "[card number removed]"),
    ("ID number", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[ID number removed]"),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[email removed]"),
    ("phone number", re.compile(r"(?<!\w)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)"), "[phone number removed]"),
    (
        "street address",
        re.compile(
            r"\b\d{1,5}\s+(?:[A-Z][\w.]*\s+){1,4}(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Ln|Lane|Dr|Drive|Ct|Court|Pl|Place|Way|Ter|Terrace)\b\.?",
            re.I,
        ),
        "[address removed]",
    ),
]

STORE_ADDRESS = "57 Broadway"  # our own public address is fine to mention


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Return the text with personal details replaced, and the kinds of details that were removed."""
    found: list[str] = []
    for kind, pattern, replacement in PII_PATTERNS:
        if pattern.search(text):
            text = pattern.sub(replacement, text)
            found.append(kind)
    return text, found


EMAIL_RE = PII_PATTERNS[3][1]
CARD_RE = PII_PATTERNS[1][1]


def find_leaks(reply: str, allowed_email: str | None) -> list[str]:
    """Personal details in a reply that must not reach the shopper (anyone else's email, card numbers)."""
    problems = []
    for email in EMAIL_RE.findall(reply):
        if not allowed_email or email.lower() != allowed_email.lower():
            problems.append(f"the reply contains the email address {email}; never share email addresses other than the logged-in customer's own")
    if CARD_RE.search(reply):
        problems.append("the reply contains what looks like a card number; never repeat card or account numbers")
    return problems
