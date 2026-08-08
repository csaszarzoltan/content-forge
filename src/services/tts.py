"""TTS provider abstraction layer (clones the LLMProvider pattern).

PROVISIONAL STUB — pre-development scaffold (pre-tester, t_ba5cfcec).
The ABC + factory + concrete providers are scaffolded so interface tests
import cleanly; runtime behavior is implemented by the developer per
analysis-brief.md §6 (P0-4, P1-3):

  TTSProvider ABC:
      async synthesize(text, voice, out_path) -> Path
      available() -> bool
      name: str
  OpenAITTSProvider      — uses the openai client audio.speech API
  ElevenLabsTTSProvider  — httpx POST to the ElevenLabs v2 API (P1)
  CoquiTTSProvider       — local coqui-tts (optional extra `video-coqui`, P1)
  get_tts_provider()     — factory, first available in chain
                            OpenAI → ElevenLabs → Coqui
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    """Abstract base for text-to-speech integrations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name, e.g. 'openai'."""

    @abstractmethod
    def available(self) -> bool:
        """Whether this provider can synthesize right now (key present, import ok)."""

    @abstractmethod
    async def synthesize(self, text: str, voice: str | None = None, out_path: str | Path = "") -> Path:
        """Synthesize ``text`` into an audio file at ``out_path`` and return the path."""


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS provider (default; uses the existing openai client)."""

    @property
    def name(self) -> str:
        raise NotImplementedError("TTS stub — not implemented yet")

    def available(self) -> bool:
        raise NotImplementedError("TTS stub — not implemented yet")

    async def synthesize(self, text: str, voice: str | None = None, out_path: str | Path = "") -> Path:
        raise NotImplementedError("TTS stub — not implemented yet")


class ElevenLabsTTSProvider(TTSProvider):
    """ElevenLabs TTS provider (P1-3; httpx POST to the v2 API)."""

    @property
    def name(self) -> str:
        raise NotImplementedError("TTS stub — not implemented yet")

    def available(self) -> bool:
        raise NotImplementedError("TTS stub — not implemented yet")

    async def synthesize(self, text: str, voice: str | None = None, out_path: str | Path = "") -> Path:
        raise NotImplementedError("TTS stub — not implemented yet")


class CoquiTTSProvider(TTSProvider):
    """Local Coqui TTS provider (P1-3; optional extra `video-coqui`)."""

    @property
    def name(self) -> str:
        raise NotImplementedError("TTS stub — not implemented yet")

    def available(self) -> bool:
        raise NotImplementedError("TTS stub — not implemented yet")

    async def synthesize(self, text: str, voice: str | None = None, out_path: str | Path = "") -> Path:
        raise NotImplementedError("TTS stub — not implemented yet")


def get_tts_provider() -> TTSProvider:
    """Factory: return the first available provider (OpenAI → ElevenLabs → Coqui)."""
    raise NotImplementedError("TTS stub — not implemented yet")


__all__ = [
    "CoquiTTSProvider",
    "ElevenLabsTTSProvider",
    "OpenAITTSProvider",
    "TTSProvider",
    "get_tts_provider",
]
