#!/usr/bin/env python3
"""
ContentForge API — Brand Voice CRUD Example

Demonstrates creating, listing, fetching, updating, and deleting brand
voice profiles via the REST API.

Prerequisites: ContentForge server running at http://localhost:8000
    uvicorn src.main:app --reload
"""

from __future__ import annotations

from api_client import ContentForgeClient


def main() -> None:
    client = ContentForgeClient("http://localhost:8000")

    # 1. Check the server is alive
    health = client.health()
    print(f"Server: {health['status']} (v{health['version']})")
    print()

    # 2. Create a brand voice
    bv = client.create_brand_voice(
        name="TechCorp Pro",
        description="Professional tech brand voice",
        brand_identity={
            "who": "Enterprise SaaS company",
            "audience": "CTOs and engineering leaders",
            "purpose": "Build trust through clarity",
        },
        attributes=[
            {
                "trait": "formality",
                "value": 0.8,
                "min_label": "Casual",
                "max_label": "Formal",
            },
            {
                "trait": "enthusiasm",
                "value": 0.4,
                "min_label": "Reserved",
                "max_label": "Energetic",
            },
        ],
        vocabulary={
            "preferred": ["scalable", "enterprise-grade", "robust"],
            "banned": ["amazing", "game-changer"],
        },
        scenarios=[
            {
                "name": "crisis",
                "tone_adjustment": "more_formal",
                "banned_terms_extra": ["panic"],
            }
        ],
        formatting={"headers": "sentence_case", "lists": "bullets", "emoji": "never"},
    )
    bv_id = bv["id"]
    print(f"Created brand voice: {bv['name']} (id={bv_id})")
    print(f"  version={bv['version']}, created={bv['created_at']}")
    print()

    # 3. List all brand voices
    voices = client.list_brand_voices()
    print(f"Brand voices: {voices['total']} total")
    for item in voices["items"]:
        print(f"  - {item['name']} ({item['id'][:8]}...) v{item['version']}")
    print()

    # 4. Fetch the brand voice by ID
    fetched = client.get_brand_voice(bv_id)
    print(f"Fetched: {fetched['name']}")
    print(f"  audience={fetched['brand_identity']['audience']}")
    print(f"  preferred_vocab={fetched['vocabulary']['preferred']}")
    print()

    # 5. Update the name (partial update)
    updated = client.update_brand_voice(bv_id, name="TechCorp Pro v2")
    print(f"Updated: {updated['name']} (version now {updated['version']})")
    print()

    # 6. Delete (soft delete)
    client.delete_brand_voice(bv_id)
    print(f"Deleted brand voice {bv_id[:8]}... (soft delete)")
    print()

    # 7. Verify it's gone from listings
    voices_after = client.list_brand_voices()
    print(f"Brand voices after delete: {voices_after['total']} total")

    client.close()


if __name__ == "__main__":
    main()
