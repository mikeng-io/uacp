# UACP full-lineage lifecycle audit and documentation package pattern (2026-05-20)

Use this reference when UACP governance/runtime/documentation work spans multiple commits or lifecycle phases and Mike asks for coherence, consistency, or full review rather than a point fix.

## Trigger signals

- Mike says the audit must cover the entire lifecycle/change series, not just one commit.
- Mike asks Kimi/Codex to use their own Agent Councils, including devil's advocate roles.
- A patch touches any combination of docs, config, validator, runtime Guardian/Heartgate, active skill exports, state/current, fixtures, or semantic packages.
- Mike warns about documentation "fracture" or "scatter".
- Git identity/provenance matters for the UACP repo.

## Full-lineage audit prompt shape

Do not ask only whether the latest commit closed the latest finding. Ask whether the whole lifecycle coheres end-to-end.

Require the external runtime to audit at least:

- PROPOSE semantic package gates.
- PLAN package gates and Phase Intent Verification contract.
- EXECUTE PIV evidence checkpoint and semantic execution package.
- VERIFY truth gate, PIV assessment, self-approval guard, and resolve readiness.
- RESOLVE closure gate, carry-forward of residual risks/deferred items, and state disposition.
- Guardian protected path binding, including shell command text, workspace, cwd/workdir, and `$UACP_ROOT`.
- Heartgate runtime parity with offline validator semantics.
- Active Hermes skill exports and reference paths.
- State source-of-truth (`state/current.yaml` vs `config/state.yaml`).
- Existing real artifacts that could become stale or contradict the new contract.

Council roles should include:

1. Lifecycle governance reviewer.
2. Validator/runtime enforcement auditor.
3. Heartgate/Guardian security reviewer.
4. Adversarial false-pass/devil's advocate reviewer.
5. Operator-handoff / semantic-recovery reviewer.
6. Lifecycle consistency historian.
7. Dependency readiness reviewer.

## Remediation classes that proved important

When audits find coherence gaps, patch the systemic surfaces, not one fixture:

- Make Guardian bind UACP paths from direct args, `workspace`, `cwd`, `workdir`, command strings, `$HOME`, and `$UACP_ROOT`.
- Ensure Heartgate and offline validator agree: if a Heartgate runtime fail fixture passes the offline validator, patch linked transition validation.
- Bind accepted exceptions by `(artifact_path, cluster_id)` and require run-bound evidence, not arbitrary existing files.
- Require PIV pass evidence to exist and be run-bound.
- VERIFY is truth; RESOLVE is closure. RESOLVE must not drop residual risks/deferred items from readiness or resolve package.
- Block unknown `uacp.*` kinds rather than silently ignoring them.
- Reconcile `state/current.yaml` with `config/state.yaml`; state pointers must be run-bound, not substring-bound.
- Check active skill exports separately from repo docs; repo docs can be correct while live skills are stale.
- Runtime smoke harnesses should use a temporary copied UACP root when they need fixture ledgers.

## Documentation anti-fracture pattern

When Mike asks for human-readable documentation after a large UACP hardening pass, create a modular guide package rather than a single mega-doc or random edits.

Recommended shape:

```text
docs/guides/<topic>/
  00-index.md                    # conductor: reading order, authority map, anti-fracture rule
  01-human-overview.md            # readable explanation for humans
  02-agent-operating-guide.md     # future-agent workflow and pitfalls
  03-artifact-and-gate-map.md     # where meaning/evidence/enforcement lives
  04-audit-and-remediation-history.md
```

Also create or update `docs/guides/INDEX.md`, then link the package from `docs/INDEX.md` and `README.md`. The guide must explain and route; it must not become a competing authority layer.

Canonical ownership remains:

- `config/phase-transitions.yaml` for phase/gate policy.
- `scripts/validate_uacp_artifacts.py` for offline validation.
- `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py` for Guardian/Heartgate runtime enforcement.
- `docs/reference/lifecycle-trace-table.md` for transition evidence map.
- ADRs for accepted historical decisions.

## Git identity/provenance pitfall

Before committing in `/home/norty/.hermes/uacp`, check local git identity. The repo once had local config overriding commits to `Norty <norty@local>` even though the intended GitHub identity was `norty-dev <norty@nortrix.io>`.

Use:

```bash
git config --get user.name
git config --get user.email
git log --format='%h %an <%ae> | %cn <%ce> | %s' --max-count=5
```

If local config is wrong, set:

```bash
git config user.name 'norty-dev'
git config user.email 'norty@nortrix.io'
```

Do not rewrite already-pushed history without explicit Mike approval; author rewriting requires a force-push and should be treated as a separate authority decision.
