"""E2E (capsule #3, slice 3): the code plane — `uacp.check.symbol_resolves`.

The reality binder's `code` resolver (design node 32): a symbol_resolves check binds to the REAL
SCIP symbol index (Codeflair, which UACP CONSUMES — CF-D9) instead of a textual shadow (the #503
`grep route_mounted` weak proxy). PASS iff the symbol resolves to >=1 SCIP descriptor in the run's
index; FAIL if it resolves to none; ERROR (fail-closed, block) if there is NO index for the run or
codeflair is unavailable — never a silent pass. Resolution happens at REPLAY (it does not project
code nodes into the manifest graph).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from codeflair.store import Store, Symbol
from engines.code_plane import index_path
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


def _symbol_check(symbol: str) -> dict:
    return {
        "kind": "uacp.check.symbol_resolves",
        "id": "chk-sym",
        "from": {"target": "wu-1", "class": "wires_symbol", "basis": f"wu-1 wires {symbol}"},
        "bind": {"plane": "code", "ref": {"symbol": symbol}},
        "severity": "block",
    }


def _build_index(root: Path, names: list[str]) -> None:
    # Build a Codeflair SCIP index at the run's conventioned path with the given symbol NAMES (the
    # resolver matches by name). A symbol needs file != '' to be resolvable (crossplane.resolve).
    path = index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    store = Store(str(path))
    for n in names:
        store.add_symbol(
            Symbol(symbol=f"scip . . `{n}`().", lang="python", file="app/routes.py", name=n)
        )
    store.con.commit()
    store.con.close()


def _put_check(root: Path, run_id: str, symbol: str) -> None:
    rel = f"verification/{run_id}-chk-sym.yaml"
    _write(root, rel, _symbol_check(symbol))
    _register(root, run_id, "check_sym", rel)


def _codes(root: Path, run_id: str) -> set[str]:
    return {v.code for v in validate_check_replay(str(root), run_id)}


def test_symbol_resolves_passes_when_symbol_in_index(temp_uacp_root: Path):
    run_id = "uacp-cp-1"
    _init(temp_uacp_root, run_id)
    _build_index(temp_uacp_root, ["settle_route"])
    _put_check(temp_uacp_root, run_id, "settle_route")
    assert "CHK_SYMBOL_RESOLVES" not in _codes(temp_uacp_root, run_id)


def test_symbol_resolves_no_substring_false_pass(temp_uacp_root: Path):
    # Council (all 3): the resolver must match EXACT identity, not a substring (the L2b bug one
    # plane up). `route` must NOT pass against an index containing only `reroute`/`router`.
    run_id = "uacp-cp-sub"
    _init(temp_uacp_root, run_id)
    _build_index(temp_uacp_root, ["reroute", "router"])
    _put_check(temp_uacp_root, run_id, "route")
    vs = validate_check_replay(str(temp_uacp_root), run_id)
    assert any(v.code == "CHK_SYMBOL_RESOLVES" and v.severity == "block" for v in vs), vs


def test_symbol_resolves_no_like_wildcard_false_pass(temp_uacp_root: Path):
    # Council (Claude): a LIKE-wildcard bind ('%' / '_') must NOT match everything — exact match
    # treats them literally, so they resolve to nothing -> FAIL (block), not a universal bypass.
    run_id = "uacp-cp-wild"
    _init(temp_uacp_root, run_id)
    _build_index(temp_uacp_root, ["settle_route"])
    _put_check(temp_uacp_root, run_id, "%")
    vs = validate_check_replay(str(temp_uacp_root), run_id)
    assert any(v.code == "CHK_SYMBOL_RESOLVES" and v.severity == "block" for v in vs), vs


def test_symbol_resolves_does_not_write_into_the_index(temp_uacp_root: Path):
    # Council (kimi): UACP CONSUMES the index (CF-D9) — resolving must NOT create the adapter's
    # `code_anchor` table (or any table) in it. Open read-only after a resolve and confirm.
    import sqlite3

    run_id = "uacp-cp-ro"
    _init(temp_uacp_root, run_id)
    _build_index(temp_uacp_root, ["settle_route"])
    _put_check(temp_uacp_root, run_id, "settle_route")
    validate_check_replay(str(temp_uacp_root), run_id)
    con = sqlite3.connect(str(index_path(temp_uacp_root)))
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con.close()
    assert "code_anchor" not in tables, tables


def test_symbol_resolves_fails_when_symbol_absent(temp_uacp_root: Path):
    # index present but the claimed symbol is NOT in it -> FAIL (block), not a pass.
    run_id = "uacp-cp-2"
    _init(temp_uacp_root, run_id)
    _build_index(temp_uacp_root, ["some_other_symbol"])
    _put_check(temp_uacp_root, run_id, "settle_route")
    vs = validate_check_replay(str(temp_uacp_root), run_id)
    assert any(v.code == "CHK_SYMBOL_RESOLVES" and v.severity == "block" for v in vs), vs


def test_symbol_resolves_errors_when_no_index(temp_uacp_root: Path):
    # #503 class A + node 32 fail-closed-until-wired: NO code index for the run -> ERROR (block),
    # never a silent pass. A wires_symbol target therefore cannot close until the plane is built.
    run_id = "uacp-cp-3"
    _init(temp_uacp_root, run_id)
    _put_check(temp_uacp_root, run_id, "settle_route")  # no _build_index
    vs = validate_check_replay(str(temp_uacp_root), run_id)
    assert any(v.code == "CHK_SYMBOL_RESOLVES" and v.severity == "block" for v in vs), vs


def test_wires_symbol_target_can_now_close_against_a_real_symbol(temp_uacp_root: Path):
    # The relevance closure (slice 3): a `wires_symbol` work_unit's floor requires symbol_resolves;
    # authoring one satisfies the FLOOR (kind present) AND, with a built index where the symbol
    # resolves, it PASSES replay — so the target finally closes. Before slice 3 it was block-until-
    # wired. The check's `from.class: wires_symbol` is honest (intent says "wire") -> no underclaim.
    from engines.graph_projection import validate_check_floor

    run_id = "uacp-cp-4"
    _init(temp_uacp_root, run_id)
    _write(
        temp_uacp_root,
        f"plans/{run_id}-piv.yaml",
        {
            "kind": "uacp.phase_intent_verification_contract",
            "work_units": [{"id": "wu-1", "intent": "wire up the settle_route handler"}],
        },
    )
    _register(temp_uacp_root, run_id, "piv", f"plans/{run_id}-piv.yaml")
    _build_index(temp_uacp_root, ["settle_route"])
    _put_check(temp_uacp_root, run_id, "settle_route")
    floor_codes = {v.code for v in validate_check_floor(str(temp_uacp_root), run_id)}
    assert "CHK_FLOOR_UNMET" not in floor_codes  # wires_symbol floor satisfied by symbol_resolves
    assert "CHK_SYMBOL_RESOLVES" not in _codes(temp_uacp_root, run_id)  # and it really resolves
