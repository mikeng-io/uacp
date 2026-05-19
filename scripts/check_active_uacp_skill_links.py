#!/usr/bin/env python3
"""Check active Hermes UACP skill exports for stale UACP path references."""
from __future__ import annotations

import re
import sys
from pathlib import Path

UACP_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = Path.home() / ".hermes" / "skills" / "devops" / "uacp"

PATTERNS = [
    re.compile(r"UACP_ROOT/([^`\s)]+)"),
    re.compile(r"`(\.\./references/[^`]+)`"),
    re.compile(r"`(references/[^`]+)`"),
]

BROKEN_LITERAL_PATTERNS = [
    "UACP_ROOT/docs/index.md",
    "UACP_ROOT/docs/lifecycle-reference.md",
    "UACP_ROOT/docs/orchestration-model.md",
    "UACP_ROOT/docs/state.yaml",
    "uacp/references/",
    "../uacp/references/",
]


def main() -> int:
    issues: list[str] = []
    if not SKILL_ROOT.exists():
        print(f"WARN active skill root not found: {SKILL_ROOT}")
        return 0
    for path in SKILL_ROOT.rglob("SKILL.md"):
        text = path.read_text(encoding="utf-8")
        for literal in BROKEN_LITERAL_PATTERNS:
            if literal in text:
                issues.append(f"{path}: stale literal reference {literal}")
        for match in PATTERNS[0].finditer(text):
            rel = match.group(1).rstrip(".,;:")
            if "<" in rel or ">" in rel:
                continue
            if not (UACP_ROOT / rel).exists():
                issues.append(f"{path}: missing UACP_ROOT/{rel}")
        for pattern in PATTERNS[1:]:
            for match in pattern.finditer(text):
                rel = match.group(1)
                target = (path.parent / rel).resolve()
                if not target.exists():
                    issues.append(f"{path}: missing relative reference {rel}")
    if issues:
        for issue in issues:
            print(f"BLOCK {issue}")
        return 2
    print("SKILL_LINK_CHECK_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
