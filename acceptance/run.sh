#!/bin/sh
# Faithful reproduction of a NORMAL USER installing + using the UACP plugin (E2E acceptance, node 13).
#
# Runs the user's published commands and reports CLAUDE CODE'S OWN verdict — it never reads the plugin
# source, launches the MCP server itself, or warms anything. If a normal install/run is broken, this
# exits non-zero and the captured Claude Code output IS the bug report.
set -u
OUT=/out
mkdir -p "$OUT"

echo "### install — the user's published path"
claude plugin marketplace add /uacp 2>&1 | tee "$OUT/01-marketplace.txt"
claude plugin install uacp@uacp 2>&1 | tee "$OUT/02-install.txt"

echo "### what Claude Code itself reports it loaded"
claude plugin list 2>&1 | tee "$OUT/03-plugin-list.txt"
claude mcp list 2>&1 | tee "$OUT/04-mcp-list.txt"

fail=0
if grep -qiE "failed to load|✘ " "$OUT/03-plugin-list.txt"; then
  echo "FAIL: Claude Code reports the plugin failed to load"
  fail=1
fi
if ! grep "plugin:uacp" "$OUT/04-mcp-list.txt" | grep -qi "connected"; then
  echo "FAIL: the plugin's MCP server did not connect"
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "PASS: Claude Code loaded the plugin and its MCP server connected"
fi
exit "$fail"
