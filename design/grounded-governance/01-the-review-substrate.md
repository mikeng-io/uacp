---
type: design
title: "The review substrate: kernel-produced diff-content, not an agent's account"
description: "What the screening reads: the actual diff CONTENT from the true commit range (merge-base..HEAD, the run's real change set) plus the reality-run's output, produced by the kernel and registered as a governed artifact — never nominated by the run under review. Extends gitio's name-only witness to content, so there is real material to precipitate against."
tags: [verify, substrate, diff, gitio, behavior-plane, witness]
timestamp: "2026-08-24"
edges: [{dst: 00-the-correctness-gap, rel: depends_on, provenance: derived}]
---
# The review substrate: kernel-produced diff-content, not an agent's account

## What the substrate must contain

For a screening to precipitate correctness defects, it needs the real work as material, three parts
in order of load-bearing (`design/verify-substrate/01`):

1. **The diff CONTENT from the true commit range** — not the file *names* (`gitio.changed_files`
   already gives those, name-only via `merge-base(default,HEAD)..HEAD`), but the actual hunks: what
   the lines became. This is the primary substrate; the eight #171 defects were all visible *in the
   hunks* (a symlink `open()`, a FIFO read, a UTF-8 slice) and invisible in any field.
2. **The reality-run's output** — what the changed code did when executed in the contained scratch
   (`behavior_plane`): exit status, stdout, observable behavior. Running turns behavior into material
   ("does this `open()` follow a symlink" is answered by pointing one at it and running).
3. **The real files and run artifacts** — as they are on disk / in the manifest, for the screening
   to cross-read against the hunks.

## The grounding rule: the kernel produces it, the run cannot nominate it

The whole point fails if the run under review hands over its own diff. So:

- The diff is computed by the **kernel** from `gitio.default_branch_merge_base(root)` (the run's real
  `base_commit`, already an audit field) to `HEAD` — the same witnessed range `changed_files` uses,
  extended from `--name-only` to content (`git diff <merge-base> HEAD`). One new gitio function,
  `diff_content(root) -> GitDiffResult`-shaped, reusing the exact merge-base logic so the review diff
  and the containment witness can never disagree about *what changed*.
- The output comes from **executing the actual component** via `behavior_plane`, its verdict
  *derived* from the run, never reported by the doer (Trustless Gate 0: `SKIP` must not masquerade as
  `PASS`).
- The substrate is written as a **governed artifact** (`verification/{run}/review-substrate…`) via a
  governed writer, so it is registered, watermarked, and resolvable — and the screening that consumes
  it, plus the gate that checks the screening, both key off a real artifact, not a transient blob.

## Why produce it as an artifact, not compute it inline

Because the screening's verdict must later be **grounded** the same way M2 grounds a remediation: the
gate that clears VERIFY checks that a screening artifact *resolves* and *covers this substrate*. If
the substrate is ephemeral, the screening's claim to have read it is back to self-attestation. A
registered substrate artifact makes "the screening read the real diff" a checkable fact: the
screening references the substrate's identity, and the gate confirms the substrate is the
kernel-produced one for this run's true range — not a diff the agent chose.

## What this deliberately is not

Not a *summary* of the diff, not a classification of it, not the agent's description of what changed.
Producing a digest here would re-commit the original sin one level down (`design/verify-substrate/01`:
the anti-pattern is pre-digesting the substrate into a label). The kernel produces the raw material;
the *reading* is the screening's job (`02`), and the *judgment* is the screening agent's, never the
producer's.
