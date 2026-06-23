"""The Manifest engine's entity-writer — the typed, validated manifest write path (node 35).

``create_entity(workspace, run_id, kind, fields, **ctx)`` is the write side of the Manifest engine.
It writes ONLY **RELATION-plane lifecycle documents** (the manifest docs under plans/ proposals/
executions/ verification/ resolutions/ brainstorm/…) — never the STATE plane, which the State engine
owns — through the fixed pipeline:

  LAYOUT (where, plane-guarded) -> SERIALIZE (OKF; YAML or markdown) -> VALIDATE-on-write (shape,
  ratcheted) -> PERSIST + watermark (record_hash, FAIL-CLOSED) -> REGISTER (State engine).

ATOMICITY (node 35 §2, Codex PR#3 + C5 review F2/F3): a watermark-persist OR register failure
RESTORES the target to its prior state — a freshly-created file is removed and its just-recorded
watermark forgotten; a pre-existing file's original bytes + watermark are restored. This is
EXCEPTION-atomic (rollback on caught errors), NOT crash-atomic: a process crash mid-pipeline can
still leave an unwatermarked or unregistered file (crash-recovery would need a write-ahead journal —
a follow-on, Kimi #4). Concurrent same-run writes are not serialized — the State layer assumes a
single writer per run (Kimi #3); the watermark index now writes atomically (temp+rename) so a
partial write cannot wipe it.

CONTAINMENT (C5 review F1/F6): the RELATION-plane guard (stricter than uacp_artifact_write's
allow/forbid-root set, which forbids state/docs/config) + ctx sanitization + ``_resolve_uacp_path``
(UACP-root containment) + the fail-closed watermark give the entity-writer containment at least as
strong as the low-level governed writer.

DEFERRED (T-008): the governed-tool runtime exposure + Guardian unbypassable cutover, and markdown
write-time STRUCTURAL validation (today deferred to the transition gate's carved validators).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from config import base_dir
from engines.domain import layout, schema
from engines.domain.artifact_hashes import forget_hash, record_hash
from engines.manifest.governed_writers import _resolve_uacp_path, _write_uacp_file


def _err(msg: str) -> dict[str, Any]:
    return {"error": msg}


def _bad_ctx_value(v: Any) -> bool:
    """A path-placeholder value that could break a path segment or be empty."""
    s = str(v)
    return (not s.strip()) or ("/" in s) or ("\\" in s) or (".." in s)


def create_entity(
    workspace: str, run_id: str, kind: str, fields: dict[str, Any], **ctx: str
) -> dict[str, Any]:
    """Create a RELATION-plane manifest document of ``kind`` for ``run_id`` via the validated
    write path. Returns ``{"ok": True, "path": <rel>, ...}`` or ``{"error": <msg>}``."""
    # 1. LAYOUT — where this kind lives (no caller-supplied path).
    fmt = layout.fmt_of(kind)
    if fmt is None:
        return _err(f"unknown kind: {kind!r} (not in the layout registry)")
    # PLANE GUARD (F1): the entity-writer owns only RELATION-plane lifecycle documents. STATE-plane
    # kinds (run_manifest / run_registry / current_state / gate_ledger / …) belong to the State
    # engine and its governed writers — never write them here.
    if layout.plane_of(kind) != layout.RELATION:
        return _err(
            f"entity-writer writes RELATION-plane lifecycle docs only; {kind} is plane "
            f"{layout.plane_of(kind)!r} (owned by the State engine)"
        )
    # run_id + ctx sanitization (F6 + Kimi #5): placeholders are interpolated into the path; reject
    # segment-breaking/empty values (defense-in-depth atop _resolve_uacp_path), and sanitize run_id
    # itself — it is NOT covered by the ctx loop. (Kimi #6, a `run_id` key in ctx, is unreachable:
    # `run_id` is a named param, so a run_id= kwarg binds to it and Python raises at the call
    # boundary; it can never land in **ctx.)
    if _bad_ctx_value(run_id):
        return _err(f"invalid run_id: {run_id!r}")
    bad = {k: ctx[k] for k in ctx if _bad_ctx_value(ctx[k])}
    if bad:
        return _err(f"invalid path-placeholder value(s): {bad}")
    try:
        rel = layout.relpath(kind, run_id=run_id, **ctx)
    except KeyError as exc:
        return _err(str(exc))

    # 2. SERIALIZE + 3. VALIDATE (shape) — branched by layout format (node 35 §2.4).
    if fmt == layout.YAML:
        # Identity (kind + run_id) is injected LAST so caller `fields` cannot forge the
        # writer-owned kind/run_id (Kimi #1 / Codex PR#5: for ratchet-unschematised kinds a
        # forged `kind` would otherwise persist with no const check).
        doc: dict[str, Any] = {**fields, "kind": kind, "run_id": run_id}
        content = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
        # VALIDATE-ON-WRITE, RATCHETED (node 33 / node 35 §5): enforce shape only for kinds with a
        # registered schema, so the ratchet grows per-kind. Reject on any violation: NO write.
        if schema.has_schema(kind):
            shape_errors = schema.validate(kind, doc)
            if shape_errors:
                return _err(f"validate-on-write rejected {kind}: " + "; ".join(shape_errors))
    elif fmt == layout.MARKDOWN:
        # OKF markdown: `kind` frontmatter + caller body. Reject a body that injects its OWN
        # frontmatter fence (F4) — it would produce a double-frontmatter doc / forged `kind`.
        body = str(fields.get("body", ""))
        # Strip leading BOM / zero-width chars before the fence check (Kimi #8: a body prefixed
        # with ﻿ bypassed a plain lstrip()).
        if body.lstrip("﻿​￾ \t\r\n").startswith("---"):
            return _err("markdown body must not begin with a '---' frontmatter fence")
        content = f"---\nkind: {kind}\n---\n\n{body}"
    else:
        return _err(f"entity-writer: unsupported layout format {fmt!r} for {kind}")

    # 4. PERSIST + watermark (FAIL-CLOSED). Snapshot prior state for atomic restore (F2).
    base = base_dir(Path(workspace))
    try:
        target = _resolve_uacp_path(rel, base)
    except ValueError as exc:
        return _err(f"layout path is not UACP-containable: {rel} ({exc})")
    existed_before = target.exists()
    prior_content = target.read_text(encoding="utf-8") if existed_before else None
    try:
        _write_uacp_file(target, content)
    except Exception as exc:
        return _err(f"persist failed: {type(exc).__name__}: {exc}")
    try:
        record_hash(workspace, run_id, rel, content)
    except Exception as exc:
        _rollback(workspace, run_id, target, rel, existed_before, prior_content)
        return _err(f"watermark could not be persisted ({type(exc).__name__}: {exc}); rolled back")

    # 5. REGISTER — cross-engine into the State engine (lazy import: the uacp-core/uacp-state seam).
    from state_machine import handle_register_artifact

    # MULTI-INSTANCE (Codex PR#3 + F7): kinds with placeholders beyond {run_id} register under a
    # COMPOSITE key (type:k=v-…) so instances don't overwrite each other in manifest.artifacts; the
    # k=v form avoids suffix-collision across multi-placeholder kinds.
    artifact_type = kind.removeprefix("uacp.")
    if ctx:
        suffix = "-".join(f"{k}={ctx[k]}" for k in sorted(ctx))
        artifact_type = f"{artifact_type}:{suffix}"
    reg = json.loads(
        handle_register_artifact(
            {"workspace": workspace, "run_id": run_id, "artifact_type": artifact_type, "path": rel}
        )
    )
    if reg.get("error"):
        _rollback(workspace, run_id, target, rel, existed_before, prior_content)
        return _err(f"register failed (rolled back): {reg['error']}")

    return {
        "ok": True,
        "path": rel,
        "kind": kind,
        "artifact_type": artifact_type,
        "watermark": "recorded",
    }


def _rollback(
    workspace: str,
    run_id: str,
    target: Any,
    rel: str,
    existed_before: bool,
    prior_content: str | None,
) -> None:
    """Restore the target to its prior state after a downstream-step failure (atomicity, F2/F3).

    Pre-existing file -> restore the original bytes AND re-record the original content's watermark
    (so index and file agree). Fresh file -> remove it AND forget its just-recorded watermark.
    Best-effort: rollback must never raise."""
    try:
        if existed_before and prior_content is not None:
            target.write_text(prior_content, encoding="utf-8")
            record_hash(workspace, run_id, rel, prior_content)
        else:
            target.unlink()
            forget_hash(workspace, run_id, rel)
    except Exception:
        pass
