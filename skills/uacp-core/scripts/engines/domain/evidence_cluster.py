"""Read-model for ``uacp.evidence_cluster`` artifacts.

Codified from ``config/evidence-clusters.yaml`` (Slice 4a).
``cluster_states`` and ``artifact_schema`` field grammar are represented here;
``universal_cluster_families``, ``evidence_domain_registry``, and
``example_artifact`` remain as doctrine in the YAML.

``ClusterState`` covers the 5-value enum:
  pass | warn | block | not_applicable | deferred

``ClusterPhase`` covers the 6-phase lifecycle enum.

``EvidenceCluster`` is a read-model with extra="allow" so engines can operate
on partially-formed or forward-extended artifacts without crashing.  Required
fields are those from artifact_schema.required_fields that the validators
enforce: cluster_id, phase, family, purpose, state, findings.

``INVARIANT_CLUSTER_FAMILIES`` is the frozenset of the 6 families whose
``invariant: true`` flag appears in ``universal_cluster_families`` (do NOT
conflate with gate-selection's 7 ``non_waivable_invariants`` — a different set).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Enums (codified from artifact_schema.fields.state.values and phase values)
# ---------------------------------------------------------------------------

ClusterState = Literal["pass", "warn", "block", "not_applicable", "deferred"]

ClusterPhase = Literal["triage", "propose", "plan", "execute", "verify", "resolve"]

# ---------------------------------------------------------------------------
# INVARIANT_CLUSTER_FAMILIES — the 6 families with invariant: true in the YAML
# ---------------------------------------------------------------------------

INVARIANT_CLUSTER_FAMILIES: frozenset[str] = frozenset(
    {
        "authority",
        "side_effects",
        "write_containment",
        "privacy_safety",
        "traceable_state",
        "conservative_failure",
    }
)

# ---------------------------------------------------------------------------
# EvidenceCluster model
# ---------------------------------------------------------------------------


class EvidenceCluster(BaseModel):
    """Read-model for a ``uacp.evidence_cluster`` artifact.

    Required fields are ``cluster_id``, ``phase``, ``family``, ``purpose``,
    ``state``, and ``findings`` — matching the validator's enforced subset of
    ``artifact_schema.required_fields``.  All other fields (trigger_conditions,
    required_inputs, allowed_tools, output_artifact_path, decision_rules,
    concurrency, dependencies, …) are tolerated via ``extra="allow"``.
    """

    model_config = ConfigDict(extra="allow")

    cluster_id: str
    phase: ClusterPhase
    family: str
    purpose: str
    state: ClusterState
    findings: list[Any]
