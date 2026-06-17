import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_artifact_writer_can_reach_lessons_prefix():
    cfg = tomllib.loads((ROOT / "config" / "uacp.toml").read_text())
    caps = cfg["scope"]["tool_path_capabilities"]["uacp_artifact_write"]
    assert "lessons/" in caps
    assert "knowledge/" in caps  # unchanged


def test_artifact_category_description_mentions_lessons():
    cfg = tomllib.loads((ROOT / "config" / "uacp.toml").read_text())
    desc = cfg["guardian"]["protected_categories"]["artifact.uacp"]["description"]
    assert "lessons/" in desc
