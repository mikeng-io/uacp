"""Serving resolver for the Oracle engine.

Resolves the endpoint URL for a given oracle service and role using a three-level
priority: explicit url-override > embedded workspace config > floor default.
"""
from __future__ import annotations

import sys
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
