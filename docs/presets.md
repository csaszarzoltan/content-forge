# Presets — Voice Profile Preset Manager

The `brand_voice.presets` module provides a gallery of built-in voice profiles plus CRUD operations for custom presets. Custom presets are persisted as JSON files.

## Built-in Presets

The library ships with 5 ready-to-use presets:

| Preset | Formality | Humor | Enthusiasm | Best For |
|--------|-----------|-------|------------|----------|
| **formal** | 0.9 | 0.1 | 0.3 | Corporate communications, executive updates |
| **casual** | 0.2 | 0.6 | 0.7 | Community posts, team updates |
| **witty** | 0.3 | 0.9 | 0.6 | Social media, product launches |
| **empathetic** | 0.4 | 0.2 | 0.5 | Support replies, incident comms |
| **technical** | 0.6 | 0.1 | 0.2 | Developer docs, API changelogs |

## PresetManager

### Initialization

```python
from brand_voice.presets import PresetManager

# Without custom directory (read-only access to built-ins)
mgr = PresetManager()

# With custom directory (enables save/delete custom presets)
mgr = PresetManager(custom_dir="/path/to/presets")
```

The custom directory is created automatically if it doesn't exist.

### Listing Presets

```python
# List all built-in preset names
builtins = mgr.list_builtins()
# Returns: ["casual", "empathetic", "formal", "technical", "witty"]

# List custom (user-saved) preset names
customs = mgr.list_custom()
# Returns: ["my-brand", ...] or [] if none saved
```

### Getting a Preset

```python
# Get by name (searches built-ins first, then custom)
profile = mgr.get_preset("formal")
print(profile.name)         # "formal"
print(profile.to_system_prompt())  # Full system prompt block
```

Raises `KeyError` if the name isn't found.

### Saving Custom Presets

```python
from brand_voice.models import VoiceProfile

mgr = PresetManager(custom_dir="/tmp/my_presets")

# Save a custom profile
profile = VoiceProfile(  # ... create from scratch or modify existing
    id="my-brand-v1",
    name="My Brand",
    description="My custom brand voice",
    ...
)
mgr.save_custom(profile, "my-brand")

# List it back
assert "my-brand" in mgr.list_custom()
```

Raises `ValueError` if no `custom_dir` was configured.

### Deleting Custom Presets

```python
mgr.delete_custom("my-brand")
assert "my-brand" not in mgr.list_custom()
```

Raises `KeyError` if the name isn't found in custom presets.

### Remixing a Preset

Create a new profile by overriding fields of an existing preset. The original is not mutated.

```python
remixed = mgr.remix("formal", {
    "name": "Formal Lite",
    "description": "A less formal formal preset",
})
print(remixed.name)         # "Formal Lite"
print(remixed.attributes)   # Same attributes as "formal"
```

### Custom Preset Persistence

Custom presets survive re-initialization:

```python
mgr1 = PresetManager(custom_dir="/tmp/presets")
mgr1.save_custom(profile, "persistent-brand")

mgr2 = PresetManager(custom_dir="/tmp/presets")
assert "persistent-brand" in mgr2.list_custom()
```
