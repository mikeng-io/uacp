# Tool and Runtime Selection

## Main session
Owns orchestration, patch application, deterministic verification, and final synthesis.

## delegate_task
Use for Agent Council review/audit only. Do not let subagents mutate artifacts.

## File/patch tools
Use targeted patch edits for code/config/skill changes after reading target surfaces.

## Terminal
Use for validator runs, AST/syntax checks, and local Heartgate dry-runs. Avoid unmanaged background processes.

## UACP tools
Use `uacp_artifact_write`, `uacp_gate_ledger_append`, and `uacp_heartgate_check` for governed artifacts/ledger/transition checks where possible.

## Runtime reload caveat
Kernel source patches do not prove the long-lived Hermes plugin has reloaded. VERIFY must state source-level vs live-runtime status separately.
