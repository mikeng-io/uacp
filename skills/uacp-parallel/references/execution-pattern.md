# Execution Pattern

For each wave, spawn tasks in parallel:

```yaml
for each wave in execution_plan:
  # Spawn all tasks in wave concurrently
  results = []

  for task_id in wave:
    task = graph[task_id]['task']

    # Use Task tool to spawn agent
    agent_type = task.agent or "general-purpose"
    capability = task.capability or "high"

    spawn_agent(
      subagent_type: agent_type,
      description: task.description,
      prompt: task.prompt,
      capability: capability
    )

  # Wait for all tasks in wave to complete
  wait_for_completion(wave)

  # Check for failures
  failed_tasks = [t for t in wave if task_failed(t)]

  if failed_tasks:
    handle_failures(failed_tasks, graph)
```

## Visual Pattern

```
Wave 1:  [Task A] [Task B] [Task C]  ← All run concurrently
            ↓        ↓        ↓
         Wait for all to complete
            ↓
Wave 2:    [Task D] [Task E]          ← Both run concurrently
              ↓        ↓
         Wait for all to complete
            ↓
Wave 3:      [Task F]                 ← Runs alone
```
