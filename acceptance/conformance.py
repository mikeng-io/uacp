"""UACP plugin conformance prober — E2E acceptance harness, Increment 0 (design node 13).

Comprehend the plugin manifest -> the capabilities a UACP install SHOULD expose; MEASURE each is
actionable against the REAL plugin (launch the MCP server as `plugin.json` configures it; resolve +
parse the hooks + skills it ships); SERIALIZE a conformance result. Fail-closed: an EXPECTED but
not-actionable capability is a FAIL (catches "the plugin didn't ship the MCP server" — the council
finding — rather than vacuously passing a near-empty manifest).

This module is the deterministic CORE of the acceptance harness: it needs `uv` + the `mcp` SDK but
NOT a model or a container, so it runs in CI. The container wrapper (acceptance/Dockerfile +
compose.yml) drives this same prober against a real `claude plugin install`.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class CapResult:
    name: str  # capability id (a tool/hook/skill name, or the group)
    kind: str  # mcp_tools | hooks | skills
    status: str  # pass | fail
    detail: str
    evidence: object = None


def _repo_root(start: Path) -> Path:
    """The plugin root == repo root (marketplace.json source is './')."""
    return start.resolve()


def _expected_tool_names(plugin_root: Path) -> set[str]:
    """UACP's EXPECTED governed-tool surface — what the MCP server must list (one source)."""
    scripts = str(plugin_root / "skills" / "uacp-core" / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from tool_specs import tool_specs  # type: ignore

    return {s.name for s in tool_specs()}


def _mcp_launch(plugin_root: Path) -> tuple[str, list[str]]:
    """The command plugin.json launches, with ${CLAUDE_PLUGIN_ROOT} bound."""
    spec = json.loads((plugin_root / ".claude-plugin" / "plugin.json").read_text())
    uacp = spec["mcpServers"]["uacp"]
    args = [a.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root)) for a in uacp["args"]]
    return uacp["command"], args


def _list_tools_over_stdio(command: str, args: list[str], plugin_root: Path) -> list[str]:
    """Launch the server as the plugin does, speak MCP stdio, return the tool names it lists.
    Raises on any failure (caller turns that into a FAIL)."""
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = {
        "PATH": os.environ.get("PATH", ""),
        "CLAUDE_PLUGIN_ROOT": str(plugin_root),
        "HOME": os.environ.get("HOME", str(plugin_root)),
    }

    async def _go() -> list[str]:
        params = StdioServerParameters(command=command, args=args, env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                resp = await session.list_tools()
                return [t.name for t in resp.tools]

    return anyio.run(_go)


def probe_mcp(plugin_root: Path) -> CapResult:
    """Launch the plugin's MCP server and assert its tool set EQUALS tool_specs() (no missing, no
    extra). A missing tool == the packaging regression the council found. Fail-closed."""
    try:
        expected = _expected_tool_names(plugin_root)
        command, args = _mcp_launch(plugin_root)
        listed = set(_list_tools_over_stdio(command, args, plugin_root))
    except Exception as exc:  # server won't launch / mcp absent / manifest broken -> FAIL, not skip
        return CapResult(
            "mcp:uacp",
            "mcp_tools",
            "fail",
            f"MCP server not actionable: {type(exc).__name__}: {exc}",
        )
    missing, extra = expected - listed, listed - expected
    if missing or extra:
        return CapResult(
            "mcp:uacp",
            "mcp_tools",
            "fail",
            f"tool set != tool_specs: missing={sorted(missing)} extra={sorted(extra)}",
            {"listed": sorted(listed)},
        )
    return CapResult(
        "mcp:uacp",
        "mcp_tools",
        "pass",
        f"all {len(expected)} governed tools listed",
        {"tools": sorted(listed)},
    )


def probe_hooks(plugin_root: Path) -> list[CapResult]:
    """The plugin's declared hooks config resolves + parses, and each referenced hook command/script
    exists. (Firing each hook is a deeper probe — design node 13 'to expand'.)"""
    spec = json.loads((plugin_root / ".claude-plugin" / "plugin.json").read_text())
    rel = spec.get("hooks")
    if not rel:
        return [CapResult("hooks", "hooks", "pass", "plugin declares no hooks")]
    hpath = (plugin_root / rel.lstrip("./")).resolve()
    if not hpath.is_file():
        return [CapResult(rel, "hooks", "fail", f"declared hooks file missing: {hpath}")]
    try:
        cfg = json.loads(hpath.read_text())
    except Exception as exc:
        return [CapResult(rel, "hooks", "fail", f"hooks file does not parse: {exc}")]
    # CC hooks.json wraps the event map under a top-level "hooks" key; tolerate either shape.
    events = cfg["hooks"] if isinstance(cfg.get("hooks"), dict) else cfg
    out: list[CapResult] = []
    for event, groups in events.items():
        cmds = [h.get("command", "") for grp in (groups or []) for h in (grp.get("hooks") or [])]
        bad = [c for c in cmds if not c]
        status = "fail" if (not cmds or bad) else "pass"
        out.append(
            CapResult(
                f"hook:{event}",
                "hooks",
                status,
                f"{event}: {len(cmds)} hook command(s) declared",
                {"commands": cmds},
            )
        )
    return out or [CapResult("hooks", "hooks", "fail", "hooks file declares no events")]


def probe_skills(plugin_root: Path) -> list[CapResult]:
    """Each shipped skill is LOADABLE: SKILL.md frontmatter parses + carries a ``name`` (what the
    runtime needs to register it). That is the install-conformance bar — NOT UACP's internal OKF
    ``kind`` convention, which is an authoring rule the in-repo lint owns and which (correctly) does
    NOT apply to vendored third-party skills (e.g. the MIT ``code-review`` skill). A skill with
    unparseable frontmatter or no ``name`` is a packaging regression. Convention-discovered from
    skills/<dir>/SKILL.md (ADR-0017)."""
    import yaml

    sk = plugin_root / "skills"
    out: list[CapResult] = []
    for d in sorted(p for p in sk.iterdir() if p.is_dir() and p.name not in {"vendor", "scripts"}):
        md = d / "SKILL.md"
        if not md.is_file():
            continue  # not every dir is a skill (helpers); only probe dirs that ship a SKILL.md
        try:
            fm = yaml.safe_load(md.read_text().split("---", 2)[1])
            assert isinstance(fm, dict) and fm.get("name"), "frontmatter missing a name"
            kind = fm.get("kind")
            label = f"{fm['name']}" + (f" (kind={kind})" if kind else " (no UACP kind — 3rd-party)")
            out.append(CapResult(f"skill:{d.name}", "skills", "pass", label))
        except Exception as exc:
            out.append(
                CapResult(
                    f"skill:{d.name}",
                    "skills",
                    "fail",
                    f"SKILL.md not loadable: {type(exc).__name__}: {exc}",
                )
            )
    return out or [CapResult("skills", "skills", "fail", "no skills with a SKILL.md found")]


def run(plugin_root: str | Path) -> dict:
    """Probe every expected capability; return the conformance result (pass iff ALL pass)."""
    root = _repo_root(Path(str(plugin_root)))
    caps = [probe_mcp(root), *probe_hooks(root), *probe_skills(root)]
    passed = all(c.status == "pass" for c in caps)
    return {
        "plugin_root": str(root),
        "pass": passed,
        "counts": {"total": len(caps), "fail": sum(c.status == "fail" for c in caps)},
        "capabilities": [asdict(c) for c in caps],
    }


def main(argv: list[str]) -> int:
    root = argv[1] if len(argv) > 1 else "."
    out = argv[3] if len(argv) > 3 and argv[2] == "--out" else None
    result = run(root)
    text = json.dumps(result, indent=2)
    if out:
        Path(out).write_text(text)
    print(text)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
