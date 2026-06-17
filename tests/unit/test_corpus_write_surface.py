import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_artifact_writer_can_reach_lessons_prefix():
    cfg = tomllib.loads((ROOT / "config" / "uacp.toml").read_text())
    caps = cfg["scope"]["tool_path_capabilities"]["uacp_artifact_write"]
    assert "lessons/" in caps
    assert "knowledge/" in caps  # unchanged


def test_artifact_writer_can_reach_brainstorm_prefix():
    """The brainstorm scope-package (brainstorm/<run_id>/07-scope-package.yaml) is
    written through uacp_artifact_write, so the brainstorm/ prefix must be reachable
    in the scope tool_path_capabilities (HIGH-2)."""
    cfg = tomllib.loads((ROOT / "config" / "uacp.toml").read_text())
    caps = cfg["scope"]["tool_path_capabilities"]["uacp_artifact_write"]
    assert "brainstorm/" in caps


def test_artifact_category_description_mentions_lessons():
    cfg = tomllib.loads((ROOT / "config" / "uacp.toml").read_text())
    desc = cfg["guardian"]["protected_categories"]["artifact.uacp"]["description"]
    assert "lessons/" in desc


def test_artifact_category_description_mentions_brainstorm():
    cfg = tomllib.loads((ROOT / "config" / "uacp.toml").read_text())
    desc = cfg["guardian"]["protected_categories"]["artifact.uacp"]["description"]
    assert "brainstorm/" in desc


def test_artifact_handler_allowed_roots_includes_lessons():
    """Direct unit-localized assertion: the in-code allowed_roots set in
    _handle_uacp_artifact_write admits 'lessons' (the Oracle corpus write surface).

    Reads the handler source rather than the config so a regression that drops
    'lessons' from the literal set is caught here, localized to the adapter code.
    """
    import re

    handler_src = (
        ROOT
        / "runtime-adapters"
        / "hermes"
        / "plugins"
        / "uacp_guardian"
        / "__init__.py"
    ).read_text()
    match = re.search(r"allowed_roots\s*=\s*\{([^}]*)\}", handler_src)
    assert match, "allowed_roots literal set not found in artifact-write handler"
    roots = {tok.strip().strip("\"'") for tok in match.group(1).split(",")}
    assert "lessons" in roots, f"'lessons' missing from allowed_roots: {roots}"
    assert "knowledge" in roots  # sibling corpus root, must remain


def test_artifact_handler_allowed_roots_includes_brainstorm():
    """Direct unit-localized assertion: the in-code allowed_roots set in
    _handle_uacp_artifact_write admits 'brainstorm' so the brainstorm scope-package
    can be written through the governed writer (HIGH-2). Reads the handler source so
    a regression that drops 'brainstorm' from the literal set is caught here."""
    import re

    handler_src = (
        ROOT
        / "runtime-adapters"
        / "hermes"
        / "plugins"
        / "uacp_guardian"
        / "__init__.py"
    ).read_text()
    match = re.search(r"allowed_roots\s*=\s*\{([^}]*)\}", handler_src)
    assert match, "allowed_roots literal set not found in artifact-write handler"
    roots = {tok.strip().strip("\"'") for tok in match.group(1).split(",")}
    assert "brainstorm" in roots, f"'brainstorm' missing from allowed_roots: {roots}"
