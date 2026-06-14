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
