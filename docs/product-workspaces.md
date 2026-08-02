# Content operations workspaces

ContentForge exposes six human-facing workspaces while retaining JSON automation contracts.

## Architecture

```text
FastAPI page/API router
    -> workflow application service
        -> explicit domain state and invariants
            -> SQLite repository
```

`src.product_ops.ContentOpsStore` owns transactional workflow state. `src.routers.workspaces` translates HTTP requests to domain calls. Rendering remains deterministic and escapes user-controlled values before HTML output.

## Workflow guarantees

- Campaigns preserve successful channel assets when another channel fails.
- High-risk approval requests cannot be approved by their requester.
- Conflicting brand voice rules prevent profile activation and retain their source excerpt.
- Publish retry calculation returns only failed or retryable channels.
- Localization quality gates operate per locale instead of blocking unrelated variants.
- Provenance exports redact template secrets while retaining human-edit events.

## Accessibility

Workspace pages provide skip navigation, semantic landmarks, visible focus, live status messages, responsive reflow, non-color status text, input labels, empty states, and recovery guidance. WCAG 2.2 AA is the implementation target, with automated and manual testing required before production release.

## Security boundary

The workflow store contains operational metadata, not platform credentials. Existing encrypted token storage remains responsible for connector credentials. Production deployments must add tenant identifiers and object-level authorization to every repository query before enabling shared multi-tenant use.

## v0.11 actionable workspace update

The Campaign workspace now supports a complete server-rendered create-and-open interaction without JavaScript. Valid submissions use post/redirect/get and lead to a stable campaign detail page. Invalid submissions return an accessible operation alert. Campaign cards link to context, technical states are translated into plain-language labels with next steps, and operational attention counts expose pending approvals, retryable deliveries, and locale reviews.

Recovery content is now shown only after an actual operation error. This avoids implying a failure when the system is healthy and improves the credibility of status feedback.
