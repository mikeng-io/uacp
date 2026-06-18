#!/usr/bin/env python3
"""Install the UACP Guardian PreToolUse hook into Kimi Code's config.toml.

Kimi Code reads ``~/.kimi-code/config.toml`` and runs ``[[hooks]]`` blocks. This
installer prints the block to add (dry-run by default) and, with ``--apply``,
appends it idempotently with a timestamped backup.

The block:

    [[hooks]]
    event = "PreToolUse"
    matcher = "*"
    command = "python3 <abs>/runtime-adapters/hooks/guardian_pretooluse.py --profile kimi"
    timeout = 10

Idempotent: if a PreToolUse hook whose command already points at this shim is
present, ``--apply`` is a no-op (it does not append a duplicate).
"""

from __future__ import annotations

import argparse
import datetime
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SHIM = _REPO_ROOT / "runtime-adapters" / "hooks" / "guardian_pretooluse.py"
_DEFAULT_CONFIG = Path.home() / ".kimi-code" / "config.toml"


def _command() -> str:
    return f'python3 {_SHIM} --profile kimi'


def _block() -> str:
    return (
        "\n[[hooks]]\n"
        'event = "PreToolUse"\n'
        'matcher = "*"\n'
        f'command = "{_command()}"\n'
        "timeout = 10\n"
    )


def _already_installed(text: str) -> bool:
    # Dedupe on the shim path appearing inside a PreToolUse hook command. We do a
    # conservative substring check (the shim absolute path + the PreToolUse event)
    # rather than a full TOML parse so this stays stdlib-only and robust to hand
    # edits / comments around the block.
    return "PreToolUse" in text and str(_SHIM) in text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="append the block to the config (with backup + idempotent dedupe); "
        "otherwise just print it.",
    )
    parser.add_argument(
        "--config",
        default=str(_DEFAULT_CONFIG),
        help=f"path to Kimi config.toml (default: {_DEFAULT_CONFIG})",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    block = _block()
    config_path = Path(args.config).expanduser()

    if not args.apply:
        sys.stdout.write(
            f"# Add the following [[hooks]] block to {config_path}:\n{block}"
        )
        return 0

    existing = config_path.read_text(encoding="utf-8") if config_path.is_file() else ""
    if _already_installed(existing):
        sys.stdout.write(
            f"UACP Guardian PreToolUse hook already present in {config_path} — no change.\n"
        )
        return 0

    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.is_file():
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = config_path.with_suffix(config_path.suffix + f".bak-{stamp}")
        shutil.copy2(config_path, backup)
        sys.stdout.write(f"Backed up existing config to {backup}\n")

    new_text = existing + (block if existing.endswith("\n") or not existing else "\n" + block)
    config_path.write_text(new_text, encoding="utf-8")
    sys.stdout.write(f"Installed UACP Guardian PreToolUse hook into {config_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
