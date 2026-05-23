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

1. **Load authority**: read `UACP_ROOT/docs/index.md`, `docs/lifecycle-reference.md`, `docs/orchestration-model.md`, `config/review-routing.yaml`, and `config/phase-transitions.yaml` as needed for the phase.
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
