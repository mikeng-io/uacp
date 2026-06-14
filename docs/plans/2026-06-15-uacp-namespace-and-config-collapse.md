# `.uacp/` Namespace + Config Collapse — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development) to implement this plan task-by-task.

**Goal:** Collapse UACP's 13 config YAMLs into one `uacp.toml` (knobs, incl. a `[paths]`
roots map) plus grammar-as-code, behind a `config.py` resolver, and relocate the entire
per-project footprint under `.uacp/` — all guarded by the existing 321-test suite.

**Architecture:** Three tiers — **knobs** in `uacp.toml` (shipped default deep-merged with
a per-project `.uacp/config.toml`), **grammar** in Python (extending `engines/domain`),
and a `config.py` Pydantic **resolver** that everything reads through. Hard-cut migration
(no fallback). Incremental: green after every slice.

**Tech Stack:** Python 3.13+, Pydantic v2, `tomllib` (stdlib read) / `tomli-w` or hand-emit
for writes, PyYAML (transitional), pytest, ruff.

**Design doc:** `docs/plans/2026-06-15-uacp-namespace-and-config-collapse-design.md`
Run with: `python3 -m pytest` (default `python` is anaconda-3.8 — unusable). Lint:
`/Users/mike/.local/bin/ruff`.

---

## Reference (verified)

- `config/roots.yaml` defines `UACP_ROOT.contains: [docs, config, proposals, plans,
  executions, verification, .outputs, knowledge, state]` → becomes `[paths]` in `uacp.toml`.
- Path resolution today: `skills/uacp-core/scripts/filesystem.py::_resolve_uacp_path`
  (traversal-safe, resolves rel against a workspace root). The new resolver wraps this and
  adds the `[paths]` map.
- `config/uacp.toml` (238 lines) already exists — the collapse target *extends* it.
- Engines read config via `skills/uacp-core/scripts/engines/io/` (`load_phase_transitions`,
  etc.) — these repoint to `config.py`/grammar as slices land.

---

# Slice 1 — `config.py` resolver + default `uacp.toml` + `[paths]`

Foundation. Introduces the resolver and the `[paths]` knob without yet moving any other
config or relocating dirs (those are Slices 2–5). Nothing else changes behavior yet.

### Task 1.1: Default `uacp.toml` `[paths]` section

**Files:**
- Modify: `config/uacp.toml` (append a `[paths]` table)

**Step 1:** Append a `[paths]` table encoding the roots map with `.uacp/` as base:
```toml
[paths]
base = ".uacp"
state = "state"
proposals = "proposals"
plans = "plans"
executions = "executions"
verification = "verification"
resolutions = "resolutions"   # replaces the old .outputs/
knowledge = "knowledge"
config = "config.toml"
```
**Step 2:** Validate it parses: `python3 -c "import tomllib; tomllib.load(open('config/uacp.toml','rb')); print('ok')"` → `ok`.
**Step 3:** Commit `feat(config): add [paths] roots map to uacp.toml`.

### Task 1.2: `config.py` — load + deep-merge (TDD)

**Files:**
- Create: `skills/uacp-core/scripts/config.py`
- Test: `tests/unit/uacp_core/test_config.py`

**Step 1: Write failing tests**
```python
from config import load_config, UacpConfig

def test_loads_default(tmp_path, monkeypatch):
    # default uacp.toml ships with the kernel; load_config(None) returns it
    cfg = load_config(project_root=None)
    assert isinstance(cfg, UacpConfig)
    assert cfg.paths.base == ".uacp"

def test_project_override_deep_merges(tmp_path):
    (tmp_path / ".uacp").mkdir()
    (tmp_path / ".uacp" / "config.toml").write_text('[paths]\nbase = ".governed"\n')
    cfg = load_config(project_root=tmp_path)
    assert cfg.paths.base == ".governed"           # overridden
    assert cfg.paths.proposals == "proposals"      # default preserved (deep merge, not replace)
```

**Step 2: Run → FAIL** (`pytest tests/unit/uacp_core/test_config.py -v`) — module missing.

**Step 3: Implement** `config.py`:
- `Paths(BaseModel)` with fields matching the `[paths]` table (defaults inline so a partial override still validates).
- `UacpConfig(BaseModel)` with `paths: Paths` (+ a permissive `extra="allow"` for knob sections added in later slices).
- `_DEFAULT_TOML = <kernel-shipped default path>` — read the repo's `config/uacp.toml` as the default source (later the plugin ships it).
- `load_config(project_root)`: `tomllib.load` the default; if `project_root/.uacp/config.toml` exists, `tomllib.load` it and **deep-merge** (recursive dict merge, override wins on leaves); validate into `UacpConfig`. Never raise on a missing override (default-only).

**Step 4: Run → PASS.**

**Step 5: Commit** `feat(config): config.py resolver with default + .uacp override deep-merge`.

### Task 1.3: Path resolution from `[paths]` (TDD)

**Files:**
- Modify: `skills/uacp-core/scripts/config.py` (add resolver methods)
- Test: `tests/unit/uacp_core/test_config.py` (append)

**Step 1: Write failing tests**
```python
def test_resolve_phase_dir(tmp_path):
    cfg = load_config(project_root=tmp_path)
    # resolutions replaces .outputs; resolves under <root>/.uacp/resolutions
    p = cfg.resolve(tmp_path, "resolutions", "run-1-closure.yaml")
    assert p == tmp_path / ".uacp" / "resolutions" / "run-1-closure.yaml"

def test_resolve_rejects_traversal(tmp_path):
    cfg = load_config(project_root=tmp_path)
    with pytest.raises(ValueError):
        cfg.resolve(tmp_path, "state", "../../etc/passwd")
```

**Step 2: Run → FAIL.**

**Step 3: Implement** `UacpConfig.resolve(root, path_key, *parts)`:
- look up the subdir from `self.paths` by key, join `root / base / subdir / *parts`,
- reuse `filesystem._resolve_uacp_path` for traversal safety (must stay within `root/base`),
- raise `ValueError` on escape (mirror existing semantics).

**Step 4: Run → PASS.** Then full suite: `python3 -m pytest tests/ -q` (still 321 + new).

**Step 5: Commit** `feat(config): [paths]-driven path resolution with traversal safety`.

### Task 1.4: ruff + register the new module

**Step 1:** `ruff check skills/uacp-core/scripts/config.py tests/unit/uacp_core/test_config.py` → clean (add to the strict path set in `pyproject` if needed). **Step 2:** Ensure conftest `sys.path` already exposes `config` (it injects `skills/uacp-core/scripts`). **Step 3:** Commit any lint/format. 

### Slice 1 done-when
- `config.py` loads default + deep-merges `.uacp/config.toml`; `[paths]` resolves under
  `.uacp/`; traversal rejected; ruff clean; full suite green. **No other config moved and
  no dirs relocated yet** — purely additive.

---

# Roadmap — Slices 2–5 (own detailed plans authored as each predecessor lands)

Each is large and depends on the prior slice's exact shape; expand into bite-sized tasks
when its predecessor is green. All are **harness-guarded** — `pytest tests/ -q` green after
every step.

### Slice 2 — Relocate runtime dirs under `.uacp/` (hard cut)
- Repoint the kernel + engines from `state/`, `.outputs/`, `proposals/…` to
  `cfg.resolve(...)` under `.uacp/`. RESOLVE artifacts go to `.uacp/resolutions/` (the
  `.outputs`→`resolutions` rename eliminates the F-EV-01 token class).
- Write `scripts/migrate_to_uacp_dir.py`: move existing `state/`, `.outputs/`→`resolutions/`,
  and the phase dirs + `knowledge/` into `.uacp/`; no fallback. Test: old layout → migrate
  → suite green.
- Update `tests/conftest.py` `temp_uacp_root` to build the `.uacp/` layout.

### Slice 3 — Collapse knob YAMLs into `uacp.toml`
- Fold `guardian-policy` (mode + tool_classification), `autonomy-policy`, `model-registry`,
  `runtime-bindings`, slimmed `review-routing` + `gate-selection`, `version-control`,
  `memory-policy` into `uacp.toml` sections; repoint readers (Guardian.load etc.) to
  `config.py`. Reserve a `[memory]` slot (Honcho, later). Delete each YAML as it lands.

### Slice 4 — Move grammar YAMLs into Python
- `artifact-schemas`, run-state schema (`state`), `evidence-clusters` → Pydantic models in
  `engines/domain` (extend what's there). Then `phase-transitions.yaml` (859 lines) → code
  **one stage at a time**, repointing Guardian/Heartgate/engines. Apply **F-T3-01
  fail-closed** + its regression test. This is the riskiest slice — smallest steps.

### Slice 5 — Finalize
- Delete remaining `config/*.yaml` (incl. `roots.yaml`); finish migrate script; update
  `AGENTS.md`, `CLAUDE.md`, `docs/INDEX.md`, and skill path references. Confirm no
  `config/*.yaml` and no root-level `state/`/`.outputs/`/phase dirs remain; suite green.

### Out of scope (sequenced after)
Plugin packaging · Honcho `[memory]` adapter · prompt caching.
