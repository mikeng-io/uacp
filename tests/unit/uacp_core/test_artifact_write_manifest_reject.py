"""CUT3 (unbypassable): raw uacp_artifact_write must REJECT RELATION-plane manifest kinds — the
governed entity-writer (uacp_entity_write) is the only path for them, so the graph_projection gate
always sees a registered + validated doc. The reject is at the HANDLER level (the Guardian category
block is bypassed by direct/MCP/test calls). Corpus roots (knowledge/, lessons/) resolve to no
manifest kind and still pass."""

import json

from governed_handlers import _handle_uacp_artifact_write
from state_machine import handle_init


def _init(root, run_id="r1"):
    handle_init({"workspace": str(root), "run_id": run_id, "source": "operator-request"})
    return run_id


def _args(root, target_path):
    return {
        "target_path": target_path,
        "content": "kind: x\nbody: y\n",
        "reason": "t",
        "authority_artifact": "proposals/x.yaml",
        "workspace": str(root),
        "uacp_run_id": "r1",
        "uacp_phase": "plan",
        "policy_version": "0.1",
        "declared_side_effects": [],
    }


def test_artifact_write_rejects_relation_manifest_kinds(tmp_path):
    _init(tmp_path)
    for p in (
        "plans/r1-piv.yaml",
        "proposals/r1-proposal.yaml",
        "verification/r1-piv-assessment.yaml",
        "brainstorm/r1/07-scope-package.yaml",
    ):
        res = json.loads(_handle_uacp_artifact_write(_args(tmp_path, p)))
        assert "error" in res and "uacp_entity_write" in res["error"], (p, res)
        assert not (tmp_path / ".uacp" / p).exists(), f"{p} should not have been written"


def test_artifact_write_allows_corpus_and_nonmanifest_paths(tmp_path):
    # Corpus roots + non-template paths resolve to no manifest kind -> still allowed.
    _init(tmp_path)
    for p in ("knowledge/note.md", "lessons/note.md", "plans/scratch.yaml"):
        res = json.loads(_handle_uacp_artifact_write(_args(tmp_path, p)))
        assert res.get("ok") is True, (p, res)
