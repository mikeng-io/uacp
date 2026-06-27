"""design_lint — decidable structure gate for UACP design bundles.

Implements the 7 checks specified in design/uacp-design/21-lint.md (the measure
half of the comprehend->measure->serialize split). Each check is deterministically
decidable from the files; no semantic / quality judgment is performed here.

The single public entry point is ``check_bundle(bundle_path)`` which returns a
list of ``Violation`` named-tuples. An empty list means PASS.

Schema used for _index.yaml:
    design/graph-engine/schema/design-index.schema.json

Node-type vocabulary (two-tier, per 21-lint.md check 5 + 10-taxonomy-audit.md):
    CORE (hard-fail if type present but unknown): analysis, design, contract,
        reference, decision, pattern
    KNOWN ONE-OFFS (warn-only if type is one of these): roadmap, lessons, evidence
    Missing / malformed type = HARD-FAIL regardless.
"""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path
from typing import NamedTuple

import yaml
from jsonschema import Draft202012Validator

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

SEVERITY_ERROR = "error"  # structural hard-fail
SEVERITY_WARN = "warn"  # type-unknown warn-only


class Violation(NamedTuple):
    bundle_path: Path
    check_id: str
    severity: str  # "error" | "warn"
    message: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Resolved relative to this file's location inside the repo
_HERE = Path(__file__).resolve()
# Walk up: engines/domain/ -> engines/ -> scripts/ -> uacp-core/ -> skills/ -> repo-root
_REPO_ROOT = _HERE.parents[5]
_SCHEMA_PATH = _REPO_ROOT / "design" / "graph-engine" / "schema" / "design-index.schema.json"

# Node `type` vocabulary (10-taxonomy-audit.md + 22-rollout-and-decisions.md decision 4)
_CORE_TYPES: frozenset[str] = frozenset(
    {"analysis", "design", "contract", "reference", "decision", "pattern"}
)
_KNOWN_ONEOFF_TYPES: frozenset[str] = frozenset({"roadmap", "lessons", "evidence"})
_ALLOWED_TYPES: frozenset[str] = _CORE_TYPES | _KNOWN_ONEOFF_TYPES

# Node frontmatter required keys (check 5)
_REQUIRED_FM_KEYS: frozenset[str] = frozenset(
    {"type", "title", "description", "tags", "timestamp", "edges"}
)

# Edge rel / provenance enums -- mirrored from design-index.schema.json
_VALID_RELS: frozenset[str] = frozenset(
    {
        "motivated_by",
        "decides_on",
        "realizes",
        "depends_on",
        "consumes",
        "extends",
        "sequences",
        "relates_to",
        "corrects",
        "grounds",
        "supersedes",
    }
)
_VALID_PROVENANCES: frozenset[str] = frozenset({"derived", "parsed", "asserted", "inferred"})

# Date pattern for Status/Checkpoint section (check 7)
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")

# Status/Checkpoint heading pattern (check 7) -- case-insensitive, optional spaces
_CHECKPOINT_HEADING_RE = re.compile(
    r"^##\s+Status\s*/\s*Checkpoint\b", re.IGNORECASE | re.MULTILINE
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _SchemaUnavailableError(Exception):
    """Raised when the design_index schema cannot be loaded -- forces fail-closed."""


def _load_index_schema() -> dict:
    """Load the design_index JSON schema.

    Fail-CLOSED: any failure to read/parse the schema raises _SchemaUnavailableError so the
    caller emits a hard error rather than silently skipping schema validation (which would
    let every bundle pass when the schema is missing/unreadable -- a fail-OPEN bug).
    """
    try:
        text = _SCHEMA_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise _SchemaUnavailableError(f"cannot read schema at {_SCHEMA_PATH}: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise _SchemaUnavailableError(f"schema at {_SCHEMA_PATH} is not valid JSON: {exc}") from exc


def _parse_frontmatter(text: str) -> tuple[dict | None, str | None]:
    """Parse YAML frontmatter from a markdown file.

    Returns ``(frontmatter_dict, error_message)``. On success the error is None;
    on failure the dict is None and the error describes the problem.
    """
    if not text.startswith("---"):
        return None, "missing frontmatter -- file must start with '---'"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, "malformed frontmatter -- no closing '---' found"
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        return None, f"YAML parse error: {exc}"
    if not isinstance(fm, dict):
        return None, "frontmatter did not parse as a YAML mapping"
    return fm, None


def _top_level_nodes(bundle_path: Path) -> list[Path]:
    """Return top-level *.md files under bundle_path, excluding _index* files."""
    return sorted(p for p in bundle_path.glob("*.md") if not p.name.startswith("_index"))


def _has_real_date(text: str) -> bool:
    """True iff text contains a YYYY-MM-DD token that is a real calendar date.

    The regex finds candidate tokens; ``strptime`` rejects impossible dates such as
    9999-99-99 (decidable -- no semantic judgment). Any single valid token suffices.
    """
    for match in _DATE_RE.finditer(text):
        try:
            datetime.date.fromisoformat(match.group(0))
        except ValueError:
            continue
        return True
    return False


# ---------------------------------------------------------------------------
# The 7 checks
# ---------------------------------------------------------------------------


def _check1_index(bundle_path: Path, viols: list[Violation]) -> dict | None:
    """Check 1: exactly one _index.yaml (not .md); validates against design_index schema.

    Returns the parsed index dict on success, or None if fatally broken.
    """
    # Check for _index.md instead of _index.yaml (a known violation)
    if (bundle_path / "_index.md").exists() and not (bundle_path / "_index.yaml").exists():
        viols.append(
            Violation(
                bundle_path,
                "DESIGN_INDEX_MD_NOT_YAML",
                SEVERITY_ERROR,
                "_index file is _index.md -- must be _index.yaml (not a mere extension rename; "
                "the file needs kind:design_index + members + edges)",
            )
        )
        return None

    if not (bundle_path / "_index.yaml").exists():
        viols.append(
            Violation(
                bundle_path,
                "DESIGN_INDEX_MISSING",
                SEVERITY_ERROR,
                "no _index.yaml found -- bundle must have exactly one _index.yaml",
            )
        )
        return None

    # Extra _index* files alongside the canonical one
    extra = sorted(
        p for p in bundle_path.iterdir() if p.name.startswith("_index") and p.name != "_index.yaml"
    )
    if extra:
        viols.append(
            Violation(
                bundle_path,
                "DESIGN_INDEX_EXTRA",
                SEVERITY_ERROR,
                f"extra _index* files alongside _index.yaml: {[p.name for p in extra]}",
            )
        )

    # Parse the _index.yaml -- fail-closed on missing keys
    try:
        raw = (bundle_path / "_index.yaml").read_text(encoding="utf-8")
        index = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        viols.append(
            Violation(
                bundle_path,
                "DESIGN_INDEX_PARSE_ERROR",
                SEVERITY_ERROR,
                f"_index.yaml YAML parse error: {exc}",
            )
        )
        return None

    if not isinstance(index, dict):
        viols.append(
            Violation(
                bundle_path,
                "DESIGN_INDEX_NOT_MAPPING",
                SEVERITY_ERROR,
                "_index.yaml did not parse as a YAML mapping",
            )
        )
        return None

    # Fail-closed on absent kind/members/edges (per 21-lint.md + the work-unit-status lesson).
    # Collect ALL missing keys before bailing -- a bundle missing both members and edges must
    # report both, not just the first.
    missing_keys = [key for key in ("kind", "members", "edges") if key not in index]
    for key in missing_keys:
        viols.append(
            Violation(
                bundle_path,
                "DESIGN_INDEX_MISSING_KEY",
                SEVERITY_ERROR,
                f"_index.yaml missing required key '{key}' -- must have kind, members, edges",
            )
        )
    if missing_keys:
        return None  # can't proceed without these

    # Schema validation -- fail-CLOSED if the schema itself cannot be loaded.
    try:
        schema = _load_index_schema()
    except _SchemaUnavailableError as exc:
        viols.append(
            Violation(
                bundle_path,
                "DESIGN_INDEX_SCHEMA_UNAVAILABLE",
                SEVERITY_ERROR,
                f"design_index schema unavailable -- cannot validate _index.yaml: {exc}",
            )
        )
        return index  # other (non-schema) checks may still run; do not fail-open

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(index), key=lambda e: list(e.path))
    for err in errors:
        path = ".".join(str(p) for p in err.path) or "(root)"
        viols.append(
            Violation(
                bundle_path,
                "DESIGN_INDEX_SCHEMA_VIOLATION",
                SEVERITY_ERROR,
                f"_index.yaml schema violation at {path}: {err.message}",
            )
        )

    return index


def _valid_member_names(index: dict, bundle_path: Path, viols: list[Violation]) -> set[str]:
    """Return the set of well-formed member names, emitting DESIGN_MEMBERS_MALFORMED for any
    entry that is not a string ending in .md (so malformed entries never vanish silently)."""
    declared: set[str] = set()
    for m in index.get("members", []):
        if isinstance(m, str) and m.endswith(".md"):
            declared.add(m)
        else:
            viols.append(
                Violation(
                    bundle_path,
                    "DESIGN_MEMBERS_MALFORMED",
                    SEVERITY_ERROR,
                    f"_index.members entry {m!r} is malformed -- must be a string ending in '.md'",
                )
            )
    return declared


def _check2_members(bundle_path: Path, index: dict, viols: list[Violation]) -> None:
    """Check 2: _index.members == top-level *.md files (excluding _index*)."""
    declared = _valid_member_names(index, bundle_path, viols)
    actual = {p.name for p in _top_level_nodes(bundle_path)}

    missing_from_members = actual - declared
    extra_in_members = declared - actual

    if missing_from_members:
        viols.append(
            Violation(
                bundle_path,
                "DESIGN_MEMBERS_MISSING",
                SEVERITY_ERROR,
                f"top-level .md files not in _index.members: {sorted(missing_from_members)}",
            )
        )
    if extra_in_members:
        viols.append(
            Violation(
                bundle_path,
                "DESIGN_MEMBERS_EXTRA",
                SEVERITY_ERROR,
                f"_index.members entries with no corresponding top-level .md file: "
                f"{sorted(extra_in_members)}",
            )
        )


def _check3_min_nodes(bundle_path: Path, index: dict, viols: list[Violation]) -> None:
    """Check 3: >=2 member nodes (must be a BUNDLE, not a single doc)."""
    # Count only well-formed members; malformed entries are reported by check 2, not here.
    members = [m for m in index.get("members", []) if isinstance(m, str) and m.endswith(".md")]
    if len(members) < 2:
        viols.append(
            Violation(
                bundle_path,
                "DESIGN_SINGLE_DOC",
                SEVERITY_ERROR,
                f"bundle has only {len(members)} member node(s) -- a design must be >=2 nodes "
                f"(the 100+x miss: single-doc is not a bundle)",
            )
        )


def _check4_placement(bundle_path: Path, viols: list[Violation]) -> None:
    """Check 4: bundle must be directly under design/<topic>/ (not nested, not docs/)."""
    resolved = bundle_path.resolve()
    design_dir = _REPO_ROOT / "design"
    try:
        rel = resolved.relative_to(design_dir)
    except ValueError:
        viols.append(
            Violation(
                bundle_path,
                "DESIGN_WRONG_PLACEMENT",
                SEVERITY_ERROR,
                f"bundle is not under design/ (repo root: {_REPO_ROOT})",
            )
        )
        return

    # rel.parts should be exactly one component (the topic dir name)
    if len(rel.parts) != 1:
        viols.append(
            Violation(
                bundle_path,
                "DESIGN_NESTED_PLACEMENT",
                SEVERITY_ERROR,
                f"bundle is nested ({rel}) -- must be directly under design/<topic>/",
            )
        )


def _check5_node_frontmatter(bundle_path: Path, viols: list[Violation]) -> None:
    """Check 5: every top-level node has required frontmatter keys; two-tier type check."""
    for node in _top_level_nodes(bundle_path):
        try:
            text = node.read_text(encoding="utf-8")
        except OSError as exc:
            viols.append(
                Violation(
                    bundle_path,
                    "DESIGN_NODE_READ_ERROR",
                    SEVERITY_ERROR,
                    f"{node.name}: cannot read file: {exc}",
                )
            )
            continue

        fm, err = _parse_frontmatter(text)
        if err is not None or fm is None:
            viols.append(
                Violation(
                    bundle_path,
                    "DESIGN_NODE_FM_PARSE_ERROR",
                    SEVERITY_ERROR,
                    f"{node.name}: {err or 'frontmatter could not be parsed'}",
                )
            )
            continue

        # Required keys
        missing = _REQUIRED_FM_KEYS - set(fm.keys())
        if missing:
            viols.append(
                Violation(
                    bundle_path,
                    "DESIGN_NODE_FM_MISSING_KEYS",
                    SEVERITY_ERROR,
                    f"{node.name}: missing required frontmatter keys: {sorted(missing)}",
                )
            )

        # Two-tier type check
        if "type" not in fm or fm["type"] is None:
            viols.append(
                Violation(
                    bundle_path,
                    "DESIGN_NODE_TYPE_MISSING",
                    SEVERITY_ERROR,
                    f"{node.name}: 'type' key is absent or null -- hard-fail",
                )
            )
        elif not isinstance(fm["type"], str) or not fm["type"].strip():
            viols.append(
                Violation(
                    bundle_path,
                    "DESIGN_NODE_TYPE_MALFORMED",
                    SEVERITY_ERROR,
                    f"{node.name}: 'type' value {fm['type']!r} is malformed -- must be a "
                    f"non-empty string -- hard-fail",
                )
            )
        elif fm["type"] not in _ALLOWED_TYPES:
            # Warn-only for unknown types (vocabulary not closed in v1)
            viols.append(
                Violation(
                    bundle_path,
                    "DESIGN_NODE_TYPE_UNKNOWN",
                    SEVERITY_WARN,
                    f"{node.name}: 'type' value {fm['type']!r} is not in the known vocabulary "
                    f"{sorted(_ALLOWED_TYPES)} -- warn-only (vocabulary not closed in v1)",
                )
            )


def _check6_edges_mirror(bundle_path: Path, index: dict, viols: list[Violation]) -> None:
    """Check 6: edges mirror on {dst, rel} only.

    For each _index edge {src,dst,rel}, node `src` must carry a frontmatter edge {dst,rel}.
    For each node out-edge {dst,rel}, that edge must appear in _index with src=<node-id>.
    A node with edges: [] is EXEMPT from the forward direction.
    rel/provenance values must be in their enums.
    """
    index_edges = index.get("edges") or []

    # Build a set of (src, dst, rel) from _index for reverse lookup
    index_edge_set: set[tuple[str, str, str]] = set()
    for edge in index_edges:
        if not isinstance(edge, dict):
            continue
        src = edge.get("src", "")
        dst = edge.get("dst", "")
        rel = edge.get("rel", "")
        prov = edge.get("provenance", "")
        # Validate enum values in _index edges
        if rel and rel not in _VALID_RELS:
            viols.append(
                Violation(
                    bundle_path,
                    "DESIGN_EDGE_INVALID_REL",
                    SEVERITY_ERROR,
                    f"_index edge {src}->{dst}: rel {rel!r} not in allowed vocabulary "
                    f"{sorted(_VALID_RELS)}",
                )
            )
        if prov and prov not in _VALID_PROVENANCES:
            viols.append(
                Violation(
                    bundle_path,
                    "DESIGN_EDGE_INVALID_PROV",
                    SEVERITY_ERROR,
                    f"_index edge {src}->{dst}: provenance {prov!r} not in allowed vocabulary "
                    f"{sorted(_VALID_PROVENANCES)}",
                )
            )
        if src and dst and rel:
            index_edge_set.add((src, dst, rel))

    # For each _index edge, verify the src node carries {dst, rel}
    for edge in index_edges:
        if not isinstance(edge, dict):
            continue
        src = edge.get("src", "")
        dst = edge.get("dst", "")
        rel = edge.get("rel", "")
        if not (src and dst and rel):
            continue

        src_file = bundle_path / (src + ".md")
        if not src_file.exists():
            viols.append(
                Violation(
                    bundle_path,
                    "DESIGN_EDGE_SRC_MISSING",
                    SEVERITY_ERROR,
                    f"_index edge src={src!r} but {src}.md does not exist",
                )
            )
            continue

        try:
            text = src_file.read_text(encoding="utf-8")
        except OSError:
            continue
        fm, err = _parse_frontmatter(text)
        if err or fm is None:
            continue  # frontmatter parse error already reported in check 5

        node_edges = fm.get("edges") or []
        # NOTE: the empty-edges exemption is FORWARD-DIRECTION only (node->index).
        # If _index claims this node is a src, the node MUST carry the matching edge --
        # even if edges: [] (a node that declares edges:[] but is listed as src in _index
        # has contradictory state: the index says it has an edge but the node denies it).
        found = any(
            isinstance(e, dict) and e.get("dst") == dst and e.get("rel") == rel for e in node_edges
        )
        if not found:
            viols.append(
                Violation(
                    bundle_path,
                    "DESIGN_EDGE_UNMIRRORED",
                    SEVERITY_ERROR,
                    f"{src}.md is missing frontmatter edge "
                    f"{{dst: {dst!r}, rel: {rel!r}}} "
                    f"(present in _index but not in node)",
                )
            )

    # Reverse: each node out-edge must appear in _index
    for node in _top_level_nodes(bundle_path):
        node_id = node.stem
        try:
            text = node.read_text(encoding="utf-8")
        except OSError:
            continue
        fm, err = _parse_frontmatter(text)
        if err or fm is None:
            continue

        node_edges = fm.get("edges")
        if not node_edges:
            continue  # edges: [] or absent -- exempt

        for e in node_edges:
            if not isinstance(e, dict):
                continue
            dst = e.get("dst", "")
            rel = e.get("rel", "")
            prov = e.get("provenance", "")
            # Validate enum values in node edges
            if rel and rel not in _VALID_RELS:
                viols.append(
                    Violation(
                        bundle_path,
                        "DESIGN_EDGE_INVALID_REL",
                        SEVERITY_ERROR,
                        f"{node.name} edge ->{dst}: rel {rel!r} not in allowed vocabulary",
                    )
                )
            if prov and prov not in _VALID_PROVENANCES:
                viols.append(
                    Violation(
                        bundle_path,
                        "DESIGN_EDGE_INVALID_PROV",
                        SEVERITY_ERROR,
                        f"{node.name} edge ->{dst}: provenance {prov!r} not in allowed vocabulary",
                    )
                )
            if dst and rel:
                if (node_id, dst, rel) not in index_edge_set:
                    viols.append(
                        Violation(
                            bundle_path,
                            "DESIGN_EDGE_NOT_IN_INDEX",
                            SEVERITY_ERROR,
                            f"{node.name} declares edge {{dst: {dst!r}, rel: {rel!r}}} "
                            f"but no matching _index edge "
                            f"{{src: {node_id!r}, dst: {dst!r}, rel: {rel!r}}} exists",
                        )
                    )


def _check7_checkpoint_shape(bundle_path: Path, viols: list[Violation]) -> None:
    """Check 7: if a node has a '## Status / Checkpoint' heading, it must contain a date.

    Absence of the heading is fine. Presence without a date is a violation.
    """
    for node in _top_level_nodes(bundle_path):
        try:
            text = node.read_text(encoding="utf-8")
        except OSError:
            continue

        match = _CHECKPOINT_HEADING_RE.search(text)
        if not match:
            continue  # no heading -- exempt

        # Heading found -- must have a date in the section body
        section_start = match.end()
        # Find the next ## heading after this one
        next_heading = re.search(r"\n##\s", text[section_start:])
        section_end = section_start + next_heading.start() if next_heading else len(text)
        section_body = text[section_start:section_end]

        if not _has_real_date(section_body):
            viols.append(
                Violation(
                    bundle_path,
                    "DESIGN_CHECKPOINT_NO_DATE",
                    SEVERITY_ERROR,
                    f"{node.name}: '## Status / Checkpoint' section found but contains "
                    f"no valid YYYY-MM-DD date",
                )
            )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def check_bundle(bundle_path: Path) -> list[Violation]:
    """Run all 7 design-bundle lint checks on bundle_path.

    Returns a list of Violation namedtuples. Empty list = PASS.

    Checks are run in order. Checks 2/3/6 are skipped if check 1 fails fatally
    (no usable index). Check 5 and 7 run on nodes independently of the index.
    """
    bundle_path = bundle_path.resolve()
    viols: list[Violation] = []

    # Check 4: placement (runs first -- independent of index)
    _check4_placement(bundle_path, viols)

    # Check 1: _index exists + conforms
    index = _check1_index(bundle_path, viols)

    if index is not None:
        # Check 2: members == files
        _check2_members(bundle_path, index, viols)
        # Check 3: >=2 member nodes
        _check3_min_nodes(bundle_path, index, viols)
        # Check 6: edge mirroring
        _check6_edges_mirror(bundle_path, index, viols)

    # Check 5: node frontmatter (independent of index)
    _check5_node_frontmatter(bundle_path, viols)

    # Check 7: checkpoint shape-if-present (independent of index)
    _check7_checkpoint_shape(bundle_path, viols)

    return viols
