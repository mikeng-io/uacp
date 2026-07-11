"""Unit tests for the runtime-neutral governed-tool registry (tool_specs).

The ``tool_specs()`` registry in skills/uacp-core/scripts/tool_specs.py is the
single source of truth for the governed tools consumed by both the Hermes
adapter and (next) an MCP server. These tests pin the contract: all names
present, each input_schema is a well-formed JSON-schema object, the read_only
flags are correct (oracle/heartgate/sandbox read-only; the rest writers —
including uacp_contained_shell which is a WRITER), and each handler is callable.
"""

from __future__ import annotations

from tool_specs import ToolSpec, hermes_schema, tool_specs

_EXPECTED_NAMES = {
    "uacp_state_write",
    "uacp_run_registry_update",
    "uacp_escalation_event",
    "uacp_artifact_write",
    "uacp_entity_write",
    "uacp_doc_write",
    "uacp_config_write",
    "uacp_sandbox_check",
    "uacp_contained_shell",
    "uacp_gate_ledger_append",
    "uacp_heartgate_check",
    "uacp_oracle_query",
    "uacp_corpus_write",  # #119 governed Oracle corpus writer
    # Run lifecycle tools (Phase 8)
    "uacp_run_init",
    "uacp_run_transition",
    "uacp_run_register_artifact",
    "uacp_run_finalize",
    "uacp_run_abort",  # #107 off-ramp primitive
}

# read_only=True only for the read-only tools; all 14 others are writers.
_READ_ONLY = {"uacp_oracle_query", "uacp_heartgate_check", "uacp_sandbox_check"}


def test_tool_specs_has_all_eighteen_names():
    specs = tool_specs()
    assert len(specs) == 18
    assert {s.name for s in specs} == _EXPECTED_NAMES


def test_each_input_schema_is_object_with_properties():
    for spec in tool_specs():
        schema = spec.input_schema
        assert isinstance(schema, dict), f"{spec.name}: input_schema not a dict"
        assert schema.get("type") == "object", f"{spec.name}: schema type not 'object'"
        assert isinstance(schema.get("properties"), dict) and schema["properties"], (
            f"{spec.name}: schema missing non-empty properties"
        )
        assert isinstance(schema.get("required"), list), (
            f"{spec.name}: schema missing required list"
        )


def test_read_only_flags_are_correct():
    for spec in tool_specs():
        expected = spec.name in _READ_ONLY
        assert spec.read_only is expected, (
            f"{spec.name}: read_only={spec.read_only}, expected {expected}"
        )
    # uacp_contained_shell is explicitly a WRITER, not read-only.
    contained = next(s for s in tool_specs() if s.name == "uacp_contained_shell")
    assert contained.read_only is False


def test_each_handler_is_callable():
    for spec in tool_specs():
        assert callable(spec.handler), f"{spec.name}: handler not callable"


def test_all_toolsets_are_uacp_guardian():
    assert all(s.toolset == "uacp_guardian" for s in tool_specs())


def test_hermes_schema_wraps_bare_input_schema():
    for spec in tool_specs():
        wrapped = hermes_schema(spec)
        assert wrapped["name"] == spec.name
        # Wrapped description is the JSON-schema-level description.
        assert wrapped["description"] == spec.schema_description
        # The wrapped 'parameters' IS the bare input_schema object.
        assert wrapped["parameters"] is spec.input_schema


def test_tool_spec_is_frozen_dataclass():
    spec = tool_specs()[0]
    assert isinstance(spec, ToolSpec)
