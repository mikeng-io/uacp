# DAG Validation

## Build Dependency Graph

For each task, create node and edges:

```python
# Pseudocode
graph = {}
for task in tasks:
    graph[task.id] = {
        'task': task,
        'dependencies': task.depends_on,
        'dependents': []  # Will be computed
    }

# Compute reverse edges (dependents)
for task_id, node in graph.items():
    for dep_id in node['dependencies']:
        graph[dep_id]['dependents'].append(task_id)
```

## Validate DAG

### 1. Check all dependencies exist

```python
for task_id, node in graph.items():
    for dep_id in node['dependencies']:
        if dep_id not in graph:
            ERROR: "Task {task_id} depends on non-existent task {dep_id}"
```

### 2. Detect cycles

```python
def has_cycle(graph):
    visited = set()
    rec_stack = set()

    def visit(node_id):
        visited.add(node_id)
        rec_stack.add(node_id)

        for dep_id in graph[node_id]['dependencies']:
            if dep_id not in visited:
                if visit(dep_id):
                    return True
            elif dep_id in rec_stack:
                return True  # Cycle detected!

        rec_stack.remove(node_id)
        return False

    for node_id in graph:
        if node_id not in visited:
            if visit(node_id):
                return True
    return False
```

**If cycle detected:**
```
ERROR: Circular dependency detected!

Example cycle: task-3 → task-5 → task-7 → task-3

This creates an infinite loop. Please restructure dependencies.
```
