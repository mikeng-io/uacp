# 06 — Concrete first instance: evidence_disposition

A live bug (Codex finding #4 on PR #68) that is the boundary violation in miniature — and
the natural first kind to convert.

## The artifact
`uacp.evidence_disposition` — VERIFY→RESOLVE paired files per evidence cluster:
- `verification/{run_id}-{cluster}-verified-facts.md`
- `verification/{run_id}-{cluster}-assumptions.md`

(layout template `{run_id}-{cluster}-{half}.md`; `half ∈ {verified-facts, assumptions}`,
authoritative in `artifact_schema.py:100-101`.)

## Why it's the exhibit
- The **content** is already Markdown — correct.
- The **relation** (which cluster, which half) is jammed into the **filename** as hyphenated
  segments. Verified empirically:
  - `entity_write(half="verified-facts")` → REJECTED: the ctx sanitizer forbids `-`
    (its anti-ambiguity guard for `{run_id}-{cluster}-{half}`).
  - `artifact_write(...-verified-facts.md)` → REJECTED: the path reverse-maps to the
    RELATION-plane manifest kind (CUT3).
  - ⇒ the `verified-facts` half is **unwriteable through any governed writer**. The model
    fights its own path guard.

## What this proves
Encoding relation data in a hyphen-delimited filename is the anti-pattern. The fix is NOT
"let the sanitizer pass hyphens" — that hardens the broken model. The fix is the model:
`cluster` and `half` become **typed relations/anchors in YAML** pointing at the MD content,
so there is no filename encoding and no sanitizer collision.

## Target shape under the model (illustrative)
```yaml
# a verification relation node (YAML)
evidence_disposition:
  cluster: c1
  halves:
    - kind: verified_facts
      anchor: "verification/{run_id}-c1-evidence.md#verified-facts"
    - kind: assumptions
      anchor: "verification/{run_id}-c1-evidence.md#assumptions"
```
Content lives in the MD under stable section ids; YAML carries the cluster + half relations.
The VERIFY→RESOLVE gate checks the *relations* (both halves present, anchors resolve,
assumptions has no unowned pending rows) instead of globbing hyphenated filenames.

## Disposition
- First kind to convert in the ratchet (stage 3–4 of [05-migration](05-migration.md)).
- This is where the `half: left|right` doc fiction in main (PR #68, abc6f06) also gets
  corrected — doc + model fixed together, per operator decision to fold it in.
