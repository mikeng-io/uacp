# Backward-compatibility shim.
# Canonical source is now skills/uacp-core/scripts/core.py.
from __future__ import annotations

import sys
from pathlib import Path

_CORE_DIR = Path(__file__).resolve().parents[4] / "skills" / "uacp-core" / "scripts"
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from core import *  # noqa: F401,F403
from core import _is_safe_run_id, _truthy, _load_artifact_schemas  # noqa: F401
