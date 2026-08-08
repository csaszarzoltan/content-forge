"""Transcreation API walkthrough.

Demonstrates the full cultural-adaptation pipeline:
  1. Analyze content for cultural risks and locale formatting issues
  2. Adapt content with per-segment reviewer decisions (accept/reject/edit)
  3. Run a preflight check before publishing
  4. Override a preflight block (explicit human approval)
  5. Export accepted adaptations after resolving low-confidence flags

Requires a running ContentForge server:
    uvicorn src.main:app --reload

Usage:
    python examples/api_transcreation.py
"""

from __future__ import annotations

import httpx

BASE = "http://localhost:8000/api/v1/transcreation"


def analyze_cultural_risks() -> None:
    """Step 1: Detect cultural risks and locale formatting issues."""
    print("=" * 60)
    print("1. ANALYZE — Cultural risk detection + locale formatting")
    print("=" * 60)

    resp = httpx.post(
        f"{BASE}/analyze",
        json={
            "text": "It's raining cats and dogs. The upgrade costs $1,000 on 07/04/2026. Mr. Smith will attend.",
            "target_locale": "de-DE",
        },
        timeout=30,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()

    print(f"  Target locale: {body['locale']}")
    print(f"  Overall risk:  {body['overall_risk']}")
    print(f"  Risk items:    {len(body['risk_items'])}")
    for item in body["risk_items"]:
        print(f"    [{item['category']}] {item['original_text']}")
        print(f"      → {item['issue_description']} (confidence={item['confidence']})")
        if item["suggested_replacement"]:
            print(f"      → Suggested: {item['suggested_replacement']}")

    print(f"  Format items:  {len(body['format_items'])}")
    for item in body["format_items"]:
        print(f"    [{item['format_type']}] {item['original']} → {item['converted']}")
        if item.get("ambiguous"):
            print("      ⚠ Ambiguous — needs manual review")

    print()


def adapt_with_review() -> None:
    """Step 2: Culturally adapt content with reviewer decisions."""
    print("=" * 60)
    print("2. ADAPT — Side-by-side review with accept/reject/edit")
    print("=" * 60)

    # First, analyze to see what segments we're working with.
    httpx.post(
        f"{BASE}/analyze",
        json={
            "text": "It's raining cats and dogs. The report is ready.",
            "target_locale": "de-DE",
        },
        timeout=30,
    ).json()

    # Accept the idiom adaptation for seg-1 (raining cats and dogs).
    adapt_resp = httpx.post(
        f"{BASE}/adapt",
        json={
            "text": "It's raining cats and dogs. The report is ready.",
            "target_locale": "de-DE",
            "asset_id": "example-asset",
            "accepted_ids": ["seg-1"],
        },
        timeout=30,
    )
    assert adapt_resp.status_code == 200
    body = adapt_resp.json()

    print(f"  Adapted text: {body['adapted_text']}")
    print(f"  Segments:     {len(body['segments'])}")
    for seg in body["segments"]:
        decision = seg.get("decision") or "pending"
        print(f"    [{seg['id']}] ({decision})")
        print(f"      Original:  {seg['original']}")
        print(f"      Literal:   {seg['literal']}")
        print(f"      Adapted:   {seg['adapted']}")

    print(f"  Flagged: {body['flagged_segments'] or 'none'}")
    print(f"  Changes: {len(body['changes_log'])} decisions logged")
    print()


def preflight_check() -> None:
    """Step 3: Run a preflight check before publishing."""
    print("=" * 60)
    print("3. PREFLIGHT — Publish gate check")
    print("=" * 60)

    # Clean content — should pass.
    clean = httpx.post(
        f"{BASE}/preflight",
        json={
            "asset_id": "clean-asset",
            "content": "The quarterly report is available for download.",
            "target_locale": "de-DE",
        },
        timeout=30,
    ).json()
    print("  Clean content:")
    print(f"    blocked:      {clean['blocked']}")
    print(f"    audit_status: {clean['audit_status']}")

    # High-risk content — should block.
    risky = httpx.post(
        f"{BASE}/preflight",
        json={
            "asset_id": "risky-asset",
            "content": "That's a load of crap.",
            "target_locale": "de-DE",
        },
        timeout=30,
    ).json()
    print("  Risky content:")
    print(f"    blocked:      {risky['blocked']}")
    print(f"    audit_status: {risky['audit_status']}")
    print(f"    reasons:      {risky['blocked_reasons']}")
    print()


def override_preflight() -> None:
    """Step 4: Override a preflight block."""
    print("=" * 60)
    print("4. OVERRIDE — Explicit human approval to unblock")
    print("=" * 60)

    asset_id = "override-demo"
    # Preflight risky content.
    httpx.post(
        f"{BASE}/preflight",
        json={
            "asset_id": asset_id,
            "content": "That's a load of crap.",
            "target_locale": "de-DE",
        },
        timeout=30,
    )

    # Verify it's blocked.
    before = httpx.get(f"{BASE}/preflight/{asset_id}", timeout=30).json()
    print(f"  Before override: blocked={before['blocked']}, status={before['audit_status']}")

    # Override.
    after = httpx.post(
        f"{BASE}/preflight/{asset_id}/override",
        json={"override": True},
        timeout=30,
    ).json()
    print(f"  After override:  blocked={after['blocked']}, status={after['audit_status']}")
    print()


def export_with_resolution() -> None:
    """Step 5: Export adaptations after resolving low-confidence flags."""
    print("=" * 60)
    print("5. EXPORT — Export with flag resolution")
    print("=" * 60)

    asset_id = "export-demo"
    # Preflight content with low-confidence risks.
    pf = httpx.post(
        f"{BASE}/preflight",
        json={
            "asset_id": asset_id,
            "content": "It's raining cats and dogs.",
            "target_locale": "de-DE",
        },
        timeout=30,
    ).json()

    flagged = [item for item in pf["risk_items"] if item["confidence"] < 0.7]
    if not flagged:
        print("  No low-confidence flags — export would succeed directly.")
        return

    flagged_ids = [item["id"] for item in flagged]
    print(f"  Flagged segments: {flagged_ids}")

    # Export without resolving → blocked (409).
    blocked_resp = httpx.post(
        f"{BASE}/assets/{asset_id}/export",
        json={},
        timeout=30,
    )
    print(f"  Export without resolution: {blocked_resp.status_code} (expected 409)")

    # Export with resolution → success (200).
    resolved_resp = httpx.post(
        f"{BASE}/assets/{asset_id}/export",
        json={"accepted_ids": flagged_ids},
        timeout=30,
    )
    assert resolved_resp.status_code == 200
    body = resolved_resp.json()
    print(f"  Export with resolution:    {resolved_resp.status_code} ✓")
    print(f"  Asset: {body['asset_id']}")
    print()


def main() -> None:
    """Run the full transcreation demo."""
    print("ContentForge Transcreation API — Example Walkthrough\n")
    analyze_cultural_risks()
    adapt_with_review()
    preflight_check()
    override_preflight()
    export_with_resolution()
    print("Done. All transcreation workflows exercised.")


if __name__ == "__main__":
    main()
