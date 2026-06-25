"""The required-kinds FLOOR policy (capsule #3 slice 2 / design node 34 Layer 2).

Maps a target's declared CLASS -> the check kind(s) it must carry, so a weak-but-present check
(e.g. ``field_present`` on a "wire up the /settle route" work_unit) cannot satisfy a target whose
class demands a stronger kind. This is the deterministic half of "a 'wires up X' claim needs a
*resolution* check, not 'a file exists'".

Doctrine home: shipped as the code DEFAULT here AND as ``config/verification-floor.yaml`` (the
doctrine YAML node 34 names). The YAML is authoritative WHEN present + well-formed (wholesale
override, matching the loaded-config-overrides / code-default-when-absent convention); a missing or
garbled YAML falls back to this default — **fail-CLOSED**, never fail-open the floor.

Honest edge (node 32): ``wires_symbol``/``changes_behavior`` require the code/behavior-plane kinds
(``symbol_resolves``/``behavioral``) NOT yet in the catalog (slice 3), so a target of those
classes can carry no satisfying check and BLOCKS until that plane is wired — by design, refusing to
let such work close on a weak proxy meanwhile.
"""

from __future__ import annotations

from pathlib import Path

import yaml

# class -> the check kind(s); the target must carry AT LEAST ONE of them.
_DEFAULT_FLOOR: dict[str, tuple[str, ...]] = {
    "wires_symbol": ("uacp.check.symbol_resolves",),
    "sets_value": ("uacp.check.field_equals",),
    "ensures_obligation": ("uacp.check.obligation_satisfied",),
    "changes_behavior": ("uacp.check.behavioral",),
}

# The closed class vocabulary (the floor keys). Used by the schema enum + Layer 2b.
CLASSES: tuple[str, ...] = tuple(_DEFAULT_FLOOR)

# --- Layer 2b: content ENTAILMENT (design node 34) --------------------------------------------
# The floor (above) keys off the AGENT-declared class, so a mis-classifier can declare a weak class
# (sets_value) for a strong-class target (wires_symbol) and satisfy the floor with a weak kind. 2b
# shrinks that surface DETERMINISTICALLY but PARTIALLY: derive a CANDIDATE class from the target's
# OWN intent/statement text; if the declared class is WEAKER than the content implies, the agent
# under-classified — emit CHK_CLASS_UNDERCLAIM. This forces a mis-classifier to also corrupt the
# intent text (which the council reads + other gates consume), not just a private label. It does NOT
# make class honesty deterministic — only the code plane (class entailed from the real symbol) does.
#
# STRENGTH RANK (higher demands a stronger check). The critical boundary is WEAK (sets_value/
# ensures_obligation — satisfiable now) vs STRONG (wires_symbol/changes_behavior — code/behavior
# plane, block-until-wired): declaring a weak class for strong content is the dodge 2b catches.
_CLASS_RANK: dict[str, int] = {
    "sets_value": 1,
    "ensures_obligation": 2,
    "wires_symbol": 3,
    "changes_behavior": 4,
}

# CONSERVATIVE keyword map (distinctive tokens only) — a false CHK_CLASS_UNDERCLAIM is a false
# BLOCK, so under-match (miss) over over-match (false-fire); Layer 3 (council) owns the residual.
_CLASS_KEYWORDS: dict[str, tuple[str, ...]] = {
    "changes_behavior": ("behavior", "behaviour", "side effect", "side-effect"),
    "wires_symbol": ("wire", "mount", "register", "route", "endpoint", "expose"),
    "ensures_obligation": ("ensure", "guarantee", "enforce", "obligation"),
    "sets_value": ("configure", "assign", "default to", "set value"),
}


def class_rank(cls: str | None) -> int:
    """Strength rank of a class (0 for None/unknown — an undeclared class is the weakest)."""
    return _CLASS_RANK.get(cls or "", 0)


def candidate_class(text: str | None) -> tuple[str | None, str]:
    """The STRONGEST class whose keyword appears in ``text`` (case-insensitive), with the matched
    keyword; ``(None, "")`` if none matches. Strongest-first so the most demanding signal wins."""
    low = (text or "").lower()
    for cls in sorted(_CLASS_KEYWORDS, key=lambda c: -_CLASS_RANK[c]):
        for kw in _CLASS_KEYWORDS[cls]:
            if kw in low:
                return cls, kw
    return None, ""


def default_floor() -> dict[str, tuple[str, ...]]:
    return dict(_DEFAULT_FLOOR)


def load_floor(workspace: str | Path) -> dict[str, tuple[str, ...]]:
    """The class->required-kinds floor for ``workspace``: ``config/verification-floor.yaml``'s
    ``target_class_floor`` when present + well-formed, else the shipped default (fail-closed).
    Never raises."""
    path = Path(str(workspace)) / "config" / "verification-floor.yaml"
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return default_floor()
    table = raw.get("target_class_floor") if isinstance(raw, dict) else None
    if not isinstance(table, dict):
        return default_floor()
    out: dict[str, tuple[str, ...]] = {}
    for cls, kinds in table.items():
        if isinstance(cls, str) and isinstance(kinds, list):
            out[cls] = tuple(str(k) for k in kinds if isinstance(k, str))
    return out or default_floor()
