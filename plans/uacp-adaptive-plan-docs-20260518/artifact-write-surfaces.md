# Artifact Write Surfaces

## Governed artifacts
Use `uacp_artifact_write` for:
- PLAN package docs.
- verification fixtures where practical.
- council synthesis / verification outputs.

## Config docs/source patches
Use `uacp_config_write` for full config rewrites where practical. Use targeted patch for code/skill changes where governed writers are not suitable.

## Bootstrapping exception
This run modifies UACP's own enforcement system. If normal patch tooling is used for code/config source, record it in EXECUTE evidence and verify exact diffs.
