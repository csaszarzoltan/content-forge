# v0.13 publish recovery implementation report

## User problem

A partially successful multi-channel publish is a high-anxiety workflow. Users need to understand which channels succeeded, which failed, and whether retrying can create duplicates.

## Implemented

- Publish Center now lists delivery batches rather than disconnected delivery rows.
- Each batch opens a contextual detail page with per-channel state and remote identifier.
- Retry scope is calculated exclusively from `FAILED` and `RETRYABLE` channels.
- Previously published channels are preserved and excluded from retry requests.
- Fully published batches do not expose a retry action.
- Retry request state is persisted as `RETRYING` and returns explicit accessible feedback.
- No synthetic external publish is performed by this UI action. It queues workflow intent honestly for the connector execution layer.

## Requirements delivered

- Users can inspect partial delivery outcomes in one place.
- Retry behavior is explicit and duplicate-safe by default.
- Successful channels stay immutable during recovery.
- Invalid retry attempts are rejected rather than silently accepted.

## TDD

`tests/test_workspace_v013.py` was added first. Its initial collection failed because publish batch detail rendering did not exist. The focused final regression passed with 16 tests.
