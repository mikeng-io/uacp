# Goal: `runner:hermes-onboarding` acceptance container — agent-native onboarding conformance

Prove trustless's documented `register -> fund -> trade` promise for autonomous agents by having
a genuinely independent agent — fresh install, fresh model session, zero insider knowledge of
trustless's source/config/database — read nothing but the public `https://agent.trustless.zone/llms.txt`
and attempt the flow on its own, with the resulting claims independently re-checked against the
live API rather than trusted.

## Why this exists (the defect class it must catch)

trustless PR #859 added `POST /v1/agents/funding/faucet` (agent self-funding) and merged on code
review + unit/handler tests alone. Five review rounds, zero live runs by an actual third-party
agent. "Reviewed" is not a measurement of "works" — it is a proxy, and a proxy standing in for a
live property is exactly the failure this harness exists to close (the sibling `acceptance/hermes`
harness closed the analogous hole for UACP plugin loading; this one closes it for the thing that
plugin conformance was never trying to prove: that the documented agent flow is actually walkable).

A second, sharper risk this harness must guard against: an LLM self-reporting success it did not
achieve. The agent under test is the only witness to its own actions unless something independent
re-derives the same facts. That is why every claim in the agent's self-report gets a second,
harness-issued HTTP call before it counts.

## Scope

**This harness drives the real flow end to end** — the opposite scope of `acceptance/hermes`
(Priority 1, plugin-load-only, explicitly *not* driving any lifecycle). Here the lifecycle drive
*is* the point:
1. Register (erc8004 — anonymous cannot fund or trade per `llms.txt`, so the agent must generate
   a wallet and produce a valid EIP-712 signature itself, with no crypto-specific help beyond what
   `llms.txt` states).
2. Observe verification (poll `GET /v1/me`).
3. Self-fund via `POST /v1/agents/funding/faucet` — no human mint, no pre-seeded balance.
4. Attempt one real order (`POST /v1/orders`) — a fill is not required (it depends on a
   counterparty this harness does not control); an accepted placement is the bar.

## Read first

- `acceptance/hermes/` — the sibling harness. Mirror its shape and discipline (fresh
  install, no warming, assert on the subject's own report, fail-closed, calibrated). Do **not**
  mirror its `network_mode: none` or its no-model stance — both are specific to plugin-load-only
  conformance and are the opposite of what this harness needs.
- `https://agent.trustless.zone/llms.txt` / `/auth.md` — read it the way the agent under test
  will: cold, nothing pre-explained. It is the only spec this container's *subject* is allowed.
  The harness *author* (you) may read it to design the independent-verification calls; the agent
  inside the container may not be given anything beyond the URL.

## Hard requirements

1. **The agent under test gets nothing trustless-specific.** No repo mount, no pre-fetched
   `llms.txt`, no hints about EIP-712, erc8004, or this API's shapes beyond what `llms.txt` itself
   says. It gets a neutral task brief and a generic developer sandbox (python3/pip/node/npm/
   openssl/curl) — the kind of general tool access any capable coding agent host would carry, not
   this-service-specific scaffolding.
2. **Fresh every run.** New `HERMES_HOME`, no memory, no UACP plugin, no skills. This is a
   different instance from the long-running host Hermes (`~/.hermes`) — that one carries months of
   accumulated memory/identity and must not be reused or touched.
3. **No self-attestation.** The agent's final JSON report is a claim, not a verdict. For every
   claim the report makes (registered, verified, funded, order placed), the harness itself issues
   an independent HTTP call using the bearer token the agent obtained, and the verdict is computed
   from THAT, not from the agent's prose. A claim the independent check cannot corroborate is a
   contradiction, reported as such — not silently trusted.
4. **Fail-closed, three legs, named.** `leg_register` / `leg_fund` / `leg_trade`, each
   PASS/FAIL/ERROR, never collapsed into one boolean. ERROR (harness could not determine — bad
   JSON, network timeout, unparseable output) is never reported as PASS. A 429/409 the API itself
   calls "ordinary" (daily cap spent, already funded) is a legitimate FAIL with that exact reason,
   not a harness defect.
5. **Non-interactive, headless, bounded.** No approval prompts (`--yolo` is justified here,
   unlike the sibling's read-only `inspect` profile — this is a consented *execute* probe in a
   disposable, no-host-mount container, not an unattended audit). Bounded turns and a wall timeout.
6. **Real run is single-shot.** The live faucet has a small daily cap shared across all callers —
   do not loop the real run for convenience. Calibration (below) must never touch the real faucet.

## Acceptance criteria — calibrated, not merely green

- **Planted-fault calibration (mandatory, and free to repeat).** Point the SAME container at an
  unreachable entrypoint (`TARGET_URL` env override to a garbage host) and confirm the harness goes
  **RED** on `leg_register` with a diagnostic naming "could not fetch entrypoint" — not a timeout
  that looks like success, not a silent PASS. Then point it back at the real URL.
- **Self-attestation calibration.** Confirm the independent-verification step actually disagrees
  with a fabricated claim: feed the verification step a synthetic agent-report claiming
  `funded: true` with a bearer token known to hold zero balance, and confirm the harness reports
  a **contradiction** (FAIL, naming the mismatch) rather than trusting the claim. This proves
  requirement 3 is live, not decorative — the error class this harness exists to catch is exactly
  an agent that says "done" when it is not.
- Record both calibration runs under `evidence/`.

## Out of scope

Achieving a trade **fill** (needs a counterparty order this harness does not control — placement
acceptance is the bar, not matching). The lifecycle ops UACP itself defines (init/transition/
register/finalize) — unrelated; this is a probe of trustless's agent-facing API, not of UACP.
Public-internet reachability from outside norty's own network (this runs from the same network as
the rest of this project's infra; it proves the documented mechanics work, not edge ingress).

## Deliverables

`acceptance/hermes-onboarding/` — Dockerfile, config.yaml, prompt.md, run.sh, compose.yml, README
stating what is proven and what is explicitly not, `evidence/` with both calibration runs recorded.
