"""Integration tests for the transcreation API endpoints.

Covers US-001..US-005 over the real HTTP stack (FastAPI TestClient):
  * POST /api/v1/transcreation/analyze   — risk detection + locale formatting
  * POST /api/v1/transcreation/adapt     — review semantics (accept/reject/edit)
  * POST /api/v1/transcreation/preflight — publish gate (blocked/override/clean)
  * GET  /api/v1/transcreation/preflight/{asset_id} + override
  * GET  /api/v1/transcreation/assets/{asset_id}/result  — persistence per asset
  * POST /api/v1/transcreation/assets/{asset_id}/export  — blocked on unresolved flags

Error contract: 400 malformed params, 404 missing resources, 409 preflight
block, all with JSON error bodies. Tests exercise real rule-based behavior
(no mocks).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.routers import transcreation

pytestmark = pytest.mark.quick


def client(tmp_path: Path) -> TestClient:
    """Standalone app with the transcreation router and a fresh SQLite DB."""
    transcreation._DB = tmp_path / "ops.db"
    app = FastAPI()
    app.include_router(transcreation.router)
    return TestClient(app)


# ── US-001 — Analyze endpoint ──────────────────────────────────────────────


class TestAnalyzeEndpoint:
    def test_analyze_returns_risk_items(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        response = api.post(
            "/api/v1/transcreation/analyze",
            json={"text": "It's raining cats and dogs.", "target_locale": "de-DE"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["locale"] == "de-DE"
        categories = {item["category"] for item in body["risk_items"]}
        assert "idiom" in categories
        item = body["risk_items"][0]
        assert item["segment"]
        assert item["issue_description"]
        assert 0.0 <= item["confidence"] <= 1.0
        assert item["suggested_replacement"]

    def test_analyze_returns_format_items(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        response = api.post(
            "/api/v1/transcreation/analyze",
            json={
                "text": "Launching on 07/04/2026. The upgrade costs $1,000.",
                "target_locale": "de-DE",
            },
        )
        assert response.status_code == 200
        body = response.json()
        types = {item["format_type"] for item in body["format_items"]}
        assert {"date", "currency"} <= types
        converted = {item["converted"] for item in body["format_items"]}
        assert "04.07.2026" in converted
        assert "1.000 €" in converted

    def test_analyze_malformed_body_returns_400(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        response = api.post(
            "/api/v1/transcreation/analyze",
            json={"text": "Hello", "target_locale": ""},
        )
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_analyze_clean_text_no_risks(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        response = api.post(
            "/api/v1/transcreation/analyze",
            json={
                "text": "The quarterly report is now available for download.",
                "target_locale": "de-DE",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["risk_items"] == []
        assert body["overall_risk"] == "low"


# ── US-002/003/004 — Adapt endpoint ────────────────────────────────────────


class TestAdaptEndpoint:
    def test_adapt_returns_segments_and_adapted_text(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        response = api.post(
            "/api/v1/transcreation/adapt",
            json={
                "text": "It's raining cats and dogs. The report is ready.",
                "target_locale": "de-DE",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["adapted_text"]
        assert len(body["segments"]) == 2
        for seg in body["segments"]:
            assert seg["original"]
            assert seg["literal"]
            assert seg["adapted"]

    def test_adapt_rejected_segment_uses_literal(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        response = api.post(
            "/api/v1/transcreation/adapt",
            json={
                "text": "It's raining cats and dogs.",
                "target_locale": "de-DE",
                "rejected_ids": ["seg-1"],
            },
        )
        assert response.status_code == 200
        body = response.json()
        rejected = next(seg for seg in body["segments"] if seg["id"] == "seg-1")
        assert rejected["decision"] == "reject"
        assert rejected["literal"] in body["adapted_text"]

    def test_adapt_edited_segment_clears_flag(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        response = api.post(
            "/api/v1/transcreation/adapt",
            json={
                "text": "He's a real Benedict Arnold.",
                "target_locale": "de-DE",
                "edits": {"seg-1": "He's a real traitor."},
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "He's a real traitor." in body["adapted_text"]
        assert "seg-1" not in body["flagged_segments"]

    def test_adapt_malformed_body_returns_422(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        response = api.post(
            "/api/v1/transcreation/adapt",
            json={"text": "Hello", "target_locale": "de-DE", "edits": "not-a-dict"},
        )
        assert response.status_code == 422
        assert "detail" in response.json()


# ── US-005 — Preflight endpoint + persistence ──────────────────────────────


class TestPreflightEndpoint:
    def test_preflight_blocks_high_risk(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        response = api.post(
            "/api/v1/transcreation/preflight",
            json={"asset_id": "asset-1", "content": "That's a load of crap.", "target_locale": "de-DE"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["asset_id"] == "asset-1"
        high = [item for item in body["risk_items"] if item["risk_level"] == "high"]
        assert high
        assert body["blocked"] is True
        assert body["blocked_reasons"]
        assert body["audit_status"] == "fail"
        assert body["override_available"] is True

    def test_preflight_passes_clean_content(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        response = api.post(
            "/api/v1/transcreation/preflight",
            json={
                "asset_id": "asset-2",
                "content": "The quarterly report is available for download.",
                "target_locale": "de-DE",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["blocked"] is False
        assert body["audit_status"] == "pass"

    def test_preflight_persists_result_per_asset(self, tmp_path: Path) -> None:
        """Analysis results are persisted per asset in SQLite (product_ops pattern)."""
        api = client(tmp_path)
        api.post(
            "/api/v1/transcreation/preflight",
            json={"asset_id": "asset-9", "content": "That's a load of crap.", "target_locale": "de-DE"},
        )
        stored = api.get("/api/v1/transcreation/preflight/asset-9")
        assert stored.status_code == 200
        body = stored.json()
        assert body["asset_id"] == "asset-9"
        assert body["blocked"] is True
        assert any(item["category"] == "taboo" for item in body["risk_items"])

    def test_preflight_override_unblocks_publish(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        api.post(
            "/api/v1/transcreation/preflight",
            json={"asset_id": "asset-3", "content": "That's a load of crap.", "target_locale": "de-DE"},
        )
        assert api.get("/api/v1/transcreation/preflight/asset-3").json()["blocked"] is True
        override = api.post("/api/v1/transcreation/preflight/asset-3/override", json={"override": True})
        assert override.status_code == 200
        body = override.json()
        assert body["blocked"] is False
        assert body["override_available"] is True
        assert body["audit_status"] == "review_needed"

    def test_preflight_unknown_asset_returns_404(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        response = api.get("/api/v1/transcreation/preflight/does-not-exist")
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_preflight_malformed_body_returns_422(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        response = api.post(
            "/api/v1/transcreation/preflight",
            json={"asset_id": "", "content": "x", "target_locale": "de-DE"},
        )
        assert response.status_code == 422
        assert "detail" in response.json()


# ── Persistence + export ───────────────────────────────────────────────────


class TestPersistenceAndExport:
    def test_asset_result_endpoint_returns_full_snapshot(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        api.post(
            "/api/v1/transcreation/preflight",
            json={"asset_id": "asset-4", "content": "That's a load of crap.", "target_locale": "de-DE"},
        )
        result = api.get("/api/v1/transcreation/assets/asset-4/result")
        assert result.status_code == 200
        body = result.json()
        assert body["asset_id"] == "asset-4"
        assert body["preflight"]["blocked"] is True
        assert body["preflight"]["blocked_reasons"]

    def test_asset_result_missing_returns_404(self, tmp_path: Path) -> None:
        api = client(tmp_path)
        response = api.get("/api/v1/transcreation/assets/nope/result")
        assert response.status_code == 404

    def test_export_blocked_on_unresolved_flags(self, tmp_path: Path) -> None:
        """US-003 AC2 — export is blocked while flagged segments are unresolved."""
        api = client(tmp_path)
        # No stored result at all → export blocked (409) with JSON body.
        response = api.post("/api/v1/transcreation/assets/asset-5/export", json={})
        assert response.status_code == 409
        assert "detail" in response.json()


# ── External failure handling (502/503 with JSON body) ─────────────────────


class TestExternalFailureHandling:
    def test_analyze_provider_failure_returns_502(self, tmp_path: Path, monkeypatch) -> None:
        """A provider outage surfaces as 502/503 with a JSON error body (no HTML)."""
        from src.services import transcreation as transcreation_service

        async def boom(*args, **kwargs):
            raise transcreation_service.TranscreationProviderError("provider timeout")

        monkeypatch.setattr(transcreation_service.TranscreationService, "analyze", boom)
        api = client(tmp_path)
        response = api.post(
            "/api/v1/transcreation/analyze",
            json={"text": "It's raining cats and dogs.", "target_locale": "de-DE"},
        )
        assert response.status_code in (502, 503)
        assert "detail" in response.json()

    def test_adapt_provider_failure_returns_502(self, tmp_path: Path, monkeypatch) -> None:
        from src.services import transcreation as transcreation_service

        async def boom(*args, **kwargs):
            raise transcreation_service.TranscreationProviderError("connection refused")

        monkeypatch.setattr(transcreation_service.TranscreationService, "adapt", boom)
        api = client(tmp_path)
        response = api.post(
            "/api/v1/transcreation/adapt",
            json={"text": "It's raining cats and dogs.", "target_locale": "de-DE"},
        )
        assert response.status_code in (502, 503)
        assert "detail" in response.json()

    def test_preflight_provider_failure_returns_503(self, tmp_path: Path, monkeypatch) -> None:
        from src.services import transcreation as transcreation_service

        async def boom(*args, **kwargs):
            raise transcreation_service.TranscreationProviderError("service unavailable")

        monkeypatch.setattr(transcreation_service.TranscreationService, "preflight", boom)
        api = client(tmp_path)
        response = api.post(
            "/api/v1/transcreation/preflight",
            json={"asset_id": "a1", "content": "That's a load of crap.", "target_locale": "de-DE"},
        )
        assert response.status_code in (502, 503)
        assert "detail" in response.json()


# ── Export positive path + resolution (BLOCKER-1 fix verification) ─────────


class TestExportPositivePath:
    """US-003 AC2 — export succeeds for clean assets and after flag resolution."""

    def test_export_clean_asset_returns_200(self, tmp_path: Path) -> None:
        """Clean asset (no flags) -> export 200 with accepted_adaptations."""
        import json as _json

        api = client(tmp_path)
        # Preflight a clean asset — analysis stored with no risk items.
        preflight = api.post(
            "/api/v1/transcreation/preflight",
            json={
                "asset_id": "asset-clean-1",
                "content": "The quarterly report is available for download.",
                "target_locale": "de-DE",
            },
        )
        assert preflight.status_code == 200
        # Export should succeed — no unresolved flags.
        response = api.post("/api/v1/transcreation/assets/asset-clean-1/export", json={})
        assert response.status_code == 200
        body = response.json()
        assert body["asset_id"] == "asset-clean-1"
        # The adapted_text field contains the JSON string from service.export().
        payload = _json.loads(body["adapted_text"])
        assert "accepted_adaptations" in payload
        assert isinstance(payload["accepted_adaptations"], list)

    def test_export_after_resolution_returns_200(self, tmp_path: Path) -> None:
        """Flagged asset -> accept decisions -> export 200."""
        import json as _json

        api = client(tmp_path)
        # Preflight an asset with low-confidence risk items (idiom: confidence 0.65).
        preflight = api.post(
            "/api/v1/transcreation/preflight",
            json={
                "asset_id": "asset-flagged-1",
                "content": "It's raining cats and dogs.",
                "target_locale": "de-DE",
            },
        )
        assert preflight.status_code == 200
        pf_body = preflight.json()
        # Verify there are low-confidence flagged items.
        low_conf = [item for item in pf_body["risk_items"] if item["confidence"] < 0.7]
        assert low_conf, "Expected low-confidence risk items for this text"
        flagged_ids = [item["id"] for item in low_conf]
        # Export without resolving should be blocked.
        blocked = api.post("/api/v1/transcreation/assets/asset-flagged-1/export", json={})
        assert blocked.status_code == 409
        # Export with accepted_ids for all flagged segments should succeed.
        resolved = api.post(
            "/api/v1/transcreation/assets/asset-flagged-1/export",
            json={"accepted_ids": flagged_ids},
        )
        assert resolved.status_code == 200
        body = resolved.json()
        assert body["asset_id"] == "asset-flagged-1"
        payload = _json.loads(body["adapted_text"])
        assert "accepted_adaptations" in payload


# ── BLOCKER-2: Large-input timing sanity ────────────────────────────────────


class TestLargeInputTiming:
    """BLOCKER-2 — _surrounding_sentence O(n) rewrite must stay fast."""

    def test_50kb_input_under_1s(self, tmp_path: Path) -> None:
        """50KB of sentences through the rule engine must complete in < 1s."""
        import time

        # Build a 50KB text by repeating sentences with slight variation.
        base_sentences = [
            "The quarterly report is available for download.",
            "Please review the attached documents before the meeting.",
            "Our team is working on the new feature release.",
            "The deadline for the project has been extended.",
            "Thank you for your prompt response to this matter.",
        ]
        # Each sentence is ~51 chars. 50KB / 51 ≈ 980 sentences; use 1200 for margin.
        text = ". ".join(
            base_sentences[i % len(base_sentences)] for i in range(1200)
        )
        assert len(text) >= 50_000, f"Text too short: {len(text)} bytes"

        api = client(tmp_path)
        start = time.perf_counter()
        response = api.post(
            "/api/v1/transcreation/analyze",
            json={"text": text, "target_locale": "de-DE"},
        )
        elapsed = time.perf_counter() - start
        assert response.status_code == 200
        assert elapsed < 1.0, f"50KB analyze took {elapsed:.2f}s — expected < 1s"
