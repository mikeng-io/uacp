"""Doc-contract guard for the uacp-debate file-based round-state feature.

Mechanical checks (no behavior is executed — the debate protocol is
agent-executed markdown instructions, not Python):

  1. references/round-state-manifest.md exists.
  2. Its embedded manifest.json example parses as valid JSON and carries the
     required top-level keys.
  3. The manifest `items` example carries BOTH state/maturity AND lineage.
  4. SKILL.md and phase-3-challenge.md reference the manifest contract.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEBATE_DIR = REPO_ROOT / "skills" / "uacp-debate"
MANIFEST_DOC = DEBATE_DIR / "references" / "round-state-manifest.md"

_JSON_BLOCK_RE = re.compile(r"```json\n(.*?)```", re.DOTALL)
_REQUIRED_KEYS = {"schema_version", "review_id", "rounds", "items", "status"}


def _embedded_manifest() -> dict:
    """Return the parsed manifest.json example embedded in the contract doc.

    Picks the first ```json block that has the manifest's required keys, so the
    test is robust to additional illustrative JSON blocks being added later.
    """
    text = MANIFEST_DOC.read_text(encoding="utf-8")
    for block in _JSON_BLOCK_RE.findall(text):
        obj = json.loads(block)  # must be valid JSON
        if isinstance(obj, dict) and _REQUIRED_KEYS <= obj.keys():
            return obj
    raise AssertionError(
        "no embedded JSON block with the manifest required keys "
        f"{sorted(_REQUIRED_KEYS)} found in {MANIFEST_DOC.relative_to(REPO_ROOT)}"
    )


def test_round_state_manifest_doc_exists() -> None:
    assert MANIFEST_DOC.is_file(), (
        f"missing round-state contract: {MANIFEST_DOC.relative_to(REPO_ROOT)}"
    )


def test_embedded_manifest_parses_and_has_required_keys() -> None:
    manifest = _embedded_manifest()
    missing = _REQUIRED_KEYS - manifest.keys()
    assert not missing, f"manifest example missing keys: {sorted(missing)}"
    assert manifest["schema_version"] == "1.0"
    assert isinstance(manifest["rounds"], list) and manifest["rounds"]
    assert isinstance(manifest["items"], dict) and manifest["items"]
    # The doc example uses the schema-placeholder form "running|complete"; accept
    # either a concrete enum value or the pipe-delimited placeholder.
    status_tokens = set(re.split(r"\s*\|\s*", str(manifest["status"])))
    assert status_tokens <= {"running", "complete"} and status_tokens


def test_manifest_items_carry_state_or_maturity_and_lineage() -> None:
    """Every item must carry lineage; findings carry `state`, candidates `maturity`."""
    items = _embedded_manifest()["items"]

    finding_states = {"confirmed", "withdrawn", "disputed", "merged", "discovered"}
    maturities = {"seed", "sketched", "refined", "candidate", "accepted", "rejected", "parked"}

    saw_finding = saw_candidate = False
    for item_id, item in items.items():
        assert "lineage" in item, f"{item_id} missing lineage"
        lineage = item["lineage"]
        assert {"derived_from", "supersedes", "merged_from"} <= lineage.keys(), (
            f"{item_id} lineage missing required sub-keys"
        )
        kind = item.get("kind")
        if kind == "finding":
            saw_finding = True
            assert item.get("state") in finding_states, (
                f"{item_id} finding has invalid/absent state: {item.get('state')}"
            )
        elif kind == "candidate":
            saw_candidate = True
            assert item.get("maturity") in maturities, (
                f"{item_id} candidate has invalid/absent maturity: {item.get('maturity')}"
            )
        else:
            raise AssertionError(f"{item_id} has unexpected kind: {kind}")

    # The example must demonstrate BOTH states and maturity (both vocabularies present).
    assert saw_finding, "manifest example must include at least one finding item"
    assert saw_candidate, "manifest example must include at least one candidate item"


def test_skill_md_references_manifest() -> None:
    text = (DEBATE_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "round-state-manifest.md" in text, (
        "SKILL.md must reference references/round-state-manifest.md"
    )
    assert "manifest.json" in text


def test_phase3_references_manifest() -> None:
    text = (DEBATE_DIR / "references" / "phase-3-challenge.md").read_text(encoding="utf-8")
    assert "round-state-manifest.md" in text, (
        "phase-3-challenge.md must reference references/round-state-manifest.md"
    )
    assert "manifest.json" in text


def test_debate_dir_still_free_of_task_agent_terms() -> None:
    """Don't regress the runtime-neutralization while editing debate docs."""
    banned = ["Task agent", "Task sub-agent", "Task-agent"]
    offenders: list[str] = []
    for md in DEBATE_DIR.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        for term in banned:
            if term in text:
                offenders.append(f"{md.relative_to(REPO_ROOT)}: {term!r}")
    assert not offenders, "non-neutral terms reintroduced:\n" + "\n".join(offenders)
