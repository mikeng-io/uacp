# Phase 5: Select Domains from the Domain Registry

Read the domain registry files:

```bash
Read: [skills-root]/uacp-core/references/domains/technical.md
Read: [skills-root]/uacp-core/references/domains/business.md
Read: [skills-root]/uacp-core/references/domains/creative.md
```

For each domain in registry:
- Check if any `trigger_signals` appear in conversation signals
- Match against: file names, topics, concerns, explicit mentions, technical terms
- Select ALL matching domains (minimum 1, no maximum)

**UACP domain override:** If `uacp_lifecycle` artifact type is detected, always include `governance` domain. If council-related signals present, include `review` domain.

If no domains match:
- For `code` → default to `api` + `testing`
- For `uacp_lifecycle` → default to `governance` + `architecture`
- For `financial` → default to `finance`
- For `marketing` → default to `marketing`
- For `research` → default to `content`
- For `creative` → default to `design` + `ux`
