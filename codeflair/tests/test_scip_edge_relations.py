"""SCIP edge relations (D2): the ingest emits THREE distinct SCIP-sourced relations —
``defines`` (container -> member), ``references`` (use of a non-callable), and ``calls``
(use of a callable) — not ``calls`` only. 01b-store specifies all three; they must be
queryable and retrievable SEPARATELY.
"""

from codeflair import Store
from codeflair.scip_ingest import ingest_scip_json

M = "scip-go gomod example.com/m v1.0.0 `example.com/m/p`"
SVC = f"{M}/Svc#"  # a Type descriptor (ends `#`) -> a container
RUN = f"{M}/Svc#Run()."  # a Method descriptor (ends `).`) -> callable
HELP = f"{M}/Svc#help()."  # a Method descriptor -> callable
CONFIG = f"{M}/Config."  # a Term descriptor (ends `.` not `).`) -> NOT callable
_DEF, _REF = 1, 0


def _occ(symbol: str, line: int, role: int) -> dict:
    return {"symbol": symbol, "range": [line, 0, 10], "symbol_roles": role}


def _fixture() -> dict:
    # s.go: def Svc#@1 (container), def Run()@2 (in Svc), ref help()@3 (call in Run),
    #       ref Config@4 (non-call reference in Run), def help()@10 (in Svc).
    return {
        "documents": [
            {
                "relative_path": "s.go",
                "occurrences": [
                    _occ(SVC, 1, _DEF),
                    _occ(RUN, 2, _DEF),
                    _occ(HELP, 3, _REF),
                    _occ(CONFIG, 4, _REF),
                    _occ(HELP, 10, _DEF),
                ],
            }
        ]
    }


def _by_rel(store: Store, rel: str) -> set[tuple[str, str]]:
    return {
        (src, dst)
        for src, dst in store.con.execute(
            "SELECT src, dst FROM edges WHERE rel=?", (rel,)
        ).fetchall()
    }


def test_three_relations_are_emitted_and_distinct():
    s = Store()
    stats = ingest_scip_json(s, _fixture())
    defines = _by_rel(s, "defines")
    calls = _by_rel(s, "calls")
    references = _by_rel(s, "references")
    # defines: the container defines each member method
    assert defines == {(SVC, RUN), (SVC, HELP)}
    # calls: a callable target referenced inside Run
    assert calls == {(RUN, HELP)}
    # references: a NON-callable target referenced inside Run
    assert references == {(RUN, CONFIG)}
    # all four edges present and SCIP-sourced; the three relations are disjoint sets
    assert stats.edges == 4
    assert s.count_edges(source="scip") == 4
    assert defines and calls and references
    assert defines.isdisjoint(calls) and calls.isdisjoint(references)


def test_call_vs_reference_split_keyed_on_callee_callability():
    # A reference to a callable (ends `).`) is a `calls`; to a non-callable is `references`.
    s = Store()
    ingest_scip_json(s, _fixture())
    # HELP is callable -> the Run->HELP edge is `calls`, never `references`
    assert (RUN, HELP) in _by_rel(s, "calls")
    assert (RUN, HELP) not in _by_rel(s, "references")
    # CONFIG is a non-callable term -> the Run->CONFIG edge is `references`, never `calls`
    assert (RUN, CONFIG) in _by_rel(s, "references")
    assert (RUN, CONFIG) not in _by_rel(s, "calls")


def test_defines_links_container_not_siblings():
    # Sibling methods must NOT define each other; only the enclosing container defines them.
    s = Store()
    ingest_scip_json(s, _fixture())
    defines = _by_rel(s, "defines")
    assert (RUN, HELP) not in defines  # Run does not define help (siblings)
    assert (HELP, RUN) not in defines
    assert all(src == SVC for src, _ in defines)  # only the container is a `defines` source


def test_calls_only_fixture_emits_no_defines_or_references():
    # The original all-methods, no-container fixture stays calls-only (regression for D2).
    foo, bar, baz = f"{M}/Foo().", f"{M}/Bar().", f"{M}/Baz()."
    data = {
        "documents": [
            {
                "relative_path": "a.go",
                "occurrences": [
                    _occ(foo, 10, _DEF),
                    _occ(baz, 12, _REF),
                    _occ(bar, 20, _DEF),
                    _occ(foo, 22, _REF),
                ],
            },
            {"relative_path": "b.go", "occurrences": [_occ(baz, 5, _DEF), _occ(bar, 7, _REF)]},
        ]
    }
    s = Store()
    stats = ingest_scip_json(s, data)
    assert stats.edges == 3
    assert _by_rel(s, "defines") == set()
    assert _by_rel(s, "references") == set()
    assert len(_by_rel(s, "calls")) == 3
