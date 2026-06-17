"""Deterministic run-state source for the Oracle engine.

Reads UACP run manifests from the workspace's .uacp/state/runs/ directory
and returns authoritative ProviderPackets. No ML deps. No external calls.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap core scripts path for engines imports
_RUNSTATE_DIR = Path(__file__).resolve().parent
_ORACLE_DIR = _RUNSTATE_DIR.parent
_ENGINES_DIR = _ORACLE_DIR.parent
_CORE_DIR = _ENGINES_DIR.parent
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from engines.io.loaders import glob_in_workspace, load_manifest  # noqa: E402
from engines.oracle.packets import ProviderPacket, TrustClass  # noqa: E402
from engines.oracle.repo import repo_commit  # noqa: E402


def query_runstate(
    workspace: Path,
    *,
    project: str,
    phase: str | None = None,
    limit: int = 10,
) -> list[ProviderPacket]:
    """Return ProviderPackets from recent run manifests in the workspace.

    Reads .uacp/state/runs/*.yaml files, filters to manifests for the given
    project, and returns up to `limit` packets as authoritative trust class.

    Args:
        workspace: Path to the UACP workspace root
        project: project identifier to filter by (matches manifest 'project' field)
        phase: optional phase filter (if set, only include manifests at this phase)
        limit: maximum number of packets to return

    Returns:
        List of ProviderPacket with trust_class=authoritative
    """
    workspace = Path(workspace)
    packets: list[ProviderPacket] = []
    commit = repo_commit(workspace)

    # glob_in_workspace globs under .uacp/
    manifest_paths = glob_in_workspace(workspace, "state/runs/*.yaml")

    for path in sorted(manifest_paths, reverse=True)[:limit * 2]:
        run_id = path.stem
        loaded = load_manifest(workspace, run_id)
        if loaded.error is not None or loaded.value is None:
            continue

        raw = loaded.value.raw
        # Filter by project
        if raw.get("project") != project:
            continue
        # Filter by phase if specified
        if phase is not None and raw.get("phase") != phase:
            continue

        summary = {
            "run_id": run_id,
            "phase": raw.get("phase", ""),
            "status": raw.get("status", ""),
            "project": raw.get("project", ""),
        }
        if raw.get("goal_id"):
            summary["goal_id"] = raw["goal_id"]

        packets.append(
            ProviderPacket(
                source="runstate",
                trust_class=TrustClass.authoritative,
                payload=summary,
                score=1.0,
                evidence_required=False,
                metadata={"run_id": run_id, "repo_commit": commit},
            )
        )
        if len(packets) >= limit:
            break

    return packets
