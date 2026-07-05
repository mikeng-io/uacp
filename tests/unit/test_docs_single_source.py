"""Single-source doc tables (#111): generator + drift guards.

The governed-writer list (AGENTS.md Invariant #3) and the writer-to-path map
(docs/runtime/runtime-enforcement.md) are GENERATED from the kernel by
scripts/gen_doc_tables.py — never hand-maintained. These tests pin the contract:

  * the derived writer list matches the tool_specs() registry exactly
    (read_only=False specs, registry order) — no phantom writers, no omissions;
  * sentinel injection is idempotent and actually replaces stale content;
  * the COMMITTED doc blocks match a fresh generation (drift red at the pytest
    gate, mirroring tests/unit/test_ruff_pin_sync.py's drift-guard pattern);
  * the docs/INDEX.md repository inventory carries no pre-`.uacp/` ghost rows
    and every non-runtime row exists in the tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import gen_doc_tables as gen  # noqa: E402

from tool_specs import tool_specs  # noqa: E402  (conftest puts uacp-core scripts on sys.path)


# ---------------------------------------------------------------------------
# Generator derivation
# ---------------------------------------------------------------------------


def test_writer_list_matches_registry_exactly():
    """The derived writer list == the read_only=False registry specs, in order."""
    expected = [s.name for s in tool_specs() if not s.read_only]
    assert gen.governed_writers() == expected
    # Non-vacuity: the registry's four run-lifecycle writers are present.
    for name in (
        "uacp_run_init",
        "uacp_run_transition",
        "uacp_run_register_artifact",
        "uacp_run_finalize",
    ):
        assert name in expected


def test_read_only_tools_are_not_writers():
    assert set(gen.read_only_tools()) == {s.name for s in tool_specs() if s.read_only}
    assert not set(gen.read_only_tools()) & set(gen.governed_writers())


def test_phantom_writers_absent_everywhere():
    """The #97 finding-1 phantoms are gone from the derivation AND the contract."""
    writers = gen.governed_writers()
    assert "uacp_kanban_write" not in writers
    assert "uacp_sandbox_write" not in writers
    agents = (ROOT / "AGENTS.md").read_text()
    assert "uacp_kanban_write" not in agents
    assert "uacp_sandbox_write" not in agents


def test_writer_path_table_covers_every_writer():
    """Every registry writer appears in the generated table (fail-closed rule)."""
    table = gen.writer_path_table()
    for name in gen.governed_writers():
        assert f"`{name}`" in table, f"writer {name} missing from the path map"
    for name in gen.read_only_tools():
        assert f"`{name}`" in table  # listed as read-only, not as a writer row


# ---------------------------------------------------------------------------
# Sentinel injection
# ---------------------------------------------------------------------------

_B = "<!-- BEGIN test -->"
_E = "<!-- END test -->"


def test_injection_replaces_stale_content():
    text = f"prefix {_B}STALE{_E} suffix"
    out = gen.inject(text, _B, _E, "FRESH")
    assert out == f"prefix {_B}FRESH{_E} suffix"


def test_injection_idempotent():
    text = f"prefix {_B}STALE{_E} suffix"
    once = gen.inject(text, _B, _E, "FRESH")
    twice = gen.inject(once, _B, _E, "FRESH")
    assert once == twice


def test_injection_fails_closed_without_sentinels():
    import pytest

    with pytest.raises(SystemExit):
        gen.inject("no sentinels here", _B, _E, "FRESH")


def test_extract_roundtrips_injection():
    text = gen.inject(f"x {_B}old{_E} y", _B, _E, "payload")
    assert gen.extract(text, _B, _E) == "payload"
    assert gen.extract("nothing", _B, _E) is None


# ---------------------------------------------------------------------------
# Committed-doc drift (the actual lint, red at the pytest gate too)
# ---------------------------------------------------------------------------


def test_committed_agents_block_matches_generation():
    committed = gen.extract((ROOT / "AGENTS.md").read_text(), gen.WRITERS_BEGIN, gen.WRITERS_END)
    assert committed is not None, "AGENTS.md lost its governed-writers sentinel block"
    assert committed == gen.writers_fragment(), (
        "AGENTS.md governed-writer list drifted from tool_specs(); "
        "run `python3 scripts/gen_doc_tables.py --write` and commit"
    )


def test_committed_writer_path_map_matches_generation():
    committed = gen.extract(
        (ROOT / "docs" / "runtime" / "runtime-enforcement.md").read_text(),
        gen.TABLE_BEGIN,
        gen.TABLE_END,
    )
    assert committed is not None, "runtime-enforcement.md lost its writer-path-map block"
    assert committed == "\n" + gen.writer_path_table() + "\n", (
        "runtime-enforcement.md writer-path map drifted from the kernel; "
        "run `python3 scripts/gen_doc_tables.py --write` and commit"
    )


def test_check_mode_reports_no_drift():
    assert gen.check() == 0


# ---------------------------------------------------------------------------
# docs/INDEX.md repository inventory
# ---------------------------------------------------------------------------


def test_inventory_has_no_ghost_layout_rows():
    """Pre-`.uacp/` top-level rows (state/, plans/, .outputs/, ...) are gone."""
    for p in gen.inventory_paths():
        assert p not in gen._LEGACY_TOP_LEVEL, (
            f"docs/INDEX.md inventory row `{p}` is the ghost pre-.uacp layout "
            "(#97 integration-checker finding 3)"
        )


def test_inventory_rows_exist_in_tree():
    assert gen.check_inventory() == []


def test_inventory_registers_previously_orphaned_files():
    """#97 finding 10: kernel-consumed files/dirs must be registered."""
    paths = set(gen.inventory_paths())
    for required in (
        "codeflair/",
        "UACP.md",
        "skills/",
        "config/verification-floor.yaml",
        "design/",
        "tests/",
        "acceptance/",
        ".uacp/",
    ):
        assert required in paths, f"{required} missing from the INDEX.md inventory"


def test_inventory_registers_uacp_state_surfaces():
    paths = set(gen.inventory_paths())
    for required in (
        ".uacp/state/",
        ".uacp/state/current.yaml",
        ".uacp/state/runs/",
        ".uacp/state/gate-ledger/",
        ".uacp/state/run-registry.yaml",
        ".uacp/state/escalations/",
    ):
        assert required in paths, f"{required} missing from the INDEX.md inventory"
