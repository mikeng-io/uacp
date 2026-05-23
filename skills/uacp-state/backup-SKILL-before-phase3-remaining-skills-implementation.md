---
name: uacp-state
description: Use when mutating UACP state, updating run manifests, current pointers, or tombstones.
---

# UACP State

## Purpose
This skill owns governed state mutation. Use it whenever the current run pointer, run manifest, bootstrap flag, or state-backed reference must change.

## Read first
- `UACP_ROOT/docs/index.md`
- `UACP_ROOT/docs/constitution.md`
- `UACP_ROOT/docs/lifecycle-reference.md`
- `UACP_ROOT/config/state.yaml`
- `UACP_ROOT/config/roots.yaml`
- `references/state-mutation-protocol.md`

## Rules
- Do not edit state files directly unless this skill is the active path.
- Do not change canonical docs from a state mutation step.
- Keep mutations narrow and traceable.
- Update only the state artifacts the run actually owns.
- Use tombstones for deleted legacy notes when needed.
- Support two modes:
  - `bootstrap_direct_edit` while the bootstrap boundary is still open.
  - `uacp_state_required` after bootstrap closes and governed mutation becomes mandatory.
- If the current mode is bootstrap, mutate only the current run's UACP artifacts and record provenance.
- If the current mode is governed, require state ownership and traceability for every mutation.
- Preserve `UACP_ROOT`-relative or symbolic paths in all written state.
- Record provenance in `state_history` for every non-trivial mutation.
- Never mutate canonical docs or config from this skill.

## Typical outputs
- `state/current.yaml`
- `state/runs/<run>.yaml`
- `state/runs/<run>-transition.yaml`

## Pitfalls

### Guardian blocks direct or under-context UACP state writes
When `governed_mutation_active: true` in `config/state.yaml`, UACP state mutation is supposed to route through the guarded state mutation path, not ordinary file edits. Direct state writes may be blocked with errors such as:
```
UACP Guardian blocked state.uacp: direct UACP state writes must use uacp_state_write
UACP Guardian blocked exec.shell: missing UACP context fields: uacp_run_id, uacp_phase, policy_version, declared_authority, declared_side_effects
UACP Guardian blocked external.unknown_mutator: policy default blocks UACP-bound action
```

**Preferred path:** use the runtime-provided `uacp_state_write`/guarded state mutation surface when available and ensure the mutation carries run id, phase, policy version, authority, declared side effects, and workspace policy.

**Doc/config writer surface:** `uacp_artifact_write` may intentionally refuse `docs/`, `config/`, and `state/` targets while `uacp_state_write` only permits `state/`. For canonical docs/config sync, prefer dedicated governed writers when available: `uacp_doc_write` for `docs/*.md` and `uacp_config_write` for `config/*.{yaml,yml}` with full UACP context and path/YAML validation. If the running session has not reloaded and cannot see newly registered writer tools yet, record the schema/reload gap in verification and keep any authorized direct mutation narrow and transitional; do not normalize direct edits as the steady-state path.

**Transition boundary:** if the current state mutation implies a phase move, validate the transition artifact with `uacp_heartgate_check` before updating current pointers or run manifests. Heartgate is the phase-transition boundary; `uacp_state_write` is only the state mutator.

**Schema discipline:** Heartgate transition files are strict. When a transition check blocks on missing fields, reuse a prior accepted transition artifact as the schema template and include the full required transition payload (`decision`, `invariant_summary`, `cluster_summary`, `deferred_items`, `authority`, `phase_local_granularity`, `composite_granularity`, `human_involvement`) before retrying. Keep `invariant_summary` and `cluster_summary` as lists of maps (`[{id/status/evidence}]`, `[{cluster_id/state/evidence}]`), not single maps or strings; the live Heartgate validator iterates them and malformed shapes may throw an attribute error before normal blocker reporting. Include explicit `blockers: []` and top-level `artifact_paths: [...]` when the policy expects them. Keep enum-like fields conservative: if council findings are accepted but non-blocking, record invariant/cluster state as `pass` and move the concern detail into `warnings` plus `deferred_items`; avoid ad-hoc values such as `pass_with_concerns` unless the live transition config explicitly permits them. When Heartgate Council/transition coherence is used, add `heartgate_coherence` with status, artifact path, and all required coherence lenses; reference a `verification/` artifact rather than embedding a long council transcript in state. Quote YAML scalar strings containing colon-space text (for example `summary: "Warnings are explicit: ..."`) so governed writer parsing succeeds before Heartgate runs.

**Contained-shell boundary:** `uacp_contained_shell` is not a substitute for `uacp_state_write` or artifact/doc/config writers. It should run in a separate execution workspace while `UACP_ROOT` stays read-only; attempts to use `UACP_ROOT` as the execution workspace may correctly fail containment checks. For UACP-root mutation, keep using the governed writer for the relevant path class.

**Manual-drill fallback:** if the guarded state mutation surface is unavailable in the current tool environment and the operator has authorized a local reversible drill, a narrow local write path may be used only to complete the drill artifact. Record it inside the produced execution/verification artifact as HIGH accepted risk or a blocker. Do **not** describe the bypass as normal enforcement, and do **not** use it as precedent for production activation.

Session-specific notes and example wording live in `references/manual-drill-state-mutation-risk.md`.

Reuse `references/heartgate-transition-schema-template.md` when a phase-transition artifact fails Heartgate for missing fields or schema drift.

### state-mutation-protocol.md may be missing
The skill references `references/state-mutation-protocol.md` but it may not exist in all installations. If the file is missing, use the rules in this SKILL.md as the authoritative protocol.

## Updated doctrine alignment

State artifacts and run manifests should preserve the updated lifecycle fields when present:

- phase-local granularity entry/exit/delta/projection,
- composite granularity,
- human involvement decision fields,
- council synthesis artifact references,
- Kanban task references as coordination memory only.

Never let Kanban status become UACP phase state. Never let a council artifact become authority until accepted by the relevant UACP transition.

Known Guardian bypass gaps must be recorded as HIGH accepted risk or blocker in verification artifacts, not normalized as routine state mutation.



## State-specific operating contract — UACP STATE

- **What this skill does:** mutate UACP runtime state, current pointers, manifests, and state records only through the governed state boundary.
- **Why it does it:** state is the lifecycle memory that later phases and Heartgate rely on; casual edits would make phase truth unverifiable.
- **How it does it:** load canonical state/path policy, verify the authority artifact, validate any transition with Heartgate before pointer movement, write bounded state records, and preserve provenance.
- **Constraints:** do not write docs/config/artifacts through the state boundary; do not move phase pointers when transition evidence is missing; do not repair artifacts by silently editing state.
- **Reason / rational intent / decisions:** intent is truthful lifecycle bookkeeping; decisions are whether state mutation is authorized, whether transition evidence is sufficient, and whether current pointers may move.
- **Tools to use / not use:** use `uacp_state_write`, `uacp_heartgate_check`, read/validator tools; avoid generic file mutation for protected state, docs/config writers, production tools, and external messaging.

This state-specific contract complements `references/agent-council-followthrough.md` when state movement consumes council or Heartgate findings.

## Agent Council follow-through wiring

When this phase invokes or consumes Agent Council output, execute `references/agent-council-followthrough.md` rather than treating council review as prose advice. In brief:

1. Select mode/tier/dispatch surface from UACP routing config and phase-local risk.
2. Dispatch retrieval-led roles when governance, runtime, artifact schema, Guardian/Heartgate, lifecycle, protected state, or skill behavior is involved.
3. Save `kind: uacp.council_synthesis` under `verification/` with `inspected_paths`, verdict, roles, findings, and evidence.
4. Extract all blockers, concerns, invariant failures, negative findings, and material warnings.
5. Do not advance the phase until every material finding is classified into the handled-findings matrix.
6. For `remediated`, `expanded`, or `justified` material findings, run one focused follow-up council unless a Heartgate-visible exception artifact is recorded.
7. Encode `handled_findings_chain`, `source_negative_findings_present`, and `followup_depth` in the transition artifact.
8. Run Heartgate after follow-through evidence exists; Agent Council synthesis is evidence, not transition approval.
9. Refuse next-phase adoption if the follow-through reference lists a refusal condition.
