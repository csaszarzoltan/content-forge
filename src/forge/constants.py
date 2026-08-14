"""Content-Forge constants (spec §3.0, §3.1).

The validated channel id set for the entire forge workspace. Every module
that validates channel ids imports this constant — never re-declare the set.
"""

from __future__ import annotations

FORGE_CHANNELS: frozenset[str] = frozenset(
    {"blog", "email", "linkedin", "x", "instagram", "landing", "script"}
)

__all__ = ["FORGE_CHANNELS"]
