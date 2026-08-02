#!/usr/bin/env python3
"""
ContentForge API — AI Visibility Metrics Example

Walks the AI visibility loop: generate content (or reuse an existing
generation), ingest AI-referred visits for all four engines, run an
on-demand visibility refresh, then query the per-content snapshot and the
Chart.js-ready trends feed.

The example runs without any AI provider API keys: the referral endpoints
and the snapshot/trends queries need no credentials, and the on-demand
refresh degrades gracefully (every engine without a configured key returns
a "not mentioned" result instead of failing).

Prerequisites:
    ContentForge server running at http://localhost:8000
        uvicorn src.main:app --reload

    If you already have a generation id (e.g. from a previous run or a
    seeded database), pass it to skip the LLM generation step:

        CONTENTFORGE_GENERATION_ID=gen_abc123 python examples/api_ai_visibility.py

Usage:
    python examples/api_ai_visibility.py
"""

from __future__ import annotations

import os

from api_client import ContentForgeClient

# Canonical AI engines tracked by ContentForge (brief §4.5).
ENGINES = ("chatgpt", "perplexity", "gemini", "google_ai_overviews")

# Real referrer domains, matching AI_ENGINE_REFERRER_DOMAINS in models.py.
REFERRER_DOMAINS = {
    "chatgpt": "chatgpt.com",
    "perplexity": "perplexity.ai",
    "gemini": "gemini.google.com",
    "google_ai_overviews": "google.com",
}


def main() -> None:
    client = ContentForgeClient("http://localhost:8000")

    # 1. Generate content first (or reuse an existing generation)
    gen_id = os.environ.get("CONTENTFORGE_GENERATION_ID", "")
    if not gen_id:
        bv = client.create_brand_voice(
            name="AI Visibility Test Voice",
            description="Test brand for AI visibility demo",
            brand_identity={
                "who": "Demo company",
                "audience": "Demo audience",
                "purpose": "Demonstrate AI visibility metrics",
            },
            attributes=[
                {
                    "trait": "formality",
                    "value": 0.5,
                    "min_label": "Casual",
                    "max_label": "Formal",
                },
            ],
            vocabulary={"preferred": ["demo", "example"], "banned": []},
        )
        content = client.generate_content(
            content_type="blog",
            topic="Understanding AI visibility",
            brand_voice_id=bv["id"],
            length="short",
        )
        gen_id = content["id"]
    print(f"Using generation: {gen_id}")
    print()

    # 2. Ingest AI-referred visits for all four engines
    print("─" * 60)
    print("Ingesting AI referrals (POST /api/v1/ai-visibility/referral)")
    print("─" * 60)
    for i, engine in enumerate(ENGINES):
        # Convert the first two engines' referrals to exercise conversion
        # metrics; keep the rest as plain visits.
        converted = i < 2
        resp = client.ingest_ai_referral(
            generation_id=gen_id,
            engine=engine,
            referrer_url=f"https://{REFERRER_DOMAINS[engine]}/c/demo-{i}",
            landing_path="/blog/understanding-ai-visibility",
            converted=converted,
            conversion_value=42.0 if converted else 0.0,
        )
        print(f"  {engine:>20} -> {resp}")
    print()

    # 3. On-demand visibility refresh (no API keys needed to run the cycle)
    print("─" * 60)
    print("On-demand refresh (POST /api/v1/ai-visibility/{id}/refresh)")
    print("─" * 60)
    poll = client.refresh_ai_visibility(gen_id)
    print(f"  engines polled:  {poll['engines_polled']}")
    print(f"  queries run:     {poll['queries_run']}")
    print(f"  mentions:        {poll['mentions_recorded']}")
    print(f"  errors:          {poll['errors']}")
    print()

    # 4. Per-content AI visibility snapshot
    print("─" * 60)
    print("Snapshot (GET /api/v1/ai-visibility/{content_id})")
    print("─" * 60)
    snap = client.get_ai_visibility(gen_id, days=30)
    print(f"  topic:      {snap['topic']}")
    print(f"  window:     {snap['date_from']} .. {snap['date_to']}")
    summary = snap["summary"]
    print(f"  total_mentions:        {summary['total_mentions']}")
    print(f"  total_citations:       {summary['total_citations']}")
    print(f"  overall_citation_rate: {summary['overall_citation_rate']:.3f}")
    print(f"  ai_referral_traffic:   {summary['ai_referral_traffic']}")
    print(f"  ai_referral_conversions: {summary['ai_referral_conversions']}")
    print()
    for engine in snap["engines"]:
        print(
            f"  {engine['engine']:>20}: "
            f"{engine['mentions']} mentions, {engine['citations']} citations, "
            f"soV {engine['share_of_voice']:.1f}, "
            f"ref traffic {engine['ai_referral_traffic']}"
        )
    print()

    # 5. Chart.js-ready trends feed
    print("─" * 60)
    print("Trends (GET /api/v1/ai-visibility/trends)")
    print("─" * 60)
    trends = client.get_ai_visibility_trends(days=30)
    print(f"  period:   {trends['period']} ({trends['days']} days)")
    print(f"  labels:   {len(trends['dates'])} dates "
          f"({trends['dates'][0]} .. {trends['dates'][-1]})")
    print(f"  series:   {len(trends['series'])} dataset(s)")
    for s in trends["series"][:5]:
        print(f"    {s['engine']:>20} {s['metric']:<22} "
              f"n={len(s['data'])} last={s['data'][-1]}")
    print(f"  totals:   {trends['totals']}")

    client.close()


if __name__ == "__main__":
    main()
