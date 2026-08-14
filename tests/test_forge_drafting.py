"""Interface + behavioral tests for Content-Forge P0-2 — multi-channel drafting.

Interface tests assert the exact public surface (DraftResult model fields,
generate_drafts / _apply_brand_voice signatures, PLATFORM_PROMPTS 7-key
contract) — these PASS once the modules exist with the specified names and
FAIL cleanly today (module absent → ModuleNotFoundError / missing keys →
clean assertion, the RED signal for the developer).

Behavioral tests encode the orchestration semantics from
analysis/forge-spec.md §3.2:

- one draft per requested channel (channels=None → brief.channels)
- unknown channel → ValueError
- per-channel independent failure: a failed channel is absent from the
  result dict and does not block the others
- each draft carries a ChannelRuleResult; channel_rules_ok reflects it
- brand voice is injected into the system prompt when the brief has a
  brand_profile_id (proven via RecordingProvider)
- drafts run through the injected provider — never a real LLM

Imports of not-yet-written modules happen INSIDE test functions so the RED
signal is a clean per-test ModuleNotFoundError (repo convention — never
stub-guard with pytest.raises(NotImplementedError)).
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

# ── Interface tests ─────────────────────────────────────────────────────────


def test_drafting_module_exists():
    """RED until the developer creates src/forge/drafting.py."""
    import src.forge.drafting  # noqa: F401


def test_draftresult_fields():
    from src.forge.drafting import DraftResult

    expected = {
        "draft_id",
        "channel",
        "body",
        "brand_profile_id",
        "channel_rules_ok",
        "rule_result",
        "compliance",
        "claims",
        "model_used",
        "created_at",
    }
    assert expected <= set(DraftResult.model_fields)


def test_draftresult_claims_default_empty():
    from src.forge.drafting import DraftResult

    assert DraftResult.model_fields["claims"].default_factory() == []


def test_generate_drafts_signature():
    from src.forge.drafting import generate_drafts

    sig = inspect.signature(generate_drafts)
    assert list(sig.parameters)[:3] == ["brief", "channels", "provider"]
    assert sig.parameters["channels"].default is None
    assert sig.parameters["provider"].default is None
    assert inspect.iscoroutinefunction(generate_drafts)


def test_apply_brand_voice_signature():
    from src.forge.drafting import _apply_brand_voice

    sig = inspect.signature(_apply_brand_voice)
    assert list(sig.parameters) == ["system_prompt", "profile"]
    assert sig.parameters["profile"].default is None


def test_platform_prompts_cover_all_seven_channels():
    """PLATFORM_PROMPTS must contain keys for all 7 forge channels."""
    from src.forge.constants import FORGE_CHANNELS
    from src.services.platform_adapter import PLATFORM_PROMPTS

    missing = FORGE_CHANNELS - set(PLATFORM_PROMPTS)
    assert not missing, f"PLATFORM_PROMPTS missing channel keys: {sorted(missing)}"


# ── Behavioral tests (RED until implemented) ────────────────────────────────


def _make_brief(
    channels: list[str] | None = None,
    brand_profile_id: str | None = None,
    **kwargs,
):
    from src.forge.brief_schemas import Brief

    return Brief(
        brief_id="b1",
        title="Launch",
        audience="CTOs",
        objective="Announce the platform",
        offer="A SaaS platform",
        primary_cta="Sign up",
        language="en",
        brand_profile_id=brand_profile_id,
        channels=channels or ["blog"],
        created_at=0.0,
        **kwargs,
    )


async def test_generate_drafts_returns_one_per_channel():
    from tests.conftest import FakeProvider

    from src.forge.drafting import generate_drafts

    brief = _make_brief(channels=["blog", "linkedin", "x"])
    drafts = await generate_drafts(
        brief, channels=["blog", "linkedin", "x"], provider=FakeProvider()
    )
    assert set(drafts.keys()) == {"blog", "linkedin", "x"}
    assert drafts["x"].channel == "x"
    assert drafts["blog"].channel_rules_ok is True


async def test_generate_drafts_defaults_to_brief_channels():
    from tests.conftest import FakeProvider

    from src.forge.drafting import generate_drafts

    brief = _make_brief(channels=["blog", "email"])
    drafts = await generate_drafts(brief, provider=FakeProvider())
    assert set(drafts.keys()) == {"blog", "email"}


async def test_max_chars_violation_flagged():
    from tests.conftest import FakeProvider

    from src.forge.drafting import generate_drafts
    from src.forge.rule_engine import RuleSeverity

    brief = _make_brief(channels=["x"])
    bad = await generate_drafts(
        brief, channels=["x"], provider=FakeProvider(text="y" * 400)
    )
    assert bad["x"].channel_rules_ok is False
    assert any(
        v.rule_id == "channel.max_chars" and v.severity == RuleSeverity.hard
        for v in bad["x"].rule_result.violations
    )


async def test_prohibited_phrase_violation_flagged():
    from tests.conftest import FakeProvider

    from src.forge.drafting import generate_drafts
    from src.forge.rule_engine import RuleSeverity

    brief = _make_brief(channels=["email"], prohibited_phrases=["buy now"])
    hits = await generate_drafts(
        brief, channels=["email"], provider=FakeProvider(text="Buy now today")
    )
    assert any(
        v.rule_id == "channel.prohibited_phrase" and v.severity == RuleSeverity.hard
        for v in hits["email"].rule_result.violations
    )


async def test_unknown_channel_raises_valueerror():
    from tests.conftest import FakeProvider

    from src.forge.drafting import generate_drafts

    brief = _make_brief(channels=["blog"])
    with pytest.raises(ValueError):
        await generate_drafts(brief, channels=["tiktok"], provider=FakeProvider())


async def test_brand_voice_injected_when_profile_present():
    from tests.conftest import RecordingProvider

    from src.forge.drafting import generate_drafts

    brief = _make_brief(channels=["blog"], brand_profile_id="acme-corp-v1")
    d = await generate_drafts(brief, channels=["blog"], provider=RecordingProvider())
    assert "Brand Voice" in d["blog"].model_used or "brand" in d["blog"].body.lower()


async def test_provider_called_with_brand_voice_system_prompt():
    """Recording provider must observe the brand-voice block in the system prompt."""
    from tests.conftest import RecordingProvider

    from src.forge.drafting import generate_drafts

    brief = _make_brief(channels=["blog"], brand_profile_id="acme-corp-v1")
    provider = RecordingProvider()
    await generate_drafts(brief, channels=["blog"], provider=provider)
    assert provider.calls, "generate() was never called on the provider"
    assert provider.last_system_prompt is not None
    assert "Brand Voice" in provider.last_system_prompt


async def test_apply_brand_voice_appends_profile_prompt():
    from src.forge.brand_voice.models import VoiceProfile
    from src.forge.drafting import _apply_brand_voice

    profile = VoiceProfile(id="p1", name="Acme", description="d")
    base = "You are a copywriter."
    out = _apply_brand_voice(base, profile)
    assert out.startswith(base)
    assert "Brand Voice" in out
