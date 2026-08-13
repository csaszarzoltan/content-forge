# Family Creator Workspace

Family Creator is a bounded collaboration layer over ContentForge. It keeps ideas private, makes the next action obvious, binds approval to an immutable revision, and reserves publishing for adults.

## User flow

1. Open `#family`, choose Family Creator or Family Business, and name the workspace.
2. Home shows one next action and explicit empty/recovery states.
3. Create a project in four steps: goal, context, message, channels.
4. Capture private ideas from the mobile Create flow.
5. Submit a revision for review. A new edit supersedes the old review.
6. An adult approves or requests changes. Publishing requires approval for the exact current revision.

## API

All routes use `/api/v1/family`. Mutations that can create duplicate side effects require `Idempotency-Key`.

- `POST /workspaces`: `{name, mode}`.
- `GET /session?workspace_id=`: workspace, role, permissions, navigation.
- `POST /workspaces/{id}/invitations`: `{email, role}`.
- `POST /invitations/{token}/accept`.
- `GET /home?workspace_id=`.
- `POST /journeys`: goal, project name, audience, message, optional CTA/notes, channels.
- `POST /ideas`: multipart private text/image idea, maximum image size 10 MiB.
- `POST /assets/{id}/submit-review`: `{workspace_id, note}`.
- `GET /reviews?workspace_id=`.
- `POST /reviews/{id}/decision`: `APPROVED` or `NEEDS_CHANGES` with reason.
- `POST /publish-batches`: exact asset revision and channels.

Errors use FastAPI's `{"detail":"code"}` shape. Cross-workspace or insufficient-role access is denied. Invitation tokens are random, hashed for lookup, expire after seven days, and are single-use. Uploaded family images are private files and are not anonymously mounted.

## Privacy boundary

The product does not collect a child's age and does not claim child-directed regulatory compliance. Teen contributor is an adult-invited constrained role. Contributors cannot publish, manage members, billing, admin, or credentials. Public deployment must derive actor headers from authenticated identity at a trusted gateway and strip client-supplied identity headers.

## Completion APIs and screens

All private family endpoints require `Authorization: Bearer <access token>`. Invitation preview is the only public family read and returns minimized workspace/role information.

- `GET /invitations/{token}/preview`, authenticated `POST /invitations/{token}/accept`
- `GET /workspaces/{id}/members`, `PATCH`/`DELETE` member endpoints, and invitation revoke
- `GET /assets/{id}`, `PUT /assets/{id}/autosave`, and revision history
- `GET /reviews/{id}` with labeled word diff
- `GET /assets/{id}/publish-eligibility`
- `GET /publish-batches/{id}`, `POST .../retry`, and `POST .../reconcile`

The family UI adds Sign in, Members, Preview-first Editor, and Publish Result. Autosave waits 800 ms after typing. A 409 conflict stops autosave and offers Copy my draft/Reload latest. Published delivery rows are never retried; UNKNOWN requires status reconciliation first.
