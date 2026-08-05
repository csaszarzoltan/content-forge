# Campaign Cockpit API, v0.11

The cockpit API is a durable vertical slice for campaign creation, versioned editing, readiness, and work recovery.

## Create a campaign

`POST /api/v1/campaigns`

Body: `name`, `brief`, and non-empty `channels`.

## Create an asset

`POST /api/v1/campaigns/{campaign_id}/assets`

Body: `channel`, `title`, `content`, and `author`. Creates version 1.

## Load cockpit context

`GET /api/v1/campaigns/{campaign_id}/cockpit`

Returns the campaign, assets, readiness percentage, ready channels, and concrete blockers.

## Autosave a revision

`PUT /api/v1/assets/{asset_id}/autosave`

Body: `content`, `expected_version`, and `author`. A stale version returns HTTP 409 with `asset_version_conflict`.

## Revision history

`GET /api/v1/assets/{asset_id}/revisions`

Returns immutable revisions newest-first.

## My Work

`GET /api/v1/my-work`

Returns pending approvals and failed or retryable publications with their next action.
