# Prompt Templates — Per-Language Generation

Language-adaptive prompt templates that tailor content instructions, brand voice, and output format to the target language. Part of the ContentForge multi-language feature set.

## Overview

Multi-language content generation requires more than translating prompt text — each language has unique grammatical structures, cultural conventions, and audience expectations. The per-language prompt template system provides:

1. **Language-specific templates** — Separate template registries per language with locale-aware instructions.
2. **Brand voice localization** — Brand voice attributes (formality, enthusiasm, jargon) are mapped to culturally appropriate equivalents per language.
3. **Variable injection** — Language, locale, and region are available as template variables for conditional content.
4. **Fallback chain** — If a template is missing for the requested language, the system falls back to `en` (English) with a translation wrapper.
5. **Template versioning** — Each language variant is versioned independently so updates don't break existing scheduled content.

## Architecture

```
contentforge.multilang.templates
├── PromptTemplate        ← Single prompt template (language-scoped)
├── MultiLangTemplateManager ← Registry of per-language templates
├── VoiceLocalizer        ← Maps brand voice attributes per language
└── TemplateFallbackChain ← Fallback logic when template is missing
```

## Usage

### Defining a Language-Specific Template

```python
from contentforge.multilang import PromptTemplate

# English template
en_template = PromptTemplate(
    name="blog-post",
    language="en",
    template_str=(
        "Write a professional blog post about {{topic}}.\n"
        "Target audience: {{audience}}.\n"
        "Tone: {{tone}}\n"
        "Word count: {{word_count}} words."
    ),
    required_variables=["topic", "audience"],
    version="2.1",
)

# Hungarian template — different structure, same variables
hu_template = PromptTemplate(
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
)

# German template
de_template = PromptTemplate(
    name="blog-post",
    language="de",
    template_str=(
        "Schreibe einen professionellen Blogbeitrag über {{topic}}.\n"
        "Zielgruppe: {{audience}}.\n"
        "Ton: {{tone}}\n"
        "Wortanzahl: {{word_count}} Wörter."
    ),
    required_variables=["topic", "audience"],
    version="1.0",
)
```

### Using the MultiLangTemplateManager

```python
from contentforge.multilang import MultiLangTemplateManager, PromptTemplate

tm = MultiLangTemplateManager()

# Register templates for multiple languages
tm.register(en_template)
tm.register(hu_template)
tm.register(de_template)

# Render by name + language — auto-selects the right locale
messages = tm.render("blog-post", language="hu", variables={
    "topic": "Felhőalapú migráció",
    "audience": "IT-vezetők",
    "tone": "szakértői",
    "word_count": 800,
})
# Returns translated system + user message pair in Hungarian
```

### Fallback Behaviour

```python
# Template "blog-post" in French does not exist → falls back to English
messages = tm.render("blog-post", language="fr", variables={
    "topic": "Cloud migration",
    "audience": "CTOs",
    "tone": "professional",
    "word_count": 800,
})
# System generates an English prompt and wraps it with:
# "Generate the response in French (fr)."
```

### Voice Localization

Brand voice attributes are not one-size-fits-all across languages. The `VoiceLocalizer` maps attribute values to culturally appropriate equivalents.

```python
from contentforge.multilang import VoiceLocalizer

localizer = VoiceLocalizer()

# English voice: "professional" with "moderate enthusiasm"
localized = localizer.localize(
    formality=0.8,      # 0.0= casual, 1.0= formal
    enthusiasm=0.6,     # 0.0= reserved, 1.0= excited
    jargon_level=0.3,   # 0.0= simple, 1.0= technical
    target_language="hu",
)
# Hungarian output: formality=0.7 (slightly less formal), 
# enthusiasm=0.5, jargon_level=0.2
# — reflects Hungarian business communication norms
```

## Configuration

### `MultiLangTemplateConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `default_language` | `str` | `"en"` | Fallback language when requested template is missing |
| `auto_register_english` | `bool` | `True` | Register English as the universal fallback on init |
| `template_dir` | `str \| None` | `None` | Directory to load `.md` template files from |

## Prompt Variable Reference

All per-language templates have access to these built-in variables:

| Variable | Type | Source | Description |
|----------|------|--------|-------------|
| `{{language}}` | `str` | Detection/override | ISO 639-1 language code (e.g., `"hu"`) |
| `{{language_name}}` | `str` | Detection/override | Full language name (e.g., `"Hungarian"`) |
| `{{locale}}` | `str` | Config | Full locale with region (e.g., `"hu-HU"`) |
| `{{topic}}` | `str` | User input | Content topic/subject |
| `{{audience}}` | `str` | User input | Target audience description |
| `{{tone}}` | `str` | Voice profile | Tone description for the content |
| `{{word_count}}` | `int` | User/Config | Desired word count |

## Template File Format

Templates can also be loaded from `.md` files:

```markdown
---
name: blog-post
language: de
version: "1.0"
required_variables:
  - topic
  - audience
---

Schreibe einen professionellen Blogbeitrag über {{topic}}.

Zielgruppe: {{audience}}.
Ton: {{tone}}.
Länge: {{word_count}} Wörter.

Berücksichtige die deutschen Geschäftskommunikationsstandards:
- Verwenden Sie die formelle Anrede (Sie)
- Strukturieren Sie den Beitrag mit Zwischenüberschriften
- Fügen Sie am Ende eine Zusammenfassung hinzu
```

Load via:

```python
tm.load_from_file("templates/de/blog-post.md")
```

## See Also

- [Language Detection](language-detection.md) — How language is identified before template selection
- [Translation Pipeline](translation-pipeline.md) — Quality assessment for cross-language output
- [Multilingual Scheduling](scheduling.md) — Scheduling content per language
