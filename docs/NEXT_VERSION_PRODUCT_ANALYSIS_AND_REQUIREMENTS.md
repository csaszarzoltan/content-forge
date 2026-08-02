# ContentForge Next-Version Product Analysis and Software Requirements

**Analysis basis:** Full static review of the application archive contained in `ZipPrompt.md`, including source code, server-rendered workspaces, domain store, API routers and schemas, tests, documentation, examples, changelog, and deployment configuration.

**Evidence boundary:** Statements labeled **Observed** are directly supported by the reviewed application. Statements labeled **Inference** describe likely user behavior or demand and should be validated with usability testing and production telemetry.

## Executive summary

ContentForge is an API-first content operations platform that has expanded into a browser-based product for planning campaigns, generating brand-aligned assets, governing approvals, publishing, localization quality assurance, provenance, platform validation, experimentation, SEO, and performance analytics.

The backend capability is broad and increasingly mature. The human-facing experience is not yet comparably mature. The six workspaces establish a sensible information architecture, accessible shell, explicit recovery language, and workflow state model, but most visible controls are static or only loosely connected to the underlying APIs. Users cannot reliably complete the core create-to-publish loop from the interface. The next version should therefore prioritize **workflow completion, cross-workspace continuity, actionable status and recovery, persistent publishing/scheduling, and user/tenant security**, rather than adding another isolated capability.

The recommended first release slice is a guided, persistent campaign workflow:

1. Create a campaign from a structured brief.
2. Generate and edit channel-specific assets.
3. Validate and resolve issues inline.
4. Submit assets for approval and complete review.
5. Preview, schedule, publish, and selectively retry.
6. Observe outcomes and navigate back to the responsible asset, campaign, or decision.

---

# 1. Product understanding

## What the application appears to do

**Observed:** ContentForge is a Python/FastAPI content operations system intended to help teams create, govern, distribute, localize, and measure content. Its capability set includes:

- Brand voice profiles, extraction, scoping, compliance scoring, and versioning.
- LLM-assisted generation for blog, social, and email content.
- SEO analysis, readability, metadata, SERP preview, JSON-LD, and internal-link suggestions.
- Language detection, translation, quality scoring, locale-aware templates, and multilingual scheduling concepts.
- Platform constraint validation for X/Twitter, LinkedIn, Instagram, Facebook, and TikTok.
- Publishing connectors currently centered on X/Twitter and LinkedIn.
- Scheduling, A/B testing, analytics, anomaly detection, exports, and content scoring.
- Six server-rendered operational workspaces backed by a dedicated SQLite workflow store.

The product is best understood as a **content operations control plane**, not merely a text generator. Its differentiator is the attempt to connect brand governance, production, approval, delivery, localization, provenance, and performance in one system.

## Likely users

### Primary segments

1. **Content marketers and campaign managers**
   - Create briefs, generate channel assets, adapt copy, coordinate publishing, and assess results.
2. **Social media managers**
   - Preview platform variants, validate restrictions, schedule posts, monitor delivery, and retry failures.
3. **Brand and content strategists**
   - Define voice rules, inspect evidence, resolve conflicts, and monitor compliance.
4. **Reviewers, legal/compliance stakeholders, and approvers**
   - Review findings, understand risk, request changes, approve, or reject with an audit trail.
5. **Localization managers and regional reviewers**
   - Compare locale variants, review quality signals, and approve languages independently.
6. **Content operations leads and auditors**
   - Trace provenance, review workflow state, export records, and monitor process reliability.
7. **Developers and integration teams**
   - Use the extensive REST API, automation contracts, examples, and connectors.

### Secondary segments

- Agencies managing multiple brands or clients.
- Small marketing teams seeking an all-in-one workflow.
- Enterprise platform administrators responsible for tenants, access, credentials, and governance.

## Main workflows and usage scenarios

### A. Campaign creation and asset production

**Observed flow:** Campaign workspace → brief and channel entry → campaign record → channel assets with states such as `DRAFT`, `PARTIAL`, `FAILED`, and `REVIEW_READY`.

**Inference:** Users expect to enter one brief, reuse their campaign/brand defaults, generate several channel variants, revise them in place, and progress only acceptable assets. They will often revisit a campaign over several sessions.

### B. Governance and approval

**Observed flow:** Approval inbox → risk filter → approval records with findings and state. The domain store prevents the requester from approving a high-risk request.

**Inference:** Reviewers need a queue ordered by urgency, campaign context, meaningful diffs, clear findings, and direct approve/request changes/reject actions. Campaign managers need to know who is blocking progress and why.

### C. Brand voice management

**Observed flow:** Brand voice studio → evidence-backed rules → conflict-gated activation. Rule records store type, value, evidence, and state.

**Inference:** Brand owners expect to import examples, review extracted rules, edit or resolve conflicts, compare versions, test voice against sample content, and activate a known version.

### D. Preview, validation, scheduling, and publishing

**Observed flow:** Publish center → LinkedIn and X preview areas → delivery records → retryable-channel calculation. Platform validation exists as an API. Publishing preserves partial success and can identify failed/retryable channels.

**Inference:** Users expect previews to be populated with actual content, validation to run automatically, account readiness to be visible, scheduling to be timezone-safe, publishing to require a deliberate confirmation, and retries to avoid duplicate posts.

### E. Localization QA

**Observed flow:** Localization workspace → locale matrix → variant score/state/content. Locale-level approval is independent, so one weak locale does not block all others.

**Inference:** Reviewers need source/translation comparison, issue categories, glossary/terminology context, change highlighting, comments, and per-locale ownership.

### F. Provenance and audit

**Observed flow:** Provenance ledger → model, prompt, voice version, events, approvals, edits, and delivery → secret-redacted export.

**Inference:** Auditors and governance users need filters, event chronology, links to associated resources, understandable explanations, and exportable evidence without exposing secrets.

### G. Analytics and optimization

**Observed flow:** Event ingestion → dashboard, content detail, channel comparison, A/B correlation, score, trends, anomalies, export.

**Inference:** Users expect insights to connect back to operational decisions: which asset, campaign, voice version, channel adaptation, or experiment caused the result, and what action to take next.

---

# 2. UI/UX analysis

## Strengths

1. **Clear top-level information architecture.** The six workspaces map to recognizable stages of content operations: campaigns, approvals, voice, publish, localization, and provenance.
2. **A workflow-oriented product direction.** The interface is organized around user jobs rather than exposing raw backend modules.
3. **Accessibility-conscious shell.** The reviewed HTML includes skip navigation, semantic navigation and main landmarks, visible current-page state, labels, live regions, empty states, responsive styling, and recovery guidance.
4. **Explicit recovery model.** Partial success is preserved in campaign and publishing logic, localization is gated per locale, and retries are selective.
5. **Evidence-oriented governance.** Voice rules retain source evidence; provenance records retain human changes and approvals; high-risk self-approval is blocked.
6. **Useful backend breadth.** Validation, generation, scoring, analytics, publishing, localization, and brand governance provide strong foundations for a unified interface.
7. **Consistent page shell.** Shared navigation, title, subtitle, readiness message, panel structure, and cards reduce visual fragmentation.

## Weaknesses

1. **The visible UI is largely a read-only façade.** The Campaign form and several buttons are rendered without form actions, JavaScript handlers, or a demonstrated interaction loop. “Generate assets,” “Activate profile,” and “Try again” appear actionable but are not connected in the reviewed rendering code.
2. **Core workflows are split across different API families and stores.** Operational workspace state uses a separate SQLite store, while generation, brand voice, scheduling, publishing, and analytics use other services/models. The user experience does not yet show coherent resource linkage.
3. **No persistent, resumable task context is visible.** List cards expose only a few fields and do not link to campaign, asset, approval, batch, locale, or provenance detail pages.
4. **Navigation is stage-based but not context-preserving.** Moving from campaign to approval or publish loses the selected campaign/asset context.
5. **Status is present but not explanatory.** Technical states are shown, but users are not told what caused the state, what is waiting, who owns the next action, or what can be done now.
6. **Previews are placeholders.** The publish workspace displays fixed “LinkedIn preview” and “X preview” articles rather than actual channel-rendered content and constraint feedback.
7. **Risk and quality signals lack explainability in the UI.** Scores and findings can be displayed without definitions, thresholds, confidence, or remediation.
8. **No robust editor is visible.** Users cannot clearly edit generated assets, compare revisions, restore a prior version, comment, or see autosave state.
9. **List usability is minimal.** Cards do not show search, sorting, pagination, saved filters, selection, bulk actions, ownership, timestamps, or deadlines.
10. **The global “Ready” live message is static.** It does not communicate loading, saving, generating, validating, publishing, partial success, or failure.
11. **Recovery is generic.** Every page shows the same recovery section whether or not an error occurred. This weakens trust and makes recovery guidance less credible.
12. **Platform support is inconsistent.** Validation supports five platforms, but real publishing supports fewer. The UI does not clearly distinguish “validate only,” “preview,” “schedule,” and “publish connected.”

## Confusing elements

- “Campaign brief” and “Channels” are insufficiently structured for dependable generation. There is no visible audience, objective, CTA, brand, locale, deadline, or content source.
- “Activate profile” appears only when no conflict exists, but the UI does not explain why it is absent or how to resolve a conflict.
- The approval queue shows findings but not the content being reviewed, its version, requester, reviewer, or decision controls.
- A locale score is shown without scale, dimensions, threshold, or confidence.
- Provenance cards show a narrow snapshot but no event timeline or relationship navigation.
- Status values such as `PARTIAL`, `RETRYABLE`, `CONFLICT`, or `REVIEW_READY` are system-centric and not translated into user guidance.
- Synthetic publishing success in development can be mistaken for a real published post unless prominently identified.

## Friction points

- Re-entering or manually carrying identifiers between APIs and workspaces.
- Repeatedly selecting brand, campaign, channels, language, and account because defaults and recent choices are not visible.
- Opening multiple workspaces to understand one asset’s end-to-end state.
- Manually finding failed channels or problematic locales rather than receiving focused next actions.
- Reviewing without side-by-side content, diffs, comments, or contextual findings.
- Error recovery without a preserved draft, retry scope, or explanation of what succeeded.
- Inability to bulk-select assets/locales/approvals for common repetitive work.
- Ambiguous save state and no clear undo/version-history path.

## Navigation and workflow observations

The top navigation is understandable, but it reflects functional departments rather than the user’s current job. Users will likely alternate between two modes:

1. **Portfolio mode:** “Show me all campaigns, approvals, failed deliveries, or locale issues.”
2. **Context mode:** “Show me everything about this campaign or asset and tell me the next action.”

The current UI supports the first mode only superficially and does not support the second. A persistent campaign/asset context, detail routes, and a unified activity/status rail are needed.

---

# 3. User behavior analysis

## Likely user habits

> The following are **inferences** grounded in the product’s workflows and should be validated through interviews, task observation, and telemetry.

- Users will clone or reuse prior campaigns, briefs, channel selections, voice profiles, and schedules.
- Campaign managers will work in short repeated sessions, checking status and resolving exceptions rather than rebuilding a workflow each time.
- Social managers will generate multiple variants, edit most of them, validate repeatedly, and publish only after previewing.
- Reviewers will batch similar approvals and prioritize high-risk, due-soon, or blocked items.
- Brand owners will edit extracted rules and want to see the effect on real sample outputs before activation.
- Localization reviewers will focus on failed or borderline locales and ignore already-approved variants.
- Operations leads will investigate anomalies by tracing performance back to campaign, asset, version, and delivery events.
- Power users will expect keyboard navigation, bulk actions, saved views, and API/UI consistency.

## Repeated actions

- Selecting the same brand voice, channels, audience, markets, and approvers.
- Regenerating or rewriting one channel variant.
- Running validation after every material edit.
- Switching between campaign, approval, publish, and analytics contexts.
- Filtering for pending/high-risk/failed/review-required records.
- Retrying failed channels and verifying that successful channels are not duplicated.
- Comparing source and locale variants.
- Exporting evidence and performance data.

## Likely pain points

- Uncertainty about whether a button performed a real action.
- Difficulty understanding the next required step.
- Loss of context across workspaces.
- Fear of duplicate posting after retry or browser refresh.
- Lack of confidence in a score that has no explanation.
- Inability to distinguish draft, saved, submitted, approved, scheduled, published, and externally confirmed states.
- Excessive manual handoff between creator, reviewer, brand owner, and publisher.
- Too much technical vocabulary for non-technical marketing users.
- Hidden differences between supported validation platforms and connected publishing platforms.

## Usage bottlenecks

1. **Campaign-to-asset bottleneck:** A campaign can be created, but the UI does not visibly complete generation, editing, validation, and asset state progression.
2. **Review bottleneck:** Approval records exist, but the reviewed UI lacks a complete decision interaction and content comparison.
3. **Publish bottleneck:** Preview placeholders, in-memory status limitations, and incomplete account readiness make real delivery risky.
4. **Cross-system bottleneck:** Separate stores and identifiers prevent a unified user journey and analytics attribution.
5. **Exception bottleneck:** Generic recovery does not prioritize the exact failed step or provide safe retry scope.

## Expected but missing interactions

- Clickable cards and detail pages.
- Autosave with visible save state.
- Inline editing and revision history.
- Generate, regenerate, shorten, adapt, and undo actions by channel.
- Real-time character/media validation in the editor.
- Approve, request changes, reject, comment, assign, and mention actions.
- Side-by-side source/translation and before/after diff.
- Platform account connection and credential health.
- Date/time picker with operator and audience timezone display.
- Publish confirmation with exact channels and duplicate-prevention assurance.
- Notifications and “My work” queue.
- Search, sort, filters, saved views, pagination, and bulk operations.
- Deep links from analytics and provenance back to the relevant campaign/asset/version.

---

# 4. What should be improved

## Critical improvements

1. **Make the primary UI workflow functional end to end.** Wire campaign creation, generation, editing, validation, approval, scheduling/publishing, retry, and status updates.
2. **Unify resource identity and context.** Campaign, asset, generation, approval, publish batch, schedule, localization job, provenance, and analytics events must be relationally connected and navigable.
3. **Add detail views and contextual next actions.** Every card must open an actionable detail page with history, owner, status explanation, blockers, and permitted actions.
4. **Implement persistent, idempotent scheduling and publishing.** Remove restart-sensitive status behavior and prevent duplicate publication on retries or repeated submissions.
5. **Protect multi-tenant data.** Apply authentication, tenant scoping, object-level authorization, and role/permission checks to UI and workflow APIs.
6. **Replace generic recovery with operation-specific recovery.** Preserve drafts and partial success; show exactly what failed, what succeeded, and the safe retry action.
7. **Provide a real editor and version model.** Users need autosave, revisions, diff, restore, comments, and explicit approval of an immutable version.
8. **Surface real platform previews and live validation.** Validation should run automatically and block unsafe publication while offering guided remediation.

## Medium-priority improvements

- Unified “My work” dashboard for approvals, failed deliveries, locale reviews, and due campaigns.
- Search, sorting, filters, saved views, pagination, and bulk actions.
- Reusable campaign templates and remembered defaults.
- Account connection center with scope, expiry, and credential health.
- Notification preferences and actionable in-product/email notifications.
- Explainable scoring with issue-level recommendations.
- Source/translation comparison with terminology and locale review comments.
- Analytics drill-through and recommendations tied to campaign decisions.
- Consistent taxonomy and human-readable state labels.
- Connected onboarding and sample workspace.

## Nice-to-have improvements

- Keyboard command palette and advanced shortcuts.
- Custom workflow templates and organization-specific approval rules.
- Calendar drag-and-drop rescheduling after persistent scheduler foundations are complete.
- Personal dashboards and saved widgets.
- User-configurable density and table/card view preference.
- Automated recommendations for reusable snippets or campaign templates based on repeated behavior.

---

# 5. Requirements

## Business requirements

### BR-01: Complete the create-to-publish product loop
- **Type:** Business
- **Description:** ContentForge shall enable an authenticated user to complete campaign creation, asset generation/editing, validation, approval, scheduling or publishing, failure recovery, and performance review from the browser UI without manually calling APIs or copying resource IDs.
- **User value:** Delivers one coherent workflow instead of a collection of capabilities.
- **Priority:** **Must have**
- **Rationale:** The backend already supports most stages, but the reviewed workspaces do not provide a complete interaction loop.
- **Acceptance criteria:**
  - A user can start from the Campaign workspace and create at least one channel asset.
  - Each stage provides a visible next action and preserves campaign/asset context.
  - The user can reach approval and publish/schedule outcomes without external API tools.
  - The resulting asset is linked to provenance and analytics identifiers.

### BR-02: Establish a production-safe workflow foundation
- **Type:** Business
- **Description:** Operational state for campaigns, approvals, localization, scheduling, publishing, and provenance shall be persistent, recoverable, and tenant-scoped.
- **User value:** Prevents lost work, duplicate posts, and cross-organization data exposure.
- **Priority:** **Must have**
- **Rationale:** Current documentation identifies in-memory or local-only components and explicitly calls out production authorization requirements.
- **Acceptance criteria:**
  - Restarting an application instance does not lose scheduled jobs, publish status, or workflow records.
  - All workflow records include tenant/organization ownership.
  - Recovery tests demonstrate no duplicate delivery after process restart.
  - Unauthorized cross-tenant requests return an appropriate denial and reveal no record metadata.

### BR-03: Reduce time and effort in repeated content operations
- **Type:** Business
- **Description:** The product shall reduce repeated setup and navigation through templates, remembered defaults, batch handling, and context-preserving transitions.
- **User value:** Faster daily work and lower cognitive load.
- **Priority:** **Should have**
- **Rationale:** Campaign/channel selection, approval triage, validation, and locale review are repetitive workflows.
- **Acceptance criteria:**
  - Users can save and reuse a campaign template.
  - The system remembers the last valid brand, channels, locales, and timezone per user where appropriate.
  - Users can perform bulk approval assignment and bulk locale actions subject to permissions.
  - Usability testing shows a material reduction in completion time against the current baseline.

### BR-04: Turn analytics into operational learning
- **Type:** Business
- **Description:** Performance data shall be attributable to campaign, asset, version, channel, experiment, voice version, and delivery.
- **User value:** Users can understand what worked and reuse successful decisions.
- **Priority:** **Should have**
- **Rationale:** Analytics are technically extensive but are not visibly connected to the human workflow.
- **Acceptance criteria:**
  - Content analytics detail links to the exact campaign and asset version.
  - Campaign views show channel outcomes and experiment status.
  - Users can clone a successful asset or campaign from analytics.
  - Attribution gaps are visibly labeled rather than silently omitted.

## User requirements

### UR-01: Resume work from a unified queue
- **Type:** User
- **Description:** As a user, I need a “My work” view that shows assigned approvals, failed deliveries, review-required locales, draft campaigns, and due items.
- **User value:** Eliminates hunting across six workspaces.
- **Priority:** **Must have**
- **Rationale:** Exception-driven, repeated use is likely to dominate daily behavior.
- **Acceptance criteria:**
  - Items can be filtered by type, priority, due date, workspace, and status.
  - Each item shows why it needs attention and its next permitted action.
  - Opening and returning to an item preserves filters and scroll position.
  - Counts update after the underlying action completes.

### UR-02: Understand status and next action
- **Type:** User
- **Description:** As a user, I need every workflow state to explain what happened, who owns the next step, and what I can do.
- **User value:** Reduces uncertainty and support needs.
- **Priority:** **Must have**
- **Rationale:** Current cards surface state codes with little interpretation.
- **Acceptance criteria:**
  - Status components include human-readable label, explanation, timestamp, and owner where applicable.
  - Blocked states identify the blocking condition.
  - System state codes remain available only in technical details, not as the primary label.
  - No enabled action is presented if it cannot complete or start a real operation.

### UR-03: Safely edit and compare content
- **Type:** User
- **Description:** As a creator or reviewer, I need to edit content, see autosave state, compare versions, and restore a prior version.
- **User value:** Supports iterative content work without losing changes.
- **Priority:** **Must have**
- **Rationale:** Generated content is rarely published unchanged, but a full editor/version experience is absent.
- **Acceptance criteria:**
  - Edits autosave with visible saving/saved/failed state.
  - Every submitted approval references an immutable version.
  - Users can view a line/word-level diff and restore an earlier version.
  - Concurrent edits trigger conflict handling rather than silent overwrite.

### UR-04: Review in context
- **Type:** User
- **Description:** As a reviewer, I need to see the content, change history, findings, campaign goal, requester, risk, and prior decisions in one review view.
- **User value:** Faster and more defensible decisions.
- **Priority:** **Must have**
- **Rationale:** The current approval list does not expose a complete decision environment.
- **Acceptance criteria:**
  - Reviewers can approve, request changes, or reject with a reason.
  - High-risk self-approval remains prohibited.
  - Request-changes creates an actionable task for the owner.
  - Decisions, reasons, and reviewed version are recorded in provenance.

### UR-05: Publish without duplicate-post anxiety
- **Type:** User
- **Description:** As a publisher, I need confirmation of account, content version, channels, schedule, and retry behavior before publishing.
- **User value:** Increases trust and prevents costly mistakes.
- **Priority:** **Must have**
- **Rationale:** Partial delivery and retry are supported, but idempotency and persistent status are gaps.
- **Acceptance criteria:**
  - The confirmation step lists exact channels/accounts and whether each action is immediate or scheduled.
  - Repeated submission with the same idempotency key cannot create duplicate posts.
  - Retry defaults to failed/retryable channels only.
  - Successfully published channels are clearly protected from accidental re-send.

### UR-06: Reuse proven setup
- **Type:** User
- **Description:** As a campaign manager, I need to duplicate prior campaigns and save reusable templates.
- **User value:** Reduces repetitive data entry.
- **Priority:** **Should have**
- **Rationale:** Repeated channel and audience patterns are likely.
- **Acceptance criteria:**
  - Users can duplicate a campaign without copying performance or delivery records.
  - Templates can include brief structure, channels, brand, locales, approval path, and schedule defaults.
  - Users can review all inherited values before generation.

## Functional requirements

### FR-01: Wire functional campaign creation and generation
- **Type:** Functional
- **Description:** The Campaign workspace shall submit a structured brief and create linked channel assets through the existing generation services.
- **User value:** Makes the primary entry point operational.
- **Priority:** **Must have**
- **Rationale:** The reviewed form is static and underspecified.
- **Acceptance criteria:**
  - Fields include campaign name, objective, audience, message, CTA, brand voice, channels, source language, target locales, deadline, and optional instructions.
  - Validation errors appear next to the affected field and preserve entered values.
  - Generation progress is shown per channel.
  - Successful assets remain available if another channel fails.
  - Failed assets can be retried individually.

### FR-02: Introduce campaign and asset detail routes
- **Type:** Functional
- **Description:** Every campaign and asset list item shall open a persistent detail view with related records and actions.
- **User value:** Preserves context and supports resumption.
- **Priority:** **Must have**
- **Rationale:** Current cards are summaries without navigation.
- **Acceptance criteria:**
  - Stable URLs exist for campaign and asset detail.
  - Detail shows status, owner, timestamps, versions, approvals, localization, delivery, provenance, and analytics links.
  - Browser back/forward navigation behaves predictably.
  - Missing or unauthorized resources have distinct, accessible states.

### FR-03: Integrate live validation into editing and publishing
- **Type:** Functional
- **Description:** Platform and brand/compliance validation shall run on the current asset version and expose actionable issue details.
- **User value:** Prevents late-stage surprises and unsafe publication.
- **Priority:** **Must have**
- **Rationale:** A strong validation API exists but is not visibly integrated into the editor/publish workspace.
- **Acceptance criteria:**
  - Text validation updates after a short debounce and can be manually rerun.
  - Results identify platform, rule, severity, current value, limit, and suggested action.
  - Publishing is blocked for unresolved errors and may proceed with warnings after explicit acknowledgment.
  - Validation timestamps and constraint registry version are recorded.

### FR-04: Provide real channel previews
- **Type:** Functional
- **Description:** The Publish center shall render previews using the selected asset version and platform-specific layout/constraints.
- **User value:** Users can verify the actual output before distribution.
- **Priority:** **Must have**
- **Rationale:** Existing preview panels are placeholders.
- **Acceptance criteria:**
  - Preview reflects text, media metadata, truncation, link treatment, and selected account.
  - Unsupported preview elements are explicitly labeled.
  - Switching channels does not lose edits.
  - The preview identifies whether it is an approximation or source-faithful rendering.

### FR-05: Complete approval actions and assignments
- **Type:** Functional
- **Description:** The approval workflow shall support assignment, due date, comments, decisions, and state transitions from the UI.
- **User value:** Enables governance without API calls.
- **Priority:** **Must have**
- **Rationale:** Backend invariants exist, but the list UI offers no complete action model.
- **Acceptance criteria:**
  - Authorized reviewers can approve, request changes, or reject.
  - Decision reasons are required for request changes/reject and configurable for approval.
  - Assignment and reassignment are audited.
  - Notifications are emitted for assignment and decision events.

### FR-06: Persist scheduler and publish history
- **Type:** Functional
- **Description:** Schedules, publish attempts, responses, retries, and external identifiers shall be stored in the primary persistence layer.
- **User value:** Reliable operation across restarts and devices.
- **Priority:** **Must have**
- **Rationale:** In-memory scheduling/status is explicitly identified as a production gap.
- **Acceptance criteria:**
  - Scheduled jobs survive restart and execute once.
  - Every attempt has status, timestamps, retry count, normalized error, and external ID/URL when available.
  - Users can list and filter real publish history.
  - Cancellation and rescheduling are transactional and audited.

### FR-07: Add safe retry and remediation actions
- **Type:** Functional
- **Description:** Failed operations shall present operation-specific remediation and retry only eligible sub-operations.
- **User value:** Faster recovery with lower duplicate risk.
- **Priority:** **Must have**
- **Rationale:** Current recovery is generic despite selective retry logic in the domain.
- **Acceptance criteria:**
  - Error details distinguish credentials, rate limit, validation, provider, network, and unknown failures.
  - Retry selection excludes successful channels/locales by default.
  - Credentials errors link to account repair.
  - Retry results update the original batch rather than creating an unrelated record.

### FR-08: Add brand voice conflict resolution and test mode
- **Type:** Functional
- **Description:** Brand voice users shall be able to resolve conflicting rules and test a draft profile against sample content before activation.
- **User value:** Makes activation understandable and safe.
- **Priority:** **Should have**
- **Rationale:** Activation is simply hidden when conflict exists.
- **Acceptance criteria:**
  - Conflicting rules are grouped and explain why they conflict.
  - Users can edit, merge, disable, or choose a rule while retaining evidence.
  - A test panel compares draft and active profile output/compliance.
  - Activation records the exact rule version and actor.

### FR-09: Add localization comparison and reviewer workflow
- **Type:** Functional
- **Description:** Locale variants shall support side-by-side comparison, issue explanation, comments, assignment, and per-locale decision.
- **User value:** Improves localization quality and throughput.
- **Priority:** **Should have**
- **Rationale:** The current locale matrix shows score/content but not a complete QA interaction.
- **Acceptance criteria:**
  - Source and target content can be viewed side by side.
  - Quality dimensions and terminology issues are explained.
  - Reviewers can approve, request changes, or reject one locale without blocking others.
  - Approved locales retain the reviewed version and reviewer identity.

### FR-10: Connect analytics to operational entities
- **Type:** Functional
- **Description:** Analytics views and APIs shall expose navigable links to campaign, asset, version, channel, experiment, and delivery records.
- **User value:** Converts metrics into decisions and reuse.
- **Priority:** **Should have**
- **Rationale:** Current analytics are powerful but operationally isolated.
- **Acceptance criteria:**
  - A metric can be drilled down to contributing assets and deliveries.
  - Content score components link to their calculation explanation and remediation.
  - A/B results show variant content and decision history.
  - Users can clone a selected asset/campaign from a performance view.

### FR-11: Add search, filtering, and bulk actions
- **Type:** Functional
- **Description:** Major lists shall support query, sort, filters, pagination, saved views, and permission-aware bulk actions.
- **User value:** Supports daily operation at scale.
- **Priority:** **Should have**
- **Rationale:** Current lists are simple cards with limited fields.
- **Acceptance criteria:**
  - Search covers relevant names, IDs, campaign, owner, and content snippets.
  - Filters are reflected in the URL and can be saved.
  - Bulk actions show eligibility and exclude invalid selections.
  - Pagination or virtualized loading prevents unbounded page rendering.

### FR-12: Add platform account connection management
- **Type:** Functional
- **Description:** Users with permission shall connect, inspect, refresh, and disconnect publishing accounts through OAuth-based flows.
- **User value:** Removes hidden configuration and makes delivery readiness visible.
- **Priority:** **Must have**
- **Rationale:** Current token storage exists, but full OAuth, refresh, and credential health are identified gaps.
- **Acceptance criteria:**
  - Connection uses the platform’s supported authorization flow.
  - Access tokens are encrypted and never displayed after capture.
  - Account status shows scopes, expiry, last validation, and actionable failure.
  - Disconnecting prevents new publishes without deleting historical records.

### FR-13: Add notifications and task handoffs
- **Type:** Functional
- **Description:** The system shall notify relevant users about assignments, requested changes, approvals, publish failures, token expiry, and locale review needs.
- **User value:** Reduces manual coordination.
- **Priority:** **Should have**
- **Rationale:** Multi-role workflows need timely handoff signals.
- **Acceptance criteria:**
  - In-product notifications link to the exact record and next action.
  - Users can configure email/in-product preferences by event type.
  - Duplicate notifications are suppressed for the same event.
  - Read/acted status is synchronized across sessions.

## Non-functional requirements

### NFR-01: Accessibility and inclusive interaction
- **Type:** Non-functional
- **Description:** All new workspaces and interactions shall meet WCAG 2.2 AA, including keyboard, screen-reader, zoom, reflow, contrast, error identification, and focus management.
- **User value:** Makes the product usable by a broader range of users and preserves current accessibility intent.
- **Priority:** **Must have**
- **Rationale:** The existing shell targets WCAG 2.2 AA, but dynamic interactions require equivalent rigor.
- **Acceptance criteria:**
  - Automated accessibility checks pass on critical routes with no serious/critical issues.
  - Manual keyboard and screen-reader tests cover the full create-to-publish flow.
  - Async status and errors are announced without moving focus unexpectedly.
  - 200% zoom and narrow viewport preserve functionality without two-dimensional scrolling except where essential.

### NFR-02: Reliability, idempotency, and recoverability
- **Type:** Non-functional
- **Description:** State-changing operations shall be atomic where appropriate, idempotent where repetition is possible, and recoverable after interruption.
- **User value:** Protects content and prevents duplicate external actions.
- **Priority:** **Must have**
- **Rationale:** Publishing, scheduling, generation, and retries are vulnerable to network and restart failure.
- **Acceptance criteria:**
  - Publish, schedule, and webhook ingestion accept idempotency keys.
  - Retry tests cover timeout after external success.
  - Partial success is preserved and accurately represented.
  - Recovery point and audit records are created before irreversible external actions.

### NFR-03: Performance and feedback latency
- **Type:** Non-functional
- **Description:** Interactive pages shall respond quickly and long-running operations shall provide progressive feedback.
- **User value:** Reduces perceived delay and repeated clicks.
- **Priority:** **Should have**
- **Rationale:** Generation, translation, validation, and publishing can be slow.
- **Acceptance criteria:**
  - Standard authenticated list/detail navigation has a p95 server response target of 500 ms under agreed reference load, excluding external-provider work.
  - Input validation feedback appears within 500 ms after debounce for typical text.
  - Long-running jobs expose queued/running/partial/completed/failed state and progress by subtask.
  - Actions are disabled or guarded while the same request is in flight.

### NFR-04: Security, privacy, and tenant isolation
- **Type:** Non-functional
- **Description:** All user-facing and workflow APIs shall enforce authentication, least privilege, tenant isolation, secure secret management, and auditable access.
- **User value:** Protects brands, credentials, unpublished content, and customer data.
- **Priority:** **Must have**
- **Rationale:** The current workspace documentation explicitly warns that tenant/object authorization is needed before shared use.
- **Acceptance criteria:**
  - Every repository query is tenant-scoped unless explicitly system-level.
  - Roles and permissions cover creator, reviewer, publisher, brand admin, auditor, and organization admin.
  - Secrets and tokens are encrypted at rest and redacted from logs/exports.
  - Security tests cover IDOR, cross-tenant access, CSRF for browser actions, and privilege escalation.

### NFR-05: Observability and supportability
- **Type:** Non-functional
- **Description:** User-visible operations shall emit correlated logs, metrics, traces, and audit events using non-secret identifiers.
- **User value:** Faster diagnosis and reliable status information.
- **Priority:** **Should have**
- **Rationale:** The product integrates multiple asynchronous and external services.
- **Acceptance criteria:**
  - Campaign, asset, job, publish, and request correlation IDs are queryable.
  - Dashboards report failure rate, latency, retry rate, queue age, and provider health.
  - User-facing errors include a support reference without exposing internals.
  - Audit events are immutable and time-ordered.

### NFR-06: Data lifecycle and compliance
- **Type:** Non-functional
- **Description:** Organizations shall have configurable retention, export, and deletion behavior for content, analytics identifiers, prompts, and audit data.
- **User value:** Supports enterprise governance and privacy obligations.
- **Priority:** **Should have**
- **Rationale:** Provenance and analytics can contain sensitive operational/user-linked data.
- **Acceptance criteria:**
  - Retention categories and defaults are documented.
  - Authorized admins can export organization data and request deletion where legally permitted.
  - Audit/provenance retention exceptions are explicit.
  - User identifiers in analytics can be pseudonymized or omitted.

## UX/UI requirements

### UX-01: Context-preserving navigation
- **Type:** UX/UI
- **Description:** Navigation shall preserve the selected campaign or asset as users move among creation, approval, publish, localization, provenance, and analytics.
- **User value:** Reduces reorientation and identifier hunting.
- **Priority:** **Must have**
- **Rationale:** The current global workspace navigation loses task context.
- **Acceptance criteria:**
  - Campaign/asset breadcrumbs and a context header appear on related pages.
  - Cross-workspace links retain the relevant resource.
  - Returning to a list restores filters and position.
  - The user can always identify the current organization, campaign, asset, and version.

### UX-02: Honest, stateful action feedback
- **Type:** UX/UI
- **Description:** Every action shall expose idle, validating, submitting, queued, running, partial, success, and failure states as applicable.
- **User value:** Prevents repeated clicks and builds trust.
- **Priority:** **Must have**
- **Rationale:** “Ready” and generic recovery are insufficient for real operations.
- **Acceptance criteria:**
  - Buttons show progress and prevent accidental duplicate submission.
  - Success messages identify what changed and provide the next action.
  - Field errors are inline; operation errors appear near the affected component.
  - Generic recovery content is not shown in the absence of a recoverable event.

### UX-03: Actionable empty and error states
- **Type:** UX/UI
- **Description:** Empty and error states shall be specific to the user’s role, data, and current workflow.
- **User value:** Helps users start or recover without documentation.
- **Priority:** **Must have**
- **Rationale:** Existing empty states are a good base but remain generic and non-interactive.
- **Acceptance criteria:**
  - Empty states include a primary action when the user has permission.
  - Errors distinguish no data, no access, disconnected account, invalid configuration, provider outage, and failed operation.
  - Recovery actions preserve user input.
  - Help text links to relevant guidance, not a generic documentation root.

### UX-04: Progressive disclosure of technical detail
- **Type:** UX/UI
- **Description:** Primary views shall use plain language while retaining expandable technical detail for power users.
- **User value:** Serves marketers and developers without overwhelming either group.
- **Priority:** **Should have**
- **Rationale:** Current states and APIs are technical, while target users span non-technical and technical roles.
- **Acceptance criteria:**
  - Primary status labels are user-centered.
  - IDs, payloads, model names, scores, and raw errors are available through details panels.
  - Copy/inspect actions are available for integration users.
  - Technical details never expose secrets.

### UX-05: Efficient high-volume list interaction
- **Type:** UX/UI
- **Description:** Users shall be able to scan and act on large queues using table/card views, density options, sticky filters, selection, and keyboard-friendly actions.
- **User value:** Improves operational throughput.
- **Priority:** **Should have**
- **Rationale:** Approval, localization, campaign, and delivery lists will grow beyond simple cards.
- **Acceptance criteria:**
  - Lists provide sortable columns and responsive card fallback.
  - Selection state is visible and announced.
  - Bulk action confirmation explains included/excluded items.
  - Keyboard users can complete selection and action without pointer input.

## Data and integration requirements

### DI-01: Unified relational resource model
- **Type:** Data/Integration
- **Description:** The data model shall formally relate organization, campaign, asset, asset version, generation, approval, localization variant, schedule, publish attempt, provenance record, experiment variant, and analytics event.
- **User value:** Enables end-to-end traceability and context.
- **Priority:** **Must have**
- **Rationale:** Separate stores and identifiers currently fragment the experience.
- **Acceptance criteria:**
  - Referential integrity is enforced for required relationships.
  - APIs return stable IDs and links for related resources.
  - Migration maps existing workflow records where possible and reports unmapped records.
  - Deletion/retention semantics are defined for each relationship.

### DI-02: Versioned workflow and API contracts
- **Type:** Data/Integration
- **Description:** UI and automation shall use versioned, documented contracts with consistent status, error, pagination, and idempotency semantics.
- **User value:** Predictable behavior for users and integrations.
- **Priority:** **Must have**
- **Rationale:** The application mixes versioned and unversioned endpoints and has differing error/status patterns.
- **Acceptance criteria:**
  - New workflow endpoints are under a versioned namespace.
  - Errors use a common structure with code, message, field, retryability, and correlation ID.
  - Pagination and filtering follow one convention.
  - Deprecation policy and migration notes are published.

### DI-03: External status reconciliation
- **Type:** Data/Integration
- **Description:** Publishing state shall be reconciled with external platforms through webhooks or safe polling where available.
- **User value:** Reflects actual delivery rather than only request-time success.
- **Priority:** **Should have**
- **Rationale:** Current status tracking may not capture later deletion, rejection, or asynchronous processing.
- **Acceptance criteria:**
  - Webhook signatures are verified and replay-protected.
  - External events update the corresponding attempt idempotently.
  - Unknown events are quarantined for investigation.
  - UI distinguishes submitted, accepted, externally confirmed, failed, and removed states.

### DI-04: Constraint registry governance
- **Type:** Data/Integration
- **Description:** Platform constraints shall include source, verification timestamp, effective version, and controlled update/review workflow.
- **User value:** Prevents false confidence from stale limits.
- **Priority:** **Should have**
- **Rationale:** A versioned registry exists, but automated freshness and governance are gaps.
- **Acceptance criteria:**
  - Every rule records source and last verification date.
  - Expired/stale rules generate an admin alert and user-facing caution where material.
  - Registry changes are reviewed, tested, versioned, and rollback-capable.
  - Validation records store the registry version used.

## Could-have and won’t-have-for-now requirements

### CH-01: Command palette and shortcuts
- **Type:** UX/UI
- **Description:** Provide quick navigation and common actions through a searchable command palette.
- **User value:** Speeds expert workflows.
- **Priority:** **Could have**
- **Rationale:** Valuable only after core workflows are stable.
- **Acceptance criteria:** Common navigation and record actions are searchable, permission-aware, and fully keyboard accessible.

### CH-02: Custom workflow designer
- **Type:** Functional
- **Description:** Allow organization admins to configure approval stages, risk routing, and conditional gates.
- **User value:** Supports enterprise process diversity.
- **Priority:** **Could have**
- **Rationale:** Market-relevant, but premature before one strong default workflow exists.
- **Acceptance criteria:** Configurations are versioned, validated, previewable, and do not permit bypassing mandatory security controls.

### WH-01: Autonomous publishing without human-configured governance
- **Type:** Business/Functional
- **Description:** Fully autonomous generation and publication with no user-configured approval or risk controls will not be pursued in the next version.
- **User value:** Avoids unsafe automation and scope dilution.
- **Priority:** **Won’t have for now**
- **Rationale:** The product’s strongest logic is governance, provenance, and recovery. Trust foundations must precede autonomy.
- **Acceptance criteria:** No workflow bypasses configured approvals, blocking validation errors, account authorization, or explicit automation policy.

### WH-02: Additional publishing platforms before workflow hardening
- **Type:** Business/Integration
- **Description:** New live publishing connectors beyond the currently implemented set will not be prioritized until persistent status, OAuth, idempotency, media handling, and reconciliation are production-ready.
- **User value:** Favors reliability over superficial breadth.
- **Priority:** **Won’t have for now**
- **Rationale:** Validation already covers more platforms than publishing; expanding connectors would amplify current operational risk.
- **Acceptance criteria:** Connector expansion requires completion of the publishing readiness gate and platform-specific support evidence.

---

# 6. New opportunities

## 1. Guided campaign cockpit

**Opportunity:** A context-first campaign page combining brief, assets, approvals, localization, publishing, provenance, and performance in one timeline.

**Why users may want it:** The current workspace navigation fragments one campaign across multiple functional pages. Campaign managers need a single place to resume and understand progress.

**Evidence/reasoning:** The data model already contains the necessary workflow objects, and the dominant UX gap is cross-workspace continuity, not missing domain breadth.

## 2. Exception-first operations dashboard

**Opportunity:** A dashboard prioritizing blocked approvals, expiring credentials, failed publishes, low-quality locales, stale schedules, and unusual analytics movement.

**Why users may want it:** Repeated users usually manage exceptions rather than creating everything from scratch each session.

**Evidence/reasoning:** The application already models failures, retryable channels, locale quality gates, approval risk, and anomalies. Surfacing them together is a logical synthesis.

## 3. Reusable playbooks

**Opportunity:** Organization templates that bundle campaign brief fields, brand voice, channels, locale set, validation rules, approval path, and schedule defaults.

**Why users may want it:** Marketing teams repeat launch, announcement, thought-leadership, incident, and evergreen campaign patterns.

**Evidence/reasoning:** The product already supports templates, scenarios, brand voices, channels, localization, and approvals separately. A playbook reduces repeated setup without inventing a new domain.

## 4. Explainable quality remediation

**Opportunity:** Convert compliance, platform, SEO, readability, and translation findings into one prioritized issue panel with “fix manually,” “apply suggestion,” and “regenerate affected section” actions.

**Why users may want it:** Multiple scores are useful only when users know what to change.

**Evidence/reasoning:** Existing analyzers expose violations and dimensions, but the workspace UI lacks actionable remediation.

## 5. Operational learning loop

**Opportunity:** Recommend a proven template, timing, channel variant, or voice treatment based on the organization’s own historical performance, with transparent evidence and user control.

**Why users may want it:** Users want to reuse what worked rather than interpret isolated metrics every time.

**Evidence/reasoning:** Analytics, A/B tests, content scoring, campaign structures, and brand versions already create the necessary signals. This should begin as evidence-based suggestions, not autonomous optimization.

## 6. Agency/client workspace boundaries

**Opportunity:** Client/brand switcher, segregated assets and credentials, client-scoped approvals, and branded exports.

**Why users may want it:** Multi-brand management and tenant concepts align naturally with agency workflows.

**Evidence/reasoning:** The application already supports multiple brand profiles and organization concepts, but the UI does not expose safe multi-client operations. This opportunity is justified only after tenant isolation is complete.

## 7. Human review analytics

**Opportunity:** Measure approval cycle time, rework reasons, common validation failures, localization bottlenecks, and publish recovery rate.

**Why users may want it:** Content operations leaders need process efficiency, not just content performance.

**Evidence/reasoning:** Approval, provenance, state transitions, retries, and timestamps supply a strong foundation. This extends current analytics logically into operational analytics.

---

# 7. Final recommendation

## What should be built first

Build a **vertical, end-to-end campaign workflow** before adding more isolated features. The first increment should cover one authenticated organization, one campaign, multiple channel assets, real editing/versioning, inline validation, approval, real preview, persistent schedule/publish status, and selective recovery.

### Recommended implementation sequence

1. **Security and data foundation**
   - Tenant-scoped relational model.
   - Role/permission model.
   - Unified related-resource IDs.
   - Persistent job/publish state and idempotency.

2. **Campaign and asset cockpit**
   - Structured brief.
   - Generation progress by channel.
   - Asset editor, autosave, versions, and details.
   - Context-preserving navigation.

3. **Validation and approval loop**
   - Live platform/brand/compliance findings.
   - Actionable remediation.
   - Complete approval decisions, assignment, comments, and audit.

4. **Publish confidence and recovery**
   - OAuth account center.
   - Real previews.
   - Timezone-safe scheduling.
   - Confirmation, idempotency, persistent history, and selective retry.

5. **Localization and learning loop**
   - Side-by-side locale QA and per-locale review.
   - Campaign-linked analytics and operational insights.

## UI and workflow improvements to prioritize immediately

- Replace every non-functional visible control with a wired action or remove/disable it with an explanation.
- Make cards clickable and introduce campaign/asset detail routes.
- Replace the static “Ready” message with real operation state.
- Remove the always-visible generic Recovery panel and show contextual recovery only after an actual issue.
- Add a persistent campaign/asset context header and breadcrumbs.
- Translate technical workflow states into plain-language labels with next actions.
- Populate previews from actual content and integrate platform validation inline.
- Add save state, version history, and diff before expanding content-generation features.

## Requirements with the highest adoption and efficiency impact

1. **BR-01 / FR-01:** Complete the UI-based create-to-publish loop.
2. **DI-01 / UX-01:** Unify resource relationships and preserve context.
3. **UR-03:** Provide safe editing, autosave, and version comparison.
4. **FR-03 / FR-04:** Integrate validation and real previews.
5. **UR-04 / FR-05:** Make approval complete and contextual.
6. **FR-06 / NFR-02:** Persist scheduling/publishing and prevent duplicates.
7. **FR-07 / UX-02:** Provide precise feedback and selective recovery.
8. **NFR-04:** Enforce tenant isolation and permission-aware operations.

## Product success measures for the next version

The release should be evaluated with user-centered and operational metrics, not only endpoint/test coverage:

- Median time from campaign brief to review-ready assets.
- Percentage of campaigns completed without external API/tool use.
- Validation issues resolved before approval/publish.
- Approval cycle time and request-changes rate.
- Publish success rate and duplicate-post incident count.
- Recovery success rate after partial failure.
- Percentage of users who resume work through “My work” or a campaign detail page.
- Task completion, error rate, and System Usability Scale or equivalent usability score from representative users.
- Accessibility completion rate for critical tasks using keyboard and screen reader.
- Cross-tenant authorization test pass rate and security incident count.

## Research validation plan

Before finalizing lower-priority requirements, conduct:

1. **6–8 contextual interviews** across campaign managers, social publishers, reviewers, brand owners, and localization reviewers.
2. **Task-based usability tests** on campaign creation, approval, failed publish recovery, and locale review.
3. **Telemetry instrumentation** for workspace entry, task starts/completions, validation loops, retries, time in state, and abandonment.
4. **Card-sorting or tree testing** to validate whether stage-based workspaces plus context navigation match user expectations.
5. **Prototype comparison** between the current workspace model and a campaign cockpit/exception dashboard model.

The core product opportunity is not more capability breadth. It is converting ContentForge’s broad, well-tested backend into a trustworthy, connected, low-friction daily workspace where users can understand state, take the next action, recover safely, and learn from outcomes.
