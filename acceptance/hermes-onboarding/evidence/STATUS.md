# Status as of 2026-09-13

## Calibrated — both required calibrations pass

- **Planted-fault** (`calibration-fault/`): `TARGET_URL` pointed at `agent.trustless.zone.invalid`
  → `verdict: ERROR`. Never a silent PASS. Re-run cleanly (single, uninterrupted process) after the
  dependency-bootstrap fix below; took 202s wall-clock for a task that should fail in seconds —
  see "Open issue" below, this is itself informative, not a passing grade on speed.
- **Self-attestation** (`calibration-self-attestation/`): synthetic agent report claiming
  `funded: true` against a real, independently-verified zero-balance bearer token →
  `leg_fund: FAIL`, `"agent claims funded, but independent GET /v1/account shows no positive
  balance — contradiction (self-attestation caught)"`. `leg_register` correctly PASSed on the same
  report (the registration claim WAS true) — proves the independent-check step discriminates
  per-leg, not just on overall vibes.

## Two real bugs found and fixed in the harness itself while getting here

1. **Cloudflare blocks `urllib`'s default User-Agent** (403, "error code: 1010"). Without the fix,
   `verify.py` would have reported a contradiction on every truthful claim, not just lies. Fixed:
   `verify.py` now sends `User-Agent: curl/8.5.0`.
2. **Hermes eagerly imports every provider adapter at startup**, and importing
   `agent/bedrock_adapter.py` silently triggers a `pip install boto3` via Hermes' own `lazy_deps`
   mechanism — regardless of which provider the run actually uses. On a fresh ephemeral install
   this ate the entire wall-clock budget on two separate real-run attempts (25min, then 45min),
   producing `usage.json: {"failure": "KeyboardInterrupt()", "api_calls": null}` — i.e. it never
   even got to complete one turn. Fixed by baking `boto3==1.42.89` (and, preemptively,
   `eth-account`/`web3`/`ethers` — the task needs an EOA + EIP-712 signature, and those libraries'
   `coincurve` dependency can need a slow from-source build) into the image at build time.

## Open issue — NOT yet fixed, recommended next step

Even after both fixes, the clean fault-calibration re-run still needed a forced `SIGKILL` (exit
137) after the full 180s bound *and* the 20s SIGINT grace period. The live, mid-run diagnostic
during the very first fault attempt showed why: when confused, the agent runs expensive, unbounded
terminal commands (observed: `grep -rn trustless / --include=* -l` — a recursive grep of the
*entire* container filesystem, including venvs and node_modules). `config.yaml`'s
`terminal.timeout: 180` should cap any single command, but the overall process still isn't
responsive to SIGINT within a reasonable grace window — plausibly because hermes is synchronously
blocked waiting on that child process and only regains control once ITS OWN per-command timeout
fires, by which point our outer SIGINT has already been sitting unhandled.

**Recommended before the next real attempt:** lower `terminal.timeout` in `config.yaml` to
something like 30–45s, so one runaway command can no longer consume the whole wall-clock budget.
This is a harness-robustness fix, not a trustless-specific one.

## The real run itself — still genuinely open

Three attempts (25min, 45min, 20min — the last two after the boto3 fix) all ended `ERROR`
(transcript never produced a parseable final JSON block), never a false PASS. The last attempt's
`usage.json` showed `KeyboardInterrupt()` with no completed turns recorded at all, which is
consistent with the terminal-timeout issue above (stuck on one expensive command) rather than the
register→fund→trade flow itself having been exercised and failed. **Whether trustless's
documented agent onboarding promise actually holds end-to-end is still unproven** — what is proven
is that this harness will correctly report ERROR (not PASS) until it genuinely completes, and that
two real, unrelated infra defects stood between "built" and "ran."

No known side effects on the live trustless deployment from any of these attempts: every killed
run never reached a point where `usage.json` or any transcript showed a completed identity
registration or faucet call, so no faucet-cap budget is known to have been consumed by this work.
