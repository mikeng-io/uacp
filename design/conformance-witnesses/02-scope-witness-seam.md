---
type: decision
title: "Scope-witness seam — authored code_refs, gate-invoked derivation, advisory-first"
description: "Decides the binding/delivery seam for the codeflair scope witness: the agent authors code_refs (the falsifiable claim); the GATE derives the independent account by exec'ing the codeflair CLI at measure time (process boundary — git-parity, no import); code compares. Rejects the file-handoff seam as agent-forgeable. Advisory-first with measurable promotion criteria. Grounded in the #83 spike, its adversarial review, and the seam review that killed the artifact handoff."
tags: [conformance, witness, seam, codeflair, decision, scope]
timestamp: 2026-07-03
edges:
  - {dst: 01-witness-scoreboard, rel: depends_on, provenance: asserted}
---
# 02 — The scope-witness seam (decision)

## The question

How does codeflair's account of a change reach the scope gate (issue #84),
under the constraint that killed Shim-B: the code plane must not enter the
kernel. Candidate claims: **A inferred** (witness derives the "declared"
touch-set itself) vs **B authored `code_refs`** (agent declares; witness
derives; code compares). Candidate deliveries: **produced artifact** (a file
the gate reads) vs **gate-invoked derivation** (the gate execs the codeflair
CLI at measure time and consumes its output directly).

## Decision

**B authored `code_refs` × gate-invoked derivation, advisory-first.**

*Claim side* — Option A collapses claim and derivation into one actor
(whoever infers the boundary also grades it): self-attestation one level up,
and an inferred boundary is not falsifiable. Option B keeps the roles apart
and gives the governance soul its object: correct-but-undeclared work is
*ungoverned*, and the remedy is re-declaring `code_refs`, never silently
widening them.

*Delivery side* — the produced-artifact handoff was REJECTED by adversarial
review: the gate would read a file at a path the agent's own governed writer
can target (`uacp_artifact_write` accepts arbitrary non-manifest YAML under
`verification/` — `governed_handlers.py:492-541`), and `generated_by:
codeflair` is a plaintext string, not provenance. EXECUTE could hand-author a
friendly witness and the "deterministic witness" would still be
self-attested. Instead the gate **derives** the account itself: at sweep time
it execs the codeflair CLI (subprocess, stdout) exactly as the `SC_DIFF_*`
half execs git via `engines/io/gitio.py` (built on `feat/scope-verify-witness`,
PR pending — the two halves land together in #85). The working tree and
the symbol graph are the ground truth; no agent-writable file sits between
witness and gate. (If the gate chooses to serialize the result under
`verification/` as an evidence record, that is a gate-written convenience
copy — never the input.)

**Executable trust root** (cross-provider review finding): codeflair source
lives inside the very repo the witnessed agent edits, so "exec the CLI" must
not mean "exec whatever the run's worktree contains" — a tampered witness
would be one work-product edit away, and ADR-0019 deliberately does not
raw-block work-product writes. The wrapper resolves the executable from
**the kernel-default config ONLY** (`config/uacp.toml`, `[witness].codeflair_cli`)
— the `.uacp/config.toml` workspace override is explicitly **ignored** for the
`[witness]` table. The adversarial council round proved the override-wins merge
would hand the *pointer* to the witnessed agent: a workspace
`[witness].codeflair_cli` naming a friendly script beats any safe operator
value, and Guardian's raw-write block on `.uacp/` is a deployment-specific
guarantor this seam must not lean on (it vanishes on hookless runtimes).
argv[0] is resolved to an absolute path before exec, **rejected if it
resolves under the run workspace**, and the resolved executable is recorded
in the violation detail. Advisory-phase residual (an operator pointing kernel
config at a mutable checkout) is documented; promotion criterion 5 below pins
it.

**CF-D9, stated precisely**: the kernel must never *import or link* the code
plane (that was Shim-B's sin — codeflair types and calls inside kernel code).
A subprocess exec across a process boundary does not put codeflair in the
kernel: the kernel gains only an *optional external prober*, with the same
doctrine as git — prober absent or failing → an UNAVAILABLE advisory, never a
crash, never a silent pass.

## The witness contract (LOCKED for the #85 build)

- **Claim**: optional `code_refs` on the scope artifact. Each ref is
  `{file, name}` where `file` is the repo-root-relative POSIX path exactly as
  the codeflair store's `file` column records it, and `name` is the
  class-qualified symbol name (`Violation`, `Heartgate.validate_closure`).
  Resolution is by (file, name) lookup — never bare-substring seeding (spike
  pitfall 1: `validate` → 508 silent candidates). `code_refs` requires
  **minItems 1**: an empty list writes as a schema error, so "declared
  empty" cannot masquerade as a claim — absence is the ONLY no-claim state,
  which is what makes promotion criterion 4's absence-escalation unambiguous.
  **Schema prerequisite** (cross-provider review): the `uacp.scope`
  write-time schema is CLOSED — unknown keys hard-fail at `uacp_entity_write`
  (`engines/domain/schema.py`; asserted by `test_schema.py`). The #85 build
  MUST add optional `code_refs` to that canonical schema + the `Scope` read
  model + write-path tests, or the claim is literally unwritable.
- **Touched-set derivation (pinned)**: the changed-file set uses the SAME
  baseline as the git half — uncommitted changes (`git status --porcelain`,
  untracked included, ignored excluded) ∪ committed-on-branch changes
  (`merge-base(default branch, HEAD)..HEAD`) — so a run that commits during
  EXECUTE (permitted by the worktree protocol) is still fully observed.
  v1 granularity is **file-level**: `symbols_touched` = all symbols the store
  records in the changed files. This is explicitly coarse (an edit to one
  function flags its file-siblings' cascade too) and is acceptable only while
  advisory; hunk/span-level touch derivation is a **pre-promotion
  requirement**, and the false-positive target below is measured against the
  hunk-level witness, not this v1.
- **Derivation — the witness reports FACTS ONLY; the gate computes every
  verdict** (the locked pattern from 00: witness *derives*, **code
  compares** — a CLI that returned "undeclared"/"over-declared" sets would
  move the comparison into the witness, making a codeflair coverage bug
  invisible and unrecomputable kernel-side). The engine calls a new io
  capability (`engines/io/` subprocess wrapper, gitio doctrine: never raises,
  typed result) that execs `codeflair witness --repo <workspace>
  [--code-ref file:name ...]` — a NEW subcommand the #85 build adds to the
  codeflair CLI (today it ships only `index`/`query`/`mcp`), composing
  existing primitives (`Store.symbols_in_file`, `expand` at hop 1, the index
  ladder) — and parses **stdout JSON** of facts:

  ```yaml
  graph_stamp:
    commit: <HEAD the index was built at>
    tree_token: <content token of the working tree at witness time>
  ingestion: scip                    # floor of the TOUCHED symbols' own sources —
                                     # a store-global floor is a laundering vector
                                     # (scip elsewhere ≠ scip on this change);
                                     # gate rejects weaker floors
  symbols_touched: [{file, name}, ...]      # symbols in the ACTUAL diff's files
  neighborhood:                      # hop-1 edges from every touched symbol
    - {src: {file, name}, dst: {file, name}, reason}   # reason ∈ {calls, references, defines}
  declared:                          # the claim echoed back with resolution facts
    - {file, name, resolved: <bool>} # resolved via store (file,name) lookup;
                                     # when resolved, `name` echoes the CANONICAL
                                     # derived symbol name (e.g. Heartgate.validate),
                                     # not the authored string — coverage compares
                                     # canonical-to-canonical, so an unqualified
                                     # authored name is a resolution convenience,
                                     # never a coverage mismatch
  unresolved_touched:                # touched but unresolvable (new/unparseable code)
    - {file, name}                   # file always known (it came from the diff);
                                     # name is NULLABLE — an unparseable/unsupported
                                     # changed file may yield zero symbol rows, and it
                                     # must still be serializable at file level rather
                                     # than dropped (silent fail-open forbidden)
  ```

- **Coverage, defined here** (not in codeflair): a touched symbol is
  *covered* ⇔ it is an exact declared ref ∨ it is hop-1-connected (any
  `reason`) to a resolved declared ref. The gate computes:
  `undeclared_cascade = symbols_touched ∖ covered`;
  `over_declared = resolved declared ∖ (symbols_touched ∪
  hop1(symbols_touched))`; `unresolved_declared = declared where resolved ==
  false`. Both sides of the wire are testable against this paragraph alone.
- **Freshness is by construction, not by stamp comparison**: `witness`
  (re)indexes the run's **current working tree** — dirty state included —
  immediately before deriving. A bare `graph_stamp.commit == HEAD` check is
  explicitly WRONG (it passes precisely when the index is most stale relative
  to the uncommitted diff); `tree_token` is what records what was actually
  indexed. Newly-added symbols therefore resolve (they are in the tree that
  was indexed); only symbols the ingester cannot parse land in
  `unresolved_touched`.
- **Cost / reuse / availability envelope (pinned)**: the io wrapper's
  timeout is **120s** (gitio's 10s doctrine would kill a legitimate ~18s
  index build at 590 files; 120s gives headroom for larger repos while still
  bounding the sweep). Derivations are **reused keyed on (`tree_token`,
  normalized `code_refs`)** — NOT the token alone: the stdout is a function of
  both the tree and the claim (the `declared` echo), so a retry that changed
  only `code_refs` on an unchanged tree MUST re-derive or the gate would
  compute coverage against a stale declaration. An unchanged (token, claim)
  pair means an unchanged answer, so a retried finalize does not pay N×index
  for nothing. The kernel-side token approximation MUST be
  **content-sensitive** (changed files' contents hashed, `-uall`): a token
  built from HEAD + status lines alone is byte-identical across a
  content-only edit to an already-dirty file and would serve stale facts —
  the council round proved this empirically. A **transient** failure
  (timeout) is retried **once** before reporting unavailable; deterministic
  failures (malformed output, non-zero exit) fail immediately — retrying
  them buys latency, not signal.
- **Declared mutation exemption**: unlike git observation, `codeflair
  witness` WRITES its index cache (`.codeflair/index.db` — per-worktree,
  gitignored, so it never appears in `changed_files`). This is a gate-owned
  cache, exempted here explicitly from the engine's "never mutates anything"
  contract (the engine still never mutates *governed or work-product state*).
  A witness run derives from a **fresh store** (delete-and-rebuild), never an
  incrementally-reused one: the ingest ladder appends rows without clearing a
  prior build, so a reused store can retain deleted symbols/edges and
  manufacture false hop-1 coverage (cross-provider council finding).
  Concurrent sweeps in one worktree serialize on SQLite (busy-timeout); a
  lost race degrades to re-derivation, never to a wrong answer.
- **Environment discipline**: the wrapper execs both git and the witness with
  `GIT_*` and `PYTHON*` variables stripped from the child environment — the
  "independent" derivation must not be steerable through inherited env
  (`GIT_DIR`, `GIT_CONFIG_*`, `PYTHONPATH` injection).
- **Gate side** (extends `engines/scope_conformance.py`; all advisory
  `severity: warn` in v1):
  - `undeclared_cascade` non-empty → `SC_UNDECLARED_CASCADE` (under-declaration:
    the boundedness catch);
  - `over_declared` non-empty → `SC_SCOPE_OVERDECLARED` (a claim ⊇ the graph
    makes every cascade "covered" — `write_paths: ["**"]` in symbol clothing;
    the claim must be a superset AND near-minimal);
  - `unresolved_declared` non-empty → `SC_WITNESS_UNRESOLVED_CLAIM` (a bogus
    ref must never silently count as coverage);
  - `unresolved_touched` non-empty → `SC_WITNESS_UNRESOLVED_TOUCHED`, fired
    **unconditionally** (visible-but-not-blocking; silent fail-open
    forbidden, hard fail-closed would flag every unparseable artifact).
    Surfacing it only inside another advisory's detail is WRONG — a diff
    whose only changed files are unparseable produces no cascade and would
    vanish entirely (council finding). Changed files in languages the index
    does not cover at all appear here too, file-level ({file, name: null}) —
    "changed code the witness cannot reason about" must be visible;
  - CLI absent / non-zero / garbled stdout / timed out after the one retry →
    `SC_WITNESS_UNAVAILABLE` (fail-closed visibility, gitio parity);
  - no `code_refs` declared → no-op while advisory (the claim is opt-in until
    promotion).
- **Signal discipline** (spike §3/§6): membership and **hop-1 connectivity**
  only. Closure-size magnitude is hub-dominated and inverts the true ranking
  (`run_all_engines` closure 267 vs `Violation` 123 despite 4-vs-65 direct
  callers) — it must not appear in any threshold. This finding also reshapes
  prevention-at-PLAN (#86): "claimed boundary ⊉ dependency-closure" cannot be
  built as written; it needs hop-1 membership, benchmarked in the direction
  it actually uses, only after this seam proves itself.

## Enforce vs advise

**Advisory-first** (`severity: warn`), the Oracle precedent. The spike's
verdict is *trust-provisional, single-repo Python*: it validated magnitude
separation on six curated symbols, not the containment operation itself.
Promotion to blocking is a separate, explicit decision gated on ALL of:

1. the end-to-end containment proof in the #85 build (declared `code_refs` vs
   a real diff's derived set) shows no false positive on real changes;
2. ≥10 real (or dogfood) runs with zero false-positive advisories at closure,
   measured over the population the witness can actually witness (edits to
   parseable, resolvable symbols — `unresolved_touched` entries are outside
   that population and are not counted as false positives). Runs where the
   witness resolved little or nothing of the touched set do NOT count toward
   the ≥10 — otherwise a starved witness (unparseable files, timeouts)
   trivially "earns" promotion without ever witnessing (council finding);
3. the multi-repo / multi-language bench the spike did not run (Trustless;
   scip-go or scip-typescript exercised on real symbols);
4. at promotion, absence itself escalates: missing `code_refs`, missing
   codeflair, or `SC_WITNESS_UNAVAILABLE` become blocking for runs whose
   scope declares code — a run must not escape the witness by never feeding
   it (the advisory-phase no-op is explicitly temporary). Blocking applies to
   *unavailable after the retried derivation* (the envelope above), never to
   a single timeout — a repo slow to index must degrade to a retry, not to a
   run that can never close;
5. the executable trust root is pinned before any blocking: the configured
   CLI must resolve outside every run workspace (installed artifact or pinned
   checkout), with its resolution recorded in evidence — never a
   worktree-relative or run-mutable path;
6. hunk/span-level touch derivation replaces the v1 file-level coarseness
   (the FP target in criterion 2 is measured against the hunk-level witness);
7. hub-declaration laundering is bounded before over-declaration blocks:
   declaring one legitimately-touched hub symbol (e.g. a 65-caller core type)
   makes hop-1(declared) cover almost anything, and the over-declaration
   check cannot see it (the hub IS touched). Pre-promotion the gate needs a
   per-ref hop-1 fan-out bound or a near-minimality measure — hop-1 of a hub
   is the same "`write_paths: ["**"]` in symbol clothing" this check exists
   to stop, one level down.

**Known observation limits (recorded, pre-promotion obligations):**
- **gitignore blind spot (shared by BOTH halves)**: `.gitignore` is an
  agent-writable work product (ADR-0019), and both git observation and the
  witness exclude ignored files — an agent can hide untracked work by
  ignoring it. Committed work is still caught via merge-base..HEAD. Before
  promotion: flag `.gitignore` deltas made during a run, or observe
  ignored-but-changed files.
- **`file:name` argv encoding** assumes no colon in repo-relative paths
  (split on first colon). Legal-but-rare; documented, not defended.
- **porcelain v1 hand-parsing** does not decode C-quoted/control-character
  paths or `->` inside names; move to `--porcelain=v1 -z` NUL records as a
  robustness follow-up.

## Where the check runs (honest as-built note)

The engine sweep (`run_all_engines`) fires at **closure** — Heartgate's
`validate_closure`, invoked by `handle_finalize` — so as-built this lands as
detection-at-closure, not a literal EXECUTE→VERIFY hook. The engine is
phase-agnostic (`validate(workspace, run_id)`); adding a VERIFY-entry
invocation later needs no contract change. Because the gate derives the
witness itself, there is no separate "who produces the file, and when"
trigger to define — every sweep re-derives from ground truth.
