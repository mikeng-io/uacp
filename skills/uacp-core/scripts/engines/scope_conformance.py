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
working tree of a real run. The formerly-documented future mode is now
IMPLEMENTED as the diff-containment check (``SC_DIFF_*`` codes, issue #85):
when the workspace root is itself a git repo, the ACTUAL change set observed
by git (uncommitted ∪ committed-since-merge-base, via :mod:`engines.io.gitio`)
is compared against the declared ``write_paths``. This is the first
independently-witnessed input to this engine — git's account of what changed,
not the run's account of itself. It is **advisory-first**: every ``SC_DIFF_*``
violation is severity ``warn`` (correct-but-out-of-scope is a governance flag
whose remedy is re-declaration, and promotion to blocking is a later, explicit
decision). A workspace with no ``.git`` at its root is a documented NO-OP
(mirroring the absent-scope precedent) — which is exactly why the synthetic
temp-root fixtures remain quiet; a repo that exists but cannot be observed is
``SC_DIFF_UNAVAILABLE``, never a silent pass (fail-closed).

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
from engines.domain import layout

# All filesystem access is delegated to the io layer (no raw reads here).
from engines.io import (
    changed_files,
    derive_witness,
    load_artifact,
    load_manifest,
    load_registry,
    load_scope,
    resolve_in_workspace,
)
from engines.io.loaders import ManifestDoc

# UACP output / state surfaces an in-scope run product may legitimately land in
# even when not explicitly enumerated in write_paths: governed-writer outputs
# (resolutions/), the run's own state (state/), and verification evidence. These
# are system-owned write surfaces, not free-form EXECUTE writes, so a referenced
# artifact under one of them is treated as in-scope. Strings are base-relative
# (resolved under .uacp/), so `resolutions` replaces the old `.outputs`.
#
# NOTE (D43 Option B): the run's own RELATION-plane GOVERNANCE artifacts (proposal,
# keyed scope module, PIV, checkpoint, assessment — under proposals/plans/executions)
# are exempted by KIND, not by prefix (see _is_governance_manifest). A dir-prefix
# whitelist over those homes would be a CONTAINMENT REGRESSION: uacp_artifact_write
# accepts ARBITRARY non-manifest files under plans/proposals/executions (it only
# refuses RELATION-plane *manifest kinds*), so an EXECUTE product could be written to
# e.g. executions/patch.py, registered, and pass scope-conformance. The kind exemption
# avoids that: a RELATION-plane manifest can only be produced by the governed manifest
# writer (raw .uacp/ writes are Guardian-blocked; artifact_write refuses RELATION
# content), so a non-manifest file under those dirs is still flagged.
_ALLOWED_OUTPUT_PREFIXES = ("resolutions", "state", "verification")

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
    violations.extend(_check_diff_containment(root, scope_rel, scope_wps))
    violations.extend(_check_cascade_witness(root, scope_rel, scope))

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


def _is_governance_manifest(root: Path, rel: str, apath: Path) -> bool:
    """True iff ``rel`` is one of the run's own RELATION-plane GOVERNANCE manifests
    (proposal / keyed scope module / PIV / checkpoint / assessment / lessons / ...),
    which are lifecycle process artifacts, NOT EXECUTE write products — so they are
    in-scope wherever they live under the governed namespace.

    Spoof-resistance (this is a containment exemption, so it must not be forgeable):

    * The kind is taken PATH-CANONICALLY first (``layout.kind_for_relpath``). That is
      unspoofable for an attacker: ``uacp_artifact_write`` refuses to write any file
      whose path resolves to a RELATION-plane manifest kind, and ``uacp_entity_write``
      schema-validates, so a canonical RELATION path cannot hold arbitrary content.
    * It falls back to the artifact's own ``kind`` field ONLY for files resolving
      UNDER the governed namespace (``.uacp/``). A RELATION-kind document there can
      only have been produced by the governed manifest writer: raw ``.uacp/`` writes
      are Guardian-blocked, and ``uacp_artifact_write`` refuses RELATION-kind content
      at ANY path. So an EXECUTE product (repo file, or an arbitrary non-manifest file
      like ``executions/patch.py``) is never mistaken for governance and stays subject
      to the write_path boundary.
    """
    kind = layout.kind_for_relpath(rel)
    if kind is None:
        try:
            base = base_dir(root).resolve()
            under_governed = apath == base or base in apath.parents
        except Exception:
            under_governed = False
        if under_governed:
            doc = load_artifact(root, rel)
            if doc.error is None and isinstance(doc.value, dict):
                k = doc.value.get("kind")
                if isinstance(k, str):
                    kind = k
    return bool(kind) and layout.plane_of(kind) == layout.RELATION


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
        # The run's own RELATION-plane governance manifests are lifecycle process
        # artifacts, not EXECUTE products — exempt by KIND (D43 Option B), never by a
        # dir whitelist (which arbitrary-content files could exploit). See
        # _is_governance_manifest for the spoof-resistance argument.
        if _is_governance_manifest(root, rel, apath):
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


def _resolve_under_root(root: Path, rel: str) -> Path | None:
    """Resolve a WORKSPACE-relative path defensively; None if it escapes the
    workspace or is unresolvable. Never raises. (Counterpart of the io layer's
    ``resolve_in_workspace``, which roots at ``base_dir`` — the governed
    namespace — and is therefore wrong for git-reported workspace paths.)"""
    try:
        resolved = (root / rel).resolve()
        resolved.relative_to(root)
        return resolved
    except Exception:
        return None


# ----------------------------------------------------------- SC diff containment
def _check_diff_containment(
    root: Path, scope_rel: str, scope_wps: list[str] | None
) -> list[Violation]:
    """SC_DIFF_OUT_OF_SCOPE / SC_DIFF_UNAVAILABLE — the ACTUAL change set git
    observes must fall under a declared write_path or the governed namespace.

    This is the implemented "future mode" (module docstring): the first input
    to this engine that is NOT the run's own account of itself. Ground truth
    comes from :func:`engines.io.gitio.changed_files`; this function only
    compares (the witness derives, the gate compares — never the reverse).

    Doctrine, in order:
    * malformed write_paths -> no-op here (already reported by the escape check);
    * workspace root not a git repo -> no-op (documented: nothing to observe —
      also what keeps the synthetic test fixtures quiet);
    * repo present but unobservable -> ``SC_DIFF_UNAVAILABLE`` (fail-closed:
      an expected witness that cannot testify is surfaced, never a silent pass);
    * changes under the governed namespace (``.uacp/``) are exempt — those are
      governed-writer territory, watched by Guardian + the containment check
      above, not free-form EXECUTE writes;
    * everything else must sit under a declared write_path, or it is flagged.

    Advisory-first: both codes are severity ``warn``. Correct-but-out-of-scope
    is STILL flagged ("ungoverned", not "wrong"); the remedy is re-declaring
    the boundary, never silently widening it.
    """
    out: list[Violation] = []
    if scope_wps is None:
        return out

    result = changed_files(root)
    if not result.is_repo:
        return out
    if result.error is not None:
        out.append(
            _v(
                "SC_DIFF_UNAVAILABLE",
                f"workspace is a git repo but its change set could not be observed "
                f"({result.error}); diff-containment for scope {scope_rel} not verifiable",
                severity="warn",
                error=result.error,
            )
        )
        return out

    # Allowed containment roots: each declared write_path's static prefix plus
    # the ENTIRE governed namespace (.uacp/ — which subsumes the permitted
    # output surfaces used by the artifact-containment check above).
    #
    # NOTE on resolution: git reports paths relative to the WORKSPACE root, and
    # write_paths declare workspace-relative boundaries — so both sides resolve
    # under ``root`` here, NOT via resolve_in_workspace (which is for the
    # base-relative artifact refs writers store under .uacp/).
    allowed_roots: list[Path] = []
    for wp in scope_wps:
        probe = wp.split("*", 1)[0] or "."
        resolved = _resolve_under_root(root, probe)
        if resolved is not None:
            allowed_roots.append(resolved)
    try:
        allowed_roots.append(base_dir(root).resolve())
    except Exception:
        pass  # no governed namespace resolvable — write_paths remain the boundary

    offenders: list[str] = []
    for rel in result.files:
        apath = _resolve_under_root(root, rel)
        if apath is None:
            continue  # escaping/undecodable path — traversal is the escape check's turf
        if any(_is_contained(apath, base) for base in allowed_roots):
            continue
        offenders.append(rel)

    if offenders:
        shown = offenders[:20]
        out.append(
            _v(
                "SC_DIFF_OUT_OF_SCOPE",
                f"{len(offenders)} actual change(s) observed by git fall outside every "
                f"declared write_path {sorted(scope_wps)}: {shown}"
                f"{' (truncated)' if len(offenders) > len(shown) else ''} — "
                f"out-of-scope work; remedy is to re-declare the boundary (scope {scope_rel})",
                severity="warn",
                files=shown,
                total=len(offenders),
            )
        )
    return out


# --------------------------------------------------------- SC cascade witness
def _sym(entry: Any) -> tuple[str, str] | None:
    """Coerce a {file, name} dict into a comparable (file, name) tuple, or None if
    the shape is not a pair of non-empty strings. Symbols compare as (file, name)."""
    if not isinstance(entry, dict):
        return None
    f = entry.get("file")
    n = entry.get("name")
    if isinstance(f, str) and f and isinstance(n, str) and n:
        return (f, n)
    return None


def _fmt_unresolved(entry: Any) -> str | None:
    """Render an ``unresolved_touched`` entry for display. Tolerates a NULL name —
    the contract allows file-level entries {file, name: null} for unparseable files,
    which surface as the bare file path (visible-not-blocking)."""
    if not isinstance(entry, dict):
        return None
    f = entry.get("file")
    if not isinstance(f, str) or not f:
        return None
    n = entry.get("name")
    return f"{f}:{n}" if isinstance(n, str) and n else f


def _normalize_code_refs(raw: Any) -> list[dict[str, str]] | None:
    """Return code_refs as a list of {file, name} str dicts, or None if malformed.

    Absent/None/empty is handled by the caller (a no-op). This is a DEFENSIVE read:
    the write-time schema constrains code_refs, but the engine reads possibly
    hand-tampered state, so a malformed shape is surfaced (never silently dropped)."""
    if not isinstance(raw, list):
        return None
    out: list[dict[str, str]] = []
    for item in raw:
        sym = _sym(item)
        if sym is None:
            return None
        out.append({"file": sym[0], "name": sym[1]})
    return out


def _check_cascade_witness(root: Path, scope_rel: str, scope: Any) -> list[Violation]:
    """SC_UNDECLARED_CASCADE / SC_SCOPE_OVERDECLARED / SC_WITNESS_UNRESOLVED_CLAIM /
    SC_WITNESS_UNRESOLVED_TOUCHED / SC_WITNESS_UNAVAILABLE — compare the scope's DECLARED
    ``code_refs`` against the independent codeflair account of the actual change.

    The witness reports FACTS ONLY; this gate computes every verdict (design node 02):
    the witness derives, the code compares — a codeflair coverage bug must stay
    recomputable kernel-side. All codes are advisory ``severity: warn`` in v1.

    Doctrine, in order:
    * no ``code_refs`` (absent/None/empty) -> no-op (the claim is opt-in until promotion);
    * malformed ``code_refs`` -> ``SC_WITNESS_UNRESOLVED_CLAIM`` (defensive read of
      possibly-tampered state; the CLI is NOT invoked);
    * witness unavailable (unconfigured/absent CLI, non-zero, garbled, timed out after
      the one retry) -> ``SC_WITNESS_UNAVAILABLE`` (fail-closed visibility, gitio parity);
    * weaker provenance floor (``ingestion != "scip"``) -> ``SC_WITNESS_UNAVAILABLE``;
    * else compute coverage: a touched symbol is COVERED iff it is a resolved declared
      ref OR hop-1-adjacent (either endpoint, any reason) to one. Undeclared cascade,
      over-declaration, and unresolved declared refs each get their own advisory.
    """
    raw = getattr(scope, "code_refs", None)
    if raw is None or raw == []:
        return []  # opt-in claim absent -> no-op (CLI never invoked)

    refs = _normalize_code_refs(raw)
    if refs is None:
        return [
            _v(
                "SC_WITNESS_UNRESOLVED_CLAIM",
                f"scope.code_refs is malformed (not a list of {{file, name}} string pairs) "
                f"({scope_rel}); cannot derive the cascade witness",
                severity="warn",
            )
        ]

    result = derive_witness(root, refs)
    if not result.available:
        return [
            _v(
                "SC_WITNESS_UNAVAILABLE",
                f"scope declares code_refs but the cascade witness could not testify "
                f"({result.error}); cascade-containment for scope {scope_rel} not verifiable",
                severity="warn",
                error=result.error,
                command=list(result.command),
            )
        ]

    facts = result.facts
    if facts is None or facts.ingestion != "scip":
        return [
            _v(
                "SC_WITNESS_UNAVAILABLE",
                f"cascade witness reported a weaker provenance floor "
                f"(ingestion={facts.ingestion if facts else None!r}, expected 'scip') "
                f"for scope {scope_rel}; account rejected",
                severity="warn",
                ingestion=(facts.ingestion if facts else None),
                command=list(result.command),
            )
        ]

    out: list[Violation] = []

    # Declared echo: resolved refs count as coverage anchors; unresolved refs never do.
    declared_resolved: set[tuple[str, str]] = set()
    unresolved_declared: list[tuple[str, str]] = []
    for entry in facts.declared:
        sym = _sym(entry)
        if sym is None:
            continue
        if entry.get("resolved") is True:
            declared_resolved.add(sym)
        else:
            unresolved_declared.append(sym)

    if unresolved_declared:
        shown = sorted(unresolved_declared)[:20]
        out.append(
            _v(
                "SC_WITNESS_UNRESOLVED_CLAIM",
                f"{len(unresolved_declared)} declared code_ref(s) did not resolve in the "
                f"code graph and DO NOT count as coverage: "
                f"{[f'{f}:{n}' for f, n in shown]} (scope {scope_rel})",
                severity="warn",
                unresolved=[f"{f}:{n}" for f, n in shown],
                total=len(unresolved_declared),
            )
        )

    touched: set[tuple[str, str]] = set()
    for entry in facts.symbols_touched:
        sym = _sym(entry)
        if sym is not None:
            touched.add(sym)

    # Hop-1 adjacency from the neighborhood edges: for each edge, record both
    # directed endpoint->endpoint links so "either endpoint, any reason" holds.
    neighbors: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for edge in facts.neighborhood:
        if not isinstance(edge, dict):
            continue
        src = _sym(edge.get("src"))
        dst = _sym(edge.get("dst"))
        if src is None or dst is None or src == dst:
            continue
        neighbors.setdefault(src, set()).add(dst)
        neighbors.setdefault(dst, set()).add(src)

    def _covered(sym: tuple[str, str]) -> bool:
        if sym in declared_resolved:
            return True
        return bool(neighbors.get(sym, set()) & declared_resolved)

    undeclared_cascade = sorted(t for t in touched if not _covered(t))
    if undeclared_cascade:
        shown = undeclared_cascade[:20]
        unresolved_touched = [
            x for x in (_fmt_unresolved(e) for e in facts.unresolved_touched) if x is not None
        ]
        out.append(
            _v(
                "SC_UNDECLARED_CASCADE",
                f"{len(undeclared_cascade)} touched symbol(s) are neither declared nor hop-1 "
                f"connected to a declared code_ref (undeclared cascade): "
                f"{[f'{f}:{n}' for f, n in shown]}"
                f"{' (truncated)' if len(undeclared_cascade) > len(shown) else ''} — "
                f"ungoverned reach; remedy is to re-declare code_refs (scope {scope_rel})",
                severity="warn",
                symbols=[f"{f}:{n}" for f, n in shown],
                total=len(undeclared_cascade),
                unresolved_touched=unresolved_touched,
            )
        )

    # Over-declaration: a resolved declared ref that is neither touched nor hop-1
    # adjacent to any touched symbol (a claim >= the graph makes every cascade
    # "covered" — write_paths:["**"] in symbol clothing; the claim must be near-minimal).
    hop1_of_touched: set[tuple[str, str]] = set()
    for t in touched:
        hop1_of_touched |= neighbors.get(t, set())
    over_declared = sorted(declared_resolved - (touched | hop1_of_touched))
    if over_declared:
        shown = over_declared[:20]
        out.append(
            _v(
                "SC_SCOPE_OVERDECLARED",
                f"{len(over_declared)} declared code_ref(s) are neither touched nor hop-1 "
                f"adjacent to any touched symbol (over-declaration): "
                f"{[f'{f}:{n}' for f, n in shown]} — the claim must be near-minimal, "
                f"not a superset that makes every cascade 'covered' (scope {scope_rel})",
                severity="warn",
                symbols=[f"{f}:{n}" for f, n in shown],
                total=len(over_declared),
            )
        )

    # Unresolved-touched surfacing (K3 / design node 02): fired UNCONDITIONALLY whenever
    # the witness reports touched-but-unresolvable files, regardless of any other finding.
    # A diff whose ONLY changed files are unparseable produces no cascade and would
    # otherwise vanish entirely (silent fail-open forbidden); it is visible-but-not-
    # blocking. This code OWNS the surfacing — the copy in the cascade advisory's detail
    # above is informational context only.
    unresolved_touched_fmt = [
        x for x in (_fmt_unresolved(e) for e in facts.unresolved_touched) if x is not None
    ]
    if unresolved_touched_fmt:
        shown = unresolved_touched_fmt[:20]
        out.append(
            _v(
                "SC_WITNESS_UNRESOLVED_TOUCHED",
                f"{len(unresolved_touched_fmt)} changed file(s)/symbol(s) the witness could not "
                f"resolve in the code graph (new/unparseable/unsupported-language code): {shown}"
                f"{' (truncated)' if len(unresolved_touched_fmt) > len(shown) else ''} — "
                f"changed code the witness cannot reason about, surfaced (scope {scope_rel})",
                severity="warn",
                unresolved_touched=shown,
                total=len(unresolved_touched_fmt),
            )
        )

    return out


# Register this engine. Guard against double-registration if the module is
# imported under more than one name (e.g. "scope_conformance" and
# "engines.scope_conformance").
if not any(name == "scope_conformance" for name, _ in ENGINES):
    ENGINES.append(("scope_conformance", validate))
