"""Filesystem layer for the UACP engines — the ONLY place that touches disk.

Every ``yaml.safe_load`` / file read / disk ``try``/``except`` for the engines
lives here. Loaders NEVER raise: a missing or garbled file is returned as a
:class:`Loaded` whose ``value`` is ``None`` and whose ``error`` carries a human
string, so the calling engine can convert it into the right ``Violation`` rather
than crashing. Domain and engine layers do no raw file I/O.
"""

from __future__ import annotations

from .loaders import (
    Loaded,
    glob_in_workspace,
    load_artifact,
    load_checkpoint_manifest,
    load_convergence_budget,
    load_current,
    load_ledger,
    load_manifest,
    load_phase_transitions,
    load_registry,
    load_scope,
    load_yaml_under_root,
    resolve_in_workspace,
)

__all__ = [
    "Loaded",
    "glob_in_workspace",
    "load_artifact",
    "load_checkpoint_manifest",
    "load_convergence_budget",
    "load_current",
    "load_ledger",
    "load_manifest",
    "load_phase_transitions",
    "load_registry",
    "load_scope",
    "load_yaml_under_root",
    "resolve_in_workspace",
]
