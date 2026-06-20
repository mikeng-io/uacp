"""Artifact-integrity engine (codes ``AI_``) — the detection watermark at the gate.

Verifies that every artifact UACP recorded a hash for still has that exact content:
loads the per-run hash index (``.uacp/state/hashes/{run_id}.json``, written by the
governed writer) and compares each recorded SHA-256 to the artifact's current
content. A mismatch is an out-of-band tamper — a write that bypassed the governed
writer (e.g. an unmapped foreign edit tool the prevention block didn't catch) — and
blocks. This is the runtime-agnostic backstop of the hybrid trust model (D24/D25):
it doesn't matter HOW the file changed, only that it diverged from what we wrote.

Honest scope:

* Only RECORDED artifacts are verified. An artifact with no watermark has no
  baseline, so it is skipped (not trusted, not flagged) — which makes this engine a
  no-op on runs that never used the governed writer. Closing the "net-new file with
  no record" gap requires the governed writer to be the universal write path (the
  later entity-writer increment), at which point closure can require a record for
  every mapped artifact.
* The index lives under ``state/`` (guarded), so it is itself tamper-resistant.

Architecture: read-only; never raises (every failure is a Violation). Registered in
``ENGINES`` so it runs at closure via ``run_all_engines``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from engines.base import ENGINES, Violation
from engines.domain.artifact_hashes import content_hash, load_hash_index


# Governed artifact roots (mirror core._UACP_ARTIFACT_ROOTS + governed_handlers
# allowed_roots). A manifest-registered path under one of these is uacp_artifact_write's
# responsibility, so in the governed regime it MUST carry a watermark.
_GOVERNED_ARTIFACT_ROOTS = frozenset({
    "plans", "proposals", "executions", "verification",
    "resolutions", "knowledge", "lessons", "brainstorm",
})


def _v(code: str, message: str, **detail: Any) -> Violation:
    return Violation(code=code, severity="block", message=message, detail=detail)


def _base_dir(workspace: str | Path) -> Path:
    p = Path(str(workspace))
    return p if p.name == ".uacp" else p / ".uacp"


def _registered_artifact_rels(workspace: str | Path, run_id: str) -> list[str]:
    """Manifest-registered artifact rels that fall under a governed root."""
    try:
        from engines.io import load_manifest

        loaded = load_manifest(Path(str(workspace)).resolve(), run_id)
        if loaded.error is not None or loaded.value is None:
            return []
        artifacts = loaded.value.raw.get("artifacts")
        if not isinstance(artifacts, dict):
            return []
        return [rel for rel in artifacts.values()
                if isinstance(rel, str) and rel.split("/", 1)[0] in _GOVERNED_ARTIFACT_ROOTS]
    except Exception:
        return []


def validate_artifact_integrity(workspace: str | Path, run_id: str) -> list[Violation]:
    """Verify recorded artifacts against their watermark. Empty == intact. Never raises."""
    if not run_id or not isinstance(run_id, str):
        return []
    try:
        base = _base_dir(workspace)
        index = load_hash_index(workspace, run_id)
    except Exception:
        return []

    out: list[Violation] = []
    for rel, recorded in index.items():
        if not isinstance(rel, str) or not isinstance(recorded, str):
            continue
        path = base / rel
        try:
            if not path.is_file():
                out.append(_v("AI_MISSING",
                              f"recorded artifact '{rel}' is missing (its watermark "
                              f"has no backing file)", artifact=rel))
                continue
            current = content_hash(path.read_text(encoding="utf-8"))
        except Exception as exc:
            out.append(_v("AI_UNREADABLE",
                          f"recorded artifact '{rel}' could not be read for verification: "
                          f"{type(exc).__name__}", artifact=rel))
            continue
        if current != recorded:
            out.append(_v("AI_TAMPERED",
                          f"artifact '{rel}' content hash {current[:12]}… does not match the "
                          f"recorded {recorded[:12]}… — out-of-band write that bypassed the "
                          f"governed writer", artifact=rel, current=current, recorded=recorded))

    # #4 (require-record): once the run has ANY watermark it is in the governed-writer
    # regime, so every manifest-registered artifact under a governed root MUST be
    # recorded. An unrecorded one was written outside the governed writer — a net-new
    # forgery the graph would otherwise project and trust. A run with no index is
    # legacy / non-governed → exempt (the engine stays a no-op for it).
    if index:
        for rel in _registered_artifact_rels(workspace, run_id):
            if rel not in index:
                out.append(_v("AI_UNRECORDED",
                              f"manifest-registered artifact '{rel}' has no watermark — written "
                              f"outside the governed writer; the graph would trust an "
                              f"unverifiable artifact", artifact=rel))
    return out


# Register (guard against double-registration under alias imports).
if not any(name == "artifact_integrity" for name, _ in ENGINES):
    ENGINES.append(("artifact_integrity", validate_artifact_integrity))
