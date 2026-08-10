"""ContentForge - AI-powered content generation platform."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import create_async_engine

from src.ai_visibility.models import (  # noqa: F401  (register tables on Base.metadata)
    AIEngineMetrics,
    AIRawMention,
    AIReferralTraffic,
    AITrendAggregate,
)
from src.ai_visibility.router import router as ai_visibility_router
from src.config import get_settings
from src.database import Base
from src.models import (  # noqa: F401
    ABEvent,
    ABTest,
    ABVariant,
    AnalyticsEvent,
    BrandVoice,
    ContentAnalytics,
    Generation,
    ScheduledPost,
    User,
)
from src.routers.ab_test import router as ab_router
from src.routers.analytics import router as analytics_router
from src.routers.auth import router as auth_router
from src.routers.brand_kit import router as brand_kit_router
from src.routers.brand_voice import router as brand_voice_router
from src.routers.constraints import router as constraints_router
from src.routers.content import router as content_router
from src.routers.languages import router as languages_router
from src.routers.publish import router as publish_router
from src.routers.schedule import router as schedule_router
from src.routers.seo import router as seo_router
from src.routers.transcreation import router as transcreation_router
from src.routers.translate import router as translate_router
from src.routers.video import router as video_router
from src.routers.video_analytics import router as video_analytics_router
from src.routers.workspaces import router as workspaces_router
from src.services.publish_service import PublishService
from src.services.scheduler import SchedulerService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    # Startup
    settings = get_settings()
    app.state.settings = settings

    # Create database tables on startup
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    # Initialize social media connectors
    from src.connectors.linkedin import LinkedInConnector
    from src.connectors.twitter import TwitterConnector

    connectors: dict = {}
    if settings.TWITTER_API_KEY:
        connectors["twitter"] = TwitterConnector(
            api_key=settings.TWITTER_API_KEY,
            api_secret=settings.TWITTER_API_SECRET,
            access_token=settings.TWITTER_ACCESS_TOKEN,
            access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET,
        )
    if settings.LINKEDIN_CLIENT_ID:
        connectors["linkedin"] = LinkedInConnector(
            client_id=settings.LINKEDIN_CLIENT_ID,
            client_secret=settings.LINKEDIN_CLIENT_SECRET,
            access_token="",
        )

    app.state.publish_service = PublishService(connectors=connectors)

    app.state.scheduler = SchedulerService()
    await app.state.scheduler.start()

    # AI visibility poller (M8 P1): opt-in background polling when enabled.
    ai_poller = None
    if settings.AI_VISIBILITY_POLL_ENABLED:
        from src.ai_visibility.poller import AiVisibilityPoller
        from src.ai_visibility.providers import ProviderRegistry

        registry = ProviderRegistry.from_settings(settings)
        ai_poller = AiVisibilityPoller(registry=registry, settings=settings)
        await ai_poller.start()
    app.state.ai_poller = ai_poller

    # Video pipeline worker (BLOCKER-1, review t_db9e57ad): processes queued
    # video jobs end-to-end (TTS → scene done → render → ready|failed).
    video_worker = None
    if settings.VIDEO_WORKER_ENABLED:
        from src.services.video_worker import VideoJobWorker

        video_worker = VideoJobWorker(settings=settings)
        await video_worker.start()
    app.state.video_worker = video_worker

    yield
    # Shutdown
    if video_worker is not None:
        await video_worker.shutdown()
    if ai_poller is not None:
        await ai_poller.shutdown()
    await app.state.scheduler.shutdown()


app = FastAPI(
    title="ContentForge",
    version="0.9.0",
    description="AI-powered content generation platform with brand voice customization",
    lifespan=lifespan,
)

# CORS middleware
settings = get_settings()
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(brand_kit_router)
app.include_router(brand_voice_router)
app.include_router(content_router)
app.include_router(languages_router)
app.include_router(translate_router)
app.include_router(transcreation_router)
app.include_router(video_router)
app.include_router(publish_router)
app.include_router(schedule_router)
app.include_router(ab_router)
app.include_router(analytics_router)
app.include_router(ai_visibility_router)
app.include_router(seo_router)
app.include_router(workspaces_router)
app.include_router(constraints_router)
app.include_router(video_analytics_router)
app.mount(
    "/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static"
)


class _UploadsStaticApp:
    """StaticFiles wrapper whose directory follows the current UPLOAD_ROOT.

    Resolved per request from ``get_settings()`` so the mount tracks config
    (including test-injected settings) instead of being pinned to whatever
    ``UPLOAD_ROOT`` was at import time. This makes uploaded brand-kit assets
    servable under ``/uploads`` (F4 finding).
    """

    def __init__(self) -> None:
        self._root: Path | None = None
        self._static: StaticFiles | None = None

    async def __call__(self, scope, receive, send) -> None:
        # Prefer the settings the app is actually running with (lifespan
        # sets app.state.settings; tests override it). The ASGI scope carries
        # the app instance, so we can read it without import-time coupling.
        app = scope.get("app")
        if app is not None and getattr(app.state, "settings", None) is not None:
            root = Path(app.state.settings.UPLOAD_ROOT)
        else:
            root = Path(get_settings().UPLOAD_ROOT)
        if self._static is None or self._root != root:
            # UPLOAD_ROOT may be relative — resolve it against the app CWD.
            root.mkdir(parents=True, exist_ok=True)
            self._static = StaticFiles(directory=str(root))
            self._root = root
        await self._static(scope, receive, send)


app.mount("/uploads", _UploadsStaticApp(), name="uploads")


@app.get("/")
async def root():
    """Root endpoint — returns API version info."""
    return {"message": "ContentForge API", "version": "0.9.0"}


@app.get("/health")
async def health():
    """Health check endpoint for Railway deployment."""
    return {
        "status": "healthy",
        "version": "0.9.0",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": {
            "database": "ok",
            "scheduler": "ok",
            "llm_provider": "ok",
        },
    }
