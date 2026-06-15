# Golden artifact fixtures

Minimal **valid** instances of each UACP structured-artifact kind. They double as
templates a real run would produce, and as inputs for later E2E tasks.

The authoritative schema is [`skills/uacp-core/scripts/engines/domain/artifact_schema.py`](../../../skills/uacp-core/scripts/engines/domain/artifact_schema.py)
(codified in Slice 4a; accessed at runtime via `artifact_schemas_dict()`).
Each fixture mirrors only the fields that schema declares — required fields plus the
bare minimum to be a valid instance (YAGNI). No invented fields.

## Filename mapping

The Task-5 brief suggested filenames `proposal / plan / checkpoint / verification /
closure`. Those are *lifecycle-phase* names, not the schema's artifact-**kind** names.
`artifact_schema.py` (via `artifact_schemas_dict()`) defines five kinds, and the YAML
fixtures are named for the schema's real kinds so the validation test can be schema-derived.
The mapping:

| Brief term      | Schema kind               | Fixture file          | Format | Validation basis            |
| --------------- | ------------------------- | --------------------- | ------ | --------------------------- |
| plan / scope    | `uacp.scope`              | `scope.yaml`          | YAML   | `required_fields`           |
| closure         | `uacp.lessons`            | `lessons.yaml`        | YAML   | `required_fields`           |
| (state)         | `uacp.run_registry`       | `run_registry.yaml`   | YAML   | `required_fields`           |
| proposal        | `uacp.intent`             | `intent.md`           | MD     | `required_sections`         |
| verification    | `uacp.evidence_disposition` | `verified-facts.md` + `assumptions.md` | MD | `paired_paths` + header check |

### Why not five YAML files named as the brief suggested

Only three schema kinds are YAML mappings with a `required_fields` list
(`scope`, `lessons`, `run_registry`) — these get YAML fixtures whose required
top-level keys the validation test reads straight from the schema.

The other two kinds are **not** YAML mappings:

- `uacp.intent` is a Markdown charter (`path_template: proposals/{run_id}-intent.md`)
  defined by `required_sections`, not `required_fields`.
- `uacp.evidence_disposition` is a *pair* of Markdown files (`paired_paths`:
  verified-facts + assumptions) governed by `required_sections`-style header
  substring cross-checks (`evidence_disposition_minimum_content`), not by
  top-level YAML keys.

Forcing those two into YAML would mean inventing fields the schema does not declare,
which the brief explicitly forbids. They are provided here as faithful Markdown golden
templates instead.

## Validation

`../test_fixtures_valid.py`:

- For the three YAML kinds, reads the `required_fields` list **from
  `engines.domain.artifact_schema.artifact_schemas_dict()`** (codified in Slice 4a)
  and asserts each fixture parses as a YAML mapping containing every required key.
  Schema-derived, so it stays correct if the schema evolves.
- For the two Markdown kinds, asserts each file contains the schema-declared
  `required_sections` headings (intent) or the required header substring from
  `evidence_disposition_minimum_content` (verified-facts / assumptions).
