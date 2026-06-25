"""E2E (capsule #3 follow-on): the catalog_version field on frozen checks (design node 30).

The entity-writer injects the CURRENT catalog version onto every uacp.check.* it writes; replay
refuses a check authored under a FOREIGN catalog (its kind semantics are not vouched for). A missing
version is tolerated (legacy/raw checks). Multi-version migration machinery is deferred (YAGNI).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from engines.domain.layout import CATALOG_VERSION
from engines.manifest.entity_writer import create_entity
from engines.manifest.projection import validate_check_replay
from state_machine import handle_init, handle_register_artifact


def _init(root: Path, run_id: str) -> None:
    handle_init({"workspace": str(root), "run_id": run_id, "source": "operator-request"})


def _write(root: Path, rel: str, doc: dict) -> None:
    p = root / ".uacp" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _register(root: Path, run_id: str, atype: str, rel: str) -> None:
    out = json.loads(
        handle_register_artifact(
            {"workspace": str(root), "run_id": run_id, "artifact_type": atype, "path": rel}
        )
    )
    assert out.get("ok") is True, out


def test_writer_injects_current_catalog_version(temp_uacp_root: Path):
    run_id = "uacp-cv-1"
    _init(temp_uacp_root, run_id)
    data_rel = f"plans/{run_id}-d.yaml"
    _write(temp_uacp_root, data_rel, {"kind": "uacp.scope", "status": "ready"})
    res = create_entity(
        str(temp_uacp_root),
        run_id,
        "uacp.check.field_equals",
        {
            "id": "chk-1",
            "from": {"target": "wu-1", "basis": "x"},
            "bind": {"plane": "artifact", "ref": {"artifact": data_rel, "path": "status"}},
            "expect": {"value": "ready"},
            "severity": "block",
        },
        seq="1",
    )
    assert res.get("ok") is True, res
    doc = yaml.safe_load((temp_uacp_root / ".uacp" / res["path"]).read_text(encoding="utf-8"))
    assert doc["catalog_version"] == CATALOG_VERSION  # injected by the writer, not the caller


def test_foreign_catalog_version_is_error_block(temp_uacp_root: Path):
    # a check from a DIFFERENT catalog version is refused (ERROR, block) — not re-run under today's
    # evaluators. (Raw-written to simulate a foreign/older check; the governed path can't forge it.)
    run_id = "uacp-cv-2"
    _init(temp_uacp_root, run_id)
    data_rel = f"plans/{run_id}-d.yaml"
    _write(temp_uacp_root, data_rel, {"kind": "uacp.scope", "status": "ready"})
    _write(
        temp_uacp_root,
        f"verification/{run_id}-chk.yaml",
        {
            "kind": "uacp.check.field_equals",
            "id": "chk-old",
            "catalog_version": "0",
            "from": {"target": "wu-1", "basis": "x"},
            "bind": {"plane": "artifact", "ref": {"artifact": data_rel, "path": "status"}},
            "expect": {"value": "ready"},
            "severity": "block",
        },
    )
    _register(temp_uacp_root, run_id, "data", data_rel)
    _register(temp_uacp_root, run_id, "check_1", f"verification/{run_id}-chk.yaml")
    vs = validate_check_replay(str(temp_uacp_root), run_id)
    assert any(v.code == "CHK_CATALOG_VERSION" and v.severity == "block" for v in vs), vs


def test_missing_catalog_version_is_tolerated(temp_uacp_root: Path):
    # a check with NO catalog_version (legacy) still replays normally (backward-compat) — a matching
    # field_equals passes, no CHK_CATALOG_VERSION.
    run_id = "uacp-cv-3"
    _init(temp_uacp_root, run_id)
    data_rel = f"plans/{run_id}-d.yaml"
    _write(temp_uacp_root, data_rel, {"kind": "uacp.scope", "status": "ready"})
    _write(
        temp_uacp_root,
        f"verification/{run_id}-chk.yaml",
        {
            "kind": "uacp.check.field_equals",
            "id": "chk-legacy",
            "from": {"target": "wu-1", "basis": "x"},
            "bind": {"plane": "artifact", "ref": {"artifact": data_rel, "path": "status"}},
            "expect": {"value": "ready"},
            "severity": "block",
        },
    )
    _register(temp_uacp_root, run_id, "data", data_rel)
    _register(temp_uacp_root, run_id, "check_1", f"verification/{run_id}-chk.yaml")
    codes = {v.code for v in validate_check_replay(str(temp_uacp_root), run_id)}
    assert "CHK_CATALOG_VERSION" not in codes and "CHK_FIELD_EQUALS" not in codes
