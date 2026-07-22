# Scoping — Voice Profile Resolution

The `brand_voice.scoping` module manages voice profile assignment at the user and project level. Resolution order: **project > user > None**.

## VoiceScope

### Initialization

```python
from brand_voice.scoping import VoiceScope

# Config directory is created automatically
scope = VoiceScope("/path/to/config")
```

### User Voice

Set and retrieve a user's default voice:

```python
scope.set_user_voice("user-123", "brand-acme-v1")

voice_id = scope.get_user_voice("user-123")
assert voice_id == "brand-acme-v1"

# Returns None if not set
assert scope.get_user_voice("unknown-user") is None
```

### Project Voice

Project-level voices override user defaults:

```python
scope.set_project_voice("project-456", "brand-project-v2")

voice_id = scope.get_project_voice("project-456")
assert voice_id == "brand-project-v2"
```

### Resolution

Resolve the effective voice ID for a user+project combination:

```python
# Project overrides user
scope.set_user_voice("user-1", "brand-user")
scope.set_project_voice("project-1", "brand-project")
result = scope.resolve("user-1", "project-1")
assert result == "brand-project"  # Project wins

# Falls back to user when project not set
result = scope.resolve("user-1", "unconfigured-project")
assert result == "brand-user"

# Returns None when nothing is configured
result = scope.resolve("lonely-user")
assert result is None
```

### Clearing Bindings

```python
# Clear user voice
scope.clear("user", "user-1")
assert scope.get_user_voice("user-1") is None

# Clear project voice
scope.clear("project", "project-1")
assert scope.get_project_voice("project-1") is None
```

## Persistence

Voice assignments persist to the config directory as JSON files:

- `user_voices.json` — User → brand_id mapping
- `project_voices.json` — Project → brand_id mapping

Data survives VoiceScope re-initialization from the same directory.
