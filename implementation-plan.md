# Implementation Plan

## Executive Summary

The previous development pass established a real Family Creator backend and a polished setup/Home/create/review shell, but its own `development-report.md` identifies the largest remaining product gaps: browser identity is still represented by trusted-looking client headers, invitation/member management lacks a complete UI, the contribution journey has no real preview-first editor, and adult publishing lacks confirmation/result/recovery screens. This plan selects three coherent completion features rather than expanding breadth:

1. **Trusted Family Access and Invitations**: authenticate family API actors from the existing JWT system, complete invitation acceptance and member administration, and eliminate browser-controlled actor identity in production paths.
2. **Preview-first Editor and Review Handoff**: finish contributor editing, conflict-safe autosave, offline draft preservation, exact-version submission, and adult comparison/decision UI.
3. **Safe Publish Confirmation and Recovery**: finish adult confirmation, schedule choice, per-channel progress, selective retry, connection recovery, and unknown-state reconciliation.

These features close the exact PARTIAL/BLOCKED items recorded after the first Family Creator implementation and deliver the sellable promise identified by research: family members can contribute simply while adults retain trustworthy control over what becomes public. No new AI provider, network, billing system, media vault, or native app is included.

## Current-State Validation

- The input is a complete 295-file project containing `research-findings.md`, the previous `implementation-plan.md`, and `development-report.md`.
- Implemented family foundations are real: `src/family/store.py` persists workspaces, memberships, invitations, projects, assets, revisions, reviews, ideas, publish batches, deliveries, idempotency records, and audit events. `src/routers/family.py` exposes additive family endpoints. `frontend/src/family.tsx` implements Setup, Home, Journey, Idea, and Review surfaces.
- The first development report truthfully marks US-002, US-004, US-005, US-008, and US-009 as partial, notes no invitation acceptance UI, contributor editor, publish confirmation/result screen, or completed Playwright verification, and warns that production identity currently depends on actor headers.
- Existing authentication already supports JWT register/login/refresh/current user in `src/routers/auth.py`, `src/dependencies.py`, and `src/services/auth_service.py`. The correct next step is to integrate family membership with `get_current_user`, not to add another identity system.
- Existing operations already model immutable revisions, approval supersession, audit events, idempotency, and per-channel deliveries. The plan extends those contracts without replacing the professional/expert workflows.
- The current family UI uses the existing React 19/Vite/CSS stack and established design tokens. A frontend rewrite would add risk without user value.

## Research Priorities

1. Preserve adult control and child-appropriate bounded participation through server-enforced identity and roles.
2. Make review understandable beside the content, with exact revision, author, preview, and measurable change requests.
3. Make public outcomes trustworthy through confirmation, idempotency, per-channel status, selective retry, and reconciliation.
4. Reduce family cognitive load with progressive disclosure and plain-language recovery.
5. Complete the real user journey before adding monetization dashboards, networks, or AI breadth.

## Selected Scope for This Pass

### Feature A: Trusted Family Access and Invitations

Stories US-010 to US-012. Replace actor headers with the existing JWT dependency on every family route; add safe invitation preview, acceptance, revocation, member listing, role update, removal, and last-owner invariant; build Invitation and Members screens.

### Feature B: Preview-first Editor and Review Handoff

Stories US-013 to US-015. Add a route-addressable editor with 800 ms autosave, optimistic concurrency, IndexedDB draft recovery, desktop split preview/mobile Edit-Preview tabs, revision history, exact-version submission, improved review detail, text diff, stale-state handling, and decision recovery.

### Feature C: Safe Publish Confirmation and Recovery

Stories US-016 to US-018. Add connection-aware confirmation, exact approved revision summary, local/UTC scheduling display, idempotent batch creation, progress polling, per-channel result, selective retry, reconnect deep links, and unknown-state reconciliation.

## Deferred Scope and Rationale

1. Billing, usage meters, and spend caps: still require a reliable usage ledger and are a monetization phase after the core journey is complete.
2. Weekly value report: requires trustworthy production event data.
3. Full image/media vault: ownership metadata, malware scanning, deletion SLA, and retention controls exceed this completion pass.
4. Offline binary image queue: text draft/idea recovery is included; binary background sync remains browser/storage sensitive.
5. Independent younger-child accounts and age assurance: require legal/safeguarding design.
6. New social networks: reliability for current destinations precedes channel breadth.
7. Rich inline comments and collaborative cursors: exact revision diff and decision reason solve the selected review job with less complexity.
8. Transactional invitation email: this pass creates copyable/revocable links; provider selection, consent, and deliverability belong to an infrastructure phase.
9. Billing/admin redesign and advanced analytics: unrelated to completing contribution-to-publication.

## User Stories (BDD)

```json
[
  {
    "id": "US-010",
    "epic": "Trusted Family Access and Invitations",
    "role": "parent owner",
    "action": "invite a family member through a clear, revocable link",
    "benefit": "the right person joins with the intended permissions",
    "story": "As a parent owner, I want to invite a family member through a clear, revocable link, so that the right person joins with the intended permissions.",
    "gui_flow": [
      "Owner opens Workspace menu -> sees Members and invitations with role summaries",
      "Owner selects Invite member -> modal asks email and role and shows allowed and blocked actions",
      "Owner submits -> API creates a seven-day single-use invitation and UI shows Copy invitation link",
      "Recipient opens the link -> invitation screen shows workspace, inviter, role, expiry, and privacy summary",
      "Recipient signs in and selects Join workspace -> membership is created and Family Home opens",
      "Owner returns to Members -> new member appears as Active and the invitation is marked Accepted"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "an authenticated adult owner enters a valid email and non-owner role",
        "when": "they create an invitation",
        "then": "one hashed, seven-day invitation is persisted and the raw token is returned only in the creation response"
      },
      {
        "type": "given",
        "text": "an invitation remains pending",
        "when": "the owner revokes it",
        "then": "the invitation becomes REVOKED and subsequent preview or acceptance returns 410 without creating membership"
      },
      {
        "type": "given",
        "text": "the API or network fails during creation",
        "when": "the owner retries with the same idempotency key",
        "then": "only one pending invitation exists and entered email and role remain visible"
      }
    ]
  },
  {
    "id": "US-011",
    "epic": "Trusted Family Access and Invitations",
    "role": "teen contributor",
    "action": "accept an invitation after authenticating",
    "benefit": "the app can enforce my identity and role without trusting browser-supplied actor headers",
    "story": "As a teen contributor, I want to accept an invitation after authenticating, so that the app can enforce my identity and role without trusting browser-supplied actor headers.",
    "gui_flow": [
      "Recipient opens invitation URL -> sees a safe preview without private project data",
      "Recipient selects Sign in to join -> authentication screen preserves the invitation token",
      "Recipient signs in with the invited email -> app returns to the invitation screen",
      "Recipient selects Join workspace -> server compares authenticated email with invitation email",
      "Success state names the role and permitted actions -> user selects Go to Home",
      "Family Home loads server-derived navigation and hides adult-only destinations"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a valid invitation email matches the authenticated user email",
        "when": "the user accepts",
        "then": "one active membership is created and the session derives actor ID and email exclusively from the verified JWT"
      },
      {
        "type": "given",
        "text": "the same user opens an already accepted token",
        "when": "the screen loads",
        "then": "the API returns ALREADY_JOINED and a Home destination without a duplicate row"
      },
      {
        "type": "given",
        "text": "the authenticated email differs or token is expired/revoked",
        "when": "the user attempts acceptance",
        "then": "the API returns 403 or 410, reveals no workspace content, and creates no membership"
      }
    ]
  },
  {
    "id": "US-012",
    "epic": "Trusted Family Access and Invitations",
    "role": "parent owner",
    "action": "manage family roles without removing the last owner",
    "benefit": "workspace control cannot be accidentally lost",
    "story": "As a parent owner, I want to manage family roles without removing the last owner, so that workspace control cannot be accidentally lost.",
    "gui_flow": [
      "Owner opens Members -> sees active members, roles, joined dates, and pending invitations",
      "Owner opens a member menu -> allowed role changes are listed",
      "Owner selects a new role -> confirmation summarizes permissions gained and lost",
      "Owner confirms -> membership role updates and an audit event is recorded",
      "Affected member refreshes -> navigation and actions immediately match the new role",
      "Owner attempts to demote or remove the final owner -> action is disabled with explanatory text"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "two active owners exist",
        "when": "one owner changes the other to ADULT_COLLABORATOR",
        "then": "the role changes, audit records old and new roles, and session permissions update"
      },
      {
        "type": "given",
        "text": "only one active owner exists",
        "when": "that owner attempts demotion or removal",
        "then": "the API returns 409 last_owner_required and no membership changes"
      },
      {
        "type": "given",
        "text": "a non-owner calls member-management endpoints",
        "when": "authorization runs",
        "then": "the API returns 403 and does not reveal the member list"
      }
    ]
  },
  {
    "id": "US-013",
    "epic": "Preview-first Editor and Review Handoff",
    "role": "teen contributor",
    "action": "edit a channel draft with live preview and conflict-safe autosave",
    "benefit": "I can create confidently without accidental overwrite or publishing",
    "story": "As a teen contributor, I want to edit a channel draft with live preview and conflict-safe autosave, so that I can create confidently without accidental overwrite or publishing.",
    "gui_flow": [
      "Contributor opens a draft from Home -> editor shows title, channel, revision, and Saved state",
      "Contributor types -> status changes to Unsaved then Saving after 800 ms idle",
      "Autosave succeeds -> status announces Saved as vN and preview updates",
      "Contributor switches Edit and Preview on mobile -> content and channel constraints remain visible",
      "Contributor opens revision history -> sees author, time, and immutable version list",
      "Contributor selects Submit for review -> note sheet opens and no Publish control is present"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the current expected version matches the server",
        "when": "autosave runs after 800 ms idle",
        "then": "one new revision is created, status announces vN, and preview displays the saved content"
      },
      {
        "type": "given",
        "text": "another user saved first",
        "when": "autosave receives a conflict",
        "then": "editor blocks further autosave and offers Reload latest and Copy my draft without losing local text"
      },
      {
        "type": "given",
        "text": "the request fails or device goes offline",
        "when": "autosave runs",
        "then": "local draft remains in IndexedDB, status says Saved on this device, and sync retries once online without duplicate revisions"
      }
    ]
  },
  {
    "id": "US-014",
    "epic": "Preview-first Editor and Review Handoff",
    "role": "teen contributor",
    "action": "submit the exact current draft with a note",
    "benefit": "an adult reviews the version I intended",
    "story": "As a teen contributor, I want to submit the exact current draft with a note, so that an adult reviews the version I intended.",
    "gui_flow": [
      "Contributor selects Submit for review -> sheet shows current revision and receiving adult role",
      "Contributor enters an optional note up to 500 characters -> counter updates",
      "Contributor confirms -> server binds one pending review to the current revision",
      "Success state shows Waiting for review and exact revision",
      "Contributor chooses Continue editing -> warning explains that a new save supersedes the request",
      "Contributor saves a change -> previous request becomes Superseded and a new submission is required"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a non-empty current revision has no matching pending review",
        "when": "the contributor submits",
        "then": "one PENDING review is created for that exact version and Home shows Waiting for review"
      },
      {
        "type": "given",
        "text": "the same revision already has a pending review",
        "when": "the contributor submits again",
        "then": "the existing review is returned and no duplicate notification or review row is created"
      },
      {
        "type": "given",
        "text": "submission fails",
        "when": "the contributor retries",
        "then": "note and draft remain available and the same client request key prevents duplicate review creation"
      }
    ]
  },
  {
    "id": "US-015",
    "epic": "Preview-first Editor and Review Handoff",
    "role": "parent approver",
    "action": "compare the submitted revision with its predecessor and decide",
    "benefit": "I can approve or request precise changes with confidence",
    "story": "As a parent approver, I want to compare the submitted revision with its predecessor and decide, so that I can approve or request precise changes with confidence.",
    "gui_flow": [
      "Parent opens Review queue -> card shows human title, contributor, channel, age, risk, and revision",
      "Parent opens a card -> preview and decision panel load with contributor note",
      "Parent selects Changes tab -> additions and removals are labeled in text and color",
      "Parent selects Request changes -> 10-1000 character required reason appears",
      "Parent confirms -> asset returns to Draft and contributor Home shows the reason",
      "Alternatively parent approves -> exact revision receives approval and Publish action becomes available"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a current pending review is opened by an adult reviewer",
        "when": "they approve it",
        "then": "review records reviewer, timestamp, reason, and APPROVED state and asset exposes Publish"
      },
      {
        "type": "given",
        "text": "a submitted revision is no longer current",
        "when": "the reviewer opens it",
        "then": "the screen labels Superseded, disables decision controls, and links to the current request if present"
      },
      {
        "type": "given",
        "text": "decision submission fails",
        "when": "the reviewer retries",
        "then": "typed reason remains, server state is refreshed, and no second decision is recorded"
      }
    ]
  },
  {
    "id": "US-016",
    "epic": "Safe Publish Confirmation and Recovery",
    "role": "parent approver",
    "action": "confirm destinations, approved revision, and timing before publishing",
    "benefit": "I know exactly what will become public",
    "story": "As a parent approver, I want to confirm destinations, approved revision, and timing before publishing, so that I know exactly what will become public.",
    "gui_flow": [
      "Parent opens an approved project -> primary action reads Publish approved vN",
      "Parent selects it -> confirmation displays reviewer, revision, preview, connected accounts, and channels",
      "Parent chooses Publish now or future schedule -> summary updates in local timezone with UTC detail",
      "Parent selects Confirm publish -> button disables and progress lists one row per channel",
      "Each row moves through Queued, Publishing, and terminal state -> screen reader receives concise updates",
      "Completion screen shows Published, Partial success, or Needs attention with next actions"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the current revision has a matching adult approval and selected accounts are healthy",
        "when": "the adult confirms",
        "then": "one idempotent batch is created and every selected channel receives one delivery row"
      },
      {
        "type": "given",
        "text": "approval becomes stale before confirmation",
        "when": "the adult confirms",
        "then": "API returns 409 approval_required_for_current_revision and UI returns to Review without creating a batch"
      },
      {
        "type": "given",
        "text": "the confirmation request times out",
        "when": "the adult selects Check status",
        "then": "the same idempotency key resolves the existing batch or safely creates it once, never duplicating deliveries"
      }
    ]
  },
  {
    "id": "US-017",
    "epic": "Safe Publish Confirmation and Recovery",
    "role": "parent owner",
    "action": "retry only failed channels after partial success",
    "benefit": "successful posts are preserved and not duplicated",
    "story": "As a parent owner, I want to retry only failed channels after partial success, so that successful posts are preserved and not duplicated.",
    "gui_flow": [
      "Parent opens Publish result -> each channel row shows status, time, and remote link or error",
      "One channel is Published and another is Retryable -> page headline says Partial success",
      "Parent selects Retry failed channels -> confirmation lists only failed channels",
      "Parent confirms -> successful row stays locked and unchanged",
      "Retrying channel moves through Queued and Publishing -> result refreshes",
      "All channels succeed -> batch headline changes to Published and retry control disappears"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a batch contains published and retryable deliveries",
        "when": "the adult retries",
        "then": "only retryable delivery IDs are queued and published remote IDs and attempt counts remain unchanged"
      },
      {
        "type": "given",
        "text": "a batch has no failed or retryable channels",
        "when": "the adult calls retry",
        "then": "API returns 409 nothing_to_retry and UI offers View result only"
      },
      {
        "type": "given",
        "text": "a failed channel has unknown external state",
        "when": "the adult attempts retry",
        "then": "UI requires Check status first and backend performs no external send until reconciliation marks it retryable"
      }
    ]
  },
  {
    "id": "US-018",
    "epic": "Safe Publish Confirmation and Recovery",
    "role": "family business owner",
    "action": "understand and recover expired connection or unknown external state",
    "benefit": "I can resolve publishing problems without technical knowledge",
    "story": "As a family business owner, I want to understand and recover expired connection or unknown external state, so that I can resolve publishing problems without technical knowledge.",
    "gui_flow": [
      "Owner opens a project with connection issue -> publish gate names the affected channel",
      "Owner selects Fix connection -> Connections panel opens with account and required action",
      "Owner reconnects or selects Check connection -> health check returns Healthy or Action required",
      "Owner returns to publish confirmation -> healthy channels are selected and blocked channels are disabled",
      "Owner confirms healthy destinations -> progress and result are visible",
      "If a provider response is unknown -> result offers Check status, not Retry, until reconciliation completes"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a selected connection is expired before batch creation",
        "when": "the owner opens confirmation",
        "then": "the channel is disabled with Reconnect and no delivery is created for it"
      },
      {
        "type": "given",
        "text": "at least one other selected connection is healthy",
        "when": "the owner removes the blocked channel and confirms",
        "then": "healthy channels publish while the blocked channel remains unattempted and clearly listed"
      },
      {
        "type": "given",
        "text": "provider state is unknown after submission",
        "when": "the owner checks status",
        "then": "the app reconciles by remote identifier, redacts provider secrets, and enables retry only after a definitive failed state"
      }
    ]
  }
]
```

## Product Requirements

### Feature A requirements

**Evidence addressed:** research demands bounded participation and child-appropriate defaults; the development report flags browser actor headers and missing invitation/member UI.

**Behavior and API rules**
- All `/api/v1/family/*` endpoints use `Depends(get_current_user)` and derive actor ID/email/display name from the verified access token. `X-User-*` values are ignored and never used as identity.
- Invitation preview is public only to the token holder and returns workspace display name, inviter display name, role, allowed/blocked capability labels, expiry, and status. It returns no project, member list, email, or internal IDs beyond invitation ID.
- Invitation acceptance requires JWT authentication and exact normalized email match. Tokens contain at least 256 bits, are SHA-256 hashed at rest, single-use, seven-day expiry, and revocable.
- Owner-only member APIs list active members and pending invitations; update roles; remove members; revoke invitations. The last active owner may not be demoted or removed.
- Membership changes invalidate family session/navigation immediately on the next API request. Audit records actor, old/new role, target, and timestamp.
- Idempotency is required for invitation creation and acceptance. Body mismatch with reused key returns 409.

**Validation and failures**
- Email uses the project's Pydantic email validation; role allowlist excludes `ADULT_OWNER` for invitations.
- Wrong email returns 403; expired/revoked token returns 410; unknown token returns 404 with the same generic public copy.
- Non-owner management requests return 403; cross-workspace targets return 404.

**Backward compatibility:** expert APIs remain unchanged. The family SPA must use Bearer tokens. A development-only authentication fixture may create tokens; production must not have header fallback.

**Non-goals:** SSO, age verification, invitation email sending, organization-wide SCIM.

### Feature B requirements

**Evidence addressed:** current family UI has no route-addressable editor; research and Planable-style workflows demand contextual review and unambiguous versions.

**Behavior**
- Editor loads asset, project, current revision, permissions, channel constraints, and preview from a workspace-scoped endpoint.
- Autosave begins 800 ms after last input; one request is active at a time; further changes queue one latest save. `expected_version` prevents overwrite.
- On 409, autosave stops. `Reload latest` replaces the editor only after confirmation; `Copy my draft` copies/local-downloads the unsaved text. Local text is never silently dropped.
- IndexedDB stores workspace/asset/user/version/text/updated time. Online success deletes the matching local snapshot. Offline state is explicit.
- Desktop 1024+ uses 55/45 editor-preview split. Tablet 768-1023 uses stacked cards. Mobile below 768 uses labeled Edit/Preview tabs and sticky action bar.
- Preview supports LinkedIn and X plain-text cards, visible character count, and warning when source exceeds platform guidance; no silent truncation.
- Revision drawer lists version, author, timestamp, and status. Read-only comparisons are produced server-side with `difflib` and returned as labeled added/removed/unchanged segments.
- Submit-review sheet binds the current version and optional 500-character note. New edit supersedes pending/approved review.
- Review detail includes title, project, contributor, channel, revision, note, preview, diff, findings, audit timestamps, and current/stale status.

**Failures:** loading has skeleton; not found is generic; offline preserves local; validation focuses summary; failed decision retains reason; stale review disables decisions.

**Non-goals:** WYSIWYG rich text, real-time collaboration, inline annotations, AI rewrite controls.

### Feature C requirements

**Evidence addressed:** research highlights publishing trust and partial-success recovery; previous implementation has domain primitives but no sellable confirmation/result UX.

**Behavior**
- Publish eligibility endpoint returns current revision, matching approval, reviewer/time, selected destination accounts, connection health, allowed schedule range, and blocking reasons.
- Only adult owner/collaborator can publish. Current revision must have `APPROVED`; stale approval returns 409.
- `publish_at` is absent for now or RFC 3339 future time. UI displays local timezone and UTC detail. Past times return 422.
- Idempotency key spans confirmation timeout/retry. Same body returns existing batch; different body returns 409.
- Batch state is derived from deliveries: `QUEUED`, `PUBLISHING`, `PUBLISHED`, `PARTIAL`, `FAILED`, or `UNKNOWN`.
- Result endpoint returns per-channel account label, state, attempt count, timestamps, safe error code/message, remote URL/ID when known, and allowed actions.
- Retry endpoint targets only `FAILED` or `RETRYABLE`; published rows are immutable. `UNKNOWN` requires reconciliation.
- Reconciliation checks connector status by remote identifier where available. No second send occurs while unknown.
- When no real connector is configured, family production API must not fabricate published success. It returns `CONNECTION_REQUIRED`; deterministic fake connectors are test-only fixtures.

**Non-goals:** new connectors, content analytics, billing credits, queue infrastructure migration.

## UI and UX Specification

### Personas and journey

- Parent owner manages members and resolves connections.
- Adult collaborator reviews and publishes.
- Teen contributor edits and submits from phone.
- Viewer reads only.

Primary journey: recipient accepts invitation -> teen opens assigned draft -> autosaves and previews -> submits exact version -> parent reviews diff -> confirms approved revision and destinations -> observes per-channel progress -> recovers only failed channel.

### Navigation

Keep Family Home, Create, Projects, Review, Calendar. Add adult workspace-menu items `Members`, `Connections`, and `Privacy`. Route guards consume server permissions and redirect forbidden routes to Home with `You do not have access to that area`; server authorization remains authoritative.

### Design system

Reuse existing CSS tokens and family classes. Extract reusable primitives into `frontend/src/family/ui/`: Button, Field, Dialog, Drawer, Tabs, StatusBadge, Skeleton, InlineError, EmptyState, Toast, ProgressRows. No runtime component library. Add `@axe-core/playwright` only as a dev dependency if not already available.

Minimum 44x44 touch targets; 4.5:1 normal text contrast; 3:1 large text/non-text control contrast; 2 px high-contrast focus ring with 2 px offset; no color-only status. Respect reduced motion. Dialogs trap focus, Escape closes only non-destructive dialogs, and focus returns to opener.

## Screen Inventory and User Flows

### 1. Invitation Preview and Acceptance `#/join/:token`

Header has logo and Sign in/out. Body card shows workspace, inviter, role, expiry, `You can` and `You cannot` lists, privacy copy, and primary `Join workspace`. Unauthenticated users see `Sign in to join`; token persists through auth. Expired/revoked state shows `Ask the owner for a new invitation`; already joined shows `Go to Home`. Skeleton mirrors card. Generic token error reveals no email or project data.

### 2. Members and Invitations `#/settings/members`

Adult-only. Header: `Family members`, subtitle, primary `Invite member`. Active members table/cards show avatar initials, display name, masked email for non-self, role, joined date, and menu. Pending section shows role, expiry, Copy link, Revoke. Invite dialog has email, role cards, permission preview, validation, Cancel/`Create invitation`. Role-change dialog lists gained/lost permissions. Last owner actions are disabled with visible explanation.

### 3. Preview-first Editor `#/projects/:projectId/assets/:assetId`

Top: breadcrumb, title, channel badge, revision selector, autosave live region. Main: editor and preview split; character count and channel warnings beneath editor. Sticky footer: contributors `Submit for review`; adults `Review current version`; no contributor Publish. Revision history drawer opens from header. Conflict banner contains `Reload latest`, `Copy my draft`, and current server version. Offline banner names local save time.

### 4. Submit Review Dialog

Shows exact revision, receiving adult role, optional note field/counter, warning that later edits supersede review, Cancel and `Submit version N`. Success toast and status panel show `Waiting for review`. Failed submission retains note and offers Retry.

### 5. Review Queue `#/review`

Filters Pending, Needs changes, Completed; search by title/project. Cards show title, contributor, channel, age, risk, version, and status. Empty state says `No reviews waiting` and links Home. Loading skeleton and per-panel Retry are required.

### 6. Review Detail `#/review/:reviewId`

Header identifies project/title/version/status. Desktop: preview left, sticky decision panel right. Tabs: Preview, Changes, Checks, Activity. Changes uses `Added`, `Removed`, `Unchanged` labels plus semantic `<ins>/<del>`. Decision panel offers `Approve current version` and `Request changes`; reason validation is inline and summarized. Superseded screen disables decisions and links current review.

### 7. Publish Confirmation `#/projects/:projectId/publish`

Header says `Publish approved vN`. Approval card shows reviewer/time and view-review link. Destination rows show channel, account, connection health, and checkbox. Timing control offers `Now` or `Schedule`; schedule displays local and UTC. Summary preview is read-only. Primary exactly `Confirm publish`; disabled states list blockers. Timeout recovery changes primary to `Check publish status` with same idempotency key.

### 8. Publish Progress and Result `#/publish/:batchId`

Headline and aggregate badge. Per-channel rows show account, live state, time, remote link, and safe error. Poll every 2 seconds while non-terminal, stop after terminal/unmount, and use `aria-live=polite` for aggregate changes only. Partial state primary `Retry failed channels`; unknown primary `Check status`; expired connection `Reconnect`. Successful rows have no retry control. Empty/not found/error states are explicit.

### 9. Connection Recovery Panel `#/settings/connections?returnTo=`

Shows only selected family workspace accounts. Each row: channel, account, health, last check, permissions, `Reconnect` or `Check connection`. Return link preserves publish context. No secret/token values are rendered.

### Responsive behavior

- Mobile `<768`: top bar plus existing five-item bottom nav; one-column screens; editor tabs; sticky review/publish actions above safe-area inset.
- Tablet `768-1023`: compact rail, stacked editor/preview, two-column member cards.
- Desktop `>=1024`: 220 px sidebar; editor 55/45 split; review 65/35; max content 1400 px.

### Full flow and recovery

Teen opens invitation, authenticates, joins, opens draft, edits offline, reconnects and autosaves, submits v3. Parent reviews v3 changes, approves, opens publish confirmation, sees one expired connection and reconnects, confirms two channels. One publishes, one becomes retryable. Parent retries only failed channel; published row remains unchanged; batch becomes Published. Every failure retains entered data and offers one safe next action.

## Architecture and Technical Design

### Backend boundaries

- Refactor `src/routers/family.py` to inject `current_user: User = Depends(get_current_user)` and delegate only.
- Extend `src/family/store.py` for revocation, member administration, asset detail, revision list/diff, eligibility, result, retry, and reconciliation. Keep parameterized SQL and workspace scoping.
- Add `src/family/permissions.py` for named permissions and exhaustive map; migrate inline role map without changing effective current permissions.
- Add `src/family/service.py` for invitation/JWT orchestration, editor DTO assembly, publish eligibility/derivation/retry/reconciliation.
- Add `src/schemas/family.py` for request/response models and enums. Remove untyped dict response construction from router.
- Reuse `src/services/publish_service.py` connectors, but inject fake connectors only in tests. Do not preserve synthetic production success.

### Frontend boundaries

Split the current monolithic `frontend/src/family.tsx` into `family/api.ts`, `session.tsx`, `routes.tsx`, `offline-drafts.ts`, shared UI primitives, and screen components. Keep `FamilyApp` as composition root. Use React local/context state, AbortController, and one polling hook; no new state library.

### Data changes

- Add `revoked_at` to invitations.
- Add `updated_at` to memberships/assets/reviews.
- Add delivery `attempt_count`, `last_attempt_at`, `error_code`, `external_state_checked_at`.
- Add publish batch `idempotency_key`, `publish_at`, `updated_at` if absent.
- Store invitation raw token nowhere. The current `token_once` column must be migrated to null and no longer written. Existing pending raw tokens are invalidated during migration because secure recovery is impossible; document this breaking security migration.
- Add indexes for workspace memberships, pending reviews, project assets, batch deliveries, invitation token hash.

Use additive SQLite migration in store initialization matching repository convention, plus migration tests against a copy of the current schema.

### Exact APIs

- `GET /api/v1/family/invitations/{token}/preview`
- `POST /api/v1/family/invitations/{token}/accept` with `Idempotency-Key`
- `GET /api/v1/family/workspaces/{id}/members`
- `PATCH /api/v1/family/workspaces/{id}/members/{membershipId}` body `{role}`
- `DELETE /api/v1/family/workspaces/{id}/members/{membershipId}`
- `DELETE /api/v1/family/workspaces/{id}/invitations/{invitationId}`
- `GET /api/v1/family/assets/{assetId}`
- `PUT /api/v1/family/assets/{assetId}/autosave` body `{content, expected_version, client_updated_at}`
- `GET /api/v1/family/assets/{assetId}/revisions`
- `GET /api/v1/family/reviews/{reviewId}`
- Existing submit/decision endpoints remain, now JWT-authenticated and typed.
- `GET /api/v1/family/assets/{assetId}/publish-eligibility`
- `POST /api/v1/family/publish-batches` with required idempotency header and optional `publish_at`
- `GET /api/v1/family/publish-batches/{batchId}`
- `POST /api/v1/family/publish-batches/{batchId}/reconcile`
- `POST /api/v1/family/publish-batches/{batchId}/retry`

All private object lookups return 404 across workspace boundaries. Error codes remain in `detail`; field errors use Pydantic 422 shape.

## Data, API, and Compatibility Changes

Existing expert APIs and hash routes remain. Family route request identity changes intentionally: `X-User-*` no longer authenticates. The SPA must obtain/store the existing access token and send `Authorization: Bearer`. Development E2E seeds users and tokens using auth endpoints or fixtures. Legacy raw invitation tokens are revoked by migration. Existing accepted memberships, projects, assets, reviews, ideas, and batches are preserved.

No backend runtime dependency is added. Frontend dev dependency `@axe-core/playwright` is permitted. Use browser IndexedDB directly.

## Security and Privacy Considerations

- JWT is the only family identity source. Reject missing/invalid token with 401 and `WWW-Authenticate: Bearer`.
- Membership and object scope checks precede serialization; cross-workspace response is 404.
- Raw invitation token is only in create response and URL, never DB/log/analytics. Hash compare uses constant-time comparison where practical.
- Invitation preview omits invited email and internal workspace data.
- Last-owner invariant is transactionally enforced.
- Autosave only accepts text, size max 100,000 characters; local drafts are namespaced by user/workspace/asset and cleared on logout.
- Publish errors redact connector credentials and response bodies. Logs include correlation ID, actor/workspace/entity, safe event, and outcome only.
- CSRF is mitigated by Authorization header token rather than cookie auth. CORS stays explicit.
- No claim of COPPA compliance; no age or behavioral advertising data is added.

## Test Strategy (TDD)

### RED-first tests

Create failing tests named/tagged US-010 through US-018 before implementation. Each of the 27 acceptance criteria maps to a unique parametrized ID such as `US-010-AC1`.

### Backend

- `tests/test_family_auth_invites.py`: JWT-only identity; spoofed headers ignored; preview minimization; accept/revoke/idempotency/expiry/wrong email.
- `tests/test_family_members.py`: permission matrix, role changes, cross-workspace 404, last-owner transaction.
- `tests/test_family_editor.py`: asset DTO, 800 ms behavior at component level, expected-version conflict, revisions, diff, stale review.
- `tests/test_family_publish_flow.py`: eligibility, schedule validation, idempotency, real connector test double, partial status, selective retry, unknown reconciliation, no synthetic production success.
- Migration integration test opens a copy of the current SQLite schema and verifies data preservation/raw-token revocation.

### Frontend

Component tests for InvitationScreen, MembersScreen, FamilyEditor, ReviewDetail, PublishConfirmation, PublishResult, ConnectionRecovery; fake timers for 800 ms autosave and polling; IndexedDB stub with real serialization; keyboard/focus assertions; mobile route rendering.

### E2E

Add `frontend/e2e/family-completion.spec.ts` with tagged flows: invitation/auth, contributor editor conflict/offline recovery, exact review, stale approval, publish partial retry, unknown reconciliation, role route denial. Run Chromium desktop 1440x900 and mobile 390x844. Capture screenshots for invitation, members, editor desktop/mobile, review, confirmation, partial result, recovered result, plus empty and error states. Add axe scans and console/page-error guard.

### Commands

Supported repository commands:

```bash
python -m pytest tests/test_family_auth_invites.py tests/test_family_members.py tests/test_family_editor.py tests/test_family_publish_flow.py
python -m pytest
ruff check src tests
cd frontend && npm test
cd frontend && npm run lint
cd frontend && npm run build
python scripts/run_backend.py
cd frontend && npm run dev
cd frontend && npx playwright test e2e/family-completion.spec.ts
```

If Playwright browsers are absent, install them before verification and record exact result. Changed/new Python modules and family frontend logic target >=90% line coverage; permission and publish-gate branches require complete case coverage.

### Objective pass criteria

Zero targeted/full failures; existing 2,587-test baseline does not regress; zero Ruff/new ESLint/type/build errors; backend and frontend start; family E2E passes desktop/mobile; no serious axe findings; all required lab gates exit 0. Any unavailable gate or git remote is BLOCKED, never reported as PASS.

## Documentation Deliverables

- `README.md`: JWT family quick start, invitation/editor/review/publish flow, configuration and troubleshooting.
- `CHANGELOG.md`: trusted access, editor/review, publish recovery, migration, tests, accessibility.
- `docs/family-workspace.md`: update all exact endpoints, role matrix, invitation lifecycle, autosave/offline/conflict, review diff, publish/reconcile/retry, privacy boundaries.
- `docs/api-overview.md`: family endpoint and error summary.
- `FEATURES-DONE.md`: list only fully completed features and map US-010 through US-018.
- `development-report.md`: replace with RED/GREEN evidence, exact test/gate/build/startup/E2E/screenshot/git results, migration evidence, files, limitations, and traceability.

## Expected File Changes

**Add:** `src/family/permissions.py`, `src/family/service.py`, `src/schemas/family.py`; focused backend test modules; `frontend/src/family/api.ts`, `session.tsx`, `routes.tsx`, `offline-drafts.ts`, `ui/*`, `screens/InvitationScreen.tsx`, `MembersScreen.tsx`, `FamilyEditor.tsx`, `ReviewQueue.tsx`, `ReviewDetail.tsx`, `PublishConfirmation.tsx`, `PublishResult.tsx`, `ConnectionRecovery.tsx`; component tests; `frontend/e2e/family-completion.spec.ts`.

**Modify:** `src/family/store.py`, `src/routers/family.py`, `src/main.py` only if dependency wiring requires it, `frontend/src/family.tsx`, `frontend/src/main.tsx`, `frontend/src/styles.css`, package dev dependencies/lock for axe, README, CHANGELOG, family/API docs, FEATURES-DONE, development-report.

Do not modify unrelated domain behavior. Fix pre-existing frontend lint issues only if required for the mandatory full lint gate, and document them separately.

## Traceability Matrix

| Research need | Research evidence | User story id | Planned requirement | Acceptance criterion | Planned implementation location | Planned test evidence | Priority |
|---|---|---|---|---|---|---|---|
| Safe bounded participation | Research recommends adult-owned roles; report flags trusted headers | US-010 | Owner invitation/revocation UI and API | create, revoke, idempotent retry | family service/router; Members screen | auth-invite unit/integration/E2E | P0 |
| Verified identity | Child privacy requires role enforcement; actor headers are current risk | US-011 | JWT-only acceptance/session | match, repeat, wrong/expired | auth dependency; Invitation screen | spoof-header and acceptance tests | P0 |
| Durable adult control | Last-owner rule planned but incomplete | US-012 | role management and invariant | update, last owner, non-owner denial | permissions/store; Members screen | member transaction tests | P0 |
| Low-friction contribution | Research asks mobile capture and contextual workflow | US-013 | preview editor and safe autosave | save, conflict, offline | editor APIs; FamilyEditor | autosave/IndexedDB/E2E | P0 |
| Exact handoff | Approval/version ambiguity is validated demand | US-014 | exact-version submit | create, duplicate, failure retry | review service/dialog | submit integration/component tests | P0 |
| Review confidence | Current report says review UI incomplete | US-015 | diff and measurable decision | approve, stale, failure | diff DTO; ReviewDetail | review API/component/E2E | P0 |
| Trust before public action | Research highlights reliable adult publishing | US-016 | eligibility and confirmation | create, stale, timeout | publish service; confirmation | idempotency/eligibility/E2E | P0 |
| Preserve successes | Research and existing domain favor selective retry | US-017 | per-channel result/retry | failed only, none, unknown | batch service; result screen | partial/retry tests | P0 |
| Plain-language recovery | Families need nontechnical connection recovery | US-018 | reconnect and reconciliation | expired, healthy subset, unknown | connector adapter; recovery panel | connector/reconcile/E2E | P0 |

## Risks and Mitigations

- JWT integration may expose assumptions in the current demo shell. Mitigate with a single family session provider and authenticated E2E fixture; no production header fallback.
- Current invitation table stores `token_once`. Revoke all legacy pending tokens and migrate safely; accepted memberships remain.
- External connector APIs may be unavailable. Use protocol-compatible test doubles; production reports connection required, never fake success.
- IndexedDB behavior differs by browser/private mode. Surface storage failure and preserve in-memory text; do not claim offline persistence if write failed.
- Monolithic current family component increases merge risk. Split by screen while preserving route entry and styles.
- Previous full regression exceeded execution timeout. Run targeted groups during work, then full suite with sufficient timeout and record exact final summary.

## Definition of Done

- [ ] Features A, B, and C are complete with no facade, browser-controlled identity, or synthetic production publish success.
- [ ] US-010 through US-018 each have happy, edge, and error tests passing.
- [ ] All 27 acceptance criteria appear in traceability/test evidence.
- [ ] Invitation, member, editor, review, confirmation, result, and recovery screens work desktop/mobile.
- [ ] JWT, tenant isolation, invitation secrecy, last-owner invariant, idempotency, stale approval, selective retry, and unknown reconciliation tests pass.
- [ ] Migration preserves existing accepted family data and invalidates legacy raw pending tokens.
- [ ] Targeted tests and full regression pass with exact counts.
- [ ] Changed/new modules measure >=90% coverage.
- [ ] Ruff, full frontend lint, tests, type-check/build, startup, Playwright desktop/mobile, screenshots, and accessibility checks pass.
- [ ] `tdd-gate-v3.sh`, `bdd-gate.sh`, `security-gate.sh`, `doc-sync-check.sh`, and `ui-gate.sh` exit 0.
- [ ] README, CHANGELOG, API/family docs, FEATURES-DONE, and development-report match actual behavior.
- [ ] No secrets, raw invitation tokens, caches, databases, dependency folders, build outputs, or screenshot scratch artifacts are packaged except intentional evidence paths documented by the lab.
- [ ] Git add/commit/pull-rebase/push completes; working tree is clean; `git-push-verify.sh` exits 0. If input lacks Git metadata/remote, exact attempts are BLOCKED in report.
- [ ] Complete project ZIP preserves top-level layout and passes integrity/list/extraction verification.
