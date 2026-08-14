"""Content-Forge claim verification & provenance (spec §3.3, P0-3).

Verified vs. suggestion classification (FR-18..FR-20, FR-22). The
verification core is MECHANICAL token-overlap on the cited excerpt span —
it never trusts model self-report (citation presence != correctness,
research risk #1). ``classify`` falls back to a deterministic safe default
(unsupported / opinion) unless an LLM-as-judge is injected.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from enum import Enum

from pydantic import BaseModel


class ClaimClassification(str, Enum):
    """Classification of a claim's support level (shared enum, spec §3.0)."""

    supported = "supported"
    partially_supported = "partially_supported"
    unsupported = "unsupported"
    opinion = "opinion"
    na = "na"


class Claim(BaseModel):
    """One extracted or submitted claim with mechanical verification state."""

    claim_id: str
    text: str
    classification: ClaimClassification
    source_ref: str | None = None  # source url/title
    excerpt: str | None = None  # supporting chunk text
    span: tuple[int, int] | None = None  # [start, end) within excerpt
    source_date: str | None = None
    stale: bool = False  # FR-20
    verified: bool = False  # True iff classification == supported AND span overlaps excerpt


class ProvenanceBlock(BaseModel):
    """EU AI Act Art. 50(2)/50(3) provenance block for one channel."""

    brief_id: str
    channel: str
    sources: list[dict]  # [{url|ref, title, excerpt, span, date}]
    claims: list[Claim]
    generated_by_ai: bool = True  # Art. 50(2) marker
    human_reviewed: bool = False  # flips True on approval (Art. 50(3) exemption)


class ClaimVerifier:
    """Mechanical span-overlap verification + deterministic classification."""

    def __init__(self, overlap_ratio: float = 0.5) -> None:
        self.overlap_ratio = overlap_ratio

    # Explicit signatures: plain functions on this interpreter expose no
    # __signature__; the pre-tester contract pins them via __signature__.
    __signature__ = None  # replaced below

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"\w+", text.lower()))

    def verify_span(self, claim_text: str, excerpt: str, span: tuple[int, int] | None) -> bool:
        """MECHANICAL: token-overlap(extracted[span], claim_text) >= overlap_ratio.

        span None → False (never trusts a citation without a span); spans
        outside the excerpt or reversed → False.
        """
        if span is None:
            return False
        start, end = span
        if start < 0 or end <= start or end > len(excerpt):
            return False
        extracted = excerpt[start:end]
        extracted_tokens = self._tokens(extracted)
        claim_tokens = self._tokens(claim_text)
        if not claim_tokens:
            return False
        overlap = len(extracted_tokens & claim_tokens) / len(claim_tokens)
        return overlap >= self.overlap_ratio

    def classify(
        self,
        text: str,
        source: str | None,
        judge: Callable[[str, str], str] | None = None,
    ) -> Claim:
        """Classify a claim. judge: LLM-as-judge returning a classification
        value; default deterministic: source None → unsupported; "I think" /
        "In my opinion" prefix → opinion; otherwise → unsupported.

        verified = (classification == supported AND source present AND
        (no span verification needed at classify time)) — span verification
        is applied later via verify_span when an excerpt span is available.
        """
        classification: ClaimClassification
        if judge is not None:
            value = judge(text, source or "")
            try:
                classification = ClaimClassification(value)
            except ValueError:
                classification = ClaimClassification.unsupported
        else:
            stripped = text.strip()
            if re.match(r"^I\s+think\b", stripped, re.IGNORECASE) or re.match(
                r"^In\s+my\s+opinion\b", stripped, re.IGNORECASE
            ):
                classification = ClaimClassification.opinion
            else:
                classification = ClaimClassification.unsupported

        verified = classification == ClaimClassification.supported and bool(source)
        return Claim(
            claim_id=f"claim_{len(text)}_{abs(hash(text)) % (10**8):08d}",
            text=text,
            classification=classification,
            source_ref=source,
            verified=verified,
        )

    def split_claims(self, text: str) -> list[str]:
        """Sentence splitter on [.!?] + newline; non-empty trimmed sentences."""
        parts = re.split(r"(?<=[.!?])\s+|\n+", text)
        return [p.strip() for p in parts if p.strip()]


__all__ = ["Claim", "ClaimClassification", "ClaimVerifier", "ProvenanceBlock"]


# -- contract-pinned signatures (spec §3.3; tests read __signature__) --------
import inspect as _inspect

ClaimVerifier.__signature__ = None  # type: ignore[assignment]
ClaimVerifier.verify_span.__signature__ = _inspect.Signature(  # type: ignore[attr-defined]
    [
        _inspect.Parameter("self", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter("claim_text", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter("excerpt", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter("span", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ]
)
ClaimVerifier.classify.__signature__ = _inspect.Signature(  # type: ignore[attr-defined]
    [
        _inspect.Parameter("self", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter("text", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter("source", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter(
            "judge", _inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None
        ),
    ]
)
ClaimVerifier.split_claims.__signature__ = _inspect.Signature(  # type: ignore[attr-defined]
    [
        _inspect.Parameter("self", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter("text", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ]
)
