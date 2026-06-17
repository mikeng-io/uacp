Shared/kernel operational reference docs for the UACP skill tree. Per the reference-document policy (skills/uacp-skills), every doc here is cited by ≥1 skill and listed below; extend an existing doc before creating a new one.

This is the OKF bundle index for the `skills/uacp-core/references/` directory. Each document carries YAML frontmatter conforming to the Open Knowledge Format convention (type, title, description, tags, timestamp). The index itself is exempt from frontmatter.

| Reference | Purpose | Cited by |
|---|---|---|
| [adaptive-package-backfill-pattern.md](adaptive-package-backfill-pattern.md) | Procedure for reconstructing missing human-readable PROPOSE/PLAN packages when a run has only YAML lifecycle envelopes | uacp |
| [adaptive-package-gate-commit-pattern.md](adaptive-package-gate-commit-pattern.md) | How to settle a large UACP working tree after governed design/runtime work by committing with a durable explanation surface | uacp |
| [agent-council-followthrough.md](agent-council-followthrough.md) | Execution procedure every lifecycle skill must follow when a council or gate review reports blockers, failures, or material warnings | uacp-execute, uacp-plan, uacp-propose, uacp-resolve, uacp-state, uacp-triage, uacp-verify |
| [architecture-packet-uacp-compatibility.md](architecture-packet-uacp-compatibility.md) | How to classify existing architecture/design packets and decide whether they need full UACP lifecycle machinery | uacp |
| [external-audit-runtime-gate-remediation.md](external-audit-runtime-gate-remediation.md) | Pattern for closing external auditor findings when docs/config pass but runtime enforcement is incomplete | uacp |
| [full-lineage-audit-and-remediation-lessons.md](full-lineage-audit-and-remediation-lessons.md) | Rules for auditing the full change lineage across multiple commits or phases rather than only the latest commit | uacp |
| [goal-driven-track.md](goal-driven-track.md) | Shipped kernel-contract mirror for the goal-driven lifecycle track (ADR-0016); read when operating a run with `track: goal-driven` | uacp-execute, uacp-plan, uacp-propose, uacp-resolve, uacp-skills, uacp-verify |
| [kimi-codex-agent-council-audit-loop.md](kimi-codex-agent-council-audit-loop.md) | Procedure for dispatching Kimi + Codex as an Agent Council audit loop for UACP runtime-gate remediation | uacp |
| [lexa-first-principles-review-sliced-continuation.md](lexa-first-principles-review-sliced-continuation.md) | Pattern for continuing a LEXA first-principles documentation review under UACP discipline after an authority reset | uacp |
| [lifecycle-semantic-gates.md](lifecycle-semantic-gates.md) | Authoritative reference for hardening UACP lifecycle phase gates and auditing whether a phase is genuinely complete | uacp-resolve, uacp-verify, uacp |
| [operator-phase-return-presentation.md](operator-phase-return-presentation.md) | Rule for separating evidence layer from operator summary layer in phase returns to human control channels | uacp |
| [council-taxonomy.md](council-taxonomy.md) | Canonical Agent-Council vocabulary — modes, tiers, roles, and dispatch surfaces that lifecycle/orchestration skills must use | uacp-council, uacp-debate, uacp-context, uacp-parallel, uacp-brainstorm |
| [semantic-package-and-operator-return-lessons.md](semantic-package-and-operator-return-lessons.md) | Lessons for work touching adaptive packages, Markdown semantic substrate, validator gates, and operator-channel returns | uacp |
