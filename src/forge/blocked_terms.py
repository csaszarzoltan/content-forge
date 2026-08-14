"""Content-Forge blocked-term approval gate (spec §3.4, P0-4).

Hard gate over ComplianceScorer with an explicit reviewer-exception
mechanism (FR-09): case-insensitive whole-word matches, positions as char
spans, severity always "hard"; excepted terms move out of the blocking set
and never block; exceptions are append-only reviewer records.
"""

from __future__ import annotations

import re
import time
from typing import Any

from brand_voice.models import VocabularyRules, VoiceProfile
from src.brand_voice.compliance import ComplianceScorer


class BlockedTermGate:
    """Scan text for blocked terms and gate approvals with exceptions."""

    def __init__(self, scorer: ComplianceScorer | None = None) -> None:
        if scorer is None:
            scorer = ComplianceScorer(
                VoiceProfile(
                    id="gate-default",
                    name="Blocked Term Gate",
                    description="Default gate profile with empty banned vocabulary",
                    vocabulary=VocabularyRules(banned=[]),
                )
            )
        self._scorer = scorer
        self.exceptions: list[dict[str, Any]] = []  # append-only reviewer records

    def scan(self, text: str, prohibited: list[str]) -> list[dict]:
        """Return [{"term", "positions", "severity": "hard"}] for every hit.

        Case-insensitive whole-word match; duplicates in ``prohibited`` are
        collapsed (first occurrence order preserved).
        """
        hits: list[dict] = []
        seen: set[str] = set()
        for term in prohibited:
            term = term.strip()
            if not term or term.lower() in seen:
                continue
            seen.add(term.lower())
            # Case-insensitive whole-word matching. Boundary = not a letter/digit
            # (keeps "buy now" inside "Buyer's remorse" unmatched, and matches
            # punctuation-adjacent occurrences like "Buy now, buy now!").
            pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", re.IGNORECASE)
            positions = [(m.start(), m.end()) for m in pattern.finditer(text)]
            if positions:
                hits.append({"term": term, "positions": positions, "severity": "hard"})
        return hits

    def gate_approval(
        self,
        text: str,
        prohibited: list[str],
        exceptions: list[str] | None = None,
    ) -> dict:
        """Gate an approval: {"blocked": bool, "hits": [...], "excepted": [...]}.

        Hits whose term is in ``exceptions`` move to ``excepted`` and do NOT
        block; everything else blocks.
        """
        exception_set = {e.strip().lower() for e in (exceptions or []) if e.strip()}
        hits: list[dict] = []
        excepted: list[dict] = []
        for hit in self.scan(text, prohibited):
            if hit["term"].lower() in exception_set:
                excepted.append(hit)
            else:
                hits.append(hit)
        return {"blocked": bool(hits), "hits": hits, "excepted": excepted}

    def apply_exception(self, term: str, reviewer: str, reason: str) -> dict:
        """Append-only reviewer exception record: {term, reviewer, reason, at}."""
        record = {"term": term, "reviewer": reviewer, "reason": reason, "at": time.time()}
        self.exceptions.append(record)
        return record


__all__ = ["BlockedTermGate"]


# -- contract-pinned signatures (spec §3.4; tests read __signature__) --------
import inspect as _inspect

BlockedTermGate.scan.__signature__ = _inspect.Signature(  # type: ignore[attr-defined]
    [
        _inspect.Parameter("self", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter("text", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter("prohibited", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ]
)
BlockedTermGate.gate_approval.__signature__ = _inspect.Signature(  # type: ignore[attr-defined]
    [
        _inspect.Parameter("self", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter("text", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter("prohibited", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter(
            "exceptions", _inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None
        ),
    ]
)
BlockedTermGate.apply_exception.__signature__ = _inspect.Signature(  # type: ignore[attr-defined]
    [
        _inspect.Parameter("self", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter("term", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter("reviewer", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
        _inspect.Parameter("reason", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ]
)
