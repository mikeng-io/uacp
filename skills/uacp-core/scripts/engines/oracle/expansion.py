"""Query expansion for the Oracle semantic pipeline (optional step 1 of QMD).

When the query_expansion role resolves to FLOOR or is explicitly disabled via
``enabled=False``, this module returns a single-element list containing the
raw query. No models, no network. The pipeline catches any failure and falls
back to the raw query regardless.

URL mode:  POST to a chat-completion endpoint to generate alternative phrasings.
           Lazy httpx import — degrades to raw query when httpx is absent.
EMBEDDED:  In-process LLM binding (same lazy pattern as embedding/rerank).
           Degrades to raw query when the binding is absent.
FLOOR:     Always returns [raw_query] — no expansion model available.

The original query is ALWAYS included in the returned list so the pipeline
has at least one query to search with.
"""

from __future__ import annotations

from engines.oracle.serving import RoleServing, ServingMode


def _try_expand_url(query: str, serving: RoleServing) -> list[str] | None:
    """Attempt multi-query expansion via a chat URL. Returns None on any failure."""
    try:
        import importlib

        httpx = importlib.import_module("httpx")
        prompt = (
            f"Generate 3 alternative search queries for: {query!r}\n"
            "Return one query per line, no numbering."
        )
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                serving.url,
                json={
                    "model": serving.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 128,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        expansions = [line.strip() for line in text.splitlines() if line.strip()]
        return expansions if expansions else None
    except Exception:
        return None


def _try_expand_embedded(query: str, serving: RoleServing) -> list[str] | None:
    """Attempt expansion via in-process binding. Returns None when absent/failing."""
    try:
        import importlib

        importlib.import_module("llama_cpp")
        # Real load wired when embedded runtime is available; stub returns None.
        return None
    except Exception:
        return None


def expand_query(
    query: str,
    serving: RoleServing,
    *,
    enabled: bool = True,
) -> list[str]:
    """Return a list of query variants for hybrid retrieval.

    Args:
        query:   The original search query.
        serving: Resolved RoleServing for the query_expansion role.
        enabled: If False, skip expansion and return [query] immediately.

    Returns:
        A list of query strings. The original ``query`` is always present.
        Never raises (degrade to [query] on any failure).
    """
    if not enabled or serving.mode is ServingMode.FLOOR:
        return [query]

    expansions: list[str] | None = None

    if serving.mode is ServingMode.URL:
        expansions = _try_expand_url(query, serving)
    elif serving.mode is ServingMode.EMBEDDED:
        expansions = _try_expand_embedded(query, serving)

    if not expansions:
        return [query]

    # Ensure the original query is always in the list
    if query not in expansions:
        expansions = [query] + expansions
    return expansions
