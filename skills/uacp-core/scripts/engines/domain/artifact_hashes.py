"""Bounded per-run artifact hash index — the detection watermark (Phase B / D24).

A SHA-256 content hash per governed artifact, stored as an overwrite-in-place JSON
map under the guarded ``.uacp/state/hashes/`` namespace. The map is keyed by
artifact path (one entry per artifact, latest hash), so the file size is bounded by
artifact COUNT, not write count — it cannot grow without bound. Git carries the
change history, so no in-file append log is needed.

Trust model: the index lives under ``state/`` (the ``state.uacp`` Guardian category),
so an agent cannot rewrite it out-of-band; the only way an entry changes is through
the governed writer. Detection then compares an artifact's *current* content hash to
its recorded hash — divergence means a tamper that did not go through the writer.

SHA-256 (not MD5): the threat model is a deliberately adversarial producer, so the
hash must resist crafted collisions. Pure-leaf: stdlib only, no kernel imports.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def content_hash(content: str) -> str:
    """SHA-256 hex digest of an artifact's serialized content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _base_dir(workspace: str | Path) -> Path:
    p = Path(str(workspace))
    return p if p.name == ".uacp" else p / ".uacp"


def hash_index_path(workspace: str | Path, run_id: str) -> Path:
    return _base_dir(workspace) / "state" / "hashes" / f"{run_id}.json"


def load_hash_index(workspace: str | Path, run_id: str) -> dict:
    """Load the run's {artifact_rel_path: sha256} map (or {} if absent/unreadable)."""
    try:
        data = json.loads(hash_index_path(workspace, run_id).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, ValueError, OSError):
        return {}


def record_hash(workspace: str | Path, run_id: str, rel: str, content: str) -> None:
    """Record (overwrite-in-place) the SHA-256 of ``content`` for artifact ``rel``."""
    index = load_hash_index(workspace, run_id)
    index[str(rel)] = content_hash(content)
    path = hash_index_path(workspace, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
