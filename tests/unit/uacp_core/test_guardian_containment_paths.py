"""C-1 HIGH: Guardian state containment + shell scanner target .uacp/, not flat state/."""
from core import Guardian, GuardianPolicy, make_event


def _guardian(root):
    return Guardian(GuardianPolicy.load(str(root)))


def test_under_state_targets_uacp_state(temp_uacp_root):
    g = _guardian(temp_uacp_root)
    # Path under .uacp/state IS contained; the flat state/ path is NOT.
    assert g._path_is_under_state(str(temp_uacp_root / ".uacp" / "state" / "runs" / "r1.yaml")) is True
    assert g._path_is_under_state(str(temp_uacp_root / "state" / "runs" / "r1.yaml")) is False


def test_scanner_catches_uacp_relative_write(temp_uacp_root):
    g = _guardian(temp_uacp_root)
    # A shell command writing `.uacp/state/x` (relative to UACP_ROOT) must be
    # collected as a candidate path that resolves under the root.
    event = make_event(tool_name="Bash", args={"command": "touch .uacp/state/evil.yaml"})
    paths = g._extract_paths(event)
    assert any(".uacp/state/evil.yaml" in p or p.endswith("/.uacp/state/evil.yaml") for p in paths), paths
