# Error Handling

## Cycle Detection Error

```
❌ ERROR: Circular dependency detected!

Dependency cycle found:
  task-A depends on task-B
  task-B depends on task-C
  task-C depends on task-A  ← Creates cycle!

This creates an infinite loop. Please restructure your dependencies.

Suggestion: Remove one of these dependencies to break the cycle.
```

## Missing Dependency Error

```
❌ ERROR: Invalid dependency reference!

Task "integration-check" depends on "domain-analysis"
But task "domain-analysis" does not exist.

Available tasks: [security-analysis, performance-analysis, integration-check]

Did you mean: "security-analysis"?
```

## Empty Wave Error

```
⚠️ WARNING: No tasks ready to execute!

All remaining tasks have unmet dependencies.
This usually indicates a cycle or missing task.

Remaining tasks: [task-7, task-9]
Waiting for: [task-3] which is blocked by [task-5]
```
