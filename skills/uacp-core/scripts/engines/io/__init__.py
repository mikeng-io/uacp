"""Filesystem layer for the UACP engines — the ONLY place that touches disk.

Every ``yaml.safe_load`` / file read / disk ``try``/``except`` for the engines
lives here. Loaders NEVER raise: a missing or garbled file is returned as a
:class:`Loaded` whose ``value`` is ``None`` and whose ``error`` carries a human
string, so the calling engine can convert it into the right ``Violation`` rather
than crashing. Domain and engine layers do no raw file I/O.
"""

from __future__ import annotations

from .forecastio import (
    forecast_record_path,
    load_forecast_record,
    write_forecast_record,
)
from .gitio import GitDiffResult, changed_files
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
    load_text_under_root,
    load_yaml_under_root,
    resolve_in_workspace,
)
from .witnessio import (
    BaselineFacts,
    WitnessFacts,
    WitnessResult,
    clear_witness_memo,
    derive_baseline_neighborhood,
    derive_witness,
)

__all__ = [
    "BaselineFacts",
    "GitDiffResult",
    "Loaded",
    "WitnessFacts",
    "WitnessResult",
    "changed_files",
    "clear_witness_memo",
    "derive_baseline_neighborhood",
    "derive_witness",
    "forecast_record_path",
    "glob_in_workspace",
    "load_forecast_record",
    "write_forecast_record",
    "load_artifact",
    "load_checkpoint_manifest",
    "load_convergence_budget",
    "load_current",
    "load_ledger",
    "load_manifest",
    "load_phase_transitions",
    "load_registry",
    "load_scope",
    "load_text_under_root",
    "load_yaml_under_root",
    "resolve_in_workspace",
]
