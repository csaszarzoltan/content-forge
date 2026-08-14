"""Pre-development contract tests for Content-Forge P0-3 (analysis/forge-spec.md §3.3).

Claim verification & provenance — verified vs. suggestion (MVP FR-18, FR-19,
FR-20, FR-22; US-004).

Interface tests (SECTION 1) verify imports, class existence, Pydantic model
fields, enum members and method signatures — they PASS immediately against
the module once the developer creates it (the module does not exist yet, so
they are currently RED via ImportError).

Behavioral tests (SECTION 2) verify the spec'd runtime semantics:
  * ``verify_span`` is MECHANICAL token-overlap on ``excerpt[span]`` — span
    None always False; non-overlapping span False; never trusts model
    self-report (citation presence != correctness, research risk #1).
  * ``classify`` default (no judge) is a safe deterministic fallback:
    source None -> unsupported; "I think"/"In my opinion" prefix -> opinion;
    otherwise unsupported. ``verified == (classification == supported and
    source present)``. Judge injection overrides the default.
  * ``split_claims`` splits on ``[.!?]`` + newline, non-empty trimmed output.

Per spec §3.3 test expectations; expectations are behavioral (assert-based),
NOT ``pytest.raises(NotImplementedError)`` stub-guards.
"""

from __future__ import annotations

from enum import Enum

import pytest
from src.forge.claims import (
    Claim,
    ClaimClassification,
    ClaimVerifier,
    ProvenanceBlock,
)

# Expected enum members and their string values (spec §3.3).
CLAIM_CLASSIFICATION_MEMBERS = {
    "supported": "supported",
    "partially_supported": "partially_supported",
    "unsupported": "unsupported",
    "opinion": "opinion",
    "na": "na",
}

# Expected Claim model fields with defaults (spec §3.3).
CLAIM_FIELDS = {
    "claim_id": None,
    "text": None,
    "classification": None,
    "source_ref": None,
    "excerpt": None,
    "span": None,
    "source_date": None,
    "stale": False,
    "verified": False,
}

# Expected ProvenanceBlock model fields with defaults (spec §3.3).
PROVENANCE_BLOCK_FIELDS = {
    "brief_id": None,
    "channel": None,
    "sources": None,
    "claims": None,
    "generated_by_ai": True,
    "human_reviewed": False,
}

# Spec §3.3 example: "Acme raised $10M" occupies excerpt[0:16].
VERIFY_EXAMPLES = [
    # (claim_text, excerpt, span, expected)
    ("Acme raised $10M", "Acme raised $10M in Series B", (0, 16), True),
    ("Acme raised $10M", "Acme raised $10M in Series B", (20, 30), False),
    ("Acme raised $10M", "Unrelated text here", None, False),
]


# ============================================================================
# SECTION 1 — INTERFACE TESTS
# ============================================================================


class TestClaimsInterface:
    """Imports, class/enum/model existence and method signatures (spec §3.3)."""

    def test_module_importable(self):
        """All five spec'd symbols import cleanly from src.forge.claims."""
        assert all(
            cls is not None
            for cls in (
                ClaimClassification,
                Claim,
                ProvenanceBlock,
                ClaimVerifier,
            )
        )

    def test_claim_classification_is_str_enum(self):
        """ClaimClassification is a str Enum with exactly the spec'd members."""
        assert issubclass(ClaimClassification, str)
        assert issubclass(ClaimClassification, Enum)

    @pytest.mark.parametrize("member,value", CLAIM_CLASSIFICATION_MEMBERS.items())
    def test_claim_classification_members(self, member, value):
        """Each enum member exists with the spec'd string value."""
        assert ClaimClassification[member].value == value

    @pytest.mark.parametrize("field,default", CLAIM_FIELDS.items())
    def test_claim_model_fields(self, field, default):
        """Claim declares the spec'd field (defaults validated behaviorally)."""
        assert field in Claim.model_fields
        if default is not None:
            assert Claim.model_fields[field].default == default

    @pytest.mark.parametrize("field,default", PROVENANCE_BLOCK_FIELDS.items())
    def test_provenance_block_fields(self, field, default):
        """ProvenanceBlock declares the spec'd field (defaults validated behaviorally)."""
        assert field in ProvenanceBlock.model_fields
        if default is not None:
            assert ProvenanceBlock.model_fields[field].default == default

    def test_verifier_init_defaults(self):
        """Default overlap_ratio is 0.5."""
        v = ClaimVerifier()
        assert v.overlap_ratio == 0.5

    def test_verifier_init_custom(self):
        """overlap_ratio is configurable."""
        assert ClaimVerifier(overlap_ratio=0.8).overlap_ratio == 0.8


class TestVerifierSignature:
    """Method signatures for ClaimVerifier (spec §3.3, exact)."""

    def test_verify_span_signature(self):
        sig = ClaimVerifier.verify_span.__signature__
        assert list(sig.parameters) == ["self", "claim_text", "excerpt", "span"]

    def test_classify_signature(self):
        sig = ClaimVerifier.classify.__signature__
        assert list(sig.parameters) == ["self", "text", "source", "judge"]
        assert sig.parameters["judge"].default is None

    def test_split_claims_signature(self):
        sig = ClaimVerifier.split_claims.__signature__
        assert list(sig.parameters) == ["self", "text"]


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (RED until developer implements §3.3)
# ============================================================================


class TestVerifySpanBehavior:
    """verify_span is a MECHANICAL token-overlap check (research risk #1)."""

    @pytest.mark.parametrize("claim,excerpt,span,expected", VERIFY_EXAMPLES)
    def test_spec_examples(self, claim, excerpt, span, expected):
        """Spec §3.3 example vectors behave exactly as documented."""
        v = ClaimVerifier()
        assert v.verify_span(claim, excerpt, span) is expected

    def test_no_span_never_trusted(self):
        """Span None => False even with a verbatim excerpt (never trusts citation)."""
        assert ClaimVerifier().verify_span("Acme raised $10M", "Acme raised $10M", None) is False

    def test_exact_match_overlaps(self):
        """Full overlap with the claim text verifies."""
        assert ClaimVerifier().verify_span("Acme raised $10M", "Acme raised $10M", (0, 16)) is True

    def test_partial_overlap_above_threshold(self):
        """Overlap ratio >= default 0.5 verifies (3/4 shared tokens)."""
        assert ClaimVerifier().verify_span("Acme raised $10M", "Acme raised $10M in Series B", (0, 11)) is True

    def test_below_threshold_rejected(self):
        """Overlap ratio < 0.5 rejects (1/4 shared tokens)."""
        assert ClaimVerifier().verify_span("Acme raised $10M", "Unrelated text here", (0, 7)) is False

    def test_out_of_bounds_span_rejected(self):
        """Span indices outside the excerpt reject."""
        assert ClaimVerifier().verify_span("Acme raised $10M", "Acme raised $10M in Series B", (40, 50)) is False

    def test_reversed_span_rejected(self):
        """Span with start > end is invalid and must not verify."""
        assert ClaimVerifier().verify_span("Acme raised $10M", "Acme raised $10M in Series B", (16, 0)) is False

    def test_custom_threshold(self):
        """Lower overlap_ratio tightens acceptance (token-level overlap semantics)."""
        assert ClaimVerifier(overlap_ratio=0.1).verify_span("Acme raised $10M", "Acme raised $10M in Series B", (0, 11)) is True


class TestClassifyBehavior:
    """classify: deterministic safe defaults + judge injection + verified flag."""

    def test_no_judge_with_source_unsupported(self):
        """Source present but no judge => unsupported (safe default)."""
        c = ClaimVerifier().classify("Acme raised $10M", source="https://example.com/round")
        assert c.classification == ClaimClassification.unsupported

    def test_no_source_unsupported(self):
        """No source and no judge => unsupported."""
        c = ClaimVerifier().classify("Acme raised $10M", source=None)
        assert c.classification == ClaimClassification.unsupported

    def test_i_think_prefix_opinion(self):
        """'I think' prefix => opinion."""
        c = ClaimVerifier().classify("I think this is great", source=None)
        assert c.classification == ClaimClassification.opinion

    def test_in_my_opinion_prefix_opinion(self):
        """'In my opinion' prefix => opinion."""
        c = ClaimVerifier().classify("In my opinion the market is ready", source=None)
        assert c.classification == ClaimClassification.opinion

    def test_judge_supported_sets_verified(self):
        """Judge returning supported with a source => verified True."""
        c = ClaimVerifier().classify(
            "Acme raised $10M",
            source="https://example.com/round",
            judge=lambda text, src: ClaimClassification.supported.value,
        )
        assert c.verified is True
        assert c.classification == ClaimClassification.supported

    def test_judge_opinion_never_verified(self):
        """Judge returning opinion => not verified regardless of source."""
        c = ClaimVerifier().classify(
            "I think this is great",
            source="https://example.com/round",
            judge=lambda text, src: ClaimClassification.opinion.value,
        )
        assert c.verified is False

    def test_supported_without_source_not_verified(self):
        """supported without a source => verified False (provenance requires source)."""
        c = ClaimVerifier().classify(
            "Acme raised $10M",
            source=None,
            judge=lambda text, src: ClaimClassification.supported.value,
        )
        assert c.classification == ClaimClassification.supported
        assert c.verified is False

    def test_classify_returns_claim(self):
        """classify returns a Claim instance (interface contract)."""
        c = ClaimVerifier().classify("Acme raised $10M", source="https://example.com/round")
        assert isinstance(c, Claim)


class TestSplitClaimsBehavior:
    """split_claims: [.!?] + newline sentence splitter, non-empty trimmed."""

    def test_spec_example(self):
        """Spec §3.3 example returns exactly the three trimmed sentences."""
        v = ClaimVerifier()
        assert v.split_claims("First sentence. Second one!\nThird") == [
            "First sentence.",
            "Second one!",
            "Third",
        ]

    def test_question_mark_splits(self):
        """Question mark is a sentence boundary."""
        assert ClaimVerifier().split_claims("Is this ready? Yes it is.") == [
            "Is this ready?",
            "Yes it is.",
        ]

    def test_newline_splits(self):
        """Newline is a sentence boundary."""
        assert ClaimVerifier().split_claims("Line one\nLine two") == ["Line one", "Line two"]

    def test_whitespace_trimmed(self):
        """Surrounding whitespace is trimmed from each sentence."""
        assert ClaimVerifier().split_claims("  First sentence.   Second!  ") == [
            "First sentence.",
            "Second!",
        ]

    def test_empty_input(self):
        """Empty input yields no sentences."""
        assert ClaimVerifier().split_claims("") == []


class TestProvenanceBlockBehavior:
    """ProvenanceBlock defaults — EU AI Act Art. 50(2)/50(3) markers."""

    def test_generated_by_ai_default_true(self):
        """generated_by_ai defaults True (Art. 50(2) transparency marker)."""
        block = ProvenanceBlock(brief_id="b1", channel="linkedin", sources=[], claims=[])
        assert block.generated_by_ai is True

    def test_human_reviewed_default_false(self):
        """human_reviewed defaults False until approval (Art. 50(3) exemption)."""
        block = ProvenanceBlock(brief_id="b1", channel="linkedin", sources=[], claims=[])
        assert block.human_reviewed is False

    def test_claims_embedded(self):
        """ProvenanceBlock carries a list of Claim models."""
        claim = Claim(claim_id="c1", text="Acme raised $10M", classification=ClaimClassification.unsupported)
        block = ProvenanceBlock(brief_id="b1", channel="x", sources=[], claims=[claim])
        assert block.claims == [claim]
