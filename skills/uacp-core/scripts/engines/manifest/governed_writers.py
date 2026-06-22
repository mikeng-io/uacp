"""The Manifest engine's governed write-port (Phase C / node 34 §3 item 3).

The entity-writer (node 35) persists manifest documents through the low-level
Guardian-gated FS primitive. This module is that primitive's seam *for the
Manifest engine*: ``_resolve_uacp_path`` (UACP-root containment: rejects absolute
paths, ``..`` traversal, and symlinked components) + ``_write_uacp_file`` (dir
guard, YAML parse-validity, atomic-ish write).

AS-BUILT DEVIATION FROM THE DESIGN'S LITERAL "physical move" (documented for review):
the design (node 34 §3) said *move* the primitive here with a re-export shim left at
``filesystem.py``. That is infeasible as-built — the primitive is **shared infra**:
a re-export shim at ``filesystem.py`` (``from engines.manifest... import ...``) cycles,
because importing anything under ``engines.manifest`` eagerly runs this package's
``__init__`` -> ``projection`` -> ``from engines.io import ...`` -> ``loaders`` ->
``from filesystem import _resolve_uacp_path`` — re-entering the half-initialised
``filesystem`` module (ImportError). And ``uacp-state`` (``state.py`` /
``state_machine.py``) writes through ``_write_uacp_file`` too, so relocating it *into*
the Manifest engine would couple the State engine backwards onto it. The primitive is
therefore left in ``filesystem.py`` (a shared leaf — only ``pathlib`` at module level,
a lazy ``import yaml`` inside ``_write_uacp_file``) and the Manifest engine RE-EXPORTS
it here as its write-port. Relocating the shared FS primitive to ``engines/io`` (the
"sole disk-touch", node 34 §4) is the correct longer-term home but a separate,
wider-blast-radius refactor (config / governed_handlers / loaders / state /
state_machine + tests), not part of the manifest carve.
"""

from __future__ import annotations

from filesystem import _resolve_uacp_path, _write_uacp_file

__all__ = [
    "_resolve_uacp_path",
    "_write_uacp_file",
]
