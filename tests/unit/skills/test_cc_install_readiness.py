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

    def test_mcp_json_exists_and_server_file_present(self) -> None:
        """'.mcp.json' must exist and its server script must be on disk."""
        mcp_json_path = REPO_ROOT / ".mcp.json"
        assert mcp_json_path.is_file(), ".mcp.json missing from repo root"
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
