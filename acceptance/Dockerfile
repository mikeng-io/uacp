# UACP E2E acceptance — Increment 0: plugin conformance in a clean container.
#
# Proves the UACP plugin is ACTIONABLE in a fresh environment with only the documented host prereqs
# (uv — the MCP server's launch dependency). It runs the conformance prober (acceptance/conformance.py)
# against the plugin: launch the MCP server exactly as plugin.json configures it and assert the listed
# tool set == tool_specs(), plus the shipped hooks/skills are loadable. No model, no network at run.
#
# The deterministic prober is the same one tests/acceptance/test_plugin_conformance.py exercises in CI;
# this container is the "fresh, isolated, prereqs-only" wrapper. Driving a full `claude plugin install`
# round-trip (vs probing the plugin source) is the next refinement (the runner image, node 11).
FROM python:3.12-slim

# uv = the ONLY host prereq the plugin's MCP server needs (it self-provisions the server's deps).
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /uacp
COPY . /uacp

# Warm the uv environment so the conformance run is offline + fast (fail the build if the plugin's
# MCP launch command can't even resolve its deps — that itself is a packaging problem worth catching).
RUN uv run --no-project --with "mcp>=1.0" --with anyio --with pyyaml --with "pydantic>=2.0" \
    --with "jsonschema>=4.0" python -c "import mcp, anyio, yaml, pydantic, jsonschema; print('deps ok')"

# AFTER the warm build step: force uv to use its (now-populated) cache without touching the registry,
# so the offline run (network_mode: none) does not DNS-fail on the nested `uv run` server launch.
# The prober passes UV_* through to that nested launch, so this reaches the server too.
ENV UV_OFFLINE=1

# Run the prober via uv with its deps (pyyaml for skills, the mcp client, + tool_specs' pydantic/
# jsonschema chain) — same self-provisioning pattern the plugin uses for the server. uv self-launches
# the server as a nested `uv run` (deps cached at build, so the run is offline). Exit non-zero if any
# expected capability is not actionable (fail-closed conformance gate).
CMD ["uv", "run", "--no-project", "--with", "mcp>=1.0", "--with", "anyio", "--with", "pyyaml", \
     "--with", "pydantic>=2.0", "--with", "jsonschema>=4.0", \
     "python", "acceptance/conformance.py", "/uacp", "--out", "/out/conformance.json"]
