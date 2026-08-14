"""Compatibility shim: re-export the shared brand voice models (spec §3.2).

The real implementation lives in src/brand_voice/models.py; this module
aliases it under the Content-Forge namespace so drafting tests can import
``src.forge.brand_voice.models``.
"""

from __future__ import annotations

from src.brand_voice.models import (  # noqa: F401
    FormattingPrefs,
    ScenarioTone,
    VocabularyRules,
    VoiceAttribute,
    VoiceProfile,
)

__all__ = ["FormattingPrefs", "ScenarioTone", "VocabularyRules", "VoiceAttribute", "VoiceProfile"]
