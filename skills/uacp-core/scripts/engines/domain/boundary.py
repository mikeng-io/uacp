"""Glob-aware workspace file boundary — the ONE predicate shared by both sides of
the scope-conformance file check (design node 04: one boundary, both sides).

The diff-containment OUTCOME side (``_check_diff_containment``) and the
cascade-forecast PREDICTION side (``validate_cascade_forecast``) must decide
"is this file outside the declared boundary?" with byte-identical semantics — a
forecast graded against a differently-computed offender set would measure noise.
So the predicate lives HERE, once, and both callers import it.

Semantics (as landed in the #85 diff-containment build):

* a declared ``write_path`` CONTAINING a glob is matched with ``fnmatch`` against
  the workspace-relative path (``docs/*.md`` constrains the suffix; the old
  static-prefix shortcut silently allowed ``docs/rogue.py``);
* a glob-free ``write_path`` allows its whole subtree (directory-prefix
  containment on resolved, workspace-relative paths);
* the ENTIRE governed namespace (``.uacp/``) is in-boundary (governed-writer
  territory, watched by Guardian + the artifact-containment check);
* the gate-owned witness index cache (``.codeflair/``) is exempt;
* a path that does not resolve INSIDE the workspace (a symlink pointing out) is
  an ESCAPE — out of boundary, never silently skipped.

PURE domain layer: no filesystem writes; the only disk touch is ``Path.resolve``
(same as the code it was extracted from). Never raises.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from config import base_dir


def is_contained(child: Path, parent: Path) -> bool:
    """True iff ``child`` is ``parent`` itself or lives under it. Path-prefix
    containment on already-resolved, workspace-relative paths."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_under_root(root: Path, rel: str) -> Path | None:
    """Resolve a WORKSPACE-relative path defensively; None if it escapes the
    workspace or is unresolvable. Never raises. (Counterpart of the io layer's
    ``resolve_in_workspace``, which roots at ``base_dir`` — the governed
    namespace — and is therefore wrong for git-reported workspace paths.)"""
    try:
        resolved = (root / rel).resolve()
        resolved.relative_to(root)
        return resolved
    except Exception:
        return None


class FileBoundary:
    """The declared write-path boundary, precompiled for repeated membership tests.

    Built once per ``(root, write_paths)``; ``is_out_of_boundary`` / ``offenders``
    then classify workspace-relative (git-reported style) file paths. The
    classification is intentionally identical for the diff-containment outcome and
    the cascade-forecast prediction — that shared predicate is the whole point.
    """

    def __init__(self, root: Path, write_paths: list[str]) -> None:
        self.root = Path(str(root)).resolve()
        allowed_roots: list[Path] = []
        glob_paths: list[str] = []
        for wp in write_paths:
            if "*" in wp:
                glob_paths.append(wp)
                continue
            resolved = resolve_under_root(self.root, wp or ".")
            if resolved is not None:
                allowed_roots.append(resolved)
        try:
            allowed_roots.append(base_dir(self.root).resolve())
        except Exception:
            pass  # no governed namespace resolvable — write_paths remain the boundary
        self.allowed_roots = allowed_roots
        self.glob_paths = glob_paths

    def is_out_of_boundary(self, rel: str) -> bool:
        """True iff the workspace-relative path ``rel`` falls outside every declared
        write_path AND outside the governed namespace (and is not the gate's own
        ``.codeflair/`` cache). An unresolvable/escaping path is out-of-boundary."""
        if rel.startswith(".codeflair/"):
            return False
        apath = resolve_under_root(self.root, rel)
        if apath is None:
            return True  # escape (e.g. a symlink pointing out) — never a silent skip
        if any(is_contained(apath, base) for base in self.allowed_roots):
            return False
        rel_norm = apath.relative_to(self.root).as_posix()
        if any(fnmatch.fnmatch(rel_norm, g) for g in self.glob_paths):
            return False
        return True

    def offenders(self, rels: list[str]) -> list[str]:
        """The subset of ``rels`` (in input order) that fall outside the boundary."""
        return [rel for rel in rels if self.is_out_of_boundary(rel)]
