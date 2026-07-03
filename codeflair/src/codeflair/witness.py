"""Codeflair witness — the scope-conformance FACTS face (UACP issue #85).

``codeflair witness --repo <root> [--code-ref file:name ...]`` (re)indexes the run's
CURRENT working tree, then reports **facts** about the change for a scope gate to grade.
It computes **no verdicts** — no coverage / undeclared / over-declared sets. That is the
kernel gate's job (design/conformance-witnesses/02-scope-witness-seam.md: "the witness
*derives*, the code *compares*"). A CLI that returned verdicts would move the comparison
into the witness, making a codeflair coverage bug invisible and unrecomputable kernel-side.

The emitted document (compact JSON, ``sort_keys``, deterministic — no wall-clock reads):

- ``graph_stamp`` — ``{commit, tree_token}``. ``commit`` is the repo HEAD; ``tree_token``
  is a content token of the CURRENT working tree (see :func:`tree_token`).
- ``ingestion`` — the honest provenance floor derived from the store (``scip`` when SCIP
  edges are present, else ``treesitter``), never hardcoded.
- ``symbols_touched`` — ``[{file, name}]``. v1 is FILE-LEVEL: every symbol the store
  records in each changed file (deliberately coarse; hunk-level is a pre-promotion item).
- ``inbound_counts`` — ``{"<file>:<name>": int}``. For EVERY symbol in ``symbols_touched``
  (key = its ``file`` and canonical derived ``name`` joined by a single colon), the count of
  DISTINCT inbound reference/call edges (``rel`` in ``calls``/``references``, ``dst`` = the
  touched symbol) in the store. Counted straight off the ``edges`` table — the class witness
  (issue #87) needs exact fan-in because the hop-1 ``neighborhood`` may be capped. Zero is a
  meaningful value (no inbound refs) and is always present, never omitted.
- ``neighborhood`` — ``[{src, dst, reason}]``. The hop-1 edges (both directions) touching
  any touched symbol; ``reason`` mapped onto ``{calls, references, defines}``.
- ``declared`` — ``[{file, name, resolved}]``. Each ``--code-ref`` echoed with a resolution
  fact: ``resolved`` iff the store has a symbol in that file whose derived human name
  matches ``name`` (class-qualified). Never bare-substring matching across the whole store.
- ``unresolved_touched`` — ``[{file, name}]``. Changed indexed-language files the ingester
  produced no symbols for (empty, unparseable, or skipped). ``name`` is NULLABLE (``null``):
  the file is known from the diff, the symbol is not — serialized file-level, never dropped
  (best-effort; empty list when none detected).

On failure (not a git repo, index produced nothing) it returns ``{"error": ...}`` and the
CLI exits nonzero.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from collections.abc import Callable, Iterable, Sequence

from codeflair.freshness import content_hash
from codeflair.store import Store, Symbol, default_store_path

# The edge relations the witness reports. The store's SCIP/tree-sitter edges carry exactly
# these ``rel`` values for real code edges; coupling kinds (co_change / shared_string) live
# in a separate table and are NOT edges, so they never appear in ``neighborhood``.
_REASONS = frozenset({"calls", "references", "defines"})

# Per-language file suffixes considered "indexed-language" for touched-symbol derivation.
# These MIRROR cli._SUFFIX exactly (kept local to avoid a cli<->witness import cycle). NOTE
# (C6): the tree-sitter breadth floor only ingests cli._TS_EXT per language (typescript ->
# .ts), so a changed .tsx resolves symbols only via SCIP. A changed file OUTSIDE these
# suffixes is NOT silently dropped — it surfaces file-level in unresolved_touched (C4):
# "changed code the witness cannot reason about" must stay visible to the gate.
_SUFFIX: dict[str, tuple[str, ...]] = {
    "go": (".go",),
    "python": (".py",),
    "typescript": (".ts", ".tsx"),
}

# Store edge/ownership source -> reported ingestion floor. The store tags tree-sitter rows
# ``tree_sitter``; the witness reports the design's floor spelling ``treesitter``.
_INGESTION_NAME = {"scip": "scip", "tree_sitter": "treesitter"}


# -- git observation (read-only; never raises to the caller) ------------------------------


def _run_git(repo: str, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Run ``git -C <repo> <args>`` capturing text output. Never checks — the caller decides
    what a non-zero return means (git parity: absence/failure is data, not a crash)."""
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, check=False
    )


def is_git_repo(repo: str) -> bool:
    """True iff ``repo`` is inside a git work tree."""
    try:
        out = _run_git(repo, ["rev-parse", "--is-inside-work-tree"])
    except OSError:
        return False
    return out.returncode == 0 and out.stdout.strip() == "true"


def head_commit(repo: str) -> str:
    """The repo's ``HEAD`` commit sha, or ``""`` if unresolvable (empty repo / no commits)."""
    out = _run_git(repo, ["rev-parse", "HEAD"])
    return out.stdout.strip() if out.returncode == 0 else ""


def porcelain_lines(repo: str) -> list[str]:
    """The raw ``git status --porcelain -uall`` lines (untracked included, ignored excluded
    — the default). ``-uall`` is load-bearing: without it an entirely-new directory collapses
    to a single ``?? dir/`` entry and every file inside it becomes invisible to the witness
    (found by the #85 end-to-end proof). Order-unstable across git versions, so callers SORT
    before hashing."""
    out = _run_git(repo, ["status", "--porcelain", "-uall"])
    if out.returncode != 0:
        return []
    # The witness's own index cache is never an observation: on a repo that does
    # not gitignore .codeflair/, the reindex would otherwise pollute the porcelain
    # view (changed-set AND tree_token) with gate-owned state (post-merge P2).
    return [
        ln
        for ln in out.stdout.splitlines()
        if ln and not _porcelain_path(ln).startswith(".codeflair/")
    ]


def _porcelain_path(line: str) -> str:
    """The path out of a porcelain v1 line (columns 0-1 status, path from column 3). For a
    rename (``R  old -> new``) the NEW path is taken. Best-effort: git-quoted exotic paths
    (core.quotepath) are left verbatim."""
    path = line[3:] if len(line) > 3 else line
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return path


def uncommitted_paths(repo: str) -> set[str]:
    """Repo-root-relative paths with uncommitted changes (modified, added, deleted, renamed,
    untracked). Ignored files are excluded by ``git status --porcelain``'s default."""
    return {_porcelain_path(ln) for ln in porcelain_lines(repo)}


def default_branch(repo: str) -> str | None:
    """The committed-diff baseline ref, or ``None`` (that half then skips gracefully).

    Candidate order mirrors the kernel git half (gitio K4): ``origin/HEAD`` (resolves to
    its symbolic target), ``origin/main``, ``origin/master``, then local ``main``/``master``
    — a linked worktree cut from a remote may carry only ``origin/*`` refs, and probing
    local heads alone would silently drop the committed half of the changed-set."""
    for name in ("origin/HEAD", "origin/main", "origin/master", "main", "master"):
        out = _run_git(repo, ["rev-parse", "--verify", "--quiet", name])
        if out.returncode == 0 and out.stdout.strip():
            return name
    return None


def committed_paths(repo: str) -> set[str]:
    """Repo-root-relative paths changed on this branch since it forked from the default
    branch: ``git diff --name-only $(git merge-base <default> HEAD) HEAD``. Empty (skipped
    gracefully) when no default branch resolves or the merge-base cannot be computed."""
    default = default_branch(repo)
    if default is None:
        return set()
    mb = _run_git(repo, ["merge-base", default, "HEAD"])
    if mb.returncode != 0 or not mb.stdout.strip():
        return set()
    base = mb.stdout.strip()
    diff = _run_git(repo, ["diff", "--name-only", base, "HEAD"])
    if diff.returncode != 0:
        return set()
    return {ln for ln in diff.stdout.splitlines() if ln}


def changed_files(repo: str) -> set[str]:
    """The full changed-set: uncommitted ∪ committed-on-branch (same baseline as the git
    half of the scope gate). A run that commits during EXECUTE is still fully observed."""
    return uncommitted_paths(repo) | committed_paths(repo)


def tree_token(repo: str, changed: Iterable[str]) -> str:
    """A deterministic content token of the CURRENT working tree.

    Construction: ``sha256`` over, in order,

      1. the HEAD sha,
      2. the SORTED ``git status --porcelain`` lines (status + path of every dirty/untracked
         non-ignored entry), and
      3. for each changed file that exists on disk, ``"<path>:<sha256(content)>"`` in sorted
         path order.

    The porcelain lines make the token change on any add/delete/rename/untrack; the per-file
    content hashes make it change on any *content* edit that keeps a file's status the same
    (an untracked file re-saved, a tracked file re-edited). A deleted / unreadable file is
    skipped in step 3 — its disappearance is already recorded in the porcelain line, so the
    token still moves. Stable whenever every tracked/untracked non-ignored byte is unchanged;
    no wall-clock or ordering nondeterminism enters."""
    h = hashlib.sha256()
    h.update(head_commit(repo).encode("utf-8"))
    h.update(b"\n")
    for line in sorted(porcelain_lines(repo)):
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    for rel in sorted(changed):
        abspath = os.path.join(repo, rel)
        try:
            with open(abspath, "rb") as fh:
                data = fh.read()
        except OSError:
            continue  # deleted/unreadable — the porcelain line already moved the token
        h.update(f"{rel}:{content_hash(data)}\n".encode())
    return h.hexdigest()


# -- symbol identity (deriving a human name from a stored symbol) --------------------------

# SCIP method disambiguator parens: ``method(+1).`` / ``method().`` -> drop the ``(...)``.
_PARENS_RE = re.compile(r"\([^)]*\)")


def _descriptor_section(scip_id: str) -> str:
    """The descriptor section of a SCIP symbol id — everything after the 4th space (scheme,
    manager, package-name, version, then descriptors). Names containing spaces are backtick-
    escaped inside this section, so a naive ``split(" ")[-1]`` can truncate them; capping the
    split at 4 keeps the whole descriptor chain."""
    return scip_id.split(" ", 4)[-1]


def _tokenize_descriptors(desc: str) -> list[tuple[str, str]]:
    """Split a SCIP descriptor chain into ``(name, kind)`` components, honoring backtick
    escapes. Terminators: ``/`` namespace, ``#`` type, ``.`` term. A trailing name with no
    terminator is treated as a term."""
    tokens: list[tuple[str, str]] = []
    buf: list[str] = []
    i, n = 0, len(desc)
    kinds = {"/": "namespace", "#": "type", ".": "term"}
    while i < n:
        c = desc[i]
        if c == "`":  # backtick-escaped name: copy verbatim until the closing backtick
            j = desc.find("`", i + 1)
            if j == -1:
                buf.append(desc[i + 1 :])
                break
            buf.append(desc[i + 1 : j])
            i = j + 1
            continue
        if c in kinds:
            name = "".join(buf)
            buf = []
            if name:
                tokens.append((name, kinds[c]))
            i += 1
            continue
        buf.append(c)
        i += 1
    if buf:
        name = "".join(buf)
        if name:
            tokens.append((name, "term"))
    return tokens


def _scip_human_name(scip_id: str) -> str:
    """A deterministic, class-qualified human name from a SCIP symbol id.

    Drops the descriptor suffixes (``#`` type, ``().`` method, ``.`` term) and the
    namespace/package components (``/``), then joins the remaining identifiers with ``.``:

      - ``…/Violation#``                      -> ``Violation``
      - ``…/Heartgate#validate_closure().``   -> ``Heartgate.validate_closure``
      - ``… `pkg`/CancelOrder#``              -> ``CancelOrder``

    Consecutive duplicate components collapse, taming the spike's doubled module-const
    descriptors (``X.X.`` -> ``X``). Never a bare substring of the raw id."""
    desc = _PARENS_RE.sub("", _descriptor_section(scip_id))
    parts = [name for name, kind in _tokenize_descriptors(desc) if kind != "namespace"]
    collapsed: list[str] = []
    for p in parts:
        if not collapsed or collapsed[-1] != p:
            collapsed.append(p)
    return ".".join(collapsed) or desc


def human_name(sym: Symbol) -> str:
    """The human name of a stored symbol. For a SCIP-descriptor id the name is normalized off
    the id (:func:`_scip_human_name`); for a tree-sitter synthesized id (``tree-sitter <lang>
    <path>:<name>#<line>``, the syntactic floor) the store's ``name`` column already holds the
    bare identifier (no descriptor decoration, no container qualification available), so it is
    used directly."""
    if sym.symbol.startswith("tree-sitter "):
        return sym.name or sym.symbol
    return _scip_human_name(sym.symbol)


def _names_match(derived: str, declared: str) -> bool:
    """Match a declared ``--code-ref`` name against a symbol's derived human name. Exact match
    always; additionally an UNQUALIFIED declared name (no ``.``) matches the last component of
    a class-qualified derived name (``validate_closure`` matches ``Heartgate.validate_closure``).
    A qualified declared name must match in full. Never a bare substring."""
    if derived == declared:
        return True
    if "." not in declared and "." in derived:
        return derived.rsplit(".", 1)[-1] == declared
    return False


# -- fact derivation over an open store ---------------------------------------------------


def ingestion_floor(store: Store) -> str:
    """The honest provenance floor, derived from the store — ``scip`` if any SCIP edges (or
    SCIP-owned symbols) exist, else ``treesitter`` if the tree-sitter floor produced anything,
    else ``none``. Never hardcoded: it reflects what the reindex actually managed to build."""
    edge_sources = {
        r[0] for r in store.con.execute("SELECT DISTINCT source FROM edges").fetchall()
    }
    for src in ("scip", "tree_sitter"):
        if src in edge_sources:
            return _INGESTION_NAME[src]
    own_sources = {
        r[0] for r in store.con.execute("SELECT DISTINCT source FROM symbol_source").fetchall()
    }
    for src in ("scip", "tree_sitter"):
        if src in own_sources:
            return _INGESTION_NAME[src]
    return "none"


def touched_ingestion_floor(store: Store, touched_ids: set[str]) -> str:
    """The provenance floor of the TOUCHED symbols specifically (design node 02 / C5).

    The WEAKEST source owning any touched symbol wins: any ``tree_sitter`` -> ``treesitter``;
    all ``scip`` -> ``scip``. A store-GLOBAL floor is a laundering vector — SCIP edges
    ELSEWHERE in the store would launder a tree-sitter-derived touched symbol past the gate's
    ``scip`` requirement (scip on this change != scip elsewhere). With NO touched symbol owned
    by any source (e.g. couplings-only, or no symbols at all) fall back to the store-wide
    floor as before."""
    owners: set[str] = set()
    for sid in touched_ids:
        owners |= store.symbol_owners(sid)
    if "tree_sitter" in owners:
        return _INGESTION_NAME["tree_sitter"]
    if "scip" in owners:
        return _INGESTION_NAME["scip"]
    return ingestion_floor(store)


def _node(store: Store, symbol_id: str) -> dict[str, str]:
    """Resolve a symbol id to a ``{file, name}`` neighborhood/touched node."""
    sym = store.symbol(symbol_id)
    if sym is None:
        return {"file": "", "name": symbol_id}
    return {"file": sym.file, "name": human_name(sym)}


def _neighborhood(store: Store, touched_ids: set[str]) -> list[dict[str, object]]:
    """Hop-1 edges (both directions) touching any id in ``touched_ids``, each as
    ``{src, dst, reason}`` with ``reason`` restricted to ``{calls, references, defines}``."""
    if not touched_ids:
        return []
    ids = list(touched_ids)
    ph = ",".join("?" * len(ids))
    rows = store.con.execute(
        f"SELECT src, dst, rel FROM edges WHERE src IN ({ph}) OR dst IN ({ph})",
        ids + ids,
    ).fetchall()
    seen: set[tuple[str, str, str, str, str]] = set()
    out: list[dict[str, object]] = []
    for src, dst, rel in rows:
        if rel not in _REASONS:
            continue
        sn, dn = _node(store, src), _node(store, dst)
        key = (sn["file"], sn["name"], dn["file"], dn["name"], rel)
        if key in seen:
            continue
        seen.add(key)
        out.append({"src": sn, "dst": dn, "reason": rel})
    out.sort(
        key=lambda e: (
            e["src"]["file"],
            e["src"]["name"],
            e["dst"]["file"],
            e["dst"]["name"],
            e["reason"],
        )
    )
    return out


# Inbound edge relations that count as a symbol being REFERENCED/CALLED (wired-in). The
# structural ``defines`` edge (container -> member) is deliberately EXCLUDED: it is present
# for every contained member and would trivially mark every method "wired-in", defeating the
# no-inbound-references distinction the class witness derives from these counts.
_INBOUND_REASONS = ("calls", "references")


def _inbound_count(store: Store, symbol_ids: set[str]) -> int:
    """The number of DISTINCT inbound reference/call edges whose ``dst`` is any id in
    ``symbol_ids`` (the ids a touched ``{file, name}`` symbol collapses to). Counted straight
    off the ``edges`` table — never the hop-1 ``neighborhood`` list, which may be capped —
    so the fan-in is exact. Distinctness collapses the store's source axis (the same
    ``src -> dst`` edge reported by both scip and tree_sitter is one edge): a ``(src, dst, rel)``
    tuple counted once. Deterministic (a set cardinality, no ordering)."""
    ph = ",".join("?" * len(_INBOUND_REASONS))
    distinct: set[tuple[str, str, str]] = set()
    for sid in symbol_ids:
        for src, rel in store.con.execute(
            f"SELECT DISTINCT src, rel FROM edges WHERE dst=? AND rel IN ({ph})",
            (sid, *_INBOUND_REASONS),
        ).fetchall():
            distinct.add((src, sid, rel))
    return len(distinct)


def _symbol_facts(
    store: Store, changed: set[str], code_refs: Sequence[tuple[str, str]], lang: str
) -> tuple[dict[str, object], set[str]]:
    """The store-derived facts (everything but ``graph_stamp`` / ``ingestion``): file-level
    ``symbols_touched``, hop-1 ``neighborhood``, ``declared`` resolution, ``unresolved_touched``.
    Returns ``(facts, touched_ids)`` — the touched symbol ids drive the touched-scoped
    ingestion floor (C5). Pure over an open store + a precomputed changed-set (so it is
    unit-testable with a seeded store, no git, no reindex)."""
    suffixes = _SUFFIX.get(lang, ())
    lang_files = sorted(f for f in changed if suffixes and f.endswith(suffixes))
    # C4: changed files OUTSIDE the indexed language (e.g. a .rs when lang=python) are not
    # dropped — they surface file-level in unresolved_touched with a NULL name.
    other_files = sorted(f for f in changed if not (suffixes and f.endswith(suffixes)))

    touched: set[tuple[str, str]] = set()
    touched_ids: set[str] = set()
    # (file, human_name) -> the store symbol ids that collapse to it. A touched symbol may map
    # to >1 id (two ids in a file sharing a derived name); inbound counts sum over the group.
    touched_ids_by_key: dict[tuple[str, str], set[str]] = {}
    unresolved: list[dict[str, object]] = []
    for f in lang_files:
        ids = store.symbols_in_file(f)
        if not ids:
            # A changed indexed-language file the ingester produced no symbols for (an empty,
            # unparseable, or ingester-skipped file). It is KNOWN from the diff but yielded no
            # symbol, so it is serialized file-level with a NULLABLE name (never dropped —
            # silent fail-open is forbidden; the gate must see it).
            unresolved.append({"file": f, "name": None})
            continue
        for sid in ids:
            sym = store.symbol(sid)
            if sym is None:
                continue
            key = (f, human_name(sym))
            touched.add(key)
            touched_ids.add(sid)
            touched_ids_by_key.setdefault(key, set()).add(sid)
    for f in other_files:
        # Non-indexed-language changed file: visible file-level, name null (C4).
        unresolved.append({"file": f, "name": None})

    symbols_touched = [{"file": f, "name": n} for f, n in sorted(touched)]

    # Per-symbol inbound fan-in for EVERY touched symbol, keyed exactly as symbols_touched
    # serializes it: "<file>:<name>" (the canonical derived human name). Zero is meaningful
    # (no inbound refs) and always present — never omitted (issue #87 class witness).
    inbound_counts = {
        f"{f}:{n}": _inbound_count(store, touched_ids_by_key[(f, n)])
        for f, n in sorted(touched)
    }

    declared: list[dict[str, object]] = []
    for file, name in code_refs:
        # Match the authored name against each symbol's CANONICAL human name; collect the
        # DISTINCT canonical names that match. Exactly one match -> echo THAT canonical name
        # (C1: coverage compares canonical-to-canonical kernel-side, so an unqualified authored
        # name must be echoed back class-qualified, e.g. "validate" -> "Heartgate.validate").
        # More than one distinct match = AMBIGUOUS (C2: bare "foo" matching both A.foo and
        # B.foo) -> resolved:false, because an arbitrary pick would count a claim the author
        # never disambiguated as coverage. Zero matches -> resolved:false. Either non-single
        # case echoes the AUTHORED name (never dropped) so the gate surfaces the exact claim.
        matches: set[str] = set()
        for sid in store.symbols_in_file(file):
            sym = store.symbol(sid)
            if sym is not None and _names_match(human_name(sym), name):
                matches.add(human_name(sym))
        if len(matches) == 1:
            declared.append({"file": file, "name": next(iter(matches)), "resolved": True})
        else:
            declared.append({"file": file, "name": name, "resolved": False})
    declared.sort(key=lambda d: (d["file"], d["name"]))

    facts = {
        "symbols_touched": symbols_touched,
        "inbound_counts": inbound_counts,
        "neighborhood": _neighborhood(store, touched_ids),
        "declared": declared,
        "unresolved_touched": sorted(unresolved, key=lambda d: d["file"]),
    }
    return facts, touched_ids


# -- orchestration ------------------------------------------------------------------------

# The reindex dependency: ``build_index(repo, *, lang=...) -> summary`` (injected so the fact
# derivation is testable against a controlled index; the CLI passes cli.build_index).
Reindex = Callable[..., dict[str, object]]


def build_witness(
    repo: str,
    reindex: Reindex,
    *,
    code_refs: Sequence[tuple[str, str]] = (),
    lang: str = "python",
) -> dict[str, object]:
    """Reindex the current working tree, then derive the witness facts. Returns the facts
    document, or ``{"error": ...}`` on failure (not a git repo, or the reindex produced no
    index content). The run is against the DIRTY tree as it exists on disk — that is the
    point: freshness is by construction (the newly-indexed tree), not by stamp comparison.

    C3: the witness derives from a FRESH store — the existing ``.codeflair/index.db`` is
    DELETED before reindex. The ingest ladder APPENDS rows without clearing a prior build, so
    a reused store retains deleted symbols/edges and can manufacture false hop-1 coverage
    (cross-provider council finding). Witness path only; best-effort (a first run has none)."""
    if not is_git_repo(repo):
        return {"error": "not a git repository", "repo": repo}

    # Delete-and-rebuild: never derive from an incrementally-reused store (C3).
    store_path = default_store_path(repo)
    try:
        if os.path.exists(store_path):
            os.remove(store_path)
    except OSError:
        pass  # best-effort; a fresh reindex overwrites in place if the unlink races

    # Observe the change set BEFORE reindexing (post-merge P2): the reindex itself
    # creates .codeflair/index.db, and on a repo that does not gitignore .codeflair/
    # a post-reindex observation would fold the witness's OWN cache into the facts
    # and the tree_token. The cache dir is also filtered defensively for the case
    # where it pre-exists as dirty state — the gate-owned cache is never a fact.
    changed = {f for f in changed_files(repo) if not f.startswith(".codeflair/")}

    summary = reindex(repo, lang=lang)
    if not summary.get("indexed"):
        return {"error": "index produced nothing", "repo": repo}
    with Store(default_store_path(repo), read_only=True) as store:
        facts, touched_ids = _symbol_facts(store, changed, code_refs, lang)
        ingestion = touched_ingestion_floor(store, touched_ids)

    return {
        "graph_stamp": {"commit": head_commit(repo), "tree_token": tree_token(repo, changed)},
        "ingestion": ingestion,
        **facts,
    }


def parse_code_ref(ref: str) -> tuple[str, str]:
    """Parse a ``--code-ref`` argument into ``(file, name)``, splitting on the FIRST colon only
    (``name`` may contain dots: ``skills/x.py:Heartgate.validate_closure``). A ref with no colon
    yields ``(ref, "")`` — echoed in ``declared`` as unresolved, never silently dropped."""
    file, _, name = ref.partition(":")
    return file, name
