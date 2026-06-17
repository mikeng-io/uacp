# Agent Council Follow-Through Procedure

Use this reference from every UACP lifecycle skill when a council, Heartgate Council, evidence cluster, invariant check, or transition review reports blockers, concerns, invariant failures, negative findings, or material warnings.

This is an execution procedure, not doctrine prose. The phase skill must either complete these steps or stop before phase progression.

## Trigger matrix

Run this procedure when any condition is true:

- Council verdict is `CONCERNS` or `FAIL`.
- Any finding has classification `blocker`, `concern`, `invariant_failure`, `negative_finding`, or `material_warning`.
- A non-waivable invariant is not `pass`.
- A warning/deferred item would cross a phase boundary.
- Work touches Agent Council, Heartgate, Guardian, lifecycle semantics, artifact schema, runtime enforcement, protected state, profile/public boundaries, or UACP skills.
- The operator asks for council review or autonomous council looping.

## Execution loop

1. **Load authority**: read `UACP_ROOT/skills/uacp-core/references/agent-council-followthrough.md` (this file), `UACP_ROOT/config/review-routing.yaml`, and `UACP_ROOT/config/phase-transitions.yaml` as needed for the phase.
2. **Select council**: choose mode, tier, roles, and dispatch surface from phase-local granularity/risk. For governance/runtime/artifact claims, make it retrieval-led.
3. **Dispatch roles**: at minimum use Primary Reviewer, Devil's Advocate, and Integration Checker for governance-core changes. Add domain experts when the plan or routing config requires them.
4. **Require ground truth**: prompts must name concrete files, configs, scripts, commands, or artifacts to inspect. Summary-only council output cannot prove correctness.
5. **Write synthesis**: save `kind: uacp.council_synthesis` under `verification/` with `inspected_paths`, roles, verdict, findings, and evidence paths/lines.
6. **Extract findings**: list all blockers, concerns, invariant failures, negative findings, and material warnings. Assign `original_finding_id`, `original_artifact_path`, severity/classification, owner, and required handling.
7. **Classify handling**: `remediated`, `expanded`, `justified`, `deferred`, `accepted_warning`, or `rejected_with_reason`.
8. **Follow-up council**: for `remediated`, `expanded`, or `justified` material findings, run one focused follow-up council unless a Heartgate-visible accepted exception artifact explains why not. The follow-up must inspect the handling artifact and affected transition evidence.
9. **Cap recursion**: record `followup_depth`. Default maximum is `1`. If a follow-up council creates another blocker/material concern, block or escalate; do not spawn unbounded councils.
10. **Build transition evidence**: encode `handled_findings_chain` in the transition artifact with handling artifact, follow-up artifact when required, owner, residual risk, next-phase obligation, `followup_depth`, and Heartgate validation status.
11. **Run Heartgate**: call `uacp_heartgate_check` on the transition artifact after follow-through evidence is present. Agent Council synthesis is evidence, not approval.
12. **Gate decision**: proceed only if Heartgate returns pass/warn without blockers and every material council finding is handled. Otherwise stop, patch, rerun focused council, and retry once.

## Handling matrix

- `blocker` or `invariant_failure` + `remediated|expanded|justified`: handling artifact + follow-up council required.
- `concern|negative_finding|material_warning` + `remediated|expanded|justified`: follow-up council required when it touches phase boundary, Guardian/Heartgate semantics, runtime enforcement, protected state, artifact schema, or next-phase assumptions.
- `deferred|accepted_warning|rejected_with_reason`: require owner, residual risk, next-phase obligation, and accepted exception/authority artifact when applicable.
- Any non-waivable invariant cannot be downgraded to warning by council alone; Heartgate must block or an explicit authority artifact must re-scope the invariant.

## Refusal conditions

A lifecycle skill must refuse next-phase adoption or RESOLVE when any is true:

- A material council finding has no handling classification.
- A handled finding lacks `handling_artifact_path`.
- Required follow-up council is missing.
- `followup_depth` exceeds the configured cap.
- Deferred/warning/rejected handling lacks owner, residual risk, or next-phase obligation.
- Transition lacks Heartgate coherence when required by policy.
- Heartgate blocks or Guardian blocks a protected action.

## Artifact fields

Transition artifacts that carry handled findings should include:

```yaml
source_negative_findings_present: true
handled_findings_chain:
  - original_finding_id: AC-001
    original_artifact_path: verification/example-council.yaml
    finding_classification: blocker
    handling_classification: remediated
    handling_artifact_path: executions/example-fix.yaml
    followup_required: true
    followup_council_synthesis_artifact: verification/example-followup-council.yaml
    followup_depth: 1
    accepted_exception_artifact: null
    owner: norty
    residual_risk: none
    next_phase_obligation: none
    heartgate_validation: pass
```

Council synthesis artifacts should include:

```yaml
kind: uacp.council_synthesis
verdict: PASS|CONCERNS|FAIL
phase: verify
mode: review
roles: [Primary Reviewer, Devil's Advocate, Integration Checker]
inspected_paths: []
findings: []
followup_depth: 0
rerun_of_findings: []
```

---

## Council invocation declaration schema

A council invocation must declare before dispatch:

- **mode**: one of the canonical modes listed below.
- **tier**: one of the canonical tiers listed below.
- **phase-local granularity and local risk basis**: the estimate driving this invocation's depth.
- **roles and diversity dimensions selected**: named roles from the roster; diversity dimensions should include domain, runtime, model/toolchain, artifact type, stakeholder perspective, risk class, and temporal horizon as applicable.
- **dispatch surfaces allowed**: `delegate_task`, Hermes Kanban workers, external coding agents, browser/computer-use automation, web extraction/search services, or other approved adapters.
- **tool/evidence adapter allowlist and side-effect boundaries**.
- **expected output artifact and finding format**: council outputs must be structured findings, not prose opinions, when the invocation is review, audit, verify, or research mode.
- **retrieval obligations**: when the council validates governance, runtime, artifact-management, Guardian/Heartgate, lifecycle, or security-sensitive claims, the prompt must name the concrete files, directories, commands, or evidence artifacts to inspect. The synthesis artifact must record `inspected_paths`.

## Canonical council modes

Council mode describes what the council is doing in a specific invocation. Declare mode explicitly; do not leave it implicit.

- `plan`: decompose strategy, execution topology, scope, dependencies, and rollback.
- `propose`: challenge authority, scope, side effects, non-goals, and viability.
- `execute`: coordinate or support bounded workers while preserving traceability.
- `verify`: validate completed artifacts against selected evidence clusters.
- `audit`: search for compliance, security, privacy, governance, or process failures.
- `review`: critique an artifact or proposal for quality and risk.
- `research`: gather and synthesize grounded information.
- `brainstorm_design`: generate alternatives before narrowing.
- `resolve`: extract lessons, residual risk, memory/skill decisions, and closure notes.

A single UACP run may invoke different council modes in different phases. Review is only one mode; implementation orchestration is also canonical. Do not collapse all invocations into `review`.

## Canonical council tiers

Council tier describes orchestration depth for one council invocation. Select adaptively from phase-local risk.

- `tier_0_single`: main orchestrator only; no council fan-out. Allowed only when no phase boundary depends on multi-perspective validation.
- `tier_1_bounded`: one to three bounded delegates or Kanban workers with narrow scope.
- `tier_2_role_diverse`: role-diverse agents covering material dimensions (architecture, safety, operations, domain fit, verification). Use at minimum a Primary Reviewer, Devil's Advocate, and Integration Checker for governance-core changes.
- `tier_3_cross_runtime`: runtime-diverse or model-diverse council; requires stronger provenance and completion evidence. Reserved for cases where independent runtime/tool perspectives materially improve confidence.
- `tier_4_deep_council`: council-of-councils or multi-stage adversarial protocol; requires explicit operator-visible rationale unless already approved in PLAN.

Higher tiers are justified by risk, ambiguity, domain/runtime diversity, verification difficulty, or irreversible side effects — not by habit.

## Retrieval-led council rule

A council that reviews governance, runtime, artifact-management, Guardian/Heartgate, lifecycle, or security-sensitive claims must inspect ground-truth artifacts directly.

- The council prompt must name the concrete files, directories, commands, or evidence artifacts to inspect.
- The synthesis artifact must record `inspected_paths` and file/path evidence for material findings.
- A summary-only council may brainstorm or critique framing, but must not be used to claim runtime/governance correctness.

## Finding schema

For review, audit, verification, and research modes, councils must produce structured findings rather than only prose opinions.

Each finding must include:

```yaml
id: "AC-NNN"
severity: critical | high | medium | low | info
summary: "one-sentence description"
evidence: "file:line or command/output reference"
affected_artifact: "path/to/artifact"
recommended_action: "concrete next step"
owner: "role or person"
state: open | resolved | accepted_risk | not_applicable | deferred
```

**Blocker**: phase transition is blocked until the issue is patched, explicitly rescoped, or rejected with human authority.

**Concern**: must be patched, accepted as residual risk, or deferred with owner, acceptance, and condition.

**rerun_required: true**: when the finding touches a boundary the next phase depends on (Guardian writer containment, Heartgate transition truthfulness, council artifact schema, runtime tool exposure, protected state mutation). A council rerun is not ceremony; it is required when the previous council found a blocker or boundary-touching concern and later work claims that finding is resolved.

## Pre-invocation setup

Before dispatching a council invocation, the lifecycle skill must:

1. **Load routing authority** — read `UACP_ROOT/config/review-routing.yaml` and `UACP_ROOT/config/phase-transitions.yaml` to determine default council tier for the current phase and risk level.
2. **Declare mode, tier, and roles** before issuing any dispatch. Do not dispatch and then classify after the fact.
3. **State retrieval obligations explicitly** — if the invocation covers governance, runtime, Guardian/Heartgate, artifact schema, or lifecycle claims, list the files/paths the council must inspect. If those paths are unknown, the first council role must retrieve and declare them.
4. **Record dispatch metadata** in the council synthesis artifact: mode, tier, roles, dispatch surfaces, retrieval obligations, and expected artifact path.

## Mid-phase escalation rule

If phase-local granularity rises mid-phase (new side effects discovered, findings reveal higher risk, protected action encountered):

- If no protected action is in flight, apply the higher council tier to pending work units immediately.
- If a protected action is in flight and the new tier would require stronger review, pause before the next irreversible or externally visible side effect and create a re-plan or checkpoint artifact.
- If escalation is caused by a HIGH/CRITICAL finding, block phase exit until the finding is resolved, accepted by the correct authority, or moved into a documented re-plan.

This rule applies to all lifecycle phases. The follow-through loop above takes effect as soon as the escalation trigger fires.
