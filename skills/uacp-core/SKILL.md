---
name: uacp-core
description: >
  Runtime-neutral UACP core — policy, Guardian evaluation, Heartgate transitions,
  audit, and shared filesystem utilities. Imported by runtime adapters; not invoked
  directly as a skill.
kind: kernel
version: 1.0.0
metadata:
  hermes:
    tags: [uacp, core, guardian, heartgate, policy, audit]
    related_skills:
      - uacp-state
      - uacp-guardian
      - uacp-heartgate
---

# UACP Core

**Runtime-neutral core library.** This skill contains the agent-neutral policy
engine, Guardian per-call enforcement, Heartgate transition validation, audit
record writing, and shared filesystem utilities.

## Purpose

Runtime adapters (Hermes, Blockcode, Kimi, etc.) dynamically import modules from
`skills/uacp-core/scripts/` to enforce UACP policy without embedding business
logic in the adapter layer.

## Scripts

| Module | Responsibility |
|--------|---------------|
| `scripts/policy.py` | `GuardianPolicy` load, validate, config reading |
| `scripts/guardian.py` | `Guardian` per-call evaluation, `GuardianEvent`, `GuardianDecision` |
| `scripts/heartgate.py` | `Heartgate` transition validation, `HeartgateDecision` |
| `scripts/audit.py` | `write_audit_record()`, audit path resolution |
| `scripts/filesystem.py` | `resolve_uacp_path()`, `safe_write_file()`, `is_safe_run_id()` |

## Usage for runtime adapters

```python
import importlib.util
from pathlib import Path

uacp_root = Path(__file__).resolve().parents[5]  # up to UACP_ROOT
core_path = uacp_root / "skills" / "uacp-core" / "scripts"

# Dynamic import — no PYTHONPATH dependency
spec = importlib.util.spec_from_file_location(
    "uacp_core", core_path / "guardian.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

guardian = module.Guardian(policy, phase_config=...)
decision = guardian.evaluate(event)
```

## Canonical authority

- `config/uacp.toml` (`[guardian]` section — policy collapsed from legacy guardian-policy.yaml in Slice 3; `[heartgate.*]` — operator-tunable knobs)
- `scripts/engines/domain/phase_graph.py` — codified phase graph (`LIFECYCLE_GRAPH`, valid transitions)
- `scripts/engines/domain/phase_transitions.py` — codified stages grammar (`allowed_tools`, `forbidden_tools`, `phase_exit_invariants`)
- `scripts/engines/domain/gate_rules.py` — codified gate/rule grammar (heartgate_coherence, run_registry, plan_validation_gate, piv_rule)
- `config/phase-transitions.yaml` (LLM-read adaptive-gate doctrine + artifact schemas; grammar above is now code-authoritative)
- `docs/runtime/runtime-integration-guide.md`
