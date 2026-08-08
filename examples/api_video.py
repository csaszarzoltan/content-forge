#!/usr/bin/env python3
"""ContentForge API — AI Video Generation Example

Walks the video generation loop end-to-end:
  1. Create a video job from a script (source_type="script")
  2. Poll the job until the background worker renders it (state == "ready")
  3. List the selectable TTS voices (GET /voices)
  4. Demonstrate partial-export / retry semantics (retry endpoint contract)
  5. Export the rendered MP4 to a local file

The example runs WITHOUT any AI provider API keys: when no TTS key is
configured the background worker writes a short silent MP3 placeholder per
scene (via the bundled ffmpeg binary), so scene rendering and MP4 export
still work offline. Configure OPENAI_API_KEY / ELEVENLABS_API_KEY (or
install the `video-coqui` extra) for real narration.

Prerequisites:
    ContentForge server running at http://localhost:8000 with the video
    worker enabled (default):

        uvicorn src.main:app --reload

    The server must have been started after the v0.15.0 video pipeline was
    installed (the background worker lives in the app lifespan).

Usage:
    python examples/api_video.py

    Point at a non-default server (e.g. a different port) with:

        CONTENTFORGE_VIDEO_BASE=http://localhost:8099/api/v1/video \\
            python examples/api_video.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx

BASE = os.getenv("CONTENTFORGE_VIDEO_BASE", "http://localhost:8000/api/v1/video")
# The worker polls every VIDEO_WORKER_INTERVAL_SECONDS (default 2s); poll a
# bit slower than that so we rarely hit the server with empty polls.
POLL_INTERVAL = 2.0
POLL_TIMEOUT = 120.0


def create_job() -> str:
    """Step 1: Create a video job from a script."""
    print("=" * 60)
    print("1. CREATE — POST /api/v1/video/jobs")
    print("=" * 60)

    resp = httpx.post(
        f"{BASE}/jobs",
        json={
            "source_type": "script",
            "source_ref": (
                "## Intro\n"
                "Hello! This is a ContentForge test video.\n\n"
                "## Body\n"
                "The pipeline turns a script into scenes, narrates each one, "
                "and renders an MP4.\n\n"
                "## Outro\n"
                "Thanks for watching!"
            ),
            "style_preset": "explainer",
            "voice": "alloy",
            "resolution": "480p",
        },
        timeout=30,
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    body = resp.json()

    job_id = body["job_id"]
    print(f"  job_id:   {job_id}")
    print(f"  state:    {body['state']}")
    print(f"  segments: {body.get('segments')}")
    print()
    return job_id


def poll_until_ready(job_id: str) -> dict:
    """Step 2: Poll GET /api/v1/video/jobs/{id} until the worker finishes."""
    print("=" * 60)
    print("2. PROGRESS — GET /api/v1/video/jobs/{id}")
    print("=" * 60)

    deadline = time.monotonic() + POLL_TIMEOUT
    while True:
        resp = httpx.get(f"{BASE}/jobs/{job_id}", timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        job = resp.json()
        print(
            f"  state={job['state']:<8} progress={job['overall_progress']:>5.1f}% "
            f"scenes={len(job['scenes'])}"
        )
        if job["state"] in ("ready", "failed", "partial"):
            return job
        if time.monotonic() > deadline:
            print("  ⚠ timed out waiting for the worker — is the server running with")
            print("    the video worker enabled (VIDEO_WORKER_ENABLED=true, default)?")
            sys.exit(1)
        time.sleep(POLL_INTERVAL)


def list_voices() -> None:
    """Step 3: List the selectable TTS voices."""
    print("=" * 60)
    print("3. VOICES — GET /api/v1/video/voices")
    print("=" * 60)

    resp = httpx.get(f"{BASE}/voices", params={"provider": "openai"}, timeout=30)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    print(f"  provider: {body['provider']}")
    for voice in body["voices"]:
        print(f"    {voice['id']:<10} {voice['name']}")
    print()


def show_retry_contract(job_id: str) -> None:
    """Step 4: Show the retry endpoint contract on a finished job."""
    print("=" * 60)
    print("4. RETRY — POST /api/v1/video/jobs/{id}/retry")
    print("=" * 60)

    # A ready job is not retryable → 409 (nothing failed, nothing to re-queue).
    resp = httpx.post(f"{BASE}/jobs/{job_id}/retry", timeout=30)
    print(f"  retry on ready job: {resp.status_code} (expected 409)")
    print(f"    detail: {resp.json().get('detail')}")
    print()
    print("  Retry re-queues ONLY failed scenes (US-003): on a job with")
    print("  failed scenes it returns {retried: [scene-id, ...]} and moves the")
    print("  job back to 'scenes' so the worker picks it up again.")
    print()


def export_mp4(job_id: str) -> None:
    """Step 5: Stream the rendered MP4 to a local file."""
    print("=" * 60)
    print("5. EXPORT — GET /api/v1/video/jobs/{id}/export")
    print("=" * 60)

    resp = httpx.get(
        f"{BASE}/jobs/{job_id}/export",
        params={"resolution": "480p"},
        timeout=120,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    out_path = Path(f"video_{job_id}.mp4")
    out_path.write_bytes(resp.content)
    print(f"  status:       {resp.status_code}")
    print(f"  content-type: {resp.headers.get('content-type')}")
    print(f"  bytes:        {len(resp.content)}")
    print(f"  saved:        {out_path}")
    print()

    # Partial export flag (only meaningful when scenes failed at max retries).
    resp = httpx.get(
        f"{BASE}/jobs/{job_id}/export",
        params={"resolution": "480p", "partial": "true"},
        timeout=120,
    )
    print(f"  partial=true: {resp.status_code} — x-partial: {resp.headers.get('x-partial')}")
    print()


def main() -> None:
    """Run the full video generation demo."""
    print("ContentForge Video Generation API — Example Walkthrough\n")
    job_id = create_job()
    job = poll_until_ready(job_id)
    print(f"  Final state: {job['state']}")
    print()
    list_voices()
    show_retry_contract(job_id)
    export_mp4(job_id)
    print("Done. All video workflows exercised.")


if __name__ == "__main__":
    main()
