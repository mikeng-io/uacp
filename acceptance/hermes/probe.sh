#!/bin/sh
# DISCOVERY probe — the reproducible record behind run.sh's choice of assertions.
#
# GOAL.md requirement 3 says to determine how Hermes reports plugin load status and tool registration
# against the REAL CLI in-container, not from documentation. This script is that determination, kept
# in-tree so it can be re-run when Hermes' pin moves. It produces NO verdict; run.sh does.
#
#   docker compose -f acceptance/hermes/compose.yml run --rm conformance-hermes /probe.sh
#
# Findings as of Hermes v0.17.0 (2026.6.19) — see README.md for the summary table:
#   USED  hermes plugins list --json ......... activation ONLY (dir scan + config allow-list); still
#                                              says "enabled" for a plugin that failed to import
#   USED  hermes logs / logs errors .......... the loader's own "Failed to load plugin '<n>': <why>"
#   USED  gateway api_server GET /v1/toolsets  concrete registered tool NAMES; needs no model
#   USED  hermes tools list --platform cli ... the plugin's toolset under "Plugin toolsets"
#   dead  hermes chat -q "/tools" / hermes -z  sends the text to the MODEL; does not dispatch slashes
#   dead  hermes mcp serve ................... a MESSAGING bridge, not the agent's tool surface
#   dead  hermes doctor / hermes status ...... nothing about user-plugin load state
#   dead  hermes tools --summary ............. requires a TTY
#   dead  hermes hooks list .................. shell-script hooks in config.yaml, a different subsystem
#   n/a   hermes prompt-size --json .......... a tool COUNT only (16 bare -> 35 bound); no names
set -u
OUT=${OUT:-/out}
API_PORT=8642
API_KEY=uacp-acceptance-local-only
mkdir -p "$OUT/probe"

run() {
  label="$1"; shift
  echo "===== $label :: $* ====="
  "$@" </dev/null 2>&1
  echo "----- exit=$? -----"
}

{
  echo "### BEFORE the bind — baseline"
  run version hermes --version
  run help hermes --help
  run prompt-size-bare hermes prompt-size --json

  echo "### install the user-real symlink binding + opt-in enable"
  mkdir -p "$HERMES_HOME/plugins"
  ln -sfn /uacp/runtime-adapters/hermes/plugins/uacp_guardian "$HERMES_HOME/plugins/uacp_guardian"
  run plugins-enable hermes plugins enable uacp_guardian

  echo "### AFTER the bind — every candidate report"
  run plugins-list-json hermes plugins list --json
  run plugins-list-plain hermes plugins list --plain --no-bundled
  run tools-list hermes tools list --platform cli
  run tools-summary hermes tools --summary
  run prompt-size-bound hermes prompt-size --json
  run doctor hermes doctor
  run status hermes status
  run hooks-list hermes hooks list
  run chat-q-slash hermes chat -q "/tools"
  run logs hermes logs --lines 200
  run logs-errors hermes logs errors --lines 100
} > "$OUT/probe/probe.txt" 2>&1

# The name-level oracle, probed separately because it needs the gateway running.
{
  echo "===== gateway api_server GET /v1/toolsets ====="
  API_SERVER_ENABLED=true API_SERVER_KEY="$API_KEY" \
  API_SERVER_PORT="$API_PORT" API_SERVER_HOST=127.0.0.1 \
    hermes gateway </dev/null > "$OUT/probe/gateway.log" 2>&1 &
  gw=$!
  i=0
  while [ "$i" -lt 90 ]; do
    curl -fsS -H "Authorization: Bearer $API_KEY" "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1 && break
    kill -0 "$gw" 2>/dev/null || break
    i=$((i + 1)); sleep 2
  done
  curl -sS -H "Authorization: Bearer $API_KEY" "http://127.0.0.1:$API_PORT/v1/toolsets" 2>&1
  echo
  kill "$gw" 2>/dev/null
} >> "$OUT/probe/probe.txt" 2>&1

echo "wrote $OUT/probe/probe.txt"
