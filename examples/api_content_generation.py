#!/usr/bin/env python3
"""
ContentForge API — Content Generation Example

Demonstrates generating blog, social, and email content via the LLM
endpoint with brand voice injection.

Prerequisites: ContentForge server running at http://localhost:8000
    uvicorn src.main:app --reload
"""

from __future__ import annotations

from api_client import ContentForgeClient


def main() -> None:
    client = ContentForgeClient("http://localhost:8000")

    # 1. Create a brand voice for generation
    bv = client.create_brand_voice(
        name="Startup Vibes",
        description="Casual, energetic startup voice",
        brand_identity={
            "who": "Early-stage B2B SaaS startup",
            "audience": "Founders and indie hackers",
            "purpose": "Inspire action with authentic, direct language",
        },
        attributes=[
            {
                "trait": "formality",
                "value": 0.3,
                "min_label": "Casual",
                "max_label": "Formal",
            },
        ],
        vocabulary={
            "preferred": ["ship", "iterate", "growth", "build"],
            "banned": ["synergy", "leverage", "paradigm"],
        },
    )
    bv_id = bv["id"]
    print(f"Using brand voice: {bv['name']} ({bv_id[:8]}...)")
    print()

    # 2. Generate a blog post
    print("─" * 50)
    print("Generating blog post...")
    print("─" * 50)
    blog = client.generate_content(
        content_type="blog",
        topic="Why your startup should ship before it's perfect",
        brand_voice_id=bv_id,
        audience="Indie founders",
        length="short",
        include_cta=True,
    )
    print(f"  ID: {blog['id']}")
    print(f"  Model: {blog['model_used']}")
    print(f"  Tokens: {blog['tokens_used']}")
    print(f"  Latency: {blog['latency_ms']}ms")
    print(f"  Compliance: {blog['compliance_score']['overall']:.0%}")
    print(f"\n  Content ({len(blog['generated_text'])} chars):")
    print(f"  {blog['generated_text'][:300]}...")
    print()

    # 3. Generate social media copy
    print("─" * 50)
    print("Generating social media post...")
    print("─" * 50)
    social = client.generate_content(
        content_type="social",
        topic="We just shipped v2.0 with real-time collaboration",
        brand_voice_id=bv_id,
        length="short",
        custom_instructions="Make it punchy, under 280 chars if possible",
    )
    print(f"  ID: {social['id']}")
    print(f"  Content: {social['generated_text'][:280]}")
    print()

    # 4. Generate email copy
    print("─" * 50)
    print("Generating email...")
    print("─" * 50)
    email = client.generate_content(
        content_type="email",
        topic="Welcome to the platform — getting started guide",
        brand_voice_id=bv_id,
        audience="New users",
        length="medium",
    )
    print(f"  ID: {email['id']}")
    print(f"  Subject-like opening: {email['generated_text'][:150]}...")
    print()

    # 5. Verify content list via analytics (will be stub data)
    summary = client.get_analytics_summary()
    print(f"Total generations (analytics): {summary['total_generations']}")

    client.close()


if __name__ == "__main__":
    main()
