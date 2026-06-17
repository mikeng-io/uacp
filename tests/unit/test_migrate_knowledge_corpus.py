import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import migrate_knowledge_corpus as mig  # noqa: E402


def _legacy(tmp_path):
    (tmp_path / "knowledge" / "lessons").mkdir(parents=True)
    (tmp_path / "knowledge" / "lessons" / "old.yaml").write_text("kind: uacp.lesson\n")
    (tmp_path / "knowledge" / "topic.md").write_text("# legacy knowledge\n")
    # Two pre-OKF root-level lesson files (real repo pattern — FIX 1)
    (tmp_path / "knowledge" / "phase5-kanban-guard-resolve-lessons-20260514.md").write_text(
        "# phase 5 lessons\n"
    )
    (tmp_path / "knowledge" / "phase6-agent-council-operationalization-lessons-20260515.md").write_text(
        "# phase 6 lessons\n"
    )
    # Preserved subdirectories — NOT moved (FIX 5)
    (tmp_path / "knowledge" / "scenarios").mkdir()
    (tmp_path / "knowledge" / "gate-templates").mkdir()


def test_moves_lessons_and_knowledge_under_uacp(tmp_path):
    _legacy(tmp_path)
    mig.migrate(tmp_path)
    assert (tmp_path / ".uacp" / "lessons" / "old.yaml").exists()
    assert (tmp_path / ".uacp" / "knowledge" / "topic.md").exists()


def test_root_level_lesson_files_land_in_lessons_not_knowledge(tmp_path):
    """FIX 1: root-level *-lessons*.md files must go to .uacp/lessons/, not .uacp/knowledge/."""
    _legacy(tmp_path)
    mig.migrate(tmp_path)
    assert (tmp_path / ".uacp" / "lessons" / "phase5-kanban-guard-resolve-lessons-20260514.md").exists()
    assert (tmp_path / ".uacp" / "lessons" / "phase6-agent-council-operationalization-lessons-20260515.md").exists()
    # Must NOT appear in knowledge/
    assert not (tmp_path / ".uacp" / "knowledge" / "phase5-kanban-guard-resolve-lessons-20260514.md").exists()
    assert not (tmp_path / ".uacp" / "knowledge" / "phase6-agent-council-operationalization-lessons-20260515.md").exists()


def test_scenarios_and_gate_templates_not_moved(tmp_path):
    """FIX 5: scenarios/ and gate-templates/ stay at knowledge/ (config still points there)."""
    _legacy(tmp_path)
    mig.migrate(tmp_path)
    assert (tmp_path / "knowledge" / "scenarios").exists()
    assert (tmp_path / "knowledge" / "gate-templates").exists()
    assert not (tmp_path / ".uacp" / "knowledge" / "scenarios").exists()


def test_idempotent(tmp_path):
    _legacy(tmp_path)
    mig.migrate(tmp_path)
    mig.migrate(tmp_path)  # must not raise
    assert (tmp_path / ".uacp" / "lessons" / "old.yaml").exists()


def test_creates_indexes_dir(tmp_path):
    _legacy(tmp_path)
    mig.migrate(tmp_path)
    assert (tmp_path / ".uacp" / "knowledge" / "indexes").is_dir()
