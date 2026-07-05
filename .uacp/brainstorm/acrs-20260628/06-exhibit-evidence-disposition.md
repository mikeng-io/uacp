# Phase 6 (vault exhibit) — evidence_disposition: the boundary bug in miniature

A live bug found mid-session (Codex finding #4 on PR #68, chained off a wrong doc fix)
that is a textbook instance of the MD↔YAML boundary problem this run addresses.

## The artifact
`uacp.evidence_disposition` — VERIFY→RESOLVE paired files per evidence cluster:
- `verification/{run_id}-{cluster}-verified-facts.md`
- `verification/{run_id}-{cluster}-assumptions.md`
(layout template: `{run_id}-{cluster}-{half}.md`; half ∈ {verified-facts, assumptions},
authoritative in `artifact_schema.py:100-101`.)

## What's right (and proves the thesis)
The CONTENT is already Markdown — verified-facts / assumptions prose lives in MD, correctly.

## What's wrong (the boundary violation)
The RELATION data — which cluster, which half — is encoded into the **filename** via
hyphenated ctx placeholders. Two consequences, both verified empirically:
- `entity_write(half="verified-facts")` → REJECTED: the writer's own ctx sanitizer
  forbids `-` (its anti-ambiguity guard for `{run_id}-{cluster}-{half}`).
- `artifact_write(...-verified-facts.md)` → REJECTED: the path reverse-maps to the
  RELATION-plane manifest kind `uacp.evidence_disposition` (CUT3).
→ **The verified-facts half is unwriteable through ANY governed writer.** The model
fights itself: relation data crammed into a path string collides with the path guard.

## Why this is THE exhibit
Under the anchor model (YAML=relations, MD=content):
- `cluster` + `half` become a typed relation/anchor in YAML pointing at the MD content,
- NOT hyphen-delimited segments of a filename,
- so there is no sanitizer collision and no unwriteable file.

The fix is NOT "let the sanitizer pass hyphens" (that patches the broken model). The fix
is the boundary redesign: stop encoding relations in filenames.

## Disposition
- Do NOT build a standalone writer patch — it would reinforce the model being replaced.
- Fold as motivating evidence here.
- Orthogonal cleanup: the `half: left|right` fiction shipped in main (PR #68, abc6f06)
  misleads agents today and should be corrected/reverted independently of the redesign.
