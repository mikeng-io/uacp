---
type: plan
title: "`.uacp/` Namespace — Slice 2 (Relocate runtime dirs) Implementation Plan"
description: "Slice 2 plan to relocate UACP runtime dirs (`state/`, `.outputs/`) under `.uacp/` via config-backed resolver"
tags: ["namespace", "config-collapse", "runtime-dirs", "paths"]
timestamp: 2026-06-15
status: archived
---

# `.uacp/` Namespace — Slice 2 (Relocate runtime dirs) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Relocate UACP's per-project runtime dirs under `.uacp/` (`state/`, `.outputs/`→`resolutions/`, and the phase dirs), repoint every hardcoded path site to read through `config.py`, and ship a hard-cut `scripts/migrate_to_uacp_dir.py` — with the 328-test suite green after every step.

**Architecture:** *Design B — config-backed `base` resolver.* The project/workspace root is unchanged; a new `base_dir(root) → <root>/.uacp` helper in `config.py` injects the namespace, and `dir_for(root, key) → <root>/.uacp/<subdir>` resolves each phase/state dir from the `[paths]` knob. Stored artifact-path strings stay **base-relative** (`proposals/…`, `verification/…`, `resolutions/…`) — only the `.outputs/`→`resolutions/` token is renamed. No fallback / dual-read: one source of truth immediately.

**Tech Stack:** Python 3.13+ (`python3` — the default `python` is anaconda-3.8 and cannot parse PEP-604 `X | None`), Pydantic v2, `tomllib`, PyYAML, pytest, ruff (`/Users/mike/.local/bin/ruff`, strict `E,F,I,UP,B`).

**Design doc:** `docs/plans/2026-06-15-uacp-namespace-and-config-collapse-design.md`
**Roadmap + council hardening (C-1…C-5):** `docs/plans/2026-06-15-uacp-namespace-and-config-collapse.md` § "Council audit".

---

## Path-reference inventory (C-1 — verified by grep on this branch)

Every site below hardcodes a runtime path and does **not** currently read `config.py`. Each is flipped in this slice. Sites are grouped by the task that owns them.

| # | File:line | Current | Owner task |
|---|---|---|---|
| 1 | `engines/io/loaders.py:96` | `workspace / "state" / "runs" / f"{run_id}.yaml"` | T3 |
| 2 | `engines/io/loaders.py:117` | `workspace / "state" / "gate-ledger" / …` | T3 |
| 3 | `engines/io/loaders.py:147` | `workspace / "state" / "current.yaml"` | T3 |
| 4 | `engines/io/loaders.py:158` | `workspace / "state" / "run-registry.yaml"` | T3 |
| 5 | `engines/coherence.py:118` | `root / "state" / "gate-ledger" / …` | T4 |
| 6 | `engines/coherence.py:159` | `root / "state" / "current.yaml"` | T4 |
| 7 | `engines/scope_conformance.py:87` | `_ALLOWED_OUTPUT_PREFIXES = (".outputs", "state", "verification")` | T5 |
| 8 | `uacp-state/scripts/state.py:108,143,150,157,165,181,271,400,401` | `root / "state" / …` containment roots | T6 |
| 9 | `uacp-state/scripts/state_machine.py:168` | `workspace / "state" / "current.yaml"` | T7 |
| 10 | `uacp-core/scripts/core.py:556` | shell-token scanner prefix tuple (`state/`, `.outputs/`, …) | T8 |
| 11 | `uacp-core/scripts/core.py:569` | `(self.policy.uacp_root / "state")` — Guardian state containment | T8 |
| 12 | `uacp-core/scripts/core.py:1369-1372` | `.outputs/{run_id}…` resolve-closure gate paths | T9 |
| 13 | `uacp-core/scripts/core.py:2211` | `self.uacp_root / "plans" / f"{run_id}-scope.yaml"` | T9 |
| 14 | `uacp-core/scripts/core.py:2262-2265` | `.outputs/{run_id}-lessons.yaml` lessons template + base | T9 |
| 15 | `uacp-core/scripts/core.py:2301,2303` | `startswith(("verification/", ".outputs/"))` accepted-exception prefix | T9 |
| 16 | `uacp-core/scripts/core.py:1426,1576,2025` | `self.uacp_root / "state" / "gate-ledger" / …` | T9 |
| 17 | `uacp_guardian/__init__.py:628,629,633,635` | artifact-write allowed/forbidden roots (`outputs`) + base | T10 |
| 18 | `uacp_guardian/__init__.py:750` | transition allowed roots (`outputs`) | T10 |
| 19 | `tests/conftest.py:28-35` | builds flat `state/`, `.outputs/`, phase dirs | T2 |
| 20 | `tests/e2e/*.py` | `.outputs/{run_id}-lessons.yaml` refs + dir creation | T11 |

**Heartgate base-resolution helpers** (core.py) that resolve a base-relative `rel` and must move from `self.uacp_root` to the new `self.governed_root` for *artifact/state* paths (but **not** for `config/`): `_load_yaml_under_root`, `_dir_under_root_exists`, `_artifact_path_exists`, `_offline_validate_artifacts`, `_canon_write_path`, and the direct `self.uacp_root / …` joins at 811, 950, 2211, 2263. Enumerated in T9.

**Out of Slice 2 scope (do NOT touch — later slices / not in `pytest tests/`):**
- `skills/scripts/validate_uacp_artifacts.py` AND `scripts/validate_uacp_artifacts.py` (two divergent copies, ~25 path refs each) → **Slice 5** (council note). They are not imported by `pytest tests/`.
- `phase-transitions.yaml` / `artifact-schemas.yaml` loading and the 9 `authority_source:` SKILL.md refs → **Slice 4** (C-3).
- `config/` directory itself stays at project root this slice (knob collapse is Slice 3).
- `_default_toml_path()` `parents[3]` → **Slice 5 / plugin** (C-4).
- `scripts/phase{1,2,3,4}_verify.py`, `scripts/live_guardian_probe.py`, `scripts/import_loader_verify.py`: standalone harnesses, not in `pytest tests/`. Audited (update or document) in **T14**.

---

## Convention (the one rule the whole slice obeys)

A **stored / passed artifact path string is relative to the governed base** (`.uacp/`). The kernel resolves it under `base_dir(root)`. Therefore:
- `proposals/x.md`, `plans/x.yaml`, `executions/x.yaml`, `verification/x.yaml`, `state/...`, `knowledge/...` → **unchanged strings**, now resolved under `.uacp/`.
- `.outputs/...` → **renamed** to `resolutions/...` everywhere (the only string change). This kills the F-EV-01 `.outputs`/`..outputs` token class.
- Migrate script (T12) rewrites only the `.outputs/`→`resolutions/` token inside already-emitted YAML, plus moves dirs. No `.uacp/` prefix is added to stored strings.

---

# Task 1: `config.py` resolver helpers

**Files:**
- Modify: `skills/uacp-core/scripts/config.py`
- Test: `tests/unit/uacp_core/test_config.py` (append)

- [ ] **Step 1: Write failing tests** (append to `tests/unit/uacp_core/test_config.py`)

```python
def test_base_dir_injects_namespace(tmp_path):
    from config import base_dir
    assert base_dir(tmp_path) == tmp_path.resolve() / ".uacp"

def test_dir_for_resolves_subdir(tmp_path):
    from config import dir_for
    assert dir_for(tmp_path, "state") == tmp_path.resolve() / ".uacp" / "state"
    assert dir_for(tmp_path, "resolutions") == tmp_path.resolve() / ".uacp" / "resolutions"

def test_dir_for_honors_base_override(tmp_path):
    from config import clear_config_cache, dir_for
    clear_config_cache()
    (tmp_path / ".uacp").mkdir()
    (tmp_path / ".uacp" / "config.toml").write_text('[paths]\nbase = ".governed"\n')
    assert dir_for(tmp_path, "state") == tmp_path.resolve() / ".governed" / "state"
    clear_config_cache()

def test_dir_for_rejects_unknown_key(tmp_path):
    from config import dir_for
    with pytest.raises(ValueError):
        dir_for(tmp_path, "nope")
```

- [ ] **Step 2: Run → FAIL**

Run: `python3 -m pytest tests/unit/uacp_core/test_config.py -q`
Expected: FAIL (`cannot import name 'base_dir'`).

- [ ] **Step 3: Implement** — append to `skills/uacp-core/scripts/config.py` (after `load_config`):

```python
from functools import lru_cache


@lru_cache(maxsize=256)
def _cached_config(root_str: str) -> UacpConfig:
    return load_config(Path(root_str))


def clear_config_cache() -> None:
    """Drop the per-root config cache (test hygiene; see conftest autouse)."""
    _cached_config.cache_clear()


def get_config(root: Path) -> UacpConfig:
    """Config for ``root``, deep-merging ``<root>/.uacp/config.toml`` if present.

    Cached per resolved root so kernel readers do not re-parse TOML on every
    path lookup. Use :func:`clear_config_cache` between tests that mutate the
    override after a prior read.
    """
    return _cached_config(str(Path(root).resolve()))


def base_dir(root: Path) -> Path:
    """The governed namespace root: ``<root>/<paths.base>`` (default ``.uacp``)."""
    cfg = get_config(root)
    return Path(root).resolve() / cfg.paths.base


def dir_for(root: Path, path_key: str) -> Path:
    """Resolve a declared ``[paths]`` subdir under the governed base.

    Plain join (no traversal check — ``path_key`` is a kernel constant, not user
    input); raises ``ValueError`` for an unknown key so typos fail loud.
    """
    cfg = get_config(root)
    if path_key not in type(cfg.paths).model_fields:
        known = ", ".join(sorted(type(cfg.paths).model_fields))
        raise ValueError(f"unknown paths key {path_key!r}; expected one of: {known}")
    return base_dir(root) / getattr(cfg.paths, path_key)
```

- [ ] **Step 4: Run → PASS**

Run: `python3 -m pytest tests/unit/uacp_core/test_config.py -q`
Expected: PASS (all config tests).

- [ ] **Step 5: Lint + commit**

```bash
/Users/mike/.local/bin/ruff check skills/uacp-core/scripts/config.py tests/unit/uacp_core/test_config.py
git add skills/uacp-core/scripts/config.py tests/unit/uacp_core/test_config.py
git commit -m "feat(config): base_dir/dir_for resolver helpers + per-root cache"
```

---

# Task 2: conftest `.uacp/` layout + cache-clear fixture

**Files:**
- Modify: `tests/conftest.py:21-128` (the `temp_uacp_root` fixture) + add an autouse fixture

- [ ] **Step 1: Rewrite the directory-creation block** (`tests/conftest.py`, replace lines that `mkdir` the flat layout)

Replace:
```python
    # Create standard UACP directories
    (test_dir / "state" / "runs").mkdir(parents=True)
    (test_dir / "state" / "gate-ledger").mkdir(parents=True)
    (test_dir / "state" / "escalations").mkdir(parents=True)
    (test_dir / "plans").mkdir(parents=True)
    (test_dir / "proposals").mkdir(parents=True)
    (test_dir / ".outputs").mkdir(parents=True)
    (test_dir / "verification").mkdir(parents=True)
    (test_dir / "config").mkdir(parents=True)
    (test_dir / "docs").mkdir(parents=True)
```
with:
```python
    # Create standard UACP directories under the .uacp/ governed namespace.
    base = test_dir / ".uacp"
    (base / "state" / "runs").mkdir(parents=True)
    (base / "state" / "gate-ledger").mkdir(parents=True)
    (base / "state" / "escalations").mkdir(parents=True)
    (base / "plans").mkdir(parents=True)
    (base / "proposals").mkdir(parents=True)
    (base / "executions").mkdir(parents=True)
    (base / "resolutions").mkdir(parents=True)  # replaces flat .outputs/
    (base / "verification").mkdir(parents=True)
    (base / "knowledge").mkdir(parents=True)
    # config/ stays at project root this slice (knob collapse is Slice 3).
    (test_dir / "config").mkdir(parents=True)
    (test_dir / "docs").mkdir(parents=True)
```
Keep the existing `guardian-policy.yaml` / `phase-transitions.yaml` writes (they go under `test_dir / "config"` — unchanged).

- [ ] **Step 2: Add an autouse cache-clear fixture** (append near the top fixtures in `tests/conftest.py`):

```python
@pytest.fixture(autouse=True)
def _clear_uacp_config_cache():
    """Reset config.py's per-root cache around every test (override hygiene)."""
    try:
        from config import clear_config_cache
    except Exception:
        yield
        return
    clear_config_cache()
    yield
    clear_config_cache()
```

- [ ] **Step 3: Run the suite — expect RED across e2e/state (the kernel still writes flat paths)**

Run: `python3 -m pytest tests/ -q`
Expected: failures concentrated in `tests/e2e/` and `tests/unit/uacp_state/` (kernel not yet repointed). This is the intended mid-migration state; later tasks turn it green. Note the count.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test(conftest): build .uacp/ layout + autouse config-cache reset"
```

---

# Task 3: Repoint engine loaders (`loaders.py`)

**Files:**
- Modify: `skills/uacp-core/scripts/engines/io/loaders.py:96,117,147,158`
- Test: `tests/unit/uacp_core/test_loaders_paths.py` (new)

- [ ] **Step 1: Write failing path-construction test** (new file `tests/unit/uacp_core/test_loaders_paths.py`)

```python
"""C-1 guard: loaders resolve state under .uacp/, never the flat root."""
from pathlib import Path

from engines.io import loaders


def test_manifest_path_is_under_uacp(tmp_path):
    # A manifest at the OLD flat location must NOT be found.
    (tmp_path / "state" / "runs").mkdir(parents=True)
    (tmp_path / "state" / "runs" / "r1.yaml").write_text("run_id: r1\n")
    assert loaders.load_manifest(tmp_path, "r1").error is not None

    # A manifest under .uacp/ IS found.
    (tmp_path / ".uacp" / "state" / "runs").mkdir(parents=True)
    (tmp_path / ".uacp" / "state" / "runs" / "r1.yaml").write_text("run_id: r1\n")
    loaded = loaders.load_manifest(tmp_path, "r1")
    assert loaded.error is None and loaded.value.raw["run_id"] == "r1"
```

- [ ] **Step 2: Run → FAIL**

Run: `python3 -m pytest tests/unit/uacp_core/test_loaders_paths.py -q`
Expected: FAIL (old flat path still found).

- [ ] **Step 3: Implement** — add the import and repoint the four joins.

At the top of `loaders.py`, alongside the `from filesystem import _resolve_uacp_path` line, add:
```python
from config import dir_for  # noqa: E402
```
Then:
- line 96: `path = workspace / "state" / "runs" / f"{run_id}.yaml"`
  → `path = dir_for(workspace, "state") / "runs" / f"{run_id}.yaml"`
- line 117: `path = workspace / "state" / "gate-ledger" / f"{run_id}.jsonl"`
  → `path = dir_for(workspace, "state") / "gate-ledger" / f"{run_id}.jsonl"`
- line 147: `path = workspace / "state" / "current.yaml"`
  → `path = dir_for(workspace, "state") / "current.yaml"`
- line 158: `path = workspace / "state" / "run-registry.yaml"`
  → `path = dir_for(workspace, "state") / "run-registry.yaml"`

- [ ] **Step 4: Run → PASS**

Run: `python3 -m pytest tests/unit/uacp_core/test_loaders_paths.py -q`
Expected: PASS.

- [ ] **Step 5: Lint + commit**

```bash
/Users/mike/.local/bin/ruff check skills/uacp-core/scripts/engines/io/loaders.py
git add skills/uacp-core/scripts/engines/io/loaders.py tests/unit/uacp_core/test_loaders_paths.py
git commit -m "refactor(engines): loaders resolve state under .uacp/ via config.dir_for"
```

---

# Task 4: Repoint `coherence.py` state joins

**Files:**
- Modify: `skills/uacp-core/scripts/engines/coherence.py:118,159`

> Note: line 118 builds a `ledger_path` used only for a violation **message** (the actual read is via `load_ledger`, already fixed in T3). Line 159 builds `current_path` likewise for messaging; the read is `load_current`. Keeping them correct avoids misleading diagnostics.

- [ ] **Step 1: Repoint** — add import at top of `coherence.py` (near the other `engines.io` imports):
```python
from config import dir_for
```
- line 118: `ledger_path = root / "state" / "gate-ledger" / f"{run_id}.jsonl"`
  → `ledger_path = dir_for(root, "state") / "gate-ledger" / f"{run_id}.jsonl"`
- line 159: `current_path = root / "state" / "current.yaml"`
  → `current_path = dir_for(root, "state") / "current.yaml"`

- [ ] **Step 2: Run the coherence engine tests**

Run: `python3 -m pytest tests/ -q -k coherence`
Expected: PASS (no regressions vs. T2 baseline for coherence).

- [ ] **Step 3: Lint + commit**

```bash
/Users/mike/.local/bin/ruff check skills/uacp-core/scripts/engines/coherence.py
git add skills/uacp-core/scripts/engines/coherence.py
git commit -m "refactor(engines): coherence state-path messages resolve under .uacp/"
```

---

# Task 5: `scope_conformance.py` allowed-output prefixes

**Files:**
- Modify: `skills/uacp-core/scripts/engines/scope_conformance.py:82-87`

- [ ] **Step 1: Rename the prefix** — replace the comment + constant at 82-87:

```python
# UACP output / state surfaces an in-scope run product may legitimately land in
# even when not explicitly enumerated in write_paths: governed-writer outputs
# (resolutions/), the run's own state (state/), and verification evidence. These
# are system-owned write surfaces, not free-form EXECUTE writes, so a referenced
# artifact under one of them is treated as in-scope.
_ALLOWED_OUTPUT_PREFIXES = ("resolutions", "state", "verification")
```
(These prefixes are matched against **base-relative** stored strings — see Convention — so `resolutions` replaces `.outputs`.)

- [ ] **Step 2: Run scope tests**

Run: `python3 -m pytest tests/ -q -k scope`
Expected: PASS.

- [ ] **Step 3: Lint + commit**

```bash
/Users/mike/.local/bin/ruff check skills/uacp-core/scripts/engines/scope_conformance.py
git add skills/uacp-core/scripts/engines/scope_conformance.py
git commit -m "refactor(engines): scope_conformance allows resolutions/ (was .outputs)"
```

---

# Task 6: Governed writers — `state.py` containment roots

**Files:**
- Modify: `skills/uacp-state/scripts/state.py` (lines 108,109,143,150,157,165,181,271,400,401)
- Test: `tests/unit/uacp_state/test_state_paths.py` (new)

These writers receive `root = policy.uacp_root` (project root) and a caller `target_path`. Under Design B the caller still passes `state/...`; resolution + containment move under `base_dir(root)`.

- [ ] **Step 1: Write failing path-construction + behavioral test** (new `tests/unit/uacp_state/test_state_paths.py`)

```python
"""C-1 guard: state writers operate under .uacp/state, not flat state/."""
import json
from pathlib import Path

import state as state_mod


def _args(tmp_path, target, content="x: 1\n"):
    return {
        "workspace": str(tmp_path),
        "target_path": target,
        "content": content,
        "reason": "test",
        "authority_artifact": "proposals/r1-intent.md",
        "uacp_run_id": "r1",
    }


def test_state_write_lands_under_uacp(tmp_path, monkeypatch):
    monkeypatch.setenv("UACP_ROOT", str(tmp_path))
    (tmp_path / ".uacp" / "state" / "runs").mkdir(parents=True)
    out = json.loads(state_mod._handle_uacp_state_write(_args(tmp_path, "state/runs/r1.yaml")))
    assert out.get("ok") is True, out
    assert (tmp_path / ".uacp" / "state" / "runs" / "r1.yaml").exists()
    assert not (tmp_path / "state" / "runs" / "r1.yaml").exists()
```

> Adjust the `_handle_uacp_state_write` arg shape to match the real signature if it differs; the assertion that matters is **lands under `.uacp/state`, not flat `state/`**.

- [ ] **Step 2: Run → FAIL**

Run: `python3 -m pytest tests/unit/uacp_state/test_state_paths.py -q`
Expected: FAIL (writes to flat `state/`).

- [ ] **Step 3: Implement** — at the top of `state.py` add:
```python
from config import base_dir
```
Then in **each** governed-writer handler, after `root = policy.uacp_root` (or equivalent), introduce a governed base and swap the containment roots:
- Resolve caller paths against `base_dir(root)`: change `target = _resolve_uacp_path(target_path, root)` → `target = _resolve_uacp_path(target_path, base_dir(root))`.
- Every containment literal `(root / "state" ...)` → `(base_dir(root) / "state" ...)`. Concretely:
  - 108-109 (gate-ledger): `ledger_root = (base_dir(root) / "state" / "gate-ledger").resolve()` and the guard `(base_dir(root) / "state")`.
  - 143: `state_root = (base_dir(root) / "state").resolve()`
  - 150: `gate_ledger_root = (base_dir(root) / "state" / "gate-ledger").resolve()`
  - 157: `run_registry_path = (base_dir(root) / "state" / "run-registry.yaml").resolve()`
  - 165: `escalations_root = (base_dir(root) / "state" / "escalations").resolve()`
  - 181: `current_pointer_path = (base_dir(root) / "state" / "current.yaml").resolve()`
  - 271: `registry_path = (base_dir(root) / "state" / "run-registry.yaml").resolve()`
  - 400-401: `out_path = (base_dir(root) / "state" / "escalations" / f"{run_id}.jsonl").resolve()`; `escalations_root = (base_dir(root) / "state" / "escalations").resolve()`
- The response `relative_to(root)` lines (e.g. 120): change to `relative_to(base_dir(root))` so the reported path stays base-relative (`state/gate-ledger/r1.jsonl`).

> **Use a local** `base = base_dir(root)` at the top of each handler to keep diffs tight and avoid re-calling (the call is cached, but a local reads cleaner).

- [ ] **Step 4: Run → PASS** (new test + existing state suite)

Run: `python3 -m pytest tests/unit/uacp_state/ -q`
Expected: PASS.

- [ ] **Step 5: Lint + commit**

```bash
/Users/mike/.local/bin/ruff check skills/uacp-state/scripts/state.py
git add skills/uacp-state/scripts/state.py tests/unit/uacp_state/test_state_paths.py
git commit -m "refactor(state): governed writers contain under .uacp/state via base_dir"
```

---

# Task 7: `state_machine.py` current pointer

**Files:**
- Modify: `skills/uacp-state/scripts/state_machine.py:168`

- [ ] **Step 1: Repoint** — add `from config import dir_for` near the top imports, then:
- line 168: `current_path = workspace / "state" / "current.yaml"`
  → `current_path = dir_for(workspace, "state") / "current.yaml"`

- [ ] **Step 2: Run state-machine tests**

Run: `python3 -m pytest tests/unit/uacp_state/test_state_machine.py -q`
Expected: PASS.

- [ ] **Step 3: Lint + commit**

```bash
/Users/mike/.local/bin/ruff check skills/uacp-state/scripts/state_machine.py
git add skills/uacp-state/scripts/state_machine.py
git commit -m "refactor(state): state_machine reads current.yaml under .uacp/state"
```

---

# Task 8: Guardian state containment + shell-token scanner (`core.py`)

**Files:**
- Modify: `skills/uacp-core/scripts/core.py:556` (scanner) and `:566-570` (`_path_is_under_state`)
- Test: `tests/unit/uacp_core/test_guardian_containment_paths.py` (new)

> **C-1 HIGH:** a behavioral-only test can pass with split-brain paths (silent containment bypass). Assert on path construction **and** behavior.

- [ ] **Step 1: Write failing tests** (new `tests/unit/uacp_core/test_guardian_containment_paths.py`)

```python
"""C-1 HIGH: Guardian state containment must target .uacp/state, not flat state/."""
from pathlib import Path

from core import GuardianPolicy


def _policy(tmp_path):
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "guardian-policy.yaml").write_text("schema_version: '0.1'\n")
    return GuardianPolicy.load(tmp_path)


def test_under_state_is_uacp_state(tmp_path):
    g = _policy(tmp_path)
    # A path under .uacp/state IS contained; the flat state/ path is NOT.
    assert g._path_is_under_state(str(tmp_path / ".uacp" / "state" / "runs" / "r1.yaml")) is True
    assert g._path_is_under_state(str(tmp_path / "state" / "runs" / "r1.yaml")) is False


def test_scanner_flags_uacp_relative_writes(tmp_path):
    g = _policy(tmp_path)
    # `.uacp/state/x` written from workspace=root must be collected as a candidate.
    paths = g._extract_paths_from_shell("touch .uacp/state/x", context_paths=[tmp_path])
    assert any(".uacp/state/x" in p for p in paths)
```

> Confirm the real method names/signatures (`_path_is_under_state`, the shell extractor) before finalizing — match them exactly. If `GuardianPolicy.load` needs a fuller policy stub, mirror `conftest`'s `guardian-policy.yaml`.

- [ ] **Step 2: Run → FAIL**

Run: `python3 -m pytest tests/unit/uacp_core/test_guardian_containment_paths.py -q`
Expected: FAIL (state containment still flat; scanner lacks `.uacp/`).

- [ ] **Step 3: Implement**

Add import near the top of `core.py`:
```python
from config import base_dir
```
- `_path_is_under_state` (569): `state_root = (self.policy.uacp_root / "state").resolve()`
  → `state_root = (base_dir(self.policy.uacp_root) / "state").resolve()`
- Scanner prefix tuple (556): add `.uacp/` and rename `.outputs/`→`resolutions/`:
```python
if token.startswith(("./", "../", ".uacp/", "state/", "config/", "docs/", "proposals/", "plans/", "executions/", "verification/", "resolutions/", "knowledge/", "uacp/")):
```
(Keeps the bare governed names — defense-in-depth — and adds the real post-migration prefix `.uacp/`.)

- [ ] **Step 4: Run → PASS** (new test + full Guardian unit suite)

Run: `python3 -m pytest tests/unit/uacp_core/ -q -k "guardian or containment"`
Expected: PASS.

- [ ] **Step 5: Lint + commit**

```bash
/Users/mike/.local/bin/ruff check skills/uacp-core/scripts/core.py
git add skills/uacp-core/scripts/core.py tests/unit/uacp_core/test_guardian_containment_paths.py
git commit -m "fix(guardian): state containment + shell scanner target .uacp/ (C-1)"
```

---

# Task 9: Heartgate base-resolution + `.outputs`→`resolutions`

**Files:**
- Modify: `skills/uacp-core/scripts/core.py` (Heartgate: `__init__` ~695-702; sites 811, 950, 1369-1372, 1426, 1576, 2025, 2211, 2262-2265, 2301-2303)

This is the riskiest task — smallest steps, full suite after each sub-step.

- [ ] **Step 1: Introduce `self.governed_root`** in `Heartgate.__init__` (after `self.uacp_root = resolve_uacp_root(uacp_root)`, ~line 697):
```python
self.governed_root = base_dir(self.uacp_root)
```
(`base_dir` already imported in T8. `config/` reads stay on `self.uacp_root`.)

- [ ] **Step 2: Repoint state gate-ledger joins** (1426, 1576, 2025):
each `ledger_path = self.uacp_root / "state" / "gate-ledger" / f"{run_id}.jsonl"`
→ `ledger_path = self.governed_root / "state" / "gate-ledger" / f"{run_id}.jsonl"`

Run: `python3 -m pytest tests/ -q -k heartgate` → note progress.

- [ ] **Step 3: Repoint phase-dir + resolutions gate paths.**
- 2211: `scope_path = self.uacp_root / "plans" / f"{run_id}-scope.yaml"`
  → `scope_path = self.governed_root / "plans" / f"{run_id}-scope.yaml"`
- 1369-1372 (rename `.outputs`→`resolutions`, base-relative strings unchanged otherwise):
```python
        selection_rel = f"resolutions/{run_id}-resolve-selection.yaml"
        closure_rel = f"resolutions/{run_id}-closure.yaml"
        readiness_rel = f"verification/{run_id}-resolve-readiness.yaml"
        package_rel = f"resolutions/{run_id}"
```
- 2262: `template = str(schema.get("path_template") or ".outputs/{run_id}-lessons.yaml")`
  → `template = str(schema.get("path_template") or "resolutions/{run_id}-lessons.yaml")`
- 2263: `path = self.uacp_root / template.replace("{run_id}", run_id)`
  → `path = self.governed_root / template.replace("{run_id}", run_id)`
- 2265: `blockers.append(f"lessons artifact missing: {path.relative_to(self.uacp_root)}")`
  → `relative_to(self.governed_root)` (so the message reads `resolutions/r1-lessons.yaml`).

- [ ] **Step 4: Repoint accepted-exception prefix checks** (2301, 2303):
```python
            if not artifact_path.startswith(("verification/", "resolutions/")):
                continue
            if run_id and not artifact_path.startswith((f"verification/{run_id}", f"resolutions/{run_id}")):
```

- [ ] **Step 5: Repoint the base-relative resolver helpers.** Inspect each helper that joins a base-relative `rel` against `self.uacp_root` and move *artifact/state* resolution to `self.governed_root` (leave `config/` reads on `self.uacp_root`). Confirmed sites: 811 (`raw_path = self.uacp_root / raw_path`), 950 (`path = self.uacp_root / path`), and the bodies of `_load_yaml_under_root`, `_dir_under_root_exists`, `_artifact_path_exists`, `_canon_write_path`, `_offline_validate_artifacts`.

For each, read the surrounding context first:
```bash
grep -n "self.uacp_root" skills/uacp-core/scripts/core.py
```
Decision rule: if the joined `rel`/`raw_path` is an **artifact/state path** (a `write_paths` entry, a gate artifact, `state/…`, `proposals/…`, `verification/…`, `resolutions/…`) → use `self.governed_root`. If it is a **config file** (`config/…`, artifact-schemas, phase-transitions) → keep `self.uacp_root`. Sites 811 and 950 resolve caller artifact paths → `self.governed_root`.

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: PASS for all `tests/unit/uacp_core` Heartgate tests and the `tests/e2e` closure/evidence tests **after** T11 (e2e fixtures). At this point e2e may still reference `.outputs/` directly — those are fixed in T11. Confirm unit Heartgate is green; e2e may stay red until T11.

- [ ] **Step 7: Lint + commit**

```bash
/Users/mike/.local/bin/ruff check skills/uacp-core/scripts/core.py
git add skills/uacp-core/scripts/core.py
git commit -m "fix(heartgate): resolve artifacts under .uacp/ governed_root; .outputs->resolutions"
```

---

# Task 10: Guardian plugin artifact-write roots (`uacp_guardian/__init__.py`)

**Files:**
- Modify: `runtime-adapters/hermes/plugins/uacp_guardian/__init__.py` (artifact-write handler ~624-636; transition handler ~748-752; and any `_resolve_uacp_path(target_path, root)` base)

- [ ] **Step 1: Repoint resolution base + rename `outputs`→`resolutions`.**

In the `uacp_artifact_write` handler:
- `target = _resolve_uacp_path(target_path, root)` → `target = _resolve_uacp_path(target_path, base_dir(root))`
- `rel = target.relative_to(root)` → `rel = target.relative_to(base_dir(root))`
- 628: `allowed_roots = {"plans", "proposals", "executions", "verification", "outputs", "knowledge"}`
  → `allowed_roots = {"plans", "proposals", "executions", "verification", "resolutions", "knowledge"}`
- 635 error string: replace `.outputs/` with `resolutions/`.

In the transition handler:
- 748: `target = _resolve_uacp_path(transition_path, root)` → resolve under `base_dir(root)`
- 749: `rel = target.relative_to(root.resolve())` → `rel = target.relative_to(base_dir(root))`
- 750: `allowed_transition_roots = {"state", "verification", "executions", "plans", "proposals", "outputs", "knowledge"}`
  → replace `"outputs"` with `"resolutions"`.

Add `from config import base_dir` to the plugin imports (mirror however `_resolve_uacp_path` is imported there).

> **Verify the import path:** the plugin lives outside `skills/uacp-core/scripts/`. Check how it currently imports kernel helpers (`grep -n "import" runtime-adapters/hermes/plugins/uacp_guardian/__init__.py | grep -i "resolve\|core\|filesystem"`) and add `base_dir` the same way. Conftest already injects `skills/uacp-core/scripts` onto `sys.path`, so `from config import base_dir` resolves under pytest.

- [ ] **Step 2: Run the Guardian plugin tests**

Run: `python3 -m pytest tests/ -q -k "guardian or artifact_write or transition"`
Expected: PASS.

- [ ] **Step 3: Lint + commit**

```bash
/Users/mike/.local/bin/ruff check runtime-adapters/hermes/plugins/uacp_guardian/__init__.py
git add runtime-adapters/hermes/plugins/uacp_guardian/__init__.py
git commit -m "fix(guardian-plugin): artifact/transition writes under .uacp/; resolutions root"
```

---

# Task 11: e2e fixtures + `.outputs`→`resolutions`

**Files:**
- Modify: `tests/e2e/test_coherence.py`, `tests/e2e/test_evidence_completeness.py`, `tests/e2e/test_heartgate_closure.py`, `tests/e2e/test_deferral_completeness.py`

- [ ] **Step 1: Grep the e2e `.outputs` references**

Run: `grep -rn '\.outputs' tests/e2e/`
Expected sites (from inventory): `test_heartgate_closure.py:56`; `test_deferral_completeness.py:44`; `test_evidence_completeness.py:79,186-187`; `test_coherence.py:117-118,206,289`.

- [ ] **Step 2: Rewrite each reference.** The stored/queried path strings are base-relative, and the on-disk dir is now `.uacp/`:
- Template strings `".outputs/{run_id}-lessons.yaml"` → `"resolutions/{run_id}-lessons.yaml"`.
- Glob `".outputs/{run_id}*"` → `"resolutions/{run_id}*"`.
- On-disk paths `temp_uacp_root / ".outputs" / f"{run_id}-lessons.yaml"` → `temp_uacp_root / ".uacp" / "resolutions" / f"{run_id}-lessons.yaml"`.
- `(root / ".outputs").mkdir(...)` → `(root / ".uacp" / "resolutions").mkdir(parents=True, exist_ok=True)`.

Apply the same base-relative principle to any `state/…`, `verification/…`, `plans/…` **on-disk** writes in these files: an on-disk path must gain the `.uacp/` segment (`temp_uacp_root / ".uacp" / "verification" / …`); a **stored YAML string** stays base-relative and only swaps `.outputs`→`resolutions`. Read each test top-to-bottom and apply the rule consistently.

- [ ] **Step 3: Run the full suite — expect GREEN**

Run: `python3 -m pytest tests/ -q`
Expected: **328 passed, 2 skipped** (baseline restored; the kernel + tests now agree on `.uacp/`).

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/
git commit -m "test(e2e): .uacp/ layout + resolutions/ artifact refs"
```

---

# Task 12: `scripts/migrate_to_uacp_dir.py` (hard cut + C-2 rewrite)

**Files:**
- Create: `scripts/migrate_to_uacp_dir.py`
- Test: `tests/unit/test_migrate_to_uacp_dir.py` (new)

- [ ] **Step 1: Write failing tests** (new `tests/unit/test_migrate_to_uacp_dir.py`)

```python
"""Migrate an OLD flat repo layout to .uacp/, rewriting in-flight YAML refs (C-2)."""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import migrate_to_uacp_dir as mig  # noqa: E402


def _old_repo(tmp_path):
    (tmp_path / "state" / "runs").mkdir(parents=True)
    (tmp_path / "state" / "gate-ledger").mkdir(parents=True)
    (tmp_path / ".outputs").mkdir(parents=True)
    (tmp_path / "proposals").mkdir(parents=True)
    (tmp_path / "plans").mkdir(parents=True)
    (tmp_path / "verification").mkdir(parents=True)
    (tmp_path / "knowledge").mkdir(parents=True)
    # an in-flight manifest referencing .outputs/ (must be rewritten)
    (tmp_path / "state" / "runs" / "r1.yaml").write_text(yaml.safe_dump({
        "run_id": "r1",
        "artifacts": {"closure": ".outputs/r1-closure.yaml",
                      "intent": "proposals/r1-intent.md"},
    }))
    # a gate-ledger line with an artifact_path under .outputs/
    (tmp_path / "state" / "gate-ledger" / "r1.jsonl").write_text(
        '{"gate": "g", "run_id": "r1", "artifact_path": ".outputs/r1-closure.yaml"}\n'
    )
    (tmp_path / ".outputs" / "r1-closure.yaml").write_text("kind: uacp.resolve_closure\n")


def test_moves_dirs_under_uacp(tmp_path):
    _old_repo(tmp_path)
    mig.migrate(tmp_path)
    assert (tmp_path / ".uacp" / "state" / "runs" / "r1.yaml").exists()
    assert (tmp_path / ".uacp" / "resolutions" / "r1-closure.yaml").exists()
    assert (tmp_path / ".uacp" / "proposals").is_dir()
    # old locations gone
    assert not (tmp_path / "state").exists()
    assert not (tmp_path / ".outputs").exists()


def test_rewrites_outputs_token_in_yaml(tmp_path):
    _old_repo(tmp_path)
    mig.migrate(tmp_path)
    manifest = yaml.safe_load((tmp_path / ".uacp" / "state" / "runs" / "r1.yaml").read_text())
    assert manifest["artifacts"]["closure"] == "resolutions/r1-closure.yaml"
    assert manifest["artifacts"]["intent"] == "proposals/r1-intent.md"  # untouched
    ledger = (tmp_path / ".uacp" / "state" / "gate-ledger" / "r1.jsonl").read_text()
    assert "resolutions/r1-closure.yaml" in ledger
    assert ".outputs/" not in ledger


def test_idempotent_second_run_is_noop(tmp_path):
    _old_repo(tmp_path)
    mig.migrate(tmp_path)
    mig.migrate(tmp_path)  # must not raise
    assert (tmp_path / ".uacp" / "state" / "runs" / "r1.yaml").exists()


def test_emits_starter_config(tmp_path):
    _old_repo(tmp_path)
    mig.migrate(tmp_path)
    assert (tmp_path / ".uacp" / "config.toml").exists()
```

- [ ] **Step 2: Run → FAIL**

Run: `python3 -m pytest tests/unit/test_migrate_to_uacp_dir.py -q`
Expected: FAIL (`No module named 'migrate_to_uacp_dir'`).

- [ ] **Step 3: Implement** `scripts/migrate_to_uacp_dir.py`:

```python
#!/usr/bin/env python3
"""Hard-cut migration of a UACP repo's flat runtime dirs into the .uacp/ namespace.

Moves state/, .outputs/ (-> resolutions/), and the phase dirs under .uacp/, then
rewrites the `.outputs/` token to `resolutions/` inside already-emitted YAML/JSONL
so in-flight runs stay resolvable (council finding C-2). No fallback / dual-read.

Usage:  python3 scripts/migrate_to_uacp_dir.py [REPO_ROOT]   (default: cwd)
"""
from __future__ import annotations

import sys
from pathlib import Path

# (dir-name-at-old-root, subdir-name-under-.uacp)
_MOVES = [
    ("state", "state"),
    (".outputs", "resolutions"),
    ("proposals", "proposals"),
    ("plans", "plans"),
    ("executions", "executions"),
    ("verification", "verification"),
    ("knowledge", "knowledge"),
]
_REWRITE_SUFFIXES = {".yaml", ".yml", ".jsonl", ".json", ".md"}


def _rewrite_outputs_token(base: Path) -> None:
    """Replace base-relative `.outputs/` with `resolutions/` in moved text files."""
    for path in base.rglob("*"):
        if not path.is_file() or path.suffix not in _REWRITE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if ".outputs/" not in text and ".outputs " not in text:
            continue
        # Word-boundary-ish: only the leading-token form `.outputs/` is a path ref.
        new = text.replace(".outputs/", "resolutions/")
        if new != text:
            path.write_text(new, encoding="utf-8")


def migrate(repo_root: Path) -> None:
    repo_root = Path(repo_root).resolve()
    base = repo_root / ".uacp"
    base.mkdir(exist_ok=True)
    for old_name, sub in _MOVES:
        src = repo_root / old_name
        dst = base / sub
        if not src.exists():
            continue  # idempotent: already migrated or never existed
        if dst.exists():
            raise SystemExit(
                f"refusing to overwrite existing {dst}; resolve manually"
            )
        src.rename(dst)
    _rewrite_outputs_token(base)
    starter = base / "config.toml"
    if not starter.exists():
        starter.write_text(
            "# UACP per-project config overrides. Defaults ship with the kernel.\n"
            "# Example:\n#   [paths]\n#   base = \".uacp\"\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    migrate(Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd())
    print("migrated to .uacp/")
```

- [ ] **Step 4: Run → PASS**

Run: `python3 -m pytest tests/unit/test_migrate_to_uacp_dir.py -q`
Expected: PASS (all four tests).

- [ ] **Step 5: Lint + commit**

```bash
/Users/mike/.local/bin/ruff check scripts/migrate_to_uacp_dir.py tests/unit/test_migrate_to_uacp_dir.py
git add scripts/migrate_to_uacp_dir.py tests/unit/test_migrate_to_uacp_dir.py
git commit -m "feat(migrate): scripts/migrate_to_uacp_dir.py — move dirs + rewrite .outputs token (C-2)"
```

---

# Task 13: `.outputs`→`resolutions` in skill / doc references (RESOLVE)

**Files:**
- Modify: skill + doc files that instruct writing to `.outputs/` (grep-discovered)

- [ ] **Step 1: Grep for `.outputs` outside Python**

Run: `grep -rn '\.outputs' skills/ docs/ config/ --include='*.md' --include='*.yaml' --include='*.yml' | grep -v 'docs/plans/2026-06-15'`
(Exclude the design/roadmap plan docs — they describe the *old* layout intentionally.)

- [ ] **Step 2: Rewrite path references** to base-relative `resolutions/` (e.g. a RESOLVE SKILL.md instruction `write closure to .outputs/{run_id}-closure.yaml` → `resolutions/{run_id}-closure.yaml`). Do **not** touch the 9 `authority_source:` refs (Slice 4 / C-3) or `phase-transitions.yaml`/`artifact-schemas.yaml` grammar (Slice 4). Only `.outputs`→`resolutions` token renames here.

> If a `config/*.yaml` (e.g. `gate-selection.yaml`, `artifact-schemas.yaml`) carries a `.outputs/` `path_template`, rename the token to `resolutions/` — the template is base-relative and resolved under `governed_root` (T9). Re-run the suite after touching any config YAML.

- [ ] **Step 3: Run the full suite**

Run: `python3 -m pytest tests/ -q`
Expected: **328 passed, 2 skipped**.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "docs(skills): RESOLVE references resolutions/ (was .outputs/)"
```

---

# Task 14: Audit standalone harness scripts

**Files:**
- Inspect (update or document): `scripts/phase{1,2,3,4}_verify.py`, `scripts/live_guardian_probe.py`, `scripts/import_loader_verify.py`

These build their own tmp `state/`/`.outputs/` layout and call kernel writers/engines directly. They are **not** in `pytest tests/`, so the suite cannot catch their breakage.

- [ ] **Step 1: Confirm they are excluded from the guarded suite**

Run: `python3 -m pytest tests/ -q --collect-only | grep -i "phase.*verify\|live_guardian\|import_loader"`
Expected: no output (not collected).

- [ ] **Step 2: For each script, decide.** If a script is referenced by CI / a Makefile / a docs runbook (`grep -rn "phase2_verify\|live_guardian_probe" --include='*.md' --include='*.yml' --include='Makefile' .`), update its tmp layout to `.uacp/` (build `tmp/.uacp/state/...`, write base-relative `resolutions/` strings) and re-run it manually:
```bash
python3 scripts/phase2_verify.py && echo OK
```
If a script is **not** referenced anywhere, add a one-line note to its module docstring: `# NOTE: pre-.uacp/ layout — see Slice 2 plan T14; update before reuse.` and leave it (no behavioral guard depends on it).

- [ ] **Step 3: Commit** whatever changed

```bash
git add -A
git commit -m "chore(scripts): align/flag standalone verify harnesses for .uacp/ layout"
```

---

# Task 15: Full-suite + ruff gate, then council review

- [ ] **Step 1: Full suite**

Run: `python3 -m pytest tests/ -q`
Expected: **328 passed, 2 skipped**.

- [ ] **Step 2: Ruff over all touched code**

Run:
```bash
/Users/mike/.local/bin/ruff check \
  skills/uacp-core/scripts/config.py \
  skills/uacp-core/scripts/core.py \
  skills/uacp-core/scripts/engines/ \
  skills/uacp-state/scripts/ \
  runtime-adapters/hermes/plugins/uacp_guardian/__init__.py \
  scripts/migrate_to_uacp_dir.py \
  tests/
```
Expected: clean (strict `E,F,I,UP,B`).

- [ ] **Step 3: Residual-scatter scan — prove no flat-root resolver remains**

Run:
```bash
grep -rn '/ "state"\|/ ".outputs"\|"\.outputs/' skills/uacp-core/scripts skills/uacp-state/scripts runtime-adapters/hermes/plugins/uacp_guardian \
  | grep -v 'get("state")\|\.get(.state\|cluster\|blocker\|finding\|disposition\|"state\.uacp"'
```
Expected: only the new `config.dir_for(...,"state")` call-sites and `base_dir(...) / "state"` containment — **no** `.outputs` and no flat `root / "state"` resolution.

- [ ] **Step 4: Council review (kernel change — mandatory).** Dispatch the council (Task tool / Agent) with three lenses over the diff (`git diff main...feat/config-collapse-slice2`):
  1. **Containment auditor** — is there any split-brain path where a write or read still targets flat `state/`/`.outputs/` while its check targets `.uacp/` (silent bypass)? Verify `_path_is_under_state`, governed writers, and Heartgate `governed_root` all agree.
  2. **Migration validator** — does T12 rewrite *every* in-flight reference class (manifest artifacts, gate-ledger `artifact_path`, scope/closure refs)? Any unrewritten `.outputs/` string class?
  3. **Devil's advocate** — what breaks for an operator who set a `[paths] base` override, or a run mid-flight at migration time? Is `config/` correctly left at project root this slice?

Resolve every material finding before merge (zero unresolved — Authority-Chain invariant #4).

- [ ] **Step 5: Finish the branch** — use `superpowers:finishing-a-development-branch` to choose merge/PR. Update this plan's checkboxes to done.

---

## Self-Review (author checklist — completed)

- **Spec coverage:** C-1 path inventory → T1-T10 + T15 §3 residual scan; C-1 explicit path-construction tests → T3/T6/T8 (assert old path absent AND new `.uacp/` present). C-2 YAML rewrite → T12. conftest `.uacp/` layout → T2. `.outputs`→`resolutions` rename → T5/T9/T10/T11/T13. migrate script → T12. Out-of-scope (validate_uacp_artifacts.py, phase-transitions, `_default_toml_path`) explicitly deferred with rationale.
- **Placeholder scan:** every code step carries real code or an exact file:line→replacement. The two "verify the real signature" notes (T6 args, T8 method names, T10 import path) are deliberate guards, not placeholders — the surrounding assertion/edit is fully specified.
- **Type/name consistency:** `base_dir(root)`, `dir_for(root, key)`, `get_config`, `clear_config_cache`, `self.governed_root` used identically across all tasks. Convention (base-relative strings; `.outputs`→`resolutions`) applied uniformly.
