"""uacp topology bedrock (engines.domain.layout): the single source of truth for WHERE
manifest + state control-plane files live + WHAT format they are. Tests assert the registry
resolves kind->path/format/plane and reverse-resolves path->kind. (The knowledge/lesson
corpus is owned solely by the Oracle, NOT this registry — see test_corpus_boundary.)"""

from __future__ import annotations

from engines.domain import layout


# --- kind -> path template + resolution -------------------------------------------
def test_scope_template_and_relpath():
    assert layout.template("uacp.scope") == "plans/{run_id}-scope.yaml"
    assert layout.relpath("uacp.scope", run_id="r1") == "plans/r1-scope.yaml"


def test_piv_contract_path():
    assert (
        layout.relpath("uacp.phase_intent_verification_contract", run_id="r1")
        == "plans/r1-piv.yaml"
    )


def test_state_singletons_have_no_run_id():
    assert layout.template("uacp.run_registry") == "state/run-registry.yaml"
    assert layout.template("uacp.current_state") == "state/current.yaml"


# --- format: YAML vs Markdown (drives which validator handles it) ------------------
def test_format_yaml_vs_markdown():
    assert layout.fmt_of("uacp.scope") == "yaml"
    assert layout.fmt_of("uacp.intent") == "markdown"
    assert layout.fmt_of("uacp.lessons") == "yaml"


# --- plane -------------------------------------------------------------------------
def test_plane():
    assert layout.plane_of("uacp.scope") == "relation"
    assert layout.plane_of("uacp.run_registry") == "state"


# --- the corpus is Oracle-owned, NOT in this registry (test_corpus_boundary) -------
def test_corpus_is_not_in_layout_oracle_owned():
    # layout covers manifest + state planes only; the knowledge/lesson corpus is owned
    # solely by the Oracle (enforced by tests/unit/uacp_oracle/test_corpus_boundary).
    assert layout.template("lesson") is None
    assert layout.template("knowledge_item") is None


# --- reverse: path -> kind (for validate_file kind-resolution) ---------------------
def test_kind_for_relpath_yaml():
    assert layout.kind_for_relpath("plans/r1-scope.yaml") == "uacp.scope"
    assert layout.kind_for_relpath("resolutions/abc-lessons.yaml") == "uacp.lessons"


def test_kind_for_relpath_markdown():
    assert layout.kind_for_relpath("proposals/r1-intent.md") == "uacp.intent"


def test_kind_for_relpath_unknown_is_none():
    assert layout.kind_for_relpath("something/random.txt") is None


# --- unknown kind ------------------------------------------------------------------
def test_unknown_kind_template_is_none():
    assert layout.template("uacp.not_a_kind") is None


# --- non-vacuity: the registry actually covers the real lifecycle document kinds ---
def test_registry_covers_lifecycle_document_kinds():
    expected = [
        "uacp.brainstorm_scope_package",
        "uacp.triage",
        "uacp.proposal_package_selection",
        "uacp.intent",
        "uacp.convergence_budget",
        "uacp.plan_package_selection",
        "uacp.scope",
        "uacp.phase_intent_verification_contract",
        "uacp.execution_checkpoint",
        "uacp.piv_assessment",
        "uacp.verification_package",
        "uacp.verify_resolve_readiness",
        "uacp.resolve_package",
        "uacp.resolve_closure",
        "uacp.lessons",
    ]
    for k in expected:
        assert layout.template(k) is not None, f"{k} missing from the layout registry"


def test_added_fixed_path_kinds_resolve():
    # The two kinds the completeness audit found missing (both fixed-path, verified).
    assert (
        layout.relpath("uacp.convergence_budget", run_id="r1")
        == "proposals/r1-convergence-budget.yaml"
    )
    assert (
        layout.relpath("uacp.brainstorm_scope_package", run_id="r1")
        == "brainstorm/r1/07-scope-package.yaml"
    )


def test_caller_provided_kinds_absent_from_fixed_registry():
    # phase_transition + council_synthesis are caller-provided (runtime arg), not fixed paths.
    assert layout.template("uacp.phase_transition") is None
    assert layout.template("uacp.council_synthesis") is None
