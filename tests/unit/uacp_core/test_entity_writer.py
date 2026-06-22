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
        {"run_id": run_id, "write_paths": ["plans/x.yaml"]},
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


def test_create_entity_unknown_kind_errors(tmp_path):
    run_id = _init_run(tmp_path)
    res = create_entity(str(tmp_path), run_id, "uacp.not_a_real_kind", {"run_id": run_id})
    assert "error" in res and "unknown kind" in res["error"]
    # Non-vacuity: nothing was written for an unknown kind.
    assert not (tmp_path / ".uacp" / "plans").exists() or not list(
        (tmp_path / ".uacp" / "plans").glob("*")
    )


def test_create_entity_markdown_kind_deferred_to_c56(tmp_path):
    # uacp.intent is a MARKDOWN kind (layout.fmt 'markdown'); the markdown branch is C5.6.
    run_id = _init_run(tmp_path)
    res = create_entity(str(tmp_path), run_id, "uacp.intent", {"run_id": run_id})
    assert "error" in res and "markdown" in res["error"].lower()


def test_governed_writers_reexport_identity():
    # C4-review guard: the write-port re-exports the SAME primitive objects as filesystem
    # (so a future "unused, delete it" sweep can't silently sever the seam — A3 pattern).
    import filesystem

    from engines.manifest import governed_writers as gw

    assert gw._write_uacp_file is filesystem._write_uacp_file
    assert gw._resolve_uacp_path is filesystem._resolve_uacp_path
