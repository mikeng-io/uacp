# UACP Commands

How to run verify scripts, probes, and validators. UACP itself does not ship a build system — these are Python 3 scripts that depend on the Hermes adapter being importable.

## Prerequisites

- Python 3.12+
- PyYAML
- `UACP_ROOT` environment variable pointing at the UACP repo root (or run scripts from the repo root).

## Per-phase verify scripts

Each phase has a deterministic verify script that exercises the fail-closed kernel branches landed in that phase. All five must pass after any non-trivial kernel or config change.

```bash
python3 scripts/phase0_verify.py    # Phase 0 — 14 checks
python3 scripts/phase1_verify.py    # Phase 1 — 23 checks
python3 scripts/phase2_verify.py    # Phase 2 — 18 checks
python3 scripts/phase3_verify.py    # Phase 3 — 30 checks
python3 scripts/phase4_verify.py    # Phase 4 — 20 checks
```

Each script writes JSON to stdout. `status: pass` means all sub-checks passed; `status: fail` lists the failing check names.

Quick all-pass sweep:

```bash
for n in 0 1 2 3 4; do
  python3 scripts/phase${n}_verify.py 2>&1 | \
    python3 -c "import json,sys; d=json.load(sys.stdin); print('phase${n}:', d['status'])"
done
```

## Live Guardian probe

Exercises the Guardian decision flow + Heartgate `uacp_heartgate_check` tool end-to-end against a temporary UACP root.

```bash
python3 scripts/live_guardian_probe.py
```

Known pre-existing failures (4):
- `loader_reports_enabled_user:thread_title_sync`
- `loader_reports_enabled_user:uacp_guardian`
- `guardian_blocks_unknown_plugin_mutator`
- `uacp_heartgate_check_passes_valid_transition`

These four are tracked as Phase 0 carry-overs `pc_7` and `pc_8` (see [`docs/plans/phase5-reserved-slot.md`](docs/plans/phase5-reserved-slot.md)). Phase 5 must remediate or formally defer.

## Artifact validator

Validates UACP artifacts against their declared schemas:

```bash
python3 scripts/validate_uacp_artifacts.py --root /home/norty/.hermes/uacp
```

## Heartgate transition check (one-off)

To validate a specific transition artifact:

```bash
UACP_ROOT=/path/to/uacp python3 -c "
import sys
sys.path.insert(0, 'runtime-adapters/hermes/plugins')
from uacp_guardian.kernel import Heartgate
hg = Heartgate.load('/path/to/uacp')
result = hg.validate_transition_file('/path/to/transition.yaml')
print(result)
"
```

## Git workflow

UACP is versioned at `nortrix-labs/uacp` (GitHub). Local working tree at `UACP_ROOT`.

```bash
# Always commit through standard git (UACP enforces commit-boundary policy via
# config/version-control.yaml — see lifecycle-reference.md for the SOP).
git status
git diff --stat HEAD
git log --oneline -10

# Push to remote (origin/main only).
git push origin main
```

## What NOT to do

- Do NOT use `cat <<EOF > file` or `echo >> file` to mutate UACP state directories. Use the governed writers (`uacp_state_write`, `uacp_gate_ledger_append`, `uacp_run_registry_update`, `uacp_escalation_event`).
- Do NOT bypass Guardian by setting `filesystem_guard_verified=true` in shell scripts. The flag is verified by Guardian's policy, not trusted from the caller.
- Do NOT modify `state/current.yaml` by hand once the run pointer is set. Use `uacp_state_write` with the caller-bound active_run_id.
- Do NOT use `--no-verify` to skip pre-commit hooks.

## See also

- [PROJECT.md](PROJECT.md) — project identity.
- [ROADMAP.md](ROADMAP.md) — Phase 5 backlog.
- [CONTRIBUTING.md](CONTRIBUTING.md) — authoring contract.
- [`docs/INDEX.md`](docs/INDEX.md) — full doc navigation.
