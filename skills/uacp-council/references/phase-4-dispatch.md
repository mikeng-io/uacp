## Phase 4: Dispatch

Dispatch branches first on **mode**, then on **tier**.

---

### Phase 4.0: Review Containment (MANDATORY for `capability_profile: inspect`)

Before dispatching **any** reviewer (every tier) for an `inspect` task type (review, analysis, research, audit, planning), the orchestrator MUST contain it per the **Review Containment** ladder in `uacp-bridge/SKILL.md` — **fail-closed**. A shelled-out reviewer CLI runs *outside* the Guardian PreToolUse hook, so read-only is not kernel-guaranteed; it is enforced at this boundary.

**Provision a disposable sandbox (Tier 2 floor) and run all reviewers against it — never the live working tree. Fail CLOSED:**

```bash
# 1. Provision the sandbox. On failure, SKIP the whole inspect dispatch — do NOT continue.
if ! SANDBOX=$(bash skills/uacp-council/scripts/review_sandbox.sh provision "{session_id}" "${scope_ref:-HEAD}"); then
  echo "containment provisioning failed → SKIP inspect dispatch"; return 1   # fail-closed (no $SANDBOX → no dispatch)
fi
# Pass $SANDBOX as each bridge's working dir (--dir / --cd / cwd). For uncommitted-diff
# review, embed the diff in the prompt (the sandbox is at the committed ref).

# 2. Per bridge, gate the resolved model BEFORE dispatch (fail-closed authorization):
for each bridge with its {resolved_model}:
  if ! python3 skills/uacp-council/scripts/check_model_authorized.py "{bridge}" "{resolved_model}"; then
    record bridge SKIPPED (skip_reason: "no authorized model"); continue   # do NOT dispatch this bridge
  fi
```

Then each bridge additionally selects its **tool-native read-only mode** (Tier 1): codex `--sandbox read-only`, claude `--allowedTools`, gemini/opencode/kimi plan mode, reasonix `review`, hermes verified read-only toolset. Each records `read_only_enforcement` and `model_authorized` in its output.

> **Limits (do not overclaim).** The worktree (Tier 2) gives **scope isolation + accidental-write containment**, not a hard boundary — it shares `.git` and is under the repo root, so a misbehaving process can still mutate the repo. Real read-only comes from the tool's OS mode (codex `--sandbox read-only`) or Tier 3 (container, deferred). For a low-trust / high-assurance review of an untrusted tool, escalate to Tier 3 or SKIP. See `uacp-bridge/SKILL.md` Review Containment.

- The configured minimum is `[bridges.defaults].inspect_containment` (default `worktree`). If provisioning fails **and** no tool-native read-only mode is verifiable for a bridge → that bridge returns **SKIPPED** (`skip_reason: "cannot guarantee read-only containment"`). Never run an `inspect` reviewer write-capable against the live tree.
- **Teardown** in Phase 7 (synthesis) after findings are collected: `bash skills/uacp-council/scripts/review_sandbox.sh teardown "{session_id}"`.

`modify` task types (implementation) are exempt — they follow `docs/lifecycle/worktree-protocol.md` for their own branch/worktree.

---

### Tier 0: Single Review

Single agent, no diversity. Use only when the scope is trivial (1 domain, no integration concerns). Allowed modes: open-ended only (not `finding-driven` — see Step 6.0).

1. Spawn one sub-agent with the domain expert's prompt (constructed using the Agent Prompt Template from `uacp-bridge`).
2. Wait for completion.
3. Skip debate (no DA, no IC).
4. Output conforms to `uacp-bridge` output schema; `debate_rounds: 0`; `diversity_sources: ["role"]`.

### Tier 1: Local Agent Council (in-runtime)

Multiple sub-agents within the current runtime — `Task` in Claude Code, `task` (lowercase) in OpenCode, `Agent` tool in Kimi, `delegate_task` in Hermes, etc.

**Roles dispatched in parallel:**

| Role | Count | Source |
|------|-------|--------|
| Domain Expert | One per domain in `council_context.domains` | `uacp-core/references/domains/` |
| Devil's Advocate | 1 | fixed role |
| Integration Checker | 1 | fixed role |

Total parallel agents = `len(domains) + 2`. If `domains > 5`, group related domains so the parallel agent count stays manageable.

**Dispatch protocol:**

1. Construct one prompt per role using the template selected in Step 6.0. For `finding-driven` mode, use the prompt templates from the Finding-Driven Mode reference (`[skills-root]/uacp-council/references/finding-driven-mode.md` and `[skills-root]/uacp-council/experts/integration-checker.md`) instead of the generic Agent Prompt Template.
2. Spawn all agents in parallel using the runtime's native sub-agent dispatch (see `uacp-bridge` for the per-runtime primitive). Detect the mechanism by availability (Claude Code Task / Agent Teams · Hermes delegate_task / Swarm · Kimi sub-agent / Swarm · MCP · CLI).
3. After all complete, run the Post-Analysis Protocol from `uacp-bridge`:
   - `intensity: quick` → 1 consolidation pass, 0 debate rounds
   - `intensity: standard` → 1 challenge + 1 response round
   - `intensity: thorough` → up to 3 rounds until convergence
4. The DA challenges findings, the IC surfaces cross-component gaps, domain experts respond/revise across rounds. Domain expansion via `cross_domain_signals` is handled per `uacp-bridge`.
5. **IC-hoist (finding-driven mode, optional):** If `council_context.ic_tier > council_context.tier`, additionally dispatch a parallel IC-only fan-out at the higher tier — see Step 6.IC below.

`diversity_sources` = `["role"]` (+ `"debate-layer"` if any debate round ran).

### Tier 2: Cross-Runtime Council

Fan out to multiple runtime adapters in parallel. Each runtime adapter runs its own internal Tier 1 council using its native dispatch.

**Step 6.2.1: Load runtime settings.**

```bash
cat .runtime-settings.json
```

If not found, run a discovery pass and present available runtimes to the user. Save to `.runtime-settings.json` with a TTL.

```json
{
  "runtimes": {
    "claude":   { "enabled": true },
    "gemini":   { "enabled": true, "model": null },
    "codex":    { "enabled": true, "model": null },
    "opencode": { "enabled": true, "models": [] },
    "kimi":     { "enabled": true, "model": null }
  },
  "reasoning_level": "medium",
  "updated": "{ISO-8601}",
  "ttl_hours": 24
}
```

See `uacp-bridge/SKILL.md` for the full settings schema.

**Step 6.2.2: Read each enabled adapter's SKILL.md.**

```
Read: [skills-root]/uacp-bridge/references/claude.md
Read: [skills-root]/uacp-bridge/references/codex.md
Read: [skills-root]/uacp-bridge/references/gemini.md
Read: [skills-root]/uacp-bridge/references/opencode.md
Read: [skills-root]/uacp-bridge/references/kimi.md
```

**Step 6.2.3: Dispatch one sub-agent per enabled adapter in parallel.**

For each enabled adapter, spawn a sub-agent (the "runtime executor") with the adapter's instructions embedded verbatim and the `runtime_input` JSON:

```json
{
  "runtime_input": {
    "session_id": "{session_id}-{runtime}",
    "scope": "{working_scope.artifact}",
    "task_description": "{constructed from intent + mode}",
    "task_type": "{council_context.task_type}",
    "mode": "{council_context.mode}",
    "domains": ["{domain1}", "{domain2}"],
    "context_summary": "{council_context.context_summary}",
    "intensity": "{council_context.intensity}",

    "findings": [],
    "fixes_applied": "",
    "original_proposal": "",
    "prior_session_id": ""
  }
}
```

When `mode == "finding-driven"`, populate `findings` / `fixes_applied` / `original_proposal` / `prior_session_id` from the council's input. For open-ended modes, leave the last four empty — runtime adapters MUST honor this by skipping the finding-driven prompt section per `uacp-bridge` Agent Prompt Template.

Each runtime executor:
- Performs the adapter's pre-flight (availability, auth, capability detection)
- Runs its own internal Tier 1 council (parallel domain experts + DA + IC)
- Returns a report conforming to the `uacp-bridge` output schema

**Step 6.2.4: Collect reports.**

Wait for all runtime executors to complete. Each returns one of:
- `COMPLETED` — include in synthesis
- `SKIPPED` — record reason, continue without
- `HALTED` — interactive: surface to user; non-interactive: auto-convert to SKIPPED and record in `auto_skipped_halted_runtimes`
- `ABORTED` — stop entire operation

If zero runtimes returned `COMPLETED` → return `status: ABORTED`, advise the user to install or configure at least one runtime adapter.

`diversity_sources` = `["role", "runtime", "toolchain"]` (+ `"model"` if any runtime ran multi-model, + `"debate-layer"` for any per-runtime debate rounds).

### Tier 3: Cross-Runtime Council with Debate

Same as Tier 2, then add a cross-runtime synthesis round.

**Step 6.3.1: Mechanical deduplication.**

After collecting all runtime reports:
- Group findings by similarity (same domain + similar title/description)
- Mark cross-runtime-confirmed findings (≥2 runtimes surfaced the same issue)
- Mark single-runtime findings (only one runtime surfaced)

**Step 6.3.2: Cross-runtime debate.**

Spawn a **Debate Coordinator** sub-agent with:
- All runtime reports
- Deduplication output
- This prompt:

```
You are the Debate Coordinator for a Tier 3 cross-runtime council.

Inputs:
- Reports from {N} runtimes: {runtime list}
- Cross-runtime-confirmed findings: {list}
- Single-runtime findings: {list}

Run a shared-bias challenge:
1. For each cross-runtime-confirmed finding, ask: "Did all runtimes agree because the
   finding is genuinely true, or because they share a blind spot (same training data,
   same prompt framing, same toolchain)?" Identify the actual independent evidence
   per runtime; downgrade findings supported only by reasoning, not evidence.
2. For each single-runtime finding: ask "Why did only this runtime surface this?
   Is it a runtime-specific blind spot of the others, or a hallucination?" Promote
   if the evidence is strong; downgrade if not.
3. Surface integration findings that emerge only from comparing runtime outputs
   (e.g., runtime A flagged X, runtime B flagged Y — combined they imply Z).
4. For intensity == thorough: run a second round challenging the first round's outputs.

Return:
{
  "confirmed_findings": [...],           // survived debate
  "downgraded_findings": [...],           // severity reduced after challenge
  "withdrawn_findings": [...],            // invalidated
  "disputed_findings": [...],             // unresolved after debate
  "integration_findings": [...],          // new findings from cross-runtime comparison
  "shared_bias_warnings": [...],          // explicit notes where bias was suspected
  "debate_rounds": 1 or 2
}
```

`diversity_sources` = `["role", "runtime", "toolchain", "debate-layer"]` (+ `"model"` if multi-model was active in any runtime).

---

### Step 6.IC: IC-Hoist (finding-driven mode only, conditional)

This sub-step runs **in addition to** the main tier dispatch when `council_context.ic_tier > council_context.tier`. It does NOT replace the regular Integration Checker — it adds a higher-tier IC pass that ONLY looks at fix-interaction.

**When to dispatch:**

The IC-hoist runs when ALL of these are true:
- `mode == "finding-driven"`
- `fixes_applied` contains 2+ fixes
- At least one signal-gated trigger fires (set via Step 3 IC-tier asymmetry rule, or by explicit input): the fixes touch shared state, concurrency primitives, security-sensitive code, persistent storage, or cross-component invariants. **Do NOT auto-hoist on fix count alone** — runtime diversity helps where evidence is underdetermined, not where the diff is concrete.

**Dispatch protocol:**

1. After the main tier dispatch completes (and produces a council report at `council_context.tier`), prepare a IC-only fan-out at `council_context.ic_tier`.
2. The IC-hoist fan-out invokes the same machinery as Tier 2 (Step 6.2) but spawns ONLY the Integration Checker role in each enabled runtime adapter, using the finding-driven IC prompt in `[skills-root]/uacp-council/experts/integration-checker.md`.
3. Each hoisted IC produces fix-interaction findings under their `outputs[]` with `type: "fix-interaction-finding"`.
4. Merge the hoisted IC outputs into the main council report's `outputs[]` (deduped by similarity), tagged with `agent: "integration-checker-hoisted"`.

**When NOT to hoist:**

If the council tier is already 2 or 3, the IC already ran across runtimes — hoisting adds no diversity. Only hoist when `tier == 1` (or when explicit `ic_tier` is set higher by the orchestrator).

Record in the council report: `ic_tier: <actual tier the IC ran at>`, distinct from the main `tier`.