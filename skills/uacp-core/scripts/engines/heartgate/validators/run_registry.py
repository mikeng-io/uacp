"""Run-registry write-path overlap gate (A3.6 extraction from the Heartgate god-class).

Detects write-path overlap between the active run and other active runs at the
PLAN->EXECUTE transition (reads state/run-registry.yaml). Carved out of the
``Heartgate`` god-class (design/graph-engine nodes 30/31, seam #7) as free
functions; the path canonicalization / overlap helpers are module-private (no
caller outside this gate). node 31 notes this gate MAY later move to the State
engine (it reads run-registry state) — kept under validators/ for now. The hub
keeps thin delegating methods for ``_run_registry_rule`` (a unit test drives it)
and ``_validate_run_registry_overlap`` (the orchestrator). Behaviour is preserved
verbatim (blocker strings byte-identical); only the gate-instance plumbing changed
(self -> hg, cls._canon_write_path -> the module function).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

from config import get_config
from engines.domain.gate_rules import run_registry_rule_default

from .helpers import _is_safe_run_id

if TYPE_CHECKING:
    from ..heartgate import Heartgate

try:
    import yaml
except ImportError:  # pragma: no cover - Hermes ships with PyYAML in normal use.
    yaml = None  # type: ignore[assignment]


def _canon_write_path(p: Any) -> str:
    """SKEP-003 / TECH-002 remediation: canonicalize a write_path entry
    into a POSIX-segment-normalized form ending with '/'. Strips leading
    './' and '/', collapses repeated separators, rejects '..' segments.
    Returns empty string when the entry is unusable.
    """
    s = str(p).strip()
    if not s:
        return ""
    # Reject absolute paths and parent-escape; both are policy violations.
    if s.startswith("/") or s in {".", ".."}:
        return ""
    try:
        pp = PurePosixPath(s)
    except Exception:
        return ""
    parts = [seg for seg in pp.parts if seg not in (".",)]
    if any(seg == ".." for seg in parts):
        return ""
    norm = "/".join(parts)
    if not norm:
        return ""
    return norm + "/"


def _paths_overlap(a_raw: Any, b_raw: Any) -> bool:
    """SKEP-003: two write_paths overlap iff one is an ancestor of the
    other after canonicalization. Bare-prefix tricks ('plans' vs
    'plans-other') no longer match; './plans/' and 'plans/' canonicalize
    to the same value.
    """
    a = _canon_write_path(a_raw)
    b = _canon_write_path(b_raw)
    if not a or not b:
        return False
    return a == b or a.startswith(b) or b.startswith(a)


def run_registry_rule(hg: Heartgate) -> Mapping[str, Any]:
    """Resolve the run_registry_rule.

    Slice 4b T4c-1: the rule grammar (registry_path, required_for_transition,
    writer_tool) is codified in engines.domain.gate_rules. The block is read
    from the loaded phase-transitions config WHEN PRESENT (production
    behavior, unchanged); when ABSENT it falls back to the code default whose
    operator-tunable ``enforcement`` mode comes from config/uacp.toml
    [heartgate.run_registry]. A fixture may opt out via an empty mapping.
    """
    if "run_registry_rule" in hg.config:
        return hg.config.get("run_registry_rule") or {}

    enforcement = None
    try:
        cfg_raw = get_config(hg.uacp_root).model_dump()
        knob = (cfg_raw.get("heartgate") or {}).get("run_registry") or {}
        if isinstance(knob, Mapping):
            value = knob.get("enforcement")
            enforcement = value if isinstance(value, str) else None
    except Exception:
        enforcement = None
    return run_registry_rule_default(enforcement=enforcement)


def validate_run_registry_overlap(
    hg: Heartgate, artifact: Mapping[str, Any], blockers: list[str], warnings: list[str]
) -> None:
    """Phase 3.2: detect write-path overlap with other active runs.

    Reads state/run-registry.yaml; for each entry in active_runs whose
    run_id != this artifact's run_id, compute path intersection. Any
    overlap with the active scope.write_paths blocks PLAN->EXECUTE.

    Phase 3 R1 hardening: malformed registry entries now block
    (SKEP-010), path normalization uses PurePosixPath segment match
    (SKEP-003), and the required transition is read from config
    (TECH-003).
    """
    rule = run_registry_rule(hg)
    if not isinstance(rule, Mapping) or not rule:
        return
    from_phase = str(artifact.get("from_phase") or "")
    to_phase = str(artifact.get("to_phase") or "")
    required_for = str(rule.get("required_for_transition") or "plan->execute")
    if f"{from_phase}->{to_phase}" != required_for:
        return
    run_id = str(artifact.get("run_id") or "")
    if not _is_safe_run_id(run_id):
        return
    registry_rel = str(rule.get("registry_path") or "state/run-registry.yaml")
    registry_path = hg.governed_root / registry_rel
    if not registry_path.exists():
        # No registry yet — emit a warning so it is observable but do not
        # block; runs that pre-date the registry must not be blocked
        # retroactively. Once at least one run has registered, overlap
        # detection is active for all subsequent transitions.
        warnings.append("run_registry: state/run-registry.yaml not yet present")
        return
    if yaml is None:
        blockers.append("run_registry: PyYAML required to validate registry")
        return
    try:
        data = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        blockers.append(f"run_registry: registry unparseable: {type(exc).__name__}")
        return
    if not isinstance(data, Mapping):
        blockers.append("run_registry: top-level value must be a YAML mapping")
        return
    active = data.get("active_runs", [])
    if active is None:
        active = []
    if not isinstance(active, list):
        blockers.append("run_registry: 'active_runs' must be a list")
        return
    # Load the active run's scope to extract its write_paths.
    scope_path = hg.governed_root / "plans" / f"{run_id}-scope.yaml"
    if not scope_path.exists():
        return  # scope_artifact validator handles missing-scope blockers
    try:
        scope = yaml.safe_load(scope_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        blockers.append(f"run_registry: scope unparseable for overlap check: {type(exc).__name__}")
        return
    my_writes = scope.get("write_paths") or []
    if not isinstance(my_writes, list):
        blockers.append("run_registry: scope.write_paths must be a list for overlap check")
        return
    for idx, entry in enumerate(active):
        if not isinstance(entry, Mapping):
            blockers.append(f"run_registry: active_runs[{idx}] must be a mapping")
            continue
        other_id = str(entry.get("run_id") or "")
        if other_id == run_id:
            continue
        if not other_id or not _is_safe_run_id(other_id):
            blockers.append(f"run_registry: active_runs[{idx}].run_id missing or unsafe")
            continue
        other_writes = entry.get("write_paths") or []
        if not isinstance(other_writes, list):
            blockers.append(f"run_registry: active_runs[{idx}].write_paths must be a list")
            continue
        for a in my_writes:
            for b in other_writes:
                if _paths_overlap(a, b):
                    ac = _canon_write_path(a) or str(a)
                    bc = _canon_write_path(b) or str(b)
                    blockers.append(
                        f"run_registry: write_paths overlap with active run '{other_id}' "
                        f"on '{ac}' / '{bc}'"
                    )
