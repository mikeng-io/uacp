"""#119: the governed uacp_corpus_write tool exposes RESOLVE lesson/knowledge
extraction on the MCP tool surface, so a tool-surface-only agent no longer has to
reach into engines.oracle.corpus_writer directly.

Covers BOTH halves of the "registering != governing" lesson (Codex #69 P1):
  * the handler round-trips an OKF doc to the corpus, AND
  * Guardian actually ADMITS the tool in RESOLVE (classification + category
    membership + self-attesting + stage allowlist), and OMITS it from a
    disallowed phase — the wiring, not just the handler.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parents[3] / "skills" / "uacp-core" / "scripts"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from core import Guardian, GuardianPolicy, make_event  # noqa: E402
from engines.domain.corpus import KnowledgeItem, Lesson  # noqa: E402
from engines.domain.phase_transitions import stages_default  # noqa: E402
from governed_handlers import _handle_uacp_corpus_write  # noqa: E402
from tool_specs import tool_specs  # noqa: E402

TOOL = "uacp_corpus_write"


def _call(root: Path, kind: str, okf: str, **extra) -> dict:
    args = {
        "kind": kind,
        "okf": okf,
        "authority_artifact": "resolutions/uacp-test-001-lessons.yaml",
        "workspace": str(root),
        "uacp_run_id": "uacp-test-001",
        "uacp_phase": "resolve",
        "policy_version": "0.1",
        "declared_side_effects": "write corpus doc",
    }
    args.update(extra)
    return json.loads(_handle_uacp_corpus_write(args))


# --------------------------------------------------------------- registry parity
def test_corpus_write_is_a_registered_write_tool():
    spec = next((s for s in tool_specs() if s.name == TOOL), None)
    assert spec is not None, f"{TOOL} must be registered in tool_specs()"
    assert spec.read_only is False, f"{TOOL} is a writer, not read-only"


# ------------------------------------------------- registering != governing (wiring)
def test_corpus_write_is_classified_artifact_uacp(temp_uacp_root: Path):
    policy = GuardianPolicy.load(str(temp_uacp_root))
    assert policy.tool_classification.get(TOOL) == "artifact.uacp", (
        f"{TOOL} must be classified artifact.uacp or Layer A treats it as an "
        f"ungoverned mutator; got {policy.tool_classification.get(TOOL)!r}"
    )


def test_corpus_write_is_allowed_tool_for_its_category(temp_uacp_root: Path):
    policy = GuardianPolicy.load(str(temp_uacp_root))
    assert policy.is_allowed_tool_for_category("artifact.uacp", TOOL), (
        f"{TOOL} must be an allowed_tool for artifact.uacp or Layer A blocks it"
    )


def test_corpus_write_is_self_attesting(temp_uacp_root: Path):
    policy = GuardianPolicy.load(str(temp_uacp_root))
    assert TOOL in policy.self_attesting_tools, (
        f"{TOOL} handler enforces its own containment (delegates to the artifact "
        f"writer), so it must be self-attesting"
    )


def test_corpus_write_admitted_in_resolve_omitted_elsewhere():
    stages = stages_default()
    assert TOOL in stages["resolve"]["allowed_tools"], (
        f"{TOOL} must be allowed in RESOLVE (lesson extraction happens there)"
    )
    # Not a triage/plan tool — its absence there proves the allowlist is scoped,
    # not a blanket grant.
    for phase in ("triage", "plan", "execute"):
        assert TOOL not in stages[phase]["allowed_tools"], (
            f"{TOOL} must NOT be allowed in {phase} — corpus writeback is a RESOLVE op"
        )


def test_guardian_evaluate_admits_in_resolve_blocks_in_execute(temp_uacp_root: Path):
    """The REAL 'registering != governing' proof — drive Guardian.evaluate (not just the
    config dicts): the tool is ADMITTED in RESOLVE and BLOCKED in a non-resolve phase
    through Guardian's actual Layer-A/B decision (council #147 review)."""
    guardian = Guardian(
        GuardianPolicy.load(str(temp_uacp_root)), phase_config={"stages": stages_default()}
    )
    base = {
        "uacp_run_id": "uacp-test-001",
        "workspace": str(temp_uacp_root),
        "policy_version": "0.1",
        "authority_artifact": "resolutions/uacp-test-001-lessons.yaml",
        "reason": "corpus test",
        "declared_side_effects": [],
        "kind": "lesson",
        "okf": "---\nid: x\n---\nbody",
    }
    admitted = guardian.evaluate(
        make_event(
            tool_name=TOOL, args={**base, "uacp_phase": "resolve"}, filesystem_guard_verified=True
        )
    )
    assert admitted.decision != "block", admitted
    assert admitted.category == "artifact.uacp", admitted
    blocked = guardian.evaluate(
        make_event(
            tool_name=TOOL, args={**base, "uacp_phase": "execute"}, filesystem_guard_verified=True
        )
    )
    assert blocked.decision == "block", blocked


# --------------------------------------------------------------- handler round-trip
def test_persist_lesson_via_tool_lands_in_corpus(temp_uacp_root: Path):
    okf = Lesson(
        id="use-governed-corpus-tool",
        title="Use the governed corpus tool",
        project="uacp",
        domains=["lifecycle"],
        body="A tool-surface-only agent persists lessons via uacp_corpus_write.",
    ).to_okf()
    out = _call(temp_uacp_root, "lesson", okf)
    assert out.get("ok") is True, out
    dst = temp_uacp_root / ".uacp" / "lessons" / "use-governed-corpus-tool.md"
    assert dst.exists(), f"lesson not persisted to {dst}"
    # Round-trips: the persisted doc parses back to the same id.
    assert Lesson.from_okf(dst.read_text()).id == "use-governed-corpus-tool"


def test_persist_knowledge_via_tool_lands_in_corpus(temp_uacp_root: Path):
    okf = KnowledgeItem(
        id="corpus-write-pattern",
        title="Corpus write pattern",
        type="pattern",
        body="Author OKF, persist via the governed tool.",
    ).to_okf()
    out = _call(temp_uacp_root, "knowledge", okf)
    assert out.get("ok") is True, out
    assert (temp_uacp_root / ".uacp" / "knowledge" / "corpus-write-pattern.md").exists()


# --------------------------------------------------------------- validation / errors
def test_corpus_write_rejects_bad_kind(temp_uacp_root: Path):
    out = _call(temp_uacp_root, "gossip", "---\nid: x\n---\nbody")
    assert "error" in out and "kind" in out["error"], out


def test_corpus_write_rejects_empty_okf(temp_uacp_root: Path):
    out = _call(temp_uacp_root, "lesson", "   ")
    assert "error" in out and "okf" in out["error"], out


def test_corpus_write_rejects_okf_without_id(temp_uacp_root: Path):
    # OKF with no 'id' in frontmatter -> Lesson.from_okf raises -> handler errors.
    out = _call(temp_uacp_root, "lesson", "---\ntitle: no id here\n---\nbody")
    assert "error" in out, out


def test_corpus_write_accepts_declared_authority_alias(temp_uacp_root: Path):
    """The governed-writer contract accepts either authority_artifact OR the documented
    declared_authority alias — uacp_corpus_write must too (Codex #147 P2), else a valid
    alias call that Guardian already admitted is wrongly rejected by the handler."""
    okf = Lesson(id="via-alias", title="t", project="uacp").to_okf()
    args = {
        "kind": "lesson",
        "okf": okf,
        "declared_authority": "resolutions/uacp-test-001-lessons.yaml",  # alias, not authority_artifact
        "workspace": str(temp_uacp_root),
        "uacp_run_id": "uacp-test-001",
        "uacp_phase": "resolve",
        "policy_version": "0.1",
        "declared_side_effects": "write corpus doc",
    }
    out = json.loads(_handle_uacp_corpus_write(args))
    assert out.get("ok") is True, out
    assert (temp_uacp_root / ".uacp" / "lessons" / "via-alias.md").exists()


def test_corpus_write_rejects_id_path_traversal(temp_uacp_root: Path):
    """The corpus id becomes the '{id}.md' path component, so a traversal id must be
    refused — the tool can never escape lessons/ / knowledge/ (gemini #147 review)."""
    okf = (
        Lesson(id="x", title="t", project="uacp")
        .to_okf()
        .replace("id: x", "id: ../../../../tmp/uacp-escape")
    )
    out = _call(temp_uacp_root, "lesson", okf)
    assert "error" in out and "invalid corpus id" in out["error"], out
    assert not Path("/tmp/uacp-escape.md").exists(), "corpus write escaped the corpus root!"
