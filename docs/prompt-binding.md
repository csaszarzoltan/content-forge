# Prompt Binding — Content-Type Prompt Generation

The `brand_voice.prompt_binding` module binds voice profiles to reusable prompt templates for content generation. It supports multiple content types with type-specific writing guidelines.

## PromptBinder

### Initialization

```python
from brand_voice.templates import TemplateEngine
from brand_voice.prompt_binding import PromptBinder

engine = TemplateEngine()
binder = PromptBinder(engine)

# Optionally provide a PresetManager for preset lookups
from brand_voice.presets import PresetManager
binder = PromptBinder(engine, preset_manager=PresetManager())
```

### Content Types

| Content Type | Purpose |
|-------------|---------|
| `email` | Transactional and marketing emails |
| `landing_page` | Landing page copy |
| `social_post` | Social media posts |
| `faq` | FAQ answers |
| `support_reply` | Customer support replies |

```python
types = binder.list_content_types()
# Returns: ["email", "faq", "landing_page", "social_post", "support_reply"]
```

### Creating Content Prompts

```python
from brand_voice.presets import PresetManager

mgr = PresetManager()
profile = mgr.get_preset("formal")

binder = PromptBinder(TemplateEngine())
prompt = binder.create_prompt(
    content_type="email",
    profile=profile,
    topic="New Feature Launch",
    audience="Enterprise customers",
    length="short",
)
print(prompt)
```

Output:

```
# Content Creation: Email
## Topic: New Feature Launch

## Brand Voice Rules
- formality: 0.9 (casual ↔ formal)
- humor: 0.1 (serious ↔ playful)
- enthusiasm: 0.3 (reserved ↔ excited)
- Preferred words: therefore, consequently, furthermore, accordingly
- Avoid: gonna, wanna, kinda, stuff
- Jargon level: heavy

## Email Guidelines
When writing emails:
- Use a clear, descriptive subject line
- Open with a personalized greeting
- Keep paragraphs short (2-3 sentences)
- End with a clear call to action

- audience: Enterprise customers
- length: short
```

### Generating System Prompts

```python
# System prompt with brand voice only
system_prompt = binder.create_system_prompt(profile)

# With content-type-specific constraints
system_prompt = binder.create_system_prompt(
    profile,
    content_type="email",
)
# Output includes both brand voice rules and email writing guidelines
```
