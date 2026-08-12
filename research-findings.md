# Research Findings

## Executive Summary

ContentForge is a technically broad, English-language content-operations product, not yet a family product. Its React interface exposes thirteen workspaces and many specialist concepts at once. The visual system is coherent and calm, and several modules have solid loading, empty, error, progress, and retry states. However, the dominant experience is a feature map rather than a guided outcome. A new user must understand campaigns, assets, approvals, localization, governance, analytics, transcreation, video, connections, and admin before the product has established a simple first success.

The strongest commercially plausible interpretation of the requested family scenario is not “an app for children.” It is a **creator household or family-run micro-business** in which one or two adults own the account, a teenager or other family member contributes ideas and drafts, and publishing, billing, credentials, and privacy remain adult-controlled. General child-directed positioning would create disproportionate safeguarding, consent, data-minimization, and moderation obligations. The next pass should therefore preserve ContentForge's professional engine but add a simplified household-facing layer.

**Top recommendation:** build one coherent, mobile-friendly journey around (1) a role-aware Family Home, (2) guardian review and safe publishing, and (3) a goal-based create-to-publish wizard. Hide specialist modules behind progressive disclosure. Sell saved time, safe collaboration, and reliable publishing, not a long feature list.

## Project Understanding

### Verified current product

- **Purpose:** AI-assisted creation, brand voice and visual identity, campaign workflow, approvals, localization/transcreation, publishing, analytics, AI visibility, and blog/script-to-video. Verified in `README.md`, `CHANGELOG.md`, `src/`, and `docs/`.
- **Stack:** FastAPI, Pydantic v2, SQLAlchemy/SQLite, React 19, TypeScript, and Vite. Video rendering uses MoviePy and imageio-ffmpeg. See `pyproject.toml` and `frontend/package.json`.
- **Principal shell:** `frontend/src/main.tsx` loads `/api/v1/workspace-overview`, renders a persistent left sidebar, and switches hash routes via `frontend/src/navigation.ts`.
- **Primary user flow:** My Work or Campaigns -> campaign cockpit -> create channel asset -> modal editor -> save revision -> request review. Specialist flows exist for Brand Kit, Transcreation, and Video.
- **Maturity:** broad implementation with extensive backend tests and focused frontend tests, but uneven product integration. The archive contains 71 Python test modules, unit/component tests for Brand Kit, Transcreation, and Video, and one Playwright transcreation specification.

### Existing GUI and observed use

The shell uses a dark green fixed sidebar, a light canvas, cards, status pills, and generous spacing (`frontend/src/styles.css`). Users can navigate directly to My Work, Campaigns, Content, Calendar, Approvals, Localization, Transcreate, Analytics, Brand Governance, Brand Kit, Connections, and Admin. The `video` route exists but is deliberately omitted from `NAV_ITEMS`, so the feature is implemented yet not normally discoverable (`frontend/src/navigation.ts`).

Strengths include consistent visual tokens, explicit loading and empty states, accessible alert/status roles in specialist screens, revision-aware editing, a five-step video wizard, and retry-oriented failure handling. The strongest UI is the Video Wizard because it narrows a complex operation into a staged path (`frontend/src/video.tsx:VideoWizard`). Brand Kit also provides immediate visual feedback, while Transcreation makes risks visible beside the text.

The core shell is less mature. Many workspaces are summary panels rather than complete task environments. The editor is a modal with a single textarea and three actions, while the documentation describes richer version comparison, inline findings, platform preview, and governance. There is no global onboarding, search, notification center, contextual help, pricing/usage surface, or clear first-run value path in the inspected frontend.

## Current-State Gap Analysis

| Area | Current evidence | Gap and family impact |
|---|---|---|
| Information architecture | 13 route concepts in `navigation.ts` | Too many equally weighted choices. A parent or teenager cannot predict where to start. |
| First use | Shell immediately requests workspace overview | No goal selection, sample project, setup checklist, or time-to-value promise. |
| Roles | Profile is hard-coded as “Content team / Professional workspace” | No household identity, invitations, minor/contributor roles, or permission preview. |
| Creation | Campaign creation asks name, brief, comma-separated channels | This is implementation-shaped input, not a guided “what are you trying to make?” experience. |
| Editor | Single modal textarea in `main.tsx:Editor` | No mobile idea capture, preview-first editing, comments, diff, or contextual guidance. |
| Review | Approval queue displays asset id, risk, and state | Weak human context. Family approvers need thumbnail, author, changes, deadline, and plain-language risk. |
| Safety | Some workflow controls and audit concepts exist | No guardian gate, age handling, child privacy mode, channel credential boundary, or adult-only billing controls. |
| Discoverability | Video route works but is absent from navigation | Capabilities can become “hidden inventory” rather than perceived value. |
| Responsiveness | Sidebar collapses to icon-only at 850px | There is no true mobile navigation, labels disappear, and touch workflows are not the primary design. |
| Accessibility | Specialist modules use `role=alert`, `aria-live`, and labels | The shell lacks skip navigation; icon-only collapsed navigation and modal focus behavior need formal WCAG 2.2 testing. |
| Trust and pricing | No visible usage, cost preview, privacy explanation, or cancellation model | Families will not pay for unpredictable credits or unclear data use. |
| Product coherence | Many powerful modules are present | Breadth increases cognitive load and support cost before a single repeatable job is proven. |

## Target Users and Jobs to Be Done

### Recommended primary segment

**Family-run creator household or micro-business.** An adult owner manages the brand, accounts, payments, and final publishing. Another adult or teenager contributes ideas, drafts, images, translations, or video scene choices. The family wants to turn everyday knowledge into consistent posts, newsletters, shop updates, or community content without buying and learning several separate tools.

### Roles

- **Parent owner:** “Help me plan and publish consistently without endangering family privacy or wasting evenings.”
- **Parent collaborator:** “Let me review, edit, or schedule work with a clear handoff.”
- **Teen contributor:** “Let me add ideas and creative work from my phone without access to credentials, billing, or accidental publishing.”
- **Younger child:** only an optional, adult-mediated contribution mode such as selecting approved photos or recording an idea. No independent publishing or public profile is recommended.

### Core jobs

1. Capture a real-life idea quickly and turn it into an approved draft.
2. Know what each family member should do next.
3. Keep private material, credentials, and billing adult-only.
4. Review the exact version before anything becomes public.
5. Reuse family brand, tone, templates, and channels without repeated setup.
6. See whether the subscription saved time or improved results.

## Target-Market Pain Points

| Problem | Segment | Recurrence | Evidence | Confidence | Implication |
|---|---|---:|---|---|---|
| Tool overload and context switching across creation, approval, scheduling, and analytics | Small teams, creators, agencies | Repeated across category comparisons | Planable, Buffer, Hootsuite, Canva and ContentForge's own earlier research all consolidate parts of this workflow [S1][S2][S4][S5][S15] | HIGH | Do not add another top-level module. Unite existing capabilities around one job. |
| Approval and version ambiguity | Teams and family collaborators | Common product-category requirement | Planable and Sprout document formal approval workflows; ContentForge already models revision-bound approval [S1][S3][S15] | HIGH | Make adult approval the differentiating safety feature, not an admin screen. |
| Social publishing failures and unclear retries | Owners responsible for public accounts | Repeated in product reviews and the project's own recovery design | ContentForge has selective retry and partial-success semantics; Hootsuite and Buffer position centralized scheduling as core value [S2][S4][S15] | MEDIUM-HIGH | Surface plain-language recovery on Home and preserve successful channels. |
| Subscription and credit uncertainty | Price-sensitive households and micro-businesses | Recurring SaaS buying objection | Competitors use free, per-channel, per-user, or tiered subscriptions [S1][S2][S4][S5][S6] | MEDIUM | Show included usage, forecast expensive AI/video actions, and cap spend. |
| Children and teens need bounded participation | Families | Structural, not anecdotal | COPPA and age-appropriate design guidance emphasize parental consent, data minimization, and child-appropriate defaults [S7][S8] | HIGH | Adult-owned accounts, no behavioral advertising, minimal child data, and guardian-controlled permissions are prerequisites. |
| Mobile capture is essential for household collaboration | Creators and teens | Category baseline | Canva, Adobe Express, Buffer, and Hootsuite all position mobile creation or management as part of the workflow [S2][S4][S5][S6] | HIGH | Replace icon-only collapse with a real bottom/drawer navigation and a one-tap idea inbox. |
| AI output needs human control and provenance | Parents, brands, regulated teams | Increasing category concern | NIST AI RMF and the project's approval/audit architecture support human oversight [S9][S15] | HIGH | Label AI-generated material, preserve sources and revisions, and require adult review for public actions. |

## Competitor Weaknesses

- **Canva:** extremely broad and visually friendly, but its breadth can make structured approval, governance, and repeatable multi-step content operations feel secondary. ContentForge can win on “safe handoff from idea to approved publication,” not on design breadth [S5].
- **Adobe Express:** strong creation and brand tooling, but a household still needs a clear operational queue and role-specific publish boundary. ContentForge can coordinate work rather than compete as a full graphics suite [S6].
- **Buffer:** approachable scheduling and per-channel packaging, but it is primarily a publication and engagement layer. ContentForge can differentiate before publishing through brand, localization, approval, and reuse [S2].
- **Planable:** excellent collaboration and approvals, but less differentiated as an AI content production, localization, and video engine. ContentForge should copy its review clarity while keeping a smaller family-facing surface [S1].
- **Hootsuite:** powerful and mature, but generally positioned for professional social teams. A family micro-business may perceive it as expensive and operationally heavy. ContentForge can offer a calmer, outcome-based entry product [S4].

## Competitor Comparison

Current public pages should be checked again immediately before commercial launch because packaging changes frequently. This research intentionally avoids unverified exact prices.

| Product | Positioning/core flow | Packaging signal | UX strength | Exploitable gap |
|---|---|---|---|---|
| Canva | Template -> visual creation -> brand -> content planning | Free plus paid individual/team tiers [S5] | Familiar, visual, quick first result | Weak differentiation on governed family handoffs and publication audit. |
| Adobe Express | Quick creative production, templates, brand, scheduling | Free and premium packaging [S6] | Polished creation and cross-device ecosystem | Less purpose-built “who does what next” household operations. |
| Buffer | Connect channels -> create queue -> publish -> analyze | Free and paid plans with channel-based logic [S2] | Simple scheduler mental model | Limited end-to-end brand governance/localization/video coordination. |
| Planable | Workspace -> create -> comment -> approve -> schedule | Free trial/free entry and paid workspace/team tiers [S1] | Review and approval clarity | Not a family-specific safety or broader AI production system. |
| Hootsuite | Connect accounts -> calendar -> publish -> monitor/analyze | Professional tiered subscription [S4] | Comprehensive professional console | High perceived complexity for households and tiny businesses. |

## Validated Demand Signals

1. **Collaboration beside the asset:** Planable makes feedback and approval part of the content review flow, and Sprout supports multi-step approval rules [S1][S3]. Implication: ContentForge should stop presenting approval primarily as a separate list of IDs.
2. **One calendar and reliable scheduling:** Buffer and Hootsuite center their value on planning and publishing across channels [S2][S4]. Implication: the calendar must become actionable, not a mostly decorative month grid.
3. **Templates and immediate visual output:** Canva and Adobe Express reduce time to first result through templates [S5][S6]. Implication: goal-based starters should precede workspace selection.
4. **Governed AI:** NIST's AI risk guidance emphasizes governance and human oversight, while ContentForge already has version, approval, and audit foundations [S9][S15]. Implication: “adult reviewed” and “exact version published” can be a trust proposition.
5. **Child privacy by default:** FTC COPPA resources and the UK ICO Children's Code require special treatment of children's data and defaults [S7][S8]. Implication: do not launch child accounts as a cosmetic role label.
6. **Accessible touch interaction:** WCAG 2.2 adds focus and target-size expectations relevant to icon-only mobile navigation and dense action areas [S10]. Implication: family mode should be touch-first and keyboard/screen-reader tested.

## Market and Pricing Evidence

The project competes with overlapping categories rather than one clean market: social scheduling, creative production, content collaboration, AI writing, localization, and video generation. A defensible TAM cannot be calculated from the available evidence without double counting, so no TAM or CAGR is asserted.

Observed competitor packaging shows four recurring patterns: freemium entry, feature-tier subscriptions, per-user/workspace charging, and per-channel or usage limits [S1][S2][S4][S5][S6]. For a family-run micro-business, the recommended offer is:

- **Free:** one adult, one project, limited drafts, watermark-free text, no connected publishing.
- **Family Creator:** one adult owner plus up to four contributors, guardian review, two channels, clear monthly AI/video allowance, and a hard spend cap.
- **Family Business:** two adult admins, more channels, brand kits, localization, analytics, audit export, and priority recovery.
- Do not charge per child/contributor. Charge for adult-controlled value: connected channels, active brands, automation, and expensive generation.
- Offer annual savings but keep monthly cancellation and usage export simple.

Willingness to pay should be validated with a fake-door pricing test and 10 to 15 moderated interviews. The decisive question is not “Would you pay for AI?” but “Would you pay to save three or more hours per week and prevent accidental or off-brand publishing?”

## Modern UX Expectations

### Baseline screens

1. Welcome and goal selection.
2. Role-aware Home with one next action.
3. Projects/Campaigns with template starters.
4. Mobile idea inbox.
5. Preview-first editor.
6. Review inbox with author, revision, diff, risk, and due date.
7. Calendar with actual scheduling controls.
8. Connections and adult-only billing/privacy center.
9. Activity and value report.

### State design

Every async action needs labeled loading, success, empty, disabled, partial-success, offline, and retry states. Existing specialist screens are a good foundation. The core shell should add skeletons, preserve drafts across errors, prevent duplicate publish, and explain which channel succeeded.

### Navigation and progressive disclosure

Default family navigation should contain **Home, Create, Projects, Review, Calendar**. Brand, analytics, localization, video, connections, and admin should appear contextually or under “More.” Adults can enable Expert mode. Children and contributors should never see billing, credentials, member removal, or direct publish controls.

### Accessibility, privacy, and trust

Target WCAG 2.2 AA, minimum touch target expectations, visible focus, skip navigation, focus trapping/restoration in dialogs, non-color status cues, reduced motion, captions/transcripts for generated video, and readable error recovery [S10]. For minors, collect the minimum data, avoid public profiles and targeted advertising, use high-privacy defaults, provide parental consent/management, and define deletion/retention behavior before launch [S7][S8]. AI-generated content should be labeled, source/revision history retained, and costly generation should show a usage estimate.

## Open-Source and Automation Opportunities

| Opportunity | Fit with stack | Use |
|---|---|---|
| Radix UI or React Aria | React/TypeScript [S11][S12] | Accessible dialogs, menus, tabs, focus management, and composable primitives. |
| React Hook Form + Zod | React/TypeScript [S13] | Replace ad hoc form state and improve field-level validation and draft preservation. |
| TanStack Query | React [S14] | Cached server state, retries, request cancellation, optimistic updates only where safe. |
| axe-core + Playwright | Existing component/E2E approach [S10][S16] | Automated accessibility and family-role permission regression tests. |
| Web Share API and PWA shell | Browser standards | Mobile idea capture, installability, and share-to-ContentForge without native apps. |
| OpenTelemetry | FastAPI/worker compatible [S17] | Measure time-to-first-value, generation failures, publish recovery, and funnel abandonment. |
| Existing job/audit infrastructure | `src/product_ops.py`, video worker, approval models | Reuse idempotency, selective retry, exact-revision approval, and audit rather than inventing a parallel family backend. |

## Differentiation Opportunities

| Capability | Problem/user | Evidence and competitor gap | Value | Complexity | Risk | Priority | Success criterion |
|---|---|---|---|---|---|---|---|
| Family Home and role-aware navigation | Everyone gets the same expert UI | Category tools are team-oriented; child privacy requires bounded roles [S1][S3][S7][S8] | Faster activation and safer collaboration | MEDIUM | Treating a role label as real safety | P0 | 80% of test families identify their next action in 10 seconds; no restricted route is reachable by contributor role. |
| Guardian review and publish gate | Minors or collaborators could publish the wrong version | Approval is validated demand; current project already versions decisions [S1][S3][S15] | Trust, fewer mistakes, paid-plan anchor | MEDIUM | Permission bypass or stale approval | P0 | 100% of public publish attempts by a minor/contributor require current-revision adult approval. |
| Goal-based create-to-publish wizard | New users face 13 modules | Canva/Adobe Express win with templates; Video Wizard proves the pattern internally [S5][S6] | First-session value | MEDIUM | Oversimplifying expert needs | P0 | Median first approved draft under 10 minutes in usability tests. |
| Mobile idea inbox | Ideas occur away from desktop | Cross-device creation is category baseline [S2][S4][S5][S6] | Habit formation and family participation | MEDIUM | Upload privacy and offline conflicts | P1 | 50% of active households capture at least one idea weekly. |
| Transparent usage and family spend controls | AI/video costs feel unpredictable | Competitors use limits and paid tiers [S1][S2][S4][S5][S6] | Pricing trust and lower refund risk | LOW-MEDIUM | Incorrect cost forecast | P1 | Fewer than 2% of paid accounts exceed a chosen cap; usage-related support tickets under 3 per 100 accounts/month. |
| Weekly value and learning report | Families cannot tell whether the tool earns its fee | Analytics exists but is operational rather than outcome-led | Retention and upsell | LOW | Vanity metrics | P1 | 40% weekly report open rate and 20% action click-through among active paid households. |
| Privacy-safe family media vault | Personal images and child content create risk | Child privacy standards require minimization/default protection [S7][S8] | Trust differentiation | HIGH | Safeguarding, consent, deletion, moderation | P2 | 100% asset deletion SLA compliance; zero public assets without explicit adult action. |

## User Stories (BDD)

```json
[
  {
    "id": "US-001",
    "epic": "Family Workspace and Guided Home",
    "role": "parent owner",
    "action": "create a household workspace with clear roles",
    "benefit": "everyone gets an appropriate, understandable experience",
    "story": "As a parent owner, I want to create a household workspace with clear roles, so that everyone gets an appropriate, understandable experience.",
    "gui_flow": [
      "User opens Welcome screen -> sees three goal choices and a 3-minute setup estimate",
      "User selects Family creator or Family business -> setup asks for workspace name and adult owner",
      "User adds a member or chooses Skip for now -> role choices explain permissions in plain language",
      "User selects a role -> preview shows exactly what that member can view and do",
      "User finishes setup -> Home shows one recommended next action and a starter project"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the user has a valid workspace and network connection",
        "when": "create a household workspace with clear roles",
        "then": "the requested state is persisted, shown after refresh, and the primary flow completes in at most 6 screens"
      },
      {
        "type": "given",
        "text": "the workspace has no other members or no prior content",
        "when": "create a household workspace with clear roles",
        "then": "the interface shows a useful empty-state action and never presents an unlabelled blank panel"
      },
      {
        "type": "given",
        "text": "the API returns an error or the connection is interrupted",
        "when": "create a household workspace with clear roles",
        "then": "no duplicate object or publication is created, entered data remains available, and a retry control names the failed step"
      }
    ]
  },
  {
    "id": "US-002",
    "epic": "Family Workspace and Guided Home",
    "role": "teen contributor",
    "action": "join a shared project without seeing billing or credentials",
    "benefit": "I can contribute safely without accessing adult controls",
    "story": "As a teen contributor, I want to join a shared project without seeing billing or credentials, so that I can contribute safely without accessing adult controls.",
    "gui_flow": [
      "User opens Welcome screen -> sees three goal choices and a 3-minute setup estimate",
      "User selects Family creator or Family business -> setup asks for workspace name and adult owner",
      "User adds a member or chooses Skip for now -> role choices explain permissions in plain language",
      "User selects a role -> preview shows exactly what that member can view and do",
      "User finishes setup -> Home shows one recommended next action and a starter project"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the user has a valid workspace and network connection",
        "when": "join a shared project without seeing billing or credentials",
        "then": "the requested state is persisted, shown after refresh, and the primary flow completes in at most 6 screens"
      },
      {
        "type": "given",
        "text": "the workspace has no other members or no prior content",
        "when": "join a shared project without seeing billing or credentials",
        "then": "the interface shows a useful empty-state action and never presents an unlabelled blank panel"
      },
      {
        "type": "given",
        "text": "the API returns an error or the connection is interrupted",
        "when": "join a shared project without seeing billing or credentials",
        "then": "no duplicate object or publication is created, entered data remains available, and a retry control names the failed step"
      }
    ]
  },
  {
    "id": "US-003",
    "epic": "Family Workspace and Guided Home",
    "role": "parent owner",
    "action": "switch between family projects and see the next action",
    "benefit": "I can coordinate work without searching across modules",
    "story": "As a parent owner, I want to switch between family projects and see the next action, so that I can coordinate work without searching across modules.",
    "gui_flow": [
      "User opens Welcome screen -> sees three goal choices and a 3-minute setup estimate",
      "User selects Family creator or Family business -> setup asks for workspace name and adult owner",
      "User adds a member or chooses Skip for now -> role choices explain permissions in plain language",
      "User selects a role -> preview shows exactly what that member can view and do",
      "User finishes setup -> Home shows one recommended next action and a starter project"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the user has a valid workspace and network connection",
        "when": "switch between family projects and see the next action",
        "then": "the requested state is persisted, shown after refresh, and the primary flow completes in at most 6 screens"
      },
      {
        "type": "given",
        "text": "the workspace has no other members or no prior content",
        "when": "switch between family projects and see the next action",
        "then": "the interface shows a useful empty-state action and never presents an unlabelled blank panel"
      },
      {
        "type": "given",
        "text": "the API returns an error or the connection is interrupted",
        "when": "switch between family projects and see the next action",
        "then": "no duplicate object or publication is created, entered data remains available, and a retry control names the failed step"
      }
    ]
  },
  {
    "id": "US-004",
    "epic": "Guardian Review and Safe Publishing",
    "role": "parent approver",
    "action": "require approval before a minor publishes",
    "benefit": "nothing goes public without an adult decision",
    "story": "As a parent approver, I want to require approval before a minor publishes, so that nothing goes public without an adult decision.",
    "gui_flow": [
      "User opens a project -> sees draft status, owner, and publish gate",
      "Contributor opens the editor -> publish control is replaced by Submit for review",
      "Contributor submits -> approver receives an in-app task with the exact revision number",
      "Approver opens review -> sees preview, changes, warnings, and contributor note",
      "Approver approves or requests changes -> status and audit entry update immediately",
      "If approved, adult selects Publish -> final confirmation lists channels and scheduled time"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the user has a valid workspace and network connection",
        "when": "require approval before a minor publishes",
        "then": "the requested state is persisted, shown after refresh, and the primary flow completes in at most 6 screens"
      },
      {
        "type": "given",
        "text": "the workspace has no other members or no prior content",
        "when": "require approval before a minor publishes",
        "then": "the interface shows a useful empty-state action and never presents an unlabelled blank panel"
      },
      {
        "type": "given",
        "text": "the API returns an error or the connection is interrupted",
        "when": "require approval before a minor publishes",
        "then": "no duplicate object or publication is created, entered data remains available, and a retry control names the failed step"
      }
    ]
  },
  {
    "id": "US-005",
    "epic": "Guardian Review and Safe Publishing",
    "role": "teen contributor",
    "action": "submit a draft with a note for review",
    "benefit": "my contribution can be reviewed without fear of accidental publishing",
    "story": "As a teen contributor, I want to submit a draft with a note for review, so that my contribution can be reviewed without fear of accidental publishing.",
    "gui_flow": [
      "User opens a project -> sees draft status, owner, and publish gate",
      "Contributor opens the editor -> publish control is replaced by Submit for review",
      "Contributor submits -> approver receives an in-app task with the exact revision number",
      "Approver opens review -> sees preview, changes, warnings, and contributor note",
      "Approver approves or requests changes -> status and audit entry update immediately",
      "If approved, adult selects Publish -> final confirmation lists channels and scheduled time"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the user has a valid workspace and network connection",
        "when": "submit a draft with a note for review",
        "then": "the requested state is persisted, shown after refresh, and the primary flow completes in at most 6 screens"
      },
      {
        "type": "given",
        "text": "the workspace has no other members or no prior content",
        "when": "submit a draft with a note for review",
        "then": "the interface shows a useful empty-state action and never presents an unlabelled blank panel"
      },
      {
        "type": "given",
        "text": "the API returns an error or the connection is interrupted",
        "when": "submit a draft with a note for review",
        "then": "no duplicate object or publication is created, entered data remains available, and a retry control names the failed step"
      }
    ]
  },
  {
    "id": "US-006",
    "epic": "Guardian Review and Safe Publishing",
    "role": "parent approver",
    "action": "see exactly what changed and approve the current version",
    "benefit": "I can make a confident decision on the correct version",
    "story": "As a parent approver, I want to see exactly what changed and approve the current version, so that I can make a confident decision on the correct version.",
    "gui_flow": [
      "User opens a project -> sees draft status, owner, and publish gate",
      "Contributor opens the editor -> publish control is replaced by Submit for review",
      "Contributor submits -> approver receives an in-app task with the exact revision number",
      "Approver opens review -> sees preview, changes, warnings, and contributor note",
      "Approver approves or requests changes -> status and audit entry update immediately",
      "If approved, adult selects Publish -> final confirmation lists channels and scheduled time"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the user has a valid workspace and network connection",
        "when": "see exactly what changed and approve the current version",
        "then": "the requested state is persisted, shown after refresh, and the primary flow completes in at most 6 screens"
      },
      {
        "type": "given",
        "text": "the workspace has no other members or no prior content",
        "when": "see exactly what changed and approve the current version",
        "then": "the interface shows a useful empty-state action and never presents an unlabelled blank panel"
      },
      {
        "type": "given",
        "text": "the API returns an error or the connection is interrupted",
        "when": "see exactly what changed and approve the current version",
        "then": "no duplicate object or publication is created, entered data remains available, and a retry control names the failed step"
      }
    ]
  },
  {
    "id": "US-007",
    "epic": "Simple Create-to-Publish Journey",
    "role": "parent creator",
    "action": "start from a goal-based template",
    "benefit": "I can get value in the first session",
    "story": "As a parent creator, I want to start from a goal-based template, so that I can get value in the first session.",
    "gui_flow": [
      "User opens Home -> sees Start a project and one recommended template",
      "User chooses a goal -> wizard asks only audience, message, channel, and due date",
      "User adds text or media -> live preview shows the selected channel output",
      "User clicks Create draft -> progress presents named stages and a cancel option",
      "User reviews the result -> issue panel shows only blocking items first",
      "User submits or publishes -> completion screen explains what happened and the next useful action"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the user has a valid workspace and network connection",
        "when": "start from a goal-based template",
        "then": "the requested state is persisted, shown after refresh, and the primary flow completes in at most 6 screens"
      },
      {
        "type": "given",
        "text": "the workspace has no other members or no prior content",
        "when": "start from a goal-based template",
        "then": "the interface shows a useful empty-state action and never presents an unlabelled blank panel"
      },
      {
        "type": "given",
        "text": "the API returns an error or the connection is interrupted",
        "when": "start from a goal-based template",
        "then": "no duplicate object or publication is created, entered data remains available, and a retry control names the failed step"
      }
    ]
  },
  {
    "id": "US-008",
    "epic": "Simple Create-to-Publish Journey",
    "role": "child collaborator",
    "action": "contribute an idea or media item from a phone",
    "benefit": "the family can capture ideas where they happen",
    "story": "As a child collaborator, I want to contribute an idea or media item from a phone, so that the family can capture ideas where they happen.",
    "gui_flow": [
      "User opens Home -> sees Start a project and one recommended template",
      "User chooses a goal -> wizard asks only audience, message, channel, and due date",
      "User adds text or media -> live preview shows the selected channel output",
      "User clicks Create draft -> progress presents named stages and a cancel option",
      "User reviews the result -> issue panel shows only blocking items first",
      "User submits or publishes -> completion screen explains what happened and the next useful action"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the user has a valid workspace and network connection",
        "when": "contribute an idea or media item from a phone",
        "then": "the requested state is persisted, shown after refresh, and the primary flow completes in at most 6 screens"
      },
      {
        "type": "given",
        "text": "the workspace has no other members or no prior content",
        "when": "contribute an idea or media item from a phone",
        "then": "the interface shows a useful empty-state action and never presents an unlabelled blank panel"
      },
      {
        "type": "given",
        "text": "the API returns an error or the connection is interrupted",
        "when": "contribute an idea or media item from a phone",
        "then": "no duplicate object or publication is created, entered data remains available, and a retry control names the failed step"
      }
    ]
  },
  {
    "id": "US-009",
    "epic": "Simple Create-to-Publish Journey",
    "role": "family business owner",
    "action": "finish and publish a campaign without learning every module",
    "benefit": "the product saves time instead of adding workflow overhead",
    "story": "As a family business owner, I want to finish and publish a campaign without learning every module, so that the product saves time instead of adding workflow overhead.",
    "gui_flow": [
      "User opens Home -> sees Start a project and one recommended template",
      "User chooses a goal -> wizard asks only audience, message, channel, and due date",
      "User adds text or media -> live preview shows the selected channel output",
      "User clicks Create draft -> progress presents named stages and a cancel option",
      "User reviews the result -> issue panel shows only blocking items first",
      "User submits or publishes -> completion screen explains what happened and the next useful action"
    ],
    "acceptance_criteria": [
      {
        "type": "given",
        "text": "the user has a valid workspace and network connection",
        "when": "finish and publish a campaign without learning every module",
        "then": "the requested state is persisted, shown after refresh, and the primary flow completes in at most 6 screens"
      },
      {
        "type": "given",
        "text": "the workspace has no other members or no prior content",
        "when": "finish and publish a campaign without learning every module",
        "then": "the interface shows a useful empty-state action and never presents an unlabelled blank panel"
      },
      {
        "type": "given",
        "text": "the API returns an error or the connection is interrupted",
        "when": "finish and publish a campaign without learning every module",
        "then": "no duplicate object or publication is created, entered data remains available, and a retry control names the failed step"
      }
    ]
  }
]
```

## Priority-Ranked Development Recommendations

1. **P0: Introduce Family mode as a real permission and navigation model.** Adult owner, adult collaborator, teen contributor, and view-only roles must be server-enforced. Home should show only relevant tasks.
2. **P0: Make approval the core trust loop.** Show preview, author, exact revision, changes, warnings, and channel destination. Any edit after approval invalidates that approval.
3. **P0: Consolidate first value into a wizard.** Start from goals such as “promote our shop,” “share a family project,” or “publish this week's update.” Reuse existing campaign, brand, generation, validation, approval, and publishing services behind the wizard.
4. **P1: Build mobile capture and proper mobile navigation.** Preserve drafts offline, upload with privacy warnings, and route every idea to an adult-controlled project.
5. **P1: Add pricing trust.** Usage meter, pre-generation cost estimate, spend cap, no per-child charge, and straightforward export/cancel controls.
6. **P1: Convert analytics into a weekly value report.** Time saved, items published, approval turnaround, recoveries, and best-performing reusable template.
7. **P2: Consider younger-child contribution only after legal/privacy design review.** Until then, younger children should participate through an adult's session, not independent accounts.

## Recommended Scope for the Next Development Pass

Deliver a vertical slice, not seven disconnected features:

- New Welcome flow with Family Creator/Family Business goal choice.
- Adult-owned workspace creation and real role/permission matrix.
- Simplified five-item family navigation plus optional Expert mode for adults.
- Home with setup checklist, one next action, review tasks, and recent projects.
- Goal-based project wizard that creates a campaign, first asset, preview, and review request.
- Guardian review screen with exact revision, diff summary, issue summary, approve/request changes.
- Publish gate enforcing current adult approval and preserving selective-retry semantics.
- Responsive drawer/bottom navigation, mobile idea capture, draft recovery.
- Instrument activation, first draft, review, publish, and week-two return.
- Run targeted component/API/E2E tests and the full regression suite after implementation.

Explicitly out of scope: new AI providers, new social networks, advanced child accounts, a native mobile app, more analytics charts, and further top-level modules.

## Risks, Unknowns, and Assumptions

- “Family users” is an inferred segment. The repository itself targets professional content teams. Validate the family-run business wedge before rebranding the whole product.
- Minor accounts trigger legal and safeguarding work that varies by country. COPPA and UK guidance are reference points, not a complete legal determination [S7][S8].
- Public pricing pages are dynamic and sometimes region-dependent. Exact competitor prices were not used as durable evidence and must be refreshed before launch.
- Existing authentication and tenant scoping are uneven across documented endpoints. A family role UI without uniform server authorization would be unsafe.
- The current `contentforge.db` is shipped in the archive as an intentional project asset, but production data handling, backups, retention, and deletion need separate review.
- The product's breadth may be an asset for expert users, so simplification should be a mode and progressive disclosure strategy, not removal of proven backend capability.
- No direct interviews, analytics, support-ticket corpus, or conversion data were provided. Demand confidence is based on product-category evidence and codebase fit.

## Sources

Accessed 2026-08-12 unless a publication date is stated.

- **[S1]** Planable, product, approvals, and pricing pages: https://planable.io/ ; https://help.planable.io/hc/en-us/articles/21715462785180-Approvals-and-Approval-Workflows ; https://planable.io/pricing/
- **[S2]** Buffer, product and pricing: https://buffer.com/ ; https://buffer.com/pricing
- **[S3]** Sprout Social, “Message Approval Workflows”: https://support.sproutsocial.com/hc/en-us/articles/205974715-Message-Approval-Workflows
- **[S4]** Hootsuite, plans and social media management product: https://www.hootsuite.com/plans ; https://www.hootsuite.com/platform
- **[S5]** Canva, pricing and Content Planner: https://www.canva.com/pricing/ ; https://www.canva.com/pro/content-planner/
- **[S6]** Adobe Express, pricing and content scheduler: https://www.adobe.com/express/pricing ; https://www.adobe.com/express/feature/content-scheduler
- **[S7]** U.S. Federal Trade Commission, Children's Online Privacy Protection Rule guidance: https://www.ftc.gov/business-guidance/privacy-security/childrens-privacy
- **[S8]** UK Information Commissioner's Office, Age Appropriate Design Code: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/childrens-information/childrens-code-guidance-and-resources/
- **[S9]** NIST, AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- **[S10]** W3C, Web Content Accessibility Guidelines 2.2: https://www.w3.org/TR/WCAG22/
- **[S11]** Radix UI documentation: https://www.radix-ui.com/primitives/docs/overview/introduction
- **[S12]** React Aria documentation: https://react-spectrum.adobe.com/react-aria/
- **[S13]** React Hook Form documentation: https://react-hook-form.com/ ; Zod: https://zod.dev/
- **[S14]** TanStack Query documentation: https://tanstack.com/query/latest
- **[S15]** Project evidence: `README.md`, `CHANGELOG.md`, `ContentForge fejlesztési terv és részletes GUI-koncepció.md`, `analysis/architecture-spec.md`, `docs/product-workspaces.md`, `frontend/src/main.tsx`, `frontend/src/navigation.ts`, `frontend/src/styles.css`.
- **[S16]** Playwright accessibility testing guidance: https://playwright.dev/docs/accessibility-testing
- **[S17]** OpenTelemetry Python documentation: https://opentelemetry.io/docs/languages/python/
- **[S18]** Contentful localization workflow: https://www.contentful.com/products/platform/localization-and-translation/ ; https://www.contentful.com/help/ai-automations/workflows/localized-workflows/
- **[S19]** Lokalise workflow management: https://lokalise.com/product/localization-workflow-management/ ; https://docs.lokalise.com/en/articles/9582608-workflows
- **[S20]** EasyContent, content operations platform comparison: https://easycontent.io/resources/best-content-operations-platforms/
