# Research Findings

## Executive Summary

ContentForge now contains a genuine **Family Creator / Family Business vertical slice**, not merely a concept. The archive implements adult-owned workspaces, role-bound invitations, private idea capture, exact-revision review, adult-only publishing, idempotent channel deliveries, connection recovery, weekly summaries, responsive family navigation, and immediate-only paid-beta publishing. The implementation sits on a broad FastAPI and React content-operations platform. Verified project evidence includes `src/family/store.py`, `src/routers/family.py`, `frontend/src/family.tsx`, `tests/test_family_api.py`, `tests/test_family_completion.py`, `docs/family-workspace.md`, and the release evidence in `development-report.md`.

The market evidence supports the problem more strongly than the exact positioning. Small and mid-sized businesses report that keeping social content fresh is difficult, while current tools split value between design, scheduling, approvals, and analytics. Verizon's 2025 survey of 600 SMB decision-makers found that 76% believed social media positively affected performance, but 54% struggled to keep content fresh and follow trends. Buffer, Planable, Metricool, Canva, Adobe Express, Publer, and Hootsuite all sell pieces of the workflow, yet none is positioned around a family-run creator household in which adults retain public-account control and a teenager contributes safely. [S1][S2][S3][S4][S5][S6][S7][S8]

The next development pass should **not reintroduce scheduling**. The paid-beta UI correctly hides it because the documented path is immediate publishing and the project does not yet prove restart-safe scheduled execution plus timezone behavior in the family flow. The highest-value work is narrower:

1. **Provider confidence and reconciliation (P0):** run real LinkedIn/X sandbox scenarios, expose connection capability checks and unknown-state reconciliation, and preserve channel-level idempotency.
2. **Pilot instrumentation and guided onboarding (P0):** measure the existing 5-10-household protocol in-product, including first-draft time, ten-second next-action comprehension, invitation/review completion, recovery support, and weekly time saved.
3. **Youth privacy and adult-controlled trust (P1):** move from role labels to explicit effective-permission views, retention/deletion controls, age-appropriate explanations, and auditable consent/role changes.

This is a release-hardening and validation pass rather than another breadth expansion. A small product that can prove safe contribution, reliable adult publication, and real weekly time savings is more defensible than a broader content suite with unverified provider configuration.

## Project Understanding

### Verified current product

ContentForge v0.15.0 is an AI-assisted content operations application with brand voice and Brand Kit management, campaigns, approvals, localization/transcreation, publishing, analytics, AI visibility, and video generation (`README.md`, `CHANGELOG.md`, `pyproject.toml`). The backend uses FastAPI, Pydantic v2, SQLAlchemy/SQLite, and httpx. The frontend uses React 19, TypeScript, and Vite (`frontend/package.json`).

The family product is a bounded layer over that professional engine:

- `src/family/store.py:FamilyStore` owns SQLite-backed workspaces, memberships, invitations, projects, ideas, assets, immutable revisions, reviews, publication batches, deliveries, connection state, reconciliation, and weekly counts.
- `src/routers/family.py` exposes authenticated `/api/v1/family/...` routes and resolves the current JWT user rather than trusting actor headers.
- `frontend/src/family.tsx:FamilyApp` provides a separate family shell with Home, Create, Projects, Review, and Calendar navigation, plus member and connection settings.
- `frontend/src/family.tsx:Setup` gives a four-step setup sequence with explicit contributor limits and private-by-default copy.
- `frontend/src/family.tsx:InvitationAccept` previews role and permissions before acceptance.
- `frontend/src/family.tsx:PublishConfirm` and `PublishResult` implement calm adult confirmation and channel-level results. The scheduling choice is intentionally absent.
- `tests/test_family_api.py` and `tests/test_family_completion.py` cover workspace idempotency, permissions, exact-revision review, invitation lifecycle, publication eligibility, idempotency, partial results, and weekly summaries.

### Principal family flow

1. An authenticated adult creates a Family Creator or Family Business workspace.
2. The owner invites adult collaborators, teen contributors, or viewers.
3. A contributor captures a private idea or completes the guided project journey.
4. A mutable asset produces immutable revisions.
5. A reviewer approves an exact revision. Later edits supersede that approval.
6. An adult confirms immediate publication to selected channels.
7. A queued batch records per-channel delivery state; successful deliveries retain their remote identifiers; only failed/retryable channels may be retried.
8. The UI reports connection-required, unknown, failed, partial-success, or published outcomes honestly.

### Maturity and verified constraints

The archive's `development-report.md` records a clean full backend run over 2,599 collected tests, 39 passing frontend tests, clean frontend lint, successful production build, and backend/frontend startup smoke checks. It also records two important blocks: real provider sandbox execution was not performed because six credential variables were absent, and Playwright browser E2E could not run because Chromium installation timed out. These are project-reported results rather than newly rerun tests in this research-only phase.

The hard constraint for planning is therefore: treat the mechanics as implemented, but do not claim provider-specific production proof, browser E2E proof, or pilot outcome proof. `provider-sandbox-results.csv` and `family-pilot-results.csv` are evidence templates, not successful outcomes.

## Current-State Gap Analysis

| Area | Verified state | Gap | Release implication |
|---|---|---|---|
| Backend regression | Project report: 2,599 collected, exit 0 | This phase is research-only and did not alter or rerun code | Preserve current baseline; require every later code pass to rerun the full backend suite. |
| Frontend quality | Project report: 39 tests, lint, build, startup pass | Browser E2E is blocked | A paid beta still needs real browser coverage for invitation, review, publish, and recovery. |
| Provider execution | Real connector paths and queued batches exist | No approved LinkedIn/X credential evidence | Do not market “verified publishing” per provider until the sandbox matrix is complete. |
| Unknown provider state | `UNKNOWN` and reconciliation semantics exist in store/API | End-user evidence and real timeout behavior remain unproved | Make reconciliation a first-class UX, never a generic retry. |
| Scheduling | General scheduling modules exist elsewhere; family UI hides scheduling | No durable family scheduled-job proof with restart/timezone tests | Keep hidden in first paid beta. |
| Roles | Owner, adult collaborator, teen contributor, viewer implemented | Effective permissions are not presented as a centralized auditable matrix | Add capability view and server-enforced regression tests for every sensitive action. |
| Invitations | Preview, expiry, single-use, revoke, accept implemented | Real households have not proved self-service comprehension | Measure completion and support minutes in pilot. |
| Privacy state | Private/public labels present | Retention, deletion, consent and data-category transparency are incomplete | Avoid child-directed marketing until privacy operations are production-ready. |
| Pilot | Protocol and CSV schema exist | No households enrolled and no outcomes | Pilot evidence is the next product gate, not optional marketing research. |
| Value proof | Weekly summary counts projects, approvals and posts | “Hours saved” is not measured or user-correctable | Add lightweight, privacy-preserving outcome telemetry. |
| Information architecture | Family mode is much narrower than the 13-workspace professional shell | Calendar currently cannot promise durable scheduling | Keep navigation label only if it clearly represents results/history, or hide until useful. |
| Documentation | Family guide, sandbox checklist and pilot guide exist | Provider and pilot result files are intentionally empty/blocked | Preserve honest status and date all future evidence. |

## Target Users and Jobs to Be Done

### Primary segment

The strongest target is a **family-run creator household or micro-business** where one or two adults own the relationship with external platforms and another family member, often a teenager, contributes ideas or drafts. This is narrower and more defensible than a general child-directed creator platform.

### Roles and jobs

- **Adult owner:** “Help us publish consistently without sharing credentials or losing control of what becomes public.”
- **Adult collaborator:** “Let me review, correct, and publish a clearly identified version without duplicating successful posts.”
- **Teen contributor:** “Let me make useful creative contributions from my phone while the product makes my limits obvious and respectful.”
- **Viewer or supporter:** “Let me see progress without editing, publishing, billing, or account access.”
- **Pilot facilitator/support lead:** “Show whether households can succeed without coaching and where recovery consumes support time.”

### Core jobs

1. Reach a useful first draft in ten minutes or less.
2. Recognize the next step in ten seconds or less.
3. Accept a family invitation without support.
4. Understand Private, Approved, Publishing, Public, Failed, and Verification required.
5. Complete exact-version adult review without losing authorship context.
6. Publish to LinkedIn/X once and recover only the failed channel.
7. Restore an expired or under-scoped connection without developer help.
8. Demonstrate at least two to three hours of weekly time saving before charging recurring family subscriptions.

## Target-Market Pain Points

| User problem | Segment | Recurrence/evidence | Confidence | Implication |
|---|---|---|---|---|
| Keeping social content fresh is a sustained burden | SMB owners | Verizon found 54% of surveyed SMBs struggled to keep content fresh and follow trends; a separate 1,960-company survey identified time as the leading barrier for 50% [S1][S9] | HIGH | Sell a repeatable weekly workflow and time saving, not generic AI generation. |
| Social effort is distributed across very small teams | Micro-businesses | TechBehemoths reported 51% relied on 2-3 people and 56.1% managed social media in-house [S9] | MEDIUM-HIGH | Household roles and handoffs match real small-team constraints. |
| Approval features are valuable but often placed in higher tiers | Small teams | Planable makes required approvals a Pro feature; Buffer reserves content approval and access levels for Team; Metricool puts approval and role management in Advanced [S2][S3][S7] | HIGH | A simple adult gate can be the core paid value, if priced below agency tools. |
| Per-seat, per-channel and per-workspace pricing becomes difficult to predict | Households and micro-businesses | Buffer charges per channel, Planable per workspace, Publer per social account plus members, and Hootsuite per user [S2][S3][S6][S8] | HIGH | Use a household bundle with included contributors, two verified channels, and explicit AI/video allowances. |
| Family work can suffer from unclear authority and remembered verbal instructions | Family businesses | Family-business discussions repeatedly describe micromanagement, ambiguous ownership, and forgotten instructions; this is anecdotal but consistent [S10][S11] | LOW-MEDIUM | Exact revisions, explicit next actions and role boundaries reduce interpersonal friction. |
| High-control parental tools can damage trust | Parent-teen pairs | A 19-pair study found collaborative transparency could support communication, but power imbalance made co-management difficult; later family-centered research favors collaboration over purely restrictive monitoring [S12][S13] | MEDIUM | Explain capabilities bilaterally; do not design covert monitoring or surveillance. |
| Children and teens need privacy-protective defaults | Families | FTC guidance centers parental control for under-13 data and the 2025 amended COPPA rule; ICO guidance requires high-privacy defaults for child-accessible services [S14][S15][S16] | HIGH | Private-by-default is correct; add retention, consent and deletion operations before child-directed expansion. |
| Provider failures are not binary | Adult publishers | The project itself models rate limit, permission, expired token, unknown state and partial success; platform tools emphasize centralized publishing but real APIs remain external systems | HIGH (project evidence) | Reconciliation and channel-level evidence are P0, not technical polish. |
| Subscription fatigue raises the proof bar | Price-sensitive households | Public discussions show aversion to accumulating recurring subscriptions; evidence is broad consumer sentiment rather than category-specific willingness to pay [S17] | MEDIUM-LOW | Validate 2-3 hours saved and offer easy cancellation/export before optimizing price. |

## Competitor Weaknesses

### Planable

Planable is the closest workflow substitute because it combines visual creation, feedback, approval and publishing. Its official pricing page offers unlimited users but charges per workspace; required approval appears at Pro and multi-level approval at Enterprise. This is strong for agencies, but the product is not built around an adult-owned household, youth-safe contribution, private family ideas or a “no Publish button for contributors” mental model. [S3]

### Buffer

Buffer has the clearest small-business publishing model and a genuine free tier. Official pricing is per connected channel; Team adds unlimited team members, access levels and content approval workflows. Buffer is a strong substitute for publishing and lightweight collaboration, but it does not offer ContentForge's exact-revision guardian review, family invitation semantics, private/public education, brand voice, localization and content-production stack in one bounded journey. [S2]

### Canva

Canva's current pricing and product surface make it a formidable design and content-planning substitute. It offers a large template/asset ecosystem, social planning in paid tiers, and tiered approvals at Enterprise. Its advantage is immediate visual output. Its gap is operational assurance: a family still needs a product that explains role boundaries, binds adult approval to the exact revision, records channel-level delivery evidence, and handles unknown external state. [S4]

### Adobe Express

Adobe Express provides free and Premium creative tools, cross-device use, brand kits, version history and social scheduling. The official page currently lists scheduling to one account per network on Free and three on Premium. It is competitively priced for solo creation, so ContentForge should not compete on templates or image editing. The opportunity is the safe, auditable family handoff and provider recovery around finished content. [S5]

### Metricool / Publer / Hootsuite

Metricool and Publer offer broad network coverage and lower-cost scheduling; Metricool places roles and post approvals in Advanced, while Publer scales by accounts and members. Hootsuite provides professional review/approval and enterprise governance but is visibly designed for professional teams. These products prove demand for integrated calendars, analytics, approvals and automation, while leaving room for a calmer household bundle. [S6][S7][S8]

## Competitor Comparison

| Product | Target/positioning | Current official packaging signal | Core UX strength | Repeated or structural weakness | ContentForge opportunity |
|---|---|---|---|---|---|
| Planable | Agencies and brand teams | Free first 50 posts; Basic/Pro per workspace; approvals deepen by tier [S3] | Feed-like review and clear approval chain | Workspace/add-on costs grow; family safety is not the model | Household bundle with adult gate and no per-contributor fee. |
| Buffer | Creators and small business | Free 3 channels; paid per channel; Team adds approvals/access [S2] | Simple queue and idea-to-publish flow | Costs scale with channels; less governance before publish | Exact-revision review plus safe channel recovery. |
| Canva | Individuals, teams, enterprise | Free, Pro, Business, Enterprise; AI allowances and content planner vary [S4] | Fast visual first result and templates | Broad suite; provider evidence and family role semantics are secondary | Goal wizard feeding audited publishing rather than a design suite. |
| Adobe Express | Individuals and creative teams | Free; Premium US$9.99/month; scheduling limits by plan [S5] | Cross-device creation, brand kits, resize and assets | Lightweight social management, not household operations | Focus on contributions, review and delivery confidence. |
| Metricool | Social managers and agencies | Free; Starter from $20; Advanced from $53 with roles/approvals [S7] | Planner, analytics, reporting in one dashboard | Team safety is a higher-tier professional feature | Make simple adult approval standard in the family paid plan. |
| Publer | Solopreneurs, creators, SMEs | Free; paid per social account, members configurable [S6] | Low-cost broad scheduling and automation | Account/member complexity; no family trust model | Predictable household price and private-by-default ideas. |
| Hootsuite | Professional and enterprise social teams | Standard, Professional, Advanced, Enterprise; review/approval in Advanced [S8] | Comprehensive professional console | Per-user complexity and enterprise weight | Calm, narrow UI and supportable two-channel beta. |

## Validated Demand Signals

1. **Fresh-content pressure is measurable.** More than half of Verizon's SMB sample struggled to keep content fresh, while 76% still credited social media with positive business impact. This supports an assistive content workflow but not an unbounded AI feature set. [S1]
2. **Approvals are monetized.** Three independent competitor structures reserve stronger approval, roles or workflow controls for paid tiers. That is a willingness-to-pay signal for controlled collaboration, though not proof for family-specific branding. [S2][S3][S7]
3. **Low-friction creation is table stakes.** Canva and Adobe Express put templates, assets, brand tools and social planning into accessible individual plans. The product must reach a useful preview quickly and cannot rely on the depth of its backend as perceived value. [S4][S5]
4. **Predictable pricing is itself differentiation.** Competitors variously charge by channel, account, member, workspace or user. A two-adult/four-contributor family bundle can be simpler if usage caps are explicit. [S2][S3][S6][S8]
5. **Collaborative safety should not become surveillance.** Parent-teen research found value in transparency but also power-imbalance concerns. The product should show both adults and teens the same capability rules and avoid hidden monitoring. [S12][S13]
6. **Private-by-default is regulatory and UX baseline.** FTC and ICO sources support parental control, data minimization and high-privacy defaults for services accessed by children. [S14][S15][S16]
7. **Open-source alternatives reduce pure scheduler defensibility.** Postiz alone has a large active GitHub community, broad platform support and self-hosting. ContentForge must differentiate on the family mental model, evidence, privacy and integrated review rather than connector count. [S18]

## Market and Pricing Evidence

This project spans several overlapping markets: social scheduling, content collaboration, AI creation, family organization and small-business marketing. A credible TAM or CAGR specific to “family creator operations” was not found, and combining adjacent market reports would double count. No TAM, CAGR, MRR or revenue forecast is asserted.

Current official pricing establishes a realistic comparison range:

- Adobe Express Premium is listed at US$9.99 per month and includes brand management plus scheduling to three accounts per social network. [S5]
- Buffer's annual rates are $5/month per channel for Essentials and $10/month per channel for Team; Team includes unlimited members, access levels and approval workflows. [S2]
- Planable lists Basic at $33/workspace/month and Pro at $49/workspace/month in the retrieved official page, with required approval in Pro and multi-level approval in Enterprise. [S3]
- Metricool lists Starter from $20/month and Advanced from $53/month; Advanced includes team/client management, roles and post approval. [S7]
- Publer lists Professional at $5/month and Business at $10/month before configuring social accounts and additional members. [S6]
- Hootsuite's retrieved official plan page confirms per-user tiers and places content review/approval in Advanced, though localized numeric prices were not visible in the page extract and should not be inferred. [S8]

Recommended paid-beta pricing research, not a final price:

- Test **CHF/EUR/USD 19-29 per household per month** for one brand, two verified channels, two adult admins, up to four non-billed contributors, review/audit, and a transparent AI allowance.
- Compare against a **CHF/EUR/USD 190-240 annual** option, but do not preselect annual billing.
- Offer a free trial that proves the first private draft and review but does not enable live provider publishing until an adult connects and verifies an account.
- Do not charge per child/contributor. Charge for adult-controlled value: verified channels, brands, advanced generation and automation.
- Add a hard monthly generation cap or spend cap. “Unlimited AI” claims are risky where provider costs are variable.

The proposed range is an experiment anchored to competitor entry and team tiers, not demonstrated willingness to pay. The pilot must ask for a real purchase or deposit decision after the workflow, not an abstract “would you pay?” response.

## Modern UX Expectations

### Category-specific baseline

1. **One-action Home:** role-aware next action, pending reviews, failed connections and recent projects.
2. **Guided first outcome:** goal, audience, private draft, preview, review and result without exposing the professional shell.
3. **Mobile capture:** one-tap idea entry, image permission explanation, offline draft preservation and touch-size controls.
4. **Exact-version review:** author, revision, diff, privacy state, channel preview, approval consequence and supersession warning.
5. **Connection health:** account identity, capabilities/scopes, expiry, last test, reconnect and a non-destructive sandbox check.
6. **Honest delivery:** channel rows, remote identifiers, rate limits, permission failures, unknown state, reconciliation and selective retry.
7. **Value report:** projects, approvals, publications, avoided duplicate retries, user-correctable time saved and connection support burden.

### State design

Every screen needs loading, empty, disabled, success, error, offline, partial-success and uncertain-external-state behavior. `frontend/src/family.tsx` already contains many of these patterns. The critical addition is to distinguish **FAILED** from **UNKNOWN**. Unknown means the product does not know whether a remote side effect occurred; a retry must be preceded by reconciliation.

### Responsiveness and accessibility

The family shell's mobile bottom navigation is directionally correct. The next pass should verify WCAG 2.2 AA across the real browser flow, including keyboard focus, focus not obscured, 24-by-24 CSS pixel minimum targets or valid spacing exceptions, accessible authentication, status announcements and non-color-only delivery states. W3C's WCAG 2.2 documentation is the source of truth. [S19]

### Trust, privacy and security indicators

- Display “Private to family,” “Approved for adult publishing,” “Public,” and “Verification required” as distinct states.
- Show the effective permissions to the member whose account is affected, not only to the owner.
- Keep provider credentials adult-only and never expose token values in evidence exports.
- Collect no more youth data than needed; publish retention periods and support deletion/export.
- Avoid targeted advertising and opaque engagement nudges in family mode.
- Reauthenticate before credential, billing, ownership or destructive privacy actions.
- Preserve an immutable minimum audit record while removing unnecessary personal linkage.

## Open-Source and Automation Opportunities

| Opportunity | Evidence/compatibility | Recommended use | Risk |
|---|---|---|---|
| Postiz connector and job patterns | Active AGPL project with broad providers and an agent/API surface [S18] | Study retry, provider normalization and webhook handling; do not copy AGPL code into a differently licensed product without legal review | License compatibility and architectural mismatch. |
| Playwright + axe-core | Existing Playwright config and E2E spec in project; W3C criteria define targets [S19] | Add role matrix, invite, review, publish-result and unknown-state browser tests | Browser binaries must be made deterministic in CI. |
| OpenTelemetry | Compatible with FastAPI/httpx ecosystem | Correlate publish batch, provider attempt, callback and reconciliation without storing credentials/content | PII leakage if attributes are not allowlisted. |
| Durable SQLite worker with lease/outbox | Fits current single-node paid beta | For future scheduling, persist due jobs, lease atomically, resume after restart, use Europe/Zurich/DST test matrix | Multi-instance scale and clock semantics. |
| Webhooks plus polling reconciliation | Fits provider adapter design | Prefer webhook inbox with dedupe; use polling when no webhook or callback is delayed | Provider-specific limits and inconsistent remote identifiers. |
| Privacy-preserving pilot events | Fits existing CSV protocol and family store | Record funnel timestamps, outcomes and support interventions without draft text | Small-sample overinterpretation. |
| Capability registry | Fits connector abstraction | Normalize provider scopes into can_post_text, can_post_link, can_read_status and token_expiry | Providers may not expose all capabilities reliably. |

Scheduling should remain out of the next pass. When revived, the acceptance bar is a persistent scheduled-job record, atomic lease, restart recovery, idempotent dispatch, timezone-aware display/storage, DST gap/fold tests, cancellation semantics, and browser-visible status.

## Differentiation Opportunities

| Capability | Problem solved / user | Evidence | Competitor gap | Value | Complexity | Principal risk | Priority | Success criterion |
|---|---|---|---|---|---|---|---|---|
| Provider Confidence Center | Adults cannot distinguish configured from proven publishing | Project sandbox gap; competitors sell centralized publishing [S2][S7][S8] | Few products expose evidence-oriented sandbox state to tiny teams | Prevents false readiness and support escalations | MEDIUM | Provider app approval and sandbox limitations | P0 | LinkedIn and X scenario matrix completes with 0 duplicate posts and evidence for every case. |
| Reconcile-before-retry | Unknown external state can create duplicate posts | Existing UNKNOWN/idempotency model | Generic tools often simplify failure into Retry | Protects family brand and trust | MEDIUM | Provider status APIs may be incomplete | P0 | 100% of UNKNOWN states block repost until reconciliation or audited override. |
| Measured First Draft Journey | Feature breadth obscures value | SMB content freshness/time pain [S1][S9] | Creator tools optimize creation, not household handoff | Faster activation and clearer purchase decision | LOW-MEDIUM | Telemetry can become invasive | P0 | Pilot median first useful draft ≤10 min, with ≥80% unaided completion. |
| Shared Permission Clarity | Adult/teen power boundaries are easily misunderstood | Family-centered privacy research [S12][S13] | Competitors use professional roles, not age-appropriate explanations | Trust without surveillance | MEDIUM | Oversimplified language may hide edge permissions | P1 | ≥90% of pilot participants correctly answer publish/billing/member capability questions. |
| Privacy Operations Center | Private labels are insufficient without data lifecycle controls | FTC/ICO guidance [S14][S15][S16] | Schedulers rarely center household retention/deletion | Enables safer expansion and enterprise-grade trust | HIGH | Jurisdictional/legal design | P1 | Export and deletion tests pass for every data category; no orphan identifiable data in defined scope. |
| Household Value Ledger | Subscription must prove time saved | Subscription fatigue plus SMB time pressure [S1][S9][S17] | Competitors report social metrics, not family workload | Supports retention and pricing | LOW | Self-reported time savings can be biased | P1 | ≥60% of pilot households report ≥2 hours saved/week by week four. |
| Explicit Immediate-only Beta | Visible scheduling without durable execution breaks trust | Project constraint and current hidden UI | Competitors feature mature calendars | Honest smaller product | LOW | Perceived feature gap | P0 | Zero family UI claims or controls imply scheduled publishing until full scheduling acceptance suite passes. |

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

## Priority-Ranked Development Recommendations

### P0.1 Complete real provider sandbox verification

Use approved, non-public LinkedIn and X accounts. Execute and retain evidence for: successful post, expired token, permission failure, rate limit, timeout/unknown state, repeated idempotency key, partial success, and failed-channel-only retry. Evidence must include UTC timestamp, provider, sanitized account identifier, correlation/idempotency identity, request category, response category, remote identifier when confirmed, and cleanup action. No credential may appear in logs or exports.

Exit gate: all scenarios have an observed result; duplicate external side effects are zero; unknown states are reconciled or explicitly unresolved; successful channels are never resent during selective retry.

### P0.2 Add connection capability and reconciliation UX

Turn the current mechanics into an adult-understandable surface. Connections should show account name, token expiry if known, granted/required posting capabilities, last successful provider check, last failure class, and an Evidence view. Publish Result should route expired-token and missing-scope failures directly to the affected connection. UNKNOWN must offer Reconcile, not Retry.

Exit gate: five untrained adults can recover expired-token and missing-scope scenarios with no developer help; no participant retries an UNKNOWN state before reconciliation.

### P0.3 Run instrumented 5-10-household pilot

Implement minimal, consented pilot events and use the existing protocol. Measure: first useful draft, ten-second next-action recognition, contributor publish-rule comprehension, private/public distinction, invitation completion, review/publish completion, connection recovery support, and weekly hours saved. Keep raw content out of analytics.

Exit gate: at least five households complete two weeks; no safety-stop event; ≥80% unaided invitation and review/publish completion; median first draft ≤10 minutes; ≥60% report ≥2 hours saved/week by week four or the product is repositioned.

### P1.1 Privacy and effective-permission operations

Add explicit capability views, role-change impact previews, immediate server-side revocation, data export, deletion/retention workflow, and age-appropriate explanations. Conduct legal review before marketing to under-13 users or collecting child personal data.

### P1.2 Browser E2E and accessibility release gate

Pin Chromium in CI and cover sign-in, setup, invite preview/accept, teen contribution, exact-revision approval, adult publish, partial success, reconcile, and reconnect. Include axe checks, keyboard-only interaction, 200% zoom, mobile viewport, reduced motion and status announcements.

### P2. Durable scheduling only after validation

Do not expose a date/time picker until restart-safe background execution, timezone conversion, DST, idempotency, cancellation and delayed-provider tests are green. If implemented, start with one timezone-aware scheduled post per batch before recurring schedules.

## Recommended Scope for the Next Development Pass

**Include:**

- provider sandbox harness and sanitized evidence model;
- connection capability/health screen;
- reconcile-before-retry UX and tests;
- deep links from failed delivery to reconnect;
- privacy-preserving pilot telemetry and export;
- first-use funnel and ten-second comprehension measurement hooks;
- effective-permission matrix for all family roles;
- Playwright/axe release flow with deterministic browser provisioning;
- updated `development-report.md`, provider results and pilot documentation in the later development phase.

**Exclude:**

- scheduled publishing;
- new social platforms;
- general-purpose design editor expansion;
- more AI generation modes;
- child-directed marketing under age 13;
- billing optimization before value proof;
- enterprise multi-tenant features unrelated to the pilot.

A coherent pass can be completed when one adult can connect a provider, prove it, invite a contributor, receive and review a draft, publish once, recover an injected failure, and explain every privacy/public state without support.

## Risks, Unknowns, and Assumptions

- **Provider access risk:** LinkedIn and X app approval, product access and sandbox behavior may constrain test coverage. This cannot be solved by mocks alone.
- **No market category proof:** “Family Creator” is a hypothesis. Adjacent product demand is validated; family-specific willingness to pay is not.
- **Small pilot sample:** Five to ten households can expose usability and severe safety failures but cannot establish population-level conversion or retention.
- **Youth privacy jurisdiction:** COPPA and the ICO Children's Code are important baselines, not a complete global legal analysis. Obtain specialist counsel before child-directed launch.
- **Role semantics:** “Teen contributor” is a product permission role, not verified age assurance. Do not infer age from role name.
- **Provider unknown state:** Some providers may not offer enough status lookup to reconcile every timeout. Manual verification and documented override may remain necessary.
- **Time-saved measurement:** Self-report is biased. Combine timestamps and user correction, and report medians with definitions.
- **Archive artifacts:** Runtime `.db` files are pre-existing in the input and were preserved for project integrity in this research phase, even though final packaging rules normally exclude runtime databases if they are not intentional assets. They were not modified.
- **Scheduling:** General scheduling code elsewhere in the repository does not prove the family paid-beta promise. The family UI should remain immediate-only.
- **Testing evidence:** The regression/build claims are copied from project evidence and not independently rerun here because this phase forbids project changes other than this report and is focused on research.

## Sources

Accessed 2026-08-12 unless otherwise noted.

- **[S1] Verizon Business.** “2025 State of Small Business Survey: Surge in AI, cybersecurity and social media demand.” 2025-05-20. https://www.verizon.com/about/news/2025-state-small-business-survey
- **[S2] Buffer.** “Pricing.” Official product/pricing page. https://buffer.com/pricing
- **[S3] Planable.** “Planable pricing: plans for agencies, brands, and enterprise teams.” Official pricing page. https://planable.io/pricing/
- **[S4] Canva.** “Canva Pricing: Compare Free, Pro, Business and Enterprise plans.” Official pricing page. https://www.canva.com/pricing/
- **[S5] Adobe.** “Pricing: Compare Free & Premium Plans | Adobe Express.” Official pricing page. https://www.adobe.com/express/pricing
- **[S6] Publer.** “Social Media Management Plans for All Needs.” Official pricing page. https://publer.com/plans
- **[S7] Metricool.** “Metricool Pricing: Find The Best Plan.” Official pricing page. https://metricool.com/pricing/
- **[S8] Hootsuite.** “Hootsuite Plans, Prices, and Features.” Official plans page. https://www.hootsuite.com/plans
- **[S9] TechBehemoths.** “How Small and Mid-Sized Businesses Use Social Media in 2025: Survey Results.” 2025-10-01. https://techbehemoths.com/blog/small-mid-sized-businesses-use-social-media-survey-results
- **[S10] Reddit r/Entrepreneur.** “For those in family businesses, lessons learned?” Community discussion, 2019-05-26. https://www.reddit.com/r/Entrepreneur/comments/bt3rov/for_those_in_family_businesses_lessons_learned/
- **[S11] Reddit r/smallbusiness.** “Family-Run Small Businesses... How To Deal With Family?” Community discussion, 2025-03-19. https://www.redditmedia.com/r/smallbusiness/comments/1jec9au/familyrun_small_businesses_how_to_deal_with_family/
- **[S12] Akter et al.** “From Parental Control to Joint Family Oversight: Can Parents and Teens Manage Mobile Online Safety and Privacy as Equals?” Proc. ACM HCI, study of 19 parent-teen pairs; arXiv version updated 2024-04-16. https://arxiv.org/html/2204.07749v2
- **[S13] Akter et al.** “Towards Collaborative Family-Centered Design for Online Safety, Privacy and Security.” 2024-04-04. https://arxiv.org/html/2404.03165v1
- **[S14] U.S. Federal Trade Commission.** “Complying with COPPA: Frequently Asked Questions.” Notes COPPA Rule amendment of 2025-04-22. https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions
- **[S15] U.S. Federal Trade Commission.** “Verifiable Parental Consent and the Children's Online Privacy Rule.” https://www.ftc.gov/business-guidance/privacy-security/verifiable-parental-consent-childrens-online-privacy-rule
- **[S16] UK Information Commissioner's Office.** “Children's code guidance and resources” and “7. Default settings.” https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/childrens-information/childrens-code-guidance-and-resources/ and https://cy.ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/childrens-information/childrens-code-guidance-and-resources/age-appropriate-design-a-code-of-practice-for-online-services/7-default-settings/
- **[S17] Reddit r/smallbusiness.** “Subscriptions fatigue.” Community discussion; weak qualitative evidence. https://www.reddit.com/r/smallbusiness/comments/kqcs7m/subscriptions_fatigue/
- **[S18] GitroomHQ.** “Postiz: open-source social media scheduling tool.” GitHub repository, 34k+ stars in retrieved listing. https://github.com/gitroomhq/postiz-app
- **[S19] W3C Web Accessibility Initiative.** “Understanding WCAG 2.2.” https://www.w3.org/WAI/WCAG22/Understanding/

### Project sources

- `pyproject.toml`
- `CHANGELOG.md`
- `development-report.md`
- `src/family/store.py`
- `src/routers/family.py`
- `src/connectors/` and publishing services referenced by the family router
- `frontend/src/family.tsx`
- `frontend/src/styles.css`
- `tests/test_family_api.py`
- `tests/test_family_completion.py`
- `docs/family-workspace.md`
- `docs/family-pilot.md`
- `docs/provider-sandbox-checklist.md`
- `provider-sandbox-results.csv`
- `family-pilot-results.csv`
