Shared/kernel operational reference docs for the UACP skill tree. Per the reference-document policy (skills/uacp-skills), every doc here is cited by ≥1 skill and listed below; extend an existing doc before creating a new one.

This is the OKF bundle index for the `skills/uacp-core/references/` directory. Each document carries YAML frontmatter conforming to the Open Knowledge Format convention (type, title, description, tags, timestamp). The index itself is exempt from frontmatter.

This directory holds exactly the five canonical skill-citable contracts below, plus a `domains/` subdirectory (the domain registry — domain definitions and the Lookup Protocol, read by `uacp-bridge`, `uacp-context`, `uacp-council`, and `uacp-debate`; see the README inside `domains/`). Durable run-lessons, design rationale, and history live in the single knowledge corpus at `.uacp/knowledge/`, not here.

| Reference | Purpose | Cited by |
|---|---|---|
| [agent-council-followthrough.md](agent-council-followthrough.md) | Execution procedure every lifecycle skill must follow when a council or gate review reports blockers, failures, or material warnings | uacp-execute, uacp-plan, uacp-propose, uacp-resolve, uacp-state, uacp-triage, uacp-verify |
| [council-taxonomy.md](council-taxonomy.md) | Canonical Agent-Council vocabulary — modes, tiers, roles, and dispatch surfaces that lifecycle/orchestration skills must use | uacp-council, uacp-debate, uacp-context, uacp-parallel, uacp-brainstorm |
| [goal-driven-track.md](goal-driven-track.md) | Shipped kernel-contract mirror for the goal-driven lifecycle track (ADR-0016); read when operating a run with `track: goal-driven` | uacp-execute, uacp-plan, uacp-propose, uacp-resolve, uacp-skills, uacp-verify |
| [lifecycle-semantic-gates.md](lifecycle-semantic-gates.md) | Authoritative reference for hardening UACP lifecycle phase gates and auditing whether a phase is genuinely complete | uacp-resolve, uacp-verify, uacp |
| [operator-phase-return-presentation.md](operator-phase-return-presentation.md) | Rule for separating evidence layer from operator summary layer in phase returns to human control channels | uacp |
