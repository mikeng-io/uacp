# Read-only Containment Validation Pattern

Use this reference when VERIFY needs to run Python validation inside a UACP contained shell where `UACP_ROOT` is mounted read-only.

## Problem

`python -m py_compile ...` can fail under read-only-root containment because CPython writes `.pyc` files into `__pycache__/`. That failure is not evidence that the source has syntax errors; it is usually evidence that containment correctly blocks writes.

Do not record this as "py_compile is broken" or as a negative tool constraint. Treat it as a validation-mode mismatch.

## Preferred read-only syntax check

Run AST parsing with bytecode writes disabled:

```bash
cd "$UACP_ROOT" && PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import ast, pathlib
for p in [
    'runtime-adapters/hermes/plugins/uacp_guardian/kernel.py',
    'runtime-adapters/hermes/plugins/uacp_guardian/__init__.py',
    'scripts/validate_uacp_artifacts.py',
]:
    ast.parse(pathlib.Path(p).read_text(), filename=p)
    print('syntax ok', p)
PY
```

Then run artifact validation with bytecode writes disabled:

```bash
cd "$UACP_ROOT" && PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_uacp_artifacts.py
```

## Evidence to record

In the VERIFY artifact, record:

- command surface, e.g. `uacp_contained_shell`
- containment mechanism, e.g. `bwrap_readonly_root`
- whether the write probe was blocked
- AST parse results for changed Python files
- artifact validator result, e.g. `RESULT PASS`
- any residual risk separately from deterministic validation results

## Pitfall

Do not switch back to uncontained shell merely because `py_compile` attempted bytecode writes. If a contained-shell run fails only due to `.pyc` creation, use AST parse + `PYTHONDONTWRITEBYTECODE=1` instead.
