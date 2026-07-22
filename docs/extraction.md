# Extraction — Voice Profile Inference

The `brand_voice.extraction` module analyzes existing text samples and automatically generates a `VoiceProfile` by inferring attributes, vocabulary, and tone style.

## VoiceExtractor

### Initialization

```python
from brand_voice.extraction import VoiceExtractor

# Default: warns below 500 words, enforces 5-word minimum
extractor = VoiceExtractor(min_words=500)

# For testing with short samples
extractor = VoiceExtractor(min_words=50)
```

### Extracting a Profile

```python
samples = [
    "We are excited to announce our new platform. "
    "This solution helps teams collaborate more effectively.",
    "Our mission is to make work easier for everyone involved.",
]

profile = extractor.extract(samples)
print(profile.name)           # "Extracted Voice"
print(profile.id)             # "extracted-a1b2c3"
print(profile.description)    # "Automatically extracted voice profile from 2 samples"

# Inferred attributes
for attr in profile.attributes:
    print(f"{attr.name}: {attr.value:.2f} ({attr.min_label} ↔ {attr.max_label})")
    # formality: 0.50 (casual ↔ formal)
    # humor: 0.00 (serious ↔ playful)
    # enthusiasm: 0.10 (reserved ↔ excited)

# Inferred vocabulary
print(profile.vocabulary.preferred)   # Top 10 frequent words (3+ chars, non-stop words)
print(profile.vocabulary.jargon_level)  # Based on avg word length
```

### Extracted Profile Structure

| Component | How It's Inferred |
|-----------|------------------|
| **Formality** | Ratio of formal markers (`therefore`, `consequently`) to informal markers (`gonna`, `wanna`) |
| **Humor** | Frequency of humor markers (`haha`, `joke`, `witty`, `funny`) normalized to word count |
| **Enthusiasm** | Exclamation count + positive sentiment word frequency |
| **Vocabulary** | Top 10 most frequent meaningful words (3+ chars, not stop words) |
| **Jargon level** | Average word length: `≤5.0` → none, `≤6.5` → light, `>6.5` → heavy |
| **Formatting** | Defaults (sentence case, dash bullets, inline citations) |

### Analyzing Samples

Get raw analysis metrics without generating a profile:

```python
analysis = extractor.analyze_samples(samples)
# {
#     "total_words": 35,
#     "total_samples": 2,
#     "unique_words": 28,
#     "type_token_ratio": 0.8,
#     "avg_sentence_length": 12.5,
#     "top_words": [("platform", 2), ("team", 1), ...]
# }
```

### Error Handling

```python
# Raises ValueError for insufficient text
try:
    extractor.extract(["Too short"])
except ValueError as e:
    print(e)  # "Insufficient words: 2 < 5 minimum..."
```
