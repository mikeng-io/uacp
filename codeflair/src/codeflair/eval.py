"""Codeflair eval harness — recall@K over the labeled seed-set (CF-D5 / 05-benchmark).

The bake-off's primary metric is **recall@K of the ground-truth node set**, REPORTED
SPLIT BY PROVENANCE (``parsed`` vs ``inferred``) so it tests whether ranking the inferred
subset is hard enough to ever justify an LLM (it is not, per CF-D11 — Policy D is the
default). This module loads ``design/codeflair/eval/seed-set.yaml``, runs Codeflair's
deterministic ``expand`` from each pair's seed, and computes recall@K of the labeled
``must_find`` nodes among the top-K heatmap symbols.

**Hermetic + deterministic.** A real multi-language index of this repo needs SCIP /
tree-sitter (absent in the dev venv), so pairs that reference the real repo carry no
``fixture`` and are reported **gated** (awaiting a built index). Pairs that DO carry a
``fixture`` (a known-by-construction in-store graph, whose shape is grounded in a real
derivation — see each pair's ``derivation``) are **exercised**: the harness builds the
store, runs the engine, and measures recall. Same seed-set -> byte-identical numbers.

CF-D9: this harness imports only ``codeflair`` + the stdlib — zero dependency on UACP and
zero third-party dependency (the seed-set is parsed by a tiny in-module YAML subset reader,
since the dev venv ships no PyYAML).

**HONESTY (F6): the exercised baseline is CIRCULAR.** A by-construction fixture's blast
radius is known *because we built the graph* — so the recall number validates that the
harness + Policy-D MECHANICS work, NOT that Codeflair retrieves the right code on a real
repo. The non-circular, real-grounded baseline is still OUTSTANDING: it needs a built
SCIP/tree-sitter index of the repo (the **gated** pairs) plus human inter-labeler
adjudication (the CF-D5 build gate). Never cite the exercised number as retrieval quality.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from codeflair.expand import expand
from codeflair.store import Edge, Store, Symbol

# --------------------------------------------------------------------------------------
# Tiny dependency-free YAML subset reader.
#
# The seed-set is authored in a deliberately restricted block-style subset so this reader
# stays small and correct (the dev venv has no PyYAML and codeflair has zero deps). It
# supports: full-line and quote-aware trailing ``#`` comments; 2-space-indented block
# mappings and block sequences; double-quoted or bare scalars (int / float / bool / null
# coerced); and single-line inline flow lists ``[a, b, c]`` / ``[]``. It does NOT support
# flow maps, anchors, aliases, or multi-line scalars — the seed-set avoids them.
# --------------------------------------------------------------------------------------

_Line = tuple[int, str]  # (indent, stripped content)


def _strip_comment(line: str) -> str:
    """Drop a trailing ``#`` comment, but never one inside a double-quoted string."""
    out: list[str] = []
    in_quote = False
    for i, ch in enumerate(line):
        if ch == '"' and (i == 0 or line[i - 1] != "\\"):
            in_quote = not in_quote
        if ch == "#" and not in_quote and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _coerce(token: str) -> object:
    t = token.strip()
    if len(t) >= 2 and t[0] == '"' and t[-1] == '"':
        return t[1:-1].replace('\\"', '"')
    if t in ("null", "~", ""):
        return None
    if t in ("true", "True"):
        return True
    if t in ("false", "False"):
        return False
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        pass
    return t


def _parse_value(token: str) -> object:
    """A right-hand-side scalar or single-line inline flow list."""
    t = token.strip()
    if t.startswith("[") and t.endswith("]"):
        inner = t[1:-1].strip()
        if not inner:
            return []
        return [_coerce(part) for part in inner.split(",")]
    return _coerce(t)


def _tokenize(text: str) -> list[_Line]:
    lines: list[_Line] = []
    for raw in text.splitlines():
        stripped = _strip_comment(raw)
        if stripped.strip() == "":
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        lines.append((indent, stripped.strip()))
    return lines


def _parse_node(lines: list[_Line], i: int, indent: int) -> tuple[object, int]:
    if lines[i][1].startswith("- "):
        return _parse_sequence(lines, i, indent)
    return _parse_mapping(lines, i, indent)


def _parse_sequence(lines: list[_Line], i: int, indent: int) -> tuple[list[object], int]:
    items: list[object] = []
    while i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
        rest = lines[i][1][2:].strip()
        j = i + 1
        block: list[_Line] = []
        while j < len(lines) and lines[j][0] > indent:
            block.append(lines[j])
            j += 1
        if rest.startswith("["):
            items.append(_parse_value(rest))
        elif ": " in rest or rest.endswith(":"):
            synthetic: list[_Line] = [(indent + 2, rest), *block]
            value, _ = _parse_mapping(synthetic, 0, indent + 2)
            items.append(value)
        elif block:
            value, _ = _parse_node(block, 0, block[0][0])
            items.append(value)
        else:
            items.append(_parse_value(rest))
        i = j
    return items, i


def _parse_mapping(lines: list[_Line], i: int, indent: int) -> tuple[dict[str, object], int]:
    result: dict[str, object] = {}
    while i < len(lines) and lines[i][0] == indent and not lines[i][1].startswith("- "):
        key, _, val = lines[i][1].partition(":")
        key = key.strip()
        val = val.strip()
        if val:
            result[key] = _parse_value(val)
            i += 1
        elif i + 1 < len(lines) and lines[i + 1][0] > indent:
            child, i = _parse_node(lines, i + 1, lines[i + 1][0])
            result[key] = child
        else:
            result[key] = None
            i += 1
    return result, i


def load_yaml_subset(text: str) -> dict[str, object]:
    """Parse the seed-set YAML subset into plain dicts/lists/scalars."""
    lines = _tokenize(text)
    if not lines:
        return {}
    value, _ = _parse_mapping(lines, 0, lines[0][0])
    return value


# --------------------------------------------------------------------------------------
# Seed-set model
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class GroundTruthNode:
    node: str
    provenance: str  # parsed | inferred
    via: str = ""


@dataclass(frozen=True)
class Pair:
    id: str
    layer: str
    requires: tuple[str, ...]
    k: int
    derivation: str
    adjudication: str
    must_find: tuple[GroundTruthNode, ...]
    fixture: Mapping[str, object] | None  # exercised iff present
    basis: str  # real-repo | real-derived-fixture | constructed

    @property
    def exercised(self) -> bool:
        return self.fixture is not None


@dataclass(frozen=True)
class SeedSet:
    repo: str
    repo_commit: str
    default_k: int
    pairs: tuple[Pair, ...]


def _as_gt_nodes(raw: object) -> tuple[GroundTruthNode, ...]:
    if not isinstance(raw, list):
        return ()
    nodes: list[GroundTruthNode] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        node = str(item.get("node", ""))
        if not node:
            continue
        nodes.append(
            GroundTruthNode(
                node=node,
                provenance=str(item.get("provenance", "parsed")),
                via=str(item.get("via", "")),
            )
        )
    return tuple(nodes)


def parse_seed_set(text: str) -> SeedSet:
    data = load_yaml_subset(text)
    default_k = int(data.get("default_k", 5) or 5)  # type: ignore[arg-type]
    raw_pairs = data.get("pairs", []) or []
    pairs: list[Pair] = []
    for raw in raw_pairs:  # type: ignore[union-attr]
        if not isinstance(raw, Mapping):
            continue
        gt = raw.get("ground_truth") or {}
        must = _as_gt_nodes(gt.get("must_find")) if isinstance(gt, Mapping) else ()
        requires_raw = raw.get("requires") or []
        requires = tuple(str(r) for r in requires_raw) if isinstance(requires_raw, list) else ()
        fixture = raw.get("fixture")
        pairs.append(
            Pair(
                id=str(raw.get("id", "")),
                layer=str(raw.get("layer", "")),
                requires=requires,
                k=int(raw.get("k", default_k) or default_k),  # type: ignore[arg-type]
                derivation=str(raw.get("derivation", "")),
                adjudication=str(raw.get("adjudication", "")),
                must_find=must,
                fixture=fixture if isinstance(fixture, Mapping) else None,
                basis=str(raw.get("basis", "")),
            )
        )
    return SeedSet(
        repo=str(data.get("repo", "")),
        repo_commit=str(data.get("repo_commit", "")),
        default_k=default_k,
        pairs=tuple(pairs),
    )


def load_seed_set(path: str | Path) -> SeedSet:
    return parse_seed_set(Path(path).read_text(encoding="utf-8"))


def default_seed_set_path() -> Path | None:
    """Walk up from this file to find ``design/codeflair/eval/seed-set.yaml`` (a CLI
    convenience; the core harness functions take an explicit path and stay repo-agnostic)."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "design" / "codeflair" / "eval" / "seed-set.yaml"
        if candidate.is_file():
            return candidate
    return None


# --------------------------------------------------------------------------------------
# The metric
# --------------------------------------------------------------------------------------


def recall_at_k(found: Sequence[str], ground_truth: Sequence[str], k: int) -> float:
    """Fraction of the (deduplicated) ground-truth node set present in the top-``k`` of
    ``found``. ``found`` is the ranked heatmap (best first); ties already broken upstream.

    Raises on empty ground truth (recall is undefined — the caller must skip such pairs).
    """
    gt = set(ground_truth)
    if not gt:
        raise ValueError("recall_at_k requires a non-empty ground-truth set")
    if k < 0:
        raise ValueError("k must be >= 0")
    topk = set(list(found)[:k])
    return len(gt & topk) / len(gt)


# --------------------------------------------------------------------------------------
# Exercising a pair
# --------------------------------------------------------------------------------------


def build_fixture_store(fixture: Mapping[str, object]) -> Store:
    """Construct an in-memory :class:`Store` from a pair's ``fixture`` block. The graph IS
    the index: its blast radius is known by construction, so recall is exactly measurable."""
    store = Store()
    symbols = fixture.get("symbols") or {}
    if isinstance(symbols, Mapping):
        for sym, file in symbols.items():
            store.add_symbol(Symbol(symbol=str(sym), file=str(file), name=str(sym)))
    for row in fixture.get("edges") or []:  # type: ignore[union-attr]
        src, dst, rel, source, provenance = (str(x) for x in row)
        store.add_edge(Edge(src=src, dst=dst, rel=rel, source=source, provenance=provenance))
    for row in fixture.get("couplings") or []:  # type: ignore[union-attr]
        file_a, file_b, kind, weight = row
        store.add_coupling(str(file_a), str(file_b), str(kind), int(weight))
    store.commit()
    return store


@dataclass(frozen=True)
class PairResult:
    pair_id: str
    exercised: bool
    reason: str = ""  # why gated, when not exercised
    k: int = 0
    recall_overall: float | None = None
    recall_parsed: float | None = None
    recall_inferred: float | None = None
    n_gt: int = 0
    n_hit: int = 0
    found: tuple[str, ...] = ()


def _subset_recall(
    found: Sequence[str], nodes: Sequence[GroundTruthNode], provenance: str, k: int
) -> float | None:
    gt = [n.node for n in nodes if n.provenance == provenance]
    if not gt:
        return None
    return recall_at_k(found, gt, k)


def run_pair(pair: Pair) -> PairResult:
    if pair.fixture is None:
        reason = (
            "gated: requires " + ", ".join(pair.requires)
            if pair.requires
            else "gated: no fixture (needs a built repo index — SCIP/tree-sitter)"
        )
        return PairResult(pair_id=pair.id, exercised=False, reason=reason)

    fixture = pair.fixture
    store = build_fixture_store(fixture)
    seed = str(fixture.get("seed", ""))
    k = int(fixture.get("k", pair.k))  # type: ignore[arg-type]
    direction = str(fixture.get("direction", "callers"))
    max_hops = int(fixture.get("max_hops", 3))  # type: ignore[arg-type]
    result = expand(store, seed, k=k, max_hops=max_hops, direction=direction)
    found = tuple(e.symbol for e in result.heatmap)

    gt_all = [n.node for n in pair.must_find]
    overall = recall_at_k(found, gt_all, k) if gt_all else None
    n_gt = len(set(gt_all))
    n_hit = len(set(gt_all) & set(found[:k]))
    return PairResult(
        pair_id=pair.id,
        exercised=True,
        k=k,
        recall_overall=overall,
        recall_parsed=_subset_recall(found, pair.must_find, "parsed", k),
        recall_inferred=_subset_recall(found, pair.must_find, "inferred", k),
        n_gt=n_gt,
        n_hit=n_hit,
        found=found,
    )


@dataclass(frozen=True)
class EvalReport:
    n_pairs: int
    n_exercised: int
    n_gated: int
    # Micro-averaged recall@K over the EXERCISED pairs' must_find nodes (Policy-D baseline).
    baseline_overall: float | None
    baseline_parsed: float | None
    baseline_inferred: float | None
    # Provenance counts (gt nodes / hits) backing the split.
    parsed_gt: int
    parsed_hit: int
    inferred_gt: int
    inferred_hit: int
    results: tuple[PairResult, ...] = field(default_factory=tuple)


def _micro(hit: int, total: int) -> float | None:
    return (hit / total) if total else None


def evaluate(seed_set: SeedSet) -> EvalReport:
    """Run every pair; aggregate a micro-averaged Policy-D recall@K baseline over the
    exercised pairs, split parsed vs inferred. Gated pairs are reported, never scored."""
    results = tuple(run_pair(p) for p in seed_set.pairs)
    exercised = [r for r in results if r.exercised]

    parsed_gt = parsed_hit = inferred_gt = inferred_hit = 0
    overall_gt = overall_hit = 0
    by_id = {p.id: p for p in seed_set.pairs}
    for r in exercised:
        pair = by_id[r.pair_id]
        topk = set(r.found[: r.k])
        for node in pair.must_find:
            overall_gt += 1
            present = node.node in topk
            overall_hit += int(present)
            if node.provenance == "inferred":
                inferred_gt += 1
                inferred_hit += int(present)
            else:
                parsed_gt += 1
                parsed_hit += int(present)

    return EvalReport(
        n_pairs=len(seed_set.pairs),
        n_exercised=len(exercised),
        n_gated=len(results) - len(exercised),
        baseline_overall=_micro(overall_hit, overall_gt),
        baseline_parsed=_micro(parsed_hit, parsed_gt),
        baseline_inferred=_micro(inferred_hit, inferred_gt),
        parsed_gt=parsed_gt,
        parsed_hit=parsed_hit,
        inferred_gt=inferred_gt,
        inferred_hit=inferred_hit,
        results=results,
    )


def _fmt(value: float | None) -> str:
    return f"{value:.3f}" if value is not None else "n/a"


def format_report(report: EvalReport) -> str:
    lines = [
        "Codeflair eval — recall@K (Policy-D, deterministic, no LLM)",
        "=" * 62,
        f"pairs: {report.n_pairs}  exercised: {report.n_exercised}  gated: {report.n_gated}",
        "",
        "BASELINE recall@K (micro-avg over exercised must_find nodes):",
        "  ⚠ CIRCULAR — measured on BY-CONSTRUCTION fixtures (the graph IS the answer key),",
        "    so this number validates harness MECHANICS, not real-repo relevance. The",
        "    non-circular baseline awaits a built SCIP/tree-sitter index + human adjudication",
        "    (the gated pairs below); do NOT cite this as Codeflair's retrieval quality.",
        f"  overall : {_fmt(report.baseline_overall)}  "
        f"({report.parsed_hit + report.inferred_hit}/{report.parsed_gt + report.inferred_gt})",
        f"  parsed  : {_fmt(report.baseline_parsed)}  ({report.parsed_hit}/{report.parsed_gt})",
        f"  inferred: {_fmt(report.baseline_inferred)}  "
        f"({report.inferred_hit}/{report.inferred_gt})",
        "",
        "per-pair:",
    ]
    for r in report.results:
        if r.exercised:
            lines.append(
                f"  [x] {r.pair_id:<42} recall@{r.k}={_fmt(r.recall_overall)} ({r.n_hit}/{r.n_gt})"
            )
        else:
            lines.append(f"  [ ] {r.pair_id:<42} {r.reason}")
    lines.append("")
    lines.append(
        "NOTE: exercised pairs use known-by-construction fixtures grounded in real "
        "derivations.\n      Gated pairs need a built SCIP/tree-sitter index of the repo. "
        "Human inter-labeler\n      adjudication (the CF-D5 build gate) is STILL OUTSTANDING "
        "— pairs are mechanically\n      derived (adjudication: needs-human / by-construction), "
        "not human-agreed."
    )
    return "\n".join(lines)


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_seed_set_path()
    if path is None or not Path(path).is_file():
        print("seed-set.yaml not found; pass its path as the first argument", file=sys.stderr)
        return 2
    report = evaluate(load_seed_set(path))
    print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
