# Social Media Auto-Publishing — Test & Implementation Plan

## Overview

This document defines the **pre-development test scaffolding** for ContentForge
v0.7.0 Social Media Auto-Publishing. Tests follow the existing project pattern:

- **Interface tests** — verify imports, class signatures, schema fields (PASS
  with stubs only)
- **Behavioral tests** — verify real behaviour against mocked HTTP (RED until
  implementation exists)

All HTTP calls are mocked via `httpx.MockTransport`. No real credentials.

---

## Phase 1 — Files to Create (Source)

_Before any test can pass, these stub files must exist. Create them in this order:_

### 1. `src/connectors/__init__.py`
Empty package init.

### 2. `src/connectors/errors.py`
Define: `PublishError(Exception)`, `AuthError(PublishError)`,
`RateLimitError(PublishError)`, `ConnectionError(PublishError)`.

### 3. `src/connectors/base.py`
`SocialMediaConnector(ABC)` with:
- `async publish(text, **kwargs) -> dict` (abstract)
- `async preview(text, **kwargs) -> dict` (abstract)
- `async validate_credentials() -> bool` (abstract)
- `platform_name: str` (abstract property)

### 4. `src/connectors/rate_limiter.py`
`TokenBucketRateLimiter` with:
- `__init__(capacity, refill_rate, refill_period=60.0)`
- `async acquire() -> None` (blocks until token available)
- `try_acquire() -> bool` (non-blocking)
- `remaining: int` property
- `capacity: int` property

### 5. `src/schemas/publish.py`
`PublishRequest(BaseModel)`, `PublishResponse(BaseModel)`, `PublishStatus`
literal.

### 6. `src/models/platform_token.py`
`PlatformToken(Base)` with columns: id, user_id (FK→users), platform,
access_token_encrypted, refresh_token_encrypted (nullable), expires_at
(nullable), created_at, updated_at.

### 7. `src/connectors/twitter.py`
`TwitterConnector(SocialMediaConnector)` — OAuth 1.0a signed requests to
Twitter API v2, 280-char truncation.

### 8. `src/connectors/linkedin.py`
`LinkedInConnector(SocialMediaConnector)` — OAuth 2.0 Bearer auth, UGC posts,
link shares.

### 9. `src/services/publish_service.py`
`PublishService` orchestrator — resolve connector → check rate limit →
publish → update ScheduledPost status.

### 10. `src/routers/publish.py`
`POST /api/v1/publish` router.

---

## Phase 2 — Test Files (all RED on creation)

### File A — `tests/test_connectors/test_base.py`

| # | Test | Type | What it checks |
|---|------|------|----------------|
| A1 | `test_social_media_connector_importable` | Interface | Module & class import |
| A2 | `test_social_media_connector_is_abc` | Interface | ABC inheritance |
| A3 | `test_social_media_connector_cannot_instantiate` | Interface | TypeError on direct instantiation |
| A4 | `test_social_media_connector_has_publish_abstract` | Interface | publish is abstractmethod |
| A5 | `test_social_media_connector_has_preview_abstract` | Interface | preview is abstractmethod |
| A6 | `test_social_media_connector_has_validate_credentials_abstract` | Interface | validate_credentials is abstractmethod |
| A7 | `test_social_media_connector_has_platform_name_property` | Interface | platform_name is abstract property |
| A8 | `test_concrete_subclass_instantiable` | Interface | Subclass with all methods works |

### File B — `tests/test_connectors/test_twitter.py`

| # | Test | Type | What it checks |
|---|------|------|----------------|
| B1 | `test_twitter_connector_importable` | Interface | TwitterConnector import |
| B2 | `test_twitter_connector_extends_base` | Interface | instanceof SocialMediaConnector |
| B3 | `test_twitter_connector_platform_name` | Interface | `platform_name == "twitter"` |
| B4 | `test_twitter_publish_is_async` | Interface | iscoroutinefunction |
| B5 | `test_twitter_preview_is_async` | Interface | iscoroutinefunction |
| B6 | `test_twitter_validate_credentials_is_async` | Interface | iscoroutinefunction |
| B7 | `test_publish_returns_tweet_url` | Behavioral | Success → dict with tweet_url |
| B8 | `test_publish_truncates_long_content` | Behavioral | Content > 280 chars → truncated |
| B9 | `test_publish_raises_auth_error_on_401` | Behavioral | 401 → AuthError |
| B10 | `test_publish_raises_rate_limit_on_429` | Behavioral | 429 → RateLimitError |
| B11 | `test_publish_retries_on_5xx` | Behavioral | 500 → retry up to max_retries |
| B12 | `test_publish_fails_after_max_retries` | Behavioral | Repeated 5xx → raises |
| B13 | `test_preview_returns_formatted_text` | Behavioral | preview() returns dict |
| B14 | `test_validate_credentials_true` | Behavioral | Valid token → True |
| B15 | `test_validate_credentials_false` | Behavioral | Invalid → False |

### File C — `tests/test_connectors/test_linkedin.py`

| # | Test | Type | What it checks |
|---|------|------|----------------|
| C1 | `test_linkedin_connector_importable` | Interface | LinkedInConnector import |
| C2 | `test_linkedin_connector_extends_base` | Interface | instanceof SocialMediaConnector |
| C3 | `test_linkedin_connector_platform_name` | Interface | `platform_name == "linkedin"` |
| C4-C6 | Async method checks | Interface | Same pattern as Twitter |
| C7 | `test_publish_returns_post_urn` | Behavioral | UGC post → dict with post_urn |
| C8 | `test_publish_text_only` | Behavioral | Text-only UGC post |
| C9 | `test_publish_link_share` | Behavioral | Link share post |
| C10 | `test_publish_raises_auth_error_on_401` | Behavioral | 401 → AuthError |
| C11 | `test_publish_raises_rate_limit_on_429` | Behavioral | 429 → RateLimitError |
| C12 | `test_publish_retries_on_5xx` | Behavioral | Retry on 5xx |

### File D — `tests/test_connectors/test_rate_limiter.py`

| # | Test | Type | What it checks |
|---|------|------|----------------|
| D1 | `test_rate_limiter_importable` | Interface | TokenBucketRateLimiter import |
| D2 | `test_rate_limiter_constructor` | Interface | capacity + refill_rate params |
| D3 | `test_rate_limiter_has_acquire` | Interface | acquire method exists, async |
| D4 | `test_rate_limiter_has_try_acquire` | Interface | try_acquire method exists, callable |
| D5 | `test_rate_limiter_has_remaining_property` | Interface | remaining property |
| D6 | `test_rate_limiter_has_capacity_property` | Interface | capacity property |
| D7 | `test_try_acquire_returns_true_when_available` | Behavioral | Has tokens → True |
| D8 | `test_try_acquire_returns_false_when_exhausted` | Behavioral | No tokens → False |
| D9 | `test_acquire_blocks_until_token_available` | Behavioral | Blocks then succeeds |
| D10 | `test_tokens_refill_over_time` | Behavioral | Wait → tokens restored |

### File E — `tests/test_publish_service.py`

| # | Test | Type | What it checks |
|---|------|------|----------------|
| E1 | `test_publish_service_importable` | Interface | PublishService import |
| E2 | `test_publish_service_constructor` | Interface | Accepts connectors registry |
| E3 | `test_publish_service_publish_is_async` | Interface | publish is async |
| E4 | `test_publish_happy_path` | Behavioral | Full publish flow → PublishResponse |
| E5 | `test_publish_updates_status_to_publishing` | Behavioral | Status transition |
| E6 | `test_publish_updates_status_to_published` | Behavioral | Success → published |
| E7 | `test_publish_retries_on_transient_failure` | Behavioral | 429 → retry |
| E8 | `test_publish_fails_on_auth_error` | Behavioral | 401 → failed |
| E9 | `test_publish_raises_on_unknown_platform` | Behavioral | Bad platform → ValueError |

### File F — `tests/test_publish_endpoint.py`

| # | Test | Type | What it checks |
|---|------|------|----------------|
| F1 | `test_publish_request_importable` | Interface | PublishRequest schema |
| F2 | `test_publish_request_is_pydantic` | Interface | Issubclass BaseModel |
| F3 | `test_publish_request_fields` | Interface | generation_id, platform, platform_config fields |
| F4 | `test_publish_response_importable` | Interface | PublishResponse schema |
| F5 | `test_publish_response_fields` | Interface | status, message, publish_id fields |
| F6 | `test_router_importable` | Interface | Router module |
| F7 | `test_router_has_publish_endpoint` | Interface | POST route registered |
| F8 | `test_router_registered_in_main_app` | Interface | Included in main FastAPI app |
| F9 | `test_publish_201_on_success` | Behavioral | Happy path → 201 |
| F10 | `test_publish_422_on_invalid_platform` | Behavioral | Bad platform → 422 |
| F11 | `test_publish_429_on_rate_limit` | Behavioral | Rate limited → 429 |
| F12 | `test_publish_503_on_provider_error` | Behavioral | Provider down → 503 |

### File G — `tests/test_models/test_platform_token.py`

| # | Test | Type | What it checks |
|---|------|------|----------------|
| G1 | `test_platform_token_importable` | Interface | PlatformToken import |
| G2 | `test_platform_token_tablename` | Interface | `__tablename__ == "platform_tokens"` |
| G3 | `test_platform_token_columns` | Interface | Column names |
| G4 | `test_platform_token_has_user_fk` | Interface | ForeignKey to users.id |
| G5 | `test_platform_token_encryption_field` | Interface | access_token_encrypted is String |
| G6 | `test_encrypt_decrypt_roundtrip` | Behavioral | Encrypt → decrypt → original |
| G7 | `test_create_token_in_db` | Behavioral | Create + query via session |

---

## Phase 3 — Implementation Order (to turn tests GREEN)

For each file, create the source module first (with real stubs), then the
implementation that makes the tests pass.

### Step 1 — Foundation stubs (interface tests pass immediately)

1. `src/connectors/__init__.py`
2. `src/connectors/errors.py`
3. `src/connectors/base.py` — ABC with abstract methods
4. `src/connectors/rate_limiter.py` — Basic TokenBucket
5. `src/schemas/publish.py` — Pydantic schemas
6. `src/models/platform_token.py` — ORM model
7. `tests/test_connectors/test_base.py` — Interface tests PASS
8. `tests/test_connectors/test_rate_limiter.py` — Interface tests PASS
9. `tests/test_publish_endpoint.py` — Interface tests PASS (schema imports)
10. `tests/test_models/test_platform_token.py` — Interface tests PASS

### Step 2 — Connector implementations (behavioral tests pass)

11. `src/connectors/twitter.py`
12. `src/connectors/linkedin.py`
13. `tests/test_connectors/test_twitter.py` — Behavioral tests PASS
14. `tests/test_connectors/test_linkedin.py` — Behavioral tests PASS

### Step 3 — Service layer + endpoint (all tests GREEN)

15. `src/services/publish_service.py`
16. `src/routers/publish.py`
17. `src/main.py` — register publish router
18. `src/config.py` — add social-publishing config fields
19. `tests/test_publish_service.py` — All PASS
20. `tests/test_publish_endpoint.py` — Behavioral tests PASS
21. `src/models/__init__.py` — export PlatformToken
22. `pyproject.toml` — promote httpx to core deps

---

## Wiring Changes

| File | Change |
|------|--------|
| `src/main.py` | Add `from src.routers.publish import router as publish_router` + `app.include_router(publish_router)` |
| `src/config.py` | Add `ENCRYPTION_KEY: str`, `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` |
| `src/services/scheduler.py` | Wire up PublishService in scheduled job execution |
| `src/models/__init__.py` | Export `PlatformToken` |
| `pyproject.toml` | Move `httpx>=0.27.0` from `[dev]` to core `dependencies` |
