"""Scope-conformance validator for UACP runs.

Read-only, defensive consumer of the kernel's emitted state. Given a workspace
(UACP_ROOT) and a run_id, it answers ONE question to the extent the kernel's
durable state allows it: *did the run stay within the boundaries it DECLARED?*
The declared boundary is the ``uacp.scope`` artifact (``write_paths`` +
``blast_radius`` + ``rollback_path``) plus the run-registry entry that mirrors
it. Stable codes are prefixed ``SC_``.

This module never mutates anything and NEVER raises: every failure mode (absent
file, garbled YAML, schema drift, traversal) is converted into a
:class:`~engines.base.Violation` rather than an exception. An empty result list
means "the declared scope is well-formed and self-consistent, and every write
the system CAN see is inside it".

Architecture (hexagonal-lite): PURE of filesystem I/O. All disk reads go through
:mod:`engines.io` (typed :mod:`engines.domain` read-models); the checks below
operate on those models. The blast-radius enum is read from the canonical
``config/artifact-schemas.yaml`` (``scope.fields.blast_radius.values``), not
hard-coded — with a conservative fallback if that document is unreadable.

WHAT THIS ENGINE CAN AND CANNOT VERIFY
--------------------------------------
The kernel keeps **no durable per-write audit log**: there is no record of which
files EXECUTE actually wrote. Therefore "every actual file write landed inside a
declared write_path" is **NOT computable from state alone** and is deliberately
NOT attempted here. What IS computable, and is what this engine checks:

* The declared boundary is internally well-formed and agrees across the three
  places it is recorded (scope artifact, run-registry entry, manifest reference).
* Every *artifact path the manifest itself references* falls inside a declared
  write_path or a permitted UACP output surface — i.e. the run-product writes the
  system DOES record are in-scope.
* The declared write_paths and blast_radius are themselves valid (no workspace
  escape, blast_radius in the schema enum).

A true "actual change stayed in scope" check requires diffing the real git
working tree of a real run (``git diff --name-only`` ∩ ``write_paths``). That is
a documented **future mode** — it cannot run against the synthetic temp-root
test fixtures (no git history, no real EXECUTE writes), so it is intentionally
unimplemented here rather than faked.

RELATIONSHIP TO COHERENCE C6
----------------------------
Coherence's ``C6_WRITE_PATHS_DISAGREE`` already compares ``scope.write_paths``
against the run-registry entry's ``write_paths`` as sets. ``SC_SCOPE_REGISTRY_
DISAGREE`` covers that SAME write_paths invariant — this is intentional, not a
silent duplicate: scope-conformance is the natural home for "scope vs registry
agreement", and it is reported under an ``SC_`` code so a scope-conformance
sweep is self-contained. SC then goes BEYOND C6 with a tripartite check (the
registry's ``scope_artifact_path`` must point at the same scope artifact the
manifest references) and the containment / blast-radius / traversal checks C6
does not perform. Operators who run both engines will see one finding per
engine for a write_paths divergence; that is the documented, accepted overlap.

DECISION: absent scope or registry is a NO-OP, not a violation. A run that has
not yet reached PLAN->EXECUTE has legitimately not declared a scope, and a run
deregistered at RESOLVE legitimately no longer appears in the registry. With no
declared boundary there is nothing to conform to, so the relevant checks
self-disable (mirroring coherence C6 and ledger_integrity's absent-ledger no-op).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import get_args as _get_args

from config import base_dir

# The shared violation type + engine registry. Every engine reports the same
# Violation; this engine registers itself in ENGINES at the bottom of the module.
from engines.base import ENGINES, Violation

# All filesystem access is delegated to the io layer (no raw reads here).
from engines.io import (
    load_manifest,
    load_registry,
    load_scope,
    resolve_in_workspace,
)
from engines.io.loaders import ManifestDoc

# UACP output / state surfaces an in-scope run product may legitimately land in
# even when not explicitly enumerated in write_paths: the governed namespace dirs
# where the run's own GOVERNANCE artifacts live — the PROPOSE proposal package +
# keyed scope module (proposals/), the PLAN package + PIV (plans/), EXECUTE
# checkpoints (executions/), VERIFY evidence (verification/), RESOLVE closure +
# lessons (resolutions/), and the run's state/ledger (state/). These are
# system-owned, governed-writer-only surfaces under .uacp/ — never free-form
# EXECUTE writes to the repo (those go to declared write_paths) — so a manifest
# referencing an artifact under one of them is in-scope, not an out-of-scope
# write. The governance homes (proposals/plans/executions) were added with D43
# Option B: coverage binding REGISTERS the keyed scope module + PIV + checkpoint
# in the manifest (entity-write already auto-registers them there), so closure's
# scope-conformance must recognise those homes as legitimate surfaces. Strings are
# base-relative (resolved under .uacp/), so `resolutions` replaces the old `.outputs`.
_ALLOWED_OUTPUT_PREFIXES = (
    "proposals",
    "plans",
    "executions",
    "verification",
    "resolutions",
    "state",
)

# Canonical blast_radius values — sourced from the codified Pydantic model
# (engines.domain.artifact_schema.BLAST_RADIUS_VALUES) via get_args(BlastRadius).
# Previously read from config/artifact-schemas.yaml (scope.fields.blast_radius.values);
# codified in Slice 4a to eliminate the live YAML read.
try:
    from engines.domain.artifact_schema import BLAST_RADIUS_VALUES

    _FALLBACK_BLAST_RADIUS: frozenset[str] = BLAST_RADIUS_VALUES
except Exception:
    _FALLBACK_BLAST_RADIUS = frozenset({"low", "medium", "high", "critical"})


def _v(code: str, message: str, severity: str = "block", **detail: Any) -> Violation:
    return Violation(code=code, severity=severity, message=message, detail=detail)


def _load_blast_radius_enum(root: Path) -> frozenset[str]:  # noqa: ARG001
    """Return the allowed blast_radius values from the codified domain model.

    Slice 4a: previously read ``config/artifact-schemas.yaml`` (``scope.fields.
    blast_radius.values``) via the io layer. Now returns ``BLAST_RADIUS_VALUES``
    from ``engines.domain.artifact_schema`` — no filesystem I/O, no YAML
    dependency. The ``root`` argument is kept for call-site compatibility.
    Never raises: on any failure fall back to the hardcoded frozenset."""
    try:
        from engines.domain.artifact_schema import BlastRadius  # noqa: PLC0415

        values = frozenset(_get_args(BlastRadius))
        return values if values else _FALLBACK_BLAST_RADIUS
    except Exception:
        return _FALLBACK_BLAST_RADIUS


def _is_contained(child: Path, parent: Path) -> bool:
    """True iff ``child`` is ``parent`` itself or lives under it. Path-prefix
    containment on already-resolved, workspace-relative paths."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def validate(workspace: str | Path, run_id: str) -> list[Violation]:
    """Validate that a run conformed to its DECLARED scope, to the extent the
    kernel's durable state permits (see module docstring for the no-write-log
    limitation). Returns a list of Violation. Empty == conformant / nothing to
    check. Never raises.
    """
    violations: list[Violation] = []

    try:
        root = Path(str(workspace)).resolve()
    except Exception as exc:
        return [_v("SC_WORKSPACE_INVALID", f"workspace path invalid: {type(exc).__name__}: {exc}")]

    if not run_id or not isinstance(run_id, str):
        return [_v("SC_RUN_ID_INVALID", f"run_id invalid: {run_id!r}")]

    loaded = load_manifest(root, run_id)
    if loaded.error is not None or loaded.value is None:
        # No manifest -> no declared scope reference -> nothing to conform to.
        # Manifest existence/shape is coherence's C0 concern, not ours.
        return violations
    doc: ManifestDoc = loaded.value
    manifest = doc.raw

    artifacts = manifest.get("artifacts") or {}
    if not isinstance(artifacts, dict):
        artifacts = {}

    scope_rel = artifacts.get("scope")
    if not isinstance(scope_rel, str) or not scope_rel:
        # Run has not declared a scope yet (pre-EXECUTE). No-op.
        return violations
    scope_path = resolve_in_workspace(root, scope_rel)
    if scope_path is None or not scope_path.exists():
        # Scope referenced but absent/escaping: coherence C5 owns existence.
        return violations
    scope_loaded = load_scope(root, scope_rel)
    if scope_loaded.error is not None or scope_loaded.value is None:
        return violations
    scope = scope_loaded.value

    scope_wps = _normalize_write_paths(scope.write_paths)

    violations.extend(_check_write_paths_escape(root, scope_rel, scope_wps))
    violations.extend(_check_blast_radius(root, scope_rel, scope))
    violations.extend(_check_scope_registry(root, run_id, scope_rel, scope_wps, scope.write_paths))
    violations.extend(_check_artifact_containment(root, scope_rel, scope_wps, artifacts))

    return violations


def _normalize_write_paths(raw: Any) -> list[str] | None:
    """Return the declared write_paths as a list of strings, or None if the
    field is malformed (not a list). An empty list is a valid declaration
    (the run declared it writes nothing outside the permitted output surfaces)."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        return None
    return [str(p) for p in raw if isinstance(p, (str, int))]


# ----------------------------------------------------------- SC write-path escape
def _check_write_paths_escape(
    root: Path, scope_rel: str, write_paths: list[str] | None
) -> list[Violation]:
    """SC_WRITE_PATH_ESCAPES_WORKSPACE — every declared write_path must resolve
    INSIDE the workspace. A path with a ``../`` traversal that escapes the root
    is an invalid declaration (the run could not legally write there). Reuses the
    io traversal-safe resolver."""
    out: list[Violation] = []
    if write_paths is None:
        out.append(
            _v(
                "SC_WRITE_PATHS_MALFORMED",
                f"scope.write_paths is not a list ({scope_rel})",
                severity="warn",
            )
        )
        return out
    for wp in write_paths:
        # Strip a trailing glob/segment so a directory-glob like 'docs/**' still
        # resolves; resolve_in_workspace treats the literal string as a path.
        probe = wp.split("*", 1)[0] or "."
        resolved = resolve_in_workspace(root, probe)
        if resolved is None:
            out.append(
                _v(
                    "SC_WRITE_PATH_ESCAPES_WORKSPACE",
                    f"declared write_path '{wp}' resolves outside the workspace "
                    f"(path traversal); scope {scope_rel}",
                )
            )
    return out


# ----------------------------------------------------------------- SC blast radius
def _check_blast_radius(root: Path, scope_rel: str, scope: Any) -> list[Violation]:
    """SC_BLAST_RADIUS_INVALID — when scope declares a blast_radius it must be one
    of the values the schema enumerates (config/artifact-schemas.yaml). An absent
    blast_radius is NOT flagged here (required-field enforcement is Heartgate's
    schema gate at PLAN->EXECUTE); we only flag a value the schema does not allow.
    """
    out: list[Violation] = []
    # Presence test: only check when the artifact actually declared the key.
    if "blast_radius" not in getattr(scope, "model_fields_set", set()):
        return out
    br = scope.blast_radius
    if br is None:
        return out
    allowed = _load_blast_radius_enum(root)
    if str(br) not in allowed:
        out.append(
            _v(
                "SC_BLAST_RADIUS_INVALID",
                f"scope.blast_radius '{br}' is not in the schema-declared enum "
                f"{sorted(allowed)} ({scope_rel})",
            )
        )
    return out


# ------------------------------------------------------------- SC scope vs registry
def _check_scope_registry(
    root: Path,
    run_id: str,
    scope_rel: str,
    scope_wps: list[str] | None,
    raw_scope_wps: Any,
) -> list[Violation]:
    """SC_SCOPE_REGISTRY_DISAGREE — the run-registry entry for this run must agree
    with the scope artifact on (a) the declared write_paths (set equality) and
    (b) which scope artifact it points at (``scope_artifact_path``).

    This write_paths check intentionally mirrors coherence C6 (documented overlap
    — see module docstring) and ADDS the scope_artifact_path tripartite check.
    No-op when the run is not in the registry (deregistered / never registered)
    or the registry is absent: with no registry mirror there is nothing to
    cross-check against (no durable write-log to fall back on)."""
    out: list[Violation] = []
    if scope_wps is None:
        return out  # malformed write_paths already reported by escape check

    registry = load_registry(root)
    if registry.value is None:
        return out
    entry = next((e for e in registry.value.active_runs if e.run_id == run_id), None)
    if entry is None:
        return out  # run not registered — nothing to compare

    reg_wps = _normalize_write_paths(entry.write_paths)
    if reg_wps is None:
        out.append(
            _v(
                "SC_SCOPE_REGISTRY_DISAGREE",
                f"run-registry write_paths for run '{run_id}' is not a list "
                f"(cannot compare against scope {scope_rel})",
                severity="warn",
            )
        )
        return out

    if set(scope_wps) != set(reg_wps):
        out.append(
            _v(
                "SC_SCOPE_REGISTRY_DISAGREE",
                f"scope.write_paths {sorted(scope_wps)} disagree with run-registry "
                f"write_paths {sorted(reg_wps)} for run '{run_id}' "
                f"(declared boundary recorded inconsistently)",
            )
        )

    # Tripartite extension: the registry's scope_artifact_path, when set, must
    # name the same scope artifact the manifest references.
    reg_scope_path = entry.scope_artifact_path
    if isinstance(reg_scope_path, str) and reg_scope_path:
        man_resolved = resolve_in_workspace(root, scope_rel)
        reg_resolved = resolve_in_workspace(root, reg_scope_path)
        if man_resolved is not None and reg_resolved is not None and man_resolved != reg_resolved:
            out.append(
                _v(
                    "SC_SCOPE_REGISTRY_DISAGREE",
                    f"run-registry scope_artifact_path '{reg_scope_path}' for run "
                    f"'{run_id}' does not match the manifest-referenced scope "
                    f"artifact '{scope_rel}'",
                )
            )
    return out


# ------------------------------------------------------- SC artifact containment
def _check_artifact_containment(
    root: Path,
    scope_rel: str,
    scope_wps: list[str] | None,
    artifacts: dict[str, Any],
) -> list[Violation]:
    """SC_ARTIFACT_OUT_OF_SCOPE — every artifact path the manifest references must
    fall UNDER a declared write_path OR a permitted UACP output surface
    (resolutions/, state/, verification/). An artifact the manifest records as
    living outside every declared boundary is an out-of-scope write the system
    CAN see.

    The scope artifact itself is exempt (it is the boundary declaration, written
    during PLAN, not an EXECUTE product). No-op when write_paths is malformed."""
    out: list[Violation] = []
    if scope_wps is None:
        return out

    # Precompute the allowed containment roots: each declared write_path's
    # static prefix + the permitted output surfaces.
    allowed_roots: list[Path] = []
    for wp in scope_wps:
        probe = wp.split("*", 1)[0] or "."
        resolved = resolve_in_workspace(root, probe)
        if resolved is not None:
            allowed_roots.append(resolved)
    # Permitted output surfaces are base-relative dirs under the governed
    # namespace (.uacp/), matching where writers place artifacts and where
    # resolve_in_workspace resolves the artifact refs below.
    for surface in _ALLOWED_OUTPUT_PREFIXES:
        allowed_roots.append((base_dir(root) / surface).resolve())

    scope_resolved = resolve_in_workspace(root, scope_rel)

    for key, rel in artifacts.items():
        if not isinstance(rel, str) or not rel:
            continue  # malformed artifact ref is coherence C5's concern
        apath = resolve_in_workspace(root, rel)
        if apath is None:
            continue  # escaping path is coherence C5's concern
        # The scope artifact declares the boundary; it is not an in-scope product.
        if scope_resolved is not None and apath == scope_resolved:
            continue
        if any(_is_contained(apath, base) for base in allowed_roots):
            continue
        out.append(
            _v(
                "SC_ARTIFACT_OUT_OF_SCOPE",
                f"artifact '{key}' ({rel}) is outside every declared write_path "
                f"{sorted(scope_wps)} and every permitted output surface "
                f"{list(_ALLOWED_OUTPUT_PREFIXES)} — out-of-scope write",
            )
        )
    return out


# Register this engine. Guard against double-registration if the module is
# imported under more than one name (e.g. "scope_conformance" and
# "engines.scope_conformance").
if not any(name == "scope_conformance" for name, _ in ENGINES):
    ENGINES.append(("scope_conformance", validate))
