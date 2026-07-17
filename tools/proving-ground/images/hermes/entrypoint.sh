#!/usr/bin/env bash
# Proving Ground hermes cell entrypoint.
#
# Two modes:
#   * Pass-through: `docker run IMAGE hermes ...` (e.g. `hermes acp --check`) execs the given hermes
#     command verbatim -- no model config needed, so the adapter self-check needs no env contract.
#   * Default drive: `docker run IMAGE` (no args) renders HERMES_HOME/config.yaml from the REQUIRED
#     env contract, then execs `hermes acp` to speak ACP over stdio.
set -euo pipefail

if [ "${1:-}" = "hermes" ]; then
  exec "$@"
fi

: "${OPENAI_BASE_URL:?OPENAI_BASE_URL is required (provider env contract)}"
: "${OPENAI_API_KEY:?OPENAI_API_KEY is required (provider env contract)}"
: "${UACP_MODEL_ID:?UACP_MODEL_ID is required (pinned model_id, provider env contract)}"

mkdir -p "${HERMES_HOME}"
# Python, not sed, and json.dumps for the whole quoted scalar: a JSON string is a valid YAML
# double-quoted scalar, so opaque values (quotes, backslashes, sed metacharacters, newlines)
# land as data — never as YAML syntax or injected config fields.
python3 - <<'PY'
import json
import os
from pathlib import Path

template = Path("/opt/proving-ground/config.yaml.template").read_text()
rendered = (
    template.replace('"@MODEL_ID@"', json.dumps(os.environ["UACP_MODEL_ID"]))
    .replace('"@BASE_URL@"', json.dumps(os.environ["OPENAI_BASE_URL"]))
    .replace('"@API_KEY@"', json.dumps(os.environ["OPENAI_API_KEY"]))
)
Path(os.environ["HERMES_HOME"], "config.yaml").write_text(rendered)
PY

exec hermes acp "$@"
