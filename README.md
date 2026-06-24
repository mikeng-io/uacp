# UACP — Universal Agent Control Plane

UACP is a runtime-neutral governance framework for AI agent work. It provides a staged lifecycle, adaptive evidence selection, multi-agent orchestration, and runtime enforcement — across domains, runtimes, and task types. UACP separates governance (what should happen and under what authority) from deliberation (how to reason about strategy and design) from coordination (tracking durable task state) from execution (bounded work performed by runtimes and tools). This separation is a reasoning invariant, not just a wiring preference: it determines which cognitive plane is authoritative for which class of decision, and prevents category errors from propagating silently through a run.

---

## The Problem UACP Solves

Agent work without governance accumulates hidden assumptions. Authority is implied rather than declared. Side effects are invisible to anything outside the immediate runtime. Phase boundaries are crossed silently — work begins executing before a plan is approved, or resolves before verification evidence exists. Evidence is asserted rather than produced: a runtime reports "done" without anything to back the claim.

UACP makes all of this explicit and enforceable before actions execute. Every phase transition is validated by Heartgate. Every tool call is evaluated by Guardian against declared policy. Every authority delegation is declared in a proposal, not inferred from context. Every evidence obligation is selected adaptively for the run — by domain, risk, reversibility, and artifact type — rather than prescribed by a fixed checklist.

The goal is not to add overhead. It is to ensure that when something goes wrong, the record shows exactly what was authorized, what evidence was produced, and where the boundary was crossed.

---

## Lifecycle

The UACP lifecycle has seven phases: **(optional) BRAINSTORM → TRIAGE → PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE**

**BRAINSTORM** is an optional pre-governance exploration phase. Use it when the request is vague, has ambiguous scope, or spans multiple possible directions. BRAINSTORM is a governed phase — it registers a formal run, writes a scope package, and runs Heartgate for the `brainstorm→triage` transition before handing off. It never skips TRIAGE.

**TRIAGE** is the mandatory entry point for all governed work. It calibrates scope, scores granularity, and routes the request before any lifecycle commitment is made. Triage can route work directly (bypassing the full lifecycle) or block it pending authority or clarification.

### Triage Routing Outcomes

| Route | Meaning |
|---|---|
| `direct` | No governed lifecycle. Handle directly without phase tracking. |
| `lightweight` | Minimal governed path with a small artifact footprint. |
| `standard` | Normal lifecycle at standard governance intensity. |
| `full_governance` | Full lifecycle with Agent Council, broader review, and durable learning. |
| `block_or_clarify` | Stop. Require authority or clarification before proceeding. |

The `lightweight`, `standard`, and `full_governance` routes all enter PROPOSE and continue through the linear chain. Evidence inside each phase is adaptive — selected by context — not a fixed checklist applied uniformly.

For the human-readable guide to the semantic package, PIV, VERIFY/RESOLVE, Guardian/Heartgate, and audit-remediation hardening series, see [`docs/guides/lifecycle-hardening/00-index.md`](docs/guides/lifecycle-hardening/00-index.md).

```mermaid
flowchart TD
    BRAINSTORM([BRAINSTORM\noptional])
    TRIAGE([TRIAGE])
    BRAINSTORM -->|scope-package + heartgate| TRIAGE
    TRIAGE -->|direct| DIRECT([Handle Directly])
    TRIAGE -->|block_or_clarify| BLOCK([Block / Clarify])
    TRIAGE -->|lightweight| PROPOSE
    TRIAGE -->|standard| PROPOSE
    TRIAGE -->|full_governance| PROPOSE

    PROPOSE --> PLAN
    PLAN --> EXECUTE
    EXECUTE --> VERIFY
    VERIFY --> RESOLVE
    RESOLVE --> DONE([Terminal])
```

### Phase Responsibilities

| Phase | Responsibility |
|---|---|
| (optional) BRAINSTORM | Pre-governance exploration; must exit to TRIAGE before any governed work begins |
| TRIAGE | Scope calibration, granularity scoring, governance routing |
| PROPOSE | Declare intent, authority, constraints, and evidence obligations |
| PLAN | Produce a verified, council-reviewed execution plan |
| EXECUTE | Perform bounded work through runtimes and tools within Guardian policy |
| VERIFY | Produce and synthesize evidence that the plan was executed correctly |
| RESOLVE | Close the run, record lessons, and release all held state |

### Two Lifecycle Tracks

UACP supports two tracks. The **standard track** is the default: fixed phases, structured artifacts, deterministic gate checks. The **goal-driven track** (ADR-0016) is for semantic or exploratory work — it adds a persistent goal artifact and a checkpoint manifest; otherwise it is byte-identical to the standard track. See [`docs/architecture/0016-goal-driven-track.md`](docs/architecture/0016-goal-driven-track.md).

---

## Cognitive and Control-Plane Model

UACP enforces a strict separation between five cognitive/operational planes, plus a boundary-enforcement layer. Mixing planes causes category errors: do not use a Coordination Adapter to decide policy; do not use Agent Council as a durable state database; do not let worker runtimes silently change UACP phase state.

```mermaid
graph TD
    UACP["UACP\n(Governance Cognition)"]
    AC["Agent Council\n(Deliberative Cognition)"]
    CA["Coordination Adapter\n(Coordination Memory)"]
    AR["Agent Runtimes\n(Worker Cognition)"]
    TA["Tool Adapters + Evidence Services\n(Actuation and Observation)"]
    GH["Guardian + Heartgate\n(Boundary Enforcement)"]

    UACP -->|authorizes| AC
    AC -->|orchestrates| CA
    CA -->|dispatches| AR
    AR -->|uses| TA

    GH -.->|enforces| UACP
    GH -.->|enforces| AC
    GH -.->|enforces| CA
    GH -.->|enforces| AR
    GH -.->|enforces| TA
```

### Plane Definitions

| Plane | Role | Examples |
|---|---|---|
| UACP | Governance cognition: should / may / must / under what risk | This repository |
| Agent Council | Deliberative cognition: think together / design / challenge / synthesize | Role-diverse agents configured per run |
| Coordination Adapter | Coordination memory: remember / coordinate / track / hand off | Kanban, issue trackers, custom queues (replaceable) |
| Agent Runtimes | Worker cognition: reason locally / perform bounded work | Hermes (host), Claude Code, Codex, OpenCode, Kimi, Gemini |
| Tool Adapters + Evidence Services | Actuation and observation: observe / act / produce evidence | Web search, browser automation, scraping APIs |
| Guardian + Heartgate | Boundary enforcement: enforce the separation between all other planes | Guardian (tool calls), Heartgate (phase transitions) |

The Coordination Adapter is intentionally replaceable. Kanban is the current implementation, not the required one. What is required is that durable task state flows through a declared adapter and is not held privately by any runtime.

---

## Key Concepts

| Concept | Definition |
|---|---|
| Triage | Scope calibration, granularity scoring, and governance routing before committing to a full run |
| Phase | One stage of the lifecycle; evidence requirements are adaptive per phase, not fixed globally |
| Granularity | Governance complexity of a run or phase; phase-local and compositional — each phase scores itself, rather than inheriting a single flat number assigned at intake |
| Guardian | Runtime tool-call enforcement engine; evaluates normalized events against policy before actions execute |
| Heartgate | Lifecycle transition validator; ensures phase boundaries are truthful and all invariants satisfied before permitting forward movement |
| Agent Council | Multi-agent deliberative primitive: role-diverse agents reason, challenge, and synthesize; review is one mode among many (plan, execute, audit, research, brainstorm, resolve) |
| Coordination Adapter | Replaceable durable task substrate used by EXECUTE for multi-worker coordination; Kanban is an example implementation |
| Runtime Adapter | Runtime-specific plugin that translates runtime events into normalized Guardian and Heartgate contracts; thin and policy-free |
| Evidence Cluster | A context-selected set of evidence obligations for one phase |
| Policy Pack | A bundle of Guardian policy for a specific governance context |

---

## Repository Layout

```
uacp/
├── README.md                          ← you are here (public-facing overview)
├── AGENTS.md                          ← authority chain + lifecycle summary for agents
├── CLAUDE.md                          ← Claude Code runtime entry (points to AGENTS.md)
├── PROJECT.md                         ← project identity (audience-keyed entry points)
├── ROADMAP.md                         ← completed phases + reserved-slot backlog
├── CONTRIBUTING.md                    ← authoring contract (how to open a UACP run)
├── COMMANDS.md                        ← verify scripts, live probe, validator commands
│
├── docs/                              ← canonical prose authority (OKF-formatted)
│   ├── INDEX.md                       ← structural navigation (start here as an agent)
│   ├── arc42-index.md                 ← partial ARC42 architecture mapping
│   ├── policy/                        ← foundational doctrine
│   │   ├── constitution.md            ← non-waivable invariants
│   │   ├── first-principles.md        ← reasoning principles behind UACP
│   │   └── alignment-spec.md          ← artifact roots + deployment-specific alignment
│   ├── lifecycle/                     ← seven-phase lifecycle model
│   │   ├── lifecycle-reference.md     ← phases, granularity, state, skill contracts
│   │   ├── orchestration-model.md     ← Agent Council, tiers, roles, execution profiles
│   │   └── worktree-protocol.md       ← branch/worktree isolation rules
│   ├── runtime/                       ← Guardian + Heartgate enforcement
│   │   ├── runtime-enforcement.md
│   │   ├── runtime-integration-guide.md
│   │   └── runtime-porting-and-version-control.md
│   ├── guides/                        ← curated human/agent reading paths
│   │   └── lifecycle-hardening/
│   │       ├── 00-index.md
│   │       ├── 01-human-overview.md
│   │       ├── 02-agent-operating-guide.md
│   │       ├── 03-artifact-and-gate-map.md
│   │       └── 04-audit-and-remediation-history.md
│   ├── reference/                     ← canonical schemas + per-skill authority
│   │   ├── proposal-schema.md
│   │   ├── skill-enforcement-spec.md
│   │   ├── lifecycle-trace-table.md
│   │   ├── learning-artifact-schema.md
│   │   └── operator-phase-return-schema.md
│   ├── architecture/                  ← numbered ADRs 0001–0017 (status lifecycle)
│   │   ├── 0000-template.md
│   │   └── 0001-…0017-*.md
│   ├── decisions/                     ← operational decision-log (lighter than ADRs)
│   │   └── decision-log.md
│   ├── plans/                         ← forward plans + reserved slots
│   │   └── phase5-reserved-slot.md
│   └── archived/                      ← completed plans and superseded docs
│
├── config/                            ← machine-readable policy derived from docs
│   ├── uacp.toml                      ← collapsed config: [guardian] [autonomy] [memory]
│   │                                     [models] [runtime_bindings] [version_control]
│   │                                     [scope] [oracle] [heartgate.*] [paths] + knobs
│   ├── phase-transitions.yaml         ← doctrine layer (LLM-read); grammar codified to
│   │                                     skills/uacp-core/scripts/engines/domain/
│   ├── state.yaml
│   ├── evidence-clusters.yaml
│   ├── gate-selection.yaml
│   ├── review-routing.yaml
│   └── hooks/                         ← hook definitions
│
├── .uacp/                             ← runtime namespace (config base = ".uacp")
│   ├── knowledge/                     ← Oracle corpus (TRACKED in git)
│   ├── lessons/                       ← Oracle lessons corpus (TRACKED in git)
│   ├── knowledge/indexes/             ← built vector index (gitignored)
│   │   [runtime-created on first run — not present in a fresh clone:]
│   ├── state/                         ← mutable runtime state (governed writers only)
│   │   ├── current.yaml              ← active-run pointer
│   │   ├── kanban.yaml               ← coordination adapter state
│   │   ├── runs/                     ← per-run state records
│   │   ├── gate-ledger/              ← append-only JSONL
│   │   ├── run-registry.yaml
│   │   └── escalations/
│   ├── proposals/                     ← PROPOSE phase artifacts
│   ├── plans/                         ← PLAN phase artifacts
│   ├── executions/                    ← EXECUTE phase records
│   ├── verification/                  ← VERIFY evidence + council synthesis
│   ├── resolutions/                   ← RESOLVE closure artifacts
│   ├── bridges/                       ← runtime bridge state
│   └── councils/                      ← council session artifacts
│
├── skills/                            ← versioned in this repo (not under HERMES_ROOT)
│   ├── uacp/                          ← umbrella entry skill
│   ├── uacp-brainstorm/               ← BRAINSTORM phase
│   ├── uacp-triage/                   ← TRIAGE phase
│   ├── uacp-propose/                  ← PROPOSE phase
│   ├── uacp-plan/                     ← PLAN phase
│   ├── uacp-execute/                  ← EXECUTE phase
│   ├── uacp-verify/                   ← VERIFY phase
│   ├── uacp-resolve/                  ← RESOLVE phase
│   ├── uacp-council/                  ← multi-agent deliberation (cross-cutting)
│   ├── uacp-debate/                   ← structured debate primitive
│   ├── uacp-parallel/                 ← parallel dispatch
│   ├── uacp-context/                  ← context management
│   ├── uacp-web/                      ← web-backend tool adapter
│   ├── uacp-core/                     ← kernel: scripts/engines + references/contracts
│   │   └── scripts/engines/
│   │       ├── domain/               ← codified phase-transition grammar (code-authoritative)
│   │       └── oracle/               ← Oracle retrieval engine implementation
│   ├── uacp-bridge/                   ← runtime dispatch contracts
│   │   └── references/               ← claude.md, codex.md, kimi.md, opencode.md, gemini.md
│   ├── uacp-state/                    ← state-mutation contracts
│   └── uacp-skills/                   ← skill-authoring meta-skill (ADR-0017)
│
├── runtime-adapters/                  ← UACP-owned adapter source per runtime
│   └── hermes/
│
├── scripts/                           ← verification and probe scripts
│   ├── phase0_verify.py … phase4_verify.py
│   ├── live_guardian_probe.py
│   └── validate_uacp_artifacts.py
│
└── tests/                             ← automated test suite
```

`docs/` is the authority layer. `config/` is derived from `docs/`. `.uacp/state/` is the only mutable layer during a run. Run artifacts (proposals, plans, executions, verification, resolutions) land under `.uacp/` and are gitignored — they are runtime-created. The Oracle corpus (`.uacp/knowledge/` and `.uacp/lessons/`) is the exception: it is tracked in git as the durable learning record.

> **Fresh clone note:** `.uacp/state/`, `.uacp/proposals/`, and other per-run dirs are runtime-created and will not exist in a fresh clone. An agent bootstrapping cold should treat a missing `.uacp/state/` as "no active run" rather than an error.

---

## Oracle / Knowledge Engine

UACP includes an **Oracle** retrieval engine that is the sole reader and writer of the `.uacp/knowledge` and `.uacp/lessons` corpus. This clean data-ownership boundary means the state engine owns state/manifest, and Oracle owns the knowledge corpus — no other subsystem reads or writes corpus content directly.

Oracle **ships inert** (`[oracle] enabled = false` in `config/uacp.toml`). When enabled it performs hybrid retrieval: BGE-M3 dense embedding, keyword search, and Qwen3-Reranker reranking, with LanceDB as the vector store. A Bayesian Effectiveness Score (BES) overlay ranks lessons by past utility. Models default to locally embedded; optional per-role OpenAI-standard URL overrides allow swapping in hosted endpoints per role. A zero-ML-dependency floor mode (keyword + structured + BES) remains functional when Oracle is disabled.

Retrieval is exposed read-only via the `uacp_oracle_query` tool. Engine implementation lives in `skills/uacp-core/scripts/engines/oracle/`. Design documentation is in `docs/archived/2026-06-17-oracle-engine-design.md`.

---

## Where To Start

**As a human reading this for the first time:**
`README.md` → `docs/policy/constitution.md` → `docs/lifecycle/lifecycle-reference.md` → `docs/lifecycle/orchestration-model.md`

**As an agent executing UACP work:**
`docs/INDEX.md` is the canonical read order. Start there. It specifies which documents to load in which sequence for a given run type.

**To integrate a new runtime:**
`docs/runtime/runtime-integration-guide.md` — defines the adapter contract, normalization requirements, and Guardian/Heartgate integration points. Bridge contracts for existing runtimes (Codex, Kimi, Claude, OpenCode, Gemini) are in `skills/uacp-bridge/references/`.

**To understand runtime enforcement (Guardian / Heartgate):**
`docs/runtime/runtime-enforcement.md` — covers the enforcement model, event normalization, policy evaluation order, and failure modes.

**To understand design history and major decisions:**
`docs/decisions/decision-log.md` — durable record of decisions that shaped the current design, including alternatives considered and why they were rejected. ADRs 0001–0017 are in `docs/architecture/`.

---

## Authority Chain

When a conflict exists between layers, earlier layers win. An explicit entry in `docs/decisions/decision-log.md` is the only mechanism to override this order.

| Priority | Layer | Role |
|---|---|---|
| 1 | `docs/INDEX.md` | Document registry and canonical read order |
| 2 | Canonical prose docs (`docs/`) | Intent, principles, lifecycle, and policy |
| 3 | YAML config (`config/`) | Machine-readable rules derived from docs |
| 4 | Runtime state (`.uacp/state/`) | Current lifecycle position and run pointers |
| 5 | Skills and runtime behavior | Implement the documented rules |
| 6 | Execution artifacts | Record what happened in a specific run |

Skills and runtimes do not override docs. Config does not override docs. If a YAML rule contradicts a prose document, the prose document is authoritative and the YAML must be corrected.

---

## Runtime Support

UACP is designed to be runtime-neutral. The current host runtime is **Hermes**. Adapter bridge contracts exist for: **Claude Code**, **Codex**, **Kimi**, **OpenCode**, and **Gemini** — see `skills/uacp-bridge/references/` for the dispatch contracts for each.

Each runtime requires a thin adapter that translates runtime-specific events into normalized Guardian and Heartgate contracts. The adapter is policy-free: it translates events but does not evaluate them. UACP-owned adapter source lives under `runtime-adapters/<runtime>/`.

See `docs/runtime/runtime-integration-guide.md` for the full integration contract, including required event schema, normalization rules, and Heartgate handshake protocol.
