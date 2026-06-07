# UACP Containment Design Direction — 2026-05-14

## Context
Session reviewed current UACP containment posture after Phase 2 governed writers and Phase 3 Heartgate tool were verified. Goal: propose the safest next containment design direction for enabling UACP-bound shell/code execution.

## Current Verified State
- Live symlink bindings: `uacp_guardian` and `thread_title_sync` active under `HERMES_ROOT/plugins/`
- Guardian `pre_tool_call` / `post_tool_call` hooks registered and enforcing
- Governed canonical writers (`uacp_doc_write`, `uacp_config_write`) path-hardened and YAML-validated
- Heartgate transition check (`uacp_heartgate_check`) live and blocking invalid transitions
- **Fail-closed shell/code blocker verified**: UACP-bound `exec.shell` and `exec.code_with_tool_proxy` block when `filesystem_guard_verified=False`
- Fresh session tool schema reload verified: all 5 UACP tools visible in new Hermes session
- Duplicate Hermes Agent plugin source removed

## Open Blockers (from `..outputs/uacp-operational-dashboard.yaml`)
| ID | Severity | Summary |
|---|---|---|
| filesystem-containment | **high** | UACP-bound shell/code execution remains blocked until verified containment exists |
| kanban-guardian-evidence | medium | UACP-bound Kanban worker completion needs reliable Guardian evidence propagation |
| runtime-adapter-contract | medium | Cross-runtime adapter contract not yet stabilized |

## Boundary Correction Before Design

Do not frame containment as UACP preventing every possible user-side mutation. Manual edits in VS Code, direct config changes, symlink replacement, and external runtimes without UACP integration are outside the governed runtime boundary. They are treated as out-of-band changes requiring revalidation before trust.

Containment is a host/runtime property. UACP declares the required posture; Guardian verifies runtime-provided evidence; the host/runtime supplies the actual isolation. If that evidence is absent, protected shell/code remains fail-closed.

See `runtime-trust-boundary-correction-20260514.md` for the session correction and operator preference.

## Minimal-Delta Containment Design

### Goal
Allow UACP-bound `terminal` and `execute_code` **only when** the runtime can prove the execution surface cannot reach protected UACP paths.

### Approach: Read-Only Bind Mount + Sandbox Working Directory
Satisfies `config/guardian-policy.yaml` accepted mechanisms:
- `filesystem_sandbox`
- `readonly_mount_for_protected_paths`
- `tool_runtime_write_guard`

### Implementation Steps
1. **Containment helper in Guardian adapter**  
   Add `verify_filesystem_containment(workspace: str) -> bool` in `uacp_guardian/__init__.py`:
   - Resolve workspace path
   - Verify `UACP_ROOT` is **not** a parent of workspace (or is mounted read-only)
   - Return `True` only if workspace is outside `UACP_ROOT` or `UACP_ROOT` is read-only

2. **`uacp_sandbox_check` tool (optional but recommended)**  
   Expose lightweight tool returning containment status for VERIFY evidence.

3. **Modify `pre_tool_call` hook**  
   For `terminal` / `execute_code`:
   - If `event.filesystem_guard_verified=True`, allow with audit
   - Else run containment check (step 1)
   - If contained, set `filesystem_guard_verified=True` and allow with audit
   - If not contained, **block** (preserve current fail-closed)

4. **Hermes `execute_code` sandbox integration**  
   Verify sandbox working directory is outside `UACP_ROOT`, or `UACP_ROOT` is read-only inside sandbox.

5. **No neutral kernel changes needed**  
   `kernel.py` already checks `event.filesystem_guard_verified`. Adapter only needs to set it correctly.

## Why This Is Minimal-Delta
- No new policy categories needed (`exec.shell`, `exec.code_with_tool_proxy` already exist)
- No new decision values needed (`allow_with_audit` vs `block` already cover it)
- No Heartgate changes needed
- No Kanban changes needed for this phase
- No upstream Hermes Agent patches needed

## Must-Fix Gaps Before Implementation
| Gap | Risk | Fix |
|---|---|---|
| Guardian `pre_tool_call` does not inspect actual filesystem mount state | Malicious workspace path bypass | Implement `verify_filesystem_containment()` using `os.path.ismount()`, `statvfs()`, or read-only bind mount check |
| No evidence artifact for containment verification | VERIFY cannot prove containment | Add `uacp_sandbox_check` tool or record containment status in audit log |
| Hermes `execute_code` sandbox may share host filesystem | Illusory containment | Verify sandbox backend; require read-only bind mount if host FS is shared |
| Breakglass path could disable containment | Global disable without scope | Ensure breakglass records include `affected_scope` and `expiry`; block global disable |

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Symlink traversal bypasses containment | Low | High | Use `Path.resolve()` and check against `UACP_ROOT` |
| Hermes sandbox backend changes | Medium | Medium | Pin containment check to sandbox working directory; add live probe test |
| Operator runs shell without containment | Low | High | Keep `fail_closed_if_unavailable: true`; require explicit `filesystem_guard_verified=True` |
| Nested mounts not read-only | Low | Medium | Check `statvfs` `ST_RDONLY` on `UACP_ROOT` and all parent mounts |

## Concrete Next Steps
1. Design review — focused Agent Council on containment approach
2. Implement `verify_filesystem_containment()` in adapter
3. Add `uacp_sandbox_check` tool to manifest
4. Update live probe (`scripts/live_guardian_probe.py`) to test allowed/blocked shell scenarios
5. Record verification artifact under `verification/`
6. Update `..outputs/uacp-current-status.yaml`

## Authority
- `docs/runtime-enforcement.md` — runtime enforcement design
- `config/guardian-policy.yaml` — policy seed (lines 295–308)
- `verification/containment-fail-closed-20260514.yaml` — fail-closed proof
- `..outputs/uacp-operational-dashboard.yaml` — open blockers
