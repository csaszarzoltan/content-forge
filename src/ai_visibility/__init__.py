"""AI Visibility Metrics package (analysis brief §5).

Re-exports the public surface: constants, ``AiVisibilityService``, and the
REST router. Importing this package registers the router module (routes are
defined at import time); the ORM models are registered with ``Base.metadata``
only after the developer implements them (see ``models.py`` docstring).
"""

from __future__ import annotations

from src.ai_visibility.models import (
    AI_ENGINES,
    AI_ENGINE_REFERRER_DOMAINS,
    AI_METRICS,
    AI_SENTIMENTS,
    AI_TREND_PERIODS,
)
from src.ai_visibility.router import router
from src.ai_visibility.service import AiVisibilityService

__all__ = [
    "AI_ENGINES",
    "AI_ENGINE_REFERRER_DOMAINS",
    "AI_METRICS",
    "AI_SENTIMENTS",
    "AI_TREND_PERIODS",
    "AiVisibilityService",
    "router",
]
