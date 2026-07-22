# Multi-Brand — Voice Manager

The `brand_voice.multi_brand` module manages multiple brand voice profiles with scope-based active voice tracking. All data is persisted as JSON files.

## VoiceManager

### Initialization

```python
from brand_voice.multi_brand import VoiceManager

# Directory is created automatically if it doesn't exist
mgr = VoiceManager("/path/to/profiles")
```

The manager stores:
- `_index.json` — Brand registry (id → name mapping)
- `_active.json` — Scope → brand_id assignments
- `{brand_id}.json` — Per-brand voice profile data

### Creating a Brand

```python
from brand_voice.models import VoiceProfile

profile = VoiceProfile(
    id="acme-v1",
    name="Acme Corp",
    description="Acme brand voice",
    ...
)
brand_id = mgr.create_brand("Acme Corp", profile)
# Returns: "a1b2c3d4" (8-character hex ID)
```

### Retrieving a Brand

```python
profile = mgr.get_brand("a1b2c3d4")
print(profile.name)  # "Acme Corp"
```

Raises `KeyError` if brand_id doesn't exist.

### Listing Brands

```python
brands = mgr.list_brands()
# Returns: {"a1b2c3d4": "Acme Corp", ...}
```

### Deleting a Brand

Removes the profile file and clears the brand from any active scopes.

```python
mgr.delete_brand("a1b2c3d4")
assert "a1b2c3d4" not in mgr.list_brands()
```

Raises `KeyError` if brand_id doesn't exist.

### Active Voice Per Scope

Assign a brand to a scope (default: `"global"`):

```python
mgr.set_active("a1b2c3d4", scope="global")

# Get the active profile for a scope
active = mgr.get_active(scope="global")
# Returns VoiceProfile or None if not set

# Scopes are isolated — setting one doesn't affect others
mgr.set_active("e5f6g7h8", scope="project-alpha")
global_active = mgr.get_active(scope="global")      # Still a1b2c3d4
project_active = mgr.get_active(scope="project-alpha")  # e5f6g7h8
```

### Listing Active Scopes

```python
scopes = mgr.list_scopes()
# Returns: {"global": "a1b2c3d4", "project-alpha": "e5f6g7h8"}
```

### Deletion and Scope Cleanup

When a brand is deleted, it's automatically cleared from any scopes it was active in:

```python
mgr.create_brand("Delete Me", profile)  # -> brand_id "del1"
mgr.set_active("del1", scope="global")
mgr.delete_brand("del1")
assert mgr.get_active(scope="global") is None
```
