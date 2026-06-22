"""Heartgate transition-coherence checks (self-attested evidence) (A3.4 extraction).

Carved out of the Heartgate god-class (design/graph-engine nodes 30/31, seam #7)
as free functions taking the gate instance (hg); the hub keeps thin delegating
methods. Each body is AST-identical to the original method (only self -> hg).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from config import get_config

if TYPE_CHECKING:
    from ..heartgate import Heartgate


def validate_heartgate_coherence(
    hg: Heartgate, artifact: Mapping[str, Any], blockers: list[str], warnings: list[str]
) -> None:
    """Validate optional Heartgate transition-coherence evidence.

    SUPERSEDED: this is the original SELF-ATTESTED coherence check — it
    trusts an agent-supplied ``heartgate_coherence.status`` flag. The
    authoritative coherence judgement is now produced by the COMPUTED
    ``coherence`` engine run via :meth:`validate_closure`, which inspects the
    run's emitted state directly rather than trusting a declared status.

    This method is retained for back-compat (existing transition artifacts
    may still carry a ``heartgate_coherence`` block), but the self-attested
    ``status`` field is advisory only; the computed engine is the source of
    truth for coherence at closure. Do not extend this self-attested path —
    add coherence checks to the computed engine instead.
    """
    coherence = artifact.get("heartgate_coherence")
    if coherence in (None, ""):
        return
    if not isinstance(coherence, Mapping):
        blockers.append("heartgate_coherence must be a mapping")
        return
    status = str(coherence.get("status") or "")
    if status not in {"pass", "warn", "block"}:
        blockers.append("heartgate_coherence.status must be pass, warn, or block")
    if status == "block":
        blockers.append("heartgate coherence blocks transition")
    artifact_path = str(coherence.get("artifact_path") or "")
    if not artifact_path:
        blockers.append("heartgate_coherence requires artifact_path")
    elif not hg._artifact_path_exists(artifact_path):
        blockers.append(f"heartgate_coherence artifact not found: {artifact_path}")
    required_lenses = {
        "doctrine_coherence",
        "cross_artifact_consistency",
        "runtime_state_alignment",
        "warning_and_deferred_item_honesty",
        "authority_plane_integrity",
        "next_phase_readiness",
    }
    lenses = coherence.get("lenses") or []
    if not isinstance(lenses, list):
        blockers.append("heartgate_coherence.lenses must be a list")
    else:
        missing = sorted(required_lenses - {str(item) for item in lenses})
        if missing:
            blockers.append("heartgate_coherence missing lens(es): " + ", ".join(missing))
    if status == "warn":
        warnings.append("heartgate coherence passed with warnings")


def heartgate_coherence_rule(hg: Heartgate) -> Mapping[str, Any]:
    """Resolve the heartgate_coherence_required_when rule.

    Slice 4b T4c-1: the structural grammar (required_field/required_lenses)
    and the selection policy (threshold + phases/routing/domains) are codified
    in engines.domain.gate_rules. The block is read from the loaded
    phase-transitions config WHEN PRESENT (production behavior, unchanged);
    when ABSENT it falls back to the code default, whose operator-tunable
    threshold + selectors come from config/uacp.toml [heartgate.coherence].

    A test fixture may opt OUT by supplying an empty mapping for the block
    (preserving prior test laxity): an explicit ``{}`` is honored as
    "rule present but empty" and disables the gate, exactly as before.
    """
    if "heartgate_coherence_required_when" in hg.config:
        return hg.config.get("heartgate_coherence_required_when") or {}
    from engines.domain.gate_rules import heartgate_coherence_required_when_default

    coherence_knob: Mapping[str, Any] = {}
    try:
        cfg_raw = get_config(hg.uacp_root).model_dump()
        coherence_knob = ((cfg_raw.get("heartgate") or {}).get("coherence")) or {}
    except Exception:
        coherence_knob = {}
    if not isinstance(coherence_knob, Mapping):
        coherence_knob = {}
    threshold = coherence_knob.get("min_composite_granularity")
    return heartgate_coherence_required_when_default(
        min_composite_granularity=threshold if isinstance(threshold, int) else None,
        selectors=dict(coherence_knob),
    )


def validate_heartgate_coherence_requirement(
    hg: Heartgate, artifact: Mapping[str, Any], blockers: list[str]
) -> None:
    rule = hg._heartgate_coherence_rule()
    if not rule:
        return
    coherence = artifact.get("heartgate_coherence")
    if coherence not in (None, ""):
        return
    reasons = []
    min_granularity = rule.get("min_composite_granularity")
    if min_granularity is not None:
        try:
            if int(artifact.get("composite_granularity") or 0) >= int(min_granularity):
                reasons.append(f"composite_granularity>={min_granularity}")
        except Exception:
            pass
    phases = set(str(x) for x in (rule.get("phases") or []))
    if phases and str(artifact.get("from_phase") or "") in phases:
        reasons.append("phase=" + str(artifact.get("from_phase") or ""))
    routing = set(str(x) for x in (rule.get("routing_outcomes") or []))
    if routing and str(artifact.get("routing_outcome") or "") in routing:
        reasons.append("routing_outcome=" + str(artifact.get("routing_outcome") or ""))
    categories = set(str(x) for x in (rule.get("domains") or []))
    artifact_domains = {str(x) for x in (artifact.get("domains") or [])}
    if categories and categories.intersection(artifact_domains):
        reasons.append("domain=" + ",".join(sorted(categories.intersection(artifact_domains))))
    if reasons:
        blockers.append("heartgate_coherence required by transition policy: " + "; ".join(reasons))
