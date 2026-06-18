# File-Based Round State and the Round Manifest

**Applies to:** `standard` and `thorough` intensity only. `quick` intensity is a
single in-memory pass — it writes NO manifest and NO round directories (see
`references/intensity-modes.md`).

This file is the authoritative contract for durable round state. For `standard`
and `thorough` debates the coordinator does NOT hold the finding/candidate
inventory in memory and re-embed it into every round's sub-agent prompts.
Instead, each round's output is persisted to disk, and the next round's
sub-agents **read** the prior round's files. The coordinator hands out file
**pointers** (paths), not embedded payloads.

This (a) survives a crash — the manifest + round files are the durable record;
(b) stops prompt bloat — round k's prompts carry paths, not the full inventory;
(c) makes the run auditable — every round's raw participant output and assembled
inventory is on disk.

## File Layout

All paths are under the existing per-run directory `.uacp/debate/{review_id}/`:

```
.uacp/debate/{review_id}/
├── manifest.json                              # durable round state (replaces coordinator-memory)
├── round-1/
│   ├── participants/{participant_id}.json     # each sub-agent's raw Phase-1 output
│   └── inventory.json                         # assembled findings F001… (or candidates P001… in brainstorm/design mode)
├── round-2/
│   ├── challenges.json                        # each entry references prior finding/candidate ids
│   └── inventory.json                         # updated inventory + states/maturity
└── …
└── {YYYYMMDD-HHMMSS}-debate-{review_id}.json   # final roll-up (JSON; see artifact-output.md)
└── {YYYYMMDD-HHMMSS}-debate-{review_id}.md     # final roll-up (Markdown; see artifact-output.md)
```

The final timestamped roll-up artifacts are unchanged from the existing
artifact-output contract — they are a roll-up OF the manifest (see
`references/artifact-output.md`).

## manifest.json Schema

`schema_version` is `"1.0"`. The manifest is written via the runtime's governed
writer / `Write`; it is rewritten (not appended) at the end of each round.

```json
{
  "schema_version": "1.0",
  "review_id": "...",
  "mode": "review|audit|brainstorm|design|research|synthesis",
  "intensity": "standard|thorough",
  "scope": "...",
  "domains": [],
  "max_rounds": 3,
  "current_round": 2,
  "status": "running|complete",
  "rounds": [
    {"round": 1, "dir": "round-1/", "participant_files": ["round-1/participants/security-expert.json"], "inventory_file": "round-1/inventory.json"},
    {"round": 2, "dir": "round-2/", "challenges_file": "round-2/challenges.json", "inventory_file": "round-2/inventory.json"}
  ],
  "items": {
    "F001": {"kind": "finding", "state": "confirmed", "first_round": 1, "lineage": {"derived_from": [], "supersedes": [], "merged_from": []}},
    "F003": {"kind": "finding", "state": "discovered", "first_round": 2, "lineage": {"derived_from": ["F001"], "supersedes": [], "merged_from": []}},
    "P001": {"kind": "candidate", "maturity": "refined", "first_round": 1, "lineage": {"derived_from": [], "supersedes": [], "merged_from": []}}
  },
  "final_verdict": null
}
```

### Field notes

- `rounds[]` — one entry per completed round. Round 1 (Phase 1 discovery) carries
  `participant_files` + `inventory_file`. Round k≥2 (Phase 3 challenge) carries
  `challenges_file` + `inventory_file`. Paths are relative to
  `.uacp/debate/{review_id}/`.
- `current_round` — the highest round persisted so far.
- `status` — `running` while rounds are in flight; `complete` once the final
  roll-up is written.
- `final_verdict` — `null` until Phase 5; then one of `PASS` / `CONCERNS` /
  `FAIL` (review/audit/research/synthesis modes). Mirrors the JSON roll-up's
  `final_verdict`.

### `items` — states AND lineage

`items` is keyed by item id and carries BOTH a state/maturity field AND lineage.
Reuse the EXISTING vocabulary — do not invent new terms:

- **Findings** (`kind: "finding"`, ids `F001…`, in review/audit/research/synthesis):
  carry `state` ∈ `confirmed | withdrawn | disputed | merged | discovered`
  (the Phase-4 finding-state vocabulary).
- **Candidates** (`kind: "candidate"`, ids `P001…`, in brainstorm/design):
  carry `maturity` ∈ `seed | sketched | refined | candidate | accepted |
  rejected | parked` (the Brainstorm Proposal Object maturity vocabulary from
  `references/packet-contract.md`).
- **`lineage`** — present on every item; captures how an item evolves across
  rounds (it is what makes brainstorm/design candidate evolution legible):
  - `derived_from` — ids this item was discovered/derived from (e.g. a Phase-3
    cross-domain discovery derived from `F001`).
  - `supersedes` — ids this item replaces.
  - `merged_from` — ids merged INTO this item during Phase-4 reconciliation.
- `first_round` — the round in which the item first appeared.

The finding-state vocabulary and the Brainstorm Proposal Object
lineage/maturity both originate in `references/packet-contract.md`; keep them
consistent with it.

## Round-Loop State-Carry Rules

The coordinator still orchestrates — it decides who runs, the ordering, and the
state updates. What changes is that it hands out **paths**, not payloads.

### Round 1 (Phase 1 — independent investigation)

- Sub-agents get **no priors** — `context_policy: minimal-non-leading` so
  independent discovery is preserved (no prior-round file pointers in round 1).
- Each sub-agent's raw output is written to
  `round-1/participants/{participant_id}.json`.
- The coordinator assembles the findings/candidates into `round-1/inventory.json`
  (assigning ids F001…/P001…).
- The coordinator WRITES `manifest.json`: `current_round: 1`, `status: running`,
  the `rounds[0]` entry, and an `items` entry per assembled item
  (`state: discovered` for findings / starting `maturity` for candidates;
  `first_round: 1`; empty lineage).

### Round k (Phase 3 — challenge, k ≥ 2)

1. **Persist round k-1** — ensure `round-{k-1}/inventory.json` reflects the
   latest states/maturity (it does, from the prior iteration).
2. **Spawn each sub-agent with file POINTERS, not embedded payloads.** The
   prompt says, in effect: "Read `round-{k-1}/inventory.json` for the current
   inventory, and read the challenges targeting you in
   `round-{k}/challenges.json`." The coordinator writes `round-{k}/challenges.json`
   first (each challenge entry references the prior finding/candidate id it
   targets), then points each sub-agent at it.
3. **Sub-agents read** the pointed-at files and respond (defense, withdrawal,
   corroboration, cross-challenge, discovery, merge-proposal).
4. **Collect** responses into `round-{k}/` and write `round-{k}/inventory.json`
   (the updated inventory + states/maturity).
5. **Update the manifest** — append the `rounds[k-1]` entry, bump
   `current_round` to `k`, and update `items`: new states/maturity, any new
   items (e.g. a discovery with `first_round: k` and `lineage.derived_from`), and
   merges (`merged_from` on the survivor, `state: merged` on the absorbed).

### Convergence / termination

Repeat round k up to `max_rounds`, or stop early on convergence (no new valid
challenges, no state changes). Then run Phase 5, write the final timestamped
roll-up (JSON + Markdown per `references/artifact-output.md`), set the manifest's
`final_verdict`, and set `status: complete`.

## Optional Shared Live Session

If the runtime offers a shared live multi-agent session and it is used (`mode:
shared_session`), continuity is carried live in that session. The per-round files
and the manifest are STILL written — files are the durable audit record
regardless of mechanism. The only difference is whether sub-agents obtain
continuity by **reading files** (the default) or by **shared live memory**
(optional); either way the files exist after each round.

## Carry-Over Invariants

- The anti-fabrication rule holds: every recorded participant message
  (`round-k/participants/*.json`, `round-k/challenges.json` responses, and the
  final roll-up `messages[]`) must correspond to a real sub-agent or
  shared-session message that actually happened.
- The finding-state / maturity vocabulary is the existing one (above).
- The final JSON/Markdown roll-up carries over unchanged — it becomes a roll-up
  of the manifest (see `references/artifact-output.md`).
