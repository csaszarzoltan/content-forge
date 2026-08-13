# Provider Sandbox Verification

## Prerequisites

Use non-public LinkedIn and X test accounts and provider-approved applications. Configure credentials only through environment variables. Never write tokens to this repository or the report.

## Required scenarios

1. LinkedIn success: publish a unique marker, verify returned remote identifier/URL and exactly one remote post.
2. X success: same requirements.
3. Expired token: provider returns authentication failure; UI shows reconnect and no success.
4. Permission failure: missing posting scope returns authorization failure and no retry loop.
5. Rate limit: status becomes retryable with no duplicate remote post.
6. No response/unknown: status is UNKNOWN; Retry is blocked until reconciliation.
7. Reused idempotency key: same body returns same batch and remote identifiers; changed body returns 409.
8. Partial success: one provider succeeds and one fails; selective retry sends only the failed delivery.

## Evidence to record

Record UTC time, provider, test account alias, local batch ID, remote ID, final state, attempt count, HTTP status class, and whether duplicate content exists. Redact tokens, authorization headers, provider response bodies, and personal account identifiers.

## Current environment result

Sandbox execution is BLOCKED when the six LinkedIn/X credential environment variables are absent. This is not a failed provider implementation and must not be reported as a successful sandbox test.
