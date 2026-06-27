"""P6 — the swappable score() policy + the four heat-formula terms, isolated on the policy.

Each test holds every other signal at its neutral value and varies ONE input, asserting the
score moves the right direction by the right SHAPE (the exact formula, not just a sign). The
constants come from PolicyD so the tests pin the real arithmetic; break a term in the policy
and its test fails. The agreement-vs-conflict guard (never boost an unreconciled node) is
proven directly here and wired end-to-end in test_heat_formula.py.
"""

from __future__ import annotations

import math

import pytest

from codeflair.policy import PolicyD, ScorePolicy, ScoreSignals, default_policy, recency_factor

P = PolicyD()


def _base(**over: object) -> ScoreSignals:
    """A neutral signal (base weight 1.0, hop 0, recency 1, fan-in 1, no PMI, one probe) with
    selective overrides — so a single term can be isolated against a known baseline of 1.0."""
    defaults: dict[str, object] = dict(rel_weight=1.0, provenance_trust=1.0, hop=0)
    defaults.update(over)
    return ScoreSignals(**defaults)  # type: ignore[arg-type]


def test_policy_is_a_named_scorepolicy():
    assert P.name == "policy-d"
    assert isinstance(P, ScorePolicy)  # runtime-checkable structural type
    assert default_policy() is default_policy()  # one shared default instance (OD-3 seam)


def test_neutral_signal_is_the_bare_base_weight():
    # all four terms neutral -> heat == base_weight (the precision-ladder weight), unchanged.
    assert P.score(_base()) == pytest.approx(1.0)
    assert P.score(_base(rel_weight=0.8, provenance_trust=0.5, hop=1)) == pytest.approx(
        0.8 * 0.5 * 0.5
    )


# --------------------------------------------------------------------------- #
# Term 1 — recency_factor: more-recently-changed scores higher
# --------------------------------------------------------------------------- #


def test_recency_helper_shape_and_neutral_fallbacks():
    # half-life decay: age 0 -> 1.0, age == half_life -> 0.5, older -> smaller.
    assert recency_factor(100, 100, half_life=30) == pytest.approx(1.0)
    assert recency_factor(70, 100, half_life=30) == pytest.approx(0.5)
    assert recency_factor(40, 100, half_life=30) == pytest.approx(0.25)
    # neutral (1.0) when the reference point or the change ordinal is unknown -> no effect.
    assert recency_factor(100, None) == 1.0
    assert recency_factor(0, 100) == 1.0
    # a future/0-age change is not boosted above 1.0 (bounded at the maximum).
    assert recency_factor(150, 100, half_life=30) == 1.0


def test_more_recent_node_scores_higher():
    recent = P.score(_base(recency_factor=1.0))
    old = P.score(_base(recency_factor=0.25))
    assert recent > old
    assert old == pytest.approx(0.25)  # multiplicative: base 1.0 × recency 0.25


# --------------------------------------------------------------------------- #
# Term 2 — fan-in penalty ÷ (1 + w·log(fan_in)): doubling fan-in lowers the score
# --------------------------------------------------------------------------- #


def test_fan_in_one_is_neutral():
    assert P.score(_base(fan_in=1)) == pytest.approx(1.0)  # log(1) = 0 -> no penalty
    assert P.score(_base(fan_in=0)) == pytest.approx(1.0)  # clamped to 1


def test_doubling_fan_in_reduces_score_per_one_plus_log():
    s4 = P.score(_base(fan_in=4))
    s8 = P.score(_base(fan_in=8))
    assert s8 < s4
    # exact shape: base 1.0 ÷ (1 + w_fanin·log(fan_in))
    assert s4 == pytest.approx(1.0 / (1.0 + P.w_fanin * math.log(4)))
    assert s8 == pytest.approx(1.0 / (1.0 + P.w_fanin * math.log(8)))


def test_huge_fan_in_is_strongly_penalised():
    # a ubiquitous util (fan-in 200) is down-weighted well below a focused node (fan-in 2).
    assert P.score(_base(fan_in=200)) < P.score(_base(fan_in=2))


# --------------------------------------------------------------------------- #
# Term 3 — co_change_PMI: higher temporal coupling scores higher (additive)
# --------------------------------------------------------------------------- #


def test_higher_pmi_scores_higher_additively():
    s0 = P.score(_base(co_change_pmi=0.0))
    s1 = P.score(_base(co_change_pmi=1.0))
    s2 = P.score(_base(co_change_pmi=2.0))
    assert s0 < s1 < s2
    # additive with weight w_cc: heat = base + w_cc·PMI
    assert s1 == pytest.approx(1.0 + P.w_cc * 1.0)
    assert s2 == pytest.approx(1.0 + P.w_cc * 2.0)


# --------------------------------------------------------------------------- #
# Term 4 — agreement_bonus: corroboration by multiple probes, NEVER on a conflict
# --------------------------------------------------------------------------- #


def test_more_probes_outrank_an_identical_single_probe_node():
    one = P.score(_base(probes_found=1))
    two = P.score(_base(probes_found=2))
    three = P.score(_base(probes_found=3))
    assert one < two < three
    # additive: agreement · (probes_found − 1)
    assert two - one == pytest.approx(P.agreement)
    assert three - one == pytest.approx(2 * P.agreement)


def test_agreement_bonus_is_zero_for_a_single_probe():
    assert P.agreement_bonus(1, conflicting=False) == 0.0
    assert P.agreement_bonus(0, conflicting=False) == 0.0  # never negative


def test_agreement_never_boosts_an_unreconciled_node():
    # the P2↔formula guard: a conflicting (SCIP↔overlay) node is surfaced, NEVER up-weighted.
    assert P.agreement_bonus(5, conflicting=True) == 0.0
    boosted = P.score(_base(probes_found=5, conflicting=False))
    conflicted = P.score(_base(probes_found=5, conflicting=True))
    assert conflicted < boosted
    assert conflicted == pytest.approx(P.score(_base(probes_found=1)))  # no bonus at all
