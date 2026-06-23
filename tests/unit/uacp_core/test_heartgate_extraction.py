"""Phase A3.0 extraction contract: the Heartgate phase-transition gate lives in
``engines/heartgate/`` and ``core.py`` only *re-exports* it (design/graph-engine
nodes 30/31/32).

These tests lock the *structure* of the extraction. The existing Heartgate
behavioural suites (``test_transition_integrity``, ``test_standard_track_equivalence``,
``test_goal_driven_*``, ``test_coherence``, the e2e lifecycle tests, ...) import
the same names through ``core``'s re-export, so they remain the behavioural
regression gate. Here we assert the invariants the move introduces and that could
silently regress:

* the new import path exists and the package ``__init__`` is the public door;
* ``core`` re-exports the *same objects* (one source of truth, not a fork — a
  redefinition in ``core`` would make the ``is`` checks fail — node 32 §3);
* each symbol lives in its node-31 module (the layout contract — node 32 §1);
* the private ``_is_safe_run_id`` (imported by ``state.py`` via ``core``) moved
  with the class and is re-exported from ``core`` but is NOT in the package
  public surface (node 32 §3).
"""

from __future__ import annotations

import core
from engines import heartgate
from engines.heartgate import heartgate as heartgate_mod
from engines.heartgate import models

_PUBLIC = (
    "Heartgate",
    "HeartgateDecision",
    "HeartgateError",
)


def test_heartgate_package_exposes_full_public_surface():
    # The package __init__ is the public door (node 32 §3): __all__ matches the
    # set callers rely on, and every name is importable from the package.
    assert set(heartgate.__all__) == set(_PUBLIC)
    for name in _PUBLIC:
        assert hasattr(heartgate, name), f"engines.heartgate missing {name}"


def test_core_reexports_are_the_same_objects():
    # core.py must re-export, never redefine (one source of truth). Identity, not
    # equality: a redefinition in core would make these `is` checks fail.
    for name in _PUBLIC:
        assert getattr(core, name) is getattr(heartgate, name), f"core.{name} is not the re-export"


def test_symbols_live_in_their_node31_modules():
    # Lock the module layout (node 32 §1): models = pure data (error + decision),
    # heartgate = the gate class.
    assert heartgate.HeartgateError is models.HeartgateError
    assert heartgate.HeartgateDecision is models.HeartgateDecision
    assert heartgate.Heartgate is heartgate_mod.Heartgate
    # The decision record is a frozen dataclass that blocks only on "block".
    blocked = models.HeartgateDecision("block", "nope")
    assert blocked.blocks_transition is True
    assert models.HeartgateDecision("pass", "ok").blocks_transition is False


# Private helpers that lived in core and are imported by name by state.py
# (_is_safe_run_id) and the hermes guardian kernel shim (all three). The move
# must keep them importable from core, as the SAME objects, without exposing them
# in the package public surface (node 32 §3: privates are never in __all__).
_PRIVATE_REEXPORTS = ("_is_safe_run_id", "_truthy", "_load_artifact_schemas")


def test_private_helpers_moved_with_class_and_reexported_from_core():
    for name in _PRIVATE_REEXPORTS:
        assert getattr(core, name) is getattr(heartgate_mod, name), (
            f"core.{name} is not the re-export of engines.heartgate.heartgate.{name}"
        )
        assert name not in heartgate.__all__, f"{name} must not be in the package __all__"
        assert not hasattr(heartgate, name), f"private {name} leaked into the package door"
    # Behavioural smoke that the moved predicate is wired (full coverage lives in
    # the path-traversal suite): rejects traversal, accepts a safe id.
    assert heartgate_mod._is_safe_run_id("run-123") is True
    assert heartgate_mod._is_safe_run_id("../escape") is False


def test_heartgate_still_wired_after_move():
    # Smoke that the relocated class is fully wired: it constructs from a
    # stage-less config and the __init__ falls back to the codified defaults
    # (stages / required_fields / artifact_schemas) — i.e. the lazy imports the
    # constructor makes all resolve from the new module location. Full gate
    # behaviour is covered by the existing transition/closure suites.
    gate = core.Heartgate({})
    assert gate.stages, "codified stages default did not populate after the move"
    assert isinstance(gate.required_fields, list)
    assert isinstance(gate.artifact_schemas, dict)
    for method in ("validate_transition", "validate_transition_file", "validate_closure"):
        assert callable(getattr(gate, method)), f"Heartgate.{method} missing after move"


def test_heartgate_tool_path_capabilities_wrapper_present():
    # C3a regression guard (Codex PR#5): _tool_path_capabilities() was carved to
    # engines.manifest.validators, but external callers remain — scripts/phase2_verify.py and
    # scripts/phase3_verify.py call ``hg._tool_path_capabilities()``. The delegating wrapper must
    # stay on Heartgate (deleting it raised AttributeError in those scripts; the pytest suite
    # missed it because the phase-verify scripts are not pytest-run).
    gate = core.Heartgate({})
    assert callable(getattr(gate, "_tool_path_capabilities", None))
    assert isinstance(gate._tool_path_capabilities(), dict)
