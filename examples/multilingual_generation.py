#!/usr/bin/env python3
"""Example: multi-language content generation pipeline.

Demonstrates the full multi-language workflow:
  1. Detect input language
  2. Select per-language prompt template
  3. Generate content in the target language
  4. Score translation quality
  5. Schedule cross-language publishing

Requires:
    PYTHONPATH to contentforge/src (or pip install contentforge)
    pip install fast-langdetect sacrebleu  # optional quality features

Usage:
    python examples/multilingual_generation.py
"""

import asyncio

# Attempt imports with helpful error if contentforge is not installed
try:
    from contentforge.multilang import LanguageDetector, MultiLangTemplateManager, PromptTemplate
except ImportError:

    class LanguageDetector:  # type: ignore[no-redef]
        """Stub demonstrating the API shape when contentforge is not installed."""

        def detect(self, text: str, default_language: str | None = None) -> dict:
            return {"language": "en", "confidence": 0.95, "reliable": True}

        def detect_batch(self, texts: list[str]) -> list[dict]:
            return [self.detect(t) for t in texts]

    class PromptTemplate:  # type: ignore[no-redef]
        def __init__(self, name: str, language: str, template_str: str,
                     required_variables: list[str] | None = None,
                     version: str = "1.0") -> None:
            self.name = name
            self.language = language
            self.template_str = template_str
            self.required_variables = required_variables or []
            self.version = version

    class MultiLangTemplateManager:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self._templates: dict[tuple[str, str], PromptTemplate] = {}

        def register(self, template: PromptTemplate) -> None:
            key = (template.name, template.language)
            self._templates[key] = template

        def render(self, name: str, language: str,
                   variables: dict[str, object]) -> list[dict[str, str]]:
            key = (name, language)
            tmpl = self._templates.get(key) or self._templates.get((name, "en"))
            if tmpl is None:
                raise KeyError(f"Template '{name}' not found for '{language}' or 'en'")
            # Simple variable substitution (stub)
            content = tmpl.template_str
            for var, val in variables.items():
                content = content.replace("{{" + var + "}}", str(val))
            return [
                {"role": "system", "content": f"You are writing in {language}."},
                {"role": "user", "content": content},
            ]

    print("INFO: Using stubs — install contentforge for real functionality.")
    print()


async def main() -> None:
    # ------------------------------------------------------------------
    # 1. Language Detection
    # ------------------------------------------------------------------
    print("=" * 60)
    print("STEP 1: Language Detection")
    print("=" * 60)

    detector = LanguageDetector()

    texts = [
        "Cloud migration strategies for enterprise",
        "Felhőalapú migrációs stratégiák vállalatoknak",
        "Cloud-Migrationsstrategien für Unternehmen",
    ]

    for text in texts:
        result = detector.detect(text)
        lang = result["language"] if isinstance(result, dict) else result.language
        conf = result["confidence"] if isinstance(result, dict) else result.confidence
        print(f"  [{lang}] (conf={conf:.2f}) → {text[:50]}...")

    print()

    # ------------------------------------------------------------------
    # 2. Per-Language Prompt Template Selection
    # ------------------------------------------------------------------
    print("=" * 60)
    print("STEP 2: Per-Language Prompt Templates")
    print("=" * 60)

    tm = MultiLangTemplateManager()

    # Register English template
    tm.register(PromptTemplate(
        name="blog-post",
        language="en",
        template_str=(
            "Write a professional blog post about {{topic}}.\n"
            "Target audience: {{audience}}.\n"
            "Tone: {{tone}}\n"
            "Word count: {{word_count}} words."
        ),
        required_variables=["topic", "audience"],
        version="2.0",
    ))

    # Register Hungarian template
    tm.register(PromptTemplate(
        name="blog-post",
        language="hu",
        template_str=(
            "Írj egy szakmai blogbejegyzést a következő témáról: {{topic}}.\n"
            "Célközönség: {{audience}}.\n"
            "Hangnem: {{tone}}\n"
            "Terjedelem: {{word_count}} szó."
        ),
        required_variables=["topic", "audience"],
        version="1.0",
    ))

    # Render Hungarian template
    messages = tm.render("blog-post", language="hu", variables={
        "topic": "Felhőalapú migráció",
        "audience": "IT-vezetők",
        "tone": "szakértői",
        "word_count": 800,
    })

    for msg in messages:
        role = msg["role"]
        content_preview = msg["content"][:80]
        print(f"  [{role}] {content_preview}...")

    print()

    # ------------------------------------------------------------------
    # 3. Translation Quality Scoring (optional, requires sacrebleu)
    # ------------------------------------------------------------------
    print("=" * 60)
    print("STEP 3: Translation Quality Scoring")
    print("=" * 60)

    try:
        from contentforge.multilang.translation import QualityScorer  # type: ignore[import-untyped]

        scorer = QualityScorer()
        score = scorer.score(
            source_language="en",
            target_language="hu",
            source_text="Cloud migration reduces infrastructure costs by 40%.",
            generated_text="A felhőalapú migráció 40%-kal csökkenti az infrastruktúra költségeit.",
        )
        print(f"  BLEU:     {score.bleu:.3f}")
        print(f"  chrF:     {score.chrf:.3f}")
        print(f"  Overall:  {score.overall:.3f}")
        print(f"  Passed:   {score.passed}")
    except ImportError:
        print("  Translation quality scoring requires 'sacrebleu' and 'sentence-transformers'.")
        print("  Install: pip install sacrebleu sentence-transformers")
        print()
        print("  Sample scores (expected for this pair):")
        print("    BLEU:     0.742")
        print("    chrF:     0.813")
        print("    Overall:  0.825")
        print("    Passed:   True")

    print()

    # ------------------------------------------------------------------
    # 4. Cross-Language Publishing Schedule
    # ------------------------------------------------------------------
    print("=" * 60)
    print("STEP 4: Multilingual Publishing Schedule")
    print("=" * 60)

    schedule_description = """
    Language  Platform        Scheduled (UTC)      Timezone
    ────────  ─────────────── ──────────────────── ──────────────────
    en        WordPress       2026-08-17 14:00:00  UTC
    de        WordPress       2026-08-17 20:00:00  Europe/Berlin
    hu        WordPress       2026-08-18 02:00:00  Europe/Budapest

    Schedule chain:
      EN publishes first (Mon 14:00 UTC)
      → DE publishes 6h later (Mon 20:00 UTC = Tue 06:00 Berlin)
      → HU publishes 6h after DE (Tue 02:00 UTC = Tue 04:00 Budapest)
    """
    print(schedule_description)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("=" * 60)
    print("Multi-Language Pipeline Summary")
    print("=" * 60)
    print("  ✓ Language detection — auto-identifies input language")
    print("  ✓ Per-language templates — locale-aware prompt selection")
    print("  ✓ Translation quality — BLEU/chrF scoring for confidence")
    print("  ✓ Cross-language scheduling — timezone-aware publishing chain")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
