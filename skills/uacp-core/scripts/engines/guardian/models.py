"""Guardian data types and decision vocabulary.

Pure data (stdlib + dataclasses only): the decision constants, the immutable
``GuardianEvent`` input, the ``GuardianDecision`` result + its audit record, and
the policy error. Moved out of ``core.py`` (Phase A1, design/graph-engine node
31) and typed to the strict-engines bar (node 32 §0): no ``Any`` — heterogeneous
tool args are ``object`` (callers must narrow), the audit record is a TypedDict.
"""

from __future__ import annotations

import os
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TypedDict

DECISION_ALLOW = "allow"
DECISION_ALLOW_WITH_AUDIT = "allow_with_audit"
DECISION_REQUIRE_APPROVAL = "require_approval"
DECISION_BLOCK = "block"
DECISION_BLOCK_PENDING_HEARTGATE = "block_pending_heartgate"


class AuditRecord(TypedDict):
    """One JSON-serialized Guardian decision line (``<log root>/uacp/guardian.jsonl``)."""

    ts: int
    policy_version: str
    uacp_run_id: str
    uacp_phase: str
    runtime: str
    adapter: str
    tool_provider: str
    tool_name: str
    category: str
    decision: str
    reason: str
    workspace: str
    authority_artifact: str
    side_effects: object
    audit_artifact: str
    runtime_commit: str
    uacp_commit: str
    evidence: list[str]


@dataclass(frozen=True)
class GuardianEvent:
    runtime: str
    adapter: str
    event_type: str
    tool_provider: str
    tool_name: str
    # Tool arguments are heterogeneous (str / list / nested) — `object`, not `Any`,
    # so every consumer must narrow (isinstance) before use.
    tool_args: Mapping[str, object] = field(default_factory=dict[str, object])
    task_id: str = ""
    session_id: str = ""
    tool_call_id: str = ""
    workspace: str = ""
    uacp_run_id: str = ""
    uacp_phase: str = ""
    policy_version: str = ""
    declared_authority: str = ""
    declared_side_effects: object = None
    kanban_task_id: str = ""
    kanban_run_id: str = ""
    filesystem_guard_verified: bool = False


@dataclass(frozen=True)
class GuardianDecision:
    decision: str
    category: str
    reason: str
    evidence: list[str] = field(default_factory=list[str])
    audit_required: bool = False

    @property
    def blocks_execution(self) -> bool:
        return self.decision in {DECISION_BLOCK, DECISION_BLOCK_PENDING_HEARTGATE}

    def to_hook_result(self) -> dict[str, str]:
        return {
            "action": "block",
            "message": f"UACP Guardian blocked {self.category}: {self.reason}",
        }

    def to_audit_record(self, event: GuardianEvent, *, audit_artifact: str = "") -> AuditRecord:
        return {
            "ts": int(time.time()),
            "policy_version": event.policy_version,
            "uacp_run_id": event.uacp_run_id,
            "uacp_phase": event.uacp_phase,
            "runtime": event.runtime,
            "adapter": event.adapter,
            "tool_provider": event.tool_provider,
            "tool_name": event.tool_name,
            "category": self.category,
            "decision": self.decision,
            "reason": self.reason,
            "workspace": event.workspace,
            "authority_artifact": event.declared_authority,
            "side_effects": event.declared_side_effects,
            "audit_artifact": audit_artifact,
            "runtime_commit": os.getenv("HERMES_RUNTIME_COMMIT", ""),
            "uacp_commit": os.getenv("UACP_COMMIT", ""),
            "evidence": list(self.evidence),
        }


class GuardianPolicyError(RuntimeError):
    pass
