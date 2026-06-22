"""C5 — the Manifest engine's entity-writer: typed, validated, watermarked, registered
manifest write path (node 35). Also guards the C4 governed-writers re-export identity."""

import yaml

from engines.domain.artifact_hashes import load_hash_index
from engines.manifest.entity_writer import create_entity
from state_machine import handle_init


def _init_run(root, run_id: str = "uacp-ew-001") -> str:
    handle_init({"workspace": str(root), "run_id": run_id, "source": "operator-request"})
    return run_id


def test_create_entity_persists_watermarks_and_registers(tmp_path):
    run_id = _init_run(tmp_path)
    res = create_entity(
        str(tmp_path),
        run_id,
        "uacp.scope",
        {
            "run_id": run_id,
            "write_paths": ["plans/x.yaml"],
            "blast_radius": "low",
            "rollback_path": "git revert HEAD",
        },
    )
    assert res.get("ok") is True, res
    rel = res["path"]
    assert rel == f"plans/{run_id}-scope.yaml"

    # PERSIST: file written under .uacp/ with the kind const + the typed fields.
    target = tmp_path / ".uacp" / rel
    assert target.is_file()
    doc = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert doc["kind"] == "uacp.scope"
    assert doc["write_paths"] == ["plans/x.yaml"]

    # WATERMARK: the fail-closed detection watermark was recorded for this path.
    assert rel in load_hash_index(tmp_path, run_id)

    # REGISTER: linked into the run manifest's artifacts (keyed by short type).
    manifest = yaml.safe_load(
        (tmp_path / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text(encoding="utf-8")
    )
    assert manifest["artifacts"]["scope"] == rel


def test_create_entity_validate_on_write_rejects_malformed_scope(tmp_path):
    # A scope missing required blast_radius + rollback_path is shape-invalid -> REJECTED,
    # with NO write and NO registration (the net-new validate-on-write gate).
    run_id = _init_run(tmp_path)
    res = create_entity(
        str(tmp_path),
        run_id,
        "uacp.scope",
        {"run_id": run_id, "write_paths": ["plans/x.yaml"]},
    )
    assert "error" in res and "validate-on-write rejected" in res["error"]
    # Non-vacuity: break the gate and this fires — nothing persisted, nothing registered.
    assert not (tmp_path / ".uacp" / "plans" / f"{run_id}-scope.yaml").exists()
    manifest = yaml.safe_load(
        (tmp_path / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text(encoding="utf-8")
    )
    assert "scope" not in (manifest.get("artifacts") or {})


def test_create_entity_unknown_kind_errors(tmp_path):
    run_id = _init_run(tmp_path)
    res = create_entity(str(tmp_path), run_id, "uacp.not_a_real_kind", {"run_id": run_id})
    assert "error" in res and "unknown kind" in res["error"]
    # Non-vacuity: nothing was written for an unknown kind.
    assert not (tmp_path / ".uacp" / "plans").exists() or not list(
        (tmp_path / ".uacp" / "plans").glob("*")
    )


def test_create_entity_markdown_kind_writes_frontmatter_and_body(tmp_path):
    # uacp.intent is a MARKDOWN kind: the entity-writer serializes `kind` frontmatter + the
    # caller-provided body and persists+registers it (structural section validation is the
    # transition gate's job, on the persisted file — C5.6).
    run_id = _init_run(tmp_path)
    body = "## Problem\n\nx\n\n## Goal\n\ny\n"
    res = create_entity(str(tmp_path), run_id, "uacp.intent", {"run_id": run_id, "body": body})
    assert res.get("ok") is True, res
    rel = res["path"]
    assert rel == f"proposals/{run_id}-intent.md"
    content = (tmp_path / ".uacp" / rel).read_text(encoding="utf-8")
    assert content.startswith("---\nkind: uacp.intent\n---")
    assert "## Problem" in content and "## Goal" in content
    manifest = yaml.safe_load(
        (tmp_path / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text(encoding="utf-8")
    )
    assert manifest["artifacts"]["intent"] == rel


def test_create_entity_multi_instance_does_not_overwrite(tmp_path):
    # execution_checkpoint is multi-instance ({seq}); two instances must both register under
    # DISTINCT composite keys, not overwrite each other (Codex PR#3 multi-instance finding).
    run_id = _init_run(tmp_path)
    r1 = create_entity(
        str(tmp_path),
        run_id,
        "uacp.execution_checkpoint",
        {"run_id": run_id, "checkpoint_id": "c1"},
        seq="1",
    )
    r2 = create_entity(
        str(tmp_path),
        run_id,
        "uacp.execution_checkpoint",
        {"run_id": run_id, "checkpoint_id": "c2"},
        seq="2",
    )
    assert r1.get("ok") and r2.get("ok"), (r1, r2)
    assert r1["path"] != r2["path"]
    assert (tmp_path / ".uacp" / r1["path"]).is_file()
    assert (tmp_path / ".uacp" / r2["path"]).is_file()
    # Non-vacuity: BOTH paths survive in the manifest (a bare-type key would drop the first).
    manifest = yaml.safe_load(
        (tmp_path / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text(encoding="utf-8")
    )
    paths = set(manifest["artifacts"].values())
    assert r1["path"] in paths and r2["path"] in paths
    assert r1["artifact_type"] != r2["artifact_type"]


def test_governed_writers_reexport_identity():
    # C4-review guard: the write-port re-exports the SAME primitive objects as filesystem
    # (so a future "unused, delete it" sweep can't silently sever the seam — A3 pattern).
    import filesystem

    from engines.manifest import governed_writers as gw

    assert gw._write_uacp_file is filesystem._write_uacp_file
    assert gw._resolve_uacp_path is filesystem._resolve_uacp_path
