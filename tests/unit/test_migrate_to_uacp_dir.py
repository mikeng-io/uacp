"""Migrate an OLD flat repo layout to .uacp/, rewriting in-flight YAML refs (C-2)."""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import migrate_to_uacp_dir as mig  # noqa: E402


def _old_repo(tmp_path):
    (tmp_path / "state" / "runs").mkdir(parents=True)
    (tmp_path / "state" / "gate-ledger").mkdir(parents=True)
    (tmp_path / ".outputs").mkdir(parents=True)
    (tmp_path / "proposals").mkdir(parents=True)
    (tmp_path / "plans").mkdir(parents=True)
    (tmp_path / "verification").mkdir(parents=True)
    (tmp_path / "knowledge").mkdir(parents=True)
    (tmp_path / "state" / "runs" / "r1.yaml").write_text(yaml.safe_dump({
        "run_id": "r1",
        "artifacts": {"closure": ".outputs/r1-closure.yaml",
                      "intent": "proposals/r1-intent.md"},
    }))
    (tmp_path / "state" / "gate-ledger" / "r1.jsonl").write_text(
        '{"gate": "g", "run_id": "r1", "artifact_path": ".outputs/r1-closure.yaml"}\n'
    )
    (tmp_path / ".outputs" / "r1-closure.yaml").write_text("kind: uacp.resolve_closure\n")


def test_moves_dirs_under_uacp(tmp_path):
    _old_repo(tmp_path)
    mig.migrate(tmp_path)
    assert (tmp_path / ".uacp" / "state" / "runs" / "r1.yaml").exists()
    assert (tmp_path / ".uacp" / "resolutions" / "r1-closure.yaml").exists()
    assert (tmp_path / ".uacp" / "proposals").is_dir()
    assert not (tmp_path / "state").exists()
    assert not (tmp_path / ".outputs").exists()


def test_rewrites_outputs_token_in_yaml(tmp_path):
    _old_repo(tmp_path)
    mig.migrate(tmp_path)
    manifest = yaml.safe_load((tmp_path / ".uacp" / "state" / "runs" / "r1.yaml").read_text())
    assert manifest["artifacts"]["closure"] == "resolutions/r1-closure.yaml"
    assert manifest["artifacts"]["intent"] == "proposals/r1-intent.md"  # untouched
    ledger = (tmp_path / ".uacp" / "state" / "gate-ledger" / "r1.jsonl").read_text()
    assert "resolutions/r1-closure.yaml" in ledger
    assert ".outputs/" not in ledger


def test_idempotent_second_run_is_noop(tmp_path):
    _old_repo(tmp_path)
    mig.migrate(tmp_path)
    mig.migrate(tmp_path)  # must not raise
    assert (tmp_path / ".uacp" / "state" / "runs" / "r1.yaml").exists()


def test_emits_starter_config(tmp_path):
    _old_repo(tmp_path)
    mig.migrate(tmp_path)
    assert (tmp_path / ".uacp" / "config.toml").exists()


def test_lifts_bridges_and_councils_out_of_resolutions(tmp_path):
    # OLD layout nested bridges/councils under .outputs/. The wholesale
    # .outputs/ -> resolutions/ move would wrongly land them at
    # resolutions/{bridges,councils}; they must be lifted to base/{bridges,
    # councils} where config/uacp.toml declares them (council Gap-1).
    _old_repo(tmp_path)
    (tmp_path / ".outputs" / "bridges").mkdir()
    (tmp_path / ".outputs" / "bridges" / "b1.jsonl").write_text('{"x": 1}\n')
    (tmp_path / ".outputs" / "councils").mkdir()
    (tmp_path / ".outputs" / "councils" / "c1.md").write_text("# council\n")
    mig.migrate(tmp_path)
    assert (tmp_path / ".uacp" / "bridges" / "b1.jsonl").exists()
    assert (tmp_path / ".uacp" / "councils" / "c1.md").exists()
    assert not (tmp_path / ".uacp" / "resolutions" / "bridges").exists()
    assert not (tmp_path / ".uacp" / "resolutions" / "councils").exists()


def test_resumable_after_half_migration(tmp_path):
    # Simulate an interrupted migration: some dirs already live under .uacp/,
    # the rest are still flat. A re-run must complete the un-done moves without
    # aborting (council Gap-4).
    _old_repo(tmp_path)
    base = tmp_path / ".uacp"
    base.mkdir()
    # state already migrated (src gone, dst present)
    (tmp_path / "state").rename(base / "state")
    # the rest remain flat
    mig.migrate(tmp_path)  # must not raise
    assert (base / "state" / "runs" / "r1.yaml").exists()
    assert (base / "resolutions" / "r1-closure.yaml").exists()
    assert (base / "proposals").is_dir()
    assert not (tmp_path / ".outputs").exists()
    assert not (tmp_path / "proposals").exists()


def test_appends_gitignore_block_idempotently(tmp_path):
    _old_repo(tmp_path)
    gi = tmp_path / ".gitignore"
    gi.write_text("node_modules/\n")
    mig.migrate(tmp_path)
    text = gi.read_text()
    assert "node_modules/" in text  # preserved
    assert ".uacp/state/" in text
    assert ".uacp/councils/" in text
    # idempotent: a second migrate must not double-append the block
    mig.migrate(tmp_path)
    assert gi.read_text().count(".uacp/state/") == 1


def test_no_gitignore_means_no_create(tmp_path):
    # If the repo has no .gitignore, migration does not invent one.
    _old_repo(tmp_path)
    mig.migrate(tmp_path)
    assert not (tmp_path / ".gitignore").exists()
