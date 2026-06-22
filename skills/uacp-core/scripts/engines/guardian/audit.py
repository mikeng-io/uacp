"""Guardian audit-record sink.

Moved verbatim out of ``core.py`` (Phase A1 of the core decomposition,
design/graph-engine node 31). Appends a Guardian decision record as one JSON
line to ``<log root>/uacp/guardian.jsonl``.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path


def write_audit_record(record: Mapping[str, object], *, log_root: str | Path | None = None) -> Path:
    default_root = Path(os.getenv("HERMES_HOME") or Path.home() / ".hermes") / "logs" / "uacp"
    root = Path(log_root) if log_root else Path(os.getenv("HERMES_UACP_LOG_ROOT") or default_root)
    root = root.expanduser()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "guardian.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return path
