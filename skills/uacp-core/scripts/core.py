"""Runtime-neutral UACP core.

Imported by runtime adapters. Contains no framework-specific imports.

This module is now a thin re-export hub. The Guardian write-time gate (A1) and
the Heartgate phase-transition gate (A3) were extracted to ``engines/guardian/``
and ``engines/heartgate/`` (design/graph-engine nodes 30/31/32). The names below
are re-exported so existing ``from core import Guardian, Heartgate, ...``
importers (governed_handlers, hook_kernel, uacp-state, tests) keep working — a
behaviour-preserving move with one source of truth per symbol (node 32 §3).
"""

from __future__ import annotations

# resolve_uacp_root lives in the domain sink (A1, node 31 step 8); re-exported
# here because importers and the extraction-contract tests resolve it via core.
from engines.domain.paths import resolve_uacp_root  # noqa: F401

from engines.guardian import (  # noqa: F401
    DECISION_ALLOW,
    DECISION_ALLOW_WITH_AUDIT,
    DECISION_BLOCK,
    DECISION_BLOCK_PENDING_HEARTGATE,
    DECISION_REQUIRE_APPROVAL,
    Guardian,
    GuardianDecision,
    GuardianEvent,
    GuardianPolicy,
    GuardianPolicyError,
    infer_tool_provider,
    make_event,
    write_audit_record,
)
from engines.heartgate import (  # noqa: F401
    Heartgate,
    HeartgateDecision,
    HeartgateError,
)

# Private helpers that lived in core and are imported by name elsewhere:
# state.py (``from core import _is_safe_run_id``) and the hermes guardian kernel
# shim (``from core import _is_safe_run_id, _truthy, _load_artifact_schemas``).
# They moved with the Heartgate class; re-export them directly from the submodule
# — they are NOT part of the heartgate package public surface (node 32 §3) —
# until they are promoted to domain helpers. Removal owner: the helper-promotion
# increment.
from engines.heartgate.heartgate import (  # noqa: F401
    _is_safe_run_id,
    _load_artifact_schemas,
    _truthy,
)
