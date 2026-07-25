# Translation Pipeline — Quality Assessment

Automated translation quality scoring, cross-language consistency checks, and post-processing for the ContentForge multi-language content engine.

## Overview

The translation pipeline evaluates content quality across languages, ensuring that translated or generated content maintains brand voice consistency, factual accuracy, and readability regardless of target language.

Key capabilities:

1. **Quality scoring** — BLEU, chrF, and semantic similarity metrics to score output quality per language.
2. **Cross-language consistency** — Compare content across languages to detect tone, structure, or factual drift.
3. **Brand voice preservation** — Verify that brand voice attributes are maintained after translation/localization.
4. **Automated post-processing** — Fix common issues (missing punctuation, inconsistent terminology, formatting errors).
5. **Human review queue** — Low-scoring content is flagged for manual review with context attached.

## Architecture

```
contentforge.multilang.translation
├── QualityScorer           ← BLEU/chrF/semantic scoring
├── ConsistencyChecker      ← Cross-language comparison
├── PostProcessor           ← Rule-based fix-ups
├── ReviewQueue             ← Low-score content for human review
└── TranslationProvider     ← External TTS/translation API adapter
```

## Usage

### Scoring Generated Content

```python
from contentforge.multilang.translation import QualityScorer

scorer = QualityScorer()

# Score a generated Hungarian blog post against reference
score = scorer.score(
    source_language="en",
    target_language="hu",
    source_text="Cloud migration reduces infrastructure costs by 40%.",
    generated_text="A felhőalapú migráció 40%-kal csökkenti az infrastruktúra költségeit.",
)

print(f"BLEU:       {score.bleu:.3f}")       # 0.742
print(f"chrF:       {score.chrf:.3f}")        # 0.813
print(f"Semantic:   {score.semantic_similarity:.3f}")  # 0.921
print(f"Overall:    {score.overall:.3f}")      # 0.825
print(f"Pass:       {score.passed}")           # True (threshold=0.7)
```

### Consistency Checking

```python
from contentforge.multilang.translation import ConsistencyChecker

checker = ConsistencyChecker()

# Compare the same content across multiple languages
results = checker.check([
    {"language": "en", "text": "Our AI platform uses machine learning to optimize workflows."},
    {"language": "de", "text": "Unsere KI-Plattform nutzt maschinelles Lernen zur Optimierung von Arbeitsabläufen."},
    {"language": "hu", "text": "AI platformunk gépi tanulást használ a munkafolyamatok optimalizálására."},
])

print(f"Tone drift:      {results.tone_drift:.2f}")       # 0.12 (low = consistent)
print(f"Factual drift:   {results.factual_drift:.2f}")    # 0.05 (very consistent)
print(f"Structure match: {results.structure_match:.2f}")   # 0.93 (similar structure)
print(f"Warnings:        {results.warnings}")              # []
```

### Brand Voice Preservation

```python
from contentforge.multilang.translation import VoicePreservationScorer

voice_scorer = VoicePreservationScorer()

profile = {
    "formality": 0.8,
    "enthusiasm": 0.6,
    "jargon_level": 0.3,
}

# Check if German output preserves the English brand voice
result = voice_scorer.score_preservation(
    source_language="en",
    target_language="de",
    voice_profile=profile,
    source_text="We're excited to announce our revolutionary new product!",
    translated_text="Wir freuen uns, unser neues revolutionäres Produkt anzukündigen.",
)

print(f"Formality match:   {result.formality_match:.2f}")   # 0.85
print(f"Enthusiasm match:  {result.enthusiasm_match:.2f}")  # 0.78
print(f"Jargon match:      {result.jargon_match:.2f}")      # 0.90
print(f"Overall:           {result.overall:.2f}")           # 0.84
```

## Quality Metrics

### `QualityScore`

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `bleu` | `float` | 0.0–1.0 | BLEU score (n-gram precision against reference) |
| `chrf` | `float` | 0.0–1.0 | chrF score (character n-gram F-score) |
| `semantic_similarity` | `float` | 0.0–1.0 | Embedding-based semantic similarity |
| `overall` | `float` | 0.0–1.0 | Weighted composite score |
| `passed` | `bool` | — | `overall >= threshold` |
| `threshold` | `float` | — | Configurable pass/fail threshold |

### `ConsistencyReport`

| Field | Type | Description |
|-------|------|-------------|
| `tone_drift` | `float` | 0.0 (identical) to 1.0 (completely different tone) |
| `factual_drift` | `float` | 0.0 (identical facts) to 1.0 (contradictory facts) |
| `structure_match` | `float` | 0.0 (different structure) to 1.0 (same structure) |
| `warnings` | `list[str]` | Human-readable warnings (e.g., "Missing key term: 'machine learning' in Hungarian") |

## Post-Processing

Automated fix-ups applied after generation/translation:

| Rule | Languages | Description |
|------|-----------|-------------|
| `punctuation_fix` | All | Normalize quotes, fix spacing around punctuation |
| `capitalization` | de | Capitalize German nouns |
| `article_normalization` | hu | Fix Hungarian definite/indefinite article agreement |
| `number_format` | All | Normalize decimal separators (`,` vs `.`) per locale |
| `whitespace` | ja, zh | Remove unnecessary spaces in CJK text |

```python
from contentforge.multilang.translation import PostProcessor

processor = PostProcessor()
text = processor.apply("hallo welt! dies ist ein test.", language="de")
print(text)  # "Hallo Welt! Dies ist ein Test."  (capitalizes German nouns)
```

## Configuration

### `TranslationPipelineConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `quality_threshold` | `float` | `0.65` | Minimum overall score to auto-pass |
| `bleu_weight` | `float` | `0.3` | BLEU weight in composite score |
| `chrf_weight` | `float` | `0.3` | chrF weight in composite score |
| `semantic_weight` | `float` | `0.4` | Semantic similarity weight in composite score |
| `post_process` | `bool` | `True` | Enable automatic post-processing |
| `human_review_threshold` | `float` | `0.4` | Scores below this go to the human review queue |
| `consistency_check_enabled` | `bool` | `True` | Enable cross-language consistency checks |

## Human Review Queue

Content that scores below `human_review_threshold` is queued for manual review:

```python
from contentforge.multilang.translation import ReviewQueue

queue = ReviewQueue()

# Check if there's content awaiting review
pending = queue.list_pending()
for item in pending:
    print(f"[{item.id}] {item.source_language} → {item.target_language}")
    print(f"  Score: {item.score} — Reason: {item.reason}")

# Approve or reject
queue.approve(item.id)
queue.reject(item.id, reason="Tone does not match brand voice")
```

## Dependencies

Add to `requirements.txt` or `pyproject.toml`:

```
sacrebleu>=2.4.0
sentence-transformers>=2.2.0
```

## See Also

- [Language Detection](language-detection.md) — Input language identification
- [Prompt Templates (per-language)](prompt-templates.md) — Language-adaptive template system
- [Multilingual Scheduling](scheduling.md) — Cross-language publishing schedule
