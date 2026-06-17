"""Serving resolver for the Oracle engine.

Resolves the endpoint URL for a given oracle service and role using a three-level
priority: explicit url-override > embedded workspace config > floor default.

Two surfaces:
  * ``resolve_serving_url(workspace, role, url_override=...)`` — the original
    workspace-config URL lookup (preserved verbatim for existing callers).
  * ``resolve_role(role, oracle_cfg, deps_present=...)`` — the per-role serving
    decision the clients consume. Precedence: ``url override > embedded > floor``.
    Per role it is exactly one mode, never both. ``enabled=false`` forces FLOOR
    for every role; ``query_expansion`` additionally honors its own ``enabled``
    flag. The embedded default needs the optional in-process llama.cpp binding;
    absent it (and with no URL) the role degrades to the FLOOR (keyword + BES,
    zero models). The binding is resolved lazily and never imported at top level.
"""
from __future__ import annotations

import enum
import importlib
import sys
from dataclasses import dataclass
from pathlib import Path

_SERVING_DIR = Path(__file__).resolve().parent
_ENGINES_DIR = _SERVING_DIR.parent
_CORE_DIR = _ENGINES_DIR.parent
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from config import get_config  # noqa: E402

# Floor (no-config) defaults per service role
_FLOOR_DEFAULTS: dict[str, str] = {
    "embedding": "",
    "rerank": "",
    "honcho": "",
}


def resolve_serving_url(
    workspace: Path,
    role: str,
    *,
    url_override: str | None = None,
) -> str:
    """Resolve the service endpoint URL for a given role.

    Priority order:
      1. url_override (if provided and non-empty)
      2. config [oracle.<role>] url (from uacp.toml / .uacp/config.toml override)
      3. floor default (empty string = not configured)

    Args:
        workspace: UACP workspace root
        role: service role ("embedding", "rerank", "honcho")
        url_override: explicit override URL, bypasses config lookup

    Returns:
        Resolved URL string, or "" if not configured
    """
    if url_override:
        return url_override

    # Try config
    try:
        oracle_cfg = get_config(workspace).model_extra.get("oracle", {})
        role_cfg = oracle_cfg.get(role, {})
        if isinstance(role_cfg, dict):
            url = role_cfg.get("url", "")
            if url:
                return url
    except Exception:
        pass

    return _FLOOR_DEFAULTS.get(role, "")


class ServingMode(enum.Enum):
    URL = "url"
    EMBEDDED = "embedded"
    FLOOR = "floor"


@dataclass(frozen=True)
class RoleServing:
    """Resolved serving decision for one role. Exactly one mode, never both."""

    role: str
    mode: ServingMode
    model: str = ""
    url: str = ""


def embedded_runtime_present() -> bool:
    """True iff the in-process llama.cpp binding can be imported. Lazy, never raises."""
    for cand in ("llama_cpp",):  # exact binding settled at impl; kept behind this helper
        try:
            importlib.import_module(cand)
            return True
        except Exception:
            continue
    return False


def resolve_role(
    role: str,
    oracle_cfg: dict,
    *,
    deps_present: bool | None = None,
) -> RoleServing:
    """Resolve the serving mode for a role: url override > embedded > floor.

    Args:
        role: "embedding", "rerank", or "query_expansion"
        oracle_cfg: the [oracle] config dict
        deps_present: override the embedded-binding probe (None = probe lazily)

    Returns:
        RoleServing with exactly one mode. enabled=false (oracle or, for
        query_expansion, the role's own flag) forces FLOOR.
    """
    if not oracle_cfg.get("enabled", False):
        return RoleServing(role, ServingMode.FLOOR)

    role_cfg = oracle_cfg.get(role) or {}
    if not isinstance(role_cfg, dict):
        role_cfg = {}

    # query_expansion is optional and carries its own enable switch.
    if role == "query_expansion" and not role_cfg.get("enabled", True):
        return RoleServing(role, ServingMode.FLOOR)

    url = str(role_cfg.get("url") or "").strip()
    model = str(role_cfg.get("model") or "")
    if url:
        return RoleServing(role, ServingMode.URL, model=model, url=url)

    present = embedded_runtime_present() if deps_present is None else deps_present
    if present:
        return RoleServing(role, ServingMode.EMBEDDED, model=model)
    return RoleServing(role, ServingMode.FLOOR, model=model)
