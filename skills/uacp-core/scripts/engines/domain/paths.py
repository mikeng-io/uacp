"""Path resolution leaf — locate the active UACP root.

Pure domain helper (stdlib only): resolves the UACP root from an explicit
argument or the ``UACP_ROOT`` / ``HERMES_HOME`` environment. Moved verbatim out
of ``core.py`` (Phase A1 of the core decomposition — design/graph-engine node 31
step 8) so engines and gates import it inward from the domain sink instead of
reaching up into ``core``.

Fail-closed: if no root can be determined, raise rather than guess. The legacy
``~/.hermes/uacp`` default was removed — it silently bound callers to a stale
Hermes-runtime home when neither an explicit root nor the env was set, which
mis-governed any other runtime (e.g. the Claude Code session that surfaced this).
"""

from __future__ import annotations

import os
from pathlib import Path


class UacpRootUnresolvedError(RuntimeError):
    """Raised when the UACP root cannot be resolved from arg or environment."""


def resolve_uacp_root(uacp_root: str | Path | None = None) -> Path:
    if uacp_root:
        return Path(uacp_root).expanduser().resolve()
    if os.getenv("UACP_ROOT"):
        return Path(os.environ["UACP_ROOT"]).expanduser().resolve()
    if os.getenv("HERMES_HOME"):
        return (Path(os.environ["HERMES_HOME"]).expanduser() / "uacp").resolve()
    raise UacpRootUnresolvedError(
        "cannot resolve the UACP root: pass an explicit root, or set UACP_ROOT "
        "(or HERMES_HOME for the Hermes runtime). The legacy ~/.hermes/uacp "
        "default was removed as stale/legacy."
    )
