"""ProviderPacket and TrustClass — normalized source output for the Oracle engine.

Every retrieval source produces ProviderPacket instances. The trust_class drives
how the aggregator and skill consumers should treat the payload:
  authoritative — UACP run state, policy; treat as ground truth
  normative     — advisory prior-art that shapes reasoning but requires corroboration
  advisory      — context from heuristic or external sources; informational only
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TrustClass(StrEnum):
    authoritative = "authoritative"
    normative = "normative"
    advisory = "advisory"


@dataclass
class ProviderPacket:
    """A single result from a retrieval source.

    Attributes:
        source: identifier of the source (e.g. "runstate", "honcho", "corpus")
        trust_class: how much weight this packet should carry
        payload: the retrieved content (string or mapping)
        score: relevance score [0.0, 1.0], 0.0 when scoring not available
        evidence_required: when True, callers must corroborate before treating as proof
        metadata: optional extra context (source-specific)
    """
    source: str
    trust_class: TrustClass
    payload: str | dict
    score: float = 0.0
    evidence_required: bool = False
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # advisory packets always require evidence corroboration
        if self.trust_class == TrustClass.advisory:
            self.evidence_required = True
        # authoritative and normative respect caller's value as-is
