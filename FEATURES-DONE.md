## Features Done (this pass)
- Complete React navigation: Every sidebar item has a real hash route, active state, and browser history support.
- My Work workspace: Shows live approval, publish recovery, localization, and campaign summary data.
- Campaigns workspace: Adds campaign creation, persistent campaign list, and cockpit navigation.
- Content workspace: Adds a real asset library connected to the versioned editor.
- Calendar workspace: Adds a responsive monthly publishing overview and honest empty state.
- Approvals workspace: Adds a governance queue populated from revision-bound approval requests.
- Localization workspace: Adds localization job and locale QA panels backed by persisted data.
- Analytics workspace: Adds workflow KPIs and a responsive health visualization.
- Brand Governance workspace: Adds voice profile, rule, evidence, and conflict views.
- Connections workspace: Adds platform connection health and setup states.
- Admin workspace: Adds runtime health and safe local-development guidance.
- Workspace overview API: Exposes all React workspace collections from the existing SQLite store.
- Python version compatibility: Uses SciPy 1.17.1 on Python 3.11 and 1.18.0 on Python 3.12+.
- Windows backend runner: Watches only Python source and excludes frontend dependencies from reloads.
## Sources
- research-findings.md items addressed: end-to-end UI workflow, context-preserving navigation, unified My Work dashboard, actionable empty/error states, approval queue, localization progress, analytics drill-through foundation
- CHANGELOG.md section this maps to: 0.13.0
