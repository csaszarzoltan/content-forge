"""Fix pytestmark in files that lost their asyncio marker.

The main-profile script replaced `pytestmark = pytest.mark.asyncio`
with `pytestmark = pytest.mark.quick`. We need both markers for async files.
"""
import re

LOST = [
    "tests/test_ab_test.py",
    "tests/test_analytics.py",
    "tests/test_analytics_ab.py",
    "tests/test_analytics_export.py",
    "tests/test_analytics_scoring.py",
    "tests/test_analytics_trends.py",
    "tests/test_auto_detection.py",
    "tests/test_brand_voice_crud.py",
    "tests/test_content_gen.py",
    "tests/test_publish_integration.py",
    "tests/test_scheduling.py",
    "tests/test_seo_analyzer.py",
    "tests/test_seo_meta_tags.py",
    "tests/test_seo_readability.py",
]

fixed = 0
for f in LOST:
    with open(f) as fh:
        content = fh.read()
    
    # Replace single marker with list of both
    old = "pytestmark = pytest.mark.quick"
    new = "pytestmark = [pytest.mark.asyncio, pytest.mark.quick]"
    if old in content and new not in content:
        content = content.replace(old, new, 1)  # first occurrence only
        with open(f, 'w') as fh:
            fh.write(content)
        print(f"FIXED: {f}")
        fixed += 1
    else:
        print(f"SKIP (pattern not found or already fixed): {f}")

print(f"\nFixed {fixed}/{len(LOST)} files")
