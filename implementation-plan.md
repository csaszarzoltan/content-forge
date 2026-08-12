# Implementation Plan

## Executive Summary

This pass turns the existing Family Creator paid-beta mechanics into a **provable, supportable release candidate**. It selects three integrated features from the research: **Provider Confidence and Reconciliation**, **Pilot Instrumentation and Guided Onboarding**, and **Youth Privacy and Adult-Controlled Trust**. The pass does not add another publishing network, generation mode, or visible scheduling promise.

The implementation reuses FastAPI, the current SQLite-backed `FamilyStore`, React 19, TypeScript, Vite, Vitest, and Playwright. It introduces no production third-party dependency. New domain modules separate provider verification, pilot aggregation, permission policy, visibility language, and privacy operations from the already large router/store. SQLite tables are added through the repository's current idempotent create/alter startup pattern, preserving existing databases. Existing `/api/v1/family` contracts remain valid; new fields are additive and new endpoints are namespaced beneath the same prefix.

A complete release candidate must satisfy two evidence tracks. Automated checks must finish with zero backend failures, zero frontend test failures, zero lint failures, a successful production build and startup smoke, and zero critical browser E2E failures. Provider claims additionally require observed LinkedIn and X sandbox evidence from approved non-public accounts. If credentials or provider approval are unavailable, automated implementation may pass, but provider verification remains **BLOCKED**, never “passed.”

Scheduling remains hidden in family mode. Its future return requires persistent due jobs, atomic leasing, restart recovery, timezone and DST tests, cancellation, idempotent dispatch, and browser-visible execution history.

## Current-State Validation

The research matches the extracted project:

- `src/family/store.py` implements adult-owned workspaces, membership roles, seven-day invitations, private ideas, projects/assets/revisions, exact-revision reviews, idempotent publish batches, per-channel deliveries, selective retry, reconciliation and weekly counts.
- `src/routers/family.py` uses JWT `get_current_user`, constructs real LinkedIn/X connectors when credentials exist, records `connection_required` otherwise, and exposes publish result, retry, reconcile, connection and weekly-summary routes.
- `frontend/src/family.tsx` supplies a separate family shell, four-step setup, Home, idea capture, guided project creation, invitation acceptance, Members, editor/review, Connections, publish confirmation and channel results.
- `tests/test_family_api.py` and `tests/test_family_completion.py` exercise the existing SQLite domain. The release report states 2,599 backend tests collected with exit 0, 39 frontend tests passing, clean frontend lint/build and successful startup smoke.
- `docs/provider-sandbox-checklist.md` and `provider-sandbox-results.csv` are an honest verification framework, not proof of successful live posting. `docs/family-pilot.md` and `family-pilot-results.csv` similarly define a pilot but contain no outcome proof.
- `frontend/playwright.config.ts` and one transcreation E2E exist, but the project has no family E2E and does not list `@playwright/test` in `frontend/package.json`. The development pass must add and pin that dev dependency and deterministic Chromium provisioning.
- Existing `research-findings.md` contains nine complete stories, three per selected feature. This plan refines all nine without changing their IDs.

Current weaknesses that directly determine scope:

1. Connections are called `HEALTHY` from credential presence alone; capability, expiry and live evidence are not represented.
2. The publish endpoint performs connector calls inline and classifies most connector failures too coarsely. Unknown state is modeled by the store but is not produced from timeout/ambiguous provider results through a dedicated application service.
3. Retry currently mutates store state but the route does not execute a provider retry, so paid-beta recovery is not end-to-end complete.
4. Pilot metrics are external CSV fields only. There is no consented cohort, privacy-preserving event model, aggregate dashboard or go/no-go computation.
5. Roles are server enforced, but Members does not show a complete effective-capability matrix and there is no family privacy/export/deletion workflow.
6. Scheduling is removed from publish confirmation, but Calendar still appears in navigation. In this pass it becomes an immediate-publication history view called **Activity**, avoiding an implied scheduling promise while preserving route compatibility.

## Research Priorities

1. **P0 provider proof:** successful LinkedIn/X posting, expired token, permission denial, rate limit, ambiguous provider outcome, repeated idempotency key, partial success and failed-channel-only retry.
2. **P0 pilot proof:** first useful draft time, ten-second next action, contributor publish-boundary comprehension, visibility-state comprehension, unaided invitation, unaided review/publish, recovery support, and weekly time saved.
3. **P1 youth/family trust:** visible effective permissions, immediate server enforcement, age-appropriate state explanations, data export/deletion and retention transparency.
4. **Release honesty:** immediate publishing only; no scheduled-job UI until durable execution is proved.
5. **Release quality:** full regression, lint, build, startup, browser E2E, accessibility and lab gates.

## Selected Scope for This Pass

### Feature A: Provider Confidence and Reconciliation

Satisfies US-001, US-002 and US-003. Add a durable connection profile and provider verification-attempt model, normalized failure taxonomy, capability checks, evidence view, real provider sandbox runner, end-to-end selective retry, and reconcile-before-retry behavior. The normal publish path and sandbox path share connector adapters and classification but use separate records and explicit `purpose` values.

### Feature B: Pilot Instrumentation and Guided Onboarding

Satisfies US-004, US-005 and US-006. Add opt-in pilot cohorts, pseudonymous household enrollment, content-free funnel events, metric aggregation/export, safety-stop decisions, and an adult-only Pilot dashboard. Instrument the existing first-draft, invitation, review/publish and recovery flows without collecting draft text, tokens or provider response bodies.

### Feature C: Youth Privacy and Adult-Controlled Trust

Satisfies US-007, US-008 and US-009. Centralize role capabilities, show effective permissions to owners and affected members, add member data export/deletion with reauthentication and retention receipts, and use one visibility-state vocabulary across Home, Editor, Review and Publish Result.

These features are coherent because the live provider flow creates the exact recovery evidence the pilot measures, while permission and visibility clarity prevent the pilot from validating an unsafe mental model.

## Deferred Scope and Rationale

1. **Durable scheduled publication:** deferred to the next reliability phase. Prerequisites: persisted due jobs, atomic lease/heartbeat, restart pickup, UTC storage, IANA timezone display, Europe/Zurich DST gap/fold tests, cancellation, outbox or equivalent deduplication, and E2E evidence.
2. **Additional social networks:** deferred until LinkedIn and X both pass the complete sandbox matrix. More adapters would increase unproved surface area.
3. **Recurring schedules/content calendar authoring:** deferred with scheduling. This pass renames family Calendar navigation to Activity while preserving `#calendar` as an alias.
4. **Child-directed under-13 launch and age assurance:** deferred pending privacy counsel, consent implementation validation and jurisdiction analysis. `TEEN_CONTRIBUTOR` remains a permission role, not proof of age.
5. **Billing and paid-plan enforcement:** deferred until at least five households complete the pilot and value/time-saving thresholds are met.
6. **New AI generation or design features:** deferred because evidence identifies trust, provider proof and comprehension as the bottlenecks.
7. **Multi-instance queue infrastructure:** deferred; the paid-beta remains a single-node SQLite deployment. Provider attempts are durable, but interactive publish execution remains request/worker bounded rather than a general distributed queue.
8. **Enterprise SSO/SCIM and cross-tenant administration:** unrelated to the validated family beta.

Deferred item count: 8.

## User Stories (BDD)

```json
[
  {
    "id": "US-001",
    "epic": "Provider Confidence and Reconciliation",
    "role": "adult owner",
    "action": "test each connected publishing account before the first real family post",
    "benefit": "I know whether LinkedIn and X are operational without risking a family draft",
    "story": "As a adult owner, I want to test each connected publishing account before the first real family post, so that I know whether LinkedIn and X are operational without risking a family draft.",
    "gui_flow": [
      "User opens Connections from Family Home -> sees each channel with Not tested, Healthy, or Action required state",
      "User selects Test connection for LinkedIn -> sees the exact account name, granted capabilities, and test scope",
      "User confirms a non-public sandbox action -> the system creates an idempotent provider test attempt",
      "The provider responds -> the screen shows success, failure, rate limit, or unknown state in plain language",
      "User opens Evidence -> sees timestamp, provider request correlation, sanitized response category, and no credential value",
      "User returns Home -> publishing readiness reflects the latest verified connection state"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a configured LinkedIn sandbox credential and an unused idempotency key",
        "when": "the adult runs Test connection",
        "then": "one provider attempt is recorded and the account becomes Healthy only after a confirmed remote identifier is returned"
      },
      {
        "type": "given",
        "text": "the same idempotency key already produced a confirmed post",
        "when": "the adult repeats the test",
        "then": "no second provider post is created and the prior remote identifier is returned"
      },
      {
        "type": "given",
        "text": "the provider times out after accepting the request",
        "when": "the test finishes without a definitive response",
        "then": "the connection is marked Verification required, automatic repost is blocked, and Reconcile is offered"
      }
    ]
  },
  {
    "id": "US-002",
    "epic": "Provider Confidence and Reconciliation",
    "role": "adult publisher",
    "action": "recover a partially successful multi-channel publish without repeating successful posts",
    "benefit": "I can fix one channel safely",
    "story": "As a adult publisher, I want to recover a partially successful multi-channel publish without repeating successful posts, so that I can fix one channel safely.",
    "gui_flow": [
      "User opens a Publish Result with LinkedIn Published and X Failed -> sees an honest partial-success summary",
      "User expands X -> sees the failure class and the next safe action",
      "User selects Retry failed channel -> sees LinkedIn excluded from the retry set",
      "User confirms -> a new X attempt reuses the original delivery idempotency identity",
      "The provider responds -> only the X row changes state while LinkedIn preserves its remote identifier",
      "User opens Audit details -> sees both attempts and the final aggregate result"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a batch has one PUBLISHED and one FAILED delivery",
        "when": "the adult retries failed channels",
        "then": "only failed or retryable channels receive a provider call and successful remote identifiers remain byte-for-byte unchanged"
      },
      {
        "type": "given",
        "text": "the failed channel is rate limited with a retry-after value",
        "when": "the adult opens the result",
        "then": "Retry is disabled until the displayed provider-safe time and no request is sent early"
      },
      {
        "type": "given",
        "text": "the provider state is UNKNOWN",
        "when": "the adult selects Retry",
        "then": "the system runs reconciliation first and blocks a new post until the remote state is resolved or a documented manual override is recorded"
      }
    ]
  },
  {
    "id": "US-003",
    "epic": "Provider Confidence and Reconciliation",
    "role": "adult owner",
    "action": "reconnect an expired or under-scoped provider credential from the failed delivery",
    "benefit": "I can restore publishing without technical support",
    "story": "As a adult owner, I want to reconnect an expired or under-scoped provider credential from the failed delivery, so that I can restore publishing without technical support.",
    "gui_flow": [
      "User opens a failed delivery -> sees Token expired or Permission missing instead of a generic error",
      "User selects Reconnect account -> the Connections screen opens with the affected channel focused",
      "User completes the approved provider OAuth flow -> the callback validates state and required scopes",
      "The system runs a non-destructive capability check -> the account shows Healthy or Missing permission",
      "User returns to the delivery -> Retry failed channel is enabled only when required capabilities are present",
      "User retries -> the result records the new credential version without exposing the token"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "an expired token is attached to a failed delivery",
        "when": "the owner completes reconnect with required scopes",
        "then": "the connection becomes Healthy and only the failed delivery becomes retryable"
      },
      {
        "type": "given",
        "text": "OAuth succeeds but a required posting scope is absent",
        "when": "the callback completes",
        "then": "the UI lists the missing capability, keeps publish disabled, and stores no false Healthy state"
      },
      {
        "type": "given",
        "text": "the OAuth state value is invalid or expired",
        "when": "the callback is received",
        "then": "the connection is unchanged, the event is audited, and the user sees a safe restart action"
      }
    ]
  },
  {
    "id": "US-004",
    "epic": "Pilot Instrumentation and Guided Onboarding",
    "role": "new adult owner",
    "action": "complete the first useful draft through one measured guided path",
    "benefit": "I can judge value before learning the whole platform",
    "story": "As a new adult owner, I want to complete the first useful draft through one measured guided path, so that I can judge value before learning the whole platform.",
    "gui_flow": [
      "User signs in to a new family workspace -> sees one Start first project action",
      "User selects a goal and audience -> sees a four-step progress indicator and a private-by-default notice",
      "User captures an idea or chooses a starter -> the draft preview appears with an editable message",
      "User saves the draft -> the system records time-to-first-useful-draft without storing keystroke content in telemetry",
      "User sees the next action Submit for adult review -> the exact revision is identified",
      "User completes the flow -> the weekly summary shows minutes saved as an estimate the user can correct"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a new owner has no projects",
        "when": "the owner saves a non-empty first draft",
        "then": "activation telemetry records one anonymous funnel event and elapsed seconds, with a target median of 600 seconds or less"
      },
      {
        "type": "given",
        "text": "the browser goes offline after step two",
        "when": "the owner continues editing and reconnects",
        "then": "the draft is restored, no duplicate project is created, and elapsed time excludes the offline wait when reported"
      },
      {
        "type": "given",
        "text": "draft generation fails",
        "when": "the owner selects Retry",
        "then": "entered goal and audience remain intact and the error event contains no draft text or credential data"
      }
    ]
  },
  {
    "id": "US-005",
    "epic": "Pilot Instrumentation and Guided Onboarding",
    "role": "teen contributor",
    "action": "understand my next permitted action within ten seconds",
    "benefit": "I can contribute without fearing accidental publication",
    "story": "As a teen contributor, I want to understand my next permitted action within ten seconds, so that I can contribute without fearing accidental publication.",
    "gui_flow": [
      "Teen opens Family Home -> sees a contributor label and one primary next action",
      "Teen opens a private idea -> sees Private to family near the content title",
      "Teen turns the idea into a draft -> sees Save draft and Submit for review controls",
      "Teen opens the action menu -> Publish is absent and a short explanation is available",
      "Teen submits the exact revision -> sees Waiting for adult review",
      "Teen returns Home -> the next action changes to Capture another idea or respond to requested changes"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the signed-in member has TEEN_CONTRIBUTOR role",
        "when": "the Home screen renders",
        "then": "the first actionable control is contributor-permitted and no publish control exists in the DOM"
      },
      {
        "type": "given",
        "text": "the teen edits a revision that was previously approved",
        "when": "the save completes",
        "then": "the prior approval is superseded and the state returns to Needs adult review"
      },
      {
        "type": "given",
        "text": "the teen calls a publish endpoint directly",
        "when": "the request is handled",
        "then": "the server returns 403, creates no batch or provider attempt, and writes a permission-denied audit event"
      }
    ]
  },
  {
    "id": "US-006",
    "epic": "Pilot Instrumentation and Guided Onboarding",
    "role": "pilot facilitator",
    "action": "export privacy-preserving pilot outcomes for five to ten households",
    "benefit": "I can make a release decision from comparable evidence",
    "story": "As a pilot facilitator, I want to export privacy-preserving pilot outcomes for five to ten households, so that I can make a release decision from comparable evidence.",
    "gui_flow": [
      "Facilitator opens Admin Pilot dashboard -> sees enrolled household count and completion status",
      "Facilitator filters by pilot cohort -> sees median draft time, invitation success, review success, recovery support, and weekly time-saved measures",
      "Facilitator opens a metric -> sees its definition, denominator, and missing-data count",
      "Facilitator selects Export -> receives a CSV with pseudonymous household IDs and no content text",
      "Facilitator reviews safety-stop events -> sees any accidental-publication or permission incident highlighted",
      "Facilitator records the release decision -> the report stores criteria values and rationale"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "at least five consenting pilot households have completed one week",
        "when": "the facilitator opens the dashboard",
        "then": "all required metrics show numerator, denominator, median or rate, and 95% confidence is not claimed for the small sample"
      },
      {
        "type": "given",
        "text": "a household withdraws consent",
        "when": "the facilitator refreshes the cohort",
        "then": "that household is excluded from future exports and its identifiable pilot linkage is deleted within the configured retention window"
      },
      {
        "type": "given",
        "text": "an accidental-publication or minor-permission incident exists",
        "when": "the facilitator attempts to mark the pilot Go",
        "then": "the system blocks Go until the safety stop is resolved and an adult reviewer records disposition"
      }
    ]
  },
  {
    "id": "US-007",
    "epic": "Youth Privacy and Adult-Controlled Trust",
    "role": "adult owner",
    "action": "review and change every member's effective permissions in plain language",
    "benefit": "I can maintain safe boundaries as family roles change",
    "story": "As a adult owner, I want to review and change every member's effective permissions in plain language, so that I can maintain safe boundaries as family roles change.",
    "gui_flow": [
      "Owner opens Members -> sees each member, role, and effective capability summary",
      "Owner selects a member -> sees Can and Cannot lists for ideas, drafts, review, publish, credentials, billing, and membership",
      "Owner changes Teen contributor to Viewer -> sees the access impact before saving",
      "Owner confirms -> active sessions are re-evaluated and new permissions apply immediately",
      "Owner opens Audit -> sees who changed the role, when, and from/to values",
      "Owner tests View as member -> sees a read-only preview without impersonating or exposing private credentials"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "an adult owner views a teen member",
        "when": "the member detail opens",
        "then": "all seven sensitive capability categories are explicitly shown and Publish, credentials, billing, and member management are denied"
      },
      {
        "type": "given",
        "text": "the only remaining owner is selected for demotion or removal",
        "when": "the owner confirms",
        "then": "the server returns 409, explains the last-owner rule, and makes no membership change"
      },
      {
        "type": "given",
        "text": "a demoted member has an existing session",
        "when": "the member performs a newly forbidden action",
        "then": "server-side authorization denies it immediately without relying on cached UI state"
      }
    ]
  },
  {
    "id": "US-008",
    "epic": "Youth Privacy and Adult-Controlled Trust",
    "role": "adult owner",
    "action": "control retention and delete a family member's contributed personal data",
    "benefit": "I can honor household privacy choices",
    "story": "As a adult owner, I want to control retention and delete a family member's contributed personal data, so that I can honor household privacy choices.",
    "gui_flow": [
      "Owner opens Privacy and data -> sees collected categories and retention periods",
      "Owner selects a member -> sees ideas, drafts, audit records, and provider records separated by legal/operational need",
      "Owner chooses Delete contributed personal data -> sees consequences and items that must be retained in de-identified audit form",
      "Owner confirms with reauthentication -> a deletion job starts and progress is visible",
      "The job completes -> content ownership is reassigned or removed according to the selected policy",
      "Owner downloads a completion receipt -> it lists categories deleted, retained, and retention reasons"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "an owner requests deletion for a non-owner member",
        "when": "the verified request completes",
        "then": "personal profile data and private unreferenced ideas are removed within the configured target and retained audit entries are pseudonymized"
      },
      {
        "type": "given",
        "text": "a draft is part of a published batch",
        "when": "deletion is requested",
        "then": "the UI explains the immutable publication record and removes unnecessary profile linkage while preserving the minimal audit evidence"
      },
      {
        "type": "given",
        "text": "reauthentication fails",
        "when": "the deletion request is submitted",
        "then": "no deletion begins and the event is logged without revealing sensitive account details"
      }
    ]
  },
  {
    "id": "US-009",
    "epic": "Youth Privacy and Adult-Controlled Trust",
    "role": "teen contributor",
    "action": "see why content is private or public and who can change that state",
    "benefit": "I understand the boundary without surveillance or hidden rules",
    "story": "As a teen contributor, I want to see why content is private or public and who can change that state, so that I understand the boundary without surveillance or hidden rules.",
    "gui_flow": [
      "Teen opens an idea -> sees Private to family with a one-sentence explanation",
      "Teen opens a draft -> sees Private draft and the adults who may review it",
      "Teen submits for review -> sees that submission does not make content public",
      "Adult approves -> the teen sees Approved for adult publishing, not Published",
      "Adult publishes -> the teen sees Public on LinkedIn or X with timestamp and account label",
      "Teen opens Learn more -> sees the role rule and how to ask an adult for a change"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a draft has never been published",
        "when": "the teen views it",
        "then": "the state label says Private and no public URL or misleading success language is shown"
      },
      {
        "type": "given",
        "text": "a revision is approved but not published",
        "when": "the teen views status",
        "then": "the UI distinguishes Approved from Public and names the remaining adult action"
      },
      {
        "type": "given",
        "text": "publication state cannot be confirmed from the provider",
        "when": "the teen views status",
        "then": "the UI says Verification required rather than Public and provides no retry control to the teen"
      }
    ]
  }
]
```

## Product Requirements

### Feature A: Provider Confidence and Reconciliation

**Research problem and evidence:** connector mechanics exist, but the configured provider applications and accounts have not been proved. Credential presence is not health. Provider outcomes include confirmed success, authentication failure, authorization failure, rate limit, transient failure and unknown external state.

**Inputs and validation**

- Supported channels for this pass are exactly `linkedin` and `twitter`; API presentation label for Twitter is `X`.
- Provider test requests accept `channel`, `scenario`, `idempotency_key`, and an optional `cleanup_requested` boolean. `scenario` is one of `success`, `expired_token`, `permission_denied`, `rate_limit`, `unknown_state`, `idempotency_replay`, `partial_success`, `selective_retry`.
- Live scenario execution is adult-owner only and available only when `CONTENTFORGE_PROVIDER_SANDBOX_ENABLED=true` and the provider account is marked non-public/test in configuration. The API returns 409 `sandbox_not_enabled` otherwise.
- The server generates unique non-sensitive markers in the form `CF-SBX-<UTC date>-<12 random hex>`; user-entered post text is not accepted by the sandbox endpoint.
- Idempotency keys must be 16-128 printable ASCII characters. Reuse with an identical canonical request returns the original attempt. Reuse with a changed request returns 409.
- Evidence stores response class, HTTP status, provider request/correlation ID when safely available, confirmed remote ID/URL, attempt count and timestamps. It never stores access tokens, authorization headers, cookies, raw response bodies, personal account identifiers or post content beyond the generated marker.

**Business rules**

- Connection health states are `NOT_CONFIGURED`, `NOT_TESTED`, `HEALTHY`, `ACTION_REQUIRED`, `RATE_LIMITED`, and `VERIFICATION_REQUIRED`.
- Delivery states remain backward compatible and include `QUEUED`, `PUBLISHING`, `PUBLISHED`, `FAILED`, `RETRYABLE`, and `UNKNOWN`.
- Only a confirmed provider remote identifier permits `PUBLISHED` and connection `HEALTHY` after a test.
- A timeout, connection reset after request transmission, malformed success response without remote ID, or provider 5xx with uncertain side effect becomes `UNKNOWN` and connection `VERIFICATION_REQUIRED`.
- `UNKNOWN` cannot be retried. Reconcile must run first. If a provider lookup confirms publication, mark `PUBLISHED`; if it confirms absence, mark `RETRYABLE`; if lookup is unsupported or still ambiguous, preserve `UNKNOWN` and provide manual verification instructions.
- Selective retry calls only `FAILED`/`RETRYABLE` deliveries. It never calls a `PUBLISHED`, `UNKNOWN`, or currently `PUBLISHING` delivery.
- Rate limits store `retry_after_at` when supplied. Retry returns 409 before that UTC time.
- Successful delivery records and remote IDs are immutable. A second completion with a conflicting remote ID returns 409 and emits a high-severity audit event.
- Sandbox cleanup is best effort and recorded separately. Failure to delete a sandbox post does not erase successful publish evidence.

**Outputs and failure behavior**

- All errors use `{"detail": "stable_machine_code", "message": "plain language", "correlation_id": "..."}` for new routes. Existing FastAPI error bodies remain accepted on old routes for backward compatibility.
- UI never calls a connection Healthy merely because secrets exist.
- Live credentials missing: `NOT_CONFIGURED`, no network call.
- Expired/invalid token: `ACTION_REQUIRED`, error code `auth_expired`, primary action `Reconnect account`.
- Missing scope/permission: `ACTION_REQUIRED`, code `permission_missing`, list of normalized missing capabilities when known.
- Rate limit: `RATE_LIMITED`, display provider-safe UTC/local retry time, disable retry.
- Unknown: `VERIFICATION_REQUIRED`, action `Reconcile status`; no retry button.

**Dependencies:** existing connectors, `PublishService`, `FamilyStore`, settings and JWT. Add only `@playwright/test` as a frontend dev dependency for browser verification.

**Backward compatibility:** preserve every existing family endpoint and response field. Add fields only. Preserve existing idempotency semantics. Keep `twitter` as the API identifier. Do not change general non-family publishing routes.

**Measurable acceptance criteria:** all US-001..003 criteria; 100% of ambiguous attempts block retry; exact replay causes zero second provider calls; a partial batch retries only failed/retryable channels; evidence scan finds no configured secret value.

**Non-goals:** provider app application/approval, production-account posting, third provider, scheduled publishing, automatic deletion guarantees, or a generic connector framework rewrite.

### Feature B: Pilot Instrumentation and Guided Onboarding

**Research problem and evidence:** the protocol exists, but no in-product evidence shows that households understand the model or save time.

**Inputs and validation**

- Adult owner creates a pilot cohort with name (2-80 characters), start/end dates, target household count 5-10, consent text version and metric target version.
- Enrollment creates a random `participant_code`; exported data never contains workspace ID, user ID, email, member name or draft content.
- An owner must explicitly opt the workspace into the pilot. Opt-in records UTC timestamp, consent version and actor. Withdrawal stops collection immediately.
- Event names are allowlisted: `journey_started`, `first_draft_saved`, `next_action_answered`, `invite_previewed`, `invite_accepted`, `review_opened`, `review_decided`, `publish_completed`, `connection_recovery_started`, `connection_recovery_completed`, `support_intervention`, `weekly_time_reported`, `critical_incident_reported`.
- Event attributes are schema-limited primitives. Reject keys named or matching `content`, `text`, `caption`, `token`, `secret`, `authorization`, `email`, `name`, `url`, or `remote_id`.
- Client durations are advisory. Server timestamps are authoritative for start/end; paused/offline seconds are recorded separately and excluded from active duration.

**Business rules**

- Instrument only enrolled workspaces. Non-enrolled workspaces produce no pilot event rows.
- First useful draft completes on the first successful non-empty saved revision in the first pilot project, not on LLM generation or text entry.
- The ten-second question is a moderated/pilot task with explicit start and recorded answer; normal navigation telemetry is not repurposed as a covert comprehension score.
- Support intervention count increments only through facilitator action after the documented 90-second threshold.
- Withdrawal removes the workspace-to-participant linkage and excludes events from future aggregates/exports. Event rows may remain only under a non-linkable participant code according to the declared research retention period.
- Pilot decision states are `DRAFT`, `GO`, `NO_GO`, `BLOCKED_SAFETY`. Any unresolved critical incident forces `BLOCKED_SAFETY` and prevents GO.
- Dashboard reports numerator, denominator and missing count for every rate. It reports medians for durations and never presents inferential confidence claims for this cohort.
- Time saved is `max(0, prior_weekly_hours - pilot_weekly_hours)` and remains marked self-reported.

**Outputs and failure behavior**

- Export CSV uses the existing `family-pilot-results.csv` column order plus `consent_version`, `withdrawn_at`, and `data_completeness`. Notes are excluded from default export; a separate adult-reviewed qualitative export may include redacted notes.
- Dashboard displays `No households enrolled`, skeleton, partial-data, export-ready, safety-blocked and API-error/retry states.
- Failed telemetry must never block the user's draft, invitation, review or publish action. It logs a redacted warning with correlation ID and retries at most once in the browser session.

**Backward compatibility:** weekly summary remains available. Additive `pilot` fields appear only for enrolled workspaces. Existing family flows work with pilot disabled, which is the default.

**Acceptance criteria:** all US-004..006 criteria; event content-key rejection; zero pilot rows for unconsented workspaces; export contains no direct identifier; safety incident blocks GO; pilot metrics reproduce fixture calculations exactly.

**Non-goals:** product analytics for all customers, session replay, keystroke capture, draft analysis, automated recruitment, incentives, causal time-saving claims or statistical significance claims.

### Feature C: Youth Privacy and Adult-Controlled Trust

**Research problem and evidence:** role enforcement exists, but users need a shared, understandable permission and visibility model plus data lifecycle controls.

**Inputs and validation**

- Capability categories are exactly `ideas`, `drafts`, `review`, `publish`, `connections`, `billing`, `members`, each with `view`, `create`, `edit`, `decide`, or `manage` actions as applicable.
- Existing roles remain `ADULT_OWNER`, `ADULT_COLLABORATOR`, `TEEN_CONTRIBUTOR`, `VIEWER`. Billing remains denied for every role until billing is implemented; UI says `Not available in this beta` rather than implying a hidden entitlement.
- Role updates accept only these values and require owner authority. The last-owner rule remains.
- Privacy export/deletion is available to adult owners for a selected membership. Destructive requests require a fresh-auth proof issued within the previous five minutes.
- Deletion options are `DELETE_PRIVATE_CONTRIBUTIONS` and `PSEUDONYMIZE_PROFILE_AND_PRIVATE_CONTRIBUTIONS`. The preview endpoint returns counts and retained categories before confirmation.

**Business rules**

- Server policy is the source of truth; UI derives from the same serialized capability matrix returned by session/member endpoints.
- Role changes apply on the next request. No long-lived authorization cache is introduced.
- `View as member` is a projection of capabilities and navigation, not impersonation. It never issues a token for the selected member or exposes their private data.
- Visibility states are `PRIVATE_IDEA`, `PRIVATE_DRAFT`, `WAITING_FOR_REVIEW`, `APPROVED_FOR_ADULT_PUBLISHING`, `PUBLISHING`, `PUBLIC`, `PARTIALLY_PUBLIC`, `VERIFICATION_REQUIRED`, `PUBLICATION_FAILED`.
- Approved is never rendered as public. Unknown provider state is `VERIFICATION_REQUIRED`, never public.
- Deletion removes or pseudonymizes member profile linkage, private unreferenced ideas, and eligible private draft authorship in one transaction. Published batch/delivery evidence is retained only with pseudonymous actor reference and documented retention reason.
- Audit event payloads are minimized; no token, draft content, email or display name is written for privacy operations.
- Completion receipt records request ID, categories deleted, categories pseudonymized, categories retained, reasons and completion UTC time. It contains no deleted content.

**Failure behavior**

- Last-owner demotion/removal returns 409 and no partial update.
- Failed reauthentication returns 401 and creates no deletion job.
- Deletion transaction failure rolls back all data changes and leaves state `FAILED_RETRYABLE`; receipt is not issued.
- Missing membership returns 404 to owners and does not reveal former membership details to non-owners.

**Backward compatibility:** preserve role names and existing membership endpoints. Extend responses with capability and visibility objects. Existing clients can ignore them.

**Acceptance criteria:** all US-007..009 criteria; policy matrix and UI agree for all four roles; role downgrade blocks the next forbidden API request; deletion is transactional; labels are consistent across all family screens.

**Non-goals:** legal determination of parental authority, age verification, under-13 onboarding, global GDPR/CCPA automation, billing controls, or deletion of remote provider posts.

## UI and UX Specification

### Personas and primary journey

- Adult owner: prove connections, manage members/privacy, review and publish.
- Adult collaborator: create, review, publish and recover, but cannot manage membership or privacy deletion.
- Teen contributor: capture ideas, edit drafts, submit review and understand status; no connection/publish/member/privacy controls.
- Pilot facilitator: adult-authorized internal role exposed only when `PILOT_ADMIN_USER_IDS` contains the current user ID. It manages cohort evidence, not family content.

Primary journey: Sign in -> Home next action -> connection verification if needed -> Create private project -> Submit exact revision -> Adult Review -> immediate Publish -> channel Result -> reconcile/reconnect on failure -> weekly/pilot outcome.

### Information architecture and navigation

Keep the current family shell and hash routing. Desktop/tablet navigation: **Home, Create, Projects, Review, Activity**. `Activity` replaces the visible `Calendar` label; `#calendar` redirects to or renders `#activity` for compatibility. Owner-only Settings links: **Members, Connections, Privacy & data**. Pilot Admin is never in family navigation; authorized facilitators access `#pilot-admin` directly and see an `Admin` badge.

### Design system decision

Reuse `frontend/src/styles.css` and existing family tokens. Do not add a component library in this pass. The UI surface is bounded and the existing project has no component dependency; adding one increases bundle and integration risk. Extract local reusable components into `frontend/src/family/` rather than keeping all behavior in `family.tsx`.

Required tokens:

- spacing: 4, 8, 12, 16, 24, 32, 48 px;
- radii: 8 px controls, 12 px cards, 16 px major panels;
- minimum control height: 44 px; minimum pointer target 24x24 CSS px with at least 8 px separation where 44 px is impossible;
- focus: 3 px high-contrast outline with 2 px offset;
- text contrast: at least 4.5:1; large text/UI graphics at least 3:1;
- states: green/confirmed, amber/action required/rate limited, red/failed/destructive, blue/private/in progress, slate/neutral. Every state includes icon and text.
- motion: transitions <=180 ms; under `prefers-reduced-motion: reduce`, remove movement and use immediate state changes.

Breakpoints: mobile `<640px`, tablet `640-1023px`, desktop `>=1024px`. Mobile uses bottom navigation and one-column cards. Tablet uses a compact side rail and two-column layouts only when each column remains at least 320 px. Desktop limits reading width to 1200 px and uses a 280 px detail sidebar where specified.

### Accessibility behavior

- Add a first-focus skip link to `main`.
- Every view has one `h1`; cards use ordered heading levels.
- Status updates use a single polite `aria-live` region; destructive/reconciliation errors use `role=alert`.
- Dialogs trap focus, close on Escape only when cancellation is safe, restore focus to the opener and have labelled title/description.
- Tables have captions, header cells and responsive card alternatives on mobile.
- Tabs use the ARIA tab pattern and arrow-key navigation.
- Icon-only buttons have explicit accessible names.
- Form errors are linked with `aria-describedby`; focus moves to the first invalid field after submission.
- Screens never indicate state by color alone.

## Screen Inventory and User Flows

### 1. Family Home

**Purpose:** one next action and immediate trust/readiness summary.

**Layout:** top workspace header; next-action hero; three status cards for `Draft & review`, `Connections`, and `This week`; recent projects; family ideas; owner-only links to Members, Connections and Privacy.

**Primary CTA:** contextual `Start first project`, `Review draft`, `Verify connection`, `Reconcile result`, or `Continue project`. **Secondary:** `Capture idea`.

**States:** skeleton cards while loading; empty project starter; offline banner with last successful refresh; partial panel failure with panel-level Retry; contributor view omits adult controls; safety block displays `Adult help needed` without exposing provider details.

**Flow:** owner opens Home -> sees `Verify connection` when no provider has passed -> opens Connections -> verifies or reconnects -> returns to Home -> CTA changes to `Start first project`.

### 2. Connections

**Purpose:** distinguish configured credentials from proved provider capability.

**Layout:** page header (`Connections`, explanation that tests use non-public accounts); provider cards; each card shows account alias, health state, capabilities, token expiry if known, last verified UTC/local time, last failure, and actions; Evidence drawer lists sanitized attempts.

**Primary CTAs:** `Test LinkedIn`, `Test X`, `Reconnect account`, or `Reconcile status` depending on state. **Secondary:** `View evidence`, `Return to publish`.

**States:** `Not configured`, `Not tested`, `Testing`, `Healthy`, `Action required`, `Rate limited until <time>`, `Verification required`; test confirmation dialog; success toast; failure explanation; disabled test with exact reason when sandbox disabled.

**Recovery:** expired token deep-links to reconnect; permission missing lists required capability; unknown state shows only Reconcile. Focus returns to the provider card after dialog completion.

### 3. Provider Test Confirmation

**Purpose:** prevent accidental public posting and explain evidence/cleanup.

**Layout:** modal with provider account alias, generated marker preview, non-public/test-account attestation, scenario, cleanup behavior and warning. Checkbox `I confirm this is an approved non-public test account` is mandatory.

**Primary CTA:** `Run sandbox test`. **Secondary:** `Cancel`.

**Validation/error:** button disabled until checked; 409 sandbox disabled remains in dialog; network ambiguity closes no dialog automatically and changes body to `Provider state needs verification` with `Open reconciliation`.

### 4. Provider Evidence Detail

**Purpose:** auditable, secret-free attempt record.

**Layout:** breadcrumb; outcome banner; definition list for provider, scenario, timestamps, attempt count, HTTP class, local correlation ID, idempotency fingerprint, remote ID when confirmed and cleanup state; attempt timeline; copy-safe JSON button containing only allowlisted fields.

**Primary CTA:** `Reconcile status` when unknown, `Reconnect account` for auth/permission, otherwise `Back to connections`. **Secondary:** `Download evidence CSV` for owner/pilot facilitator.

**Empty/error:** no raw provider body; unavailable evidence displays a stable local attempt ID and Retry loading action.

### 5. Publish Confirmation

**Purpose:** calm adult-only immediate publication of an approved exact revision.

**Layout:** privacy/approval banner; content preview; approved revision and reviewer; channel checkboxes with connection health; immediate-publication statement; consequences.

**Primary CTA:** `Publish now`. **Secondary:** `Back to review`.

**Rules:** no date/time/scheduling control. Disable an unhealthy channel with `Fix connection`. If all selected channels are unhealthy, disable Publish and focus the first explanation.

### 6. Publish Result

**Purpose:** honest channel-level final or recoverable state.

**Layout:** aggregate banner; one row/card per channel with state, attempt time, remote link, error explanation and next action; audit/evidence accordion.

**Primary CTA by state:** `View public post`, `Retry failed channel`, `Reconnect account`, or `Reconcile status`. `UNKNOWN` never displays Retry. **Secondary:** `Back home`.

**Partial flow:** LinkedIn Published, X Failed -> user expands X -> clicks Retry failed channel -> confirmation explicitly says LinkedIn will not be resent -> only X changes to Publishing -> final result updates; LinkedIn remote ID remains visible and unchanged.

### 7. Guided Create Journey

**Purpose:** first useful private draft with consented timing.

**Layout:** existing four steps retained: goal, project/audience, message/CTA, channels/summary. Persistent progress, private-by-default notice and Save state.

**Primary CTA:** `Continue` then `Create private draft`. **Secondary:** `Back`, `Save and exit`.

**Instrumentation:** when enrolled, a small `Pilot measurement on` badge links to data explanation. No draft text enters measurement events. Offline state stores draft locally, displays `Saved on this device`, and syncs once with the same idempotency key.

### 8. Contributor Home and Editor

**Purpose:** safe contribution with visible limits.

**Layout:** role badge `Teen contributor`; next action; visibility badge next to title; editor; revision/save state; permission explanation link.

**Primary CTA:** `Save private draft` or `Submit for adult review`. There is no Publish element in DOM. **Secondary:** `Why can't I publish?` opens a non-modal explanation.

**Error/edge:** direct prohibited API action renders `An adult controls public publishing` without suggesting credential access. Editing an approved revision immediately shows `Approval needs to be repeated`.

### 9. Invitation Preview and Acceptance

**Purpose:** self-service acceptance with role clarity.

**Layout:** workspace, inviter display name if available, expiry, role, Can/Cannot matrix, private-default notice, sign-in/join action.

**Primary CTA:** `Join workspace`. **Secondary:** `Sign in with another account`.

**States:** checking skeleton; expired/revoked generic unavailable state; email mismatch with account-switch action; success confirmation and Home redirect. Pilot instrumentation records only timestamps/outcome and participant code.

### 10. Review Inbox and Review Detail

**Purpose:** approve exact content with visible author, revision and visibility effect.

**Layout:** inbox filters; detail header; content and word diff; author/role; current state; decision panel.

**Primary CTA:** `Approve revision` or `Request changes`. **Secondary:** `Back to inbox`.

**Rules:** approval copy says `Approved for adult publishing`, not public. Request changes requires reason. Superseded revision disables decision and links to current revision.

### 11. Members and Effective Permissions

**Purpose:** owner management and shared capability clarity.

**Layout:** member list; selected-member detail; Can/Cannot table across seven categories; role selector; impact preview; audit summary; `View as member` projection.

**Primary CTA:** `Save role change`. **Secondary:** `View as member`, `Remove member`.

**States:** owner-only edit controls; affected member receives read-only capability view; last-owner action disabled with explanation and backed by 409; role save success moves focus to updated role heading.

### 12. Privacy & Data

**Purpose:** data-category transparency, export and deletion.

**Layout:** collection/retention overview; member selector; data category counts; `Export member data`; destructive `Delete or pseudonymize`; request history.

**Primary CTA:** `Export data` or, within destructive dialog, `Continue to reauthentication`. **Secondary:** `Cancel`.

**Deletion flow:** preview counts -> choose policy -> display retained publication/audit reasons -> reauthenticate -> confirm exact member -> processing state -> completion receipt. Failure rolls back and offers `Retry request`; no content preview is shown.

### 13. Activity

**Purpose:** immediate publication history without a scheduling promise.

**Layout:** chronological batches grouped by date; filters `All`, `Published`, `Needs action`; channel/state rows and links to results.

**Primary CTA:** row-specific `Open result`. Empty state: `No publication activity yet` plus `Create a private draft`. `#calendar` resolves here but UI title is Activity.

### 14. Pilot Admin Dashboard

**Purpose:** conduct a 5-10-household pilot and make a documented go/no-go decision.

**Layout:** cohort selector; consent/enrollment card; metric cards with definitions/denominators/missing counts; household pseudonymous table; safety incidents; exports; decision panel.

**Primary CTAs:** `Create cohort`, `Export pilot CSV`, `Record decision`. **Secondary:** `Enroll workspace`, `Withdraw household`, `View metric definition`.

**States:** unauthorized 404-style screen; no cohort; loading skeleton; partial data; safety blocked red banner; decision confirmation. GO button is disabled when a critical incident remains unresolved or fewer than five active households have required completion.

### End-to-end success and recovery

Success: owner signs in -> verifies LinkedIn/X -> creates a private draft -> teen edits/submits -> adult opens Review and approves exact revision -> Publish now -> both channel rows become Published -> Activity and weekly/pilot metrics update.

Friendly recovery: X times out after request transmission -> result says Verification required -> Retry is absent -> owner selects Reconcile -> provider confirms no post -> X becomes Retryable -> owner retries X only -> LinkedIn is not called -> X succeeds -> aggregate becomes Published. If reconciliation cannot decide, state stays Verification required with manual-check instructions and correlation ID.

## Architecture and Technical Design

### Component boundaries

- `src/family/permissions.py`: immutable role/capability policy and serialization.
- `src/family/visibility.py`: pure domain-to-UI visibility mapping and messages.
- `src/family/provider_verification.py`: scenario validation, safe marker generation, outcome classification, evidence allowlist and provider test orchestration.
- `src/family/connections.py`: connection profile/capability normalization and health computation.
- `src/services/family_publish.py`: application service for initial publish, selective retry and reconciliation; router no longer owns connector loop.
- `src/family/pilot.py`: event schema allowlist, aggregation, go/no-go rules and CSV generation.
- `src/family/privacy.py`: export inventory, deletion preview, transactional execution and receipt construction.
- `src/family/store.py`: persistence primitives and migrations only; retain public methods for compatibility.
- `src/routers/family.py`: thin HTTP validation/auth/error mapping.
- Frontend split into `frontend/src/family/FamilyApp.tsx`, `Home.tsx`, `Connections.tsx`, `Publish.tsx`, `Members.tsx`, `Privacy.tsx`, `PilotAdmin.tsx`, `types.ts`, `api.ts`, `components.tsx`; keep `frontend/src/family.tsx` as a compatibility export.

### Data flow and state management

Continue React local state and fetch helpers; do not introduce Redux or a query library. Each page owns `idle/loading/success/error` state and aborts stale requests with `AbortController`. Provider/publish result polling uses bounded backoff (1s, 2s, 4s, then 5s, maximum 60s) and stops on terminal state or unmount. All mutations include an idempotency key generated once per user intent and retained across browser retry.

Server flow: router authenticates -> application service checks capability -> store opens transaction -> connector call occurs outside a long SQLite write transaction -> result classifier normalizes outcome -> store atomically records attempt/delivery/audit -> response serializer returns additive contract.

### Persistence changes

Add idempotently:

- `family_connections`: `id`, `workspace_id`, `channel`, `account_alias`, `state`, `capabilities_json`, `token_expires_at`, `last_verified_at`, `last_error_code`, `updated_at`; unique `(workspace_id, channel)`.
- `family_provider_attempts`: `id`, `workspace_id`, `batch_id`, `delivery_id`, `connection_id`, `purpose`, `scenario`, `idempotency_key_hash`, `marker`, `state`, `http_status`, `provider_correlation_id`, `remote_id`, `error_code`, `retry_after_at`, `cleanup_state`, `started_at`, `completed_at`, `attempt_count`.
- `family_pilot_cohorts`: cohort metadata, target count, consent/metric versions and decision state.
- `family_pilot_participants`: pseudonymous code, cohort/workspace linkage, consent/withdrawal timestamps. Workspace linkage is nullable and cleared on withdrawal.
- `family_pilot_events`: participant code, allowlisted event, numeric/boolean attributes JSON, server timestamp, client elapsed/offline seconds.
- `family_pilot_incidents`: severity, status, privacy-safe category, timestamps, disposition.
- `family_privacy_requests`: selected membership pseudonymous reference, policy, state, preview/result JSON, requested/completed timestamps and actor.
- `family_reauth_proofs`: hashed one-time proof, actor, purpose, issued/expires/used timestamps.

Add to `family_deliveries`: `retry_after_at`, `provider_attempt_id`, `state_verified_at`. Add to `family_audit` no new content-bearing columns.

Migrations follow current PRAGMA inspection and `ALTER TABLE` behavior in `FamilyStore.__init__`. Every migration is idempotent and tested against a copied pre-change SQLite fixture. No existing row is deleted or rewritten during migration.

### Alternatives considered

- **Celery/Redis:** rejected for this pass; unnecessary infrastructure for interactive paid-beta verification.
- **New component library:** rejected; current design system can satisfy scope and dependencies should remain small.
- **Raw provider response storage:** rejected for secret/PII risk. Store normalized allowlisted evidence.
- **Retry on timeout:** rejected because it can duplicate external posts.
- **General analytics SDK:** rejected because pilot consent/data minimization need a narrower event schema.
- **Hard-delete all historical evidence:** rejected because publication integrity requires a minimal pseudonymous audit record.

## Data, API, and Compatibility Changes

All endpoints require JWT except invitation preview and provider OAuth callbacks. Owner-only routes explicitly check `ADULT_OWNER`; pilot routes also require configured facilitator allowlist.

### Connection and provider verification APIs

- `GET /api/v1/family/connections?workspace_id=<id>&return_to=<hash>` -> `{items:[{id,channel,label,account_alias,state,capabilities:{required,granted,missing},token_expires_at,last_verified_at,last_error_code,actions:[]}],return_to}`.
- `POST /api/v1/family/connections/{connection_id}/sandbox-tests` with header `Idempotency-Key` and body `{workspace_id,scenario,cleanup_requested,test_account_attested}` -> 202 attempt summary.
- `GET /api/v1/family/provider-attempts/{attempt_id}?workspace_id=<id>` -> sanitized evidence only.
- `GET /api/v1/family/provider-attempts?workspace_id=<id>&channel=<optional>&limit=50` -> paginated sanitized attempts.
- `POST /api/v1/family/provider-attempts/{attempt_id}/reconcile` -> updated attempt/delivery state; 409 when not reconcilable.
- `POST /api/v1/family/connections/{connection_id}/recheck` -> non-posting capability/token check; never creates content.
- OAuth start returns server-generated state and PKCE data where provider supports it; callbacks validate state, bind workspace/actor and redirect to the sanitized `return_to`. Existing direct external URLs are removed from API responses once server OAuth initiation exists.

### Publish APIs

- Existing `POST /publish-batches` remains and returns additive `correlation_id`, `immediate:true`, and normalized delivery fields.
- Existing `POST /publish-batches/{batch_id}/retry` becomes async and executes connector calls for eligible channels; optional body `{workspace_id,channels}`, where omitted means all eligible. Existing query-only call remains accepted for one compatibility release.
- Existing `POST /publish-batches/{batch_id}/reconcile` executes provider lookup when available and returns per-channel evidence. Existing query parameter remains accepted.
- `GET /publish-batches/{batch_id}` adds `can_retry`, `can_reconcile`, `retry_after_at`, `attempt_id`, and privacy-safe `message` per delivery.

### Pilot APIs

- `POST /api/v1/family/pilot/cohorts`; `GET /pilot/cohorts`; `GET /pilot/cohorts/{id}`.
- `POST /pilot/cohorts/{id}/enroll` with `workspace_id` and consent version.
- `POST /pilot/participants/{code}/withdraw`.
- `POST /pilot/events` accepts one allowlisted event; returns 204. It is non-blocking to product flows.
- `GET /pilot/cohorts/{id}/metrics` returns definitions, numerators, denominators, missing counts, medians and threshold state.
- `GET /pilot/cohorts/{id}/export.csv` downloads pseudonymous CSV.
- `POST /pilot/cohorts/{id}/incidents`; `PATCH /pilot/incidents/{id}` for disposition.
- `POST /pilot/cohorts/{id}/decision` with `GO|NO_GO`; server derives `BLOCKED_SAFETY` and rejects invalid GO.

### Permission/privacy APIs

- `GET /workspaces/{id}/members` adds `capability_summary` to each member.
- `GET /workspaces/{id}/members/{membership_id}/capabilities` returns role, seven categories, Can/Cannot text and navigation projection.
- Existing role PATCH accepts `preview=true` as a dry run or add `POST .../role-preview` if query dry-run conflicts with FastAPI docs; selected contract is `POST /members/{id}/role-preview` with `{role}`.
- `POST /privacy/reauth` with password uses existing auth verification and returns a one-time five-minute proof.
- `GET /privacy/members/{membership_id}/preview?workspace_id=<id>`.
- `POST /privacy/members/{membership_id}/export` -> 202 privacy request; `GET /privacy/requests/{id}` returns state and a one-time download URL when ready.
- `POST /privacy/members/{membership_id}/delete` with `workspace_id`, `policy`, `reauth_proof`, `preview_hash` -> 202.
- `GET /privacy/requests/{id}/receipt` returns JSON/CSV receipt after completion.

### Compatibility guarantees

- No endpoint removal.
- No role, route prefix, state or field rename in backend storage contracts.
- `#calendar` remains a route alias, while visible text becomes Activity.
- Old SQLite databases open and migrate automatically; migration failure aborts startup before serving traffic.
- Pilot is disabled by default. Sandbox live execution is disabled by default.
- Existing general ContentForge workspaces remain unchanged.

## Security and Privacy Considerations

- Secrets stay in settings/environment and are redacted from logs, exceptions, evidence and test snapshots. Add a test that loads unique sentinel secrets and scans response/log artifacts for them.
- OAuth state is random, single-use, actor/workspace-bound and expires in ten minutes. Use PKCE where supported. Redirect targets are allowlisted local hash routes, never arbitrary URLs.
- Provider evidence uses normalized fields only. Hash idempotency keys before persistence in attempt evidence; retain the existing idempotency storage behavior needed for request replay.
- All connection, provider evidence, pilot, member and privacy queries are workspace-scoped server side.
- Pilot collection requires explicit versioned consent, can be withdrawn, and rejects content-like attribute names.
- Privacy export/download URLs are one-time, expire in ten minutes and require the requesting owner session.
- Deletion uses one transaction and a preview hash to prevent deleting a changed data set without another preview.
- Reauthentication proof is one-time, purpose-bound and expires in five minutes.
- `View as member` cannot create an impersonation session.
- Teen and viewer APIs remain server-denied for publishing, connections, member management, pilot administration and privacy deletion.
- Rate-limit sandbox execution per workspace/provider to five attempts per hour and one concurrent attempt.
- Log correlation IDs, machine error codes and state transitions, but not post text, draft text, emails, tokens, raw provider bodies or qualitative pilot notes.

## Test Strategy (TDD)

### RED-first workflow

Before implementation, create failing tests derived directly from every acceptance criterion. Do not weaken or skip them after implementation. Tests use fake provider transports for deterministic error classes and real temporary SQLite files for persistence. Live sandbox tests are separately marked `provider_sandbox` and never run in the default suite.

### Feature A tests

- Pure unit tests for provider outcome classification, capability normalization, state transition rules, evidence allowlist and retry eligibility.
- SQLite integration tests for attempt idempotency, immutable successful remote ID, rate-limit time, UNKNOWN reconciliation gate and additive migration.
- Router tests with dependency-injected fake connectors for success, expired token, permission denial, 429 with Retry-After, timeout after send, malformed success, replay and partial success.
- Verify connector call counts: replay 0 additional, selective retry calls only requested failed channel, PUBLISHED 0 calls, UNKNOWN 0 calls until reconcile.
- Playwright: Connections test success; reconnect missing scope; Publish Result partial retry; unknown reconcile flow; console/page errors empty.
- Live provider tests execute the eight checklist scenarios and append sanitized observed results. A missing credential produces pytest skip plus release status BLOCKED, never success.

### Feature B tests

- Unit tests for event schema allowlist/rejection, active-duration calculation, median/rate/missing count, time-saved calculation and decision rules.
- SQLite tests for consent gating, withdrawal unlinking, no direct identifiers in export, safety-blocked GO and migration.
- Router tests for facilitator authorization, cohort size bounds, enrollment, event ingestion, export headers/order and withdrawal.
- Frontend component tests for pilot badge, non-blocking telemetry failure, dashboard states and disabled GO.
- Playwright first-draft timing flow and pilot dashboard export using seeded pseudonymous cohort.

### Feature C tests

- Exhaustive parameterized policy matrix for four roles x seven capability categories.
- Store/router tests for immediate downgrade enforcement, last-owner protection, unauthorized capability lookup, view-as projection and exact visibility mapping.
- Privacy tests with real SQLite transactions: preview hash, reauth expiry/use-once, private idea deletion, published evidence pseudonymization, rollback on injected failure and receipt contents.
- Component tests ensure contributor has no Publish element and sees correct state explanations.
- Playwright member role preview, contributor flow, privacy deletion success/failure, keyboard focus restoration and 200% zoom smoke.

### Acceptance-criterion mapping rule

Test names include the story and criterion sequence, for example `test_us_002_ac_03_unknown_reconciles_before_retry`. Every story has AC-01 happy path, AC-02 edge condition and AC-03 error condition. The development report contains a generated inventory showing 27/27 acceptance criteria mapped to at least one test. The traceability matrix below maps every story at feature level; the test inventory supplies criterion-level file/test names.

### Commands

Supported repository commands:

- Backend targeted: `.venv/bin/python -m pytest tests/test_family_api.py tests/test_family_completion.py tests/test_family_provider_confidence.py tests/test_family_pilot.py tests/test_family_privacy.py -q`
- Backend full: `.venv/bin/python -m pytest`
- Backend lint: `.venv/bin/python -m ruff check .`
- Frontend install: `cd frontend && npm ci`
- Frontend tests: `cd frontend && npm test`
- Frontend lint: `cd frontend && npm run lint`
- Frontend type-check and production build: `cd frontend && npm run build`
- Playwright provision: `cd frontend && npx playwright install --with-deps chromium`
- Family E2E: `cd frontend && npx playwright test e2e/family.spec.ts --project=chromium`
- All E2E: `cd frontend && npx playwright test --project=chromium`
- Backend startup: `.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8099`
- Frontend startup: `cd frontend && npm run dev -- --host 127.0.0.1 --port 5173`
- Smoke: HTTP 200 from `/health`, frontend `/`, and authenticated family session fixture; no startup traceback.

The development environment creates `.venv` outside final packaging or removes it before delivery. If the lab gate scripts are supplied outside this archive, run: `tdd-gate-v3.sh`, `bdd-gate.sh`, `security-gate.sh`, `doc-sync-check.sh`, `ui-gate.sh`, and `git-push-verify.sh`. If they remain unavailable, the phase is BLOCKED by lab policy and must not mark them passed.

### Objective gates

- Backend full suite: exit 0, zero failures/errors.
- Frontend Vitest: exit 0, zero failures.
- Ruff and ESLint: exit 0, zero warnings/errors.
- Production build/type-check: exit 0.
- Startup smoke: all required HTTP probes 200 and processes stop cleanly.
- E2E: zero failed tests and zero console/page errors; no critical accessibility violations.
- Changed/new Python modules and extracted frontend family modules: >=90% line coverage; all security/state branches listed above exercised.
- Live sandbox: both provider successes plus all failure/idempotency/partial scenarios observed, or release remains BLOCKED.

## Documentation Deliverables

- `README.md`: Family paid-beta workflow, immediate-only publishing statement, Provider Confidence Center, pilot opt-in/privacy, role capability summary, setup and verification commands.
- `CHANGELOG.md`: additive APIs/tables, connection/reconciliation behavior, pilot instrumentation, privacy operations, Activity rename/route alias, test counts and explicitly blocked live evidence if applicable.
- `docs/family-workspace.md`: complete screen/role/state flow, exact visibility vocabulary, recovery matrix and privacy lifecycle.
- `docs/provider-sandbox-checklist.md`: prerequisites, exact commands/process, eight scenarios, expected classifications, cleanup and evidence redaction.
- `docs/provider-sandbox-results.md` plus existing CSV: dated observed evidence, environment/app aliases, scenario result, remote ID hash, duplicate check and unresolved states; no secrets.
- `docs/family-pilot.md`: consent, event dictionary, facilitator workflow, metric formulas, withdrawal/deletion and go/no-go rule.
- `docs/api-overview.md`: all new family connection, attempt, pilot, capability and privacy endpoints with request/response/error examples.
- `FEATURES-DONE.md`: mark only actually implemented and verified items; distinguish automated, live-sandbox and pilot-field evidence.
- `development-report.md`: scope, architecture, files, migrations, RED/GREEN evidence, 27-criterion traceability, targeted/full command outputs, coverage, accessibility, screenshots, lab gates, live provider outcome, blocks, known limitations and suggested commit.
- `family-pilot-results.csv` and `provider-sandbox-results.csv`: retain headers and append only real observed data. Never fabricate rows.

## Expected File Changes

**Add:**

- `src/family/permissions.py`
- `src/family/visibility.py`
- `src/family/provider_verification.py`
- `src/family/connections.py`
- `src/family/pilot.py`
- `src/family/privacy.py`
- `src/services/family_publish.py`
- `frontend/src/family/FamilyApp.tsx`
- `frontend/src/family/Home.tsx`
- `frontend/src/family/Connections.tsx`
- `frontend/src/family/Publish.tsx`
- `frontend/src/family/Members.tsx`
- `frontend/src/family/Privacy.tsx`
- `frontend/src/family/PilotAdmin.tsx`
- `frontend/src/family/components.tsx`
- `frontend/src/family/api.ts`
- `frontend/src/family/types.ts`
- `frontend/src/family/family.test.tsx`
- `frontend/e2e/family.spec.ts`
- `tests/test_family_provider_confidence.py`
- `tests/test_family_pilot.py`
- `tests/test_family_privacy.py`
- `docs/provider-sandbox-results.md`

**Modify:**

- `src/family/store.py`
- `src/family/__init__.py`
- `src/routers/family.py`
- `src/config.py`
- `frontend/src/family.tsx` (compatibility export)
- `frontend/src/main.tsx`
- `frontend/src/styles.css`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/playwright.config.ts`
- `README.md`
- `CHANGELOG.md`
- `docs/family-workspace.md`
- `docs/family-pilot.md`
- `docs/provider-sandbox-checklist.md`
- `docs/api-overview.md`
- `FEATURES-DONE.md`
- `development-report.md`
- result CSVs only when real observations exist.

No existing unrelated module is reformatted or rewritten.

## Traceability Matrix

| Research need | Research evidence | User story id (US-xxx) | Planned requirement | Acceptance criterion | Planned implementation location | Planned test evidence | Priority |
|---|---|---|---|---|---|---|---|
| Provider readiness is unproved | Real LinkedIn/X credentials were absent; competitors monetize reliable publishing | US-001 | Provider sandbox attempt and evidence record | Configured sandbox test returns one classified attempt and a confirmed remote ID only on success | `src/family/provider_verification.py; src/routers/family.py` | unit provider classifier; SQLite integration; Playwright Connections flow | P0 |
| Partial success must not duplicate posts | Existing per-channel delivery/idempotency semantics and required sandbox matrix | US-002 | Selective retry and reconcile-before-retry | Only RETRYABLE/FAILED channels are called; PUBLISHED remote IDs and attempt counts remain unchanged | `src/family/store.py; src/services/family_publish.py; frontend/src/family.tsx` | connector fake integration; real sandbox evidence; Playwright Publish Result | P0 |
| Adults need self-service recovery | Expired-token and permission scenarios are required but unproved | US-003 | Capability-aware connection recovery | Reconnect remains incomplete until required capabilities pass; OAuth state failures make no connection change | `src/family/connections.py; src/routers/family.py; frontend/src/family.tsx` | OAuth callback tests; scope parser tests; browser reconnect flow | P0 |
| Time to first value is not measured | SMBs report content freshness/time pressure; pilot target is <=10 minutes | US-004 | Privacy-preserving activation events | First saved useful draft records elapsed seconds without draft text; median is calculable | `src/family/pilot.py; src/family/store.py; frontend/src/family.tsx` | event payload unit tests; real SQLite funnel test; component test | P0 |
| Teen next action and publish boundary need field proof | Parent-teen research favors transparent rules; existing role blocks publish | US-005 | Role-aware guided Home and measured comprehension task | Teen DOM and API expose no publish action; direct request returns 403 and no batch | `src/family/store.py; src/routers/family.py; frontend/src/family.tsx` | role matrix tests; component DOM test; Playwright teen flow | P0 |
| Pilot evidence is empty | Existing 5-10 household protocol defines measurable go/no-go targets | US-006 | Consent-based pilot cohort, metrics and CSV export | Export is pseudonymous, excludes content, shows denominators/missing values, and safety incidents block GO | `src/family/pilot.py; src/routers/family.py; frontend/src/family.tsx` | aggregation unit tests; export schema integration; admin browser flow | P0 |
| Role labels do not fully explain effective authority | Family research warns against opaque control and surveillance | US-007 | Effective capability matrix and role-change impact preview | Seven capability categories render; server enforces immediately; last owner remains protected | `src/family/permissions.py; src/family/store.py; frontend/src/family.tsx` | permission matrix unit tests; session revocation integration; Members UI test | P1 |
| Private labels lack lifecycle controls | FTC/ICO emphasize parental control, minimization and privacy defaults | US-008 | Member data export/deletion with retention receipt | Eligible personal data is removed/pseudonymized; immutable publication evidence is minimized and explained | `src/family/privacy.py; src/family/store.py; src/routers/family.py; frontend/src/family.tsx` | deletion transaction and retention tests; reauth failure; Privacy UI E2E | P1 |
| Private, approved and public can be confused | Pilot requires state comprehension; provider UNKNOWN must not appear public | US-009 | Shared visibility-state model and explanations | Private, Approved, Public and Verification required are distinct for every role | `src/family/visibility.py; frontend/src/family.tsx` | state mapper unit tests; component labels; Playwright contributor flow | P1 |

## Risks and Mitigations

- **Provider sandbox cannot emulate every error:** use provider-approved means and test accounts; never intentionally compromise credentials. Where a real rate limit/expired token cannot be safely induced, record BLOCKED and retain deterministic fake-server integration evidence separately.
- **Unknown-state reconciliation unsupported:** preserve UNKNOWN, show manual verification, block automatic retry. Do not downgrade ambiguity to failure.
- **OAuth differences:** isolate provider-specific callbacks/capabilities behind `connections.py`; test state/PKCE and redaction independently.
- **SQLite schema growth:** idempotent migrations, fixture migration tests and startup fail-fast. Keep transactions short around external calls.
- **Pilot data becomes surveillance:** explicit opt-in, narrow event allowlist, no content, transparent badge, withdrawal and retention.
- **Deletion conflicts with publication audit:** pseudonymize actor linkage and retain only minimal reasoned evidence; explain in preview and receipt.
- **Scope pressure:** no scheduling, billing, new provider or design editor work in this pass.
- **Browser availability:** pin `@playwright/test`, provision Chromium in CI with an explicit cache and verify before tests; inability to provision blocks UI release evidence.
- **Lab scripts absent:** obtain them from the lab environment. Absence is BLOCKED, not waived.
- **Git metadata absent from transport:** development must run in the actual repository/branch with remote configured; commit/push verification cannot be fabricated in a detached archive.

## Definition of Done

- [ ] All three selected features are complete, integrated and contain no facade, synthetic provider success or placeholder UI.
- [ ] US-001 through US-009 are implemented with all 27 acceptance criteria mapped to passing tests.
- [ ] Credential presence alone never produces Healthy; provider proof is evidence-backed.
- [ ] Initial publish, partial success, selective retry and reconcile-before-retry work end to end.
- [ ] Live approved LinkedIn and X sandbox accounts complete the required scenario matrix, or release is explicitly BLOCKED.
- [ ] Pilot collection is opt-in, content-free, pseudonymous, withdrawable and exports correct metrics/denominators.
- [ ] Critical incidents force `BLOCKED_SAFETY`; GO cannot bypass the rule.
- [ ] All roles display and enforce the same capability policy; teen/viewer forbidden actions are server denied.
- [ ] Visibility labels distinguish Private, Approved, Public, Partial, Failed and Verification required.
- [ ] Privacy preview, reauthentication, transaction, pseudonymization and receipt flows pass.
- [ ] Family UI contains no scheduling choice; Calendar is presented as Activity with compatibility alias.
- [ ] Targeted backend tests pass.
- [ ] Full backend suite passes with zero failures/errors.
- [ ] Frontend tests pass with zero failures.
- [ ] Ruff and ESLint pass with zero findings.
- [ ] TypeScript check and production Vite build pass.
- [ ] Backend and frontend startup smoke tests pass.
- [ ] Full Chromium family E2E passes with zero critical failures, console errors or page errors.
- [ ] Automated accessibility checks have zero critical/serious violations; keyboard, focus, reduced-motion, mobile and 200% zoom checks are recorded.
- [ ] Changed/new modules reach at least 90% line coverage.
- [ ] `tdd-gate-v3.sh`, `bdd-gate.sh`, `security-gate.sh`, `doc-sync-check.sh`, and `ui-gate.sh` pass in the lab environment.
- [ ] README, CHANGELOG, API docs, `FEATURES-DONE.md`, sandbox/pilot docs and `development-report.md` match observed behavior.
- [ ] No token, credential, authorization header, personal test account identifier, private draft or raw provider body appears in repository artifacts or logs.
- [ ] No `.venv`, `node_modules`, `dist`, coverage, Playwright reports, screenshots containing personal data, runtime DB, credentials, caches or scratch files enter the final package unless pre-existing intentional repository assets are explicitly preserved.
- [ ] Every requirement is traceable to implementation and test evidence.
- [ ] Changes are committed and pushed to the configured repository remote.
- [ ] `git-push-verify.sh` passes and the verified commit hash is recorded.
- [ ] The complete project is repackaged, ZIP integrity-tested, listed, separately extracted and checked for required files and root layout.
