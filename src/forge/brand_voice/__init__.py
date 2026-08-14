"""Compatibility shim: src.forge.brand_voice re-exports the real brand_voice
package (spec §3.2 — drafting reuses src/brand_voice/, never rebuilds it).

Tests import ``src.forge.brand_voice.models``; keep the alias so the
Content-Forge namespace is self-contained while the implementation lives in
the shared src/brand_voice/ package.
"""

from __future__ import annotations

from src.forge.brand_voice.models import *  # noqa: F401,F403
