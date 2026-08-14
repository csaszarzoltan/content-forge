"""Pre-development contract tests for Content-Forge P0-4 (analysis/forge-spec.md §3.4).

Blocked-term enforcement — hard gate + reviewer exception (MVP FR-09; US-002).

Interface tests (SECTION 1) verify imports, class existence and method
signatures — they PASS immediately against the module once the developer
creates it (the module does not exist yet, so they are currently RED via
ImportError).

Behavioral tests (SECTION 2) verify the spec'd runtime semantics:
  * ``scan``: case-insensitive whole-word regex, positions as char spans,
    severity always "hard", duplicates in `prohibited` collapsed, no false
    positives on substrings ("buy now" not matched inside "valid until
    Friday" / "Buyer's remorse").
  * ``gate_approval``: hits whose term is in `exceptions` move to `excepted`
    and do NOT block; otherwise blocked=True with the hits.
  * ``apply_exception``: append-only reviewer record with timestamp.

Per spec §3.4 test expectations; expectations are behavioral (assert-based),
NOT ``pytest.raises(NotImplementedError)`` stub-guards.
"""

from __future__ import annotations

from src.forge.blocked_terms import BlockedTermGate

# ============================================================================
# SECTION 1 — INTERFACE TESTS
# ============================================================================


class TestBlockedTermsInterface:
    """Imports and class existence (spec §3.4)."""

    def test_module_importable(self):
        """BlockedTermGate imports cleanly from src.forge.blocked_terms."""
        assert BlockedTermGate is not None

    def test_default_constructible(self):
        """BlockedTermGate() constructs without arguments (scorer optional)."""
        assert isinstance(BlockedTermGate(), BlockedTermGate)

    def test_scorer_injectable(self):
        """A custom ComplianceScorer may be injected via __init__."""
        gate = BlockedTermGate(scorer=None)
        assert isinstance(gate, BlockedTermGate)


class TestGateSignature:
    """Method signatures for BlockedTermGate (spec §3.4, exact)."""

    def test_scan_signature(self):
        sig = BlockedTermGate.scan.__signature__
        assert list(sig.parameters) == ["self", "text", "prohibited"]

    def test_gate_approval_signature(self):
        sig = BlockedTermGate.gate_approval.__signature__
        assert list(sig.parameters) == ["self", "text", "prohibited", "exceptions"]
        assert sig.parameters["exceptions"].default is None

    def test_apply_exception_signature(self):
        sig = BlockedTermGate.apply_exception.__signature__
        assert list(sig.parameters) == ["self", "term", "reviewer", "reason"]


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (RED until developer implements §3.4)
# ============================================================================


class TestScanBehavior:
    """scan: case-insensitive whole-word matches with positions + hard severity."""

    def test_spec_example(self):
        """Spec §3.4 example returns both terms in order, all hard."""
        hits = BlockedTermGate().scan("Buy now and save big. Guaranteed results.", ["buy now", "guaranteed"])
        assert [h["term"] for h in hits] == ["buy now", "guaranteed"]
        assert all(h["severity"] == "hard" for h in hits)

    def test_no_false_positive(self):
        """Spec §3.4: term absent => empty list (no false positive)."""
        assert BlockedTermGate().scan("The offer is valid until Friday.", ["buy now"]) == []

    def test_case_insensitive(self):
        """Matching is case-insensitive ('BUY NOW' hits 'buy now')."""
        hits = BlockedTermGate().scan("BUY NOW and save.", ["buy now"])
        assert [h["term"] for h in hits] == ["buy now"]

    def test_whole_word_only(self):
        """Whole-word match: 'buy now' must not match inside 'Buyer'."""
        assert BlockedTermGate().scan("The Buyer's remorse set in.", ["buy now"]) == []

    def test_positions_char_spans(self):
        """positions are (start, end) char spans of the match in the text."""
        hits = BlockedTermGate().scan("Buy now and save.", ["buy now"])
        assert hits[0]["positions"] == [(0, 7)]

    def test_multiple_occurrences(self):
        """Every occurrence is reported as a separate position."""
        hits = BlockedTermGate().scan("Buy now, buy now, buy now!", ["buy now"])
        assert hits[0]["positions"] == [(0, 7), (9, 16), (18, 25)]

    def test_duplicates_collapsed(self):
        """Duplicate terms in `prohibited` are collapsed into one hit."""
        hits = BlockedTermGate().scan("Buy now to win.", ["buy now", "buy now", "buy now"])
        assert [h["term"] for h in hits] == ["buy now"]

    def test_multiple_terms_multiple_positions(self):
        """Multiple distinct terms each carry their own positions."""
        hits = BlockedTermGate().scan("Guaranteed results, guaranteed income.", ["guaranteed"])
        # Real byte offsets: second 'guaranteed' starts at char 20 (single space after the comma)
        assert hits[0]["positions"] == [(0, 10), (20, 30)]


class TestGateApprovalBehavior:
    """gate_approval: exception moves hits out of the blocking set."""

    def test_spec_example_excepted(self):
        """Spec §3.4: excepted term => blocked False, one entry in `excepted`."""
        r = BlockedTermGate().gate_approval("Buy now to win.", ["buy now"], exceptions=["buy now"])
        assert r["blocked"] is False
        assert len(r["excepted"]) == 1
        assert len(r["hits"]) == 0

    def test_spec_example_blocked(self):
        """Spec §3.4: no exception => blocked True with one hit."""
        r = BlockedTermGate().gate_approval("Buy now to win.", ["buy now"])
        assert r["blocked"] is True
        assert len(r["hits"]) == 1

    def test_excepted_hit_carries_position(self):
        """Excepted hits keep their scan metadata (term + positions)."""
        r = BlockedTermGate().gate_approval("Buy now to win.", ["buy now"], exceptions=["buy now"])
        assert r["excepted"][0]["term"] == "buy now"
        assert r["excepted"][0]["positions"] == [(0, 7)]

    def test_mixed_exception_and_block(self):
        """Only excepted terms move out; the rest still block."""
        r = BlockedTermGate().gate_approval(
            "Buy now — guaranteed results.",
            ["buy now", "guaranteed"],
            exceptions=["guaranteed"],
        )
        assert r["blocked"] is True
        assert [h["term"] for h in r["hits"]] == ["buy now"]
        assert [e["term"] for e in r["excepted"]] == ["guaranteed"]

    def test_clean_text_not_blocked(self):
        """No prohibited terms => blocked False with empty hits/excepted."""
        r = BlockedTermGate().gate_approval("The offer is valid until Friday.", ["buy now"])
        assert r["blocked"] is False
        assert r["hits"] == []
        assert r["excepted"] == []

    def test_empty_exceptions_list(self):
        """exceptions=[] behaves identically to no exceptions."""
        r = BlockedTermGate().gate_approval("Buy now to win.", ["buy now"], exceptions=[])
        assert r["blocked"] is True
        assert len(r["hits"]) == 1


class TestApplyExceptionBehavior:
    """apply_exception: append-only reviewer exception record."""

    def test_record_shape(self):
        """Record carries term, reviewer, reason and a float timestamp."""
        rec = BlockedTermGate().apply_exception("buy now", reviewer="alice", reason="legal approved")
        assert rec["term"] == "buy now"
        assert rec["reviewer"] == "alice"
        assert rec["reason"] == "legal approved"
        assert isinstance(rec["at"], float)

    def test_records_are_append_only(self):
        """Each call appends a new record; existing records are untouched."""
        gate = BlockedTermGate()
        first = gate.apply_exception("buy now", reviewer="alice", reason="legal approved")
        second = gate.apply_exception("guaranteed", reviewer="bob", reason="campaign copy")
        assert gate.exceptions == [first, second]
        assert first["at"] <= second["at"]
