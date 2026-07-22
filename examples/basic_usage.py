#!/usr/bin/env python3
"""
ContentForge — Basic Usage Example

Demonstrates loading a preset, generating a system prompt,
rendering scenario templates, and multi-brand management.
"""

from brand_voice.presets import PresetManager
from brand_voice.templates import TemplateEngine
from brand_voice.multi_brand import VoiceManager
from brand_voice.prompt_binding import PromptBinder
from brand_voice.scoping import VoiceScope
import tempfile
import os


def main():
    # ── 1. Load a built-in preset ────────────────────────────────────
    print("=" * 60)
    print("1. Loading a built-in preset")
    print("=" * 60)

    mgr = PresetManager()
    print("Built-in presets:", mgr.list_builtins())

    profile = mgr.get_preset("formal")
    print(f"\nLoaded preset: '{profile.name}'")
    print(f"Description: {profile.description}")
    print(f"Formality: {profile.attributes[0].value} "
          f"({profile.attributes[0].min_label} ↔ {profile.attributes[0].max_label})")
    print(f"Preferred vocab: {profile.vocabulary.preferred}")
    print(f"Banned vocab: {profile.vocabulary.banned}")

    # ── 2. Generate a system prompt for LLM injection ────────────────
    print("\n" + "=" * 60)
    print("2. Generating a system prompt")
    print("=" * 60)

    prompt = profile.to_system_prompt()
    print(prompt)

    # ── 3. Render scenario templates ─────────────────────────────────
    print("\n" + "=" * 60)
    print("3. Rendering scenario templates")
    print("=" * 60)

    engine = TemplateEngine()
    print("Available scenarios:", engine.list_scenarios())

    incident_prompt = engine.render("incident", profile)
    print("\n--- Incident Response ---")
    print(incident_prompt[:300] + "...\n")

    launch_prompt = engine.render(
        "launch",
        profile,
        context={"product_name": "Acme Cloud", "release_date": "Q3 2026"},
    )
    print("\n--- Product Launch ---")
    print(launch_prompt[:300] + "...\n")

    # ── 4. System prompt with scenario ───────────────────────────────
    print("\n" + "=" * 60)
    print("4. System prompt with scenario")
    print("=" * 60)

    system = engine.render_system_prompt(profile, scenario="support_reply")
    print(system[:400] + "...\n")

    # ── 5. Multi-brand management ────────────────────────────────────
    print("\n" + "=" * 60)
    print("5. Multi-brand management")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as td:
        vm = VoiceManager(os.path.join(td, "brands"))

        # Create two brands
        formal = mgr.get_preset("formal")
        casual = mgr.get_preset("casual")

        brand_a = vm.create_brand("Corporate", formal)
        brand_b = vm.create_brand("Community", casual)

        print(f"All brands: {vm.list_brands()}")

        # Set active scope
        vm.set_active(brand_a, scope="global")
        vm.set_active(brand_b, scope="community")

        active_global = vm.get_active(scope="global")
        active_community = vm.get_active(scope="community")
        print(f"Global active: {active_global.name}")
        print(f"Community active: {active_community.name}")

    # ── 6. Prompt binding ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("6. Prompt binding")
    print("=" * 60)

    binder = PromptBinder(TemplateEngine())
    print("Content types:", binder.list_content_types())

    email_prompt = binder.create_prompt(
        content_type="email",
        profile=profile,
        topic="Q3 Performance Review",
        audience="Stakeholders",
    )
    print("\n--- Email Prompt ---")
    print(email_prompt)

    # ── 7. Voice scoping ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("7. Voice scoping")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as td:
        vs = VoiceScope(os.path.join(td, "config"))

        vs.set_user_voice("user-alice", brand_a)
        vs.set_project_voice("project-docs", brand_b)

        # Resolution: project overrides user
        resolved = vs.resolve("user-alice", "project-docs")
        print(f"Resolved voice for alice@docs: {resolved} (should be {brand_b})")

        # Fallback: user voice when no project voice
        resolved = vs.resolve("user-alice", "unknown-project")
        print(f"Resolved voice for alice@unknown: {resolved} (should be {brand_a})")

        # No voice at all
        resolved = vs.resolve("new-user")
        print(f"Resolved voice for new-user: {resolved} (should be None)")


if __name__ == "__main__":
    main()
