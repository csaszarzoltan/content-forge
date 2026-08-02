"""Regression tests for tech-lead review findings B1-B5 (commit 79d3846).

New file on purpose: the review explicitly asks for added tests while the
pre-written test files stay untouched. Covers:

- B1 (CRITICAL): a configured provider failure must never leak the API key
  into a ProviderError message — even when the underlying httpx exception
  string embeds the keyed request URL (Gemini sends the key as a query
  param; Perplexity in the Authorization header).
- B2 (HIGH): ``get_content_visibility`` validates ``days`` in {7,30,90}
  before any lookup (days=10**15 previously blew up in ``timedelta`` as an
  unhandled OverflowError -> 500); router maps it to 422.
- B4 (MEDIUM): ``_target_url`` honors ``AI_VISIBILITY_CONTENT_BASE_URL``
  and falls back to the reserved ``.example`` placeholder when empty.
- B5 (P1): POST /{content_id}/refresh — 404 for unknown generations, runs
  ``poll_once`` for the given content on the happy path, and works
  standalone (builds a poller from ``ProviderRegistry.from_settings`` when
  ``app.state.ai_poller`` is None).
"""

from __future__ import annotations

import types
from datetime import UTC, datetime

import httpx
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai_visibility.poller import AiVisibilityPoller
from src.ai_visibility.providers import (
    GeminiProvider,
    PerplexityProvider,
    ProviderError,
    ProviderRegistry,
)
from src.ai_visibility.router import (
    get_content_visibility,
    refresh_content_visibility,
)
from src.ai_visibility.schemas import PollResult
from src.ai_visibility.service import AiVisibilityService
from src.config import Settings
from tests.ai_visibility_test_utils import seed_generation

API_KEY = "sk-secret-test-key-9f2c1d"


# ============================================================================
# B1 — ProviderError messages never leak the API key
# ============================================================================


class _KeyedURLErrorClient:
    """Fake httpx.AsyncClient: POST fails with an HTTPStatusError whose
    message embeds the request URL carrying ``?key=<api_key>`` — exactly the
    shape a real Gemini ``raise_for_status()`` produces on older httpx
    (``httpx>=0.27.0``; 0.28 redacts the value to ``***`` but the URL is
    still attached to the exception)."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self) -> "_KeyedURLErrorClient":
        return self

    async def __aexit__(self, *exc_info) -> bool:
        return False

    async def post(self, url: str, **kwargs) -> None:
        params = kwargs.get("params") or {}
        key = params.get("key", "")
        request = httpx.Request("POST", f"{url}?key={key}")
        response = httpx.Response(403, request=request)
        # Simulate raise_for_status(): the message carries the full URL.
        raise httpx.HTTPStatusError(
            f"Client error '403 Forbidden' for url '{request.url}'",
            request=request,
            response=response,
        )


async def test_b1_gemini_provider_error_never_leaks_api_key(monkeypatch):
    """Gemini sends the key as a ?key= query param; the ProviderError must
    be generic (status code only) and never contain the key."""
    monkeypatch.setattr(httpx, "AsyncClient", _KeyedURLErrorClient)
    provider = GeminiProvider(api_key=API_KEY)
    with pytest.raises(ProviderError) as exc_info:
        await provider.check_visibility("what is acme?", "https://acme.com/x")
    message = str(exc_info.value)
    assert API_KEY not in message
    assert "HTTP 403" in message  # generic status-only message


async def test_b1_perplexity_provider_error_message_is_generic(monkeypatch):
    """Perplexity sends the key in the Authorization header (never in the
    URL), but the message must still be generic — no URL, no key."""
    monkeypatch.setattr(httpx, "AsyncClient", _KeyedURLErrorClient)
    provider = PerplexityProvider(api_key=API_KEY)
    with pytest.raises(ProviderError) as exc_info:
        await provider.check_visibility("what is acme?", "https://acme.com/x")
    message = str(exc_info.value)
    assert API_KEY not in message
    assert "HTTP 403" in message


class _RequestErrorClient:
    """Fake httpx.AsyncClient whose POST fails with a transport-level
    RequestError (URL attached) — must map to a generic ProviderError too."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self) -> "_RequestErrorClient":
        return self

    async def __aexit__(self, *exc_info) -> bool:
        return False

    async def post(self, url: str, **kwargs) -> None:
        request = httpx.Request("POST", f"{url}?key={API_KEY}")
        raise httpx.ConnectError("all connection attempts failed", request=request)


async def test_b1_gemini_request_error_message_is_generic(monkeypatch):
    """Transport errors must not interpolate the exception either (its
    string can carry the request URL)."""
    monkeypatch.setattr(httpx, "AsyncClient", _RequestErrorClient)
    provider = GeminiProvider(api_key=API_KEY)
    with pytest.raises(ProviderError) as exc_info:
        await provider.check_visibility("what is acme?", "https://acme.com/x")
    message = str(exc_info.value)
    assert API_KEY not in message
    assert "request error" in message


# ============================================================================
# B2 — days validation on get_content_visibility
# ============================================================================


async def test_b2_service_rejects_invalid_days(db_session: AsyncSession):
    """days=5 -> ValueError before any DB lookup (was: no validation)."""
    with pytest.raises(ValueError, match=r"Invalid days: 5"):
        await AiVisibilityService().get_content_visibility(
            db_session, "gen_whatever", days=5
        )


async def test_b2_huge_days_raises_value_error_not_overflow(
    db_session: AsyncSession,
):
    """days=10**15 previously reached timedelta(days=days-1) as an unhandled
    OverflowError -> 500; must now be a ValueError (-> 422)."""
    with pytest.raises(ValueError, match=r"Invalid days"):
        await AiVisibilityService().get_content_visibility(
            db_session, "gen_whatever", days=10**15
        )


async def test_b2_router_maps_invalid_days_to_422(db_session: AsyncSession):
    """Handler maps the ValueError to HTTP 422 (not a 500)."""
    with pytest.raises(HTTPException) as exc_info:
        await get_content_visibility(
            content_id="gen_whatever", days=5, db=db_session, current_user=None
        )
    assert exc_info.value.status_code == 422


# ============================================================================
# B4 — _target_url honors AI_VISIBILITY_CONTENT_BASE_URL
# ============================================================================


def test_b4_target_url_uses_configured_base_url():
    settings = Settings(AI_VISIBILITY_CONTENT_BASE_URL="https://app.contentforge.io/")
    poller = AiVisibilityPoller(registry=ProviderRegistry(Settings()), settings=settings)
    assert (
        poller._target_url("gen_7")
        == "https://app.contentforge.io/generations/gen_7"  # trailing slash stripped
    )


def test_b4_target_url_falls_back_to_placeholder():
    poller = AiVisibilityPoller(registry=ProviderRegistry(Settings()))
    assert (
        poller._target_url("gen_7")
        == "https://contentforge.example/generations/gen_7"
    )


# ============================================================================
# B5 — POST /{content_id}/refresh
# ============================================================================


def _make_request(poller):
    """Minimal stand-in for a FastAPI Request exposing app.state.ai_poller."""
    app = types.SimpleNamespace(state=types.SimpleNamespace(ai_poller=poller))
    return types.SimpleNamespace(app=app)


async def test_b5_refresh_unknown_generation_404(db_session: AsyncSession):
    """Unknown generation -> HTTP 404 (canonical ValueError mapping)."""
    with pytest.raises(HTTPException) as exc_info:
        await refresh_content_visibility(
            content_id="missing",
            request=_make_request(poller=None),
            db=db_session,
            current_user=None,
        )
    assert exc_info.value.status_code == 404


class _FakePoller:
    """Records poll_once calls; returns a canned PollResult."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def poll_once(
        self,
        db: AsyncSession,
        generation_ids: list[str] | None = None,
        engines: list[str] | None = None,
        queries_per_generation: int = 5,
    ) -> PollResult:
        self.calls.append(list(generation_ids or []))
        return PollResult(
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            engines_polled=["gemini"],
            queries_run=5,
        )


async def test_b5_refresh_happy_path_uses_app_poller(db_session: AsyncSession):
    """Known generation + app.state.ai_poller -> poll_once([content_id]) and
    the PollResult is returned."""
    await seed_generation(db_session, "gen_refresh")
    fake = _FakePoller()
    result = await refresh_content_visibility(
        content_id="gen_refresh",
        request=_make_request(poller=fake),
        db=db_session,
        current_user=None,
    )
    assert isinstance(result, PollResult)
    assert result.engines_polled == ["gemini"]
    assert fake.calls == [["gen_refresh"]]


async def test_b5_refresh_works_standalone_without_app_poller(
    db_session: AsyncSession, monkeypatch
):
    """app.state.ai_poller is None -> the handler builds a poller from
    ProviderRegistry.from_settings and still returns a PollResult."""
    await seed_generation(db_session, "gen_standalone")

    # No API keys configured -> from_settings registers no engines; keep the
    # singleton deterministic for this test regardless of the environment.
    # Patch the router MODULE (importlib, not `import ... as`/dotted-path:
    # the package attribute `src.ai_visibility.router` is shadowed by the
    # APIRouter re-export in __init__.py).
    import importlib

    router_module = importlib.import_module("src.ai_visibility.router")
    monkeypatch.setattr(router_module, "get_settings", lambda: Settings())
    result = await refresh_content_visibility(
        content_id="gen_standalone",
        request=_make_request(poller=None),
        db=db_session,
        current_user=None,
    )
    assert isinstance(result, PollResult)
