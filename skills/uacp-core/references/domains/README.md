# Domain Registry

Reference library of domain definitions used by UACP lifecycle skills and bridge adapters to select appropriate expert agents for a given artifact type.

**This is a REFERENCE LIBRARY.** Skills read it via the `Read` tool to determine which domain experts to spawn. It is never invoked directly. It lives under `skills/uacp-core/references/domains/` (the shared canonical reference home); skills cite it as `../uacp-core/references/domains/`.

---

## Overview

The Domain Registry enables intelligent selection of domain-specific expert roles for code review, analysis, and verification tasks. Each domain has:

- **Trigger signals** — keywords that indicate this domain is relevant
- **Focus areas** — what the expert looks for
- **Standards** — what standards/best practices apply
- **Expert role framing** — title, lens, and prompt template for agent councils

---

## Available Domains

| File                   | Categories                                                                                                                                                                       |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `technical.md` | Security, Database, API, Async-Queue, Performance, Infrastructure, Crypt, Code Quality, Architecture, Testing, Error Handling, Concurrency, TypeScript, Frontend, Data Integrity |
| `business.md`  | Finance, Product, Marketing, Operations, Compliance, Analytics                                                                                                                   |
| `creative.md`  | UX Design, Visual Design, Copywriting                                                                                                                                            |

---

## Domain Selection Protocol (Lookup Protocol)

### Tier 1: Exact Match

1. Extract trigger signals from context
2. Match against domain `trigger_signals`
3. If exact match found → use domain `expert_role`

**Example:**

- Context mentions "authentication" → matches `security` domain
- Context mentions "subscription pricing" → matches `finance` domain
- Context mentions "wireframe usability" → matches `ux-design` domain

### Tier 2: Adapted Match

When no exact match, find the closest related domain and adapt the framing:

```yaml
adapted_expert:
  base_domain: "{closest-match}"
  adapted_focus: ["{scope-specific concerns}"]
  adapted_title: "{Role} for {context}"
```

**Example:**

- Context mentions "real-time data processing" (no exact match)
- Closest match: `async-queue` domain
- Adapted focus: ["stream processing latency", "backpressure handling"]

### Tier 3: Virtual Expert Synthesis

When no domain matches, synthesize a session-based virtual expert from related domains:

```yaml
virtual_expert:
  name: "{Specific Role Title}"
  synthesized_from: ["{registry-domain-1}", "{registry-domain-2}"]
  focus_areas: ["{area specifically relevant}"]
  standards: ["{standard relevant}"]
  scope: session # ephemeral
```

**Example:**

- Context mentions "blockchain smart contract audit" (no exact match)
- Synthesize from: `security` + `architecture` + `code-quality`
- Virtual expert: "Smart Contract Auditor" with focus on cryptographic correctness, gas optimization, security patterns

---

## Expert Role Format

Each domain includes enhanced framing for agent councils:

```yaml
expert_role:
  title: "Role Title"
  lens: "One-sentence perspective that guides all analysis"
  prompt_template: |
    You are a {title} reviewing: {scope}

    ## Your Lens
    {lens}

    ## Context
    {context_summary}

    ## Your Focus Areas
    {focus_areas}

    ## Standards to Apply
    {standards}

    ## Output Format
    Return findings as json with severity, affected areas,
    impact, remediation, and confidence level.
```

### Using Expert Roles

Skills using the domain registry should:

1. Read the appropriate `domains/*.md` file(s)
2. Match context signals against domain `trigger_signals`
3. Extract the `expert_role` for matched domains
4. Inject the `prompt_template` into agent prompts, replacing placeholders:
   - `{scope}` — the artifact being reviewed
   - `{context_summary}` — the context description
   - `{focus_areas}` — from domain definition
   - `{standards}` — from domain definition

---

## Skills Using the Domain Registry

| Skill           | Usage                                        |
| --------------- | -------------------------------------------- |
| `uacp-council`  | Select expert roles for role-diverse council |
| `uacp-debate`   | Domain experts for adversarial investigation |
| `uacp-context`  | Domain detection for context building        |
| `uacp-bridge`   | Resolve expert role / focus / standards per runtime |
| lifecycle skills | Domain experts for phase councils (triage→resolve) |

---

## Adding New Domains

To add a new domain:

1. Choose the appropriate file (`technical.md`, `business.md`, or `creative.md`)
2. Add a domain entry following the schema (`name`, `trigger_signals`, `expert_role`, `focus_areas`, `standards`)
3. Ensure `trigger_signals` are lowercase and distinctive
4. Ensure `expert_role` has all required fields

---

## Notes

- Domains are **read-only** — skills read them, never invoke directly
- Virtual expert synthesis allows handling project-specific issues without bloating the registry
- The `lens` field should be distinctive and memorable — it guides the expert's entire analysis
