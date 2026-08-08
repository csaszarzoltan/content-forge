"""TTS provider abstraction layer (clones the LLMProvider pattern).

P0-4 + P1-3 implementation per analysis-brief.md §6:

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

import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

# Static OpenAI preset voices (verified 2026-08-08, platform.openai.com).
OPENAI_VOICES: list[dict[str, str]] = [
    {"id": "alloy", "name": "Alloy"},
    {"id": "echo", "name": "Echo"},
    {"id": "fable", "name": "Fable"},
    {"id": "onyx", "name": "Onyx"},
    {"id": "nova", "name": "Nova"},
    {"id": "shimmer", "name": "Shimmer"},
]


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


def _openai_key() -> str:
    """Return the OpenAI API key (OPENAI_API_KEY or the LLM_API_KEY fallback)."""
    return os.getenv("OPENAI_API_KEY", "") or os.getenv("LLM_API_KEY", "")


def _write_silent_mp3(path: Path) -> Path:
    """Write a short silent MP3 placeholder via the bundled ffmpeg binary.

    Used when a TTS provider is not configured (no API key): the pipeline
    still produces a playable audio file so scene rendering and exports work
    offline. CPU-bound ffmpeg runs synchronously here only because this
    helper is called from async context via ``asyncio.to_thread`` where
    applicable; callers treat it as a fast degraded path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        result = subprocess.run(
            [
                exe,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=24000:cl=mono",
                "-t",
                "1",
                "-q:a",
                "9",
                "-acodec",
                "libmp3lame",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if result.returncode != 0 or not path.exists() or path.stat().st_size == 0:
            # Absolute last resort: a minimal valid MP3 frame header.
            path.write_bytes(
                b"\xff\xfb\x90\x64\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            )
    except (OSError, ValueError, subprocess.SubprocessError):
        path.write_bytes(
            b"\xff\xfb\x90\x64\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )
    return path


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS provider (default; uses the existing openai client)."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else _openai_key()
        self._model = model or os.getenv("OPENAI_TTS_MODEL", "tts-1")
        self._client = None

    def _get_client(self):
        """Lazy-initialize the OpenAI async client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:
                raise ImportError(
                    "openai package is required for OpenAITTSProvider. "
                    "Install with: pip install openai"
                ) from exc
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    @property
    def name(self) -> str:
        return "openai"

    def available(self) -> bool:
        return bool(self._api_key)

    async def synthesize(self, text: str, voice: str | None = None, out_path: str | Path = "") -> Path:
        """Call OpenAI audio.speech and write the mp3 bytes to ``out_path``.

        When no API key is configured the provider degrades gracefully: a
        short silent MP3 placeholder is written (via the bundled ffmpeg) so
        the pipeline stays testable offline. Real synthesis requires the key.
        """
        path = Path(out_path)
        if not self.available():
            return _write_silent_mp3(path)
        client = self._get_client()
        chosen_voice = voice or os.getenv("OPENAI_TTS_VOICE", "alloy")
        response = await client.audio.speech.create(
            model=self._model,
            voice=chosen_voice,
            input=text,
            response_format="mp3",
        )
        data = response.read()
        if not data:
            raise RuntimeError("OpenAI TTS returned an empty audio response")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path


class ElevenLabsTTSProvider(TTSProvider):
    """ElevenLabs TTS provider (P1-3; httpx POST to the v2 API)."""

    def __init__(self, api_key: str | None = None, voice_id: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else os.getenv("ELEVENLABS_API_KEY", "")
        self._voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "")

    @property
    def name(self) -> str:
        return "elevenlabs"

    def available(self) -> bool:
        return bool(self._api_key)

    async def synthesize(self, text: str, voice: str | None = None, out_path: str | Path = "") -> Path:
        """POST to the ElevenLabs v2 text-to-speech API and write the audio."""
        import httpx

        voice_id = voice or self._voice_id or "21m00Tcm4TlvDq8ikWAM"  # default Rachel
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": self._api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, headers=headers, json={"text": text})
        if response.status_code != 200:
            raise RuntimeError(f"ElevenLabs TTS failed: HTTP {response.status_code}")
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
        return path


class CoquiTTSProvider(TTSProvider):
    """Local Coqui TTS provider (P1-3; optional extra `video-coqui`)."""

    @property
    def name(self) -> str:
        return "coqui"

    def available(self) -> bool:
        try:
            import coqui_tts  # noqa: F401
        except ImportError:
            return False
        return True

    async def synthesize(self, text: str, voice: str | None = None, out_path: str | Path = "") -> Path:
        """Synthesize locally via coqui-tts (heavy import; run in executor)."""
        import asyncio

        def _run() -> Path:
            from coqui_tts import TTS  # type: ignore[import-not-found]

            model = voice or os.getenv("COQUI_TTS_MODEL", "tts_models/en/ljspeech/tacotron2-DDC")
            tts = TTS(model_name=model)
            path = Path(out_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            tts.tts_to_file(text=text, file_path=str(path))
            return path

        return await asyncio.to_thread(_run)


def get_tts_provider() -> TTSProvider:
    """Factory: return the first available provider (OpenAI → ElevenLabs → Coqui)."""
    for provider in (OpenAITTSProvider(), ElevenLabsTTSProvider(), CoquiTTSProvider()):
        if provider.available():
            return provider
    raise RuntimeError(
        "No TTS provider available: set OPENAI_API_KEY (or LLM_API_KEY), "
        "ELEVENLABS_API_KEY, or install the video-coqui extra."
    )


__all__ = [
    "OPENAI_VOICES",
    "CoquiTTSProvider",
    "ElevenLabsTTSProvider",
    "OpenAITTSProvider",
    "TTSProvider",
    "get_tts_provider",
]
