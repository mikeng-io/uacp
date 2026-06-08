# Topological Sort: Compute Execution Waves

Use Kahn's algorithm to compute execution order:

```python
def compute_waves(graph):
    # Count incoming edges (dependencies)
    in_degree = {task_id: len(node['dependencies'])
                 for task_id, node in graph.items()}

    # Start with tasks that have no dependencies
    queue = [task_id for task_id, degree in in_degree.items()
             if degree == 0]

    waves = []

    while queue:
        # All tasks in queue can run in parallel (same wave)
        current_wave = queue[:]
        waves.append(current_wave)
        queue = []

        # Process each task in current wave
        for task_id in current_wave:
            # Reduce in-degree for dependent tasks
            for dependent_id in graph[task_id]['dependents']:
                in_degree[dependent_id] -= 1

                # If all dependencies satisfied, add to next wave
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

    return waves
```

## Output Example

```yaml
execution_plan:
  wave_1: [task-1, task-2, task-3]  # Run in parallel
  wave_2: [task-4, task-5]          # After wave 1 completes
  wave_3: [task-6]                  # After wave 2 completes
  wave_4: [task-7]                  # After wave 3 completes

estimated_time: "sum of longest path in DAG"
parallelization_factor: "3.2x" # tasks_total / waves_count
```
