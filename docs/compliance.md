# Compliance Scoring — Brand Voice Compliance

The `brand_voice.compliance` module scores generated text against brand voice rules, including vocabulary adherence, readability (Flesch-Kincaid), and banned term detection.

## ComplianceResult

The output of every scoring operation.

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `overall_score` | `float` | 0.0–1.0 | Weighted compliance score |
| `vocabulary_score` | `float` | 0.0–1.0 | Vocabulary adherence (preferred words − banned penalty) |
| `readability_score` | `float` | 0.0–1.0 | Flesch-Kincaid-based readability |
| `tone_score` | `float` | 0.0–1.0 | Tone alignment (1.0 if no banned terms) |
| `banned_terms_found` | `list[str]` | — | Banned terms detected in text |
| `violations` | `list[str]` | — | Human-readable violation descriptions |

## ComplianceScorer

### Initialization

```python
from brand_voice.presets import PresetManager
from brand_voice.compliance import ComplianceScorer

mgr = PresetManager()
profile = mgr.get_preset("formal")
scorer = ComplianceScorer(profile)
```

### Scoring Text

```python
# Clean text — scores 1.0
result = scorer.score("We offer scalable and robust solutions for enterprise teams.")
print(result.overall_score)  # 1.0
print(result.violations)     # []

# Text with banned terms — score drops
bad_text = "We need to pivot our strategy and disrupt the market."
result = scorer.score(bad_text)
print(result.overall_score)        # < 0.5
print(result.banned_terms_found)   # ["pivot", "disrupt"]
print(result.violations)           # ["Banned term found: 'pivot'", ...]
```

### Checking Individual Rules

```python
# Check for banned terms only
found = scorer.check_banned_terms("Let's pivot on this.")
# Returns: ["pivot"]

# Vocabulary analysis
analysis = scorer.check_vocabulary("We designed robust, scalable solutions.")
print(analysis["preferred_ratio"])   # e.g., 0.4
print(analysis["banned_count"])      # 0
print(analysis["preferred_count"])   # 2

# Readability score (Flesch-Kincaid normalized to 0–1)
score = scorer.check_readability("This is an easily readable sentence.")
print(score)  # Between 0.0 and 1.0
```

### Scoring Algorithm

1. **Vocabulary score**: Ratio of preferred terms used. Penalized −0.3 per banned term found (floor 0.0).
2. **Readability score**: Flesch-Kincaid grade level normalized to 0–1. Grade 0 → 1.0, grade 14+ → 0.0.
3. **Tone score**: Starts at 1.0. Drops proportionally with banned terms.
4. **Overall score**:
   - If no banned terms: **1.0** (fully compliant)
   - If violations found: `0.4 × vocab_score + 0.3 × readability + 0.3 × tone_score`
