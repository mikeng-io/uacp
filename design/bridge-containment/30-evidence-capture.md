---
type: analysis
title: Review Evidence Capture — the Universal Fidelity Ladder
description: Capturing the reviewer's traversal (not just its conclusions) as provenanced evidence, via a capability ladder owned at UACP's boundary, with evidence_fidelity feeding how the gate weights the proof.
tags: [evidence, coverage, trajectory, fidelity, acp, proof]
timestamp: 2026-06-25
edges:
  - {dst: 00-overview, rel: extends, provenance: asserted}
  - {dst: 40-open-items, rel: relates_to, provenance: asserted}
---

# Review Evidence Capture

## The problem

Keeping only a reviewer's **output** (a few findings) discards the **traversal** — the reasoning, what files it actually opened, the grounding. A bare findings-JSON is an *assertion*; proof must be **re-derivable** (`[[uacp-core-principle-comprehend-measure-serialize]]`: "trustless → re-derivable"). Findings are the index; the transcript + coverage are the evidence body. The current bridge artifact format captures conclusions, not traversal — same gap.

## The universal move

Don't depend on the agent to expose its trail (per-runtime capability roulette). **Capture at a boundary UACP owns** — the same principle as containment ([[00-overview]]). This yields a fidelity ladder; each bridge fills one canonical evidence bundle (`{files_examined, commands_run, findings_with_grounding_pointers, raw_transcript_ref, evidence_fidelity}`) at the highest tier it can reach:

| Tier | Mechanism | Universal? | Coverage trust |
|------|-----------|-----------|----------------|
| 0 | stdout + **self-reported** coverage ("list files you examined") | any text agent | untrusted |
| 1 | sandbox / FS audit on the provisioned worktree (what was opened/changed) | any FS-touching agent | **verified** |
| 2 | UACP serves the agent's tools over **MCP**, logs every call | any MCP agent | **verified** |
| 3 | agent's native rich transcript (codex `--json`, claude stream-json, **reasonix/hermes session JSONL + tool_stats**) | per-runtime → normalize | verified + reasoning |

`evidence_fidelity` is not just metadata — it **weights the proof**: an observed-coverage finding (Tier 1/2) outranks a self-reported one (Tier 0). Capture-for-audit (cheap, on disk, referenced) is separate from re-inject-into-context (expensive) — keep the full transcript addressable; flow only findings + coverage into synthesis.

## Reference: ACP + OpenAB

ACP (Agent Client Protocol, stdio JSON-RPC) is emerging as the **universal transport** — codex/gemini/opencode/hermes/reasonix all expose `acp` modes. `[[openab-acp-broker-reference]]` (Open Agent Broker, Rust, MIT) demonstrates ACP-as-lingua-franca *and* sandbox-only execution (read-only root FS) across the same agent roster — a reference for both a future UACP **ACP-universal bridge transport** and Tier-3 per-agent container images. Hermes's trajectory JSONL + `tool_stats` is the natural Tier-3 evidence proof-of-concept.

## Status

Parked (not built). The MVP containment work ([[10-containment-ladder]]) is the prerequisite boundary; evidence capture rides the same wrapper.
