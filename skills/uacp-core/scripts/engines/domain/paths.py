"""Path resolution leaf — locate the active UACP root.

Pure domain helper (stdlib only): resolves the UACP root from an explicit
argument, the ``UACP_ROOT`` / ``HERMES_HOME`` environment, or the default
``~/.hermes/uacp``. Moved verbatim out of ``core.py`` (Phase A1 of the core
decomposition — design/graph-engine node 31 step 8) so engines and gates import
it inward from the domain sink instead of reaching up into ``core``.
"""

from __future__ import annotations

import os
from pathlib import Path


def resolve_uacp_root(uacp_root: str | Path | None = None) -> Path:
    if uacp_root:
        return Path(uacp_root).expanduser().resolve()
    if os.getenv("UACP_ROOT"):
        return Path(os.environ["UACP_ROOT"]).expanduser().resolve()
    if os.getenv("HERMES_HOME"):
        return (Path(os.environ["HERMES_HOME"]).expanduser() / "uacp").resolve()
    return (Path.home() / ".hermes" / "uacp").resolve()
