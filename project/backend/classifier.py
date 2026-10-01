"""Query classifier — routes incoming questions into one of five categories.

Categories:
  FACTUAL       — factual question about scheme attributes (expense ratio, SIP, exit load, etc.)
  ADVICE        — asks for investment advice or recommendations
  PERFORMANCE  — asks about returns, NAV predictions, or performance comparisons
  OUT_OF_SCOPE — unrelated to mutual funds entirely
  PII           — contains personal identifiable information
"""

from __future__ import annotations
import re
from enum import Enum
from dataclasses import dataclass


class QueryCategory(str, Enum):
    FACTUAL = "FACTUAL"
    ADVICE = "ADVICE"
    PERFORMANCE = "PERFORMANCE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    PII = "PII"


@dataclass
class ClassificationResult:
    category: QueryCategory
    reason: str


# ── PII patterns ──────────────────────────────────────────────
_PII_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"[A-Z]{5}\d{4}[A-Z]"),                       # PAN
    re.compile(r"\b\d{12}\b"),                                # Aadhaar
    re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),                # Aadhaar spaced
    re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I),  # Email
    re.compile(r"\b\d{10}\b"),                                # Phone
    re.compile(r"\b\d{6}\b"),                                 # OTP / PIN
    re.compile(r"\b(?:\+\d{1,3}[-\s]?)?\d{10}\b"),            # Intl phone
    re.compile(r"\b(?:PAN|Aadhaar|OTP|account\s*(?:number|no)?)\b", re.I),
]

# ── Advice patterns ───────────────────────────────────────────
_ADVICE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"should\s+i\s*(?:invest|buy|sell|redeem|switch)", re.I),
    re.compile(r"which\s*(?:fund|scheme)\s*(?:should|to)\s*(?:i\s*)?(?:invest|buy|choose)", re.I),
    re.compile(r"is\s*(?:it|this)\s*(?:a\s*)?(?:good|bad)\s*(?:time|investment)", re.I),
    re.compile(r"recommend", re.I),
    re.compile(r"best\s*(?:fund|scheme|investment)", re.I),
    re.compile(r"should\s+i\s*(?:hold|exit|continue)", re.I),
    re.compile(r"portfolio\s*(?:allocation|recommendation|suggestion)", re.I),
    re.compile(r"how\s*(?:much|should)\s*i\s*invest", re.I),
    re.compile(r"is\s*(?:hdfc|this)\s*(?:fund|scheme)\s*(?:safe|good|bad)", re.I),
]

# ── Performance patterns ─────────────────────────────────────
_PERFORMANCE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"will\s*(?:the\s*)?(?:nav|return|fund)\s*(?:go|be|increase|decrease)", re.I),
    re.compile(r"predict", re.I),
    re.compile(r"future\s*(?:return|performance|nav)", re.I),
    re.compile(r"compare\s*(?:the\s*)?(?:return|performance|nav)", re.I),
    re.compile(r"which\s*is\s*better", re.I),
    re.compile(r"(?:past|historical|expected)\s*(?:return|performance|yield)", re.I),
    re.compile(r"(?:cagr|annualized?\s*return|total\s*return)", re.I),
]

# ── Factual keywords ─────────────────────────────────────────
_FACTUAL_KEYWORDS = [
    "expense ratio", "exit load", "lock-in", "lock in", "lockin",
    "riskometer", "risk", "benchmark", "sip", "systematic investment",
    "minimum", "minimum amount", "minimum sip",
    "factsheet", "scheme information", "kim", "key information",
    "open ended", "open-ended", "close ended", "close-ended",
    "asset allocation", "fund manager", "fund type",
    "amc", "trustee", "custodian",
    "sebi", "amfi", "regulation",
    "statement", "portfolio statement",
    "nav", "aum", "fund size", "corpus",
    "direct plan", "regular plan",
    "entry load", "switch",
    "scheme", "fund",
]

# ── Mutual fund domain keywords ──────────────────────────────
_DOMAIN_KEYWORDS = [
    "mutual fund", "sip", "nav", "amc", "sebi", "amfi",
    "expense ratio", "exit load", "lock-in", "benchmark",
    "riskometer", "factsheet", "scheme", "redeem", "redemption",
    "hdfc", "balanced advantage", "mid-cap", "mid cap", "midcap",
    "short term debt", "short-term debt", "index fund", "nifty",
    "equity", "debt", "hybrid", "fund",
]


def _matches_any(text: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.search(text) for p in patterns)


def classify_query(question: str) -> ClassificationResult:
    """Classify a user question into one of five categories.

    Order of checks matters:
      1. PII first — never process PII regardless of intent.
      2. ADVICE — investment advice / recommendations.
      3. PERFORMANCE — return predictions / comparisons.
      4. FACTUAL — factual scheme attribute questions.
      5. OUT_OF_SCOPE — everything else.
    """
    q = question.strip()
    if not q:
        return ClassificationResult(QueryCategory.OUT_OF_SCOPE, "Empty question.")

    # 1. PII
    if _matches_any(q, _PII_PATTERNS):
        return ClassificationResult(
            QueryCategory.PII,
            "Your question appears to contain sensitive personal information "
            "(PAN, Aadhaar, OTP, phone, email, or account details). "
            "For your security, I cannot process questions containing PII. "
            "Please rephrase your question without personal details.",
        )

    # 2. ADVICE
    if _matches_any(q, _ADVICE_PATTERNS):
        return ClassificationResult(
            QueryCategory.ADVICE,
            "I am a facts-only chatbot and cannot provide investment advice, "
            "recommendations, or suggestions. I can only answer factual questions "
            "about expense ratio, SIP, exit load, lock-in period, riskometer, "
            "benchmark, and scheme statements from official sources. "
            "Please ask a factual question instead.",
        )

    # 3. PERFORMANCE
    if _matches_any(q, _PERFORMANCE_PATTERNS):
        return ClassificationResult(
            QueryCategory.PERFORMANCE,
            "I cannot provide return predictions, performance forecasts, or "
            "fund comparisons. I can only state factual attributes from official "
            "source documents. Please ask about expense ratio, SIP, exit load, "
            "lock-in, riskometer, or benchmark instead.",
        )

    # 4. FACTUAL — check if the question contains factual keywords
    q_lower = q.lower()
    has_factual = any(kw in q_lower for kw in _FACTUAL_KEYWORDS)
    has_domain = any(kw in q_lower for kw in _DOMAIN_KEYWORDS)

    if has_factual or has_domain:
        return ClassificationResult(QueryCategory.FACTUAL, "")

    # 5. OUT_OF_SCOPE
    return ClassificationResult(
        QueryCategory.OUT_OF_SCOPE,
        "This question is outside the scope of this chatbot. I only answer "
        "factual questions about HDFC mutual fund schemes from official "
        "AMC/SEBI/AMFI sources. Try asking about expense ratio, SIP, exit "
        "load, lock-in period, riskometer, or benchmark.",
    )
