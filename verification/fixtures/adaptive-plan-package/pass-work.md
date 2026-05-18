# Plan Semantic Fixture

Work breakdown: this fixture proves the PLAN package contains real execution topology, not only a YAML plan envelope.

Dependencies: the plan must name hard and soft dependencies so future agents know what must exist before execution.

Authority and side effects: the plan must identify who authorized execution and which side effects are allowed or forbidden.

Tool and runtime selection: the plan must explain why selected tools and runtime surfaces are appropriate.

Artifact write surfaces: the plan must name where evidence and runtime outputs are written.

Verification strategy: the plan must define checks, review conditions, and pass/block evidence.

Rollback recovery: the plan must explain how to undo or contain the work.

Council review topology: the plan must specify review roles when needed.

Transition readiness: the plan must state what allows PLAN to move to EXECUTE.
