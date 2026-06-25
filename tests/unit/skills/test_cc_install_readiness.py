"""Claude Code plugin install-readiness smoke test.

Two layers:
  (a) STATIC structural validation (always runs, no external binary):
      - .claude-plugin/marketplace.json parses as JSON with required fields
      - .claude-plugin/plugin.json parses as JSON with required fields
      - every plugin entry in marketplace.json resolves to a real plugin dir
      - all bundled components referenced by manifests exist on disk
      - `author` (if present anywhere) is an object, not a string

  (b) REAL loader check (gated by claude CLI presence):
      - if `claude` is on PATH, run `claude plugin marketplace add <repo>`
        and `claude plugin install uacp@<mktplace>` then clean up; assert
        both exit 0. Skipped when claude CLI is absent.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_DIR = REPO_ROOT / ".claude-plugin"
PLUGIN_JSON = PLUGIN_DIR / "plugin.json"
MARKETPLACE_JSON = PLUGIN_DIR / "marketplace.json"
SKILLS_DIR = REPO_ROOT / "skills"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict:
    """Load JSON from path; raise with a clear message on failure."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        pytest.fail(f"{path.relative_to(REPO_ROOT)} is not valid JSON: {exc}")
    except FileNotFoundError:
        pytest.fail(f"{path.relative_to(REPO_ROOT)} does not exist")


def _bare_req_name(spec: str) -> str:
    """Lowercased bare package name from a PEP 508 requirement string — strips
    extras and any version/marker specifier. Shared by both sides of the manifest
    drift guard so the two parsers can never disagree on normalization."""
    name = spec.strip()
    for sep in ("[", ">", "<", "=", "!", "~", ";", " "):
        name = name.split(sep)[0]
    return name.strip().lower()


def _kernel_runtime_dep_names() -> set[str]:
    """Normalized package names the MCP server needs at runtime: pyproject's core
    [project.dependencies] plus the `mcp` optional extra (the server's own dep).

    Reads the single source of truth (pyproject.toml) so the manifest drift guard
    never hardcodes the list. Returns lowercased bare names (no version specifier).
    """
    try:
        import tomllib  # py3.11+
    except ModuleNotFoundError:  # pragma: no cover - fallback for <3.11
        import tomli as tomllib  # type: ignore

    pyproject = REPO_ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data.get("project", {})
    specs = list(project.get("dependencies", []))
    specs += list(project.get("optional-dependencies", {}).get("mcp", []))

    return {_bare_req_name(s) for s in specs if _bare_req_name(s)}


def _assert_not_string_author(data: dict, label: str) -> None:
    """Regression guard for the known CC bug: author must be an object, not a string."""
    author = data.get("author")
    if author is not None:
        assert not isinstance(author, str), (
            f"{label}: 'author' must be an object ({{\"name\": ...}}), "
            f"not a plain string — known Claude Code bug. "
            f"Got: {author!r}"
        )


# ---------------------------------------------------------------------------
# Layer (a): static structural validation
# ---------------------------------------------------------------------------


class TestMarketplaceJson:
    """Validate .claude-plugin/marketplace.json structure."""

    def test_file_exists(self) -> None:
        assert MARKETPLACE_JSON.is_file(), (
            f"{MARKETPLACE_JSON.relative_to(REPO_ROOT)} missing — "
            "create .claude-plugin/marketplace.json to make the plugin distributable"
        )

    def test_parses_as_json(self) -> None:
        _load_json(MARKETPLACE_JSON)  # raises on parse failure

    def test_has_name(self) -> None:
        data = _load_json(MARKETPLACE_JSON)
        assert "name" in data and data["name"], (
            "marketplace.json must have a non-empty 'name' field (kebab-case)"
        )

    def test_name_is_kebab_case(self) -> None:
        data = _load_json(MARKETPLACE_JSON)
        name = data.get("name", "")
        import re
        assert re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name), (
            f"marketplace.json 'name' must be kebab-case; got: {name!r}"
        )

    def test_has_owner_with_name(self) -> None:
        data = _load_json(MARKETPLACE_JSON)
        assert "owner" in data, "marketplace.json must have an 'owner' field"
        owner = data["owner"]
        assert isinstance(owner, dict), (
            f"marketplace.json 'owner' must be an object; got: {type(owner).__name__}"
        )
        assert owner.get("name"), (
            "marketplace.json 'owner.name' must be a non-empty string"
        )

    def test_has_plugins_array(self) -> None:
        data = _load_json(MARKETPLACE_JSON)
        assert "plugins" in data, "marketplace.json must have a 'plugins' array"
        plugins = data["plugins"]
        assert isinstance(plugins, list) and len(plugins) >= 1, (
            "marketplace.json 'plugins' must be a non-empty array"
        )

    def test_uacp_plugin_entry_present(self) -> None:
        data = _load_json(MARKETPLACE_JSON)
        plugins = data.get("plugins", [])
        names = [p.get("name") for p in plugins]
        assert "uacp" in names, (
            f"marketplace.json 'plugins' must contain an entry with name='uacp'; "
            f"found: {names}"
        )

    def test_uacp_plugin_has_source(self) -> None:
        data = _load_json(MARKETPLACE_JSON)
        entry = next(p for p in data["plugins"] if p.get("name") == "uacp")
        assert "source" in entry and entry["source"], (
            "uacp plugin entry in marketplace.json must have a non-empty 'source' field"
        )

    def test_uacp_plugin_source_resolves_to_plugin_dir(self) -> None:
        """The source value must point to a directory containing plugin.json."""
        data = _load_json(MARKETPLACE_JSON)
        entry = next(p for p in data["plugins"] if p.get("name") == "uacp")
        source = entry["source"]

        # source is a relative path string (e.g. "./" or "./plugin")
        assert isinstance(source, (str,)), (
            f"uacp 'source' must be a string path; got: {type(source).__name__}"
        )
        plugin_root = (REPO_ROOT / source).resolve()
        assert plugin_root.is_dir(), (
            f"uacp source '{source}' resolves to {plugin_root}, which is not a directory"
        )
        resolved_plugin_json = plugin_root / ".claude-plugin" / "plugin.json"
        assert resolved_plugin_json.is_file(), (
            f"uacp source '{source}' → {plugin_root} does not contain "
            f".claude-plugin/plugin.json"
        )

    def test_author_is_not_string(self) -> None:
        """Regression guard: CC bug — author must be an object not a string."""
        data = _load_json(MARKETPLACE_JSON)
        _assert_not_string_author(data, "marketplace.json top-level")
        for entry in data.get("plugins", []):
            _assert_not_string_author(entry, f"marketplace.json plugin '{entry.get('name')}'")


class TestPluginJson:
    """Validate .claude-plugin/plugin.json structure."""

    def test_file_exists(self) -> None:
        assert PLUGIN_JSON.is_file(), (
            f"{PLUGIN_JSON.relative_to(REPO_ROOT)} missing"
        )

    def test_parses_as_json(self) -> None:
        _load_json(PLUGIN_JSON)

    def test_has_name(self) -> None:
        data = _load_json(PLUGIN_JSON)
        assert "name" in data and data["name"], (
            "plugin.json must have a non-empty 'name' field"
        )

    def test_hooks_pointer_resolves(self) -> None:
        """plugin.json 'hooks' pointer (./hooks/hooks.json) must exist."""
        data = _load_json(PLUGIN_JSON)
        if "hooks" not in data:
            return  # optional field
        hooks_rel = data["hooks"]
        hooks_path = (REPO_ROOT / hooks_rel).resolve()
        assert hooks_path.is_file(), (
            f"plugin.json 'hooks' → '{hooks_rel}' resolves to {hooks_path}, "
            f"which does not exist"
        )

    def test_author_is_not_string(self) -> None:
        data = _load_json(PLUGIN_JSON)
        _assert_not_string_author(data, "plugin.json")

    def test_has_author_object_with_name(self) -> None:
        """plugin.json must carry author attribution (object with a non-empty name).

        `claude plugin validate --strict` warns (and, under --strict, fails) when
        plugin.json has no author. Attribution must be present, not merely well-typed.
        """
        data = _load_json(PLUGIN_JSON)
        author = data.get("author")
        assert isinstance(author, dict), (
            "plugin.json must declare an 'author' object (e.g. {\"name\": \"mikeng-io\"}); "
            f"got: {author!r}"
        )
        assert author.get("name"), "plugin.json 'author.name' must be a non-empty string"


class TestMcpServerShipsInManifest:
    """The uacp MCP server must be declared in the COMMITTED plugin manifest.

    Regression guard for the gap that the rest of this suite missed: the server
    was historically wired ONLY through the gitignored operator-local .mcp.json,
    so a marketplace install produced hooks+skills but no governed-tool MCP server.
    The committed manifest (plugin.json) must declare it so it ships.
    """

    def _plugin_mcp_servers(self) -> dict:
        """Return the mcpServers mapping from plugin.json, resolving the
        string-pointer form (\"mcpServers\": \"./.mcp.json\") if used."""
        data = _load_json(PLUGIN_JSON)
        servers = data.get("mcpServers")
        assert servers is not None, (
            "plugin.json must declare 'mcpServers' so the governed-tool MCP server "
            "ships with the plugin (it must NOT rely on the gitignored .mcp.json)"
        )
        if isinstance(servers, str):
            # pointer form — resolve the referenced file at plugin root
            pointer = (REPO_ROOT / servers).resolve()
            assert pointer.is_file(), (
                f"plugin.json 'mcpServers' points to '{servers}', missing at {pointer}"
            )
            servers = _load_json(pointer).get("mcpServers", {})
        assert isinstance(servers, dict), "resolved 'mcpServers' must be an object"
        return servers

    def test_declares_uacp_server(self) -> None:
        servers = self._plugin_mcp_servers()
        assert "uacp" in servers, (
            f"plugin manifest must declare an 'uacp' MCP server; found: {list(servers)}"
        )

    def test_uacp_server_script_resolves_on_disk(self) -> None:
        """Every .py token in the uacp server command/args must exist on disk
        (resolved against the plugin root via ${CLAUDE_PLUGIN_ROOT})."""
        entry = self._plugin_mcp_servers()["uacp"]
        tokens = [entry.get("command", ""), *entry.get("args", [])]
        py_tokens = [t for t in tokens if isinstance(t, str) and t.endswith(".py")]
        assert py_tokens, (
            "uacp MCP server command/args must reference a .py server script"
        )
        for tok in py_tokens:
            rel = tok.replace("${CLAUDE_PLUGIN_ROOT}/", "").replace("${CLAUDE_PLUGIN_ROOT}", "")
            script = REPO_ROOT / rel
            assert script.is_file(), (
                f"uacp MCP server references '{rel}', not found at {script}"
            )

    def test_with_deps_cover_kernel_runtime_deps(self) -> None:
        """The server's handlers import the full UACP kernel transitively
        (tool_specs → engines → state_machine → yaml/pydantic/jsonschema), so the
        manifest's `uv run --with <pkg>` set MUST cover pyproject's core
        [project.dependencies] PLUS the `mcp` extra. Otherwise the server boots
        into a ModuleNotFoundError on a fresh install. This guards against the
        manifest drifting behind pyproject when a core dependency is added.
        """
        entry = self._plugin_mcp_servers()["uacp"]
        assert entry.get("command") == "uv", (
            "uacp server is provisioned via `uv run --with ...`; this drift guard "
            f"assumes that command. Got command={entry.get('command')!r}"
        )
        args = entry.get("args", [])
        # Collect every token that immediately follows a `--with` flag, normalized
        # with the SAME parser as the pyproject side (so they cannot disagree).
        with_pkgs = {
            _bare_req_name(args[i + 1])
            for i, tok in enumerate(args[:-1])
            if tok == "--with" and isinstance(args[i + 1], str)
        }

        required = _kernel_runtime_dep_names()
        missing = required - with_pkgs
        assert not missing, (
            f"plugin.json uacp server `--with` set is missing {sorted(missing)}; "
            f"the server imports the full kernel and will ModuleNotFoundError on a "
            f"fresh install. Declared --with: {sorted(with_pkgs)}; "
            f"required (pyproject core deps + 'mcp'): {sorted(required)}"
        )


# ---------------------------------------------------------------------------
# Layer (b+): official validator — must pass --strict (no warnings)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    shutil.which("claude") is None,
    reason="claude CLI not present — skipping official validator check",
)
class TestClaudePluginValidateStrict:
    """`claude plugin validate <repo> --strict` must exit 0 (zero warnings)."""

    def test_strict_validate_passes(self) -> None:
        result = subprocess.run(
            ["claude", "plugin", "validate", str(REPO_ROOT), "--strict"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, (
            f"`claude plugin validate --strict` failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# Layer (c): real server boot — provision via the EXACT manifest command and
# speak MCP to it. This is the only test that validates the manifest against
# actual runtime behaviour (not against pyproject), so it catches a --with set
# that is internally consistent yet insufficient to import the server.
# ---------------------------------------------------------------------------


def _mcp_client_importable() -> bool:
    import importlib.util

    try:
        return importlib.util.find_spec("mcp.client.stdio") is not None
    except Exception:
        return False


@pytest.mark.skipif(
    shutil.which("uv") is None,
    reason="uv not on PATH — cannot provision/boot the MCP server",
)
@pytest.mark.skipif(
    not _mcp_client_importable(),
    reason="mcp client SDK not importable in the test env — cannot speak MCP",
)
class TestMcpServerBoots:
    """Launch the uacp server via the manifest's own command and list its tools."""

    def _manifest_command(self) -> tuple[str, list[str]]:
        """Return (command, args) from plugin.json with ${CLAUDE_PLUGIN_ROOT}
        resolved to the repo root — i.e. exactly what Claude Code would run."""
        data = _load_json(PLUGIN_JSON)
        entry = data["mcpServers"]["uacp"]
        command = entry["command"]
        args = [
            a.replace("${CLAUDE_PLUGIN_ROOT}", str(REPO_ROOT)) for a in entry["args"]
        ]
        return command, args

    def _expected_tool_names(self) -> set[str]:
        """Tool names from the source registry, imported in-process — the server
        (a subprocess off the same tree) must expose exactly these."""
        import sys

        for sub in ("uacp-core", "uacp-state"):
            p = str(REPO_ROOT / "skills" / sub / "scripts")
            if p not in sys.path:
                sys.path.insert(0, p)
        from tool_specs import tool_specs  # type: ignore

        return {spec.name for spec in tool_specs()}

    def test_boots_and_exposes_the_full_governed_tool_set(self) -> None:
        import asyncio

        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        command, args = self._manifest_command()

        async def _list_tool_names() -> set[str]:
            params = StdioServerParameters(command=command, args=args)
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    resp = await session.list_tools()
                    return {t.name for t in resp.tools}

        async def _run() -> set[str]:
            # Generous timeout: first launch may provision deps over the network.
            return await asyncio.wait_for(_list_tool_names(), timeout=180)

        served = asyncio.run(_run())
        expected = self._expected_tool_names()
        # Anti-vacuity floor: a collapsed/empty registry would make served==expected
        # trivially true. The governed-tool set must not silently shrink below 12.
        assert len(expected) >= 12, (
            f"source registry collapsed to {len(expected)} tools (expected >= 12); "
            "served==expected would be vacuously true"
        )
        assert served == expected, (
            "MCP server (booted via the plugin manifest command) does not expose the "
            f"source registry's tool set.\n  served:   {sorted(served)}\n"
            f"  expected: {sorted(expected)}\n  missing:  {sorted(expected - served)}\n"
            f"  extra:    {sorted(served - expected)}"
        )


class TestBundledComponents:
    """Assert every file referenced by the manifests actually exists."""

    def test_skills_directory_exists(self) -> None:
        assert SKILLS_DIR.is_dir(), "skills/ directory missing"

    def test_minimum_skill_count(self) -> None:
        """At least 16 skills must exist (guards against glob returning empty)."""
        skill_dirs = [p for p in SKILLS_DIR.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()]
        assert len(skill_dirs) >= 16, (
            f"Expected at least 16 skill directories; found {len(skill_dirs)}"
        )

    def test_all_skill_md_files_exist_and_parse(self) -> None:
        """Every skills/<n>/SKILL.md must exist and be readable UTF-8 text."""
        skill_mds = list(SKILLS_DIR.glob("*/SKILL.md"))
        assert len(skill_mds) >= 16, (
            f"Expected at least 16 SKILL.md files; found {len(skill_mds)}"
        )
        for skill_md in skill_mds:
            text = skill_md.read_text(encoding="utf-8")
            assert len(text) > 0, f"{skill_md.relative_to(REPO_ROOT)} is empty"

    @pytest.mark.skipif(
        not (REPO_ROOT / ".mcp.json").is_file(),
        reason=".mcp.json is gitignored operator-local config (af93cbe), absent in CI; "
        "the committed server file is covered by test_mcp_manifests.test_server_file_exists",
    )
    def test_mcp_json_server_wiring_when_present(self) -> None:
        """When the operator-local .mcp.json is present, its 'uacp' server entry must
        point at a server script that exists on disk. (.mcp.json itself is gitignored
        per af93cbe, so this is verified only when present — see the skipif reason.)"""
        mcp_json_path = REPO_ROOT / ".mcp.json"
        data = _load_json(mcp_json_path)

        # Verify the uacp MCP server entry points to an existing script.
        servers = data.get("mcpServers", {})
        assert "uacp" in servers, ".mcp.json must declare an 'uacp' MCP server entry"
        args = servers["uacp"].get("args", [])
        # The script path uses ${CLAUDE_PLUGIN_ROOT}/... — resolve against REPO_ROOT
        for arg in args:
            if arg.endswith(".py"):
                # strip the ${CLAUDE_PLUGIN_ROOT}/ prefix for filesystem check
                rel = arg.replace("${CLAUDE_PLUGIN_ROOT}/", "").replace("${CLAUDE_PLUGIN_ROOT}", "")
                script_path = REPO_ROOT / rel
                assert script_path.is_file(), (
                    f".mcp.json server script '{rel}' not found at {script_path}"
                )

    def test_hooks_json_exists_and_hook_script_present(self) -> None:
        """'hooks/hooks.json' must exist and each hook command script must be on disk."""
        hooks_json_path = REPO_ROOT / "hooks" / "hooks.json"
        assert hooks_json_path.is_file(), "hooks/hooks.json missing"
        data = _load_json(hooks_json_path)

        hooks_section = data.get("hooks", {})
        for event_name, matchers in hooks_section.items():
            for matcher_entry in matchers:
                for hook in matcher_entry.get("hooks", []):
                    cmd = hook.get("command", "")
                    # Extract the script path (first .py token in the command)
                    for token in cmd.split():
                        if token.endswith(".py"):
                            rel = (
                                token.strip('"')
                                .replace("${CLAUDE_PLUGIN_ROOT}/", "")
                                .replace("${CLAUDE_PLUGIN_ROOT}", "")
                            )
                            script_path = REPO_ROOT / rel
                            assert script_path.is_file(), (
                                f"hooks/hooks.json references '{rel}' in {event_name} hook, "
                                f"but the script was not found at {script_path}"
                            )


# ---------------------------------------------------------------------------
# Layer (b): real loader check (gated by claude CLI presence)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    shutil.which("claude") is None,
    reason="claude CLI not present — skipping real loader check",
)
class TestClaudeCliValidation:
    """Use the actual claude CLI to verify the plugin is install-shaped.

    Both the marketplace-add and plugin-install steps must exit 0.
    We clean up after ourselves (uninstall + remove marketplace) regardless of
    outcome so the test is idempotent on a box that already has claude installed.
    """

    _MKTPLACE_NAME = "uacp-smoke-test"
    _TIMEOUT = 30  # seconds — generous for a local path lookup

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["claude", *args],
            capture_output=True,
            text=True,
            timeout=self._TIMEOUT,
        )

    def _cleanup(self) -> None:
        """Best-effort cleanup — never let cleanup failures mask the real result."""
        try:
            self._run("plugin", "uninstall", "uacp")
        except Exception:
            pass
        try:
            self._run("plugin", "marketplace", "remove", self._MKTPLACE_NAME)
        except Exception:
            pass

    def test_marketplace_add_succeeds(self) -> None:
        """claude plugin marketplace add <path> must exit 0."""
        # Clean up any stale state from a previous partial run.
        self._cleanup()
        result = self._run(
            "plugin", "marketplace", "add", str(REPO_ROOT),
            "--name", self._MKTPLACE_NAME,
        )
        try:
            # Some versions don't support --name; fall back without it.
            if result.returncode != 0 and "--name" in (result.stderr or ""):
                result = self._run("plugin", "marketplace", "add", str(REPO_ROOT))
            assert result.returncode == 0, (
                f"`claude plugin marketplace add` failed (exit {result.returncode}):\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        finally:
            # Clean up marketplace entry regardless of pass/fail.
            try:
                self._run("plugin", "marketplace", "remove", self._MKTPLACE_NAME)
            except Exception:
                try:
                    self._run("plugin", "marketplace", "remove", "uacp")
                except Exception:
                    pass

    def test_plugin_install_succeeds(self) -> None:
        """claude plugin install uacp@<marketplace> must exit 0."""
        # Register marketplace fresh for this test.
        add = self._run("plugin", "marketplace", "add", str(REPO_ROOT))
        mktplace_name = "uacp"  # the name declared in marketplace.json
        if add.returncode != 0:
            pytest.skip(f"Could not add marketplace (exit {add.returncode}): {add.stderr}")

        try:
            result = self._run("plugin", "install", f"uacp@{mktplace_name}")
            assert result.returncode == 0, (
                f"`claude plugin install uacp@{mktplace_name}` failed "
                f"(exit {result.returncode}):\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        finally:
            self._cleanup()
