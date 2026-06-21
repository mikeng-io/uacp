"""uacp topology — the single source of truth for WHERE control-plane files live.

Every governed artifact KIND maps to (plane, dir, filename pattern, format). The scattered
hardcoded path literals across core.py / state.py / artifact_schema.py / gate_rules.py / the
validators are meant to read from HERE — so a path can't be changed in one place and missed in
five others. (The desync this fixes: `plans/{run_id}-scope.yaml` was hardcoded in 5+ files;
`state/run-registry.yaml` in ~7.)

`dir` is a config `[paths]` segment (default == the key name); `template`/`relpath` return
BASE-RELATIVE paths (under the governed root) using the default segments — what the previously-
hardcoded call sites used. For `[paths]`-override-honoring ABSOLUTE resolution, callers pass
`dir_of(kind)` to `config.get_config(root).resolve(...)` and join the filename.

`fmt` decides the validator: `yaml` -> JSON-Schema (schema.py) + referential checks (uacp-lint);
`markdown` -> required-section / paired-file checks (uacp-lint); `jsonl`/`json` -> own validators.

SCOPE: the **manifest (relation) + state planes only**. The knowledge/lesson CORPUS is
deliberately NOT here — it is owned solely by the Oracle (the single corpus accessor; enforced
by tests/unit/uacp_oracle/test_corpus_boundary.py). Folding the corpus location into this
registry would relax that ownership boundary — a separate, deliberate decision.

References: design/graph-engine/26-nomenclature.md (kinds) + 27-directory-taxonomy.md (layout).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Formats
YAML = "yaml"
MARKDOWN = "markdown"
JSONL = "jsonl"
JSON = "json"

# Planes
RELATION = "relation"
STATE = "state"


@dataclass(frozen=True)
class Entry:
    """One kind's location + format. `dir` is a config [paths] segment; `filename` is the
    pattern beneath it (with `{run_id}` / `{id}` / ... placeholders)."""

    kind: str
    plane: str
    dir: str
    filename: str
    fmt: str

    @property
    def template(self) -> str:
        return f"{self.dir}/{self.filename}"


# The registry — one row per kind. Grounded in config [paths] + the validator path templates
# (scripts/validate_uacp_artifacts.py) + node 27. Order is presentation-only; reverse lookup
# resolves most-specific-first regardless.
_ENTRIES: tuple[Entry, ...] = (
    # --- relation plane: lifecycle documents ---
    # NOTE: "brainstorm" is an artifact root that is NOT yet in config [paths] (only in
    # uacp_artifact_write's allowed_roots) — a [paths] gap worth closing.
    Entry(
        "uacp.brainstorm_scope_package",
        RELATION,
        "brainstorm",
        "{run_id}/07-scope-package.yaml",
        YAML,
    ),
    Entry("uacp.triage", RELATION, "proposals", "{run_id}-triage.yaml", YAML),
    Entry(
        "uacp.proposal_package_selection",
        RELATION,
        "proposals",
        "{run_id}-package-selection.yaml",
        YAML,
    ),
    Entry("uacp.intent", RELATION, "proposals", "{run_id}-intent.md", MARKDOWN),
    Entry(
        "uacp.convergence_budget", RELATION, "proposals", "{run_id}-convergence-budget.yaml", YAML
    ),
    Entry("uacp.plan_package_selection", RELATION, "plans", "{run_id}-plan-selection.yaml", YAML),
    Entry("uacp.scope", RELATION, "plans", "{run_id}-scope.yaml", YAML),
    Entry("uacp.phase_intent_verification_contract", RELATION, "plans", "{run_id}-piv.yaml", YAML),
    Entry(
        "uacp.execution_checkpoint", RELATION, "executions", "{run_id}-checkpoint-{seq}.yaml", YAML
    ),
    Entry("uacp.piv_assessment", RELATION, "verification", "{run_id}-piv-assessment.yaml", YAML),
    Entry(
        "uacp.verification_package",
        RELATION,
        "verification",
        "{run_id}-verify-selection.yaml",
        YAML,
    ),
    Entry(
        "uacp.verify_resolve_readiness",
        RELATION,
        "verification",
        "{run_id}-resolve-readiness.yaml",
        YAML,
    ),
    Entry(
        "uacp.evidence_disposition",
        RELATION,
        "verification",
        "{run_id}-{cluster}-{half}.md",
        MARKDOWN,
    ),
    Entry("uacp.resolve_package", RELATION, "resolutions", "{run_id}-resolve-selection.yaml", YAML),
    Entry("uacp.resolve_closure", RELATION, "resolutions", "{run_id}-closure.yaml", YAML),
    Entry("uacp.lessons", RELATION, "resolutions", "{run_id}-lessons.yaml", YAML),
    # --- state plane ---
    # NOTE: uacp.phase_transition + uacp.council_synthesis are CALLER-PROVIDED paths (passed
    # as a `transition_path` / council arg, under state/runs/ and verification|resolutions/
    # respectively) — NOT fixed templates. They are documented in node 27 but intentionally
    # NOT in this fixed-path registry (there is no fixed path to enforce on a runtime arg).
    Entry("uacp.run_manifest", STATE, "state", "runs/{run_id}.yaml", YAML),
    Entry("uacp.run_registry", STATE, "state", "run-registry.yaml", YAML),
    Entry("uacp.current_state", STATE, "state", "current.yaml", YAML),
    Entry("uacp.gate_ledger", STATE, "state", "gate-ledger/{run_id}.jsonl", JSONL),
    Entry("uacp.escalations", STATE, "state", "escalations/{run_id}.jsonl", JSONL),
    Entry("uacp.artifact_hashes", STATE, "state", "hashes/{run_id}.json", JSON),
)

_BY_KIND: dict[str, Entry] = {e.kind: e for e in _ENTRIES}


def _to_regex(tmpl: str) -> re.Pattern[str]:
    """Compile a path template to a regex (each `{placeholder}` -> one non-slash run)."""
    parts = re.split(r"(\{[a-z_]+\})", tmpl)
    body = "".join(r"[^/]+" if p.startswith("{") else re.escape(p) for p in parts)
    return re.compile(f"^{body}$")


# Reverse-lookup table, most-specific-first (longest template wins) so e.g. a phase_transition
# path is never mis-resolved to the broader run_manifest pattern.
_REGEXES: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (_to_regex(e.template), e.kind)
    for e in sorted(_ENTRIES, key=lambda e: len(e.template), reverse=True)
)


def template(kind: str) -> str | None:
    """Base-relative path template for `kind` (e.g. 'plans/{run_id}-scope.yaml'), or None."""
    e = _BY_KIND.get(kind)
    return e.template if e else None


def relpath(kind: str, **ctx: str) -> str:
    """Resolve `kind`'s base-relative path with placeholders filled (e.g. run_id='r1')."""
    e = _BY_KIND.get(kind)
    if e is None:
        raise KeyError(f"unknown kind '{kind}' — not in the layout registry")
    return e.template.format(**ctx)


def fmt_of(kind: str) -> str | None:
    e = _BY_KIND.get(kind)
    return e.fmt if e else None


def plane_of(kind: str) -> str | None:
    e = _BY_KIND.get(kind)
    return e.plane if e else None


def dir_of(kind: str) -> str | None:
    """The config [paths] segment for `kind` (e.g. 'plans', 'lessons')."""
    e = _BY_KIND.get(kind)
    return e.dir if e else None


def kind_for_relpath(path: str) -> str | None:
    """Reverse lookup: a base-relative path -> its kind (for validate_file). None if no match."""
    for rx, kind in _REGEXES:
        if rx.match(path):
            return kind
    return None


def all_kinds() -> tuple[str, ...]:
    return tuple(e.kind for e in _ENTRIES)
