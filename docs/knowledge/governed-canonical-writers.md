# Governed Canonical Writer Surfaces

Use this reference when UACP runtime work needs to mutate canonical artifacts without falling back to direct file edits.

## Pattern

UACP-owned runtime adapters should expose narrow writer tools by artifact class instead of relying on broad filesystem access:

- `uacp_state_write` for `state/` artifacts.
- `uacp_artifact_write` for allowed run/verification/output artifacts.
- `uacp_doc_write` for canonical Markdown under `docs/`.
- `uacp_config_write` for canonical YAML under `config/`.

The writer boundary should live in the UACP-owned runtime adapter source, with the host runtime consuming it through a user-plugin symlink or equivalent runtime binding.

## Required Context

Every governed writer call should carry full UACP context, not just a path and content:

- `uacp_run_id`
- `uacp_phase`
- `policy_version`
- `authority_artifact` / declared authority
- `declared_side_effects`
- `reason`
- target path and content

If these fields are missing, Guardian should block or treat the mutation as under-contexted.

## Containment Rules

- Resolve target paths against the intended UACP root and block path escape.
- Keep writer scopes separate: docs writer should not write config/state; config writer should not write docs/state.
- Restrict docs to `.md` unless the policy explicitly broadens the doc surface.
- Restrict config to `.yaml`/`.yml` and validate YAML before writing.
- Keep `state/` mutation under `uacp_state_write`; do not silently route state writes through generic doc/config/artifact writers.

## Guardian Classification

When host-runtime plugin provenance would otherwise classify all plugin calls as `runtime.extension`, use an explicit tool-name classification map for known UACP writers:

- known `uacp_*_write` tools receive their intended class (`state.uacp` or `file.write`) and audit decision;
- unknown plugin mutators remain blocked as `runtime.extension`.

This avoids weakening plugin security while permitting governed canonical writers.

## Verification Pattern

A safe live proof harness should test both positive and negative behavior, preferably against a temporary UACP root:

- positive doc write under `docs/`;
- positive YAML config write under `config/`;
- invalid YAML rejected by config writer;
- path escape rejected;
- known UACP writer classified as intended, e.g. `file.write / allow_with_audit`;
- unknown plugin mutator still blocked as `runtime.extension`;
- live user-plugin symlink and loader behavior still valid after adapter edits.

Record the result under `verification/` and update status artifacts through governed writers when available.

## Pitfall

Do not normalize manual doc/config edits after governed writer surfaces exist. If the running session schema has not reloaded and cannot see newly registered tools yet, state that as a runtime/session reload limitation and keep any direct writes narrow, recorded, and transitional.
