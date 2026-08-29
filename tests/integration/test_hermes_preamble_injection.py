"""Integration: the Hermes cognition-injection surface.

CMS is enforced two ways — architecturally (Guardian/gates) and in the agent's cognition (the
injected UACP.md preamble). Hermes had only the first: the adapter registered pre/post tool-call
hooks and nothing carried the preamble, so a Hermes session inherited the governed TOOLS but not the
discipline that tells the agent how to use them.

It rides ``pre_llm_call`` rather than ``on_session_start`` because Hermes DECLARES the latter in its
valid-hook list but never fires it — a probe plugin registering seven hooks saw only
``on_session_finalize`` fire in a real session. ``pre_llm_call`` is fired (agent/turn_context.py) and
supplies ``is_first_turn``, giving once-per-session semantics without adapter-side state.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PLUGINS_DIR = _REPO_ROOT / "runtime-adapters" / "hermes" / "plugins"


def _adapter():
    """Import the adapter as the PACKAGE it is — it uses relative imports (`from .kernel import`),
    so a bare file-location load has no package context and fails."""
    if str(_PLUGINS_DIR) not in sys.path:
        sys.path.insert(0, str(_PLUGINS_DIR))
    import uacp_guardian

    return importlib.reload(uacp_guardian)


@pytest.fixture
def uacp_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal governed project: UACP.md at the root, `.uacp/` present, no PRINCIPLE.md."""
    (tmp_path / "UACP.md").write_text(
        "<!-- role: preamble -->\n# UACP\n\nSENTINEL_CMS_PREAMBLE\n", encoding="utf-8"
    )
    (tmp_path / ".uacp").mkdir()
    monkeypatch.setenv("UACP_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_preamble_injected_on_first_turn(uacp_tree: Path) -> None:
    """The first turn of a Hermes session receives the UACP.md preamble in Hermes' own
    contribution shape (`{"context": ...}`), which the host appends to the user message."""
    result = _adapter().on_pre_llm_call(is_first_turn=True)

    assert isinstance(result, dict)
    assert "SENTINEL_CMS_PREAMBLE" in result["context"]
    assert "<!-- role: preamble -->" not in result["context"]  # file-role metadata stripped


def test_not_injected_on_later_turns(uacp_tree: Path) -> None:
    """Once per SESSION, not once per turn — otherwise the preamble is re-sent on every call,
    burning context and duplicating the instruction."""
    assert _adapter().on_pre_llm_call(is_first_turn=False) is None


def test_principle_rides_the_same_surface(uacp_tree: Path) -> None:
    """PRINCIPLE.md reaches Hermes too — the project telos, fenced and labelled untrusted."""
    (uacp_tree / "PRINCIPLE.md").write_text(
        "---\nkind: principle\n---\n# PRINCIPLE\n\nSENTINEL_PROJECT_TELOS\n", encoding="utf-8"
    )

    ctx = _adapter().on_pre_llm_call(is_first_turn=True)["context"]

    assert "SENTINEL_PROJECT_TELOS" in ctx
    assert "untrusted" in ctx.lower()  # framed as project-supplied, not framework authority
    assert ctx.index("SENTINEL_CMS_PREAMBLE") < ctx.index("SENTINEL_PROJECT_TELOS")


def test_bootstrap_nudge_when_governed_project_has_no_principle(uacp_tree: Path) -> None:
    """A governed project without a principle gets the advisory bootstrap prompt, same as Claude."""
    ctx = _adapter().on_pre_llm_call(is_first_turn=True)["context"]

    assert "uacp-bootstrap" in ctx


def test_fail_open_when_uacp_md_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail OPEN: this is a cognition nudge, not a gate. No UACP.md => inject nothing, never raise."""
    monkeypatch.setenv("UACP_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    assert _adapter().on_pre_llm_call(is_first_turn=True) is None


def test_registers_the_hook_hermes_actually_fires(uacp_tree: Path) -> None:
    """`register()` must wire pre_llm_call. Guards the reason this surface was chosen: Hermes
    declares on_session_start but never fires it, so wiring that instead would be dead code."""

    class _Ctx:
        def __init__(self) -> None:
            self.hooks: list[str] = []

        def register_hook(self, name, _cb):
            self.hooks.append(name)

        def register_tool(self, **_kw):
            pass

    ctx = _Ctx()
    _adapter().register(ctx)

    assert "pre_llm_call" in ctx.hooks
    assert "on_session_start" not in ctx.hooks  # declared by Hermes, never fired — would be dead
