"""Architectural boundary test: the Oracle owns the knowledge/lesson corpus.

This test scans Python source under skills/, runtime-adapters/, and scripts/ and
enforces the data-ownership boundary that the Oracle refactor establishes:

  1. CORPUS OWNERSHIP — Only code inside the oracle package
     (skills/uacp-core/scripts/engines/oracle/) may touch the corpus.  This is
     enforced STRUCTURALLY (not merely grep-only) along these axes:
       (a) IMPORT-SCAN — no module outside the oracle package may import
           engines.oracle.corpus_io or engines.oracle.corpus_writer (the disk
           loaders and the governed writer now live INSIDE the oracle package, so
           any out-of-package import of them is the violation, robust against the
           loaders being callable under any local alias).
       (b) LOADER/PATH LITERAL SCAN — no out-of-package module may reference the
           loader/writer tokens (load_lessons_dir, load_knowledge_dir,
           persist_lesson, persist_knowledge) or hard-code a .uacp/lessons /
           .uacp/knowledge path literal.
       (c) PATH-INDIRECTION SCAN — no out-of-package module may build a corpus
           path indirectly via `.resolve(..., "lessons")` / `.resolve(...,
           "knowledge")` or write into `.uacp/lessons` / `.uacp/knowledge`.
       (d) PURE-ACCESSOR SCAN — no out-of-package module may call the pure corpus
           OKF accessors (`<X>.from_okf(...)` / `.to_okf()`) on the corpus types,
           nor a corpus dir-builder (`dir_for(...)` / `base_dir(...)` joined with
           a "lessons"/"knowledge" component).  These accessors live on the PURE
           corpus dataclasses, so calling them outside the oracle is a way to
           round-trip the corpus while bypassing the oracle's single-owner read
           surface (corpus_io) — this axis closes that bypass.
     The corpus dataclass module (engines/domain/corpus.py) is allowlisted (it is
     PURE now — it holds no loaders/writers — but stays on the allowlist as it is
     the canonical corpus type module that DEFINES from_okf/to_okf).

  2. NO STATE IN THE ORACLE — The oracle package imports NO state/manifest
     reader: no engines.oracle.sources.runstate, no state_machine, and no
     core/state manifest-path readers (load_manifest / state/runs reads).

Scan scope: production + maintenance Python under skills/, runtime-adapters/, and
scripts/.  Allowlisted by path (with a comment at the allowlist):
  - the oracle package and engines/domain/corpus.py (they OWN / DEFINE the corpus);
  - scripts/migrate_knowledge_corpus.py — one-time data-movement migration;
  - scripts/phase{1,2,3}_verify.py — phase verification harnesses that only
    `mkdir` a .uacp/knowledge directory as test-root scaffolding (read-only
    maintenance: they do NOT read/write corpus documents through the loaders).
The tests/ tree is NOT scanned (test scaffolding legitimately constructs corpus
paths and documents).

LIMITATION — this is a PURELY STATIC source scan.  It cannot catch dynamic
corpus access: e.g. `getattr(corpus_mod, "from_okf")`, an importlib-resolved
module, or a path assembled from runtime-computed string fragments.  A complete
guarantee would require a RUNTIME guard at the corpus read/write surface; that is
a documented follow-up, intentionally NOT built here.  This test therefore
asserts the boundary over the *statically analyzable* source, not a repo-wide
dynamic-proof ownership claim.

Failure messages name the offending file and the offending token precisely.
"""
from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ORACLE_PKG = _REPO_ROOT / "skills" / "uacp-core" / "scripts" / "engines" / "oracle"
_CORPUS_MODULE = (
    _REPO_ROOT / "skills" / "uacp-core" / "scripts" / "engines" / "domain" / "corpus.py"
)

# Directories scanned for boundary violations (production + maintenance source).
# scripts/ IS scanned (MED-2): the migration + phase-verify scripts are real
# corpus-adjacent surfaces and must obey the boundary (with explicit allowlist
# entries for the legitimate exceptions below).
_SCAN_ROOTS = (
    _REPO_ROOT / "skills",
    _REPO_ROOT / "runtime-adapters",
    _REPO_ROOT / "scripts",
)

# Path-based allowlist: these files MAY touch the corpus loaders/writers/accessors
# or the corpus directories without being a boundary violation.
#   - the oracle package: it OWNS the corpus.
#   - engines/domain/corpus.py: it IS the corpus module (it DEFINES from_okf/to_okf).
#   - scripts/migrate_knowledge_corpus.py: one-time data-movement migration.
#   - scripts/phase{1,2,3}_verify.py: phase verification harnesses that only
#     `mkdir` a .uacp/knowledge directory as test-root scaffolding — read-only
#     maintenance, NOT corpus document reads/writes through the loaders.
# (tests/ are excluded from the scan entirely.)
_CORPUS_ALLOWLIST = (
    _ORACLE_PKG,
    _CORPUS_MODULE,
    _REPO_ROOT / "scripts" / "migrate_knowledge_corpus.py",
    _REPO_ROOT / "scripts" / "phase1_verify.py",
    _REPO_ROOT / "scripts" / "phase2_verify.py",
    _REPO_ROOT / "scripts" / "phase3_verify.py",
)

# Tokens that denote reading/writing the corpus via the domain module.
_CORPUS_LOADER_TOKENS = (
    "load_lessons_dir",
    "load_knowledge_dir",
    "persist_lesson",
    "persist_knowledge",
)

# Import-scan patterns: the disk loaders + governed writer now live INSIDE the
# oracle package.  Any out-of-package module that imports either module is, by
# construction, reaching into the oracle's corpus-ownership surface — regardless
# of what local alias it binds the loaders to.  This catches import-evasion that
# the token scan alone would miss.
_CORPUS_MODULE_IMPORT_PATTERNS = (
    re.compile(r"engines\.oracle\.corpus_io"),
    re.compile(r"engines\.oracle\.corpus_writer"),
    re.compile(r"from\s+engines\.oracle\s+import\s+[^\n]*\bcorpus_io\b"),
    re.compile(r"from\s+engines\.oracle\s+import\s+[^\n]*\bcorpus_writer\b"),
)

# Regexes that denote a direct write to the corpus directories.  We look for the
# governed-namespace corpus paths as string literals.
_CORPUS_PATH_PATTERNS = (
    re.compile(r"\.uacp/lessons"),
    re.compile(r"\.uacp/knowledge"),
)

# Path-INDIRECTION patterns: a module that does not name a .uacp/lessons literal
# can still reach the corpus by resolving a path key through the config resolver
# (`get_config(root).resolve(root, "lessons")`) or by joining the governed
# namespace at runtime.  Flag any out-of-package module that resolves the
# "lessons"/"knowledge" path keys or writes a .uacp / "lessons" | "knowledge"
# path component.
_CORPUS_PATH_INDIRECTION_PATTERNS = (
    re.compile(r"""\.resolve\([^)]*["'](?:lessons|knowledge)["']"""),
    re.compile(r"""\.uacp["']?\s*[/,]\s*["'](?:lessons|knowledge)["']"""),
)

# Pure-accessor patterns (MED-2): the corpus dataclasses expose pure OKF
# (de)serializers `from_okf` / `to_okf`.  An out-of-package module can round-trip
# the corpus by calling these on a resolved corpus path, bypassing the oracle's
# single-owner read surface (corpus_io).  Flag any `.from_okf(` / `.to_okf(` call
# outside the oracle package + corpus module.  Also flag a corpus dir-builder
# (`dir_for(...)` / `base_dir(...)`) joined with a lessons/knowledge component —
# the structural form a helper would take to assemble a corpus directory.
_CORPUS_ACCESSOR_PATTERNS = (
    re.compile(r"\.from_okf\s*\("),
    re.compile(r"\.to_okf\s*\("),
    re.compile(r"""(?:dir_for|base_dir)\s*\([^)]*\)\s*/\s*["'](?:lessons|knowledge)["']"""),
    re.compile(r"""(?:dir_for|base_dir)\s*\(\s*["'](?:lessons|knowledge)["']"""),
)

# Tokens that denote a state/manifest reader the oracle must NOT import.
_STATE_READER_TOKENS = (
    "sources.runstate",
    "sources import runstate",
    "query_runstate",
    "state_machine",
    "load_manifest",
)


def _iter_python_files(root: Path):
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _is_allowlisted_for_corpus(path: Path) -> bool:
    for allowed in _CORPUS_ALLOWLIST:
        if allowed.is_dir():
            if allowed in path.parents or path == allowed:
                return True
        elif path == allowed:
            return True
    return False


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def test_corpus_loaders_only_referenced_inside_oracle_package():
    """Only the oracle package + corpus module may reference corpus loaders/writers.

    Any other production module that imports load_lessons_dir / load_knowledge_dir
    / persist_lesson / persist_knowledge, or hard-codes a .uacp/lessons /
    .uacp/knowledge path, is a data-ownership boundary violation.
    """
    violations: list[str] = []

    for scan_root in _SCAN_ROOTS:
        if not scan_root.is_dir():
            continue
        for path in _iter_python_files(scan_root):
            if _is_allowlisted_for_corpus(path):
                continue
            text = _read(path)
            # (a) import-scan: importing the oracle's corpus_io / corpus_writer
            # modules from outside the package is a violation no matter what
            # alias the loaders are bound to.
            for pattern in _CORPUS_MODULE_IMPORT_PATTERNS:
                if pattern.search(text):
                    violations.append(
                        f"{path} imports the oracle corpus module "
                        f"'{pattern.pattern}' but is outside the oracle package "
                        f"(corpus access must go through engines.oracle, "
                        f"not by importing its private loader/writer modules)"
                    )
            # (b) loader/writer token + path-literal scan.
            for token in _CORPUS_LOADER_TOKENS:
                if token in text:
                    violations.append(
                        f"{path} references corpus loader/writer "
                        f"'{token}' but is outside the oracle package "
                        f"(corpus access must go through engines.oracle)"
                    )
            for pattern in _CORPUS_PATH_PATTERNS:
                if pattern.search(text):
                    violations.append(
                        f"{path} hard-codes corpus path "
                        f"'{pattern.pattern}' but is outside the oracle package "
                        f"(corpus writes must go through engines.oracle)"
                    )
            # (c) path-indirection scan: resolving the lessons/knowledge path
            # keys or joining the governed namespace at runtime.
            for pattern in _CORPUS_PATH_INDIRECTION_PATTERNS:
                if pattern.search(text):
                    violations.append(
                        f"{path} resolves a corpus path indirectly "
                        f"(matched '{pattern.pattern}') but is outside the oracle "
                        f"package (corpus path resolution must go through "
                        f"engines.oracle)"
                    )
            # (d) pure-accessor scan: calling the corpus OKF (de)serializers
            # from_okf/to_okf, or a corpus dir-builder, outside the oracle package
            # is a bypass of the oracle's single-owner corpus read/write surface.
            for pattern in _CORPUS_ACCESSOR_PATTERNS:
                if pattern.search(text):
                    violations.append(
                        f"{path} calls a pure corpus accessor / dir-builder "
                        f"(matched '{pattern.pattern}') but is outside the oracle "
                        f"package (corpus (de)serialization must go through "
                        f"engines.oracle, not direct from_okf/to_okf on the "
                        f"corpus types)"
                    )

    assert not violations, "Corpus-ownership boundary violations:\n" + "\n".join(
        violations
    )


def test_oracle_package_imports_no_state_or_manifest_reader():
    """The oracle package must not read state/manifest — that belongs to the state engine.

    No file under engines/oracle/ may import the run-state source, the state
    machine, or the manifest loader.  The oracle's sources are knowledge/lesson
    (via the corpus) and honcho only.
    """
    violations: list[str] = []

    for path in _iter_python_files(_ORACLE_PKG):
        text = _read(path)
        for token in _STATE_READER_TOKENS:
            if token in text:
                violations.append(
                    f"{path} references state/manifest reader '{token}' — "
                    f"the oracle must not read state/manifest "
                    f"(that boundary belongs to the state engine)"
                )

    assert not violations, "Oracle-touches-state boundary violations:\n" + "\n".join(
        violations
    )
