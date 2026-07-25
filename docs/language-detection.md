# Language Detection — Multi-Language Content Engine

Auto-detect input language and route content to the appropriate prompt pipeline. Part of the ContentForge multi-language feature set.

## Overview

The language detection module identifies the source language of input text (topic, audience description, or raw content) and enriches the generation context with language metadata. Detection runs before template selection so prompts can be tailored to the detected language.

Key capabilities:

1. **Automatic detection** — Identifies language from free-text input using statistical models (fast-text / heuristics).
2. **Explicit override** — Callers can set `language` explicitly to skip detection and force a target language.
3. **Confidence scoring** — Returns a confidence score per language; low-confidence results can trigger a fallback (e.g., default to English).
4. **Language metadata** — Detected language is injected as a template variable so prompt templates can adapt their instructions per language.
5. **Batch detection** — Process multiple text fragments in a single call for scheduling workflows.

## Supported Languages

| Code   | Language     |
|--------|--------------|
| `en`   | English      |
| `hu`   | Hungarian    |
| `de`   | German       |
| `fr`   | French       |
| `es`   | Spanish      |
| `it`   | Italian      |
| `pt`   | Portuguese   |
| `nl`   | Dutch        |
| `pl`   | Polish       |
| `ro`   | Romanian     |
| `cs`   | Czech        |
| `sv`   | Swedish      |
| `da`   | Danish       |
| `fi`   | Finnish      |
| `nb`   | Norwegian    |
| `ja`   | Japanese     |
| `zh`   | Chinese      |
| `ko`   | Korean       |
| `ar`   | Arabic       |

> The full supported set scales with the underlying detection library (`fast-langdetect` or `langdetect`). Unsupported languages fall back to `en` with a warning.

## Usage

### Basic Detection

```python
from contentforge.multilang import LanguageDetector

detector = LanguageDetector()

# Auto-detect
result = detector.detect("I would like a blog post about cloud computing")
print(result.language)      # "en"
print(result.confidence)    # 0.97
print(result.reliable)      # True

# Short text still works
result = detector.detect("Hola, necesito contenido en español")
print(result.language)      # "es"
print(result.confidence)    # 0.92
```

### Explicit Override

```python
# Skip detection — force a specific language
result = detector.detect(
    "I want content for my German audience",
    default_language="de"   # Override: treat as German regardless of input
)
print(result.language)      # "de"
```

### Batch Detection

```python
fragments = [
    "Blog post about AI trends",
    "Artikel über künstliche Intelligenz",
    "Cikk a magyar piacról",
]
results = detector.detect_batch(fragments)
for r in results:
    print(f"{r.text[:30]:30s} → {r.language} (conf={r.confidence:.2f})")
```

### Integration with ContentForge Generator

```python
from contentforge.services import ContentGenerator
from contentforge.multilang import LanguageDetector

detector = LanguageDetector()
generator = ContentGenerator()

# Detect language first, then generate with language-aware context
topic = "Cloud migration strategies"
lang_info = detector.detect(topic)

result = await generator.generate(
    content_type="blog",
    topic=topic,
    language=lang_info.language,   # Pass to generator for per-language templates
)
```

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_length` | `int` | `10` | Minimum text length (chars) before detection is attempted |
| `fallback_language` | `str` | `"en"` | Default language when detection is unreliable or input is too short |
| `confidence_threshold` | `float` | `0.5` | Minimum confidence to consider a result reliable |
| `provider` | `str` | `"fast-langdetect"` | Backend provider (fast-langdetect, langdetect, or None to disable detection) |

```python
from contentforge.multilang import LanguageDetectorConfig

config = LanguageDetectorConfig(
    min_length=20,
    fallback_language="en",
    confidence_threshold=0.6,
    provider="fast-langdetect",
)
detector = LanguageDetector(config=config)
```

## Data Model

### `LanguageResult`

| Field | Type | Description |
|-------|------|-------------|
| `language` | `str` | Detected language code (ISO 639-1) |
| `confidence` | `float` | Detection confidence (0.0 – 1.0) |
| `reliable` | `bool` | `True` if confidence >= configured threshold |
| `text` | `str` | Original input text (batch operations only) |

## Error Handling

- **Very short input** (< `min_length` chars) returns `fallback_language` with confidence `0.0` and `reliable=False`.
- **Detection library unavailable** — returns `fallback_language` with `reliable=False` and logs a warning.
- **Empty or whitespace-only input** — raises `ValueError`.

## Dependencies

Add to `requirements.txt` or `pyproject.toml`:

```
fast-langdetect>=1.0.0
# or: langdetect>=1.0.9
```

## See Also

- [Prompt Templates (per-language)](prompt-templates.md) — How detected language drives template selection
- [Translation Pipeline](translation-pipeline.md) — Quality assessment and cross-language content
- [Multilingual Scheduling](scheduling.md) — Timezone-aware publishing per language
