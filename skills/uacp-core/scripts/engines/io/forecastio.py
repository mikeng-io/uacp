"""Gate-owned cascade-forecast record I/O (design node 04 — prevention forecast).

The plan_exit gate WRITES its own forecast as evidence; the closure sweep JOINS the
observed outcome onto it. This is a gate-owned evidence copy (02 doctrine: legitimate —
it is never a gate INPUT the gate trusts back; the forecast is deterministically
re-derivable from the recorded ``graph_stamp``). The record lives under the governed
verification surface: ``<base>/verification/<run_id>-cascade-forecast.yaml``.

Like every io helper this NEVER raises: a failed write returns ``False``, a malformed or
absent record surfaces as ``(None, error)`` / ``(None, None)`` so the caller emits the
right advisory rather than crashing the sweep.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from config import dir_for


def forecast_record_path(root: Path, run_id: str) -> Path | None:
    """``<base>/verification/<run_id>-cascade-forecast.yaml`` (config-aware), or None when
    the governed verification dir cannot be resolved. Never raises."""
    try:
        vdir = dir_for(Path(root).resolve(), "verification")
    except Exception:
        return None
    return vdir / f"{run_id}-cascade-forecast.yaml"


def write_forecast_record(root: Path, run_id: str, record: dict[str, Any]) -> bool:
    """Write the gate-owned forecast record (LAST-WRITE-WINS across retried plan_exit
    attempts — the forecast of record is the successful transition's write). Creates the
    verification dir if needed. Returns True on success. Never raises."""
    path = forecast_record_path(root, run_id)
    if path is None:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
        return True
    except Exception:
        return False


def load_forecast_record(root: Path, run_id: str) -> tuple[dict[str, Any] | None, str | None]:
    """Load the forecast record. Returns ``(record, None)`` when present and well-formed,
    ``(None, None)`` when ABSENT (no forecast of record — nothing to join), or
    ``(None, error)`` when present but unreadable/not a mapping (→ the caller fires
    SC_FORECAST_JOIN_FAILED). Never raises."""
    path = forecast_record_path(root, run_id)
    if path is None or not path.exists():
        return None, None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"forecast record unreadable: {type(exc).__name__}: {exc}"
    if not isinstance(data, dict):
        return None, "forecast record is not a mapping"
    return data, None
