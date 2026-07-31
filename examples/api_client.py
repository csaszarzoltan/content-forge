#!/usr/bin/env python3
"""
ContentForge API — Shared HTTPX Client

Usage:
    from api_client import ContentForgeClient

    client = ContentForgeClient("http://localhost:8000")
    health = client.health()
    print(health)
"""

from __future__ import annotations

from typing import Any

import httpx


class ContentForgeClient:
    """Thin wrapper around httpx for ContentForge API calls."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=30.0)

    # ── System ────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        """GET /health — deployment health check."""
        r = self._client.get("/health")
        r.raise_for_status()
        return r.json()

    def root(self) -> dict[str, Any]:
        """GET / — API version info."""
        r = self._client.get("/")
        r.raise_for_status()
        return r.json()

    # ── Brand Voice CRUD ──────────────────────────────────────────────

    def create_brand_voice(self, **data: Any) -> dict[str, Any]:
        """POST /brand-voice — create a new brand voice profile."""
        r = self._client.post("/brand-voice", json=data)
        r.raise_for_status()
        return r.json()

    def list_brand_voices(
        self, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        """GET /brand-voice — list brand voices (paginated)."""
        r = self._client.get("/brand-voice", params={"limit": limit, "offset": offset})
        r.raise_for_status()
        return r.json()

    def get_brand_voice(self, brand_voice_id: str) -> dict[str, Any]:
        """GET /brand-voice/{id} — get a single brand voice."""
        r = self._client.get(f"/brand-voice/{brand_voice_id}")
        r.raise_for_status()
        return r.json()

    def update_brand_voice(
        self, brand_voice_id: str, **data: Any
    ) -> dict[str, Any]:
        """PUT /brand-voice/{id} — partial update of a brand voice."""
        r = self._client.put(f"/brand-voice/{brand_voice_id}", json=data)
        r.raise_for_status()
        return r.json()

    def delete_brand_voice(self, brand_voice_id: str) -> None:
        """DELETE /brand-voice/{id} — soft-delete a brand voice."""
        r = self._client.delete(f"/brand-voice/{brand_voice_id}")
        r.raise_for_status()

    # ── Content Generation ────────────────────────────────────────────

    def generate_content(
        self,
        content_type: str,
        topic: str,
        brand_voice_id: str | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """POST /generate/{content_type} — generate content via LLM."""
        body: dict[str, Any] = {
            "topic": topic,
            "brand_voice_id": brand_voice_id,
            "parameters": params,
        }
        r = self._client.post(f"/generate/{content_type}", json=body)
        r.raise_for_status()
        return r.json()

    # ── Scheduling ────────────────────────────────────────────────────

    def schedule_content(
        self,
        generation_id: str,
        publish_at: str,
        platform: str,
        **data: Any,
    ) -> dict[str, Any]:
        """POST /schedule — schedule content for publishing."""
        body: dict[str, Any] = {
            "generation_id": generation_id,
            "publish_at": publish_at,
            "platform": platform,
            **data,
        }
        r = self._client.post("/schedule", json=body)
        r.raise_for_status()
        return r.json()

    def get_schedule_status(self, schedule_id: str) -> dict[str, Any]:
        """GET /schedule/{id} — get schedule status."""
        r = self._client.get(f"/schedule/{schedule_id}")
        r.raise_for_status()
        return r.json()

    def cancel_schedule(self, schedule_id: str) -> None:
        """DELETE /schedule/{id} — cancel a scheduled post."""
        r = self._client.delete(f"/schedule/{schedule_id}")
        r.raise_for_status()

    # ── Analytics Dashboard (v0.9.0, /api/v1/analytics) ─────────────

    def track_event(
        self,
        generation_id: str,
        event_type: str,
        channel: str = "web",
        value: int = 1,
        user_identifier: str | None = None,
        metadata: dict | None = None,
        occurred_at: str | None = None,
    ) -> dict[str, Any]:
        """POST /api/v1/analytics/track — record one analytics event.

        event_type: impression, click, share, comment, conversion, read_time
        channel: twitter, linkedin, medium, blog, email, web, other
        """
        body: dict[str, Any] = {
            "generation_id": generation_id,
            "channel": channel,
            "event_type": event_type,
            "value": value,
        }
        if user_identifier is not None:
            body["user_identifier"] = user_identifier
        if metadata is not None:
            body["metadata"] = metadata
        if occurred_at is not None:
            body["occurred_at"] = occurred_at
        r = self._client.post("/api/v1/analytics/track", json=body)
        r.raise_for_status()
        return r.json()

    def get_dashboard(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        channel: str | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """GET /api/v1/analytics/dashboard — aggregated metrics (default: last 30 days)."""
        params = self._window_params(date_from, date_to)
        if channel:
            params["channel"] = channel
        if content_type:
            params["content_type"] = content_type
        r = self._client.get("/api/v1/analytics/dashboard", params=params)
        r.raise_for_status()
        return r.json()

    def get_content_performance(
        self,
        generation_id: str,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict[str, Any]:
        """GET /api/v1/analytics/content/{id} — per-content performance breakdown."""
        r = self._client.get(
            f"/api/v1/analytics/content/{generation_id}",
            params=self._window_params(date_from, date_to),
        )
        r.raise_for_status()
        return r.json()

    def get_channel_comparison(
        self,
        metric: str = "impressions",
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict[str, Any]:
        """GET /api/v1/analytics/channels — cross-channel comparison, best first."""
        params = {"metric": metric, **self._window_params(date_from, date_to)}
        r = self._client.get("/api/v1/analytics/channels", params=params)
        r.raise_for_status()
        return r.json()

    def get_ab_results(
        self,
        test_id: str,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict[str, Any]:
        """GET /api/v1/analytics/ab-results — A/B variant vs. analytics correlation."""
        params = {"test_id": test_id, **self._window_params(date_from, date_to)}
        r = self._client.get("/api/v1/analytics/ab-results", params=params)
        r.raise_for_status()
        return r.json()

    def get_content_score(self, generation_id: str) -> dict[str, Any]:
        """GET /api/v1/analytics/score/{id} — deterministic content quality score."""
        r = self._client.get(f"/api/v1/analytics/score/{generation_id}")
        r.raise_for_status()
        return r.json()

    def export_analytics(
        self,
        format: str = "json",
        date_from: str | None = None,
        date_to: str | None = None,
        channel: str | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """GET /api/v1/analytics/export — CSV/JSON export of daily aggregates.

        The returned ``data`` field is a string (CSV text or JSON array text).
        """
        params = {"format": format, **self._window_params(date_from, date_to)}
        if channel:
            params["channel"] = channel
        if content_type:
            params["content_type"] = content_type
        r = self._client.get("/api/v1/analytics/export", params=params)
        r.raise_for_status()
        return r.json()

    def get_trends(
        self,
        period: str = "30d",
        metric: str = "impressions",
        channel: str | None = None,
    ) -> dict[str, Any]:
        """GET /api/v1/analytics/trends — daily trend series with anomaly flags."""
        params: dict[str, Any] = {"period": period, "metric": metric}
        if channel:
            params["channel"] = channel
        r = self._client.get("/api/v1/analytics/trends", params=params)
        r.raise_for_status()
        return r.json()

    def get_anomalies(
        self, period: str = "30d", metric: str = "impressions"
    ) -> dict[str, Any]:
        """GET /api/v1/analytics/anomalies — statistically flagged days (|z| >= 2.0)."""
        r = self._client.get(
            "/api/v1/analytics/anomalies", params={"period": period, "metric": metric}
        )
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _window_params(
        date_from: str | None, date_to: str | None
    ) -> dict[str, Any]:
        """Build the shared date-window query params."""
        params: dict[str, Any] = {}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return params

    # ── Lifecycle ─────────────────────────────────────────────────────

    def close(self) -> None:
        self._client.close()
