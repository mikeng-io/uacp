"""CUT1 — the uacp_entity_write governed tool handler (the auto-registering manifest write path).

The handler marshals tool args into engines.manifest.entity_writer.create_entity; the point of the
tool is that a governed write now ALSO registers the artifact into the run manifest — which is what
makes the graph_projection gate non-dormant (it reads manifest.artifacts)."""

import json

import yaml

from governed_handlers import _handle_uacp_entity_write
from state_machine import handle_init


def _init_run(root, run_id: str = "uacp-ewh-001") -> str:
    handle_init({"workspace": str(root), "run_id": run_id, "source": "operator-request"})
    return run_id


def _args(root, run_id, **over):
    base = {
        "workspace": str(root),
        "uacp_run_id": run_id,
        "kind": "uacp.scope",
        "fields": {
            "run_id": run_id,
            "write_paths": ["plans/x.yaml"],
            "blast_radius": "low",
            "rollback_path": "git revert HEAD",
        },
        "reason": "test",
        "authority_artifact": "proposals/x.yaml",
    }
    base.update(over)
    return base


def test_entity_write_handler_writes_and_registers(tmp_path):
    # The activation point: a governed entity write populates manifest.artifacts (so the gate sees it).
    run_id = _init_run(tmp_path)
    res = json.loads(_handle_uacp_entity_write(_args(tmp_path, run_id)))
    assert res.get("ok") is True, res
    rel = res["path"]
    assert rel == f"plans/{run_id}-scope.yaml"
    assert (tmp_path / ".uacp" / rel).is_file()
    manifest = yaml.safe_load(
        (tmp_path / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text(encoding="utf-8")
    )
    assert manifest["artifacts"]["scope"] == rel  # REGISTERED — the dormancy-breaker


def test_entity_write_handler_requires_run_id_and_kind(tmp_path):
    run_id = _init_run(tmp_path)
    assert "error" in json.loads(_handle_uacp_entity_write(_args(tmp_path, run_id, uacp_run_id="")))
    assert "error" in json.loads(_handle_uacp_entity_write(_args(tmp_path, run_id, kind="")))


def test_entity_write_handler_rejects_non_object_fields(tmp_path):
    run_id = _init_run(tmp_path)
    res = json.loads(_handle_uacp_entity_write(_args(tmp_path, run_id, fields="not-an-object")))
    assert "error" in res and "fields must be an object" in res["error"]


def test_entity_write_handler_propagates_validate_on_write(tmp_path):
    # A malformed entity is rejected by create_entity's validate-on-write — nothing registered.
    run_id = _init_run(tmp_path)
    res = json.loads(_handle_uacp_entity_write(_args(tmp_path, run_id, fields={"run_id": run_id})))
    assert "error" in res
    manifest = yaml.safe_load(
        (tmp_path / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text(encoding="utf-8")
    )
    assert "scope" not in (manifest.get("artifacts") or {})
