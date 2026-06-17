## Phase 8: Admission Check Before TRIAGE

Brainstorm is informal, but the boundary into TRIAGE is not. Before handing the scope package to TRIAGE, verify that it is coherent enough to enter UACP governance.

### Step 8.1: Guardian admission check

Guardian ensures the scope package contains the minimum fields required to enter TRIAGE. This is a transition-enforcement check, not a full lifecycle gate.

```bash
python3 skills/uacp-core/scripts/core.py check-preflight uacp-brainstorm \
  --scope-set true \
  --task-type planning \
  --mode brainstorm \
  --findings-count 0 \
  --domains-set {true if scope_package.signals.domains else false}
```

Guardian evaluates:
- `selected_scope.title` and `selected_scope.description` are non-empty
- `in_scope` is non-empty
- `declared_side_effects` is present (may be empty list)
- `authority.source` is documented
- `estimated_governance.routing_advisory` is valid

**Exit codes:**
- `0` (PASS) → proceed to Heartgate
- `1` (WARN) → record warnings, proceed if user accepts
- `2` (BLOCK) → return to Phase 5 to refine scope. Do NOT enter TRIAGE.

### Step 8.2: Heartgate coherence check (conditional)

Heartgate checks whether the proposed scope conflicts with existing UACP state. This is optional for brand-new work with no active runs. Run it when:

- An active UACP run exists in `state/current.yaml`
- The scope touches protected state, public/private boundaries, or shared infrastructure
- The user explicitly asks for coherence checking

```bash
python3 skills/uacp-core/scripts/core.py heartgate \
  --proposed-phase triage \
  --artifact-path .uacp/brainstorm/{session_id}/07-scope-package.yaml \
  --side-effects {declared_side_effects}
```

**Results:**
- `COHERENT` → proceed to TRIAGE
- `INCOHERENT` → surface findings to user; trim scope further or accept as recorded risk before entering TRIAGE

### 8.3 Record admission result in manifest.yaml

```yaml
admission:
  guardian_status: pass | warn | block
  guardian_findings: []
  heartgate_status: coherent | incoherent | skipped
  heartgate_findings: []
  final_decision: proceed_to_triage | stop | refine_scope
```

**Note:** Brainstorm artifacts themselves are NOT registered in `uacp-state`. Only official lifecycle artifacts (starting from TRIAGE) are state-persistent.
