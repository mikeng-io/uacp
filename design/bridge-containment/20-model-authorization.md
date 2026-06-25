---
type: decision
title: Fail-Closed Model Authorization
description: Constraining which provider/model a bridge may use — distinct from model validation — via a callable allowlist gate, motivated by an unauthorized minimax-m3-via-opencode usage.
tags: [model-authorization, allowlist, fail-closed, opencode, multi-provider]
timestamp: 2026-06-25
edges:
  - {dst: 00-overview, rel: realizes, provenance: asserted}
  - {dst: 30-evidence-capture, rel: relates_to, provenance: asserted}
---

# Fail-Closed Model Authorization

## Motivation

Nothing constrained *which model* a bridge used. Multi-provider bridges (opencode, hermes) can reach any configured provider — including unapproved ones. This surfaced as an observed `minimax-m3`-via-opencode usage that was a **rejected** routing swap (the approved reviewer is `opencode-go/mimo-v2.5`). Validation ("does the model exist?") is not authorization ("are we *allowed* to use it?").

## Design

- `[bridges.defaults].enforce_model_allowlist = true` — global fail-closed toggle.
- **Single-provider bridges** (claude/codex/gemini/kimi/reasonix): the model resolved from `[models.tier_mappings.<bridge>]` is implicitly authorized (the tier mapping already pins it).
- **Multi-provider bridges** (opencode, hermes): the selected model MUST be in `[bridges.<bridge>].allowed_models`. Empty list under enforcement → the bridge **SKIPs** (`skip_reason: "no authorized model"`). opencode is pinned to `mimo-v2.5`; `minimax-m3` is therefore barred.
- Bridges record `model_authorized: true|false` in output.

## Real teeth (not prose)

The gate is a **callable check**, `skills/uacp-council/scripts/check_model_authorized.py <bridge> <model>` → exit 0 authorized, exit 3 not (SKIP), exit 2 usage. It reads `config/uacp.toml` directly. Wired into Phase 4.0 dispatch (per-bridge, before dispatch) and into `opencode.md` (no proceeding on an opaque default). Tested: `minimax-m3` → exit 3; `mimo-v2.5` → exit 0; empty hermes allowlist → exit 3; gate-disabled → exit 0.

## Limit

Like all bridge controls, the gate binds only when the orchestrator *calls* it. The hard version is **Tier 3 egress allowlist** ([[10-containment-ladder]]): if the reviewer's network can only reach the approved provider endpoint, an unapproved model is *physically* unreachable — code-enforced, not convention. Until Tier 3, this gate + the orchestrator contract is the floor.
