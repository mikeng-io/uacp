#!/bin/sh
# UACP E2E acceptance — `runner:hermes`, Priority 1: PLUGIN CONFORMANCE.
#
# Faithful reproduction of a real user binding the UACP Guardian adapter into Hermes, then a verdict
# read ENTIRELY OUT OF HERMES' OWN REPORTS. This script never reads the plugin's source, never
# imports UACP's Python, and never starts the adapter itself: every DISCOVERED fact below comes from
# a Hermes command's output. If the bind is broken, this exits non-zero and the captured Hermes
# output under /out IS the bug report.
#
# WHAT IS PROVEN / WHAT IS NOT — see acceptance/hermes/README.md. In short: proven = the plugin
# loads inside a real Hermes at the interpreter Hermes itself chose, and every governed tool it
# declares is registered under its toolset. NOT proven = the lifecycle drive (Priority 2) and hook
# firing (Hermes exposes no model-free report of plugin hook registration).
set -u

OUT=${OUT:-/out}
UACP=${UACP:-/uacp}
ADAPTER=uacp_guardian
PLUGIN_YAML="$UACP/runtime-adapters/hermes/plugins/$ADAPTER/plugin.yaml"
API_PORT=8642
API_KEY=uacp-acceptance-local-only
mkdir -p "$OUT"

fail=0
fail_with() { echo "FAIL: $*"; fail=1; }

# Environment evidence: which interpreter did HERMES pick? The defect this harness exists to catch
# was a floor defect, so the interpreter is part of the record, not an aside.
echo "### the runtime under test (Hermes' own report)"
hermes --version 2>&1 | tee "$OUT/00-hermes-version.txt"

# ---------------------------------------------------------------------------
# EXPECTED — derived from the shipped manifest, never hardcoded here.
# ---------------------------------------------------------------------------
# The governed surface is whatever `tool_specs()` yields. plugin.yaml's tool list is GENERATED from
# that registry by scripts/gen_doc_tables.py and drift-linted in CI (`make docs-drift`), so reading
# the generated block is reading a projection of the registry — it tracks the registry automatically
# instead of rotting the way a literal count in this file would. (A hand-kept copy is exactly how the
# manifest once drifted to 10 while the kernel registered 19.)
sed -n '/BEGIN GENERATED: hermes-plugin-tools/,/END GENERATED: hermes-plugin-tools/p' "$PLUGIN_YAML" \
  | sed -n 's/^- *//p' | sort -u > "$OUT/10-expected-tools.txt"
expected_n=$(wc -l < "$OUT/10-expected-tools.txt" | tr -d ' ')
echo "### expected governed tools (derived from $PLUGIN_YAML): $expected_n"
if [ "$expected_n" -eq 0 ]; then
  # Fail closed: an empty EXPECTED set would make every comparison below vacuously true.
  echo "FAIL: could not derive the expected tool set from the generated block in $PLUGIN_YAML"
  exit 1
fi

# ---------------------------------------------------------------------------
# INSTALL — the user-real path for Hermes.
# ---------------------------------------------------------------------------
# Hermes has no marketplace. `config/uacp.toml [runtime_bindings.hermes]` declares the binding as a
# SYMLINK from HERMES_ROOT/plugins/<adapter> to the repo's adapter directory, and Hermes plugins are
# opt-in — a bound-but-not-enabled plugin never loads. Both steps are the user's.
echo "### install — symlink binding + opt-in enable (the declared Hermes binding)"
mkdir -p "$HERMES_HOME/plugins"
ln -sfn "$UACP/runtime-adapters/hermes/plugins/$ADAPTER" "$HERMES_HOME/plugins/$ADAPTER"
ls -l "$HERMES_HOME/plugins/" 2>&1 | tee "$OUT/01-binding.txt"
hermes plugins enable "$ADAPTER" </dev/null 2>&1 | tee "$OUT/02-plugins-enable.txt"

# ---------------------------------------------------------------------------
# OBSERVE — Hermes' own reports.
# ---------------------------------------------------------------------------
echo "### what Hermes itself reports"
hermes plugins list --json </dev/null > "$OUT/03-plugins-list.json" 2>&1
hermes tools list --platform cli </dev/null > "$OUT/04-tools-list.txt" 2>&1

# `hermes plugins list` reports ACTIVATION only (a directory scan + the config allow-list); it says
# nothing about whether the module imported. The loader's own view — which tools actually reached the
# live registry — is exposed by the api_server platform's GET /v1/toolsets, whose own docstring calls
# it "the deterministic equivalent of what a client would otherwise have to recover by asking the
# model what tools it can call". That is the report this harness reads: name-level, and model-free.
echo "### starting Hermes' api_server platform to read its registered-tool report"
API_SERVER_ENABLED=true \
API_SERVER_KEY="$API_KEY" \
API_SERVER_PORT="$API_PORT" \
API_SERVER_HOST=127.0.0.1 \
  hermes gateway </dev/null > "$OUT/05-gateway.log" 2>&1 &
gateway_pid=$!

ready=0
i=0
while [ "$i" -lt 90 ]; do
  if curl -fsS -H "Authorization: Bearer $API_KEY" "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  kill -0 "$gateway_pid" 2>/dev/null || break
  i=$((i + 1))
  sleep 2
done

if [ "$ready" -eq 1 ]; then
  curl -fsS -H "Authorization: Bearer $API_KEY" \
    "http://127.0.0.1:$API_PORT/v1/toolsets" > "$OUT/06-toolsets.json" 2>"$OUT/06-toolsets.err"
else
  fail_with "Hermes' api_server never became ready — cannot read its registered-tool report"
  echo ":: last 40 lines of Hermes' gateway log ::"
  tail -40 "$OUT/05-gateway.log"
fi

kill "$gateway_pid" 2>/dev/null
wait "$gateway_pid" 2>/dev/null

# Hermes records a plugin that raised during import/register() as
# `WARNING hermes_cli.plugins: Failed to load plugin '<name>': <reason>` in its own log, NOT on the
# gateway's stdout — so read it back through Hermes' own `logs` command, which is where a user would
# look. This is what turns a bare "nothing registered" into a diagnostic with the actual cause.
hermes logs --lines 600 </dev/null > "$OUT/07-hermes-logs.txt" 2>&1
hermes logs errors --lines 200 </dev/null > "$OUT/08-hermes-logs-errors.txt" 2>&1

# ---------------------------------------------------------------------------
# ASSERT — fail-closed, each against a Hermes-produced artifact.
# ---------------------------------------------------------------------------

# (1) The binding took: Hermes sees the adapter as a user plugin and it is opted in.
if ! jq -e --arg n "$ADAPTER" \
      'map(select(.name == $n and .source == "user" and .status == "enabled")) | length == 1' \
      "$OUT/03-plugins-list.json" >/dev/null 2>&1; then
  fail_with "Hermes does not report '$ADAPTER' as an enabled user plugin (see 03-plugins-list.json)"
fi

# (2) THE CRUX. Hermes wraps each plugin's load in its own `except` and merely records an error
# string, so "hermes started" proves nothing — a loaded-but-errored plugin is indistinguishable from
# a loaded one at the process level, and `hermes plugins list` still calls it "enabled". Hermes'
# OWN log carries the real verdict: `Failed to load plugin '<name>': <reason>`.
if grep -h "Failed to load plugin '$ADAPTER'" \
      "$OUT/07-hermes-logs.txt" "$OUT/08-hermes-logs-errors.txt" 2>/dev/null | sort -u > "$OUT/09-load-errors.txt" \
   && [ -s "$OUT/09-load-errors.txt" ]; then
  fail_with "Hermes reports '$ADAPTER' FAILED TO LOAD:"
  sed 's/^/    /' "$OUT/09-load-errors.txt"
fi

# (3) The plugin's toolset reached Hermes' LIVE tool registry. A plugin that raised during import or
# register() contributes no toolset at all, so absence here is the positive catch for (2) even when
# the log line is missing.
if [ -s "${OUT}/06-toolsets.json" ] && jq -e --arg n "$ADAPTER" \
      'any(.data[]; .name == $n)' "$OUT/06-toolsets.json" >/dev/null 2>&1; then
  jq -r --arg n "$ADAPTER" '.data[] | select(.name == $n) | .tools[]' \
    "$OUT/06-toolsets.json" | sort -u > "$OUT/11-discovered-tools.txt"
else
  fail_with "Hermes' registered-tool report contains no '$ADAPTER' toolset — the plugin registered nothing"
  : > "$OUT/11-discovered-tools.txt"
fi
discovered_n=$(wc -l < "$OUT/11-discovered-tools.txt" | tr -d ' ')

# (4) EXPECTED vs DISCOVERED, by NAME and exactly. Missing => a declared governed tool is not
# actionable. Extra => the shipped manifest no longer describes what installs.
comm -23 "$OUT/10-expected-tools.txt" "$OUT/11-discovered-tools.txt" > "$OUT/12-missing-tools.txt"
comm -13 "$OUT/10-expected-tools.txt" "$OUT/11-discovered-tools.txt" > "$OUT/13-unexpected-tools.txt"
if [ -s "$OUT/12-missing-tools.txt" ]; then
  fail_with "governed tools DECLARED but not registered in Hermes:"
  sed 's/^/    - /' "$OUT/12-missing-tools.txt"
fi
if [ -s "$OUT/13-unexpected-tools.txt" ]; then
  fail_with "tools registered under '$ADAPTER' that the shipped manifest does not declare:"
  sed 's/^/    + /' "$OUT/13-unexpected-tools.txt"
fi

# ---------------------------------------------------------------------------
# SERIALIZE.
# ---------------------------------------------------------------------------
verdict=PASS
[ "$fail" -eq 0 ] || verdict=FAIL
jq -n \
  --arg verdict "$verdict" \
  --arg adapter "$ADAPTER" \
  --arg hermes_version "$(head -1 "$OUT/00-hermes-version.txt" 2>/dev/null)" \
  --arg interpreter "$(sed -n 's/^Python: *//p' "$OUT/00-hermes-version.txt" 2>/dev/null | head -1)" \
  --argjson expected_count "$expected_n" \
  --argjson discovered_count "${discovered_n:-0}" \
  --arg expected "$(cat "$OUT/10-expected-tools.txt")" \
  --arg discovered "$(cat "$OUT/11-discovered-tools.txt")" \
  --arg missing "$(cat "$OUT/12-missing-tools.txt" 2>/dev/null)" \
  --arg unexpected "$(cat "$OUT/13-unexpected-tools.txt" 2>/dev/null)" \
  --arg load_errors "$(cat "$OUT/09-load-errors.txt" 2>/dev/null)" \
  '{
     measurement: "plugin-conformance",
     runner: "hermes",
     verdict: $verdict,
     adapter: $adapter,
     hermes_version: $hermes_version,
     interpreter_selected_by_hermes: $interpreter,
     binding_kind: "symlink into HERMES_ROOT/plugins (config/uacp.toml [runtime_bindings.hermes])",
     expected_source: "generated tools block of the shipped plugin.yaml (derived from tool_specs())",
     discovered_source: "hermes gateway api_server GET /v1/toolsets",
     hermes_reported_load_errors: ($load_errors | split("\n") | map(select(length > 0))),
     expected_count: $expected_count,
     discovered_count: $discovered_count,
     expected_tools: ($expected | split("\n") | map(select(length > 0))),
     discovered_tools: ($discovered | split("\n") | map(select(length > 0))),
     missing_tools: ($missing | split("\n") | map(select(length > 0))),
     unexpected_tools: ($unexpected | split("\n") | map(select(length > 0))),
     not_proven_here: [
       "lifecycle drive (Priority 2 — no MCP/tool channel for init/transition/register/finalize)",
       "plugin hook firing (Hermes exposes no model-free report of plugin hook registration)"
     ]
   }' > "$OUT/conformance.json"

echo
if [ "$fail" -eq 0 ]; then
  echo "PASS: Hermes loaded '$ADAPTER' on Python $(sed -n 's/^Python: *//p' "$OUT/00-hermes-version.txt" | head -1) and registered all $expected_n declared governed tools"
else
  echo "FAILED — see $OUT/conformance.json and the captured Hermes output in $OUT/"
fi
exit "$fail"
