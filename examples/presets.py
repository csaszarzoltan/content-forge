#!/usr/bin/env python3
"""
ContentForge — Preset Management Example

Demonstrates custom preset CRUD operations: saving, listing,
retrieving, deleting, and remixing presets.
"""

from brand_voice.models import (
    VoiceProfile,
    VoiceAttribute,
    VocabularyRules,
    ScenarioTone,
    FormattingPrefs,
)
from brand_voice.presets import PresetManager
import tempfile
import os


def main():
    print("=" * 60)
    print("Preset Manager — Built-in Presets")
    print("=" * 60)

    mgr = PresetManager()

    # List all built-in presets
    builtins = mgr.list_builtins()
    print(f"Built-in presets ({len(builtins)}):")
    for name in builtins:
        profile = mgr.get_preset(name)
        print(f"  • {name:<15} — {profile.description}")

    print("\n" + "=" * 60)
    print("Preset Manager — Custom Presets")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as td:
        custom_dir = os.path.join(td, "presets")
        cmgr = PresetManager(custom_dir=custom_dir)

        # Create a custom voice profile from scratch
        my_profile = VoiceProfile(
            id="startup-inc-v1",
            name="Startup Inc.",
            description="Energetic and direct voice for a fast-moving startup",
            brand_identity={
                "who": "Startup Inc., a B2B SaaS company in growth stage",
                "audience": "Early-stage founders and VC scouts",
                "purpose": "Communicate ambition and velocity",
            },
            attributes=[
                VoiceAttribute(name="formality", min_label="casual", max_label="formal", value=0.3),
                VoiceAttribute(name="humor", min_label="serious", max_label="playful", value=0.7),
                VoiceAttribute(name="enthusiasm", min_label="reserved", max_label="excited", value=0.9),
            ],
            vocabulary=VocabularyRules(
                preferred=["growth", "scale", "velocity", "impact", "ship"],
                banned=["synergy", "circle back", "thought leadership", "going forward"],
                jargon_level="light",
            ),
            scenarios=[
                ScenarioTone(
                    scenario="launch",
                    tone="hype",
                    instructions="Amplify the energy. Use bold claims backed by data.",
                ),
                ScenarioTone(
                    scenario="incident",
                    tone="direct",
                    instructions="No fluff. Say what broke, why, and the fix timeline.",
                ),
            ],
            formatting=FormattingPrefs(
                heading_style="title",
                bullet_style="dash",
                citation_format="inline",
            ),
            metadata={"created_at": "2026-07-22", "author": "example"},
        )

        # Save custom preset
        cmgr.save_custom(my_profile, "startup-inc")
        print("Saved custom preset: 'startup-inc'")
        print(f"Custom presets: {cmgr.list_custom()}")

        # Retrieve it back
        retrieved = cmgr.get_preset("startup-inc")
        print(f"Retrieved: '{retrieved.name}' — {retrieved.description}")
        print(f"System prompt:\n{retrieved.to_system_prompt()}\n")

        # Remix a built-in preset
        print("-" * 40)
        print("Remixing 'formal' preset:")
        remixed = cmgr.remix("formal", {
            "name": "Semi-Formal",
            "description": "A slightly relaxed formal voice",
        })
        cmgr.save_custom(remixed, "semi-formal")
        print(f"  Remixed preset: '{remixed.name}' (preserved attributes from 'formal')")
        print(f"  Custom presets now: {cmgr.list_custom()}")

        # Delete custom preset
        cmgr.delete_custom("semi-formal")
        print("\nDeleted 'semi-formal'")
        print(f"Custom presets now: {cmgr.list_custom()}")

        # Attempt to delete non-existent preset
        try:
            cmgr.delete_custom("nonexistent")
        except KeyError as e:
            print(f"\nExpected error on delete: {e}")

    # After temp dir cleanup, custom presets are gone
    print("\n(Outside temp directory, no custom presets survive.)")


if __name__ == "__main__":
    main()
