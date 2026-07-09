from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _resolve_uacp_path(raw: str, root: Path) -> Path:
    root = root.resolve()
    path = Path(raw)
    if path.is_absolute():
        raise ValueError("target_path must be UACP-root-relative")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("target_path must not contain empty, current, or parent path segments")
    candidate = root / path
    # Fail closed on symlinked path components before writing.  A symlink inside
    # UACP_ROOT can otherwise resolve outside the governed workspace.
    current = root
    for part in path.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError("target_path must not traverse symlinked directories")
    if candidate.exists() and candidate.is_symlink():
        raise ValueError("target_path must not be a symlink")
    resolved = candidate.resolve(strict=False)
    if resolved == root:
        raise ValueError("target_path must point to a file under UACP_ROOT")
    if root not in resolved.parents:
        raise ValueError("target_path escapes UACP_ROOT")
    return resolved


def _write_uacp_file(target: Path, content: str) -> None:
    if target.exists() and target.is_dir():
        raise ValueError("target_path must point to a file, not a directory")
    if target.suffix in {".yaml", ".yml"}:
        import yaml

        # Validate BEFORE writing anything (fail-closed): a malformed YAML never
        # reaches disk, and no temp file is created.
        yaml.safe_load(content)
    target.parent.mkdir(parents=True, exist_ok=True)
    # ATOMIC write (#103-W1): write to a temp file in the SAME directory, flush +
    # fsync, then os.replace() — an atomic rename on the same filesystem. A reader
    # (or a crash) therefore never observes a partially-written governed state file:
    # target is always either the complete OLD content or the complete NEW content,
    # never a truncated mix. A failure at any step cleans up the temp and leaves the
    # existing target untouched.
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            # The temp was already renamed onto the target (os.replace succeeded and a
            # later step raised) or never created — nothing to clean up.
            pass
        raise
