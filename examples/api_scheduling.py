#!/usr/bin/env python3
"""
ContentForge API — Scheduling Example

Demonstrates scheduling generated content, checking status, and
cancelling a scheduled post.

Prerequisites: ContentForge server running at http://localhost:8000
    uvicorn src.main:app --reload
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from api_client import ContentForgeClient


def main() -> None:
    client = ContentForgeClient("http://localhost:8000")

    # 1. First create a brand voice and generate content to schedule
    bv = client.create_brand_voice(
        name="Editorial Voice",
        description="Balanced editorial voice for scheduled content",
        brand_identity={
            "who": "Technology publication",
            "audience": "Developers and IT decision-makers",
            "purpose": "Educate and inform",
        },
        attributes=[
            {
                "trait": "formality",
                "value": 0.6,
                "min_label": "Casual",
                "max_label": "Formal",
            },
        ],
        vocabulary={
            "preferred": ["architecture", "pattern", "design", "trade-off"],
            "banned": ["seamless", "next-gen"],
        },
    )
    bv_id = bv["id"]

    # 2. Generate the content
    content = client.generate_content(
        content_type="blog",
        topic="Event-driven architecture patterns for 2026",
        brand_voice_id=bv_id,
        audience="Senior developers",
        length="medium",
    )
    gen_id = content["id"]
    print(f"Generated content: {gen_id[:8]}...")
    print()

    # 3. Schedule it for tomorrow
    publish_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    schedule = client.schedule_content(
        generation_id=gen_id,
        publish_at=publish_at,
        platform="blog",
        platform_config={"channel_id": "engineering-blog"},
        retry_on_failure=True,
        max_retries=3,
    )
    sch_id = schedule["schedule_id"]
    print(f"Scheduled content:")
    print(f"  Schedule ID: {sch_id}")
    print(f"  Status: {schedule['status']}")
    print(f"  Platform: {schedule['platform']}")
    print(f"  Publish at: {schedule['publish_at']}")
    print()

    # 4. Check status
    status = client.get_schedule_status(sch_id)
    print(f"Schedule status check:")
    print(f"  Status: {status['status']}")
    print(f"  Retries: {status['retry_count']}/{status['max_retries']}")
    print()

    # 5. Cancel the schedule
    client.cancel_schedule(sch_id)
    print(f"Cancelled schedule {sch_id[:8]}...")

    client.close()


if __name__ == "__main__":
    main()
