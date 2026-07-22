"""
Pytest configuration and shared fixtures for brand voice tests.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from brand_voice.models import (
    FormattingPrefs,
    ScenarioTone,
    VocabularyRules,
    VoiceAttribute,
    VoiceProfile,
)


@pytest.fixture
def sample_voice_profile() -> VoiceProfile:
    """A realistic sample voice profile for a tech company."""
    return VoiceProfile(
        id="acme-corp-v1",
        name="Acme Corp Professional",
        description="Professional and approachable voice for Acme Corporation",
        brand_identity={
            "who": "Acme Corporation, a B2B SaaS company",
            "audience": "Engineering leaders and CTOs at mid-size tech companies",
            "purpose": "Build trust through transparent, data-driven communication",
        },
        attributes=[
            VoiceAttribute(name="formality", min_label="casual", max_label="formal", value=0.7),
            VoiceAttribute(name="humor", min_label="serious", max_label="playful", value=0.3),
            VoiceAttribute(name="enthusiasm", min_label="reserved", max_label="excited", value=0.6),
        ],
        vocabulary=VocabularyRules(
            preferred=["scalable", "robust", "proven", "enterprise-grade", "seamless"],
            banned=["crunch", "pivot", "disrupt", "synergy", "circle back"],
            jargon_level="light",
        ),
        scenarios=[
            ScenarioTone(
                scenario="incident",
                tone="transparent",
                instructions="Be direct about what happened, what was affected, and what's being done. "
                "No spin, no excuses. Include timeline and next steps.",
            ),
            ScenarioTone(
                scenario="launch",
                tone="excited",
                instructions="Celebrate the achievement. Highlight customer value, "
                "not features. Include data points.",
            ),
            ScenarioTone(
                scenario="support_reply",
                tone="empathetic",
                instructions="Acknowledge the frustration first. Provide clear next steps. "
                "No jargon. Use customer's name.",
            ),
        ],
        formatting=FormattingPrefs(
            heading_style="sentence",
            bullet_style="dash",
            citation_format="inline",
        ),
        metadata={
            "source_file": "BRAND_VOICE.md",
            "created_at": "2026-07-01T00:00:00Z",
            "version": "1.0.0",
        },
    )


@pytest.fixture
def preset_names() -> list[str]:
    """Expected built-in preset names."""
    return ["formal", "casual", "witty", "empathetic", "technical"]


@pytest.fixture
def scenario_names() -> list[str]:
    """Expected built-in scenario names."""
    return ["incident", "launch", "support_reply", "social_media", "faq"]


@pytest.fixture
def content_types() -> list[str]:
    """Expected content types for PromptBinder."""
    return ["email", "landing_page", "social_post", "faq", "support_reply"]


@pytest.fixture
def temp_dir() -> Path:
    """A temporary directory that cleans up after the test."""
    with TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def sample_text() -> str:
    """A sample text for compliance scoring."""
    return (
        "We are excited to announce our new scalable platform. "
        "This enterprise-grade solution is proven to deliver robust results. "
        "Contact our team for more information."
    )


@pytest.fixture
def sample_text_with_banned_terms() -> str:
    """Sample text containing banned marketing terms."""
    return (
        "We need to pivot our strategy and disrupt the market. "
        "Let's circle back on the synergy opportunities."
    )
