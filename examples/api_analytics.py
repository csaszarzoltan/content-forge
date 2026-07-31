#!/usr/bin/env python3
"""
ContentForge API — Analytics Dashboard Example

Walks the full analytics loop: generate content, track engagement events,
then query the dashboard, per-content performance, channel comparison,
content score, trends, anomalies, and export (CSV + JSON).

Prerequisites:
    ContentForge server running at http://localhost:8000
        uvicorn src.main:app --reload

    If you already have a generation id (e.g. from a previous run or a
    seeded database), pass it to skip the LLM generation step:

        CONTENTFORGE_GENERATION_ID=gen_abc123 python examples/api_analytics.py

Usage:
    python examples/api_analytics.py
"""

from __future__ import annotations

import os
import sys

from api_client import ContentForgeClient


def main() -> None:
    client = ContentForgeClient("http://localhost:8000")

    # 1. Generate content first (or reuse an existing generation)
    gen_id = os.environ.get("CONTENTFORGE_GENERATION_ID", "")
    if not gen_id:
        bv = client.create_brand_voice(
            name="Analytics Test Voice",
            description="Test brand for analytics demo",
            brand_identity={
                "who": "Demo company",
                "audience": "Demo audience",
                "purpose": "Demonstrate analytics features",
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
            topic="Understanding content analytics",
            brand_voice_id=bv["id"],
            length="short",
        )
        gen_id = content["id"]
    print(f"Using generation: {gen_id}")
    print()

    # 2. Track engagement events across channels
    print("─" * 60)
    print("Tracking events (POST /api/v1/analytics/track)")
    print("─" * 60)
    events = [
        ("medium", "impression", 500),
        ("medium", "click", 40),
        ("twitter", "impression", 300),
        ("twitter", "click", 25),
        ("twitter", "share", 8),
        ("email", "impression", 200),
        ("email", "conversion", 5),
        ("blog", "read_time", 180),
    ]
    for channel, event_type, value in events:
        resp = client.track_event(
            generation_id=gen_id,
            event_type=event_type,
            channel=channel,
            value=value,
        )
        print(f"  {channel:8s} {event_type:10s} value={value:4d} -> event_id={resp['event_id'][:8]}...")
    print()

    # 3. Dashboard (aggregated metrics, default window: last 30 days)
    print("─" * 60)
    print("Dashboard (GET /api/v1/analytics/dashboard)")
    print("─" * 60)
    dash = client.get_dashboard()
    totals = dash["totals"]
    print(f"  Impressions:   {totals['impressions']}")
    print(f"  Clicks:        {totals['clicks']}")
    print(f"  Shares:        {totals['shares']}")
    print(f"  Comments:      {totals['comments']}")
    print(f"  Conversions:   {totals['conversions']}")
    print(f"  Engagement:    {totals['engagement_rate']:.1%}")
    print(f"  Top content:   {[(t['topic'][:30], t['impressions']) for t in dash['top_content']]}")
    print()

    # 4. Per-content performance
    print("─" * 60)
    print("Per-content performance (GET /api/v1/analytics/content/{id})")
    print("─" * 60)
    perf = client.get_content_performance(gen_id)
    print(f"  Topic:         {perf['topic']}")
    print(f"  Compliance:    {perf['compliance']['overall']:.0f}/100")
    print(f"  Views:         {perf['performance']['views']}")
    print(f"  Engagement:    {perf['performance']['engagement_rate']:.1%}")
    print(f"  Channels:      {list(perf['channel_breakdown'].keys())}")
    print()

    # 5. Channel comparison
    print("─" * 60)
    print("Channel comparison (GET /api/v1/analytics/channels)")
    print("─" * 60)
    channels = client.get_channel_comparison(metric="impressions")
    print(f"  Best channel:  {channels['best_channel']}")
    for row in channels["channels"]:
        print(f"  {row['channel']:8s} impressions={row['impressions']:5d} "
              f"clicks={row['clicks']:4d} engagement={row['engagement_rate']:.1%}")
    print()

    # 6. Content score
    print("─" * 60)
    print("Content score (GET /api/v1/analytics/score/{id})")
    print("─" * 60)
    score = client.get_content_score(gen_id)
    print(f"  Score: {score['score']} (grade {score['grade']})")
    for name, value in score["breakdown"].items():
        print(f"    {name:12s} {value:.2f}")
    print()

    # 7. Trends + anomalies (need >= 7 days of data for anomaly detection)
    print("─" * 60)
    print("Trends (GET /api/v1/analytics/trends?period=30d)")
    print("─" * 60)
    trends = client.get_trends(period="30d", metric="impressions")
    flagged = [p["date"] for p in trends["points"] if p["anomaly"]]
    print(f"  Days with data: {len(trends['points'])}")
    print(f"  Anomaly days:   {flagged or 'none'}")
    anomalies = client.get_anomalies(period="30d", metric="impressions")
    for item in anomalies["anomalies"]:
        print(f"  {item['date']}: {item['metric']}={item['value']:.0f} "
              f"z={item['z_score']:.2f} ({item['direction']})")
    print()

    # 8. Export (JSON + CSV)
    print("─" * 60)
    print("Export (GET /api/v1/analytics/export)")
    print("─" * 60)
    export_json = client.export_analytics(format="json")
    print(f"  JSON filename: {export_json['filename']} ({export_json['content_type']})")
    print(f"  JSON rows:     {export_json['data']}")
    export_csv = client.export_analytics(format="csv")
    print(f"  CSV filename:  {export_csv['filename']} ({export_csv['content_type']})")
    print(f"  CSV preview:   {export_csv['data'].splitlines()[0]}")
    print()

    # 9. Error handling — unknown generation is a 404
    print("─" * 60)
    print("Error handling — non-existent generation:")
    print("─" * 60)
    try:
        client.get_content_performance("gen_nonexistent")
    except Exception as exc:  # noqa: BLE001 - httpx.HTTPStatusError
        print(f"  Expected error: {exc}")

    client.close()


if __name__ == "__main__":
    sys.exit(main())
