"""E2E (capsule #3, slice 0c): the GOVERNED authoring path for uacp.check.* checks.

A kind is writable through the entity-writer only if it has BOTH a layout Entry AND
(for shape enforcement) a registered schema — schema alone is not enough; the writer
refuses an unknown kind at the LAYOUT step before validation (council finding). These
tests prove a check authored via `create_entity` persists + registers + projects as a
`check` node and replays, and that a malformed check is rejected validate-on-write.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from engines.domain import layout, schema
from engines.manifest.entity_writer import create_entity
from engines.manifest.projection import validate_check_replay
from state_machine import handle_init


def _init(root: Path, run_id: str) -> None:
    handle_init({"workspace": str(root), "run_id": run_id, "source": "operator-request"})


def _field_equals_fields(target: str, artifact: str, path: str, value: str) -> dict:
    return {
        "id": "chk-1",
        "from": {"target": target, "basis": f"{target} sets {path}"},
        "bind": {"plane": "artifact", "ref": {"artifact": artifact, "path": path}},
        "expect": {"value": value},
        "severity": "block",
    }


def test_check_kind_is_in_layout_and_schema_registries():
    # The BOTH-registries requirement (council finding): every catalog kind needs a
    # layout Entry (so the writer accepts it) AND a schema (so it is shape-enforced).
    for sub in ("field_equals", "field_present", "edge_exists", "artifact_integrity"):
        kind = f"uacp.check.{sub}"
        assert layout.fmt_of(kind) == layout.YAML, kind
        assert layout.plane_of(kind) == layout.RELATION, kind
        assert schema.has_schema(kind), kind


def test_every_layout_check_kind_has_a_schema():
    # The catalog is duplicated (layout owns it; schema keeps a stdlib-leaf copy). This pins
    # the harmful direction — a kind added to the layout catalog but missing a schema would be
    # writable UNVALIDATED (the BOTH-registries gap the council flagged). Every catalog kind
    # must be both governed-located AND shape-enforced.
    for sub in layout.CHECK_KINDS:
        kind = f"uacp.check.{sub}"
        assert layout.fmt_of(kind) == layout.YAML, kind
        assert schema.has_schema(kind), f"{kind} is in the layout catalog but has no schema"


def test_authored_check_persists_projects_and_replays(tmp_path):
    run_id = "uacp-auth-1"
    _init(tmp_path, run_id)
    # a data artifact the check binds to, authored the same governed way is overkill;
    # write it directly (the check is the unit under test).
    data_rel = f"plans/{run_id}-data.yaml"
    (tmp_path / ".uacp" / "plans").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".uacp" / data_rel).write_text(
        yaml.safe_dump({"kind": "uacp.scope", "status": "ready"}), encoding="utf-8"
    )
    # register the data artifact so the manifest carries it for projection
    from state_machine import handle_register_artifact

    handle_register_artifact(
        {"workspace": str(tmp_path), "run_id": run_id, "artifact_type": "data", "path": data_rel}
    )

    res = create_entity(
        str(tmp_path),
        run_id,
        "uacp.check.field_equals",
        _field_equals_fields("wu-1", data_rel, "status", "ready"),
        seq="1",
    )
    assert res.get("ok") is True, res
    # the writer injected kind + run_id; the doc on disk is a real frozen check
    doc = yaml.safe_load((tmp_path / ".uacp" / res["path"]).read_text(encoding="utf-8"))
    assert doc["kind"] == "uacp.check.field_equals" and doc["id"] == "chk-1"

    # it replays (status=ready == expected ready -> PASS, no violation)
    replay = validate_check_replay(str(tmp_path), run_id)
    assert not [v for v in replay if v.code.startswith("CHK_")], replay


def test_governed_check_severity_must_be_block(tmp_path):
    # Reviewer (MAJOR): a gate check cannot be authored non-blocking. The governed path rejects
    # severity 'warn' — slice-0 checks gate, they don't advise (policy-graded severity is L2).
    run_id = "uacp-auth-3"
    _init(tmp_path, run_id)
    fields = _field_equals_fields("wu-1", f"plans/{run_id}-d.yaml", "status", "ready")
    fields["severity"] = "warn"
    res = create_entity(str(tmp_path), run_id, "uacp.check.field_equals", fields, seq="1")
    assert "error" in res and "validate-on-write rejected" in res["error"], res


def test_validate_on_write_rejects_malformed_check(tmp_path):
    # A check missing the required `from.target` is shape-invalid -> REJECTED, nothing
    # persisted/registered. Non-vacuity: the well-formed sibling above is accepted.
    run_id = "uacp-auth-2"
    _init(tmp_path, run_id)
    res = create_entity(
        str(tmp_path),
        run_id,
        "uacp.check.field_equals",
        {"id": "chk-x", "from": {}, "bind": {"plane": "artifact"}},  # no from.target
        seq="1",
    )
    assert "error" in res and "validate-on-write rejected" in res["error"], res
    assert not list((tmp_path / ".uacp" / "verification").glob("*")) if (
        tmp_path / ".uacp" / "verification"
    ).exists() else True
