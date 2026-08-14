"""Interface + behavioral tests for Content-Forge P0-2 — ChannelRuleEngine.

Interface tests assert the exact public surface (imports, enums, pydantic
models, method signatures) — these PASS once the module exists with the
specified names and FAIL cleanly today (module absent → ModuleNotFoundError,
the RED signal the developer resolves by creating src/forge/rule_engine.py).

Behavioral tests encode the deterministic rule semantics from
analysis/forge-spec.md §3.2:

- char limit from ConstraintRegistry → "channel.max_chars" HARD
  (message names observed vs limit)
- prohibited phrase hit → "channel.prohibited_phrase" HARD
  (positions = match spans)
- hashtag count > registry max_hashtags → "channel.max_hashtags" HARD
- required_sections missing → "channel.required_section" SOFT
- reading_level keywords absent → "channel.reading_level" SOFT
- ok == no hard violations

All imports of the not-yet-written module happen INSIDE test functions so
the RED signal is a clean per-test ModuleNotFoundError (repo convention —
never stub-guard with pytest.raises(NotImplementedError)).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

# ── Interface tests ─────────────────────────────────────────────────────────


def test_rule_engine_module_exists():
    """RED until the developer creates src/forge/rule_engine.py."""
    import src.forge.rule_engine  # noqa: F401


def test_ruleseverity_enum_values():
    from src.forge.rule_engine import RuleSeverity

    assert RuleSeverity.hard.value == "hard"
    assert RuleSeverity.soft.value == "soft"


def test_ruleviolation_fields():
    from src.forge.rule_engine import RuleViolation

    assert "rule_id" in RuleViolation.model_fields
    assert "channel" in RuleViolation.model_fields
    assert "severity" in RuleViolation.model_fields
    assert "message" in RuleViolation.model_fields
    assert "positions" in RuleViolation.model_fields


def test_ruleviolation_positions_default_empty():
    from src.forge.rule_engine import RuleSeverity, RuleViolation

    v = RuleViolation(
        rule_id="channel.max_chars", channel="x", severity=RuleSeverity.hard, message="m"
    )
    assert v.positions == []


def test_channelruleresult_fields_and_defaults():
    from src.forge.rule_engine import ChannelRuleResult

    assert "channel" in ChannelRuleResult.model_fields
    assert "ok" in ChannelRuleResult.model_fields
    assert "violations" in ChannelRuleResult.model_fields
    assert "warnings" in ChannelRuleResult.model_fields
    r = ChannelRuleResult(channel="x", ok=True)
    assert r.violations == []
    assert r.warnings == []


def test_channelruleengine_signatures():
    from src.forge.rule_engine import ChannelRuleEngine

    init_sig = inspect.signature(ChannelRuleEngine.__init__)
    assert "registry" in init_sig.parameters
    assert init_sig.parameters["registry"].default is None

    eval_sig = inspect.signature(ChannelRuleEngine.evaluate)
    assert list(eval_sig.parameters)[:4] == ["self", "channel", "text", "constraints"]
    assert eval_sig.parameters["constraints"].default is None
    assert "prohibited_phrases" in eval_sig.parameters
    assert eval_sig.parameters["prohibited_phrases"].default is None

    eval_all_sig = inspect.signature(ChannelRuleEngine.evaluate_all)
    assert list(eval_all_sig.parameters)[:3] == ["self", "drafts", "brief"]


def test_rule_engine_accepts_registry():
    """Engine must accept the existing ConstraintRegistry (default None)."""
    from src.forge.rule_engine import ChannelRuleEngine

    registry = _load_registry()
    engine = ChannelRuleEngine(registry=registry)
    assert engine is not None


# ── Behavioral tests (RED until implemented) ────────────────────────────────


def _load_registry():
    """Load the repo's ConstraintRegistry from its default JSON."""
    from src.constraints.registry import ConstraintRegistry

    registry = ConstraintRegistry()
    registry.load()
    return registry


def test_ok_true_when_no_hard_violations():
    from src.forge.rule_engine import ChannelRuleEngine

    engine = ChannelRuleEngine(registry=_load_registry())
    result = engine.evaluate("x", "Concise update.")
    assert result.channel == "x"
    assert result.ok is True
    assert result.violations == []
    assert result.warnings == []


def test_max_chars_hard_when_exceeded():
    from src.forge.rule_engine import RuleSeverity

    engine = _make_engine()
    result = engine.evaluate("x", "y" * 400)
    assert result.ok is False
    hard = [v for v in result.violations if v.severity == RuleSeverity.hard]
    assert any(v.rule_id == "channel.max_chars" for v in hard)
    offending = next(v for v in result.violations if v.rule_id == "channel.max_chars")
    assert "400" in offending.message and "280" in offending.message


def _make_engine():
    from src.forge.rule_engine import ChannelRuleEngine

    return ChannelRuleEngine(registry=_load_registry())


def test_prohibited_phrase_hard_with_positions():
    from src.forge.rule_engine import RuleSeverity

    engine = _make_engine()
    result = engine.evaluate(
        "email", "Buy now today and save.", prohibited_phrases=["buy now"]
    )
    hard = [v for v in result.violations if v.severity == RuleSeverity.hard]
    hit = next(v for v in hard if v.rule_id == "channel.prohibited_phrase")
    assert hit.positions == [(0, 7)]
    assert result.ok is False


def test_hashtags_over_budget_hard():
    from src.forge.rule_engine import RuleSeverity

    registry = _load_registry()
    # instagram allows max_hashtags=30; fabricate a tight budget via a copy
    from src.constraints.models import PlatformConstraints

    from src.forge.rule_engine import ChannelRuleEngine

    constraints = registry.get("instagram")
    tight = PlatformConstraints(
        display_name=constraints.display_name,
        text=constraints.text.model_copy(update={"max_hashtags": 2}),
        image=constraints.image,
        video=constraints.video,
        media_per_post=constraints.media_per_post,
        rate_limits=constraints.rate_limits,
        auth=constraints.auth,
    )
    registry.update("instagram", tight)
    engine = ChannelRuleEngine(registry=registry)
    result = engine.evaluate(
        "instagram",
        "Great post #a #b #c #d about our launch #e",
    )
    hard = [v for v in result.violations if v.severity == RuleSeverity.hard]
    assert any(v.rule_id == "channel.max_hashtags" for v in hard)
    assert result.ok is False


def test_required_sections_missing_is_soft():
    from src.forge.rule_engine import RuleSeverity

    registry = _load_registry()
    from src.forge.brief_schemas import OutputConstraints

    engine = _make_engine()
    constraints = OutputConstraints(required_sections=["pricing", "testimonials"])
    result = engine.evaluate("blog", "Just a short body.", constraints=constraints)
    soft = [v for v in result.violations if v.severity == RuleSeverity.soft]
    assert any(v.rule_id == "channel.required_section" for v in soft)
    # soft-only → ok stays True
    assert result.ok is True


def test_reading_level_keywords_absent_is_soft():
    from src.forge.rule_engine import RuleSeverity

    from src.forge.brief_schemas import OutputConstraints

    engine = _make_engine()
    constraints = OutputConstraints(
        reading_level="specialist", keywords=["scalable", "enterprise"]
    )
    result = engine.evaluate("blog", "Plain words only here.", constraints=constraints)
    soft = [v for v in result.violations if v.severity == RuleSeverity.soft]
    assert any(v.rule_id == "channel.reading_level" for v in soft)
    assert result.ok is True


def test_ok_is_false_with_any_hard_violation():
    from src.forge.rule_engine import ChannelRuleEngine

    engine = ChannelRuleEngine(registry=_load_registry())
    result = engine.evaluate("x", "y" * 400, prohibited_phrases=["zzz"])
    assert result.ok is False


def test_evaluate_all_aggregates_per_channel():
    from src.forge.brief_schemas import Brief

    from src.forge.rule_engine import ChannelRuleEngine

    engine = ChannelRuleEngine(registry=_load_registry())
    brief = Brief(
        brief_id="b1",
        title="Launch",
        audience="CTOs",
        objective="Announce",
        offer="Platform",
        primary_cta="Sign up",
        channels=["x", "blog"],
    )
    results = engine.evaluate_all({"x": "y" * 400, "blog": "Fine body."}, brief)
    assert set(results.keys()) == {"x", "blog"}
    assert results["x"].ok is False
    assert results["blog"].ok is True
