---
type: pattern
title: Claude Code Print-Mode Adversarial Review
description: "3-line recipe: pipe design docs into `claude -p --effort high --max-turns 1` for adversarial architecture/security review."
tags: [claude-code, review, adversarial, security]
timestamp: 2026-06-17
---

# Claude Code Print-Mode Adversarial Review

For design/architecture documents, use Claude Code print mode (`-p`) with `--effort high` for adversarial review. Pipe the document via stdin:

```bash
cat design-doc.md | claude -p 'Review this document for [specific focus areas]...' --max-turns 1 --effort high
```

This is effective for security/threat model review, architecture consistency checks, schema completeness validation, and guard/policy gap detection. In practice this approach has surfaced critical issues and gaps that quick read-throughs missed.
