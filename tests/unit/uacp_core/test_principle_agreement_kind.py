"""The `uacp.principle_agreement` governed entity kind (PRINCIPLE.md bootstrap).

Records the engineer's AGREEMENT to a derived PRINCIPLE.md as a first-class, provenanced manifest
node — who agreed, when, from what evidence, which version — rather than a frontmatter flag (the
settled design decision). Pins its layout registration (RELATION plane, `resolutions/` segment — NOT
the `knowledge` Oracle-corpus segment — run-scoped template) and its write-time schema (required
provenance fields incl. a content-hash binding, fail-closed on a missing one).
"""

from __future__ import annotations

import yaml

from engines.domain import layout
from engines.domain.artifact_hashes import load_hash_index
from engines.domain.schema import has_schema, validate
from engines.manifest.entity_writer import create_entity
from state_machine import handle_init

_KIND = "uacp.principle_agreement"


def _init_run(root, run_id: str = "uacp-boot-001") -> str:
    handle_init({"workspace": str(root), "run_id": run_id, "source": "operator-request"})
    return run_id


def test_kind_registered_relation_plane_resolutions_segment() -> None:
    assert layout.fmt_of(_KIND) == layout.YAML  # a governed YAML manifest node
    assert layout.plane_of(_KIND) == layout.RELATION  # entity-writer-owned, not STATE
    tmpl = layout.template(_KIND)
    assert tmpl is not None and tmpl.endswith("principle-agreement.yaml")
    assert "{run_id}" in tmpl  # provenance is run-scoped


_GOOD_HASH = "a" * 64  # 64 lowercase hex chars


def _well_formed() -> dict:
    return {
        "kind": _KIND,
        "run_id": "uacp-boot-001",
        "principle_path": "PRINCIPLE.md",
        "principle_content_sha256": _GOOD_HASH,
        "agreed_by": "operator",
        "agreed_at": "2026-08-17T00:00:00Z",
        "derived_from": "the uacp-bootstrap derivation record",
    }


def test_schema_accepts_a_well_formed_agreement() -> None:
    assert has_schema(_KIND)
    assert validate(_KIND, _well_formed()) == []  # no errors


def test_schema_rejects_missing_provenance() -> None:
    """A record omitting WHO agreed (or any required provenance field) is refused at write —
    agreement-without-provenance is exactly what this kind exists to prevent. Non-vacuous."""
    doc = _well_formed()
    del doc["agreed_by"]  # provenance hole
    errors = validate(_KIND, doc)
    assert errors  # MUST reject
    assert any("agreed_by" in e for e in errors)


def test_schema_requires_content_hash_binding() -> None:
    """The agreement MUST carry a content-hash of the PRINCIPLE.md it covers — without it the claim
    is unfalsifiable (the file could be edited and nothing would notice). Missing => reject."""
    doc = _well_formed()
    del doc["principle_content_sha256"]
    assert validate(_KIND, doc)  # MUST reject


def test_schema_rejects_non_sha256_hash() -> None:
    """A malformed hash (not 64 lowercase hex) is refused — the binding must be a real digest."""
    for bad in ["not-a-hash", "A" * 64, "abc", _GOOD_HASH + "x", _GOOD_HASH + "\n"]:
        doc = _well_formed()
        doc["principle_content_sha256"] = bad
        assert validate(_KIND, doc), f"expected rejection for {bad!r}"


def test_schema_rejects_wrong_kind_const() -> None:
    doc = _well_formed()
    doc["kind"] = "uacp.lessons"  # forged/wrong kind
    assert validate(_KIND, doc)  # kind-const mismatch rejected


# --- end-to-end: the REAL writer with a run context (settled option-1 flow) ---------------


def test_end_to_end_write_persists_watermarks_and_registers(tmp_path) -> None:
    """Drive the real entity-writer with a run context (bootstrap opens a lightweight run). Proves
    the kind is wired end-to-end — layout path (RELATION dir, NOT knowledge/), plane guard,
    validate-on-write, watermark, manifest registration — not just the two registries in isolation.
    This is the test whose absence let the wrong-segment defect ship."""
    run_id = _init_run(tmp_path)
    fields = {
        "principle_path": "PRINCIPLE.md",
        "principle_content_sha256": _GOOD_HASH,
        "agreed_by": "operator",
        "agreed_at": "2026-08-17T00:00:00Z",
        "derived_from": "the uacp-bootstrap derivation record",
    }
    res = create_entity(str(tmp_path), run_id, _KIND, fields)
    assert res.get("ok") is True, res
    rel = res["path"]
    assert rel == f"resolutions/{run_id}-principle-agreement.yaml"  # RELATION dir, not knowledge/
    target = tmp_path / ".uacp" / rel
    assert target.is_file()
    doc = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert doc["kind"] == _KIND and doc["principle_content_sha256"] == _GOOD_HASH
    assert rel in load_hash_index(tmp_path, run_id)  # watermarked
    manifest = yaml.safe_load(
        (tmp_path / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text(encoding="utf-8")
    )
    assert rel in manifest["artifacts"].values()  # registered into the run manifest


def test_end_to_end_rejects_missing_hash_no_write(tmp_path) -> None:
    """Validate-on-write refuses an agreement lacking the content-hash binding — no file, no
    registration (the fail-closed writer path)."""
    run_id = _init_run(tmp_path)
    fields = {
        "principle_path": "PRINCIPLE.md",
        # principle_content_sha256 intentionally MISSING
        "agreed_by": "operator",
        "agreed_at": "2026-08-17T00:00:00Z",
        "derived_from": "x",
    }
    res = create_entity(str(tmp_path), run_id, _KIND, fields)
    assert res.get("ok") is not True and "error" in res  # rejected
    assert not (
        tmp_path / ".uacp" / "resolutions" / f"{run_id}-principle-agreement.yaml"
    ).exists()  # no stray file
