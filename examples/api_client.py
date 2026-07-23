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

    # ── Analytics ─────────────────────────────────────────────────────

    def get_content_analytics(self, generation_id: str) -> dict[str, Any]:
        """GET /analytics/content/{id} — per-generation analytics."""
        r = self._client.get(f"/analytics/content/{generation_id}")
        r.raise_for_status()
        return r.json()

    def get_analytics_summary(self) -> dict[str, Any]:
        """GET /analytics/summary — aggregate analytics."""
        r = self._client.get("/analytics/summary")
        r.raise_for_status()
        return r.json()

    # ── Lifecycle ─────────────────────────────────────────────────────

    def close(self) -> None:
        self._client.close()
