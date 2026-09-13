# `runner:hermes-onboarding` — agent-native onboarding conformance

The execute-profile sibling of [`acceptance/hermes`](../hermes/README.md). Same discipline —
fresh install, no warming, assert on the subject's own report — aimed at a different target and
with the two things that harness withholds turned on: a real model, and real network.

## The hole it closes

trustless PR #859 added agent self-funding (`POST /v1/agents/funding/faucet`) and merged on code
review + unit/handler tests alone — never driven by an actual independent agent. Code review is a
proxy for "works," not a measurement of it. `GOAL.md` has the full context.

## Run it

```bash
OMNIROUTE_API_KEY=$(grep -m1 '^OMNIROUTE_API_KEY=' ~/.hermes/.env | cut -d= -f2-) \
  docker compose -f acceptance/hermes-onboarding/compose.yml run --rm onboarding-hermes
cat acceptance/hermes-onboarding/out/conformance.json   # the serialized verdict
cat acceptance/hermes-onboarding/out/01-hermes-session.txt   # the agent's full transcript
```

**The real run is single-shot.** The live faucet shares a small daily cap across every caller on
the deployment — do not loop this for convenience. For calibration (below), use `TARGET_URL` to
point at a harmless target instead of repeating the real run.

## What it does

1. **A genuinely clean agent.** Fresh `HERMES_HOME` built inside the image: no memory, no skills,
   no plugins (not even UACP's own), no prior conversation. This is a different instance from the
   long-running host Hermes (`~/.hermes`) — that one carries months of accumulated identity/memory
   and is never touched or reused here. The agent is told nothing about trustless, erc8004, or
   EIP-712 beyond what it discovers by fetching `https://agent.trustless.zone/llms.txt` itself. It
   gets a generic coding sandbox (python3/pip/node/npm/openssl/curl) — the kind of tool access any
   capable agent host would carry — not this-API-specific scaffolding.
2. **Drive the real flow.** `hermes -z` (headless, one-shot, `--yolo` — justified here because this
   is a consented *execute* probe in a disposable, no-host-mount container, not an unattended audit
   of someone else's code) is told to register, get itself verified, fund itself, and place one
   real order, using only what it discovers. It reports back a single structured JSON claim.
3. **Never trust the claim.** `verify.py` is the measuring instrument, and it runs *outside* the
   agent: for every claim (registered / funded / order placed) it issues its own HTTP call against
   the live API using the bearer token the agent reports, and computes the verdict from THOSE
   responses — not from the agent's prose. An agent that says "funded: true" while its own account
   balance is independently observed to be zero is reported as a **contradiction**, not a pass.
4. **Three legs, fail-closed.** `leg_register` / `leg_fund` / `leg_trade`, each PASS / FAIL / ERROR.
   ERROR (bad JSON, network failure, can't determine) is never reported as PASS. A 429/409 the API
   itself documents as "ordinary" (daily faucet cap spent, already funded) is a legitimate FAIL
   with that exact reason — not a harness defect.

## Proven / not proven

**Proven.** That a third-party agent — different model, fresh install, zero insider knowledge of
trustless's source, config, or database, nothing but the public `llms.txt` — can autonomously
complete register → verify → self-fund → place-an-order against the live deployment, with every
step independently re-derived from the API itself rather than taken on the agent's word.

**Not proven, deliberately:**
- **A trade fill.** Placement acceptance is the bar; a fill needs a counterparty order this harness
  does not control.
- **Public-internet reachability.** This runs from the same network as the rest of this project's
  infra, not from an arbitrary external vantage point.
- **Repeatable-at-will.** The real run consumes a slice of a small, shared, global daily faucet
  cap. Running it often is itself a way to break the thing it is testing.

## Calibrated, not merely green

Both required calibrations — [`evidence/`](evidence/) — before this is trusted:
- **Planted-fault (entrypoint unreachable).** `TARGET_URL` pointed at a garbage host → confirmed
  RED on `leg_register`, naming "could not fetch entrypoint," not a silent pass or a bare timeout.
  Costs nothing (never reaches the real faucet).
- **Self-attestation (the defect class this harness exists to catch).** A synthetic agent report
  claiming `funded: true` against a bearer token independently known to hold a zero balance →
  confirmed the verdict is **FAIL with a named contradiction**, proving the independent-check step
  is live and not decorative.

## Where this runs

Periodic / pre-release, like its sibling — not a merge gate, and not something to run on a cron
given the shared faucet cap. Run it when the agent-facing surface (identity, funding, or order
placement routes) changes, or before claiming the onboarding story is "done."
