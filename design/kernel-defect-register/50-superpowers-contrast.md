---
type: analysis
title: The superpowers contrast — the four places it earns a line
description: Demoted from the original framing. Corrected numbers, corrected citations, and only the comparisons that survive contact with the register.
tags: [comparison, superpowers, prior-art]
timestamp: 2026-08-22
edges:
  - {dst: 00-register, rel: depends_on, provenance: derived}
  - {dst: 30-emission-defects, rel: extends, provenance: asserted}
---

# The superpowers contrast

`obra/superpowers` @ `b36e082` (v6.3.0). This began as the frame for the whole investigation and
is demoted here because most of the comparison did not survive verification — an adversarial
audit refuted eleven claims, four of them by finding the refuting evidence inside a file the
author had already opened.

## Corrected figures

| | superpowers | UACP |
|---|---|---|
| Skills | 14 | 20 |
| Tracked `.md` under `skills/` | **39** (not "14 prose files") | 156 |
| Words in `skills/` | 43,072 | 151,558 total · **96,567 UACP-own** |
| Python LOC | **542** (not 0) | 79,498 |
| Hooks | 1 SessionStart, matcher `startup\|clear\|compact` | SessionStart (no matcher) + PreToolUse Guardian |
| Blocking enforcement | none — all prose-honored | Guardian + Heartgate, fail-closed *(when the plugin is enabled — D-14)* |

The prose ratio is 2.2×, not 3.5×: 55k of UACP's `skills/` words are the vendored third-party
`code-review` library, not governance prose.

## Where it earns a line

**1. Emission at every seam.** Superpowers' skills end by naming the next skill imperatively and
exclusively — *"Do NOT invoke any other skill. writing-plans is the next step"*
(`brainstorming/SKILL.md:231`) — and `writing-plans/SKILL.md:61` stamps the handoff into the
**plan document header**, so a fresh session that reads the plan learns how to execute it. That
is the shape D-13 is missing, and the useful part is the *stamping into the artifact*, not the
prose.

**2. Termination structure for a fix loop.** Five rounds; rounds 1–3 resume the same implementer,
4–5 escalate to a fresh one on a stronger model; a **scoped** re-review over the fix diff only,
verdicting each finding ADDRESSED / NOT ADDRESSED; a breaker at the cap that forces adjudication
of every open finding into a written ruling; and *"adjudicating earlier to end a loop is
pre-judging with a different name."* Relevant to D-08 — though UACP's own PPV gate already
demonstrates the cap-with-trip-action pattern, so the transplant is the *adjudication* half,
not the cap.

**3. Handing artifacts over as files.** *"Everything you paste into a dispatch prompt … stays
resident in your context for the rest of the session"*
(`subagent-driven-development/SKILL.md:231-233`), with the observed cost at `:269` — a real
dispatch that hit 42k chars of which 99% was pasted history. Three bash scripts (127 lines
total) implement it: a per-plan workspace, a task-brief extractor, and a review-package writer.
Directly relevant to D-16, where exactly one UACP dispatch path passes file pointers and the
rest interpolate strings.

**4. Skill prose treated as testable code.** RED (run the scenario *without* the skill, capture
the rationalization verbatim) → GREEN (write the minimal skill addressing those failures) →
pressure-test under 3+ combined pressures → plug the new rationalization. The `Thought | Reality`
tables are the serialized output of that process, not advice; their contributor rules forbid
rewording them without eval evidence. UACP has labeled eval lanes for a retriever
(`engines/oracle/eval/seed_evalset.json`), a detector (`design/codeflair/eval/seed-set.yaml`,
build-gating), and an install (`acceptance/`) — but none for skill-prose → agent behavior. The
transplant is a new seed unit in an existing lane, not a new discipline. Relevant to D-18: a
tested rationalization row is the right shape for what is currently narrative accretion.

## Where the arrow points the other way

- **Superpowers deletes its record on success** — `rm -rf <workspace>`
  (`subagent-driven-development/SKILL.md:483`) at merge, taking every ruling and parked finding
  with it. Nothing crosses plans; it ends every project at zero.
- **Its classification is never a gate.** spike / bounded / architectural is a self-announced
  string; mislabel and the agent simply proceeds. UACP's granularity and routing outcome are
  `classification_inputs` to a fail-closed meta-gate, and `uacp-execute/SKILL.md:203-210`
  carries a mid-phase escalation rule with real consequences (council tier, pause before
  irreversible side effects, exit block on unresolved HIGH/CRITICAL).
- **Its disposition vocabulary is prose.** UACP types it: five finding classes, six handling
  classes, per-class required evidence, `rejected_with_reason` as first-class typed pushback.
  D-04 is one missing existence check inside a structure superpowers does not have at all.
- **Compaction.** `skills/uacp-handoff/SKILL.md:92` is an explicit `## Verb: RESUME (at session
  start)` with an inclusion contract — *can a fresh agent recover this from the commits, the
  diff, and repo status? YES → an anchor, never body prose* — which is superpowers'
  hand-artifacts-over-as-files rule in stronger typed form, plus committed per-workstream
  capsules the injector surfaces automatically.

## The methodological finding

Every refuted claim failed the same way: superpowers states its discipline in prose an agent
reads, UACP encodes the same discipline in schemas, enums, engines, and config an agent only
meets when a gate refuses it. **A surface reading of the two systems will systematically
under-credit UACP** — and that is not only an artifact of this comparison. It is the same
asymmetry that makes UACP's own defects hard to see from its documentation, which is why the
register above was built from the kernel outward rather than the docs inward.
