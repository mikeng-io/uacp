"""Phase A1 extraction contract: the Guardian gate lives in ``engines/guardian/``
and ``core.py`` only *re-exports* it (design/graph-engine nodes 31/32).

These tests lock the *structure* of the extraction. The existing Guardian
behavioural suites (``test_policy``, ``test_guardian_*``, ``test_pretooluse_hook``,
``test_guardian_oracle_eval``, ...) import the same names through ``core``'s
re-export, so they remain the behavioural regression gate. Here we assert the
invariants that move introduces and that could silently regress:

* the new import path exists and the package ``__init__`` is the public door;
* ``core`` re-exports the *same objects* (one source of truth, not a fork — a
  redefinition in ``core`` would make the ``is`` checks fail — node 32 §3);
* each symbol lives in its node-31 module (the layout contract — node 32 §1);
* ``resolve_uacp_root`` moved to the domain leaf (Phase A1 option ii).
"""

from __future__ import annotations

import pytest

import core
from engines import guardian
from engines.domain import paths as domain_paths
from engines.guardian import audit, events, models, policy
from engines.guardian import guardian as guardian_mod

_PUBLIC = (
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
)


def test_guardian_package_exposes_full_public_surface():
    # The package __init__ is the public door (node 32 §3): __all__ matches the
    # set callers rely on, and every name is importable from the package.
    assert set(guardian.__all__) == set(_PUBLIC)
    for name in _PUBLIC:
        assert hasattr(guardian, name), f"engines.guardian missing {name}"


def test_core_reexports_are_the_same_objects():
    # core.py must re-export, never redefine (one source of truth). Identity, not
    # equality: a redefinition in core would make these `is` checks fail.
    for name in _PUBLIC:
        assert getattr(core, name) is getattr(guardian, name), f"core.{name} is not the re-export"


def test_resolve_uacp_root_moved_to_domain_leaf():
    # Phase A1 (option ii) pulled node-31 step 8 forward: the root helper lives in
    # the domain sink, and core imports the *same* object (no core->core lazy dep).
    assert core.resolve_uacp_root is domain_paths.resolve_uacp_root


def test_resolve_uacp_root_fail_closed_when_unset(monkeypatch, tmp_path):
    # Fail-closed contract: with no explicit arg and neither UACP_ROOT nor
    # HERMES_HOME set, the resolver RAISES rather than guessing the removed
    # legacy ~/.hermes/uacp default.
    monkeypatch.delenv("UACP_ROOT", raising=False)
    monkeypatch.delenv("HERMES_HOME", raising=False)
    with pytest.raises(domain_paths.UacpRootUnresolvedError):
        domain_paths.resolve_uacp_root()

    # NON-VACUITY: the raise is specifically due to absence — setting UACP_ROOT
    # makes the same call return that root (so the test fails for the right
    # reason, not because the resolver always raises).
    monkeypatch.setenv("UACP_ROOT", str(tmp_path))
    assert domain_paths.resolve_uacp_root() == tmp_path.resolve()


def test_symbols_live_in_their_node31_modules():
    # Lock the module layout (node 32 §1): models = data, policy = GuardianPolicy,
    # guardian = the gate, events = factories, audit = the sink.
    assert guardian.GuardianEvent is models.GuardianEvent
    assert guardian.GuardianDecision is models.GuardianDecision
    assert guardian.GuardianPolicyError is models.GuardianPolicyError
    assert guardian.GuardianPolicy is policy.GuardianPolicy
    assert guardian.Guardian is guardian_mod.Guardian
    assert guardian.make_event is events.make_event
    assert guardian.infer_tool_provider is events.infer_tool_provider
    assert guardian.write_audit_record is audit.write_audit_record
    # The decision vocabulary is defined in models (consumed by GuardianDecision).
    assert models.DECISION_BLOCK == "block"


def test_extracted_factories_run_without_fixtures():
    # A behavioural smoke that the moved factory code is wired and runs (no config
    # root needed). Full Guardian behaviour is covered by the existing suites.
    event = guardian.make_event(tool_name="read_file", args={"path": "x.txt"})
    assert isinstance(event, guardian.GuardianEvent)
    assert event.tool_name == "read_file"
    assert guardian.infer_tool_provider("mcp_search") == "mcp"
    assert guardian.infer_tool_provider("read_file", "core") == "core"
