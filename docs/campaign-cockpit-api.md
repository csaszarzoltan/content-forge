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

## Request revision-bound approval

`POST /api/v1/assets/{asset_id}/approval`

Binds `requester`, `risk`, and `findings` to the current immutable asset version.

## Decide approval

`POST /api/v1/approvals/{request_id}/decision`

Accepts `reviewer`, `decision`, and mandatory `reason`. A changed asset returns HTTP 409 `approval_revision_stale`.

## Asset audit

`GET /api/v1/assets/{asset_id}/audit`

Returns approval requests and decisions in chronological order.

## Complete workspace overview

`GET /api/v1/workspace-overview`

Returns campaigns, assets, approvals, publish batches, delivery attempts, localization jobs, locale variants, brand profiles, voice rules, provenance records, and actionable summary counts for the routed React workspaces.
