## Features Done (this pass)
- Campaign Cockpit: Persists campaign briefs and returns assets, readiness, and actionable blockers in one API context.
- Modern React workspace: Adds responsive onboarding, cockpit, asset editing, empty states, and friendly recovery messaging.
- Versioned content editor: Creates immutable revisions with optimistic concurrency protection.
- Revision-bound approval: Binds every review request and decision to one exact asset version.
- Approval invalidation: Editing pending or approved content automatically supersedes outdated approval decisions.
- Approval audit trail: Records review request, reviewer decision, reason, risk, and revision version.
- Request review UI: Lets creators send the current editor version to approval from the React workflow.
- My Work queue: Surfaces pending approvals and failed publications with next actions.
- SQLite compatibility migration: Adds brief, title, version, revisions, approval version, and audit tables without dropping records.
## Sources
- research-findings.md items addressed: campaign cockpit, safe editing/versioning, contextual approval, auditability, actionable feedback, unified My Work queue
- CHANGELOG.md section this maps to: 0.12.0
