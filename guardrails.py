# guardrails.py — production-level input/output guardrails.
#
# Scope & honesty note: these are deterministic, regex/heuristic guardrails —
# fast, dependency-free, and fully auditable. They are NOT an ML content
# classifier. For higher-assurance moderation, put a hosted moderation API
# (e.g. OpenAI moderation, Azure Content Safety) in front of this layer; this
# module is designed so that's a drop-in addition (see `moderate()` below).
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from metrics import (
    GUARDRAIL_INPUT_BLOCKS,
    GUARDRAIL_OUTPUT_REDACTIONS,
    GUARDRAIL_PII_REDACTIONS,
    GUARDRAIL_HALLUCINATION_FLAGS,
)

logger = logging.getLogger("smartrfp.guardrails")

MAX_INPUT_LENGTH = 25000
MAX_OUTPUT = 7000

# ---------------------------------------------------------------------------
# Prompt-injection detection
# ---------------------------------------------------------------------------
# Broader than a single-phrase list: several small pattern families instead of
# one exact-match list, so mild paraphrases ("please disregard the above
# instructions") are still caught. Still deterministic/auditable — every hit
# is logged with which pattern matched.
_INJECTION_PATTERNS = [
    re.compile(r"\bignore\s+(all\s+)?(the\s+)?(previous|prior|above)\s+instructions?\b", re.I),
    re.compile(r"\bforget\s+(all\s+)?(the\s+)?(previous|prior|above)\s+instructions?\b", re.I),
    re.compile(r"\bdisregard\s+(all\s+)?(the\s+)?(previous|prior|above)\b", re.I),
    re.compile(r"\byou\s+are\s+now\s+(a|an)\b", re.I),
    re.compile(r"\bact\s+as\s+(a|an|chatgpt|dan|jailbreak)\b", re.I),
    re.compile(r"\breveal\s+(your|the)\s+(system\s+)?(prompt|instructions)\b", re.I),
    re.compile(r"\bsystem\s+prompt\b", re.I),
    re.compile(r"\bdeveloper\s+(mode|message)\b", re.I),
    re.compile(r"\bjailbreak\b", re.I),
    re.compile(r"\bprint\s+(your|the)\s+(instructions|prompt)\b", re.I),
    re.compile(r"\bdo\s+anything\s+now\b", re.I),
    re.compile(r"</?(system|assistant|user)>", re.I),  # fake role-tag injection
]

# ---------------------------------------------------------------------------
# PII detection (regex-based; conservative, low false-negative bias)
# ---------------------------------------------------------------------------
_PII_PATTERNS = {
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

_BAD_WORDS = ["password", "secret key", "api key", "private key", "access token"]

_HALLUCINATION_TERMS = [
    "100%", "guaranteed", "certified", "iso 27001 certified", "soc2 certified",
    "soc 2 certified", "we have won", "award-winning", "market leader",
]


class GuardrailViolation(ValueError):
    """Raised when input fails a guardrail check. Carries the rule that fired
    so callers/logs can distinguish 'too long' from 'injection attempt'."""

    def __init__(self, message: str, rule: str):
        super().__init__(message)
        self.rule = rule


@dataclass
class GuardrailReport:
    """Structured result for output-side checks, so callers/UI can show
    *why* a section was flagged instead of a bare boolean."""
    redacted_secrets: list = field(default_factory=list)
    pii_redactions: dict = field(default_factory=dict)
    hallucination_terms: list = field(default_factory=list)
    truncated: bool = False


# ---------------------------------------------------------------------------
# Input side
# ---------------------------------------------------------------------------
def validate_input(text: str) -> str:
    """Validate + normalize untrusted input before it reaches a prompt.

    Raises GuardrailViolation (never a bare ValueError) so callers can
    distinguish guardrail rejections from other errors and log/metric them.
    """
    if not text or not text.strip():
        raise GuardrailViolation("Empty input.", rule="empty_input")

    if len(text) > MAX_INPUT_LENGTH:
        logger.info("Input truncated: %d -> %d chars", len(text), MAX_INPUT_LENGTH)
        text = text[:MAX_INPUT_LENGTH]

    for pattern in _INJECTION_PATTERNS:
        m = pattern.search(text)
        if m:
            GUARDRAIL_INPUT_BLOCKS.labels(rule="prompt_injection").inc()
            logger.warning("Prompt injection pattern matched: %r", m.group(0)[:80])
            raise GuardrailViolation(
                f"Prompt injection attempt detected (matched pattern near: {m.group(0)[:40]!r}).",
                rule="prompt_injection",
            )

    return text


def remove_pii(text: str) -> str:
    """Redact PII in-place, tracking counts per category for observability."""
    if not text:
        return text
    for label, pattern in _PII_PATTERNS.items():
        text, n = pattern.subn("[REDACTED]", text)
        if n:
            GUARDRAIL_PII_REDACTIONS.labels(category=label).inc(n)
    return text


# ---------------------------------------------------------------------------
# Output side
# ---------------------------------------------------------------------------
def validate_output(text: str, report: "GuardrailReport | None" = None) -> str:
    """Sanitize LLM output before it is shown/persisted. Optionally fills a
    GuardrailReport with what was found, for audit logging."""
    if report is None:
        report = GuardrailReport()

    if len(text) > MAX_OUTPUT:
        text = text[:MAX_OUTPUT]
        report.truncated = True

    for word in _BAD_WORDS:
        if word.lower() in text.lower():
            text = re.sub(re.escape(word), "[REDACTED]", text, flags=re.I)
            report.redacted_secrets.append(word)
            GUARDRAIL_OUTPUT_REDACTIONS.labels(reason="secret_leak").inc()

    flags = detect_hallucination(text)
    if flags:
        report.hallucination_terms = flags
        GUARDRAIL_HALLUCINATION_FLAGS.inc(len(flags))

    return text


def detect_hallucination(text: str) -> list:
    low = (text or "").lower()
    return [term for term in _HALLUCINATION_TERMS if term in low]


def moderate(text: str) -> GuardrailReport:
    """Single entry point combining PII redaction + hallucination flagging on
    a piece of text, returning a report. Kept separate from validate_output
    so a future hosted moderation call can be inserted here without touching
    every call site."""
    report = GuardrailReport()
    cleaned = remove_pii(text)
    report.hallucination_terms = detect_hallucination(cleaned)
    return report