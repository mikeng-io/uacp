---
type: analysis
title: Open Items & Follow-ups
description: What remains after the containment MVP — the hard tier (Tier 3 container + egress), the ACP-universal bridge transport, synthesis-time enforcement, and evidence capture.
tags: [open-items, tier-3, acp, follow-up]
timestamp: 2026-06-25
edges:
  - {dst: 00-overview, rel: relates_to, provenance: asserted}
---

# Open Items

Built (MVP): Tier 1+2 containment, `review_sandbox.sh`, Phase 4.0 dispatch step, fail-closed model-auth gate (`check_model_authorized.py`), older-bridge sweep, honest trust model. Open:

1. **Tier 3 container + egress allowlist (the hard boundary).** Build per-agent Docker images (mine `[[openab-acp-broker-reference]]`'s `Dockerfile.*`), a read-only repo mount, and an egress-allowlist network so an untrusted reviewer cannot write the host or reach an unapproved provider. This is the only tier safe against a misbehaving process, and it closes the model-authorization gap physically. Until built, `inspect_containment="container"` must not be claimed; orchestrator falls back to the worktree floor.

2. **Synthesis-time enforcement (close the convention gap).** Today the orchestrator *should* reject an `inspect` report with `read_only_enforcement: none` or `model_authorized: false`, and *should* call the gates. Make this a callable check in Phase 7 synthesis (reject non-conforming bridge reports) so it is code-enforced, not prose.

3. **ACP-universal bridge transport.** codex/gemini/opencode/hermes/reasonix all expose `acp` modes; collapsing N bespoke CLI bridges into one ACP adapter would shrink the contract and standardize containment + evidence capture. Research-level; see `[[openab-acp-broker-reference]]`.

4. **Review evidence capture** ([[30-evidence-capture]]): implement the fidelity ladder (Tier 1 FS-audit coverage from the worktree; Tier 3 native-transcript normalization). Rides the same wrapper as containment.

5. **`review_sandbox.sh` robustness (MEDIUM, from council):** provision reuses an existing worktree without re-checking the requested ref; concurrent dispatch with the same `session_id` shares one sandbox (caller contract: unique session_id per concurrent review). Teardown's `rm -rf` fallback is guarded by id-sanitization but remains a footgun. Harden if concurrent reviews become common.
