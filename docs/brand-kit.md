# Brand Kit — Visual Identity Management

Brand Kit adds visual identity management to ContentForge — color palettes,
font pairings, logo storage, and brand guidelines generation. It complements
the text-based [Brand Voice](brand-voice-api.md) module so you can manage
both *what you say* and *how it looks* from a single platform.

---

## Quick Start

```bash
# Create a brand kit
curl -X POST http://localhost:8000/brand-kit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "description": "Primary brand identity",
    "brand_type": "business",
    "colors": {
      "primary": "#0066cc",
      "secondary": "#ffffff",
      "accent": "#ff9900",
      "background": "#f5f5f5",
      "text": "#333333"
    },
    "fonts": {
      "heading": "Manrope",
      "body": "DM Sans",
      "accent": "Inter"
    }
  }'
```

```bash
# Generate brand guidelines HTML
curl "http://localhost:8000/brand-kit/guidelines?brand_kit_id=<id>"
```

---

## How It Complements Brand Voice

| Concern | Brand Voice | Brand Kit |
|---------|-------------|-----------|
| Identity | Tone, vocabulary, scenario rules | Colors, fonts, logos |
| Output | System prompts for LLMs | HTML guidelines, static assets |
| Module | `src/brand_voice/` | `src/brand_kit/` |
| API prefix | `/brand-voice` | `/brand-kit` |
| Links to | — | `brand_voice_id` FK (optional) |

A brand kit can reference a brand voice profile via the optional
`brand_voice_id` field, enabling the guidelines generator to combine visual
identity and writing voice in a single document.

---

## Data Model

### ColorPalette

Five hex colors with computed RGB/HSL conversions.

| Field | Default | Description |
|-------|---------|-------------|
| `primary` | `#000000` | Primary brand color |
| `secondary` | `#ffffff` | Secondary color |
| `accent` | `#0066cc` | Accent / highlight |
| `background` | `#ffffff` | Background color |
| `text` | `#333333` | Text color |

Hex values are validated with pattern `^#?[0-9A-Fa-f]{6}$`. The response
model exposes computed properties:

```python
kit.colors.primary_rgb   # (0, 102, 204)
kit.colors.primary_hsl   # (210, 100, 40)
```

### FontSet

| Field | Type | Default |
|-------|------|---------|
| `heading` | str | `"Arial"` |
| `body` | str | `"Arial"` |
| `accent` | str | `"Arial"` |
| `heading_file` | str \| None | None |
| `body_file` | str \| None | None |
| `accent_file` | str \| None | None |

Font names are display labels; `*_file` paths point to uploaded custom font
files.

### LogoSet

| Field | Type | Description |
|-------|------|-------------|
| `primary` | str \| None | Primary logo file path |
| `secondary` | str \| None | Secondary logo path |
| `icon` | str \| None | Favicon / icon path |
| `watermark` | str \| None | Watermark path |
| `primary_format` | str \| None | e.g. `"png"`, `"svg"` |
| `primary_size` | int \| None | File size in bytes |

---

## API Endpoints

All endpoints are under the `/brand-kit` prefix.

### Create Brand Kit

**`POST /brand-kit`** → `201 Created`

```bash
curl -X POST http://localhost:8000/brand-kit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Startup Brand",
    "description": "Our visual identity",
    "brand_type": "business",
    "colors": {
      "primary": "#e63946",
      "secondary": "#f1faee",
      "accent": "#457b9d",
      "background": "#ffffff",
      "text": "#1d3557"
    },
    "fonts": {
      "heading": "Manrope",
      "body": "DM Sans",
      "accent": "Inter"
    }
  }'
```

**Response:**

```json
{
  "id": "a1b2c3d4-...",
  "name": "Startup Brand",
  "description": "Our visual identity",
  "brand_type": "business",
  "user_id": null,
  "brand_voice_id": null,
  "colors": {
    "primary": "#e63946",
    "secondary": "#f1faee",
    "accent": "#457b9d",
    "background": "#ffffff",
    "text": "#1d3557"
  },
  "fonts": {
    "heading": "Manrope",
    "body": "DM Sans",
    "accent": "Inter",
    "heading_file": null,
    "body_file": null,
    "accent_file": null
  },
  "logos": {
    "primary": null,
    "secondary": null,
    "icon": null,
    "watermark": null,
    "primary_format": null,
    "primary_size": null
  },
  "version": 1,
  "created_at": "2026-08-06T14:30:00+00:00",
  "updated_at": "2026-08-06T14:30:00+00:00"
}
```

### List Brand Kits

**`GET /brand-kit?limit=20&offset=0`** → `200 OK`

```bash
curl "http://localhost:8000/brand-kit?limit=10"
```

```json
{
  "items": [ ... ],
  "total": 3,
  "limit": 10,
  "offset": 0
}
```

Soft-deleted kits are excluded from results.

### Get Brand Kit by ID

**`GET /brand-kit/{brand_kit_id}`** → `200 OK`

```bash
curl http://localhost:8000/brand-kit/a1b2c3d4-...
```

Returns `404` if the kit is not found or has been soft-deleted.

### Generate Brand Guidelines

**`GET /brand-kit/guidelines?brand_kit_id={id}`** → `200 OK` (HTML)

```bash
curl "http://localhost:8000/brand-kit/guidelines?brand_kit_id=a1b2c3d4-..."
```

Returns a self-contained HTML document with:

- **Color palette** — visual swatches with hex values
- **Typography** — heading, body, and accent font names
- **Logos** — file paths for uploaded assets
- **Brand voice** — linked voice profile identity (if `brand_voice_id` is set)

The HTML uses inline CSS and is ready for browser rendering or PDF conversion.

### Upload File

**`POST /brand-kit/upload?brand_kit_id={id}&file_type=font|logo`** → `201 Created`

Uploads a font or logo file for the specified brand kit.

**File type constraints:**

| `file_type` | Allowed extensions |
|-------------|--------------------|
| `font` | `.ttf`, `.otf`, `.woff`, `.woff2` |
| `logo` | `.png`, `.jpg`, `.jpeg`, `.svg`, `.webp` |

Files are stored at `<upload_root>/brand_kit/<kit_id>/fonts/` or `logos/`.
Filenames are sanitized (path traversal rejected, directory components stripped).

---

## File Upload Constraints

| Constraint | Value |
|------------|-------|
| Font types | TTF, OTF, WOFF, WOFF2 |
| Logo types | PNG, JPG, JPEG, SVG, WebP |
| Path traversal | Rejected (`..` and `\` in filenames) |
| Filename sanitization | Directory components stripped |
| Storage | Local filesystem under `UPLOAD_ROOT` |

---

## Multi-Brand Support

Users can create multiple brand kits (e.g., personal + business, or per-client
identities). Each kit is an independent record with its own colors, fonts, logos,
and optional brand voice link.

```python
# Create two kits
personal = httpx.post("/brand-kit", json={"name": "Personal Brand", "brand_type": "personal"})
business = httpx.post("/brand-kit", json={"name": "Work Brand", "brand_type": "business"})

# List all kits
kits = httpx.get("/brand-kit").json()
print(kits["total"])  # 2
```

---

## Linking to Brand Voice

Set the optional `brand_voice_id` when creating or updating a brand kit to
connect it to a brand voice profile. The guidelines generator will include
the voice identity in the output document.

```bash
curl -X POST http://localhost:8000/brand-kit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Full Brand",
    "brand_voice_id": "voice-abc-123",
    "colors": { "primary": "#0066cc" }
  }'
```

---

## ORM Model

The `brand_kits` table (SQLAlchemy):

| Column | Type | Notes |
|--------|------|-------|
| `id` | String(36) | UUID primary key |
| `name` | String(255) | Required |
| `description` | Text | Default `""` |
| `brand_type` | String(50) | `"personal"` or `"business"` |
| `user_id` | String(36) | Optional FK |
| `brand_voice_id` | String(36) | Optional FK to `brand_voices.id` |
| `colors` | JSON | `ColorPalette` dict |
| `fonts` | JSON | `FontSet` dict |
| `logos` | JSON | `LogoSet` dict |
| `guidelines_html` | Text | Cached generated HTML |
| `version` | Integer | Auto-incremented on update |
| `deleted_at` | DateTime | Soft-delete timestamp |
| `created_at` | DateTime | Auto-set on insert |
| `updated_at` | DateTime | Auto-set on insert/update |

Methods: `soft_delete()`, `increment_version()`.

---

## Error Codes

| Status | Meaning |
|--------|---------|
| `201` | Brand kit created / file uploaded |
| `200` | Successful retrieval or list |
| `404` | Brand kit not found (or soft-deleted) |
| `422` | Validation error (invalid hex color, missing name, etc.) |
