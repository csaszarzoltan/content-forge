# Implementation Plan

## Executive Summary

This pass converts ContentForge's strongest existing workflow primitives into a coherent **Family Creator vertical slice**. It selects exactly three integrated features: (1) adult-owned family workspaces with role-aware Home and navigation, (2) guardian review with an exact-revision publish gate, and (3) a four-step goal-based create-to-publish journey with mobile idea capture. Together they satisfy US-001 through US-009 from `research-findings.md` and address the core research finding that the current product is visually coherent but exposes expert modules before delivering a simple success.

The implementation reuses FastAPI, React 19, TypeScript, SQLite-backed `ContentOpsStore`, revision-bound approvals, selective publish retry, and the existing green design language. It does not rewrite the frontend, add an external state library, add new social connectors, or create independent accounts for young children. Family roles are server-enforced, not cosmetic. Existing expert hash routes and APIs remain available to current behavior; authenticated family mode adds a simplified route set and additive `/api/v1/family/*` contracts.

## Current-State Validation

- The research matches the project. `frontend/src/navigation.ts` contains thirteen route concepts, while `frontend/src/main.tsx` renders a fixed professional shell. Video deliberately uses a five-step wizard and demonstrates that staged UX fits the stack.
- `src/product_ops.py` already provides durable campaigns, assets, immutable revisions, revision-bound approvals, audit events, publish batches, per-channel delivery states, and selective retry. These are the correct foundations for the selected scope.
- `src/routers/workspaces.py` exposes campaign, asset, approval, overview, and publish-batch contracts, but most are not uniformly authenticated or tenant-scoped. `src/models/user.py` has only global `user/admin` roles and optional `organization_id`; it cannot express family membership safely.
- The current React shell has loading, empty, and alert patterns, but no first-run onboarding, project switcher, server-driven permissions, adult-only navigation, mobile bottom navigation, or usage-aware family Home.
- Existing tests establish backend, component, and limited Playwright patterns. The repository includes `scripts/run_backend.py`, frontend `test`, `lint`, and `build` commands, and Python pytest/ruff configuration. Lab gate scripts are policy commands supplied by the Micro-SaaS Lab harness rather than files in this archive.
- The research report contains nine actionable stories. This plan retains all IDs and sharpens each criterion to API states, limits, permissions, and observable UI results.

## Research Priorities

1. Reduce first-use cognitive load by replacing the default expert feature map with a role-aware outcome path.
2. Turn revision approval and selective retry into a family trust promise: contributors cannot publish, adults approve the exact version, and successes are never duplicated.
3. Create first-session value through goal templates and a preview-first flow.
4. Make mobile contribution safe and bounded.
5. Preserve expert functionality through progressive disclosure rather than removal.

Evidence is documented in `research-findings.md`, especially the Current-State Gap Analysis, Validated Demand Signals, and Differentiation Opportunities sections.

## Selected Scope for This Pass

### Feature A: Family Workspace and Guided Home

Satisfies US-001, US-002, and US-003. Adds adult-owned family workspaces, invitations, server-enforced memberships, a permission/session endpoint, a five-item family navigation, and a Home that selects one next action from real workflow state.

### Feature B: Guardian Review and Safe Publishing

Satisfies US-004, US-005, and US-006. Extends existing revision-bound approval with contributor notes, stale-request display, adult decision rules, and a mandatory current-revision approval check before family publish-batch creation.

### Feature C: Simple Create-to-Publish Journey

Satisfies US-007, US-008, and US-009. Adds a four-step goal wizard, transaction-safe campaign/asset creation, mobile private idea capture, and an integrated publish result/recovery experience.

The coherent end-to-end slice is: adult creates family workspace -> contributor joins/captures idea -> adult creates or edits draft -> contributor submits -> adult reviews exact revision -> adult publishes -> partial failure selectively retries.

## Deferred Scope and Rationale

1. **Transparent usage meter and spend caps:** defer to the next monetization pass because no billing/credit ledger exists; prerequisite is metering generation and video costs.
2. **Weekly value report:** defer until activation and workflow events have at least four weeks of trustworthy data.
3. **Privacy-safe media vault:** this pass supports private idea attachments only; full rights metadata, retention policy UI, moderation, and asset reuse are a P2 privacy phase.
4. **Younger-child independent accounts:** explicitly deferred pending legal/safeguarding review and parental-consent design. Young children may participate only through an adult session.
5. **Native mobile application:** responsive PWA-compatible web behavior is sufficient for this pass.
6. **New social networks:** current LinkedIn and X boundaries remain. Reliability precedes breadth.
7. **Expert module redesign:** expert routes remain compatible; only navigation defaults and family wrappers change.
8. **Advanced inline comments and rich-text diff:** this pass includes plain text revision diff and decision reason. Annotation is a later collaboration phase.
9. **External email delivery for invitations/notifications:** invitation links and in-app tasks are in scope; transactional email requires provider/privacy configuration and is deferred.

## User Stories (BDD)

```json
[
  {
    "id": "US-001",
    "epic": "Family Workspace and Guided Home",
    "role": "parent owner",
    "action": "create an adult-owned family workspace and assign bounded roles",
    "benefit": "each family member sees only appropriate actions",
    "story": "As a parent owner, I want to create an adult-owned family workspace and assign bounded roles, so that each family member sees only appropriate actions.",
    "gui_flow": [
      "User signs in and opens Welcome -> sees Family Creator and Family Business choices plus a 3-minute estimate",
      "User selects a family mode -> setup shows workspace name, adult-owner notice, and privacy summary",
      "User enters a unique workspace name and continues -> member step shows Adult collaborator, Teen contributor, and Viewer role cards",
      "User adds an optional member or selects Skip for now -> permission summary lists allowed and blocked actions",
      "User selects Finish setup -> workspace is persisted and Home opens with a starter project card and one Next action",
      "User refreshes Home -> the same workspace, role, and setup progress remain visible"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "an authenticated user has no family workspace",
        "when": "they submit a 2-80 character name and choose a family mode",
        "then": "the API creates exactly one workspace with the user as ADULT_OWNER and returns Home within one redirect"
      },
      {
        "type": "given",
        "text": "the owner skips member invitation",
        "when": "they finish setup",
        "then": "Home loads with a starter project action and setup completeness is 75%, not a blank member panel"
      },
      {
        "type": "given",
        "text": "workspace creation times out after submission",
        "when": "the user selects Retry",
        "then": "the same idempotency key is reused, no duplicate workspace exists, and all entered values remain populated"
      }
    ]
  },
  {
    "id": "US-002",
    "epic": "Family Workspace and Guided Home",
    "role": "teen contributor",
    "action": "join an invited workspace without access to adult controls",
    "benefit": "I can contribute without seeing billing, credentials, or direct publishing",
    "story": "As a teen contributor, I want to join an invited workspace without access to adult controls, so that I can contribute without seeing billing, credentials, or direct publishing.",
    "gui_flow": [
      "Teen opens an invitation link -> sees workspace name, inviter display name, role, and expiry",
      "Teen signs in or registers -> invitation screen returns with no lost state",
      "Teen selects Join workspace -> membership is created and a success notice names the permitted actions",
      "Teen opens Home -> navigation contains Home, Create, Projects, Review, and Calendar only when applicable",
      "Teen opens More -> Billing, Connections, Admin, member role editing, and direct Publish are absent",
      "Teen enters the invitation URL again -> sees Already joined and a Go to Home action"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a valid unexpired TEEN_CONTRIBUTOR invitation belongs to the signed-in email",
        "when": "the user accepts it",
        "then": "one active membership is created and restricted navigation is returned by the session endpoint"
      },
      {
        "type": "given",
        "text": "the invitation was already accepted by the same user",
        "when": "the user opens it again",
        "then": "the API returns membership state without a second row and the UI offers Go to Home"
      },
      {
        "type": "given",
        "text": "the invitation is expired, revoked, or for another signed-in email",
        "when": "the user attempts acceptance",
        "then": "the API returns 410 or 403, creates no membership, and the UI explains how to ask the owner for a new invitation"
      }
    ]
  },
  {
    "id": "US-003",
    "epic": "Family Workspace and Guided Home",
    "role": "parent owner",
    "action": "switch projects and immediately see the next family action",
    "benefit": "I can coordinate work without searching across expert modules",
    "story": "As a parent owner, I want to switch projects and immediately see the next family action, so that I can coordinate work without searching across expert modules.",
    "gui_flow": [
      "Owner opens Home -> header shows current workspace and role",
      "Owner opens the project switcher -> sees up to 10 recent projects with status and pending-action count",
      "Owner selects a project -> URL and Home context update without a full page reload",
      "Home loads Next action first, followed by pending reviews, recent drafts, and setup progress",
      "Owner selects the Next action card -> the relevant wizard, editor, or review opens",
      "Owner returns with browser Back -> selected project and scroll position are restored"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the workspace has projects and actionable items",
        "when": "the owner selects a project",
        "then": "Home shows the highest-priority item using review due, publish failure, then incomplete draft ordering"
      },
      {
        "type": "given",
        "text": "the workspace has no projects",
        "when": "Home loads",
        "then": "a Create your first project empty state appears with one primary button labeled Start a project"
      },
      {
        "type": "given",
        "text": "the overview request fails",
        "when": "Home loads",
        "then": "a page-level recovery card shows last successful refresh time, Retry, and no fabricated counts"
      }
    ]
  },
  {
    "id": "US-004",
    "epic": "Guardian Review and Safe Publishing",
    "role": "parent approver",
    "action": "require current-revision adult approval before contributor work can publish",
    "benefit": "nothing becomes public without an adult decision",
    "story": "As a parent approver, I want to require current-revision adult approval before contributor work can publish, so that nothing becomes public without an adult decision.",
    "gui_flow": [
      "Parent opens a project -> publish gate shows Review required and the current revision number",
      "Parent selects Open review -> sees author, channel preview, exact revision, warnings, and contributor note",
      "Parent compares with the previous revision -> additions and removals use text labels as well as color",
      "Parent selects Approve current version -> optional note field and decision confirmation appear",
      "Parent confirms Approve -> audit entry is recorded and project shows Approved vN",
      "Parent selects Publish -> confirmation lists only approved revision, destinations, and schedule"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a contributor-created asset has a pending approval for its current revision",
        "when": "an ADULT_OWNER or ADULT_COLLABORATOR approves",
        "then": "the approval records reviewer, reason, timestamp, revision number, and changes asset state to APPROVED"
      },
      {
        "type": "given",
        "text": "an asset changes after approval",
        "when": "any member saves a new revision",
        "then": "the prior approval becomes SUPERSEDED immediately and publish returns 409 approval_required_for_current_revision"
      },
      {
        "type": "given",
        "text": "a contributor calls the publish endpoint directly",
        "when": "authorization is evaluated",
        "then": "the API returns 403 contributor_cannot_publish and creates no batch or delivery"
      }
    ]
  },
  {
    "id": "US-005",
    "epic": "Guardian Review and Safe Publishing",
    "role": "teen contributor",
    "action": "submit a draft and note for adult review",
    "benefit": "I can hand off work without accidental publication",
    "story": "As a teen contributor, I want to submit a draft and note for adult review, so that I can hand off work without accidental publication.",
    "gui_flow": [
      "Teen opens a draft -> editor header shows Draft vN and Submit for review, never Publish",
      "Teen edits content -> autosave status announces Saving then Saved vN",
      "Teen selects Submit for review -> sheet asks for a 0-500 character note and shows the receiving adult",
      "Teen adds a note and confirms -> exact revision is locked into a pending approval request",
      "Success screen shows Waiting for review, approver name, and Continue editing warning",
      "Teen edits after submission -> confirmation explains that the pending request will be superseded before saving"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a contributor has an editable non-empty current revision",
        "when": "they submit it with an optional note",
        "then": "one pending approval is created for that revision and Home shows Waiting for review"
      },
      {
        "type": "given",
        "text": "a pending request already exists for the same revision",
        "when": "the contributor submits again",
        "then": "the API returns the existing request and does not notify the approver twice"
      },
      {
        "type": "given",
        "text": "autosave or submission fails",
        "when": "the contributor retries",
        "then": "draft text and note remain local, no duplicate revision or approval is created, and the failing step is named"
      }
    ]
  },
  {
    "id": "US-006",
    "epic": "Guardian Review and Safe Publishing",
    "role": "parent approver",
    "action": "review differences and request measurable changes",
    "benefit": "I can make a confident decision and the contributor knows what to fix",
    "story": "As a parent approver, I want to review differences and request measurable changes, so that I can make a confident decision and the contributor knows what to fix.",
    "gui_flow": [
      "Parent opens Review -> queue cards show title, contributor, channel, age, risk, and revision",
      "Parent opens a card -> responsive review screen shows preview and decision panel",
      "Parent selects Changes -> required reason field appears with 10-1000 character counter",
      "Parent enters a reason and confirms -> decision is saved against the exact revision",
      "Contributor Home shows Needs changes and the parent's reason",
      "Contributor selects Edit draft -> editor opens the asset and no publish control is shown"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a pending current-revision request is open",
        "when": "an adult enters at least 10 characters and requests changes",
        "then": "approval becomes NEEDS_CHANGES, asset becomes IN_EDITING, and the reason appears to the contributor"
      },
      {
        "type": "given",
        "text": "the request references an older revision",
        "when": "the adult opens it",
        "then": "the decision buttons are disabled and the screen labels it Superseded with a link to the current request"
      },
      {
        "type": "given",
        "text": "the decision request fails",
        "when": "the adult retries",
        "then": "the typed reason remains, the action is not duplicated, and the latest server state is re-fetched before a second decision"
      }
    ]
  },
  {
    "id": "US-007",
    "epic": "Simple Create-to-Publish Journey",
    "role": "parent creator",
    "action": "start a project from a goal-based template",
    "benefit": "I can reach a useful draft in the first session",
    "story": "As a parent creator, I want to start a project from a goal-based template, so that I can reach a useful draft in the first session.",
    "gui_flow": [
      "User opens Home and selects Start a project -> goal cards show Promote our shop, Share a family project, and Weekly update",
      "User selects a goal -> wizard shows step 1 of 4 and asks project name and audience",
      "User continues -> message step asks key point, optional call to action, and source notes",
      "User continues -> channel step uses checkboxes for LinkedIn and X and shows length guidance",
      "User selects Create draft -> a progress panel names Creating project, Drafting, and Checking",
      "Wizard completes -> preview-first editor opens with project, asset revision 1, and Review draft action"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "an adult enters valid fields and selects at least one supported channel",
        "when": "they create the draft",
        "then": "one campaign and one asset per selected channel are created transactionally and the editor opens within the completed response"
      },
      {
        "type": "given",
        "text": "the user leaves optional source notes and call to action blank",
        "when": "they continue",
        "then": "the wizard proceeds without validation errors and preview labels optional omissions"
      },
      {
        "type": "given",
        "text": "generation fails after campaign creation",
        "when": "the user sees recovery",
        "then": "the campaign remains visible as Draft, failed asset creation is not duplicated, and Retry resumes from the named failed stage"
      }
    ]
  },
  {
    "id": "US-008",
    "epic": "Simple Create-to-Publish Journey",
    "role": "teen contributor",
    "action": "capture a text or image idea from a phone",
    "benefit": "our family can collect ideas where they happen",
    "story": "As a teen contributor, I want to capture a text or image idea from a phone, so that our family can collect ideas where they happen.",
    "gui_flow": [
      "Teen opens Create on a viewport below 768 px -> bottom navigation remains labeled and touch targets are at least 44 px high",
      "Teen selects Quick idea -> sheet offers Text note and Image with caption",
      "Teen enters up to 2000 characters or chooses one validated image -> local preview appears before upload",
      "Teen chooses a project and selects Save idea -> progress announces upload and save state",
      "Success view shows Added to project and Ask for draft action",
      "Teen selects Ask for draft -> adult Home receives a contributor idea task"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "a contributor supplies text or an allowed image under 10 MB",
        "when": "they save to an accessible project",
        "then": "the idea is persisted with author, project, private state, and created time and becomes visible to adults"
      },
      {
        "type": "given",
        "text": "the device goes offline before save",
        "when": "the user selects Save idea",
        "then": "the idea remains in an explicit On this device queue and submits once after reconnection without duplication"
      },
      {
        "type": "given",
        "text": "the image type, size, or upload scan is invalid",
        "when": "the user selects it",
        "then": "the UI rejects it before project attachment, names the allowed formats and 10 MB limit, and stores no public URL"
      }
    ]
  },
  {
    "id": "US-009",
    "epic": "Simple Create-to-Publish Journey",
    "role": "family business owner",
    "action": "complete review and publish without navigating expert modules",
    "benefit": "the subscription saves time instead of adding workflow overhead",
    "story": "As a family business owner, I want to complete review and publish without navigating expert modules, so that the subscription saves time instead of adding workflow overhead.",
    "gui_flow": [
      "Owner opens Home -> Next action says Review weekly update",
      "Owner opens the item -> preview-first editor shows blocking issues before suggestions",
      "Owner resolves or explicitly leaves non-blocking suggestions -> Review current version becomes enabled",
      "Owner approves the exact revision -> primary action changes to Publish",
      "Owner selects Publish -> confirmation lists channels, account names, revision, and immediate or scheduled time",
      "Owner confirms -> progress shows one row per channel",
      "Completion screen shows Published, Partial success, or Needs attention with View result and Retry failed channels"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the current revision is adult-approved and all selected connections are valid",
        "when": "the owner confirms publish",
        "then": "one idempotent batch is created and each channel shows a terminal or retryable status"
      },
      {
        "type": "given",
        "text": "one channel succeeds and one fails",
        "when": "publishing completes",
        "then": "the success is preserved, status is Partial success, and Retry failed channels targets only the failed channel"
      },
      {
        "type": "given",
        "text": "the connection expires or publish state is unknown",
        "when": "the owner confirms or retries",
        "then": "the UI shows Reconnect or Check status first, and the backend never sends a second post until reconciliation clears the unknown state"
      }
    ]
  }
]
```

## Product Requirements

### A. Family Workspace and Guided Home

**Research problem:** the same expert navigation is shown to every user; the project lacks household identity and bounded roles.

**Inputs and validation**
- Workspace name: trimmed UTF-8, 2-80 characters.
- Mode: `FAMILY_CREATOR` or `FAMILY_BUSINESS`.
- Roles: `ADULT_OWNER`, `ADULT_COLLABORATOR`, `TEEN_CONTRIBUTOR`, `VIEWER`.
- Invitation email: normalized valid email, maximum 255 characters; cannot invite an existing active member twice.
- Invitation expiry: fixed seven days; token stored as SHA-256 hash, raw token returned only once.
- All mutation endpoints accept `Idempotency-Key`, 16-128 visible ASCII characters. Reuse with a different request body returns 409.

**Business rules**
- Creator becomes the sole `ADULT_OWNER`; at least one active owner must always remain.
- Only owners manage membership and invitations. Adult collaborators review and publish. Teen contributors create/edit/submit but cannot manage members, connections, billing, admin, or publish. Viewers have read-only project access.
- Access checks occur on the server for every family endpoint and referenced entity.
- Home next-action ordering is: current user's pending review -> unknown/failed publication -> needs-changes draft -> incomplete draft -> setup task -> start project.
- Family navigation is server-derived from permissions. Hiding controls is not authorization.

**Outputs and failure behavior**
- Session response includes current workspace, membership role, permission strings, navigation items, and onboarding completion.
- Invalid/revoked/expired invitations never reveal whether an unrelated email is registered.
- Empty Home always returns a typed empty state and primary action.
- Existing users without a family workspace see Welcome; existing expert behavior is not deleted.

**Acceptance:** all criteria in US-001 to US-003; restricted endpoints return 403; tenant crossing returns 404; duplicate mutation protection is verified with real SQLite I/O.

**Non-goals:** billing, child age verification, independent younger-child accounts, email delivery, SSO.

### B. Guardian Review and Safe Publishing

**Research problem:** approval demand is validated, but current list cards provide weak context and family safety is not enforced at publish time.

**Inputs and validation**
- Review note: optional, maximum 500 characters.
- Decision: `APPROVED` or `NEEDS_CHANGES`; `REJECTED` remains supported by legacy expert API but is not shown in family UI.
- Changes reason: required for `NEEDS_CHANGES`, trimmed 10-1000 characters. Approval note is optional, maximum 1000.
- Publish request references asset ID, exact revision, channels, and optional RFC 3339 scheduled time. Family UI supports now or future times only.

**Business rules**
- Approval is bound to the current immutable asset revision.
- Saving any new revision supersedes pending and approved requests, as existing store behavior already intends.
- Teen/viewer publish always returns 403. Adult publish returns 409 unless an approved request matches the current version.
- One pending request per asset/revision; repeat submission returns existing request.
- Decisions are idempotent. A second different decision returns 409.
- Publish creates one batch per idempotency key. Retry only failed or retryable channels and preserves successful delivery rows.

**Outputs and failure behavior**
- Review detail includes project, asset title, channel, requester display name, current and requested revisions, unified text diff, risk/findings, note, status, and audit timestamps.
- Stale requests are readable but not actionable.
- Failed decisions preserve typed reasons and refresh server state before retry.

**Acceptance:** all criteria in US-004 to US-006, plus direct API authorization tests and stale-revision publish tests.

**Non-goals:** pixel-level visual diff, real-time co-editing, legal-signature workflows, email approvals.

### C. Simple Create-to-Publish Journey

**Research problem:** campaign creation is implementation-shaped and users must navigate multiple modules before value.

**Inputs and validation**
- Goal: `PROMOTE_SHOP`, `SHARE_PROJECT`, or `WEEKLY_UPDATE`.
- Project name: 2-80 characters; audience 2-160; key message 10-2000; optional CTA 0-240; source notes 0-5000.
- Channels: one or both of `linkedin`, `twitter`; no free-text channel input.
- Idea text: 1-2000; image: JPEG, PNG, or WebP, maximum 10 MiB; caption maximum 500.
- The first pass uses deterministic template assembly for the draft. It must work without an LLM key and must not silently incur external cost. Existing generation services may be invoked later from the editor, outside this pass.

**Business rules**
- Journey completion transactionally creates the campaign and one asset per channel, each at revision 1.
- Template output clearly marks optional fields and channel-specific length warnings; it never truncates user content silently.
- Ideas are private to the workspace/project and never publishable objects.
- Mobile offline text/image metadata is queued in IndexedDB with a client UUID; binary image queue is limited to one 10 MiB item per pending idea. Server idempotency prevents duplicate saves.
- Family publish uses Feature B's gate and existing batch/retry semantics.

**Outputs and failure behavior**
- Journey endpoint returns project and created assets plus `next_url`.
- If asset creation fails, transaction rolls back; if later draft checks fail, project remains `DRAFT` with a named recoverable stage.
- Upload validation occurs client-side and server-side. Server stores assets under configured upload root using generated filenames, never user path components.

**Acceptance:** all criteria in US-007 to US-009; responsive and offline browser tests; transaction rollback and idempotency integration tests.

**Non-goals:** new AI model selection, brand-kit wizard, additional networks, video generation inside onboarding, native background sync guarantee on every browser.

## UI and UX Specification

### Personas and primary journey

- Parent owner on desktop: set up workspace, create weekly project, review, publish, recover.
- Parent collaborator on tablet: review exact revision and schedule.
- Teen contributor on phone: join, capture idea, edit draft, submit for review.
- Viewer: read project and outcomes only.

### Information architecture

Family mode primary navigation order is **Home, Create, Projects, Review, Calendar**. `More` contains Brand, Analytics, Localization, Video, and Transcreate for adults in Expert mode. Connections, Members, Privacy, and Admin are available only from the adult workspace menu. Teen and viewer responses do not include forbidden destinations.

Desktop uses the existing left sidebar at 244 px. Tablet 768-1023 px uses a 72 px rail plus labels in tooltips and an explicit workspace menu. Mobile below 768 px uses a top app bar and fixed five-item bottom navigation with text labels. Content max width is 1200 px; forms max at 720 px; review max at 1400 px.

### Design system decision

Reuse `frontend/src/styles.css` tokens and React components. Add no component-library dependency in this pass because controls are limited and the current stack already has bespoke visual language. Create accessible internal primitives (`Button`, `Field`, `Dialog`, `StatusBadge`, `Skeleton`, `Toast`, `EmptyState`) in `frontend/src/ui/`. Dialog must implement focus trap, Escape close when safe, initial focus, and focus restoration. Do not use remote Google Fonts in family mode; use the current font stack with system fallbacks to avoid a privacy/network dependency.

Add tokens: 4/8/12/16/24/32/48 spacing; 8/12/16 radii; 1/2/3 elevation; semantic colors for info/success/warning/danger with 4.5:1 text contrast; 2 px focus ring with 2 px offset. All touch targets are at least 44 by 44 CSS pixels. At `prefers-reduced-motion: reduce`, transitions become 0 ms except progress state changes, which use non-animated text.

### Global states

- Loading: skeleton matches eventual layout; no indefinite spinner without label.
- Empty: title, one-sentence explanation, one primary CTA.
- Validation: inline message linked by `aria-describedby`; summary receives focus after submit.
- Error: preserve input; name failed stage; Retry and safe Back action.
- Success: `role=status` announcement and explicit next action.
- Disabled: disabled control plus visible prerequisite text.
- Offline: persistent banner and local queue count; no false success claim.
- Partial publish: per-channel rows, successful rows locked, failed rows selectable for retry.

## Screen Inventory and User Flows

### 1. Welcome and Family Setup (`#/welcome`)

**Purpose:** reach an adult-owned workspace in at most five panels.

**Layout:** minimal header with logo and Sign out; centered 720 px step card; progress text “Step N of 4”; footer Back/Continue. Step 1 has two mode cards and one Expert workspace link. Step 2 has name and privacy summary. Step 3 has optional invitation and role cards. Step 4 is a permission summary and Finish setup.

**CTA:** primary `Continue` then `Finish setup`; secondary `Skip for now`; tertiary `Use expert workspace` for adults.

**States:** skeleton while session loads; duplicate-name inline validation; API error card preserving values; completion status leads to Home. Browser Back moves one step and never discards without confirmation.

### 2. Accept Invitation (`#/join/:token`)

**Layout:** workspace summary, inviter, role badge, seven-day expiry, allowed/blocked permission list, privacy notice. Primary `Join workspace`; secondary `Decline`.

**States:** sign-in required retains token in session storage; expired/revoked shows `Ask for a new invitation`; already joined shows `Go to Home`; wrong email shows generic permission error without account disclosure.

### 3. Family Home (`#/home`)

**Layout:** top row workspace switcher, role badge, mobile notification icon. Main column begins with `Next action` hero card. Below: `Waiting for you`, `Recent projects`, `Ideas from family`, and setup checklist. Desktop has a right rail with upcoming calendar and connection health; mobile stacks all blocks.

**CTA:** context-specific hero label, otherwise `Start a project`. Secondary `Capture idea`. Project cards show status, owner, last update, and pending count.

**States:** skeleton cards; no-project empty state; partial panel errors remain isolated; full failure displays last refresh and Retry. No fabricated zero counts.

### 4. Projects (`#/projects`) and Project Detail (`#/projects/:id`)

**Layout:** searchable project cards on list. Detail header has project name, goal, owner, status, and progress. Tabs are Overview, Drafts, Activity. Overview shows next action and family members. Drafts show channel previews and revision state.

**CTA:** `Create draft` for adults, `Add idea` for contributors. `Open review` appears only with permission. `Publish` appears only after current approval.

**States:** forbidden project resolves as not found; empty drafts provide goal-specific create action; stale data conflict offers Refresh before overwrite.

### 5. Goal Wizard (`#/create/project`)

**Layout:** four steps: Goal, Message, Channels, Review. Left desktop rail shows completed steps; mobile uses progress text. Review displays exact values and a generated preview sample per channel.

**CTA:** `Continue`, final `Create draft`; secondary Back; `Save and exit` after step 1.

**States:** field validation; channel length warning is non-blocking; creation progress names three stages; recoverable failure offers `Retry Drafting` or `View project` where safe.

### 6. Quick Idea (`#/create/idea`)

**Layout:** mobile-first segmented control Text/Image, large input, image preview/caption, project selector, privacy badge `Visible only to this family workspace`.

**CTA:** `Save idea`; secondary `Save on this device` while offline. Success actions: `Ask for draft`, `Add another`, `Go to project`.

**States:** image validation before upload; upload progress; scanning/processing label; offline queue; failed upload retains local preview and caption; deletion removes local queued binary.

### 7. Preview-first Editor (`#/projects/:projectId/assets/:assetId`)

**Layout:** header title, channel, revision, autosave status. Desktop has editor left and live preview right; mobile toggles Edit/Preview. Bottom action bar shows `Submit for review` for contributors and `Review current version` for adults. Revision history is secondary drawer.

**States:** autosave Saving/Saved/Needs attention in `aria-live=polite`; conflict blocks save and presents Reload latest/Copy my draft; submission sheet preserves note on error.

### 8. Review Queue (`#/review`) and Review Detail (`#/review/:id`)

**Layout:** filter chips Pending/Needs changes/Completed. Cards include human title, author, channel, age, risk, revision. Detail has preview, change summary, warnings, note, and sticky decision panel. Text diff uses `Added:` and `Removed:` labels.

**CTA:** `Approve current version`; secondary `Request changes`. Stale request has no decision CTA and links to current request.

**States:** empty queue congratulates and links Home; decision validation focuses reason; failure preserves reason; success announces and advances to next queue item only after explicit `Review next`.

### 9. Publish Confirmation and Result (`#/projects/:id/publish`)

**Layout:** confirmation lists revision, approval reviewer/time, destinations/accounts, timing, and immutable summary. Result view shows one row per channel with status, remote link if available, and error recovery.

**CTA:** `Publish now` or `Schedule`; partial result `Retry failed channels`; unknown state `Check status`; expired connection `Reconnect`.

**States:** approval stale disables confirmation; pending action has progress and prevents double submit; partial success never offers retry for successful channels; failure messages redact provider secrets.

### End-to-end happy and recovery flow

Owner completes Welcome -> Home `Start a project` -> Goal Wizard creates LinkedIn and X drafts -> teen captures an idea and edits one draft -> teen submits v2 -> parent Review approves v2 -> Publish creates one batch -> LinkedIn succeeds and X fails -> result says Partial success -> parent retries X only -> both channels show Published. If the approval becomes stale or a network call fails, entered data remains, the exact failed stage is named, and no duplicate workspace, approval, batch, or delivery is created.

### Accessibility verification

Use semantic landmarks (`header`, `nav`, `main`, `aside`), one `h1`, ordered heading levels, native buttons/links, named form controls, status text in addition to color, keyboard-operable switchers, and focus restoration. Add axe checks to every new Playwright flow, keyboard-only smoke tests, 200% zoom screenshots, and reduced-motion emulation.

## Architecture and Technical Design

### Boundaries

- `src/family/permissions.py`: role-permission constants and pure authorization functions.
- `src/family/service.py`: workspace, invitation, Home prioritization, journey transaction, idea and publish-gate orchestration.
- `src/models/family.py`: SQLAlchemy models for family workspaces, memberships, invitations, ideas, and idempotency records.
- `src/schemas/family.py`: all Pydantic request/response contracts.
- `src/routers/family.py`: authenticated `/api/v1/family` endpoints only; no domain SQL.
- Existing `ContentOpsStore` remains the campaign/revision/approval/publish source of truth. Add workspace ownership columns and methods with additive SQLite migration logic. Do not copy campaign logic into family tables.
- Frontend `family-api.ts` owns typed fetch, auth header, idempotency key, and normalized error mapping. `family-session.tsx` provides session/workspace context. Screen files own local form state; no new global data dependency.

### State/data flow

On app start, authenticated family routes fetch `/api/v1/family/session`. Response drives navigation and route guards. Home fetches a workspace-scoped overview. Mutations include idempotency keys and refresh affected resources after success. Autosave uses existing expected-version optimistic concurrency. Offline ideas use IndexedDB and client-generated UUIDs; queued synchronization is explicit and retryable.

### Error/logging

Every family response uses existing FastAPI `{"detail": code}` convention plus optional `message` and `field_errors`. Log structured event name, workspace ID, actor ID, entity ID, outcome, and correlation ID; never log invitation tokens, email beyond a masked form, draft content, upload bytes, credentials, or provider responses. Audit workspace creation, membership changes, invitation acceptance, review submission/decision, publish-gate evaluation, and retry.

### Alternatives rejected

- Reusing global `User.role`: rejected because a user can have different roles in different workspaces.
- Frontend-only role hiding: rejected as insecure.
- New PostgreSQL/Redis infrastructure: rejected for one-pass fit; current SQLite conventions support deterministic tests and additive migration.
- Replacing React or CSS with a framework: rejected as scope without user value.
- LLM-first wizard: rejected because first value must work offline from provider keys and cost must be predictable.

## Data, API, and Compatibility Changes

### New tables

- `family_workspaces(id, name, mode, created_by, created_at, updated_at)`.
- `family_memberships(id, workspace_id, user_id, role, state, joined_at, UNIQUE(workspace_id,user_id))`.
- `family_invitations(id, workspace_id, email_normalized, role, token_hash, state, expires_at, created_by, accepted_by, created_at)`.
- `family_ideas(id, workspace_id, project_id, author_id, client_id, kind, text, caption, asset_path, state, created_at, UNIQUE(workspace_id,client_id))`.
- `idempotency_records(id, workspace_id, actor_id, key, request_hash, response_status, response_json, created_at, UNIQUE(workspace_id,actor_id,key))`.

### Additive ContentOps columns

Add nullable `workspace_id` to campaigns, assets, approvals, publish_batches, and audit_events where absent. Legacy rows remain nullable and accessible through existing expert APIs exactly as before. Family APIs only query matching non-null `workspace_id`. Add `contributor_note` and decision timestamps to approvals. Migration occurs through the project's existing startup/add-column convention and gets real legacy-DB tests.

### Exact API contracts

- `POST /api/v1/family/workspaces` -> 201. Body `{name, mode}`; header `Idempotency-Key`; response `{workspace, membership, next_url}`.
- `GET /api/v1/family/session?workspace_id=` -> `{user, workspace, membership, permissions[], navigation[], onboarding}`.
- `POST /api/v1/family/workspaces/{id}/invitations` -> 201. Body `{email, role}`; returns invitation metadata plus one-time `accept_url` in development/test only. Production logs never include token.
- `GET /api/v1/family/invitations/{token}` -> safe invitation preview.
- `POST /api/v1/family/invitations/{token}/accept` -> membership and workspace.
- `GET /api/v1/family/home?workspace_id=&project_id=` -> typed next action, queues, projects, ideas, setup, last_refreshed_at.
- `POST /api/v1/family/journeys` -> 201. Body includes workspace, goal, project name, audience, message, CTA, notes, channels; header idempotency; response campaign, assets, checks, next_url.
- `POST /api/v1/family/ideas` multipart -> 201; fields workspace_id, project_id, client_id, kind, text, caption, optional file.
- `POST /api/v1/family/assets/{asset_id}/submit-review` -> 201/200 idempotent; body `{note}`; response approval.
- `GET /api/v1/family/reviews` and `GET /api/v1/family/reviews/{id}` -> queue/detail with diff.
- `POST /api/v1/family/reviews/{id}/decision` -> body `{decision, reason}`; response updated review and asset.
- `POST /api/v1/family/publish-batches` -> 201; body `{asset_id, revision_version, channels, publish_at}`; enforces adult and current approval.
- `POST /api/v1/family/publish-batches/{id}/retry` -> 202 with targeted channels only.

Compatibility: existing `/api/v1/campaigns`, asset, approvals, workspace overview, expert routes, and publish APIs keep their request/response forms. Family UI never calls unauthenticated legacy mutation routes. New models are imported in `src/models/__init__.py` and startup registration. OpenAPI documents all new endpoints.

No new runtime dependency is required. Frontend offline queue uses browser IndexedDB directly. Tests may add `@axe-core/playwright` as a dev dependency because accessibility checks are an explicit acceptance requirement.

## Security and Privacy Considerations

- Every family endpoint requires `get_current_user`; object lookup is scoped by active membership before revealing existence.
- Permission matrix is deny-by-default and unit tested exhaustively for all four roles and actions.
- Invitation tokens contain at least 256 bits of randomness, are hashed at rest, expire after seven days, and are single-use/revocable.
- Owners cannot remove/demote the last active owner.
- Teen and viewer roles cannot access connection credentials, billing/admin routes, member administration, raw audit exports, or publish mutations.
- Upload filenames are generated; extension, MIME signature, and 10 MiB cap are checked; SVG is not accepted. Assets remain private and are never mounted as anonymous public files.
- Idempotency and optimistic concurrency prevent duplicate workspace, approval, and publication side effects.
- Error responses and logs redact credentials, invitation tokens, draft bodies, and external provider payloads.
- This pass does not claim COPPA compliance or collect age/date of birth. “Teen contributor” is an adult-invited bounded role. Product copy must not market independent use to children.
- Add privacy copy documenting who can see ideas, how the adult removes a member, and that publishing is adult-controlled.

## Test Strategy (TDD)

### RED-first mapping

Before implementation, create failing tests for every acceptance criterion. Name tests with story and criterion, for example `test_us001_ac1_owner_workspace_persists`. Maintain a machine-readable mapping in test docstrings or parametrized IDs.

### Backend tests

- `tests/test_family_permissions.py`: complete role x permission matrix, last-owner invariant.
- `tests/test_family_store.py`: real temporary SQLite workspace/invitation/idea/idempotency persistence, expiry, uniqueness, legacy migration.
- `tests/test_family_api.py`: auth, tenant isolation, validation, safe 403/404/410 mapping, session navigation.
- `tests/test_family_home.py`: deterministic next-action priority and empty/error shapes.
- `tests/test_family_review_publish.py`: exact-revision approval, supersession, direct contributor publish 403, idempotent decisions/batches, selective retry.
- `tests/test_family_journey.py`: transaction creation per channel, rollback/recovery, deterministic draft templates.
- `tests/test_family_uploads.py`: format/signature/size/path validation and private storage.

Each selected story has happy, edge, and error tests. Changed/new backend modules require at least 90% line coverage when measured by the lab gate; critical permission and gate branches require 100% branch-case enumeration even if repository-wide coverage is lower.

### Frontend tests

- `family-navigation.test.tsx`: server-driven routes and forbidden-item absence.
- `family-setup.test.tsx`: all panels, validation, preserved retry, idempotency header.
- `family-home.test.tsx`: next action, switcher, skeleton, empty and partial error.
- `family-journey.test.tsx`: four-step state, optional fields, progress, recovery.
- `family-idea.test.tsx`: mobile input, validation, offline queue, duplicate prevention.
- `family-review.test.tsx`: queue context, stale disablement, reason validation, decision retry.
- `family-publish.test.tsx`: gate, per-channel progress, partial retry.

### E2E and accessibility

Add `frontend/e2e/family-flow.spec.ts` using a seeded temporary ops database and authenticated test user. Cover full US-001 -> US-009 flow, contributor forbidden direct URL/API, approval supersession, and partial publish retry. Add axe scans for Welcome, Home, Wizard, Editor, Review, and Publish Result; keyboard-only path through setup/review; mobile viewport 390x844; desktop 1440x900; reduced-motion; and 200% zoom screenshot evidence when the runner supports screenshots.

### Commands

During development:

```bash
python -m pytest tests/test_family_permissions.py tests/test_family_store.py tests/test_family_api.py tests/test_family_home.py tests/test_family_review_publish.py tests/test_family_journey.py tests/test_family_uploads.py
ruff check src tests
cd frontend && npm test -- --run
cd frontend && npm run lint
cd frontend && npm run build
```

Startup/E2E, following existing ports and config:

```bash
python scripts/run_backend.py
cd frontend && npm run dev
cd frontend && npx playwright test e2e/family-flow.spec.ts
```

Full regression and lab gates after targeted tests are green:

```bash
python -m pytest
ruff check src tests
cd frontend && npm test
cd frontend && npm run lint
cd frontend && npm run build
tdd-gate-v3.sh
bdd-gate.sh
security-gate.sh
doc-sync-check.sh
ui-gate.sh
git-push-verify.sh
```

The named gate commands are required Micro-SaaS Lab harness entry points. If unavailable in the developer shell, the phase is blocked rather than reported as passing.

Objective pass: zero failing targeted/full tests; zero lint/type/build errors; new E2E green in Chromium; all required gates exit 0; no console/page errors; no serious axe findings; backend starts and `/health` plus `/api/v1/family/session` respond as specified.

## Documentation Deliverables

- `README.md`: add Family Creator value proposition, role table, quick-start journey, privacy boundary, and exact development/E2E commands.
- `CHANGELOG.md`: under Unreleased, list family workspace, safe review/publish gate, journey, mobile idea capture, migration, and tests.
- `docs/family-workspace.md`: roles/permissions, onboarding, invitations, Home prioritization, every family endpoint with examples and errors, privacy and deletion behavior.
- `docs/api-overview.md`: endpoint summary and auth/idempotency requirements.
- `FEATURES-DONE.md`: machine-readable completion entries mapped to US-001 through US-009 and test evidence.
- `development-report.md`: files changed, migrations, architecture decisions, commands/results, gate results, screenshots/artifact paths, known limitations, and commit hash.
- Update any existing OpenAPI/API examples whose behavior is touched; do not document deferred email, billing, or child-account features as shipped.

## Expected File Changes

**Add:** `src/family/__init__.py`, `src/family/permissions.py`, `src/family/service.py`, `src/models/family.py`, `src/schemas/family.py`, `src/routers/family.py`, the seven backend test modules named above, `frontend/src/family-api.ts`, `frontend/src/family-session.tsx`, `frontend/src/family-types.ts`, `frontend/src/ui/*`, `frontend/src/family/FamilySetup.tsx`, `FamilyHome.tsx`, `ProjectList.tsx`, `ProjectDetail.tsx`, `GoalWizard.tsx`, `QuickIdea.tsx`, `FamilyEditor.tsx`, `ReviewQueue.tsx`, `ReviewDetail.tsx`, `PublishFlow.tsx`, corresponding component tests, `frontend/e2e/family-flow.spec.ts`, `docs/family-workspace.md`, and `development-report.md`.

**Modify:** `src/product_ops.py`, `src/main.py`, `src/models/__init__.py`, `frontend/src/main.tsx`, `frontend/src/navigation.ts`, `frontend/src/styles.css`, `frontend/package.json` and lockfile only for axe dev tooling, `README.md`, `CHANGELOG.md`, `docs/api-overview.md`, and `FEATURES-DONE.md`.

Do not modify unrelated feature modules. Keep existing routes and tests green.

## Traceability Matrix

| Research need | Research evidence | User story id | Planned requirement | Acceptance criterion | Planned implementation location | Planned test evidence | Priority |
|---|---|---|---|---|---|---|---|
| Role-appropriate experience | 13 equally weighted routes; child privacy requires bounded roles | US-001 | Adult-owned workspace setup | Create persists once; skip produces useful Home; retry is idempotent | `models/family.py`, `family/service.py`, `FamilySetup.tsx` | `test_family_store.py`, `family-setup.test.tsx`, E2E setup | P0 |
| Restricted contributor access | No current household permissions | US-002 | Server-derived permissions/navigation | Valid join; repeat join idempotent; invalid invite safe | `permissions.py`, `routers/family.py`, `family-session.tsx` | permission matrix, API invitation tests, direct-route E2E | P0 |
| One obvious next action | My Work is generic and IDs lack context | US-003 | Deterministic Family Home priority | priority ordering, empty CTA, honest failure | `service.py`, `FamilyHome.tsx` | `test_family_home.py`, home component tests | P0 |
| Adult-controlled public action | Approval is validated demand and store is revision-bound | US-004 | Current-revision adult approval gate | adult approval audit; edit supersedes; contributor publish 403 | `product_ops.py`, family review/publish services | `test_family_review_publish.py`, E2E gate | P0 |
| Safe contributor handoff | Editor currently offers generic review action | US-005 | Submit exact revision with note | one request; repeated submit idempotent; draft preserved on error | `family/service.py`, `FamilyEditor.tsx` | API/component submission tests | P0 |
| Review clarity | Current queue cards expose asset IDs and risk only | US-006 | Human queue, diff, measurable reason | needs-changes transition; stale disabled; failure retry safe | review schemas/endpoints, `ReviewDetail.tsx` | review API/component/E2E tests | P0 |
| First-session value | Campaign form uses brief and comma channels | US-007 | Four-step goal wizard and deterministic drafts | transactional creation; optional fields; named recovery | journey service/endpoint, `GoalWizard.tsx` | `test_family_journey.py`, wizard tests/E2E | P0 |
| Mobile household contribution | Current mobile sidebar becomes icon-only | US-008 | Private mobile idea and offline queue | valid persist; offline dedupe; invalid image rejected | idea service/API, `QuickIdea.tsx`, IndexedDB helper | upload/store/component/mobile E2E | P0 |
| End-to-end paid value | Existing modules require navigation and partial success is hidden | US-009 | Integrated approval-to-publish result | idempotent batch; partial retry only failed; unknown state reconciles first | family publish endpoint, `PublishFlow.tsx` | review/publish integration and E2E recovery | P0 |

## Risks and Mitigations

- **Two persistence systems:** family user models use SQLAlchemy while workflow uses `ContentOpsStore` SQLite. Mitigate with service boundary, workspace IDs, transaction tests, and no duplicated campaign records. A future pass may consolidate stores.
- **Legacy unauthenticated APIs bypass family rules:** family UI never uses them, but deployment exposure remains. Add a configuration guard that disables legacy mutation routes in family production mode while defaulting to compatibility in tests/development; document the policy.
- **Invitation leakage:** hash tokens, single-use expiry, masked emails, no token logging.
- **Role semantics mistaken for age assurance:** copy explicitly states invited contributor; collect no age data and make no compliance claim.
- **Offline image storage quota:** cap one 10 MiB queued image per idea, surface storage failure, and allow text-only fallback.
- **Scope pressure:** no billing, email, new networks, rich comments, or full media library in this pass.
- **E2E environment drift:** provide deterministic seed fixture and start commands; retain traces on failure.

## Definition of Done

- [ ] Features A, B, and C are complete end-to-end with no facade, hard-coded success, or placeholder data.
- [ ] US-001 through US-009 each have passing happy, edge, and error evidence.
- [ ] Adult/teen/viewer permissions are enforced server-side and tenant isolation tests pass.
- [ ] Current-revision approval is mandatory for family publish and direct contributor publish is blocked.
- [ ] Goal wizard, private idea capture, editor, review, publish, partial retry, and friendly recovery work in the browser.
- [ ] Existing expert routes and current regression tests remain compatible.
- [ ] Targeted tests and full `python -m pytest` pass.
- [ ] Frontend test, lint, TypeScript production build, startup, and Playwright family flow pass.
- [ ] Changed/new modules meet at least 90% line coverage; critical permission matrix is exhaustively tested.
- [ ] axe, keyboard, mobile, reduced-motion, focus, contrast, and 200% zoom verification is recorded.
- [ ] `tdd-gate-v3.sh`, `bdd-gate.sh`, `security-gate.sh`, `doc-sync-check.sh`, and `ui-gate.sh` exit 0.
- [ ] README, CHANGELOG, API guide, `FEATURES-DONE.md`, and `development-report.md` match actual behavior.
- [ ] Migration is tested against a copy of the existing database and rollback/backout instructions are in the development report.
- [ ] No credentials, raw invitation tokens, caches, build outputs, database copies, uploads, or stray artifacts are committed.
- [ ] Every criterion is traceable to implementation and test evidence.
- [ ] Git working tree is reviewed, changes are committed and pushed, and `git-push-verify.sh` exits 0.
- [ ] The complete project is packaged without an extra directory level and ZIP integrity/extraction verification passes.
