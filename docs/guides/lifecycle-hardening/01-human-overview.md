---
type: guide
tags: [human-readable, overview, lifecycle-hardening]
status: living-document
canonical_authority: false
---

# Human Overview — What Changed and Why

The lifecycle hardening work makes UACP understandable after the chat context is gone. It turns phase movement from “the agent says it is done” into a recoverable chain of intent, evidence, verification, and closure.

The core idea is simple:

```text
YAML is the machine envelope.
Markdown packages are the semantic recovery substrate.
Operator messages are concise summaries with evidence pointers.
```

That separation matters. A YAML artifact can prove a field was present, but it often cannot explain why a decision was made. A chat transcript can explain why, but it is not durable enough for future agents. A Telegram summary is useful for Mike, but it must not become the evidence layer. UACP now requires each layer to do the correct job.

## The problem this solved

Before the hardening series, several failure modes were possible:

- A phase could produce only skeletal YAML and lose the rationale.
- Operator channels could receive raw inventories instead of meaningful summaries.
- EXECUTE could move to VERIFY without a pre-declared evidence contract.
- VERIFY and RESOLVE could blur together, allowing closure to launder unresolved risk.
- Heartgate runtime checks could be shallower than the offline validator.
- Guardian could miss protected UACP writes hidden in shell command strings.
- Active skill exports could drift from repo docs and mislead future agents.

The result was not one bug. It was lifecycle fracture: docs, config, runtime, skills, and artifacts could each tell a slightly different story.

## The current model

UACP now uses a stronger chain:

1. PROPOSE and PLAN select adaptive semantic packages.
2. PLAN authors a Phase Intent Verification contract for non-trivial EXECUTE work.
3. EXECUTE records evidence against that contract and produces a semantic execution package.
4. VERIFY judges truth, including PIV satisfaction and independent re-verification where needed.
5. RESOLVE consumes verified truth, carries forward residual risks/deferred items, and closes the run without re-verifying itself.
6. Heartgate checks phase transitions at runtime.
7. Guardian binds protected tool calls to UACP even when paths are hidden in shell strings.
8. The offline validator and runtime gates now share the same artifact semantics more closely.

## What “coherence” means here

Coherence means a future human or agent can answer these questions without asking Mike or searching chat history:

- What was intended?
- Who authorized it?
- What evidence was required?
- What evidence was produced?
- What remained risky or deferred?
- Why was the run allowed to move to the next phase?
- Which file owns the canonical rule?

If those answers live in different places, they must link cleanly. If two files disagree, the change is not done.

## What this guide is not

This guide is not the canonical contract. It is a reading path. For enforcement, read the config, validator, runtime kernel, and reference specs linked from [00-index.md](00-index.md).
