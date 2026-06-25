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
