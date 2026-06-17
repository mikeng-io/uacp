## Phase 1: Registration & Scope

This phase establishes the council manifest. It resolves what the council is allowed to do, what it is acting on, and whether Guardian is available to enforce the registration.

### Required dependencies

Verify required skills are present:

```
[skills-root]/uacp-core/references/council-taxonomy.md
[skills-root]/domain-registry/README.md
[skills-root]/uacp-bridge/SKILL.md
```

If a required file is missing, stop and emit an install advisory.

Guardian is optional but should be detected at one of these paths:

```
[skills-root]/uacp-core/scripts/core.py   # Guardian is implemented here
.guardian/guardian.py                      # runtime-local hook binding (if present)
```

For Tier 2+ dispatch, also verify runtime adapters:

```
[skills-root]/uacp-bridge/references/claude.md
[skills-root]/uacp-bridge/references/codex.md
[skills-root]/uacp-bridge/references/gemini.md
[skills-root]/uacp-bridge/references/opencode.md
[skills-root]/uacp-bridge/references/kimi.md
```

If only some *runtime adapters* are missing → log which are unavailable; Tier 2+ will dispatch only the ones present.

### Scope resolution

**Context classification (optional):**

If the `uacp-context` skill is available, invoke it:

```
Skill("uacp-context")
```

`uacp-context` classifies the artifact, detects domains from `domain-registry`, and assesses confidence. If `uacp-context` is not available, the caller must provide `working_scope` directly — see below.

**Conditionally invoke `uacp-preflight`** when context confidence is `low` OR `missing_signals` is non-empty. Preflight asks at most 3 targeted questions to fill exactly the gaps context could not resolve. If `uacp-preflight` is not available, proceed with caller-provided scope and mark `confidence: medium`.

Merge into `working_scope`:

```yaml
working_scope:
  artifact: ""           # what to analyze
  intent: ""             # review | audit | verify | research | implement | analysis | planning
  task_type: ""          # canonical uacp-bridge task_type
  mode: ""               # canonical council mode
  domains: []            # from context (authoritative), supplemented by preflight, or caller-provided
  constraints: []        # from preflight (empty if skipped)
  context_summary: ""    # combined description for agent prompts
  intensity: "standard"  # quick | standard | thorough — from routing signals + user request
```

### Council manifest

Build a single manifest before routing or dispatch:

```yaml
council_manifest:
  skill: uacp-council
  session_id: "council-{YYYYMMDD-HHmmss}"
  scope: ""                # from working_scope.artifact
  task_type: ""            # review | audit | research | analysis | planning | implementation
  mode: ""                 # review | audit | brainstorm | design | research | synthesis | finding-driven
  domains: []              # from working_scope.domains
  context_summary: ""      # from working_scope.context_summary
  intensity: ""            # quick | standard | thorough
  tier: null               # populated during routing
  ic_tier: null            # populated for finding-driven mode
  capability_profile: ""   # inspect | modify, derived from uacp-bridge
  guardian_enforced: false
  guardian_warnings: []
  registration_errors: []
```

Read `uacp-bridge/SKILL.md` for the canonical capability profile mapping. `task_type` controls authority: inspect tasks (`review`, `audit`, `research`, `analysis`, `planning`) must not modify project state; `implementation` may modify project state.

### Guardian registration enforcement

If Guardian is present, run registration checks against the manifest before selecting a tier or dispatching any agent:

```bash
python3 {guardian_path} check-preflight uacp-council \
  --scope-set true \
  --task-type {council_manifest.task_type} \
  --mode {council_manifest.mode} \
  --findings-count {len(findings) if council_manifest.mode == "finding-driven" else 0} \
  --domains-set {true if council_manifest.domains else false}

python3 {guardian_path} check-session-id {council_manifest.session_id}
```

If Guardian exits `2`, stop and surface the BLOCK message. Do not route, dispatch, or write an artifact. If session ID uniqueness fails, generate a new `session_id` and retry once; if the retry fails, stop.

If Guardian exits `1`, continue but record the warning in `guardian_warnings`. If Guardian is absent, continue and keep `guardian_enforced: false`.

The manifest is the shared registration object for the rest of the run. Runtime adapters receive a projection of it as `runtime_input`; output artifacts preserve it so Guardian can validate the completed registration.