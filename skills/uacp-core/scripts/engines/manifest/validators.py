"""Manifest-document validators carved from the Heartgate hub (Phase C / node 34 §3).

These four gate validators enforce the per-phase MANIFEST DOCUMENT contracts that
Heartgate runs at transition time:

* ``validate_intent_doc`` — TRIAGE->PROPOSE intent.md required sections (markdown);
* ``validate_scope_artifact`` — PLAN->EXECUTE scope.yaml fields + write-path reachability;
* ``validate_evidence_dispositions`` — VERIFY->RESOLVE paired files + pending ownership (markdown);
* ``validate_lessons_artifact`` — VERIFY->RESOLVE lessons.yaml shape.

Carved out of ``engines/heartgate/heartgate.py`` (design/graph-engine nodes 30/34) as
free functions taking the gate instance ``hg`` (the A3 extraction pattern): the bodies
are behaviour-identical (only ``self.`` -> ``hg.`` and the three dedicated helpers, which
move here too, become module-local calls). The hub keeps thin delegating methods so the
orchestrator call sites are unchanged.

Read sites still use ``path.read_text`` / ``yaml.safe_load`` here; rewiring onto the io
``Loaded[T]`` contract (incl. a ``load_text_under_root`` for the markdown kinds) is the
next increment (C3b — node 34 §3 / Codex PR#3 round-3). ``_is_safe_run_id`` is imported
from the Heartgate validators leaf pending its promotion to ``engines.domain``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from config import get_config
from engines.heartgate.validators.helpers import _is_safe_run_id

if TYPE_CHECKING:
    from engines.heartgate import Heartgate

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is a hard dependency in practice
    yaml = None  # type: ignore[assignment]


def validate_intent_doc(hg: Heartgate, artifact: Mapping[str, Any], blockers: list[str]) -> None:
    """Phase 2.3: TRIAGE->PROPOSE requires proposals/{run_id}-intent.md
    with the four required sections.
    """
    schema = hg.artifact_schemas.get("intent") or {}
    required_transition = str(schema.get("required_for_transition") or "")
    if not required_transition:
        return
    from_phase = str(artifact.get("from_phase") or "")
    to_phase = str(artifact.get("to_phase") or "")
    if f"{from_phase}->{to_phase}" != required_transition:
        return
    run_id = str(artifact.get("run_id") or "")
    if not _is_safe_run_id(run_id):
        blockers.append("intent doc: unsafe or missing run_id")
        return
    template = str(schema.get("path_template") or "proposals/{run_id}-intent.md")
    path = hg.governed_root / template.replace("{run_id}", run_id)
    if not path.exists():
        blockers.append(f"intent doc missing: {path.relative_to(hg.governed_root)}")
        return
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        blockers.append(f"intent doc unreadable: {type(exc).__name__}")
        return
    # Phase 3 hardening (pc_p2_t5 + SKEP-004): anchored per-line regex;
    # skip both ``` and ~~~ CommonMark fences AND any leading YAML
    # frontmatter delimited by `---` at the top of the file.
    required_sections = list(schema.get("required_sections") or [])
    import re as _re

    lines = text.splitlines()
    # Detect leading YAML frontmatter and skip it entirely.
    skip_until = 0
    if lines and lines[0].strip() == "---":
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                skip_until = idx + 1
                break
    in_fence = False
    present: set[str] = set()
    for ln_no, raw_line in enumerate(lines):
        if ln_no < skip_until:
            continue
        line = raw_line.rstrip()
        stripped = line.lstrip()
        # CommonMark recognizes both ``` and ~~~ as code fences.
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _re.match(r"^(#{1,2})\s+(.+?)\s*$", line)
        if not m:
            continue
        raw_header = m.group(2).strip()
        # Accept "Header" and "Header: free text" (split on first colon).
        header_main = raw_header.split(":", 1)[0].strip()
        for section in required_sections:
            if raw_header == section or header_main == section:
                present.add(section)
    for section in required_sections:
        if section not in present:
            blockers.append(f"intent doc missing required section: '{section}'")


def validate_scope_artifact(
    hg: Heartgate, artifact: Mapping[str, Any], blockers: list[str], warnings: list[str]
) -> None:
    """Phase 2.1: PLAN->EXECUTE requires plans/{run_id}-scope.yaml.
    Validates required fields, cross-checks write_paths against Layer B
    allowed_tools (pc_p1_gov_2).
    """
    schema = hg.artifact_schemas.get("scope") or {}
    required_transition = str(schema.get("required_for_transition") or "")
    if not required_transition:
        return
    from_phase = str(artifact.get("from_phase") or "")
    to_phase = str(artifact.get("to_phase") or "")
    if f"{from_phase}->{to_phase}" != required_transition:
        return
    run_id = str(artifact.get("run_id") or "")
    if not _is_safe_run_id(run_id):
        blockers.append("scope artifact: unsafe or missing run_id")
        return
    template = str(schema.get("path_template") or "plans/{run_id}-scope.yaml")
    path = hg.governed_root / template.replace("{run_id}", run_id)
    if not path.exists():
        blockers.append(f"scope artifact missing: {path.relative_to(hg.governed_root)}")
        return
    if yaml is None:
        blockers.append("scope artifact requires PyYAML to validate")
        return
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        blockers.append(f"scope artifact unparseable: {type(exc).__name__}")
        return
    if not isinstance(data, Mapping):
        blockers.append("scope artifact must be a YAML mapping")
        return
    for field_name in schema.get("required_fields") or []:
        if field_name not in data:
            blockers.append(f"scope artifact missing required field: {field_name}")
    # Cross-check write_paths against EXECUTE Layer B (pc_p1_gov_2).
    write_paths = data.get("write_paths") or []
    if not isinstance(write_paths, list):
        blockers.append("scope.write_paths must be a list")
        return
    # Phase 3 R2 (SKEP-R1-004): empty write_paths is "containment by
    # absence" — both overlap detection and reachability cross-check
    # silently no-op on empty lists, allowing a run to declare no writes,
    # pass governance, then write through governed tools without bound.
    # Require either at least one write path OR an explicit
    # no_writes_intended sentinel that the scope author has acknowledged.
    if len(write_paths) == 0 and not bool(data.get("no_writes_intended")):
        blockers.append(
            "scope.write_paths is empty (write authority cannot be inferred from absence; "
            "either declare at least one path or set 'no_writes_intended: true')"
        )
        return
    execute_stage = hg.stages.get("execute") or {}
    allowed_tools = list((execute_stage or {}).get("allowed_tools") or [])
    tool_path_capabilities = _tool_path_capabilities(hg)
    # SKEP-008 remediation: a positive prefix match is not enough — some
    # handlers refuse sub-paths of an allowed prefix. Honor those refusals
    # here so a scope can't launder unreachable paths.
    # Slice 4a: handler_refusals moved from artifact-schemas.yaml to
    # config/uacp.toml [scope.handler_refusals] (operator-tunable knob).
    try:
        cfg_raw = get_config(hg.uacp_root).model_dump()
        handler_refusals = (cfg_raw.get("scope") or {}).get("handler_refusals") or {}
    except Exception:
        handler_refusals = {}
    if not isinstance(handler_refusals, Mapping):
        handler_refusals = {}
    for wp in write_paths:
        wp_str = str(wp)
        reachable = False
        for tool in allowed_tools:
            prefixes = tool_path_capabilities.get(tool) or []
            if not any(wp_str.startswith(pfx) or wp_str == pfx.rstrip("/") for pfx in prefixes):
                continue
            # Apply per-tool refusals (e.g. uacp_state_write refuses state/gate-ledger/).
            refused = handler_refusals.get(tool) or []
            if isinstance(refused, list) and any(
                isinstance(r, str) and r and (wp_str == r.rstrip("/") or wp_str.startswith(r))
                for r in refused
            ):
                continue
            reachable = True
            break
        if not reachable and _self_patch_authorizes_path(data, wp_str, blockers):
            reachable = True
        if not reachable:
            blockers.append(
                f"scope.write_paths cross-check: '{wp_str}' is not reachable "
                "by any execute-phase allowed_tool"
            )


def _self_patch_authorizes_path(
    scope: Mapping[str, Any], write_path: str, blockers: list[str]
) -> bool:
    """Narrow bootstrap escape hatch for UACP self-repair paths.

    This does not make terminal/patch a general governed writer. It only lets
    Heartgate accept specific UACP self-patch paths when the scope carries an
    explicit authority block with owner, rollback, and verification duties.
    """
    auth = scope.get("self_patch_write_authority")
    if not isinstance(auth, Mapping) or not bool(auth.get("enabled")):
        return False
    for field_name in (
        "reason",
        "authority_artifact",
        "owner",
        "rollback_path",
        "verification_obligations",
    ):
        if auth.get(field_name) in (None, "", []):
            blockers.append(f"self_patch_write_authority missing {field_name}")
            return False
    obligations = auth.get("verification_obligations")
    if not isinstance(obligations, list) or not all(
        isinstance(item, str) and item.strip() for item in obligations
    ):
        blockers.append(
            "self_patch_write_authority.verification_obligations must be a "
            "non-empty list of strings"
        )
        return False
    allowed = auth.get("allowed_prefixes") or [
        "skills/devops/uacp/",
        "scripts/",
        "runtime-adapters/",
    ]
    if not isinstance(allowed, list):
        blockers.append("self_patch_write_authority.allowed_prefixes must be a list")
        return False
    safe_prefixes = {"skills/devops/uacp/", "scripts/", "runtime-adapters/"}
    cleaned = [
        str(prefix) for prefix in allowed if isinstance(prefix, str) and prefix in safe_prefixes
    ]
    if not cleaned:
        blockers.append("self_patch_write_authority has no safe allowed_prefixes")
        return False
    return any(write_path.startswith(prefix) for prefix in cleaned)


def _tool_path_capabilities(hg: Heartgate) -> dict[str, list[str]]:
    """Path prefixes each governed writer tool can reach.

    Slice 4a: the canonical source is now ``config/uacp.toml [scope.tool_path_capabilities]``
    (operator-tunable). Previously read from
    ``config/artifact-schemas.yaml#cross_checks.scope_write_paths_vs_layer_b.tool_path_capabilities``
    via ``self.artifact_schemas``. Schemas are codified in engines.domain; the
    operator knobs moved to uacp.toml so project operators can tune them without
    touching kernel code.

    Shell/exec surfaces are deliberately absent — they target the workspace,
    not UACP_ROOT, and do not satisfy UACP-rooted scope.write_paths (F1).

    Phase 3 hardening (pc_p2_n1): drop prefixes that are empty or the
    literal "*" so a future config-author mistake cannot accidentally
    wildcard-match every write_path.

    Fail-closed default: if the config section is missing or malformed,
    return an empty mapping so every write_path is unreachable.
    """
    try:
        cfg_raw = get_config(hg.uacp_root).model_dump()
        caps = (cfg_raw.get("scope") or {}).get("tool_path_capabilities") or {}
    except Exception:
        caps = {}
    if not isinstance(caps, Mapping):
        return {}
    # SKEP-007 remediation: schema metadata keys (description, purpose, notes,
    # documentation) must never be loaded as writer tools. Sibling fields are
    # legitimate metadata, not policy.
    metadata_keys = {"description", "purpose", "notes", "documentation"}
    # SKEP-003 / TECH-004 remediation: reject footgun prefixes that would
    # collapse path-segment boundaries (bare wildcards, root, dot-relative).
    forbidden_prefixes = {"", "*", "**", "/", ".", "..", "./", "../"}
    result: dict[str, list[str]] = {}
    for tool, prefixes in caps.items():
        if not isinstance(tool, str) or tool in metadata_keys:
            continue
        if isinstance(prefixes, list):
            cleaned = [
                str(p)
                for p in prefixes
                if isinstance(p, str) and str(p).strip() not in forbidden_prefixes
            ]
        elif isinstance(prefixes, str) and prefixes.strip() not in forbidden_prefixes:
            cleaned = [prefixes]
        else:
            cleaned = []
        if cleaned:
            result[tool] = cleaned
    return result


def validate_evidence_dispositions(
    hg: Heartgate, artifact: Mapping[str, Any], blockers: list[str]
) -> None:
    """Phase 2.2: VERIFY->RESOLVE requires verified-facts + assumptions
    pair files for each required cluster. Pending assumptions without
    owner/next_phase_obligation block.
    """
    schema = hg.artifact_schemas.get("evidence_disposition") or {}
    required_transition = str(schema.get("required_for_transition") or "")
    if not required_transition:
        return
    from_phase = str(artifact.get("from_phase") or "")
    to_phase = str(artifact.get("to_phase") or "")
    if f"{from_phase}->{to_phase}" != required_transition:
        return
    run_id = str(artifact.get("run_id") or "")
    if not _is_safe_run_id(run_id):
        blockers.append("evidence_disposition: unsafe or missing run_id")
        return
    cluster_summary = artifact.get("cluster_summary") or []
    if not isinstance(cluster_summary, list):
        return
    # Phase 3 (pc_p2_t3): empty cluster_summary at VERIFY->RESOLVE is a block.
    # If a run truly has no clusters to verify, it must declare that
    # explicitly elsewhere (handled_findings_chain or accepted_exceptions);
    # silent zero-cluster passage is not acceptable for traceable state.
    handled_chain = artifact.get("handled_findings_chain") or []
    accepted_exc = artifact.get("accepted_exceptions") or []

    # Phase 3 R2 (SKEP-R1-002): escape-hatch presence is not sufficient;
    # entries must be non-empty mappings with the documented shape.
    # Garbage lists ([None, {}, ""]) no longer satisfy the escape hatch.
    def _valid_handled(c: Any) -> bool:
        if not isinstance(c, Mapping):
            return False
        ofid = c.get("original_finding_id") or c.get("finding_id")
        klass = c.get("handling_classification") or c.get("classification")
        return bool(ofid) and bool(klass)

    def _valid_exception(e: Any) -> bool:
        if not isinstance(e, Mapping):
            return False
        return bool(e.get("artifact_path")) and bool(e.get("owner")) and bool(e.get("rationale"))

    handled_valid = isinstance(handled_chain, list) and any(
        _valid_handled(c) for c in handled_chain
    )
    exc_valid = isinstance(accepted_exc, list) and any(_valid_exception(e) for e in accepted_exc)
    has_escape_hatch = handled_valid or exc_valid
    if len(cluster_summary) == 0:
        if not has_escape_hatch:
            blockers.append(
                "evidence_disposition: cluster_summary is empty at VERIFY->RESOLVE "
                "(must declare at least one cluster or non-empty "
                "handled_findings_chain/accepted_exceptions)"
            )
        return
    # Phase 3 R1 (SKEP-006): a run cannot pass VERIFY->RESOLVE by declaring
    # every cluster as not_applicable/deferred. At least one cluster must
    # be in a real verification state, OR an escape hatch must be present.
    non_na_count = 0
    for c in cluster_summary:
        if isinstance(c, Mapping):
            st = str(c.get("state") or "")
            if st and st not in {"not_applicable", "deferred"}:
                non_na_count += 1
    if non_na_count == 0 and not has_escape_hatch:
        blockers.append(
            "evidence_disposition: all clusters are not_applicable/deferred and no "
            "handled_findings_chain or accepted_exceptions declared (silent skip not allowed)"
        )
        return
    paired = schema.get("paired_paths") or {}
    facts_tmpl = str(paired.get("verified_facts") or "")
    assumptions_tmpl = str(paired.get("assumptions") or "")
    if not facts_tmpl or not assumptions_tmpl:
        return
    for cluster in cluster_summary:
        if not isinstance(cluster, Mapping):
            continue
        cluster_id = str(cluster.get("cluster_id") or "")
        state = str(cluster.get("state") or "")
        if not cluster_id or state in {"not_applicable", "deferred"}:
            continue
        # Phase 2 F3 remediation: file existence is insufficient; each file
        # must contain at least the documented table header (Fact / Disposition).
        cross = hg.artifact_schemas.get("cross_checks") or {}
        minc = cross.get("evidence_disposition_minimum_content") or {}
        facts_req = str(minc.get("verified_facts_required_header_substring") or "")
        assump_req = str(minc.get("assumptions_required_header_substring") or "")
        for tmpl, label, required_substring in (
            (facts_tmpl, "verified-facts", facts_req),
            (assumptions_tmpl, "assumptions", assump_req),
        ):
            rel = tmpl.replace("{run_id}", run_id).replace("{cluster}", cluster_id)
            p = hg.governed_root / rel
            if not p.exists():
                blockers.append(
                    f"evidence_disposition: missing {label} for cluster '{cluster_id}': {rel}"
                )
                continue
            if required_substring:
                try:
                    body = p.read_text(encoding="utf-8")
                except Exception:
                    body = ""
                if required_substring not in body:
                    blockers.append(
                        f"evidence_disposition: {label} file for cluster '{cluster_id}' "
                        f"is empty or missing required header '{required_substring}': {rel}"
                    )
        # Inspect assumptions for unowned 'pending' rows.
        assumptions_rel = assumptions_tmpl.replace("{run_id}", run_id).replace(
            "{cluster}", cluster_id
        )
        assumptions_path = hg.governed_root / assumptions_rel
        if assumptions_path.exists():
            try:
                text = assumptions_path.read_text(encoding="utf-8")
                _check_pending_assumptions(text, cluster_id, blockers)
            except Exception:
                pass


def _check_pending_assumptions(text: str, cluster_id: str, blockers: list[str]) -> None:
    """Parse a markdown table looking for `pending` rows with empty owner
    or empty next_phase_obligation. The expected table shape is:
        | Assumption | Disposition | Owner | Next-phase obligation |

    Phase 3 R1 hardening (SKEP-005): header detection uses exact column-name
    match (not substring), with optional leading pipe per CommonMark. After
    the separator row, every non-blank pipe-bearing line is a data row
    regardless of substring content.
    """
    expected_header = ["assumption", "disposition", "owner", "next-phase obligation"]
    # State machine: 0 = before header, 1 = header seen / awaiting separator, 2 = in data rows
    state = 0
    column_count_warned = False
    saw_pipe_row = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        # Allow rows without leading pipe — strip pipes uniformly via split.
        if "|" not in line:
            continue
        saw_pipe_row = True
        # Skip separator-only lines (`---|---|---`).
        if set(line) <= {"|", "-", " ", ":"}:
            if state == 1:
                state = 2
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        cells_lower = [c.lower() for c in cells]
        if state == 0:
            if cells_lower == expected_header:
                state = 1
                continue
            # State remains 0 — but a malformed table that has rows but no
            # recognized header is itself a blocker (covers SKEP-005's "no
            # exact header" silent-skip case AND pc_p2_t4 column-count
            # detection for tables that omit the canonical header).
            if len(cells) != 4 and not column_count_warned:
                blockers.append(
                    f"evidence_disposition: cluster '{cluster_id}' assumptions table "
                    f"has unexpected column count ({len(cells)} != 4)"
                )
                column_count_warned = True
            continue
        # state in {1, 2}: data rows (or a stray separator/header repeat)
        if cells_lower == expected_header:
            # repeated header; ignore
            continue
        if len(cells) != 4:
            if not column_count_warned:
                blockers.append(
                    f"evidence_disposition: cluster '{cluster_id}' assumptions table "
                    f"has unexpected column count ({len(cells)} != 4)"
                )
                column_count_warned = True
            continue
        disposition = cells[1].lower()
        owner = cells[2]
        next_obl = cells[3]
        if disposition == "pending" and (not owner or not next_obl):
            blockers.append(
                f"evidence_disposition: cluster '{cluster_id}' has unowned "
                f"'pending' assumption: {cells[0][:60]}"
            )
    # If the file had table-like rows but no canonical header was ever seen,
    # the table is structurally malformed for the disposition contract.
    if saw_pipe_row and state == 0 and not column_count_warned:
        blockers.append(
            f"evidence_disposition: cluster '{cluster_id}' assumptions table "
            "missing canonical header "
            "'| Assumption | Disposition | Owner | Next-phase obligation |'"
        )


def validate_lessons_artifact(
    hg: Heartgate, artifact: Mapping[str, Any], blockers: list[str]
) -> None:
    """Phase 2.4: VERIFY->RESOLVE requires resolutions/{run_id}-lessons.yaml
    with structured schema (run_id + lessons list).
    """
    schema = hg.artifact_schemas.get("lessons") or {}
    required_transition = str(schema.get("required_for_transition") or "")
    if not required_transition:
        return
    from_phase = str(artifact.get("from_phase") or "")
    to_phase = str(artifact.get("to_phase") or "")
    if f"{from_phase}->{to_phase}" != required_transition:
        return
    run_id = str(artifact.get("run_id") or "")
    if not _is_safe_run_id(run_id):
        blockers.append("lessons: unsafe or missing run_id")
        return
    template = str(schema.get("path_template") or "resolutions/{run_id}-lessons.yaml")
    path = hg.governed_root / template.replace("{run_id}", run_id)
    if not path.exists():
        blockers.append(f"lessons artifact missing: {path.relative_to(hg.governed_root)}")
        return
    if yaml is None:
        return
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        blockers.append(f"lessons artifact unparseable: {type(exc).__name__}")
        return
    if not isinstance(data, Mapping):
        blockers.append("lessons artifact must be a YAML mapping")
        return
    for field_name in schema.get("required_fields") or []:
        if field_name not in data:
            blockers.append(f"lessons artifact missing required field: {field_name}")
    lessons_list = data.get("lessons")
    if lessons_list is not None and not isinstance(lessons_list, list):
        blockers.append("lessons.lessons must be a list")
