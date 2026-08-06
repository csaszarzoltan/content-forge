# Social Media Auto-Publishing

Publish generated content directly to Twitter/X and LinkedIn through the ContentForge API. The publishing system uses a pluggable connector architecture with per-platform rate limiting, automatic retry, and Fernet-encrypted credential storage.

---

## Overview

The social media publishing feature lets you send generated content to social platforms in a single API call. Content flows through these stages:

1. **Submit** — Send your content via `POST /api/v1/publish`
2. **Rate limit** — The token bucket checks per-platform limits before publishing
3. **Publish** — The platform connector posts the content via the platform's API
4. **Track** — Query publish status with `GET /api/v1/publish/{publish_id}`

The system handles character limits (280 for Twitter/X, 3000 for LinkedIn), authentication errors (no retry), rate limit errors (retried up to 3 times), and server errors (retried up to 3 times). When no real connector credentials are configured (dev/test), the endpoint returns a synthetic success response so you can develop and test the integration without live credentials.

---

## Architecture

### SocialMediaConnector (ABC)

```python
from abc import ABC, abstractmethod
from typing import Any

class SocialMediaConnector(ABC):
    """Abstract base for publishing content to a social media platform."""

    @abstractmethod
    async def publish(self, text: str, **kwargs: Any) -> dict:
        """Publish content to the platform."""

    @abstractmethod
    async def preview(self, text: str, **kwargs: Any) -> dict:
        """Preview how the content will look on the platform."""

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Validate that the current credentials are valid."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name identifier (e.g. 'twitter', 'linkedin')."""
```

Every connector implements the same three methods plus the `platform_name` property. The `publish` method accepts the content text and platform-specific keyword arguments, returning a dict with the platform's post ID and URL. The `preview` method returns metadata (character count, truncation info) without posting. The `validate_credentials` method tests connectivity by calling a lightweight platform API endpoint.

### Available Connectors

#### Twitter (X) API v2

`TwitterConnector` in `src/connectors/twitter.py`

- **Auth:** OAuth 1.0a User Context (signed headers with HMAC-SHA1)
- **Max characters:** 280 (text longer than 280 is truncated)
- **API base:** `https://api.twitter.com/2` (external Twitter/X API)
- **Publish endpoint:** `POST https://api.twitter.com/2/tweets` (external Twitter/X API endpoint — the connector calls this from `src/connectors/twitter.py:118`; it is NOT a ContentForge local endpoint)
- **Credential test:** `GET /2/users/me`
- **Requires:** API key, API secret, access token, access token secret

The connector builds OAuth 1.0a signed `Authorization` headers for every request. On a `201 Created` response, it returns the tweet ID and a `tweet_url`. Authentication failures (401/403) raise `AuthError`, rate limits (429) raise `RateLimitError`, and server errors (5xx) are retried.

```python
# Preview a tweet before posting
connector = TwitterConnector(
    api_key="...", api_secret="...",
    access_token="...", access_token_secret="...",
)
preview = await connector.preview("Your content text here")
print(preview)
# {"char_count": 21, "truncated": "Your content text here", "will_be_truncated": False}
```

#### LinkedIn API v2

`LinkedInConnector` in `src/connectors/linkedin.py`

- **Auth:** OAuth 2.0 Bearer token
- **Max characters:** 3000
- **API base:** `https://api.linkedin.com`
- **Publish endpoint:** `POST /rest/posts`
- **Credential test:** `GET /v2/userinfo`
- **Requires:** Client ID, client secret, access token

The connector supports text-only posts and link/article shares. Pass `article_url` and `article_title` in `platform_config` (see API examples below) to create a link share post. Authentication failures (401/403) raise `AuthError`, rate limits (429) raise `RateLimitError`, and server errors (5xx) are retried.

```python
# Preview a LinkedIn post
connector = LinkedInConnector(
    client_id="...", client_secret="...", access_token="..."
)
preview = await connector.preview("Your content text here")
print(preview)
# {"char_count": 21, "within_limit": True, "format": "text"}
```

### How to Add a New Connector

1. Create a new module in `src/connectors/` (e.g. `instagram.py`)
2. Subclass `SocialMediaConnector` and implement all abstract methods:

```python
from src.connectors.base import SocialMediaConnector
from src.connectors.errors import AuthError, PublishError, RateLimitError

class InstagramConnector(SocialMediaConnector):
    @property
    def platform_name(self) -> str:
        return "instagram"

    async def publish(self, text: str, **kwargs: Any) -> dict:
        # Implement platform API call here
        ...

    async def preview(self, text: str, **kwargs: Any) -> dict:
        # Return char count, format validation, etc.
        ...

    async def validate_credentials(self) -> bool:
        # Test connectivity with a lightweight API call
        ...
```

3. Add the platform name to `VALID_PLATFORMS` in `src/routers/publish.py`
4. Add the connector class to the `PublishService` connector dict during app initialisation
5. Add the corresponding environment variables to `Settings` in `src/config.py`
6. Register the platform in the `Platform` literal type in `src/schemas/publish.py`

### PublishService Orchestrator

`PublishService` in `src/services/publish_service.py` coordinates the full publish lifecycle:

1. Resolves the platform name to a `SocialMediaConnector` instance
2. Creates or reuses a `TokenBucketRateLimiter` for the platform
3. Acquires a rate limit token (non-blocking `try_acquire`)
4. Calls the connector's `publish` method
5. Stores the result in an in-memory dictionary with a `pub_` prefixed ID
6. On failure: `AuthError` surfaces immediately (fatal), `RateLimitError` triggers up to 3 retries

### Error Handling

```python
from src.connectors.errors import (
    ConnectorError,       # Base for all connector errors
    PublishError,         # Publish operation failed (5xx or unrecoverable)
    AuthError,            # Authentication failure (401/403) — no retry
    RateLimitError,       # Rate limit exceeded (429) — retried up to 3 times
)
```

| Error | HTTP Status | Retries | Cause |
|-------|-------------|---------|-------|
| `AuthError` | 401/403 | No | Invalid or expired credentials |
| `RateLimitError` | 429 | Up to 3 | Too many requests, try later |
| `PublishError` | 500/5xx | Up to 3 | Server error or network failure |

**Status transitions:**

```
submitted → rate_limit_check → connector.publish() → published
                                  ↓ (on error)
                              retry (up to 3×)
                                  ↓ (exhausted)
                              failed
```

---

## Configuration

| Env Var | Required | Default | Description |
|---------|----------|---------|-------------|
| `ENCRYPTION_KEY` | Yes (prod) | `""` | Fernet key for token encryption (32 url-safe base64 bytes) |
| `TWITTER_API_KEY` | No | `""` | Twitter/X API v2 key |
| `TWITTER_API_SECRET` | No | `""` | Twitter/X API v2 secret |
| `TWITTER_ACCESS_TOKEN` | No | `""` | OAuth 1.0a user access token |
| `TWITTER_ACCESS_TOKEN_SECRET` | No | `""` | OAuth 1.0a user access token secret |
| `LINKEDIN_CLIENT_ID` | No | `""` | LinkedIn OAuth 2.0 client ID |
| `LINKEDIN_CLIENT_SECRET` | No | `""` | LinkedIn OAuth 2.0 client secret |

**Generating an `ENCRYPTION_KEY`:**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

The `ENCRYPTION_KEY` is required in production for the `PlatformToken` model (encrypted credential storage per user). In development it falls back to a module-level auto-generated key. All other variables are optional — when omitted the connector is not registered in the `PublishService`, and the endpoint returns a synthetic success for testing.

Tokens are encrypted at rest using the `cryptography.fernet.Fernet` symmetric cipher before being stored in the `platform_tokens` database table.

---

## API Endpoints

### `POST /api/v1/publish`

Publish content to a social media platform.

**Request body:**

```json
{
  "generation_id": "gen_a1b2c3d4e5f6",
  "platform": "twitter",
  "text": "Check out our latest blog post on microservices vs monoliths! https://blog.example.com/microservices-vs-monoliths",
  "platform_config": {}
}
```

**Request fields:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `generation_id` | Yes | string | ID of the generated content to publish |
| `platform` | Yes | string | Target platform — `"twitter"` or `"linkedin"` |
| `text` | No | string | Content text to publish (default: `""`) |
| `platform_config` | No | object | Platform-specific configuration (see below) |

**Platform-specific `platform_config` options:**

| Platform | Key | Type | Description |
|----------|-----|------|-------------|
| `linkedin` | `article_url` | string | URL of the article to share (creates a link share post) |
| `linkedin` | `article_title` | string | Title for the linked article |
| `linkedin` | `author` | string | URN of the author (default: `urn:li:person:current_user`) |

**Response** (201 Created):

```json
{
  "publish_id": "pub_a1b2c3d4e5f6",
  "generation_id": "gen_a1b2c3d4e5f6",
  "platform": "twitter",
  "status": "published",
  "platform_url": "https://twitter.com/user/status/1234567890",
  "created_at": "2026-07-26T12:00:00+00:00"
}
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `publish_id` | string | Unique publish operation ID (`pub_` prefix + 12 hex chars) |
| `generation_id` | string | ID of the published content |
| `platform` | string | Platform published to |
| `status` | string | Publish status (`"published"`, `"failed"`) |
| `platform_url` | string \| null | URL of the published post (null for synthetic/dev responses) |
| `created_at` | datetime | When the publish was created |

**Errors:**

| Status | Condition |
|--------|-----------|
| `422` | Invalid platform (not `"twitter"` or `"linkedin"`) |
| `422` | Unknown platform (connector not configured) |
| `500` | Auth failure or rate limit exhausted |

---

### `GET /api/v1/publish/{publish_id}`

Get the status of a publish operation.

```bash
curl http://localhost:8000/api/v1/publish/pub_a1b2c3d4e5f6
```

**Response** (200 OK):

```json
{
  "publish_id": "pub_a1b2c3d4e5f6",
  "status": "published",
  "retry_count": 0,
  "error_message": null
}
```

**Status values:**

| Status | Meaning |
|--------|---------|
| `published` | Content published successfully |
| `failed` | Publishing failed after retries |
| `not_found` | No publish operation with this ID |

---

### `GET /api/v1/publish/status`

List publish operations, optionally filtered by status.

```bash
# List all publishes
curl http://localhost:8000/api/v1/publish/status

# Filter by status
curl "http://localhost:8000/api/v1/publish/status?status_filter=published"
```

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `status_filter` | string \| null | `null` | Filter by status value |

**Response** (200 OK):

```json
{
  "statuses": [],
  "filter": null
}
```

> **Note:** The listing endpoint is an in-memory stub in the current release — it always returns an empty `statuses` array. Persistent tracking with database-backed history is planned for a future release.

---

## Rate Limits

The rate limiter uses the **token bucket algorithm** — each platform gets its own bucket. A bucket starts full (`capacity` tokens) and refills at `refill_rate` tokens per second. Acquiring a token consumes one from the bucket; if no tokens remain, the request is blocked.

### Default limits per platform

| Platform | Burst Capacity | Refill Rate | Effective Window |
|----------|----------------|-------------|------------------|
| Twitter/X | 300 | 20/sec | ~300 per 15 seconds burst |
| LinkedIn | 300 | 20/sec | ~300 per 15 seconds burst |

The same token bucket defaults are applied to every platform. Adjust per-platform limits by customising the `TokenBucketRateLimiter` parameters in `PublishService`:

```python
# In src/services/publish_service.py
self.rate_limiters[platform] = TokenBucketRateLimiter(
    capacity=your_capacity,
    refill_rate=your_refill_rate,
    name=platform,
)
```

### TokenBucketRateLimiter API

```python
limiter = TokenBucketRateLimiter(capacity=300, refill_rate=20.0, name="twitter")

# Non-blocking check — returns True/False immediately
if limiter.try_acquire():
    print("Token acquired, proceed with publish")

# Block until token available — returns wait time in seconds
wait_time = await limiter.acquire()
print(f"Waited {wait_time:.2f}s for a token")

# Inspect current state
print(f"Capacity: {limiter.capacity}")   # Maximum tokens
print(f"Remaining: {limiter.remaining}")  # Current tokens (refills first)
```

---

## Examples

### Publish a tweet (curl)

```bash
curl -X POST http://localhost:8000/api/v1/publish \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-access-token>" \
  -d '{
    "generation_id": "gen_a1b2c3d4e5f6",
    "platform": "twitter",
    "text": "Just published a deep dive into microservices vs monoliths. Check it out!"
  }'
```

### Publish a LinkedIn article share (curl)

```bash
curl -X POST http://localhost:8000/api/v1/publish \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-access-token>" \
  -d '{
    "generation_id": "gen_a1b2c3d4e5f6",
    "platform": "linkedin",
    "text": "Our latest engineering blog explores the trade-offs between microservices and monolithic architectures.",
    "platform_config": {
      "article_url": "https://blog.example.com/microservices-vs-monoliths",
      "article_title": "Microservices vs Monoliths: An Engineering Perspective"
    }
  }'
```

### Publish and check status (Python)

```python
import httpx

base_url = "http://localhost:8000"
headers = {"Authorization": "Bearer <your-access-token>"}

# Step 1: Publish
resp = httpx.post(
    f"{base_url}/api/v1/publish",
    headers=headers,
    json={
        "generation_id": "gen_a1b2c3d4e5f6",
        "platform": "twitter",
        "text": "Exploring the microservices vs monoliths debate on our blog!",
    },
)
result = resp.json()
publish_id = result["publish_id"]
print(f"Published: {result['publish_id']} → {result.get('platform_url')}")

# Step 2: Check status
status = httpx.get(
    f"{base_url}/api/v1/publish/{publish_id}",
    headers=headers,
).json()
print(f"Status: {status['status']}, retries: {status['retry_count']}")
```

---

## Production Readiness

The current implementation is **functional but not production-hardened** for high-volume social media publishing. The following are recommended before using in production:

1. **Real OAuth 2.0 flow** — Implement the full OAuth authorization code grant for each platform instead of hard-coding tokens. The `PlatformToken` model and `token_encryption` module provide the storage layer; wire up redirect endpoints (`/auth/{platform}/callback`) to complete the flow.

2. **Token refresh** — LinkedIn access tokens expire after 90 days. Add automatic token refresh logic using the `refresh_token` field in the `PlatformToken` model.

3. **Webhook callbacks** — Register webhook URLs with each platform to receive real-time publish status updates (e.g. tweet deletion, engagement metrics). The current `PublishService` stores results in-memory only.

4. **Persistent status store** — The publish status dictionary (`PublishService._publishes`) is in-memory and lost on restart. Back it with the database (`platform_tokens` or a new `publishes` table).

5. **Per-user rate limiting** — The current token bucket is per-platform (global), not per-user. For multi-tenant deployments, scope rate limiters by `(platform, user_id)`.

6. **Idempotency** — Add an `idempotency_key` to `POST /api/v1/publish` to prevent duplicate publishes on network retry.

7. **Media uploads** — Neither connector currently supports image or video attachments. Extend `publish()` to accept media file references and use the platform's media upload API.

---

## Related

- [API Overview](api-overview.md) — Complete REST endpoint reference
- [Content Generation](content-generation.md) — Generate the content to publish
- [Scheduling](scheduling.md) — Schedule content for future publication
- [Deployment](deployment.md) — Environment variables and configuration
