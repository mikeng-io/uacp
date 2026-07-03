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

import os
import tempfile
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
    """Write the gate-owned forecast record ATOMICALLY (design node 04 / K2).

    Serializes to a temp file IN THE SAME DIRECTORY, ``fsync``s it, then ``os.replace``s it
    over the target — an atomic rename on POSIX, so a reader never observes a half-written
    record and a crash mid-write cannot leave a partial file (last-write-wins across retried
    plan_exit attempts is preserved: the replace is the write). On ANY persistence failure
    the temp file is cleaned up and ``False`` is returned (the caller emits
    SC_FORECAST_WRITE_FAILED rather than silently dropping the record). Creates the
    verification dir if needed. Never raises."""
    path = forecast_record_path(root, run_id)
    if path is None:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = yaml.safe_dump(record, sort_keys=False)
    except Exception:
        return False

    tmp_path: Path | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)  # atomic within the same directory
        return True
    except Exception:
        # Clean the temp so a partial file never lingers (K2: partial-file impossible by
        # construction — the target is only ever swapped in by an atomic rename).
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except OSError:
                pass
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
