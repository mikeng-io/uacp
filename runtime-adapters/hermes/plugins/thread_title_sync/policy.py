from __future__ import annotations

import fcntl
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

from hermes_constants import get_hermes_home

logger = logging.getLogger(__name__)

_DISCORD_THREAD_LIMIT = 100
_DISPATCH_COUNTER_PREFIX = "discord_dispatch_counter_"
_PREFIX_RE = re.compile(r"^(#\d+)\b")


def _platform_value(platform: Any, source: Any) -> str:
    value = platform or getattr(getattr(source, "platform", None), "value", "")
    return str(value or "").strip().lower()


def _discord_scope_id(source: Any) -> str:
    scope_id = str(
        getattr(source, "parent_chat_id", "")
        or getattr(source, "chat_id", "")
        or ""
    ).strip()
    return scope_id or "global"


def _counter_path(scope_id: str) -> Path:
    safe_scope = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(scope_id).strip()) or "global"
    return get_hermes_home() / f"{_DISPATCH_COUNTER_PREFIX}{safe_scope}"


def _extract_prefix(name: str) -> Optional[str]:
    if not name:
        return None
    match = _PREFIX_RE.match(name)
    return match.group(1) if match else None


def _max_prefix_number(names: Any) -> int:
    max_n = 0
    for name in names or []:
        match = _PREFIX_RE.match(str(name or ""))
        if match:
            max_n = max(max_n, int(match.group(1).lstrip("#")))
    return max_n


def _allocate_counter(source: Any, *, seed: int = 0) -> int:
    path = _counter_path(_discord_scope_id(source))
    try:
        os.makedirs(path.parent, exist_ok=True)
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    except OSError:
        return 1

    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            st = os.fstat(fd)
            raw = b""
            if st.st_size > 0:
                os.lseek(fd, 0, os.SEEK_SET)
                raw = os.read(fd, min(st.st_size, 32))
            current = int(raw.strip()) if raw.strip() else 0
            if seed > current:
                current = seed
            current += 1
            os.lseek(fd, 0, os.SEEK_SET)
            os.ftruncate(fd, 0)
            os.write(fd, str(current).encode())
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
    return current


def _build_discord_thread_name(prefix: str, proposed_title: str) -> str:
    clean_title = (proposed_title or "").strip()
    thread_name = f"{prefix} — {clean_title}" if clean_title else prefix
    if len(thread_name) <= _DISCORD_THREAD_LIMIT:
        return thread_name

    max_title_len = _DISCORD_THREAD_LIMIT - len(prefix) - 3  # " — "
    if max_title_len < 1:
        return thread_name[: _DISCORD_THREAD_LIMIT - 3].rstrip() + "..."
    truncated_title = clean_title[:max_title_len].rstrip()
    return f"{prefix} — {truncated_title}"


def _resolve_discord_title(
    *,
    source: Any,
    proposed_title: str,
    existing_thread_name: str = "",
    live_thread_name: str = "",
    scope_thread_names: Any = None,
) -> dict[str, str]:
    prefix = _extract_prefix(existing_thread_name) or _extract_prefix(live_thread_name)
    if prefix is None:
        prefix = f"#{_allocate_counter(source, seed=_max_prefix_number(scope_thread_names))}"
    thread_name = _build_discord_thread_name(prefix, proposed_title)
    return {
        "action": "rename",
        "title": thread_name,
        "reason": "discord thread title sync",
    }


def handle_pre_thread_title_sync(
    *,
    platform: str = "",
    source: Any = None,
    session_id: str = "",
    proposed_title: str = "",
    existing_thread_name: str = "",
    live_thread_name: str = "",
    scope_thread_names: Any = None,
    **_: Any,
) -> dict[str, str] | None:
    if source is None:
        return None
    if _platform_value(platform, source) != "discord":
        return None
    if not getattr(source, "thread_id", None):
        return None
    if not proposed_title and not existing_thread_name and not live_thread_name:
        return None
    try:
        return _resolve_discord_title(
            source=source,
            proposed_title=proposed_title,
            existing_thread_name=existing_thread_name,
            live_thread_name=live_thread_name,
            scope_thread_names=scope_thread_names,
        )
    except Exception:
        logger.debug("thread_title_sync plugin failed for session %s", session_id, exc_info=True)
        return None
