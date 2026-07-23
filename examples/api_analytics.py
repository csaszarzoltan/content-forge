#!/usr/bin/env python3
"""
ContentForge API — Analytics Example

Demonstrates per-content analytics and aggregate summary queries.

Prerequisites: ContentForge server running at http://localhost:8000
    uvicorn src.main:app --reload
"""

from __future__ import annotations

from api_client import ContentForgeClient


def main() -> None:
    client = ContentForgeClient("http://localhost:8000")

    # 1. Generate some content first
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
    bv_id = bv["id"]

    content = client.generate_content(
        content_type="blog",
        topic="Understanding content analytics",
        brand_voice_id=bv_id,
        length="short",
    )
    gen_id = content["id"]
    print(f"Generated content for analytics: {gen_id[:8]}...")
    print()

    # 2. Get per-content analytics
    print("─" * 50)
    print("Per-content analytics:")
    print("─" * 50)
    analytics = client.get_content_analytics(gen_id)
    print(f"  Generation ID: {analytics['generation_id'][:16]}...")
    print(f"  Content type: {analytics['content_type']}")
    print(f"  Model: {analytics['model_used']}")
    print(f"  Tokens: {analytics['tokens_used']}")
    print(f"  Compliance:")
    print(f"    Overall: {analytics['compliance']['overall']:.0%}")
    print(f"    Vocabulary: {analytics['compliance']['vocabulary']:.0%}")
    print(f"    Readability: {analytics['compliance']['readability']:.0%}")
    print(f"    Tone: {analytics['compliance']['tone']:.0%}")
    print(f"    Violations: {analytics['compliance']['violations']}")
    print(f"  Performance:")
    print(f"    Views: {analytics['performance']['views']}")
    print(f"    Engagement rate: {analytics['performance']['engagement_rate']:.1%}")
    print(f"    Shares: {analytics['performance']['shares']}")
    print()

    # 3. Get aggregate summary
    print("─" * 50)
    print("Aggregate analytics summary:")
    print("─" * 50)
    summary = client.get_analytics_summary()
    print(f"  Total generations: {summary['total_generations']}")
    print(f"  Avg compliance: {summary['avg_compliance']:.0%}")
    print(f"  Content type breakdown: {summary['content_type_breakdown']}")
    print(f"  Total views: {summary['total_views']}")
    print(f"  Avg engagement rate: {summary['avg_engagement_rate']:.1%}")
    print()

    # 4. Fetch a non-existent generation (expect 404)
    print("─" * 50)
    print("Error handling — non-existent generation:")
    print("─" * 50)
    try:
        client.get_content_analytics("gen_nonexistent")
    except Exception as exc:
        print(f"  Expected error: {exc}")

    client.close()


if __name__ == "__main__":
    main()
