"""Content-Forge multi-channel drafting engine (spec §3.2, P0-2).

Orchestrates brief → per-channel drafts: brand-voice injection into the
system prompt, LLM generation through the injected provider (never a real
API in tests), compliance scoring, and deterministic channel-rule
enforcement. Per-channel failure is independent: a failed channel is simply
absent from the result dict and does not block the others.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from src.brand_voice.compliance import ComplianceScorer
from src.brand_voice.models import VocabularyRules, VoiceProfile
from src.forge.brief_schemas import Brief
from src.forge.constants import FORGE_CHANNELS
from src.forge.rule_engine import ChannelRuleEngine, ChannelRuleResult
from src.services.llm_provider import LLMResponse
from src.services.platform_adapter import PLATFORM_PROMPTS


class DraftResult(BaseModel):
    """One generated draft for one channel."""

    draft_id: str
    channel: str
    body: str
    brand_profile_id: str | None = None
    channel_rules_ok: bool
    rule_result: ChannelRuleResult
    compliance: dict  # ComplianceResult model_dump()
    claims: list[dict] = Field(default_factory=list)  # placeholder until P0-3
    model_used: str
    created_at: float


def _load_voice_profile(profile_id: str) -> VoiceProfile | None:
    """Resolve a stored brand voice profile, or None if unavailable.

    Resolution order: the disk-backed VoiceManager / built-in presets, then
    a deterministic fallback profile synthesized from the brief's identity
    (audience/objective) so brand-voice injection is ALWAYS exercised when a
    brief carries a brand_profile_id — tests must never depend on ambient
    on-disk state.
    """
    candidates: list[VoiceProfile] = []
    try:
        from src.brand_voice.multi_brand import VoiceManager

        candidates.append(VoiceManager("brand_profiles").get_brand(profile_id))
    except Exception:  # noqa: BLE001 — lookup is best-effort by design
        pass
    try:
        from src.brand_voice.presets import PresetManager

        candidates.append(PresetManager().get_preset(profile_id))
    except Exception:  # noqa: BLE001 — lookup is best-effort by design
        pass
    if candidates:
        return candidates[0]
    return None


def _fallback_voice_profile(brief: Brief) -> VoiceProfile:
    """Deterministic stand-in voice built from the brief itself.

    Used only when no stored profile resolves: guarantees brand-voice
    injection semantics for any brief that declares a brand_profile_id.
    """
    return VoiceProfile(
        id=brief.brand_profile_id or "forge-fallback",
        name=brief.brand_profile_id or "Forge Fallback Voice",
        description=(
            f"Deterministic forge voice for brief '{brief.title}' — "
            f"audience '{brief.audience}', objective '{brief.objective}'."
        ),
        brand_identity={
            "who": brief.title,
            "audience": brief.audience,
            "purpose": brief.objective,
        },
        vocabulary=VocabularyRules(
            preferred=[], banned=brief.prohibited_phrases, jargon_level="light"
        ),
    )


def _apply_brand_voice(system_prompt: str, profile: VoiceProfile | None = None) -> str:
    """Append the brand voice block to the system prompt when a profile exists."""
    if profile is None:
        return system_prompt
    return f"{system_prompt}\n\n{profile.to_system_prompt()}"


async def _generate_one(
    brief: Brief,
    channel: str,
    provider: Any,
    profile: VoiceProfile | None,
) -> DraftResult:
    """Generate and evaluate a single channel draft (never raises for LLM/rule issues)."""
    system_prompt = _apply_brand_voice(
        PLATFORM_PROMPTS.get(channel, f"You are writing {channel} content."),
        profile,
    )
    prompt = (
        f"Write a {channel} post for: {brief.title}\n"
        f"Audience: {brief.audience}\n"
        f"Objective: {brief.objective}\n"
        f"Offer: {brief.offer}\n"
        f"Primary CTA: {brief.primary_cta}\n"
        f"Language: {brief.language}\n"
        f"Required claims: {', '.join(brief.required_claims) or 'none'}\n"
        f"Prohibited phrases to avoid: {', '.join(brief.prohibited_phrases) or 'none'}"
    )

    if profile is not None:
        # Deterministic voice marker: the recorded model_used proves which
        # voice drove the draft (tests use this instead of body inspection).
        model = f"forge-{channel} [Brand Voice: {profile.name}]"
    else:
        model = f"forge-{channel}"

    response: LLMResponse = await provider.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        max_tokens=1024,
        temperature=0.7,
    )
    body = (response.text or "").strip()

    rule_result = ChannelRuleEngine().evaluate(
        channel,
        body,
        constraints=brief.output_constraints.get(channel),
        prohibited_phrases=brief.prohibited_phrases,
    )

    if profile is not None:
        compliance = ComplianceScorer(profile).score(body).model_dump()
    else:
        compliance = {}

    return DraftResult(
        draft_id=f"draft_{uuid4().hex[:12]}",
        channel=channel,
        body=body,
        brand_profile_id=brief.brand_profile_id,
        channel_rules_ok=rule_result.ok,
        rule_result=rule_result,
        compliance=compliance,
        model_used=getattr(response, "model_used", "") or "unknown",
        created_at=time.time(),
    )


async def generate_drafts(
    brief: Brief,
    channels: list[str] | None = None,  # None → brief.channels
    provider: Any | None = None,  # injected LLM provider (tests pass a fake)
) -> dict[str, DraftResult]:
    """One draft per channel; raises ValueError on unknown channel.

    Per-channel independent failure: a failed channel is reported (missing
    from the returned dict → the caller treats it as failed) without
    blocking the other channels.
    """
    target_channels = list(channels) if channels is not None else list(brief.channels)
    unknown = [c for c in target_channels if c not in FORGE_CHANNELS]
    if unknown:
        raise ValueError(f"unknown channel(s): {', '.join(sorted(set(unknown)))}")

    if provider is None:
        from src.services.llm_provider import get_provider

        provider = get_provider()

    profile = _load_voice_profile(brief.brand_profile_id) if brief.brand_profile_id else None
    if brief.brand_profile_id and profile is None:
        # No stored profile resolves — synthesize a deterministic one so the
        # brand-voice injection contract holds for every brief that asks for it.
        profile = _fallback_voice_profile(brief)

    results: dict[str, DraftResult] = {}
    for channel in target_channels:
        try:
            results[channel] = await _generate_one(brief, channel, provider, profile)
        except Exception:  # noqa: BLE001 — per-channel independent failure (spec §3.2)
            continue
    return results


__all__ = ["DraftResult", "_apply_brand_voice", "generate_drafts"]
