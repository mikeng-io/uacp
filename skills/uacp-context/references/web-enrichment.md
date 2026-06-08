# Phase 4: Enrich Context via Web Backends (Optional)

If artifact type is `code`, `mixed`, or `research` AND local conversation signals are sparse (confidence ≤ medium), optionally enrich via `uacp-web` backends:

**When to enrich:**
- Minimal conversation context (low-confidence signals)
- User asks about architectural intent, not just file contents
- Repository is large or unfamiliar
- External documentation or research is relevant

**Enrichment protocol:**

1. **Identify enrichment target:** Extract repo name, technology names, or key concepts from signals.
2. **Select backend:**
   - **Tavily** — general web search for technology/context/docs
   - **Firecrawl** — deep extraction from specific URLs mentioned
   - **Context7** — library/framework documentation retrieval
3. **Query construction:** Formulate 1-3 targeted queries based on detected topics.
4. **Execute enrichment:** Spawn lightweight Task agent with `uacp-web` backend instructions.
5. **Merge results:** Add enriched findings to `conversation_signals.topics` and `conversation_signals.concerns`.

**Non-blocking:** If enrichment fails or `uacp-web` is unavailable, proceed with local signals only and mark `enrichment_status: skipped`.
