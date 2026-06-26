"""Tests for engines.domain.design_lint — the decidable design-bundle structure gate.

Structure:
1. Fixture-based unit tests with tiny in-tmp-path bundles (valid + one-per-check violators)
2. A corpus test that runs check_bundle on all design/*/ dirs and reports the violation
   inventory, with an allowlist for known non-conforming bundles.

TDD contract:
- A valid minimal bundle passes with zero violations.
- Each check test violates EXACTLY that check and asserts the matching check_id fires.
- Non-vacuity: the fixture violator test must fail if the violation is not injected
  (caller can verify by removing the violation and seeing the assertion fail).
- Corpus test: conforming bundles must have zero errors; allowlisted bundles must still exist.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from engines.domain.design_lint import (
    SEVERITY_ERROR,
    SEVERITY_WARN,
    check_bundle,
)

# ---------------------------------------------------------------------------
# Repo + design-dir resolution
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DESIGN_DIR = _REPO_ROOT / "design"
_REAL_SCHEMA = _REPO_ROOT / "design" / "graph-engine" / "schema" / "design-index.schema.json"


@pytest.fixture(autouse=True)
def _point_at_real_schema(monkeypatch):
    """Default every fixture test at the REAL schema so the fail-closed
    DESIGN_INDEX_SCHEMA_UNAVAILABLE check does not fire incidentally. Tests that exercise the
    unavailable path (or want to skip schema validation) override _SCHEMA_PATH themselves AFTER
    this fixture runs."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_SCHEMA_PATH", _REAL_SCHEMA)


def _use_permissive_schema(tmp_path: Path, monkeypatch) -> None:
    """Point _SCHEMA_PATH at a permissive (accept-anything) schema -- a LOADABLE schema that
    imposes no constraints. Use this to isolate a non-schema check without fail-OPENing:
    the schema still loads (so DESIGN_INDEX_SCHEMA_UNAVAILABLE cannot fire), it just does not
    constrain the index. (Distinct from a MISSING schema, which must fail closed.)"""
    import engines.domain.design_lint as dl
    schema_file = tmp_path / "permissive-schema.json"
    schema_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(dl, "_SCHEMA_PATH", schema_file)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_VALID_INDEX = textwrap.dedent("""\
    kind: design_index
    title: Test Bundle
    description: A minimal valid test bundle for lint fixtures.
    status: design
    governance: pre-governance-input
    timestamp: '2026-06-26'
    members:
      - 00-alpha.md
      - 01-beta.md
    edges:
      - {src: 01-beta, dst: 00-alpha, rel: depends_on, provenance: derived}
""")

_VALID_NODE_ALPHA = textwrap.dedent("""\
    ---
    type: analysis
    title: Alpha node
    description: The root node.
    tags: [test]
    timestamp: 2026-06-26
    edges: []
    ---
    # Alpha
    Body.
""")

_VALID_NODE_BETA = textwrap.dedent("""\
    ---
    type: design
    title: Beta node
    description: A dependent node.
    tags: [test]
    timestamp: 2026-06-26
    edges:
      - {dst: 00-alpha, rel: depends_on, provenance: derived}
    ---
    # Beta
    Body.
""")


def _make_valid_bundle(tmp_path: Path) -> Path:
    """Create a minimal valid design bundle under tmp_path/design/test-bundle/."""
    bundle = tmp_path / "design" / "test-bundle"
    bundle.mkdir(parents=True)
    (bundle / "_index.yaml").write_text(_VALID_INDEX, encoding="utf-8")
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(_VALID_NODE_BETA, encoding="utf-8")
    return bundle


# An _index with NO edges -- lets a fixture isolate a non-edge check (both nodes edgeless,
# so neither edge direction can fire). Members still has 2 nodes (>=2 satisfied).
_INDEX_NO_EDGES = textwrap.dedent("""\
    kind: design_index
    title: Test Bundle
    description: A minimal valid test bundle for lint fixtures.
    status: design
    governance: pre-governance-input
    timestamp: '2026-06-26'
    members:
      - 00-alpha.md
      - 01-beta.md
    edges: []
""")

# A second edgeless node so an isolated fixture has two valid, edge-free nodes.
_NODE_BETA_NO_EDGES = textwrap.dedent("""\
    ---
    type: design
    title: Beta node
    description: A dependent node.
    tags: [test]
    timestamp: 2026-06-26
    edges: []
    ---
    # Beta
    Body.
""")


def _assert_exact_check_ids(viols, expected_ids: set[str]) -> None:
    """Assert the EXACT set of check_ids produced equals expected_ids.

    Proves non-vacuity AND no cross-contamination: the fixture must violate ONLY the
    check(s) under test -- nothing else fires.
    """
    actual = {v.check_id for v in viols}
    assert actual == expected_ids, (
        f"check_id set mismatch.\n  expected: {sorted(expected_ids)}\n  actual:   {sorted(actual)}"
        f"\n  full: {[(v.check_id, v.message) for v in viols]}"
    )


# ---------------------------------------------------------------------------
# 1. Valid bundle -- passes all checks
# ---------------------------------------------------------------------------


def test_valid_bundle_passes(tmp_path: Path, monkeypatch) -> None:
    """A well-formed minimal bundle has zero violations."""
    # Monkeypatch _REPO_ROOT so check 4 (placement) resolves correctly
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(dl, "_SCHEMA_PATH", _REPO_ROOT / "design" / "graph-engine" / "schema" / "design-index.schema.json")

    bundle = _make_valid_bundle(tmp_path)
    viols = check_bundle(bundle)
    errors = [v for v in viols if v.severity == SEVERITY_ERROR]
    assert errors == [], f"Expected no errors, got: {errors}"


# ---------------------------------------------------------------------------
# 2. Check 1 -- _index.yaml missing / _index.md instead
# ---------------------------------------------------------------------------


def test_check1_index_missing(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_INDEX_MISSING fires when no _index.yaml exists."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)

    bundle = tmp_path / "design" / "no-index"
    bundle.mkdir(parents=True)
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(_VALID_NODE_BETA, encoding="utf-8")

    viols = check_bundle(bundle)
    ids = [v.check_id for v in viols]
    assert "DESIGN_INDEX_MISSING" in ids, f"Expected DESIGN_INDEX_MISSING, got: {ids}"


def test_check1_index_md_not_yaml(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_INDEX_MD_NOT_YAML fires when _index.md exists instead of _index.yaml."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)

    bundle = tmp_path / "design" / "md-index"
    bundle.mkdir(parents=True)
    (bundle / "_index.md").write_text("---\ntype: design-bundle-index\ntitle: x\n---\n", encoding="utf-8")
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")

    viols = check_bundle(bundle)
    ids = [v.check_id for v in viols]
    assert "DESIGN_INDEX_MD_NOT_YAML" in ids, f"Expected DESIGN_INDEX_MD_NOT_YAML, got: {ids}"


def test_check1_index_missing_key_no_members(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_INDEX_MISSING_KEY fires when _index.yaml lacks 'members'."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    # Point at a real schema so the SCHEMA_UNAVAILABLE fail-closed check does NOT fire here.
    monkeypatch.setattr(
        dl, "_SCHEMA_PATH",
        _REPO_ROOT / "design" / "graph-engine" / "schema" / "design-index.schema.json",
    )

    bundle = tmp_path / "design" / "bad-index"
    bundle.mkdir(parents=True)
    # Missing BOTH 'members' and 'edges' -- the checker must report ALL missing keys, not just
    # the first (finding 5: partial report bug).
    (bundle / "_index.yaml").write_text(
        "kind: design_index\ntitle: x\ndescription: y\n", encoding="utf-8"
    )
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")

    viols = check_bundle(bundle)
    missing_key_msgs = [v.message for v in viols if v.check_id == "DESIGN_INDEX_MISSING_KEY"]
    assert any("'members'" in m for m in missing_key_msgs), (
        f"Expected a 'members' missing-key violation, got: {missing_key_msgs}"
    )
    assert any("'edges'" in m for m in missing_key_msgs), (
        f"Finding 5: both missing keys must be reported, not just the first. "
        f"Got: {missing_key_msgs}"
    )


def test_check1_schema_unavailable_fails_closed(tmp_path: Path, monkeypatch) -> None:
    """Finding 1: when the schema cannot be loaded, the lint FAILS CLOSED.

    A well-formed bundle must NOT silently pass if the schema file is missing -- otherwise the
    lint is fail-OPEN (every bundle passes when the schema is gone), violating UACP's
    fail-closed thesis.
    """
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    # Point the schema path at a file that does not exist -> _load_index_schema must raise.
    monkeypatch.setattr(dl, "_SCHEMA_PATH", tmp_path / "no-such-schema.json")

    bundle = _make_valid_bundle(tmp_path)
    viols = check_bundle(bundle)
    ids = [v.check_id for v in viols]
    assert "DESIGN_INDEX_SCHEMA_UNAVAILABLE" in ids, (
        f"Finding 1: a missing schema must fire DESIGN_INDEX_SCHEMA_UNAVAILABLE (fail-closed), "
        f"got: {ids}"
    )
    unavail = [v for v in viols if v.check_id == "DESIGN_INDEX_SCHEMA_UNAVAILABLE"]
    assert all(v.severity == SEVERITY_ERROR for v in unavail), "must be an ERROR (fail-closed)"


def test_check2_member_malformed_not_silent(tmp_path: Path, monkeypatch) -> None:
    """Finding 4: a member entry that is not a string ending in .md is REPORTED, not silently
    dropped from both sides."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = tmp_path / "design" / "malformed-member"
    bundle.mkdir(parents=True)
    # members has two valid .md entries plus a malformed one (an int and a non-.md string).
    (bundle / "_index.yaml").write_text(
        textwrap.dedent("""\
            kind: design_index
            title: x
            description: y
            status: design
            governance: pre-governance-input
            timestamp: '2026-06-26'
            members:
              - 00-alpha.md
              - 01-beta.md
              - 12345
            edges: []
        """),
        encoding="utf-8",
    )
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(_NODE_BETA_NO_EDGES, encoding="utf-8")

    viols = check_bundle(bundle)
    ids = [v.check_id for v in viols]
    assert "DESIGN_MEMBERS_MALFORMED" in ids, (
        f"Finding 4: a non-string/non-.md member must fire DESIGN_MEMBERS_MALFORMED, got: {ids}"
    )


# ---------------------------------------------------------------------------
# 3. Check 2 -- members mismatch
# ---------------------------------------------------------------------------


def test_check2_members_extra_file(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_MEMBERS_MISSING fires when a top-level .md is not in members."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = tmp_path / "design" / "members-mismatch"
    bundle.mkdir(parents=True)
    # THREE edgeless nodes exist but _index.members lists only two. The ONLY defect is the
    # un-listed file (02-gamma.md) -- two members are listed so DESIGN_SINGLE_DOC cannot fire,
    # and all nodes are edgeless so no edge check can fire.
    (bundle / "_index.yaml").write_text(
        textwrap.dedent("""\
            kind: design_index
            title: x
            description: y
            status: design
            governance: pre-governance-input
            timestamp: '2026-06-26'
            members:
              - 00-alpha.md
              - 01-beta.md
            edges: []
        """),
        encoding="utf-8",
    )
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(_NODE_BETA_NO_EDGES, encoding="utf-8")
    (bundle / "02-gamma.md").write_text(_NODE_BETA_NO_EDGES, encoding="utf-8")  # unlisted

    viols = check_bundle(bundle)
    _assert_exact_check_ids(viols, {"DESIGN_MEMBERS_MISSING"})


def test_check2_members_stale_entry(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_MEMBERS_EXTRA fires when members lists a file that does not exist."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = tmp_path / "design" / "stale-member"
    bundle.mkdir(parents=True)
    # Two edgeless nodes + a ghost member entry. The ONLY defect is the stale 99-ghost.md.
    (bundle / "_index.yaml").write_text(
        textwrap.dedent("""\
            kind: design_index
            title: x
            description: y
            status: design
            governance: pre-governance-input
            timestamp: '2026-06-26'
            members:
              - 00-alpha.md
              - 01-beta.md
              - 99-ghost.md
            edges: []
        """),
        encoding="utf-8",
    )
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(_NODE_BETA_NO_EDGES, encoding="utf-8")

    viols = check_bundle(bundle)
    _assert_exact_check_ids(viols, {"DESIGN_MEMBERS_EXTRA"})


# ---------------------------------------------------------------------------
# 4. Check 3 -- fewer than 2 member nodes
# ---------------------------------------------------------------------------


def test_check3_single_doc(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_SINGLE_DOC fires when only 1 member node exists."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = tmp_path / "design" / "single-doc"
    bundle.mkdir(parents=True)
    (bundle / "_index.yaml").write_text(
        textwrap.dedent("""\
            kind: design_index
            title: x
            description: y
            status: design
            governance: pre-governance-input
            timestamp: '2026-06-26'
            members:
              - 00-alpha.md
            edges: []
        """),
        encoding="utf-8",
    )
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")

    viols = check_bundle(bundle)
    _assert_exact_check_ids(viols, {"DESIGN_SINGLE_DOC"})


# ---------------------------------------------------------------------------
# 5. Check 4 -- wrong placement
# ---------------------------------------------------------------------------


def test_check4_wrong_placement(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_WRONG_PLACEMENT fires when the bundle is not under design/."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)

    # Put the bundle under docs/ instead
    bundle = tmp_path / "docs" / "plans" / "my-bundle"
    bundle.mkdir(parents=True)
    (bundle / "_index.yaml").write_text(_VALID_INDEX, encoding="utf-8")
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(_VALID_NODE_BETA, encoding="utf-8")

    viols = check_bundle(bundle)
    ids = [v.check_id for v in viols]
    assert "DESIGN_WRONG_PLACEMENT" in ids, f"Expected DESIGN_WRONG_PLACEMENT, got: {ids}"


def test_check4_nested_placement(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_NESTED_PLACEMENT fires when bundle is nested inside design/topic/sub/."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)

    bundle = tmp_path / "design" / "topic" / "subtopic"
    bundle.mkdir(parents=True)
    (bundle / "_index.yaml").write_text(_VALID_INDEX, encoding="utf-8")
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(_VALID_NODE_BETA, encoding="utf-8")

    viols = check_bundle(bundle)
    ids = [v.check_id for v in viols]
    assert "DESIGN_NESTED_PLACEMENT" in ids, f"Expected DESIGN_NESTED_PLACEMENT, got: {ids}"


# ---------------------------------------------------------------------------
# 6. Check 5 -- node frontmatter
# ---------------------------------------------------------------------------


def test_check5_missing_required_keys(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_NODE_FM_MISSING_KEYS fires when a node lacks required frontmatter fields."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = tmp_path / "design" / "bad-fm"
    bundle.mkdir(parents=True)
    # Edgeless index + edgeless alpha so no edge check can fire. 01-beta keeps a valid
    # 'type' and 'edges: []' but drops 'description' -- the ONLY defect is the missing key.
    (bundle / "_index.yaml").write_text(_INDEX_NO_EDGES, encoding="utf-8")
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(
        textwrap.dedent("""\
            ---
            type: design
            title: Beta node
            tags: [test]
            timestamp: 2026-06-26
            edges: []
            ---
            # Beta
        """),
        encoding="utf-8",
    )

    viols = check_bundle(bundle)
    _assert_exact_check_ids(viols, {"DESIGN_NODE_FM_MISSING_KEYS"})


def test_check5_type_missing_hard_fail(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_NODE_TYPE_MISSING fires when 'type' is absent -- hard-fail."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = tmp_path / "design" / "no-type"
    bundle.mkdir(parents=True)
    # Edgeless index + edgeless alpha. 01-beta has EVERY required key except 'type' (which
    # is absent) -- 'edges: []' is present so DESIGN_NODE_FM_MISSING_KEYS does NOT fire and
    # no edge check fires. The ONLY defect is the missing 'type'.
    (bundle / "_index.yaml").write_text(_INDEX_NO_EDGES, encoding="utf-8")
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(
        textwrap.dedent("""\
            ---
            title: Beta
            description: No type field.
            tags: [test]
            timestamp: 2026-06-26
            edges: []
            ---
            # Beta
        """),
        encoding="utf-8",
    )

    viols = check_bundle(bundle)
    # 'type' missing fires BOTH the required-keys check and the dedicated type check; both are
    # the single defect (the absent 'type' field). Nothing else may fire.
    _assert_exact_check_ids(viols, {"DESIGN_NODE_FM_MISSING_KEYS", "DESIGN_NODE_TYPE_MISSING"})
    type_viols = [v for v in viols if v.check_id == "DESIGN_NODE_TYPE_MISSING"]
    assert all(v.severity == SEVERITY_ERROR for v in type_viols)


def test_check5_type_unknown_warn_only(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_NODE_TYPE_UNKNOWN fires as WARN (not error) for an unrecognised type."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = tmp_path / "design" / "unknown-type"
    bundle.mkdir(parents=True)
    (bundle / "_index.yaml").write_text(_VALID_INDEX, encoding="utf-8")
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(
        textwrap.dedent("""\
            ---
            type: some-new-type
            title: Beta
            description: New type.
            tags: [test]
            timestamp: 2026-06-26
            edges:
              - {dst: 00-alpha, rel: depends_on, provenance: derived}
            ---
            # Beta
        """),
        encoding="utf-8",
    )

    viols = check_bundle(bundle)
    type_viols = [v for v in viols if v.check_id == "DESIGN_NODE_TYPE_UNKNOWN"]
    assert type_viols, f"Expected DESIGN_NODE_TYPE_UNKNOWN, got: {[v.check_id for v in viols]}"
    assert all(v.severity == SEVERITY_WARN for v in type_viols), "type-unknown must be WARN"
    # No SEVERITY_ERROR should come from the type check
    type_errors = [v for v in viols if v.severity == SEVERITY_ERROR and "TYPE" in v.check_id]
    assert not type_errors, f"type-unknown must not produce errors: {type_errors}"


def test_check5_yaml_parse_error_in_node(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_NODE_FM_PARSE_ERROR fires when node frontmatter has a YAML syntax error."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = tmp_path / "design" / "yaml-err"
    bundle.mkdir(parents=True)
    # Edgeless index + edgeless alpha so no edge check fires. 01-beta has a YAML syntax error
    # (unquoted colons) -- the ONLY defect.
    (bundle / "_index.yaml").write_text(_INDEX_NO_EDGES, encoding="utf-8")
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(
        textwrap.dedent("""\
            ---
            type: design
            title: Bad: title: with colons
            description: Fine.
            tags: [test]
            timestamp: 2026-06-26
            edges: []
            ---
            # Beta
        """),
        encoding="utf-8",
    )

    viols = check_bundle(bundle)
    _assert_exact_check_ids(viols, {"DESIGN_NODE_FM_PARSE_ERROR"})


# ---------------------------------------------------------------------------
# 7. Check 6 -- edge mirroring
# ---------------------------------------------------------------------------


def test_check6_edge_unmirrored_in_node(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_EDGE_UNMIRRORED fires when _index has an edge not reflected in the src node.

    Scenario: _index says 01-beta depends_on 00-alpha, but 01-beta only declares
    a relates_to edge -- the required {dst: 00-alpha, rel: depends_on} is absent.
    """
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = tmp_path / "design" / "edge-unmirror"
    bundle.mkdir(parents=True)
    # _index claims 01-beta depends_on 00-alpha
    (bundle / "_index.yaml").write_text(
        textwrap.dedent("""            kind: design_index
            title: x
            description: y
            status: design
            governance: pre-governance-input
            timestamp: '2026-06-26'
            members:
              - 00-alpha.md
              - 01-beta.md
            edges:
              - {src: 01-beta, dst: 00-alpha, rel: depends_on, provenance: derived}
        """),
        encoding="utf-8",
    )
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    # 01-beta declares edges: [] -- exempt from the REVERSE (node->index) direction, so
    # DESIGN_EDGE_NOT_IN_INDEX cannot fire. The _index claims an edge the node lacks, so ONLY
    # the FORWARD direction (DESIGN_EDGE_UNMIRRORED) fires -- a clean single-check fixture.
    (bundle / "01-beta.md").write_text(
        textwrap.dedent("""            ---
            type: design
            title: Beta
            description: Declares no edges, but the index claims one.
            tags: [test]
            timestamp: 2026-06-26
            edges: []
            ---
            # Beta
        """),
        encoding="utf-8",
    )

    viols = check_bundle(bundle)
    _assert_exact_check_ids(viols, {"DESIGN_EDGE_UNMIRRORED"})
def test_check6_edge_not_in_index(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_EDGE_NOT_IN_INDEX fires when a node declares an edge not in _index."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = tmp_path / "design" / "edge-not-in-index"
    bundle.mkdir(parents=True)
    # _index has no edges at all, but 01-beta declares one
    (bundle / "_index.yaml").write_text(
        textwrap.dedent("""\
            kind: design_index
            title: x
            description: y
            status: design
            governance: pre-governance-input
            timestamp: '2026-06-26'
            members:
              - 00-alpha.md
              - 01-beta.md
            edges: []
        """),
        encoding="utf-8",
    )
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(_VALID_NODE_BETA, encoding="utf-8")

    viols = check_bundle(bundle)
    # _index edges: [] but 01-beta declares a valid edge -> only the reverse direction fires.
    _assert_exact_check_ids(viols, {"DESIGN_EDGE_NOT_IN_INDEX"})


def test_check6_invalid_rel_enum(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_EDGE_INVALID_REL fires for an unrecognised rel value."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = tmp_path / "design" / "bad-rel"
    bundle.mkdir(parents=True)
    (bundle / "_index.yaml").write_text(
        textwrap.dedent("""\
            kind: design_index
            title: x
            description: y
            status: design
            governance: pre-governance-input
            timestamp: '2026-06-26'
            members:
              - 00-alpha.md
              - 01-beta.md
            edges:
              - {src: 01-beta, dst: 00-alpha, rel: invented_rel, provenance: derived}
        """),
        encoding="utf-8",
    )
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(
        textwrap.dedent("""\
            ---
            type: design
            title: Beta
            description: Bad rel.
            tags: [test]
            timestamp: 2026-06-26
            edges:
              - {dst: 00-alpha, rel: invented_rel, provenance: derived}
            ---
            # Beta
        """),
        encoding="utf-8",
    )

    viols = check_bundle(bundle)
    # Both _index and node carry the same bad rel; the edge mirrors cleanly, so the ONLY
    # defect is the invalid rel value (fired once per side, same check_id).
    _assert_exact_check_ids(viols, {"DESIGN_EDGE_INVALID_REL"})


# ---------------------------------------------------------------------------
# 8. Check 7 -- Status/Checkpoint shape-if-present
# ---------------------------------------------------------------------------


def test_check7_checkpoint_with_date_passes(tmp_path: Path, monkeypatch) -> None:
    """A ## Status / Checkpoint section with a date does not fire a violation."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = tmp_path / "design" / "checkpoint-ok"
    bundle.mkdir(parents=True)
    (bundle / "_index.yaml").write_text(_VALID_INDEX, encoding="utf-8")
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(
        textwrap.dedent("""\
            ---
            type: design
            title: Beta
            description: Has a valid checkpoint.
            tags: [test]
            timestamp: 2026-06-26
            edges:
              - {dst: 00-alpha, rel: depends_on, provenance: derived}
            ---
            # Beta

            ## Status / Checkpoint

            > **2026-06-26 -- DESIGN.** All good here.
        """),
        encoding="utf-8",
    )

    viols = check_bundle(bundle)
    checkpoint_viols = [v for v in viols if v.check_id == "DESIGN_CHECKPOINT_NO_DATE"]
    assert not checkpoint_viols, f"Unexpected checkpoint violations: {checkpoint_viols}"


def test_check7_checkpoint_without_date(tmp_path: Path, monkeypatch) -> None:
    """DESIGN_CHECKPOINT_NO_DATE fires when the section exists but lacks a YYYY-MM-DD date."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = tmp_path / "design" / "checkpoint-no-date"
    bundle.mkdir(parents=True)
    (bundle / "_index.yaml").write_text(_VALID_INDEX, encoding="utf-8")
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(
        textwrap.dedent("""\
            ---
            type: design
            title: Beta
            description: Has a checkpoint without a date.
            tags: [test]
            timestamp: 2026-06-26
            edges:
              - {dst: 00-alpha, rel: depends_on, provenance: derived}
            ---
            # Beta

            ## Status / Checkpoint

            Work in progress -- no date here.
        """),
        encoding="utf-8",
    )

    viols = check_bundle(bundle)
    ids = [v.check_id for v in viols]
    assert "DESIGN_CHECKPOINT_NO_DATE" in ids, (
        f"Expected DESIGN_CHECKPOINT_NO_DATE, got: {ids}"
    )


def test_check7_impossible_date_fails(tmp_path: Path, monkeypatch) -> None:
    """Finding 6: a ## Status / Checkpoint section whose only date is impossible (9999-99-99)
    must fail -- the date must be a real calendar date, not just a YYYY-MM-DD-shaped token."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = tmp_path / "design" / "checkpoint-impossible-date"
    bundle.mkdir(parents=True)
    (bundle / "_index.yaml").write_text(_VALID_INDEX, encoding="utf-8")
    (bundle / "00-alpha.md").write_text(_VALID_NODE_ALPHA, encoding="utf-8")
    (bundle / "01-beta.md").write_text(
        textwrap.dedent("""\
            ---
            type: design
            title: Beta
            description: Has a checkpoint with only an impossible date.
            tags: [test]
            timestamp: 2026-06-26
            edges:
              - {dst: 00-alpha, rel: depends_on, provenance: derived}
            ---
            # Beta

            ## Status / Checkpoint

            > **9999-99-99 -- DESIGN.** Not a real date.
        """),
        encoding="utf-8",
    )

    viols = check_bundle(bundle)
    ids = [v.check_id for v in viols]
    assert "DESIGN_CHECKPOINT_NO_DATE" in ids, (
        f"Finding 6: 9999-99-99 is not a real date and must fire DESIGN_CHECKPOINT_NO_DATE, "
        f"got: {ids}"
    )


def test_check7_no_checkpoint_heading_passes(tmp_path: Path, monkeypatch) -> None:
    """A node with no ## Status / Checkpoint heading is exempt -- no violation."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    _use_permissive_schema(tmp_path, monkeypatch)

    bundle = _make_valid_bundle(tmp_path)
    viols = check_bundle(bundle)
    checkpoint_viols = [v for v in viols if v.check_id == "DESIGN_CHECKPOINT_NO_DATE"]
    assert not checkpoint_viols, f"Unexpected: {checkpoint_viols}"


# ---------------------------------------------------------------------------
# Non-vacuity guard -- the violator tests fail for the right reason
# ---------------------------------------------------------------------------


def test_nonvacuity_valid_bundle_has_no_violations(tmp_path: Path, monkeypatch) -> None:
    """Confirm the valid bundle fixture is actually violation-free (non-vacuity of the corpus test)."""
    import engines.domain.design_lint as dl
    monkeypatch.setattr(dl, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(dl, "_SCHEMA_PATH", _REPO_ROOT / "design" / "graph-engine" / "schema" / "design-index.schema.json")

    bundle = _make_valid_bundle(tmp_path)
    viols = check_bundle(bundle)
    errors = [v for v in viols if v.severity == SEVERITY_ERROR]
    # Remove the index to prove the test is not vacuous
    (bundle / "_index.yaml").unlink()
    viols_broken = check_bundle(bundle)
    ids_broken = [v.check_id for v in viols_broken]
    assert "DESIGN_INDEX_MISSING" in ids_broken, "Non-vacuity: removing _index must fire"
    # Restore would be needed for the valid test -- but we already checked above
    assert errors == [], f"Valid fixture must have no errors, got: {errors}"


# ---------------------------------------------------------------------------
# Corpus test -- runs check_bundle on every real design bundle
# ---------------------------------------------------------------------------

# Allowlist: bundle-name -> reason
# Each entry must still EXIST (the allowlist itself is checked for staleness).
# Violations listed are expected; any new violation outside this allowlist is a failure.
KNOWN_NONCONFORMING: dict[str, str] = {
    "work-unit-status": (
        "_index.md instead of _index.yaml (RECONSTRUCT needed: kind+members+edges missing); "
        "node type 'design-node' (unknown); nodes missing 'description' and 'edges' fields"
    ),
    "graph-engine": (
        "4 nodes with YAML-invalid frontmatter (unquoted colons in title/description values: "
        "16a-control-plane-schema.md, 25-schema-source-spec.md, 28-component-registry.md); "
        "2 nodes missing 'edges' key (01-context-intent.md, 18-glossary.md)"
    ),
    "verification-method": (
        "14-council-method.md has YAML-invalid frontmatter (unquoted colon in description)"
    ),
    "bridge-containment": (
        "_index.yaml scope block has unexpected 'in'/'out' keys (schema violation); "
        "4 nodes declare edges not mirrored in _index (edge drift: relates_to edges absent)"
    ),
    "codeflair": (
        "02-probes.md missing an edge that _index claims (DESIGN_EDGE_UNMIRRORED); "
        "15-completion-roadmap.md declares 3 edges not in _index (edge drift)"
    ),
    "entrypoints": (
        "both nodes declare edges absent from _index (edge drift); "
        "00-unified-entrypoints.md has a cross-bundle edge dst"
    ),
    "handoff": (
        "_index.yaml scope block has unexpected 'in'/'out' keys (schema violation); "
        "2 nodes declare edges absent from _index (edge drift)"
    ),
}


def _bundle_names() -> list[str]:
    return sorted(d.name for d in _DESIGN_DIR.iterdir() if d.is_dir())


@pytest.mark.parametrize("bundle_name", _bundle_names())
def test_corpus_conforming_bundles(bundle_name: str) -> None:
    """Conforming bundles (not in KNOWN_NONCONFORMING) must have zero ERROR-severity violations."""
    if bundle_name in KNOWN_NONCONFORMING:
        pytest.skip(f"allowlisted: {KNOWN_NONCONFORMING[bundle_name]}")

    bundle_path = _DESIGN_DIR / bundle_name
    viols = check_bundle(bundle_path)
    errors = [v for v in viols if v.severity == SEVERITY_ERROR]

    report_lines = [
        f"  [{v.severity.upper()}] {v.check_id}: {v.message}" for v in viols
    ]
    report = "\n".join(report_lines)
    assert not errors, (
        f"Bundle '{bundle_name}' has {len(errors)} error violation(s):\n{report}"
    )


@pytest.mark.parametrize("name", sorted(KNOWN_NONCONFORMING))
def test_corpus_allowlist_entries_still_nonconforming(name: str) -> None:
    """Finding 2: each allowlisted bundle must still produce >=1 ERROR-severity violation TODAY.

    A mere directory-exists check is vacuous -- a fully-reconciled (clean) bundle could stay
    allowlisted forever. By asserting it still has an error, the moment a bundle is fixed this
    test goes RED and forces removing it from KNOWN_NONCONFORMING.
    """
    bundle_dir = _DESIGN_DIR / name
    assert bundle_dir.is_dir(), (
        f"Allowlist entry '{name}' no longer exists -- remove it from KNOWN_NONCONFORMING"
    )
    viols = check_bundle(bundle_dir)
    errors = [v for v in viols if v.severity == SEVERITY_ERROR]
    assert errors, (
        f"Allowlisted bundle '{name}' now has ZERO error violations -- it has been reconciled. "
        f"Remove it from KNOWN_NONCONFORMING so the gate enforces it."
    )


def test_corpus_uacp_design_dogfood_passes() -> None:
    """The uacp-design bundle itself (the first dogfood) must pass with zero errors."""
    bundle_path = _DESIGN_DIR / "uacp-design"
    viols = check_bundle(bundle_path)
    errors = [v for v in viols if v.severity == SEVERITY_ERROR]
    report = "\n".join(f"  [{v.severity.upper()}] {v.check_id}: {v.message}" for v in viols)
    assert not errors, (
        f"uacp-design (dogfood) has {len(errors)} error violation(s):\n{report}"
    )


def test_corpus_full_violation_report(capsys) -> None:
    """Print the full violation inventory across all design bundles (informational)."""
    all_names = _bundle_names()
    report_lines = [f"=== Design bundle lint report ({len(all_names)} bundles) ==="]

    total_errors = 0
    total_warns = 0

    for name in all_names:
        bundle_path = _DESIGN_DIR / name
        viols = check_bundle(bundle_path)
        errors = [v for v in viols if v.severity == SEVERITY_ERROR]
        warns = [v for v in viols if v.severity == SEVERITY_WARN]
        total_errors += len(errors)
        total_warns += len(warns)
        status = "PASS" if not errors else "FAIL"
        allowlist_note = " [ALLOWLISTED]" if name in KNOWN_NONCONFORMING else ""
        report_lines.append(f"\n{status}{allowlist_note} {name}/")
        for v in viols:
            report_lines.append(f"  [{v.severity.upper()}] {v.check_id}: {v.message}")

    report_lines.append(
        f"\nSummary: {total_errors} errors, {total_warns} warns across {len(all_names)} bundles"
    )
    report_lines.append(f"Allowlisted: {sorted(KNOWN_NONCONFORMING.keys())}")

    print("\n".join(report_lines))
    # This test always passes -- it is a report, not an assertion
    assert True
