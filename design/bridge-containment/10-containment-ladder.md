---
type: decision
title: The Containment Ladder (Tier 0–3) and the Honest Trust Model
description: The read-only containment ladder — tool-native mode, ephemeral worktree, container — with an explicit split between code/OS-enforced and orchestrator-convention controls, and the as-built MVP (Tier 1+2).
tags: [containment, ladder, read-only, worktree, sandbox, fail-closed]
timestamp: 2026-06-25
edges:
  - {dst: 00-overview, rel: realizes, provenance: asserted}
  - {dst: 40-open-items, rel: relates_to, provenance: asserted}
---

# The Containment Ladder

Escalate by **how little the tool can be trusted**. Each tier declares `read_only_enforcement` in the bridge output.

| Tier | Mechanism | Real guarantee | Enforced by |
|------|-----------|----------------|-------------|
| 1 | Tool-native read-only mode (codex `--sandbox read-only`; claude `--allowedTools`; gemini/opencode/kimi plan; reasonix `review`) | Read-only **for a cooperating tool** | **codex = OS** (sandbox). The rest = tool/harness-level (convention-ish: trusts the tool to honor its flag) |
| 2 | Ephemeral detached worktree, disposed after | **Scope isolation + accidental-write containment only** | UACP (provisioning) — but **NOT a boundary**: shares `.git`, under repo root → `git push`/parent-path escape possible |
| 3 | Container: read-only repo mount + egress allowlist | **Hard** boundary (untrusted process can't write host or reach unapproved provider) | OS/container — the only tier safe against a *misbehaving* process. **Deferred.** |

## The honest split (the council's CRITICAL)

- **Code/OS-enforced today:** codex `--sandbox read-only` (Tier 1, OS), and the two callable checks UACP owns — `review_sandbox.sh` (provisioning) and `check_model_authorized.py` ([[20-model-authorization]]).
- **Convention (LLM-followed) today:** worktree placement, plan-mode for the non-codex tools, the SKIP-on-no-containment rule, declaring `read_only_enforcement` truthfully. These bind only because the orchestrator honors the contract.

A git **worktree is not a sandbox.** It limits an *accidental relative write* by a *cooperating* tool; it does not stop a buggy/malicious process (shared `.git`; `cd ../..`; absolute paths). Real read-only against an untrusted tool requires **Tier 1 OS-sandbox or Tier 3**.

## As-built MVP (2026-06-25)

- **Tier 1 + Tier 2 required**, fail-closed (`[bridges.defaults].inspect_containment = "worktree"`).
- Orchestrator provisions a disposable worktree (`skills/uacp-council/scripts/review_sandbox.sh`) at **Phase 4.0** of dispatch (`uacp-council/references/phase-4-dispatch.md`), passes it as the reviewer's cwd, tears it down at synthesis. Fails CLOSED if provisioning fails.
- For tools without a trustworthy OS read-only mode (reasonix `run`; the harness-level plan modes), Tier 2 gives **accident-containment, not hard containment** — a low-trust / high-assurance review must escalate to Tier 3 (deferred) or SKIP.

## Why not just always copy outside the repo?

Placing the sandbox in `/tmp` doesn't help: an in-process child can still write any path it has permission to (absolute paths). **No in-process directory placement is a boundary** — only OS/container isolation is. Hence Tier 3 is the real fix; Tier 2 is honest about being accident-containment.
