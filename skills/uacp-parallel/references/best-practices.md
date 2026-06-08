# Best Practices

## 1. Minimize Critical Path

The critical path is the longest dependency chain. Minimize it:

```yaml
# ❌ Bad: Long critical path
task-1 → task-2 → task-3 → task-4 → task-5  (5 waves)

# ✅ Good: Shorter critical path
Wave 1: [task-1]
Wave 2: [task-2, task-3, task-4]  # Parallel
Wave 3: [task-5]                   (3 waves)
```

## 2. Balance Wave Sizes

Avoid waves with very different task counts:

```yaml
# ⚠️ Suboptimal: Unbalanced waves
Wave 1: [task-1]                    # 1 task
Wave 2: [task-2, task-3, ..., task-10]  # 9 tasks
Wave 3: [task-11]                   # 1 task

# ✅ Better: Balanced waves
Wave 1: [task-1, task-2, task-3]    # 3 tasks
Wave 2: [task-4, task-5, task-6]    # 3 tasks
Wave 3: [task-7, task-8]            # 2 tasks
```

## 3. Declare Only Necessary Dependencies

Don't over-constrain:

```yaml
# ❌ Bad: Unnecessary dependencies
- id: task-C
  depends_on: [task-A, task-B]  # If task-C only needs task-A

# ✅ Good: Minimal dependencies
- id: task-C
  depends_on: [task-A]  # Only declare what's actually needed
```

## 4. Group Related Tasks

Keep related tasks in same wave when possible:

```yaml
# ✅ Good: Related analysis grouped
Wave 1:
  - security-analysis
  - accessibility-analysis
  - performance-analysis

Wave 2:
  - integration-check  # Uses all Wave 1 results
```
