"""Disk loaders that return domain read-models and never raise.

Result pattern: every loader returns a :class:`Loaded` wrapper with ``value``
(the parsed model / mapping, or ``None`` on failure) and ``error`` (a human
string when the load failed, else ``None``). Callers branch on ``error`` /
``value`` to emit the right ``Violation`` — no exception ever escapes.

Path resolution reuses ``filesystem._resolve_uacp_path`` for traversal safety;
``resolve_in_workspace`` returns ``None`` (never raises) when a relative path
escapes the workspace or is otherwise unresolvable.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Bootstrap sibling-kernel imports (filesystem helper) the same way the engine
# package does, so the io layer works regardless of how it is imported.
_IO_DIR = Path(__file__).resolve().parent
_ENGINES_DIR = _IO_DIR.parent
_CORE_DIR = _ENGINES_DIR.parent
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from filesystem import _resolve_uacp_path  # noqa: E402

# Importing the domain package also bootstraps state_machine onto sys.path and
# reuses RunManifest (it is not re-declared here).
from engines.domain import (  # noqa: E402
    CurrentPointer,
    LedgerEntry,
    RunManifest,
    RunRegistry,
    Scope,
)


@dataclass(frozen=True)
class Loaded[T]:
    """Result of a disk load. ``value`` is None exactly when ``error`` is set."""

    value: T | None = None
    error: str | None = None


@dataclass(frozen=True)
class ManifestDoc:
    """A loaded run manifest.

    ``raw`` is always the parsed YAML mapping (the coherence engine performs its
    own tolerant shape checks against it, preserving its C0 behavior). ``model``
    is the validated kernel :class:`RunManifest` when the mapping satisfies it,
    else ``None`` — so a structurally-odd manifest still loads as ``raw``.
    """

    raw: dict[str, Any]
    model: RunManifest | None = None


def resolve_in_workspace(root: Path, rel: str) -> Path | None:
    """Resolve a UACP-root-relative path defensively, or None if it escapes /
    is unresolvable. Never raises."""
    try:
        resolved = _resolve_uacp_path(rel, root)
        resolved.relative_to(root)
        return resolved
    except Exception:
        return None


def _safe_load_yaml(path: Path) -> tuple[Any, str | None]:
    """Return (parsed, error). ``error`` is a human string when load failed."""
    try:
        if not path.exists():
            return None, f"file not found: {path}"
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return raw, None
    except Exception as exc:  # defensive: garbled YAML must not raise
        return None, f"{type(exc).__name__}: {exc}"


def load_manifest(workspace: Path, run_id: str) -> Loaded[ManifestDoc]:
    """Load ``state/runs/<run_id>.yaml``.

    On a missing/garbled file: ``error`` set, ``value`` None. On a parsed but
    non-mapping body: ``error`` set ("not a YAML mapping"). On a mapping: ``value``
    is a :class:`ManifestDoc` whose ``raw`` is the mapping and whose ``model`` is
    the validated :class:`RunManifest` when it validates, else None.
    """
    path = workspace / "state" / "runs" / f"{run_id}.yaml"
    raw, err = _safe_load_yaml(path)
    if err is not None:
        return Loaded(error=err)
    if not isinstance(raw, dict):
        return Loaded(error="run manifest is not a YAML mapping")
    model: RunManifest | None = None
    try:
        model = RunManifest.model_validate(raw)
    except Exception:
        model = None  # tolerate manifests the strict schema would reject
    return Loaded(value=ManifestDoc(raw=raw, model=model))


def load_ledger(workspace: Path, run_id: str) -> tuple[list[LedgerEntry], list[str]]:
    """Load the gate ledger ``state/gate-ledger/<run_id>.jsonl``.

    Returns ``(entries, errors)``. ``errors`` holds one human string per
    unreadable file or malformed line (the engine maps each to a violation).
    A missing ledger yields ``([], [])`` — its absence is the caller's concern.
    """
    path = workspace / "state" / "gate-ledger" / f"{run_id}.jsonl"
    entries: list[LedgerEntry] = []
    errors: list[str] = []
    if not path.exists():
        return entries, errors
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        return entries, [f"gate ledger unreadable: {type(exc).__name__}: {exc}"]
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception as exc:
            errors.append(f"gate ledger line {lineno} is not valid JSON: {exc}")
            continue
        if not isinstance(rec, dict):
            errors.append(f"gate ledger line {lineno} is not a JSON object")
            continue
        entries.append(LedgerEntry.model_validate(rec))
    return entries, errors


def load_current(workspace: Path) -> Loaded[CurrentPointer]:
    """Load the ``state/current.yaml`` active-run pointer.

    A missing file is reported via ``error`` (callers may treat it as benign).
    ``value`` is None when the body is missing, garbled, or not a mapping.
    """
    path = workspace / "state" / "current.yaml"
    raw, err = _safe_load_yaml(path)
    if err is not None:
        return Loaded(error=err)
    if not isinstance(raw, dict):
        return Loaded(error="state/current.yaml is not a YAML mapping")
    return Loaded(value=CurrentPointer.model_validate(raw))


def load_registry(workspace: Path) -> Loaded[RunRegistry]:
    """Load ``state/run-registry.yaml``. ``value`` None on missing/garbled/non-mapping."""
    path = workspace / "state" / "run-registry.yaml"
    raw, err = _safe_load_yaml(path)
    if err is not None:
        return Loaded(error=err)
    if not isinstance(raw, dict):
        return Loaded(error="state/run-registry.yaml is not a YAML mapping")
    return Loaded(value=RunRegistry.model_validate(raw))


def load_artifact(workspace: Path, rel: str) -> Loaded[dict[str, Any]]:
    """Load an arbitrary run-root-relative artifact as a parsed mapping.

    Used to read ``run_id`` (C1) and ``write_paths`` (C6) out of referenced
    artifacts. ``value`` is the parsed mapping; ``error`` is set when the path
    escapes the workspace, is missing, garbled, or is not a mapping.
    """
    apath = resolve_in_workspace(workspace, rel)
    if apath is None:
        return Loaded(error=f"path does not resolve inside the workspace: {rel!r}")
    raw, err = _safe_load_yaml(apath)
    if err is not None:
        return Loaded(error=err)
    if not isinstance(raw, dict):
        return Loaded(error="artifact is not a YAML mapping")
    return Loaded(value=raw)


def load_scope(workspace: Path, rel: str) -> Loaded[Scope]:
    """Load a ``uacp.scope`` artifact as a typed :class:`Scope` model."""
    loaded = load_artifact(workspace, rel)
    if loaded.error is not None or loaded.value is None:
        return Loaded(error=loaded.error or "scope artifact is not a mapping")
    return Loaded(value=Scope.model_validate(loaded.value))


def load_phase_transitions(workspace: Path) -> Loaded[dict[str, Any]]:
    """Load ``config/phase-transitions.yaml`` as a parsed mapping.

    Used by the evidence-completeness engine to read each phase's declared
    ``phase_exit_invariants``. ``value`` is the parsed mapping; ``error`` is set
    when the file is missing, garbled, or is not a mapping. Never raises.
    """
    path = workspace / "config" / "phase-transitions.yaml"
    raw, err = _safe_load_yaml(path)
    if err is not None:
        return Loaded(error=err)
    if not isinstance(raw, dict):
        return Loaded(error="config/phase-transitions.yaml is not a YAML mapping")
    return Loaded(value=raw)


def glob_in_workspace(workspace: Path, pattern: str) -> list[Path]:
    """Glob a workspace-relative pattern, returning only matches inside the root.

    Defensive: never raises. Patterns whose literal prefix escapes the workspace,
    or that cannot be globbed, yield ``[]``. Matches that resolve outside the
    workspace (e.g. via symlinks) are dropped.
    """
    try:
        root = workspace.resolve()
        matches: list[Path] = []
        for m in root.glob(pattern):
            try:
                m.resolve().relative_to(root)
            except Exception:
                continue
            matches.append(m)
        return matches
    except Exception:
        return []
