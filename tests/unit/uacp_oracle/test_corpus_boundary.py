"""Architectural boundary test: the Oracle owns the knowledge/lesson corpus.

This test scans the repository's Python source and enforces the data-ownership
boundary that the Oracle refactor establishes:

  1. CORPUS OWNERSHIP — Only code inside the oracle package
     (skills/uacp-core/scripts/engines/oracle/) may import the corpus
     loaders/writers from engines.domain.corpus (load_lessons_dir,
     load_knowledge_dir, persist_lesson/persist_knowledge helpers) or write to
     .uacp/lessons/ / .uacp/knowledge/.  The corpus module itself
     (engines/domain/corpus.py) is the only other allowlisted source.

  2. NO STATE IN THE ORACLE — The oracle package imports NO state/manifest
     reader: no engines.oracle.sources.runstate, no state_machine, and no
     core/state manifest-path readers (load_manifest / state/runs reads).

Scan scope: production Python under skills/ and runtime-adapters/.  Tests
(tests/) and the one-time migration script (scripts/migrate_knowledge_corpus.py)
are intentionally excluded — they are data-movement / verification surfaces, not
runtime consumers of the corpus, and are allowlisted by path with a comment.

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

# Directories scanned for boundary violations (production source only).
_SCAN_ROOTS = (
    _REPO_ROOT / "skills",
    _REPO_ROOT / "runtime-adapters",
)

# Path-based allowlist: these files MAY touch the corpus loaders/writers or
# the corpus directories without being a boundary violation.
#   - the oracle package: it OWNS the corpus.
#   - engines/domain/corpus.py: it IS the corpus module.
#   - scripts/migrate_knowledge_corpus.py: one-time data-movement migration.
# (tests/ are excluded from the scan entirely.)
_CORPUS_ALLOWLIST = (
    _ORACLE_PKG,
    _CORPUS_MODULE,
    _REPO_ROOT / "scripts" / "migrate_knowledge_corpus.py",
)

# Tokens that denote reading/writing the corpus via the domain module.
_CORPUS_LOADER_TOKENS = (
    "load_lessons_dir",
    "load_knowledge_dir",
    "persist_lesson",
    "persist_knowledge",
)

# Regexes that denote a direct write to the corpus directories.  We look for the
# governed-namespace corpus paths as string literals.
_CORPUS_PATH_PATTERNS = (
    re.compile(r"\.uacp/lessons"),
    re.compile(r"\.uacp/knowledge"),
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
