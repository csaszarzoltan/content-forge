# Templates — Scenario Template Engine

The `brand_voice.templates` module renders scenario-specific voice prompts by combining a `VoiceProfile` with a built-in or custom scenario template.

## Built-in Scenarios

| Scenario | Tone Focus | Use Case |
|----------|------------|----------|
| `incident` | Transparent, authoritative | Incident communications, outages |
| `launch` | Excited, confident | Product launches, feature announcements |
| `support_reply` | Empathetic, patient | Customer support responses |
| `social_media` | Engaging, concise | Social media posts |
| `faq` | Direct, clear | FAQ answers, knowledge base |

## TemplateEngine

### Initialization

```python
from brand_voice.templates import TemplateEngine

# Built-in scenarios only
engine = TemplateEngine()

# With custom template directory (.md files are loaded by stem name)
engine = TemplateEngine(template_dir="/path/to/templates")
```

### Listing Scenarios

```python
scenarios = engine.list_scenarios()
# Returns: ["faq", "incident", "launch", "social_media", "support_reply"]
# Custom templates are merged with built-ins
```

### Rendering a Scenario

```python
from brand_voice.presets import PresetManager

mgr = PresetManager()
profile = mgr.get_preset("witty")

engine = TemplateEngine()
result = engine.render("incident", profile)
print(result)
```

Output includes voice rules (attributes, vocabulary, jargon level) plus scenario-specific instructions:

```
# Incident Communication — witty

**Tone:** transparent

## Voice Rules
- formality: 0.3 (casual ↔ formal)
- humor: 0.9 (serious ↔ playful)
- enthusiasm: 0.6 (reserved ↔ excited)
- Preferred words: brilliant, game-changing, game-changer, pro tip
- Avoid: boring, standard, typical
- Jargon level: light

## Scenario Instructions
Be transparent about what happened...

When communicating about an incident:
- Be transparent about what happened
- State the impact clearly
- Provide a timeline for resolution
- Outline next steps and prevention measures
```

### Rendering with Context

Pass additional template variables via the `context` parameter:

```python
result = engine.render(
    "launch",
    profile,
    context={"product_name": "Acme Cloud", "audience": "CTOs"},
)
# Context variables are appended to the output
```

### Generating System Prompts

```python
# Base system prompt (voice profile only)
prompt = engine.render_system_prompt(profile)

# System prompt with scenario-specific tone appended
prompt = engine.render_system_prompt(profile, scenario="support_reply")
# Includes an "Active Scenario" section with tone and instructions
```

### Custom Templates

Place `.md` files in the template directory. The filename stem (without `.md`) becomes the scenario name. Templates support string formatting with these variables:

- `{brand_name}` — Profile name
- `{tone}` — Inferred tone for the scenario
- `{voice_rules}` — Attribute/vocabulary rules block
- `{instructions}` — Scenario-specific instructions from the profile
