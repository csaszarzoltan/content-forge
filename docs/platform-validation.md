# Platform Validation Engine

Validate content against real social media platform constraints before publishing. The validation engine checks text length, media formats, file sizes, aspect ratios, and platform-specific rules for Twitter/X, LinkedIn, Instagram, Facebook, and TikTok.

## Supported Platforms

| Platform | Display Name | Max Characters | Image Formats | Video Formats |
|----------|-------------|---------------|---------------|---------------|
| `twitter` | Twitter/X | 280 (25,000 premium) | jpg, jpeg, png, gif, webp | mp4, mov |
| `linkedin` | LinkedIn | 3,000 | jpg, jpeg, png, gif, webp | mp4 |
| `instagram` | Instagram | 2,200 | jpg, jpeg, png | mp4, mov |
| `facebook` | Facebook | 63,206 | jpg, jpeg, png, gif, webp | mp4, mov |
| `tiktok` | TikTok | 2,200 | jpg, jpeg, png, webp | mp4, mov |

## API Reference

### List All Platforms

```
GET /api/v1/constraints
```

Returns a summary of all supported platforms with their key constraints.

**Response:**
```json
{
  "platforms": {
    "twitter": {
      "platform": "twitter",
      "display_name": "Twitter/X",
      "max_chars": 280,
      "supported_image_formats": ["jpg", "jpeg", "png", "gif", "webp"],
      "supported_video_formats": ["mp4", "mov"]
    }
  }
}
```

### Get Platform Constraints

```
GET /api/v1/constraints/{platform}
```

Returns the full constraint set for a single platform, including text, image, video, media-per-post, rate limit, and auth constraints.

**Path Parameters:**
- `platform` (string, required) — one of: `twitter`, `linkedin`, `instagram`, `facebook`, `tiktok`

**Error:** 404 if platform not found.

### Validate Content

```
POST /api/v1/validate
```

Validate content against one or more platforms. Returns per-platform results with errors, warnings, and truncation info.

**Request Body:**
```json
{
  "platforms": ["twitter", "linkedin"],
  "text": "Check out our new feature!",
  "media": [
    {
      "type": "image",
      "filename": "banner.jpg",
      "size_bytes": 1024000,
      "format": "jpg",
      "width": 1920,
      "height": 1080
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platforms` | `Platform[]` | Yes | Target platforms (`twitter`, `linkedin`, `instagram`, `facebook`, `tiktok`) |
| `text` | `string` | No | Text content to validate |
| `media` | `MediaAttachment[]` | No | Media files to validate |

**Media Attachment Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"image" \| "video" \| "gif"` | Yes | Media type |
| `filename` | `string` | Yes | File name |
| `size_bytes` | `integer` | Yes | File size in bytes |
| `format` | `string` | Yes | File extension (e.g., `jpg`, `mp4`) |
| `width` | `integer` | No | Image/video width in pixels |
| `height` | `integer` | No | Image/video height in pixels |
| `duration_seconds` | `float` | No | Video duration |

**Response:**
```json
{
  "valid": false,
  "platforms": {
    "twitter": {
      "valid": false,
      "errors": [
        {
          "field": "text",
          "rule": "max_chars",
          "message": "Text exceeds 280 character limit (312 characters)",
          "severity": "error"
        }
      ],
      "warnings": [],
      "truncated_text": "Check out our new feature! This is a lo...",
      "media_acceptable": true
    },
    "linkedin": {
      "valid": true,
      "errors": [],
      "warnings": [],
      "truncated_text": null,
      "media_acceptable": true
    }
  }
}
```

### Cross-Platform Validation

```
POST /api/v1/validate/cross-platform
```

Check content compatibility across multiple platforms in a single call. Returns which platforms are fully compatible, which need adaptation, and specific adaptation suggestions.

**Request Body:**
```json
{
  "text": "Longform content here...",
  "media": [],
  "platforms": ["twitter", "linkedin", "facebook"]
}
```

**Response:**
```json
{
  "compatible_all": false,
  "compatible_platforms": ["linkedin", "facebook"],
  "needs_adaptation": ["twitter"],
  "adaptations": {
    "twitter": [
      "Text exceeds 280 character limit — consider a thread or link post"
    ]
  }
}
```

### Constraint Preview

```
GET /api/v1/constraints/{platform}/preview?text={content}
```

Preview how content will render on a platform, including truncation points and character count breakdown.

**Query Parameters:**
- `text` (string, required) — Content to preview

## Constraint Registry Format

The constraint registry is a JSON file at `src/constraints/data/registry.json`. Each platform entry contains nested constraint objects:

```json
{
  "version": "1.0.0",
  "last_verified": "2026-08-01",
  "platforms": {
    "twitter": {
      "display_name": "Twitter/X",
      "text": {
        "max_chars": 280,
        "premium_max_chars": 25000,
        "url_consumed_chars": 23,
        "hashtags_count_toward_limit": true,
        "media_does_not_count": false,
        "truncation_cutoff": 280,
        "max_hashtags": null,
        "max_mentions": null
      },
      "image": {
        "formats": ["jpg", "jpeg", "png", "gif", "webp"],
        "max_size_bytes": 5242880,
        "max_count": 4,
        "aspect_ratios": ["1:1", "16:9", "9:16"],
        "recommended": "16:9"
      },
      "video": {
        "formats": ["mp4", "mov"],
        "codecs": ["h264", "h265"],
        "max_size_bytes": 5368709120,
        "duration_max_seconds": 140,
        "max_frame_rate": 60
      }
    }
  }
}
```

### Constraint Categories

| Category | Fields | Description |
|----------|--------|-------------|
| **Text** | `max_chars`, `premium_max_chars`, `url_consumed_chars`, `hashtags_count_toward_limit`, `truncation_cutoff` | Character limits and text rendering rules |
| **Image** | `formats`, `max_size_bytes`, `max_count`, `aspect_ratios`, `recommended` | Image upload constraints |
| **Video** | `formats`, `codecs`, `max_size_bytes`, `duration_max_seconds`, `max_frame_rate` | Video upload constraints |
| **Media per Post** | `max_images`, `max_gifs`, `max_videos`, `mutually_exclusive` | Combined media limits |
| **Rate Limits** | `posts_per_day`, `media_uploads_per_24h`, `api_calls_per_hour` | API and posting rate limits |
| **Auth** | `method`, `token_lifetime`, `requires_partner_program` | Authentication requirements |

## Examples

### Validate a Tweet

```bash
curl -X POST http://localhost:8000/api/v1/validate \
  -H 'Content-Type: application/json' \
  -d '{
    "platforms": ["twitter"],
    "text": "Excited to announce our new Platform Validation Engine! Now you can validate content against real platform constraints before publishing. #ContentForge #Validation",
    "media": []
  }'
```

### Validate with Media

```bash
curl -X POST http://localhost:8000/api/v1/validate \
  -H 'Content-Type: application/json' \
  -d '{
    "platforms": ["instagram", "facebook"],
    "text": "Summer sale starts now!",
    "media": [
      {
        "type": "image",
        "filename": "promo.jpg",
        "size_bytes": 2048000,
        "format": "jpg",
        "width": 1080,
        "height": 1080
      }
    ]
  }'
```

### Cross-Platform Check

```bash
curl -X POST http://localhost:8000/api/v1/validate/cross-platform \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "We are thrilled to announce the launch of our comprehensive Platform Validation Engine, designed to help content creators ensure their posts meet the specific requirements of each social media platform before publishing.",
    "media": [],
    "platforms": ["twitter", "linkedin", "facebook"]
  }'
```

### Python Client

```python
import httpx

resp = httpx.post("http://localhost:8000/api/v1/validate", json={
    "platforms": ["twitter", "linkedin"],
    "text": "Check out our new feature!",
    "media": [],
})

result = resp.json()
for platform, validation in result["platforms"].items():
    status = "✓" if validation["valid"] else "✗"
    print(f"  {platform}: {status}")
    for error in validation.get("errors", []):
        print(f"    - {error['message']}")
```

## Usage in Content Pipeline

The validation engine is designed to integrate into the content creation pipeline:

1. **Pre-publish validation** — Validate content before sending to platform connectors
2. **Real-time feedback** — Show validation errors to users as they compose
3. **Cross-platform adaptation** — Automatically suggest platform-specific versions
4. **Batch validation** — Validate multiple pieces of content in bulk

## Architecture

```
POST /api/v1/validate
  → ConstraintValidator.validate()
    → ConstraintRegistry.get(platform)
    → Text constraint check (char count, hashtags, URLs)
    → Media constraint check (formats, sizes, dimensions)
    → PlatformValidationResult (per platform)
  → ValidateResponse (aggregated)
```

The registry is loaded once at startup and shared across requests. The validator is stateless and thread-safe.
