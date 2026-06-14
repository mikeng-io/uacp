"""E2E: golden artifact fixtures are valid instances of their schema kinds.

For the YAML artifact kinds the required-key list is read FROM
`config/artifact-schemas.yaml` (not hardcoded), so these tests stay correct if
the schema evolves. The two Markdown kinds (intent, evidence_disposition) are
not YAML mappings, so they are checked against their schema-declared
`required_sections` / required-header substrings instead. See fixtures/README.md
for the filename->kind mapping.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

UACP_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCHEMAS = yaml.safe_load((UACP_ROOT / "config" / "artifact-schemas.yaml").read_text())

# Fixture file <-> schema-kind key in config/artifact-schemas.yaml.
YAML_FIXTURES = {
    "scope.yaml": "scope",
    "lessons.yaml": "lessons",
    "run_registry.yaml": "run_registry",
}


@pytest.mark.parametrize("filename,schema_key", sorted(YAML_FIXTURES.items()))
def test_yaml_fixture_has_schema_required_fields(filename: str, schema_key: str):
    """Each YAML fixture parses as a mapping with every schema-required key."""
    required = SCHEMAS[schema_key]["required_fields"]
    assert required, f"schema {schema_key} declares no required_fields"

    doc = yaml.safe_load((FIXTURES / filename).read_text())
    assert isinstance(doc, dict), f"{filename} did not parse as a YAML mapping"

    missing = [key for key in required if key not in doc]
    assert not missing, f"{filename} missing schema-required keys: {missing}"


def test_intent_fixture_has_required_sections():
    """The intent Markdown charter contains every schema-declared section heading."""
    text = (FIXTURES / "intent.md").read_text()
    for section in SCHEMAS["intent"]["required_sections"]:
        assert section in text, f"intent.md missing required section: {section!r}"


@pytest.mark.parametrize(
    "filename,substring_key",
    [
        ("verified-facts.md", "verified_facts_required_header_substring"),
        ("assumptions.md", "assumptions_required_header_substring"),
    ],
)
def test_evidence_disposition_fixture_has_required_header(filename: str, substring_key: str):
    """Each disposition-pair fixture contains its schema-required header substring."""
    rules = SCHEMAS["cross_checks"]["evidence_disposition_minimum_content"]
    substring = rules[substring_key]
    text = (FIXTURES / filename).read_text()
    assert substring in text, f"{filename} missing required header substring: {substring!r}"
