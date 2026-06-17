"""Tests for oracle.packets ProviderPacket and TrustClass."""
from __future__ import annotations


from engines.oracle.packets import ProviderPacket, TrustClass


def test_trust_class_values():
    assert TrustClass.authoritative.value == "authoritative"
    assert TrustClass.normative.value == "normative"
    assert TrustClass.advisory.value == "advisory"


def test_advisory_packet_sets_evidence_required_true():
    p = ProviderPacket(
        source="test",
        trust_class=TrustClass.advisory,
        payload="some text",
        evidence_required=False,  # should be overridden to True
    )
    assert p.evidence_required is True


def test_authoritative_packet_respects_caller_evidence_required_false():
    p = ProviderPacket(
        source="test",
        trust_class=TrustClass.authoritative,
        payload="some text",
        evidence_required=False,
    )
    assert p.evidence_required is False


def test_authoritative_packet_respects_caller_evidence_required_true():
    p = ProviderPacket(
        source="test",
        trust_class=TrustClass.authoritative,
        payload="some text",
        evidence_required=True,
    )
    assert p.evidence_required is True


def test_normative_packet_respects_caller_evidence_required():
    p = ProviderPacket(
        source="test",
        trust_class=TrustClass.normative,
        payload="some text",
        evidence_required=True,
    )
    assert p.evidence_required is True


def test_default_score_is_zero():
    p = ProviderPacket(source="s", trust_class=TrustClass.advisory, payload="x")
    assert p.score == 0.0


def test_default_metadata_is_empty_dict():
    p = ProviderPacket(source="s", trust_class=TrustClass.advisory, payload="x")
    assert p.metadata == {}
