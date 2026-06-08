# Task Definitions

Task definitions follow this structure:

```yaml
tasks:
  - id: task-1
    description: "Description of what this task does"
    agent: "agent-name"  # Optional: specific agent type
    prompt: "Task-specific instructions"
    depends_on: []  # List of task IDs this depends on

  - id: task-2
    description: "Another task"
    prompt: "Instructions"
    depends_on: [task-1]  # This task runs after task-1

  - id: task-3
    description: "Independent task"
    prompt: "Instructions"
    depends_on: []  # Runs in parallel with task-1
```

## Field Definitions

- `id` (required): Unique task identifier
- `description` (required): What this task does
- `prompt` (required): Instructions for the agent
- `depends_on` (required): Array of task IDs (empty array if no dependencies)
- `agent` (optional): Specific agent type to use (defaults to general-purpose)
- `capability` (optional): "highest", "high", "standard" (defaults to "high")
