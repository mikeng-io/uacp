# Report Format

## During Execution

Show progress in real-time:

```
Executing Wave 1/4 (3 tasks)...
  ✓ task-1 completed (2.3s)
  ✓ task-2 completed (1.8s)
  ✓ task-3 completed (3.1s)

Executing Wave 2/4 (2 tasks)...
  ✓ task-4 completed (1.2s)
  ✗ task-5 failed (error: timeout)

Skipping Wave 3 (1 task) - dependencies failed
  ⏭️ task-6 skipped (depends on task-5)

Executing Wave 4/4 (1 task)...
  ✓ task-7 completed (0.8s)

Total execution time: 8.2s
Parallelization achieved: 3.5x speedup
```

## Final Report

Generate comprehensive execution report:

```markdown
# Parallel Workflow Execution Report

**Status:** SUCCESS | PARTIAL_FAILURE | FAILED
**Total Tasks:** 10
**Completed:** 8
**Failed:** 1
**Skipped:** 1
**Execution Time:** 8.2 seconds
**Parallelization Factor:** 3.5x

## Execution Timeline

### Wave 1 (0.0s - 3.1s)
- ✓ task-1: "Analyze structure" (2.3s)
- ✓ task-2: "Identify technologies" (1.8s)
- ✓ task-3: "Map dependencies" (3.1s)

### Wave 2 (3.1s - 5.5s)
- ✓ task-4: "Analyze architecture" (1.2s)
- ✗ task-5: "Trace workflows" (FAILED: timeout after 2.4s)

### Wave 3 (skipped)
- ⏭️ task-6: "Synthesize findings" (depends on task-5)

### Wave 4 (5.5s - 8.2s)
- ✓ task-7: "Generate report" (2.7s)

## Task Results

### Completed Tasks (8)

**task-1:** Analyze structure
- Agent: Structure Explorer
- Duration: 2.3s
- Output: Found 45 files across 12 directories...

**task-2:** Identify technologies
- Agent: Technology Explorer
- Duration: 1.8s
- Output: Detected Python 3.11, FastAPI, PostgreSQL...

[... rest of completed tasks ...]

### Failed Tasks (1)

**task-5:** Trace workflows
- Agent: Workflow Explorer
- Duration: 2.4s (timeout)
- Error: "Request timeout after 2.4s"
- Impact: Caused task-6 to be skipped

### Skipped Tasks (1)

**task-6:** Synthesize findings
- Reason: Upstream dependency task-5 failed
- Would have depended on: task-5

## Performance Analysis

**Critical Path:** task-1 → task-4 → task-7 (6.2s)
**Total Work:** 28.5s (sum of all task durations)
**Actual Time:** 8.2s
**Speedup:** 3.5x
**Parallelization Efficiency:** 87%

## Recommendations

1. Investigate task-5 timeout - may need longer timeout or optimization
2. Consider splitting task-3 (longest in Wave 1) into subtasks
3. Wave 4 could potentially merge with Wave 3 if dependencies allow
```
