#!/usr/bin/env python3
"""
ContentForge — Compliance Scoring Example

Demonstrates scoring text against brand voice rules, including
banned term detection, vocabulary analysis, and readability.
"""

from brand_voice.presets import PresetManager
from brand_voice.compliance import ComplianceScorer


def main():
    print("=" * 60)
    print("Compliance Scoring — Brand Voice Checker")
    print("=" * 60)

    # Load a preset to use as the scoring baseline
    mgr = PresetManager()
    formal_profile = mgr.get_preset("formal")

    scorer = ComplianceScorer(formal_profile)

    # ── Clean text (should score 1.0) ─────────────────────────────────
    print("\n1. CLEAN TEXT — No violations expected")
    print("-" * 40)

    clean_text = (
        "We are pleased to announce our scalable platform. "
        "This enterprise-grade solution is proven to deliver robust results. "
        "Contact our team for further information."
    )

    result = scorer.score(clean_text)
    print(f"  Overall score:      {result.overall_score:.2f}")
    print(f"  Vocabulary score:   {result.vocabulary_score:.2f}")
    print(f"  Readability score:  {result.readability_score:.2f}")
    print(f"  Tone score:         {result.tone_score:.2f}")
    print(f"  Banned terms found: {result.banned_terms_found}")
    print(f"  Violations:         {result.violations}")

    # ── Text with banned terms ────────────────────────────────────────
    print("\n2. VIOLATION TEXT — Banned terms present")
    print("-" * 40)

    bad_text = (
        "We're gonna pivot our strategy. "
        "This kinda stuff is gonna disrupt the market."
    )

    result = scorer.score(bad_text)
    print(f"  Overall score:      {result.overall_score:.2f}")
    print(f"  Vocabulary score:   {result.vocabulary_score:.2f}")
    print(f"  Readability score:  {result.readability_score:.2f}")
    print(f"  Tone score:         {result.tone_score:.2f}")
    print(f"  Banned terms found: {result.banned_terms_found}")
    print(f"  Violations:         {result.violations}")

    # ── Individual rule checks ────────────────────────────────────────
    print("\n3. INDIVIDUAL CHECKS")
    print("-" * 40)

    text = "Our scalable solution is robust and reliable."

    # Banned term check
    found = scorer.check_banned_terms(text)
    print(f"  Banned terms in '{text}': {found}")

    # Vocabulary analysis
    analysis = scorer.check_vocabulary(text)
    print(f"  Vocabulary analysis: {analysis}")

    # Readability
    hard_text = ("The implementation necessitates comprehensive "
                 "evaluation of multifaceted interdependencies.")
    readability = scorer.check_readability(hard_text)
    print(f"  Readability (simple):     {scorer.check_readability(text):.2f}")
    print(f"  Readability (complex):    {readability:.2f}")

    # ── Comparison across presets ─────────────────────────────────────
    print("\n4. CROSS-PRESET COMPARISON")
    print("-" * 40)

    sample = (
        "Hey team! Here's a cool update about our awesome platform. "
        "We're excited to share some great news with you all!"
    )

    for preset_name in ["formal", "casual", "witty", "technical"]:
        profile = mgr.get_preset(preset_name)
        s = ComplianceScorer(profile)
        r = s.score(sample)
        print(f"  {preset_name:<12} — overall: {r.overall_score:.2f}, "
              f"banned: {r.banned_terms_found}, "
              f"readability: {r.readability_score:.2f}")


if __name__ == "__main__":
    main()
