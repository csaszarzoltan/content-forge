# Test results

## TDD red phase

`tests/test_workspace_v013.py` initially failed during collection because `render_publish_batch_detail` was not implemented.

## Focused regression

```text
pytest -q -o addopts='' tests/test_workspace_v013.py tests/test_workspace_v012.py tests/test_product_workspaces.py
16 passed, 0 failed, 2 dependency deprecation warnings
```

## Compilation

```text
python -m py_compile src/product_ops.py src/routers/workspaces.py
```

Passed.
