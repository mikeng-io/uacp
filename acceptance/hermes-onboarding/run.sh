#!/bin/sh
# runner:hermes-onboarding — drive a fresh, insider-knowledge-free Hermes through trustless's
# documented agent onboarding flow, then independently re-verify every claim it makes (verify.py)
# rather than trusting its self-report. See README.md / GOAL.md for what this proves.
set -u
OUT=${OUT:-/out}
TARGET_URL=${TARGET_URL:-https://agent.trustless.zone/llms.txt}
TIMEOUT_SECONDS=${TIMEOUT_SECONDS:-1500}
ORIGIN=$(python3 -c "import sys,urllib.parse as u; p=u.urlparse(sys.argv[1]); print(f'{p.scheme}://{p.netloc}')" "$TARGET_URL")
mkdir -p "$OUT"

echo "### the runtime under test (Hermes' own report)"
hermes --version 2>&1 | tee "$OUT/00-hermes-version.txt"
echo "### target: $TARGET_URL  (origin for independent checks: $ORIGIN)"

# Build the prompt: substitute the real target into the neutral brief. The agent gets ONLY this
# URL — nothing trustless-specific is added here or anywhere else in this container.
sed "s#__TARGET_URL__#$TARGET_URL#" /home/agent/prompt.md > "$OUT/prompt-used.md"
PROMPT=$(cat "$OUT/prompt-used.md")

echo "### running the agent (headless, single shot, bounded at ${TIMEOUT_SECONDS}s)"
# --yolo is deliberate here (unlike a read-only `inspect` run): this is a consented EXECUTE probe
# in a disposable container with no host mount, not an unattended audit of someone else's code.
# PYTHONUNBUFFERED + stdbuf: so 01-hermes-session.txt fills in live (checkable mid-run with `tail
# -f`) instead of buffering until exit, which matters for a run that can take many minutes.
# -s INT, not the default TERM: Python's default SIGTERM handling just kills the process with no
# cleanup, so any "flush partial output / write the usage file even on failure" path hermes has
# only gets a chance to run on SIGINT (-> KeyboardInterrupt). -k 20 force-kills if it still won't
# exit 20s after that.
PYTHONUNBUFFERED=1 stdbuf -oL -eL timeout -s INT -k 20 "$TIMEOUT_SECONDS" \
  hermes -z "$PROMPT" -m norty --provider omniroute -t terminal --yolo \
  --usage-file "$OUT/usage.json" \
  > "$OUT/01-hermes-session.txt" 2>&1
hermes_exit=$?
echo "hermes -z exit code: $hermes_exit" | tee -a "$OUT/01-hermes-session.txt" >/dev/null

if [ "$hermes_exit" -eq 124 ]; then
  echo "FAIL: hermes -z was killed after ${TIMEOUT_SECONDS}s without finishing"
fi

echo "### measuring — independent verification against $ORIGIN (verify.py), not the agent's prose"
python3 /verify.py --transcript "$OUT/01-hermes-session.txt" --origin "$ORIGIN" --out "$OUT/conformance.json"
verify_exit=$?

echo
echo "### verdict: $(python3 -c "import json;print(json.load(open('$OUT/conformance.json'))['verdict'])" 2>/dev/null || echo UNKNOWN)"
echo "full detail: $OUT/conformance.json"
exit "$verify_exit"
