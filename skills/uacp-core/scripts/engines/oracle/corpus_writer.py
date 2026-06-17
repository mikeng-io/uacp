"""Oracle corpus-write surface — the ONLY governed path that writes the corpus.

The Oracle is the single owner of the knowledge/lesson corpus (``.uacp/lessons/``
and ``.uacp/knowledge/``). Every corpus write goes through this surface, which
serializes an OKF document (via :class:`engines.domain.corpus.Lesson` /
:class:`engines.domain.corpus.KnowledgeItem`) and writes it through the
**governed artifact writer** (the ``uacp_artifact_write`` handler) so Guardian
still audits the write. No raw filesystem writes happen here.

Callers (e.g. RESOLVE lesson extraction/distillation) MUST route corpus writes
through ``persist_lesson`` / ``persist_knowledge`` rather than calling
``uacp_artifact_write`` directly or touching the filesystem — that keeps the
data-ownership boundary intact (see tests/unit/uacp_oracle/test_corpus_boundary.py).

This module performs NO heavy/ML imports — it is part of the floor.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from engines.domain.corpus import KnowledgeItem, Lesson


def _governed_artifact_write(args: dict[str, Any]) -> dict[str, Any]:
    """Invoke the governed ``uacp_artifact_write`` handler and return its result dict.

    The handler is the runtime boundary that Guardian audits. It is imported
    lazily so the corpus-writer module has no hard dependency on the Hermes
    adapter at import time (floor-safe). The handler resolves the UACP root from
    the ``UACP_ROOT`` env / cached policy, so we pin the env to the workspace and
    reset the cached policy before calling.
    """
    handler, plugin = _resolve_handler()
    workspace = str(args["workspace"])

    prev_root = os.environ.get("UACP_ROOT")
    os.environ["UACP_ROOT"] = workspace
    # The plugin caches the GuardianPolicy at module level keyed off UACP_ROOT;
    # reset it so the handler binds to the workspace we are writing into.
    if plugin is not None:
        plugin._POLICY = None
    try:
        raw = handler(args)
    finally:
        if prev_root is None:
            os.environ.pop("UACP_ROOT", None)
        else:
            os.environ["UACP_ROOT"] = prev_root
        if plugin is not None:
            plugin._POLICY = None

    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {"error": f"governed writer returned non-JSON: {raw!r}"}


def _resolve_handler():
    """Locate the governed artifact-write handler + its plugin module. Lazy."""
    try:
        import uacp_guardian as plugin  # type: ignore

        return plugin._handle_uacp_artifact_write, plugin
    except Exception:
        pass

    # Path bootstrap: the plugin is a package (uacp_guardian) whose __init__ uses
    # both relative (.kernel) and absolute (filesystem, config) imports. Importing
    # it by package name needs the plugins/ PARENT dir on sys.path.
    import sys

    core_scripts = Path(__file__).resolve().parents[2]
    repo_root = core_scripts.parents[2]  # .../skills/uacp-core/scripts -> repo root
    plugins_dir = repo_root / "runtime-adapters" / "hermes" / "plugins"
    if str(plugins_dir) not in sys.path:
        sys.path.insert(0, str(plugins_dir))
    # The absolute imports inside the plugin (filesystem, config) live under
    # uacp-core/scripts, which the oracle package is already importable from.
    if str(core_scripts) not in sys.path:
        sys.path.insert(0, str(core_scripts))
    import uacp_guardian as plugin  # type: ignore

    return plugin._handle_uacp_artifact_write, plugin


def _write_okf(
    workspace: Path | str,
    *,
    path_key: str,
    item_id: str,
    okf_text: str,
    run_id: str,
    phase: str,
    reason: str,
    authority_artifact: str,
) -> dict[str, Any]:
    target_path = f"{path_key}/{item_id}.md"
    args = {
        "target_path": target_path,
        "content": okf_text,
        "reason": reason,
        "authority_artifact": authority_artifact,
        "workspace": str(Path(workspace)),
        "uacp_run_id": run_id,
        "uacp_phase": phase,
        "policy_version": "",
        "declared_side_effects": [f"write {target_path}"],
    }
    return _governed_artifact_write(args)


def persist_lesson(
    workspace: Path | str,
    lesson: Lesson,
    *,
    run_id: str,
    phase: str = "resolve",
    reason: str = "persist lesson to corpus",
    authority_artifact: str,
) -> dict[str, Any]:
    """Serialize ``lesson`` to OKF and write it to ``.uacp/lessons/<id>.md``.

    Routes through the governed artifact writer. Returns the handler's result
    dict (``{"ok": True, "path": ...}`` on success, ``{"error": ...}`` on
    rejection). Never raises for a rejected write — the governed writer's
    error is surfaced in the result.
    """
    return _write_okf(
        workspace,
        path_key="lessons",
        item_id=lesson.id,
        okf_text=lesson.to_okf(),
        run_id=run_id,
        phase=phase,
        reason=reason,
        authority_artifact=authority_artifact,
    )


def persist_knowledge(
    workspace: Path | str,
    item: KnowledgeItem,
    *,
    run_id: str,
    phase: str = "resolve",
    reason: str = "persist knowledge to corpus",
    authority_artifact: str,
) -> dict[str, Any]:
    """Serialize ``item`` to OKF and write it to ``.uacp/knowledge/<id>.md``.

    Routes through the governed artifact writer (Guardian-audited).
    """
    return _write_okf(
        workspace,
        path_key="knowledge",
        item_id=item.id,
        okf_text=item.to_okf(),
        run_id=run_id,
        phase=phase,
        reason=reason,
        authority_artifact=authority_artifact,
    )
