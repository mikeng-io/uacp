# Failure Handling

When a task fails, decide what to do with dependent tasks.

## Strategy 1: Skip Dependent Tasks (Default)

```yaml
if task fails:
  mark_failed(task_id)

  # Skip all tasks that depend on this one
  for dependent_id in compute_all_dependents(task_id):
    mark_skipped(dependent_id, reason: "dependency {task_id} failed")
```

## Strategy 2: Continue with Partial Results (Optional)

```yaml
if task fails:
  mark_failed(task_id)

  # Still execute dependent tasks, but with warning
  for dependent_id in dependents:
    add_warning(dependent_id, "Upstream task {task_id} failed")
    # Let task decide how to handle missing input
```

## Failure Report

```markdown
## Execution Summary

**Status:** PARTIAL_FAILURE

**Completed:** 7/10 tasks
**Failed:** 1/10 tasks
**Skipped:** 2/10 tasks (due to dependency failures)

### Failed Tasks

❌ **task-3** (Wave 2)
- Error: "API endpoint not responding"
- Impact: Skipped task-7, task-9 (depend on task-3)

### Skipped Tasks

⏭️ **task-7** - Skipped because task-3 failed
⏭️ **task-9** - Skipped because task-3 failed
```
