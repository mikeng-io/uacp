---
type: design
title: "Injection + bootstrap mechanism (Slice 1)"
description: "The injection-hook extension that carries PRINCIPLE.md on the neutral session-start surface (fenced, untrusted), and the uacp-bootstrap procedure (comprehend-implementation -> propose -> agree -> serialize + a governed uacp.principle_agreement node). Grounded on the real hook; records the settled build decisions."
tags: [grounded-governance, injection, bootstrap, hook, principle-agreement, design]
timestamp: 2026-08-17
edges: [{dst: 01-principle-md, rel: extends, provenance: asserted}]
---
# 03 — Injection + bootstrap mechanism

Node 03 of `grounded-governance`. Consumes node 01 (what PRINCIPLE.md is) and the agreed `PRINCIPLE.md`. Grounded on the **real** injection code, not an assumed one. Design altitude — build decisions are surfaced, not pre-resolved.

## 1. As-is (grounded — the real mechanism)

The runtime already has exactly the split the axes need:

- **SessionStart hook** `runtime-adapters/claude/inject_uacp_md.py` (wired in `runtime-adapters/claude/hooks.json`). It:
  - reads the framework payload `UACP.md` from the **plugin root** (`_plugin_root()`, `:51-56`, `:235`);
  - resolves a **separate workspace root** by walking up from the SessionStart payload `cwd` to the nearest ancestor containing `.uacp/` (`_workspace_root`, `:79-104`) — the *governed project* (ROOT), which may differ from the plugin (HOME);
  - **already appends a second, workspace-sourced section** — the active-handoffs summary from `<ws_root>/.uacp/handoffs/_index.yaml` (`_active_handoffs_section`, `:200-222`), with untrusted committed fields **length-clamped** (`:225-229`) and the whole hook **fail-open** (`:19-25`, a cognition nudge, never a gate).
- `UACP.md` is the plugin's **runtime-neutral cognition payload**; its own header notes other runtimes (Kimi, opencode) "need their own session-start hook to inject it" — the injection is per-platform, the payload is neutral.

The hook is already a HOME-vs-ROOT machine, and it already knows how to append a workspace-sourced section. That is the whole mechanism.

## 2. One neutral mechanism; the two axes are two values of `ws_root`

**Correction (2026-08-17): the injection surface is `UACP.md`, not `CLAUDE.md`.** `CLAUDE.md` is platform-specific (Claude Code); Kimi/opencode use their own native files. Hanging the principal off `CLAUDE.md` platform-locks a UACP feature. The runtime-neutral surface is the injected `UACP.md` payload — each platform supplies its own session-start hook.

So there is **one mechanism**: the session-start hook appends a labelled **"Project Principle"** section — read from `<ws_root>/PRINCIPLE.md` — to the injected `UACP.md` payload, exactly paralleling the existing handoffs section (same read-from-workspace, same clamp, same fail-open). The framework payload (`UACP.md`, plugin-sourced) and the project telos (`PRINCIPLE.md`, workspace-sourced) ride as **two clearly-labelled sections**, so the two principals never mix (your "don't mix" constraint, enforced by labelling + separate sources).

The **two axes are two values of `ws_root`**, not two mechanisms:

- **Axis 1 — developing a repo directly** (UACP itself, here): `ws_root == plugin_root`, so the hook appends the repo's *own* `PRINCIPLE.md`.
- **Axis 2 — installed UACP governing a foreign project**: `ws_root != plugin_root`, so the hook appends *that project's* `PRINCIPLE.md`.

Same code, correct principal *by construction* — the `ws_root` walk (`:79-104`) already resolves which project you are actually in. This is why it is neutral and why the axes cannot cross-contaminate. (The "double-injection" concern from the CLAUDE.md draft is gone — there is only one path.)

## 3. Settled decisions (2026-08-17) + the trade

**The trade.** Unifying on `UACP.md` means principal injection **depends on the UACP hook being active** — no plugin/hook, no injected principal (on any platform). The `CLAUDE.md` static include I first proposed would have survived a dropped plugin, but only for Claude Code — platform-locking rejected. The principal is a UACP feature; it rides UACP's neutral surface. *Consequence:* each non-Claude runtime needs its session-start hook before it gets the principal — already a flagged follow-up in `UACP.md`'s header.

**Settled:**

1. **Inject the WHOLE `PRINCIPLE.md`** as the labelled section (engineer's call, over the core-only lean) — the complete telos (statement + invariants + frontier + provenance) is standing context every session. *Consequence made explicit:* since the whole file — possibly from a **foreign, untrusted** repo — is injected, the section is **length-capped, sanitized, and fail-open** (the handoffs clamp, scaled to file size), and `PRINCIPLE.md` is kept **concise by convention** so the per-session cost and injection surface stay small.
2. **Drop the platform-specific static include entirely.** One neutral path (the `UACP.md` hook). No second source, no drift, no double-inject. Plugin/hook reliability (a principal vanishing when the plugin drops) is treated as **its own concern**, not papered over with a platform-locked file.
3. *(lean, still open — see §6)* **Always-on vs run-scoped** injection: leaning always-on (the telos is a standing orientation, not run-scoped).

## 4. Bootstrap mechanism (net-new — UACP has no init skill)

Verified: no init/bootstrap skill exists. Bootstrap is where `PRINCIPLE.md` is *produced* for a project that lacks one. It is a **generalization of what this session did by hand**:

- **Trigger (settled): verb + auto-surface.** A `uacp-bootstrap` skill verb runs it on demand; *additionally*, a governed session that finds `<ws_root>/.uacp/` present but `<ws_root>/PRINCIPLE.md` absent surfaces a gentle **advisory** prompt (a cheap file check). Discoverable without forcing — it does **not** block work (that stronger option was declined).
- **Procedure (CMS at the project grain):**
  1. **comprehend** the *implementation* — the N-reader sweep (entrypoints/kernel, config-as-wired, tests, git trajectory), implementation-first, docs treated as claims. (This session's 4-reader sweep is the reference implementation.)
  2. **measure** → a proposed principle: statement + sacred invariants + frontier/forward-vector, each grounded in a mechanism.
  3. **propose** to the engineer; they **confirm/correct** and supply the **forward vector** (the one thing the code can't give). This is the agreement gate.
  4. **serialize** → write `PRINCIPLE.md` at the project root (`status: agreed`) **and** record the agreement as a **first-class governed manifest node (settled)** — a new `principle_agreement` entity kind written via `uacp_entity_write`, carrying who agreed, when, from what evidence (the derivation record), and which version. This makes agreement a **queryable, auditable governed act**, not a frontmatter flag.
- **Plane boundary.** `PRINCIPLE.md` is the **project's own file** (work-product plane, project root — like its `AGENTS.md`), *not* `.uacp/` governed state, so it is a normal user-confirmed write. But the **agreement is a first-class governed node** — which resolves node-01 **Q4 (agreement authority)**: agreement is a provenanced act, not a vibe. (New governed `kind` ⇒ small kernel surface: a schema + entity-writer registration — flagged for the build.)
- **Re-derivation / staleness (node-01 Q2).** Bootstrap is re-runnable. A drift between the *current* implementation and the *agreed* principle is a **finding** (same reconcile step). `PRINCIPLE.md` carries `status` + agreed-at; a re-derivation proposes a new version that **requires re-agreement**.

## 5. Scope of this node

- **In:** the single neutral injection path (hook appends `<ws_root>/PRINCIPLE.md` to the `UACP.md` payload) grounded on the real hook; the bootstrap procedure, trigger, plane boundary, and provenance-of-agreement.
- **Deferred:** the N-reader sweep's *scale rule* for small projects; whether bootstrap auto-prompts or is verb-only; which governed writer records the agreement (`uacp_entity_write` with a new `principle_agreement` kind, or a doc); the per-runtime session-start hooks (Kimi/opencode) needed for axis-neutral coverage.

## 6. Decision status

**Settled 2026-08-17:** inject **whole `PRINCIPLE.md`** (capped/sanitized/fail-open); bootstrap trigger = **verb + advisory auto-surface**; agreement = **first-class `principle_agreement` governed node**; platform static-include belt = **dropped** (one neutral path).

**Still open for red-pen:**
1. **Always-on vs run-scoped injection** — append the project principal on *every* session in the tree, or only when a governed run is active? (Leaning always-on.)
2. **N-reader scale rule** — the derivation sweep is token-heavy; a small project may warrant a single-pass comprehension. What sizes the sweep?
3. **Per-runtime hooks** — Kimi/opencode need their own session-start hook for axis-neutral coverage (out of this node's scope; tracked in `UACP.md`'s header).
