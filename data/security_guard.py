"""
TechPrep AI — PII Security Guard

Detects and redacts sensitive personal information before it reaches
the agent's context window. Implements input sanitization as described
in Day 4 (Vibe Coding Agent Security and Evaluation).

Patterns detected and redacted:
- Indian Aadhaar numbers (12-digit national ID)
- Mobile phone numbers (Indian format)
- Generic long digit sequences that may be ID numbers
- Email addresses (flagged, not redacted — emails are often intentional)
- Passwords and API keys (common accidental paste scenarios)

Course concept demonstrated: Context Hygiene & PII Redaction (Day 4)
"""

import re
from dataclasses import dataclass


@dataclass
class ScanResult:
    """Result of scanning a text string for sensitive content."""
    original_text: str
    cleaned_text: str
    redactions_made: list[str]
    is_clean: bool

    def summary(self) -> str:
        if self.is_clean:
            return "Input is clean — no sensitive data detected."
        types = ", ".join(self.redactions_made)
        return (
            f"[Security Notice: Sensitive information was detected and redacted "
            f"from your input ({types}). Please never share personal ID numbers, "
            f"phone numbers, or passwords in this interface.]"
        )


# ─── DETECTION PATTERNS ───────────────────────────────────────────────────────

# Indian Aadhaar: exactly 12 digits, possibly space or dash separated
AADHAAR_PATTERN = re.compile(
    r'\b(\d{4}[\s\-]?\d{4}[\s\-]?\d{4})\b'
)

# Indian mobile numbers: 10 digits starting with 6, 7, 8, or 9
# With or without country code (+91 or 0)
PHONE_PATTERN = re.compile(
    r'(?:\+91|0)?[\s\-]?[6-9]\d{9}\b'
)

# Generic long numeric sequences that look like IDs (9+ digits)
# but are not caught by more specific patterns
GENERIC_ID_PATTERN = re.compile(
    r'\b\d{9,}\b'
)

# API keys: common patterns (starts with AIzaSy for Google, or long alphanumeric)
API_KEY_PATTERN = re.compile(
    r'\b(AIzaSy[A-Za-z0-9_\-]{33}|sk-[A-Za-z0-9]{32,}|[A-Za-z0-9]{40,})\b'
)

# Passwords: common patterns like "password: xyz" or "pass = xyz"
PASSWORD_PATTERN = re.compile(
    r'(?i)(password|passwd|pwd|secret)\s*[:=]\s*\S+',
)

# PAN Card: Indian format (5 letters, 4 digits, 1 letter)
PAN_PATTERN = re.compile(
    r'\b[A-Z]{5}[0-9]{4}[A-Z]\b'
)


def scan_and_redact(text: str) -> ScanResult:
    """
    Scan input text for sensitive information.
    Redact detected patterns and return a ScanResult.

    Args:
        text: The raw input string from the student.

    Returns:
        ScanResult with cleaned text and details of what was redacted.
    """
    if not text or not text.strip():
        return ScanResult(
            original_text=text,
            cleaned_text=text,
            redactions_made=[],
            is_clean=True
        )

    cleaned = text
    redactions = []

    # Check Aadhaar numbers first (most specific Indian ID)
    if AADHAAR_PATTERN.search(cleaned):
        cleaned = AADHAAR_PATTERN.sub("[AADHAAR-REDACTED]", cleaned)
        redactions.append("Aadhaar number")

    # Check PAN card numbers
    if PAN_PATTERN.search(cleaned):
        cleaned = PAN_PATTERN.sub("[PAN-REDACTED]", cleaned)
        redactions.append("PAN card number")

    # Check phone numbers
    if PHONE_PATTERN.search(cleaned):
        cleaned = PHONE_PATTERN.sub("[PHONE-REDACTED]", cleaned)
        redactions.append("phone number")

    # Check API keys and tokens
    if API_KEY_PATTERN.search(cleaned):
        cleaned = API_KEY_PATTERN.sub("[API-KEY-REDACTED]", cleaned)
        redactions.append("API key or token")

    # Check passwords
    if PASSWORD_PATTERN.search(cleaned):
        cleaned = PASSWORD_PATTERN.sub(r"\1: [PASSWORD-REDACTED]", cleaned)
        redactions.append("password")

    # Check generic long ID numbers (run last to avoid double-redacting)
    if GENERIC_ID_PATTERN.search(cleaned):
        cleaned = GENERIC_ID_PATTERN.sub("[ID-REDACTED]", cleaned)
        redactions.append("numeric ID")

    is_clean = len(redactions) == 0

    return ScanResult(
        original_text=text,
        cleaned_text=cleaned,
        redactions_made=redactions,
        is_clean=is_clean
    )


def is_safe(text: str) -> bool:
    """Quick check — returns True if no sensitive data detected."""
    result = scan_and_redact(text)
    return result.is_clean


if __name__ == "__main__":
    # Test the security guard with real-world examples
    test_cases = [
        ("Normal input", "I want to practice arrays at medium difficulty"),
        ("Aadhaar leak", "My Aadhaar is 1234 5678 9012 and I need help"),
        ("Phone number", "Call me at 9876543210 for interview prep"),
        ("Password paste", "I use password: MySecret123 for all accounts"),
        ("API key paste", "My key is AIzaSyD-mock-key-value-12345abcdefgh"),
        ("Clean code question", "How do I reverse a linked list in O(n) time?"),
        ("PAN card", "PAN: ABCDE1234F is my tax number"),
    ]

    print("TechPrep AI — Security Guard Test\n" + "=" * 40)
    for label, text in test_cases:
        result = scan_and_redact(text)
        status = "CLEAN" if result.is_clean else "REDACTED"
        print(f"\n[{status}] {label}")
        print(f"  Input:   {text}")
        if not result.is_clean:
            print(f"  Output:  {result.cleaned_text}")
            print(f"  Notice:  {result.summary()}")