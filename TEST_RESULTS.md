# Test results

Date: 2026-08-02

## TDD red phase

`tests/test_workspace_experience.py` was created before implementation. Initial collection failed because `render_campaign_detail` did not exist, confirming the new behavior was not already present.

## Focused regression

```text
pytest -q -o addopts='' tests/test_workspace_experience.py tests/test_product_workspaces.py
15 passed, 2 warnings
```

The warnings are dependency deprecations from Starlette TestClient/httpx and Passlib/Python crypt.

## Full regression

```text
pytest -q -o addopts=''
1761 passed, 27 skipped, 29 failed
```

The failures are outside the modified workspace path and are concentrated in:

- Authentication tests affected by the execution environment's bcrypt version.
- One configuration default assertion.
- Language detection tests, including contradictory implementation/stub expectations and unavailable/changed detector behavior.

No workspace experience or existing product workspace test failed in the final focused run.

## Compilation

```text
python -m py_compile src/product_ops.py src/routers/workspaces.py
```

Passed.

## Lint note

Ruff was requested in the handoff environment, but the installed Python wrapper could not locate its native executable. Lint success is therefore not claimed.
