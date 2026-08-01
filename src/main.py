"""ContentForge - AI-powered content generation platform."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import create_async_engine

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
from src.routers.brand_voice import router as brand_voice_router
from src.routers.content import router as content_router
from src.routers.languages import router as languages_router
from src.routers.publish import router as publish_router
from src.routers.schedule import router as schedule_router
from src.routers.seo import router as seo_router
from src.routers.translate import router as translate_router
from src.routers.workspaces import router as workspaces_router
from src.routers.constraints import router as constraints_router  # noqa: F401
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
    yield
    # Shutdown
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
app.include_router(brand_voice_router)
app.include_router(content_router)
app.include_router(languages_router)
app.include_router(translate_router)
app.include_router(publish_router)
app.include_router(schedule_router)
app.include_router(ab_router)
app.include_router(analytics_router)
app.include_router(seo_router)
app.include_router(workspaces_router)
app.mount(
    "/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static"
)


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
