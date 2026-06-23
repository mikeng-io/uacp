"""The Guardian write-time gate (Phase A1 extraction from ``core.py``).

The Guardian classifies tool-call events against a loaded ``GuardianPolicy`` and
decides allow / allow_with_audit / require_approval / block. Extracted from the
``core.py`` monolith as the first decomposition increment (design/graph-engine
node 31). ``core.py`` re-exports these names so existing ``from core import
Guardian`` importers are unaffected — this package's ``__init__`` is the public
door (re-imports + ``__all__``), per node 32 §1/§3.
"""

from __future__ import annotations

from .audit import write_audit_record
from .events import infer_tool_provider, make_event
from .guardian import Guardian
from .models import (
    DECISION_ALLOW,
    DECISION_ALLOW_WITH_AUDIT,
    DECISION_BLOCK,
    DECISION_BLOCK_PENDING_HEARTGATE,
    DECISION_REQUIRE_APPROVAL,
    GuardianDecision,
    GuardianEvent,
    GuardianPolicyError,
)
from .policy import GuardianPolicy

__all__ = [
    "DECISION_ALLOW",
    "DECISION_ALLOW_WITH_AUDIT",
    "DECISION_REQUIRE_APPROVAL",
    "DECISION_BLOCK",
    "DECISION_BLOCK_PENDING_HEARTGATE",
    "Guardian",
    "GuardianDecision",
    "GuardianEvent",
    "GuardianPolicy",
    "GuardianPolicyError",
    "infer_tool_provider",
    "make_event",
    "write_audit_record",
]
