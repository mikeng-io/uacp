---
name: uacp-parallel
description: >
  Universal DAG-based task orchestration skill. Automatically determines optimal
  parallel execution order while respecting task dependencies. Can run standalone
  for any multi-step workflow or be invoked from UACP lifecycle phases when
  governed execution is needed.
location: managed
dependencies:
  - uacp-council-taxonomy
  - bridge-commons
allowed-tools:
  - Read
  - Write
  - Task
  - Bash(ls *)
---

# Parallel Workflow: DAG-Based Task Orchestration

Execute complex multi-step workflows with dependencies, maximizing parallelism while respecting execution order.

This skill is **universal** — it does not assume UACP lifecycle context. Use it for any parallelizable work: build pipelines, data processing, research tasks, verification suites, codebase exploration, or multi-agent dispatch. When invoked from a UACP phase, it composes naturally with the lifecycle without becoming hard-bound to it.

## When to Use This Skill

Use this skill when you need to run multiple tasks that have dependencies between them. The skill builds a DAG, validates it, computes execution waves via topological sort, executes each wave in parallel, and reports results.

Common use cases:

- **Codebase exploration** — map structure, then analyze technologies, then synthesize architecture
- **Multi-stage verification** — run independent security, performance, and accessibility checks, then integration synthesis
- **Build / CI pipelines** — compile, test, lint, package in dependency order
- **Research synthesis** — gather sources in parallel, then synthesize conclusions
- **Council dispatch** — spawn multiple reviewers/experts concurrently when they have no interdependencies
- **Data processing** — ingest, transform, validate, and load in waves

## Input Contract

Accept a task list from the caller. Before parsing, Read `references/task-definitions.md` for the full field schema and example.

```yaml
tasks:
  - id: task-1
    description: "Description of what this task does"
    agent: "agent-name"  # Optional: specific agent type
    prompt: "Task-specific instructions"
    depends_on: []  # List of task IDs this depends on
```

## Orchestration Flow

1. **Read `references/task-definitions.md`** — validate task fields and defaults (`agent` defaults to `general-purpose`, `capability` defaults to `high`).
2. **Read `references/dag-validation.md`** — build the dependency graph, check that every `depends_on` reference exists, and detect cycles using DFS.
3. **Read `references/topological-sort.md`** — compute execution waves using Kahn's algorithm. All tasks with zero unsatisfied dependencies enter the same wave and run concurrently.
4. **Read `references/execution-pattern.md`** — spawn each wave in parallel with Task agents, wait for the wave to complete, and check results before advancing.
5. **Read `references/failure-handling.md`** — on failure, skip dependent tasks by default (or continue with warnings if configured), and emit a failure report showing impact.
6. **Read `references/report-format.md`** — emit progress updates during execution and a final execution report with timeline, task results, performance analysis, and recommendations.

## Output

Save execution report to `.outputs/workflow/`:

```
.outputs/workflow/
├── YYYYMMDD-HHMMSS-workflow-execution.md
└── YYYYMMDD-HHMMSS-workflow-execution.json
```

JSON format follows schema in `schemas/workflow-execution-schema.json`.

**No symlinks.** To find the latest artifact:
```bash
ls -t .outputs/workflow/ | head -1
```

## Additional References

- `references/advanced-features.md` — conditional dependencies, retry logic with exponential backoff, and per-task timeout control
- `references/scenarios.md` — codebase exploration, multi-stage verification, build pipeline, and council dispatch examples with expected execution plans
- `references/error-handling.md` — cycle detection, missing dependency, and empty wave error messages
- `references/best-practices.md` — minimize critical path, balance wave sizes, declare only necessary dependencies, and group related tasks

## Using uacp-parallel Within UACP

When this skill is invoked from a UACP lifecycle phase, it remains a generic orchestration primitive. The caller phase owns the governance context:

- **PROPOSE** may use parallel exploration to evaluate multiple design alternatives concurrently.
- **PLAN** may use parallel verification to check assumptions before committing to an execution graph.
- **EXECUTE** may use parallel dispatch for independent implementation tasks.
- **VERIFY** may use parallel checks for independent evidence clusters.
- **uacp-council** may use parallel dispatch internally to spawn domain experts + DA + IC in a single wave.

The parallel skill does not enforce UACP phase transitions, invariant checks, or state registration — those remain the responsibility of the caller phase and Guardian/Heartgate.

## Verification Checklist

Before finishing a parallel workflow run, confirm:
- [ ] All `depends_on` references resolve to existing task IDs
- [ ] DAG has no cycles
- [ ] Every task appears in exactly one wave
- [ ] Failed tasks triggered correct skip/continue behavior
- [ ] JSON report conforms to `schemas/workflow-execution-schema.json`
- [ ] Markdown report includes execution timeline and performance analysis

## Notes

- Parallelization speedup is limited by critical path length.
- Wave count equals the length of the longest dependency chain.
- Max parallelism equals the size of the largest wave.
- Cycle detection is O(V + E) using DFS.
- Topological sort is O(V + E) using Kahn's algorithm.
- Failure handling can be configured per-workflow.
- Always validate the DAG before spawning any Task agents to avoid wasted work.
