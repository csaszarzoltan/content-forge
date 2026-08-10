"""ContentForge CLI — Typer application for admin and analytics commands.

Provides CLI access to analytics, content generation, and platform
management features from the terminal.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import typer

app = typer.Typer(help="ContentForge — AI-powered content platform CLI")


@app.command()
def root():
    """ContentForge CLI entry point."""
    typer.echo("ContentForge CLI v0.15.0")


analytics_app = typer.Typer(help="Analytics commands")
app.add_typer(analytics_app, name="analytics")


@analytics_app.command("video-performance")
def video_performance(
    platform: str | None = typer.Option(None, help="Filter by platform (youtube, tiktok, instagram)"),
    days: int = typer.Option(30, help="Number of days to analyze"),
) -> None:
    """Display video performance metrics across platforms."""
    from src.config import get_settings
    from src.services.video_analytics import (
        InstagramClient,
        TikTokClient,
        VideoAnalyticsService,
        YouTubeClient,
    )

    settings = get_settings()
    youtube = YouTubeClient(api_key=settings.YOUTUBE_API_KEY)
    tiktok = TikTokClient(client_key=settings.TIKTOK_API_KEY)
    instagram = InstagramClient(access_token=settings.INSTAGRAM_ACCESS_TOKEN)

    svc = VideoAnalyticsService(youtube=youtube, tiktok=tiktok, instagram=instagram)
    now = datetime.now(UTC)
    result = svc.get_performance(
        video_id="",
        platform=platform,
        date_from=now - timedelta(days=days),
        date_to=now,
    )

    # Display table
    typer.echo(f"{'Platform':<15} {'Views':>10} {'Likes':>10} {'Comments':>10} {'Shares':>10}")
    typer.echo("-" * 55)

    platforms = result.get("platforms", [])
    if not platforms:
        typer.echo("  No data available (no platforms configured or all returned errors)")
    else:
        for p in platforms:
            typer.echo(
                f"{p.get('platform', 'unknown'):<15} "
                f"{p.get('views', 0):>10} "
                f"{p.get('likes', 0):>10} "
                f"{p.get('comments', 0):>10} "
                f"{p.get('shares', 0):>10}"
            )

    unavailable = result.get("platforms_unavailable", [])
    if unavailable:
        typer.echo(f"\nUnavailable platforms: {', '.join(unavailable)}")

    typer.echo(f"\nDate range: {days} days")
