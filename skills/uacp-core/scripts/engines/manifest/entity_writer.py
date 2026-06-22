"""The Manifest engine's entity-writer — the typed, validated manifest write path (node 35).

``create_entity(workspace, run_id, kind, fields, **ctx)`` runs the fixed pipeline:

  LAYOUT (where) -> SERIALIZE (OKF) -> [VALIDATE shape — C5.3] -> PERSIST + watermark
  (``record_hash``, FAIL-CLOSED) -> REGISTER (State engine) — ATOMIC.

Atomicity (node 35 §2, Codex PR#3): a watermark-persist failure OR a REGISTER failure
rolls back a freshly-created file, so the run manifest never references an unwatermarked
or unregistered orphan. This replicates the ``uacp_artifact_write`` envelope
(``governed_handlers.py``) — the C4-review risk that the low-level write-port alone does
not carry the Guardian/watermark gate.

This sub-increment (C5.2) lands the core for single-instance YAML kinds (the scope
ratchet). Following sub-increments: validate-on-write (C5.3), the Guardian
``artifact.manifest`` category + Layer-B wiring (C5.4), multi-instance registration
(C5.5), and the markdown branch (C5.6).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from config import base_dir
from engines.domain import layout
from engines.domain.artifact_hashes import record_hash
from engines.manifest.governed_writers import _resolve_uacp_path, _write_uacp_file


def _err(msg: str) -> dict[str, Any]:
    return {"error": msg}


def create_entity(
    workspace: str, run_id: str, kind: str, fields: dict[str, Any], **ctx: str
) -> dict[str, Any]:
    """Create a manifest document of ``kind`` for ``run_id`` via the validated write path.

    Returns ``{"ok": True, "path": <rel>, "kind": <kind>, ...}`` or ``{"error": <msg>}``.
    """
    # 1. LAYOUT — where this kind lives (no caller-supplied path).
    fmt = layout.fmt_of(kind)
    if fmt is None:
        return _err(f"unknown kind: {kind!r} (not in the layout registry)")
    try:
        rel = layout.relpath(kind, run_id=run_id, **ctx)
    except KeyError as exc:
        return _err(str(exc))
    # C5.2 supports single-instance YAML kinds (the scope ratchet); markdown is C5.6.
    if fmt != layout.YAML:
        return _err(
            f"entity-writer C5.2 supports YAML kinds only; {kind} is {fmt} (markdown -> C5.6)"
        )

    # 2. SERIALIZE — the OKF doc carries the `kind` const + the typed fields.
    doc: dict[str, Any] = {"kind": kind, **fields}
    content = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)

    # 3. VALIDATE (shape) — C5.3 (deferred): YAML -> schema.validate; markdown -> structural.

    # 4. PERSIST + watermark (FAIL-CLOSED, replicating the uacp_artifact_write envelope).
    base = base_dir(Path(workspace))
    try:
        target = _resolve_uacp_path(rel, base)
    except ValueError as exc:
        return _err(f"layout path is not UACP-containable: {rel} ({exc})")
    existed_before = target.exists()
    try:
        _write_uacp_file(target, content)
    except Exception as exc:
        return _err(f"persist failed: {type(exc).__name__}: {exc}")
    try:
        record_hash(workspace, run_id, rel, content)
    except Exception as exc:
        _rollback(target, existed_before)
        return _err(
            f"watermark could not be persisted ({type(exc).__name__}: {exc}); "
            + ("write rolled back" if not existed_before else "existing artifact retained")
        )

    # 5. REGISTER — cross-engine into the State engine (node 35 §7 boundary; lazy import keeps
    # uacp-core's module-load independent of uacp-state being on sys.path). ATOMIC: a register
    # failure rolls back a freshly-created file so the graph never sees an unregistered orphan.
    from state_machine import handle_register_artifact

    artifact_type = kind.removeprefix("uacp.")
    reg = json.loads(
        handle_register_artifact(
            {
                "workspace": workspace,
                "run_id": run_id,
                "artifact_type": artifact_type,
                "path": rel,
            }
        )
    )
    if reg.get("error"):
        _rollback(target, existed_before)
        verb = "rolled back" if not existed_before else "retained"
        return _err(f"register failed (write {verb}): {reg['error']}")

    return {
        "ok": True,
        "path": rel,
        "kind": kind,
        "artifact_type": artifact_type,
        "watermark": "recorded",
    }


def _rollback(target: Any, existed_before: bool) -> None:
    """Remove a freshly-created file on a downstream-step failure (atomicity)."""
    if not existed_before:
        try:
            target.unlink()
        except OSError:
            pass
