---
type: plan
title: "Oracle Retrieval Engine — Implementation Plan"
description: "Implementation plan for `engines/oracle/` with QMD pipeline, LanceDB store, and the `uacp_oracle_query` governed tool"
tags: ["oracle", "retrieval", "lancedb", "qmd"]
timestamp: 2026-06-17
status: archived
---

# Oracle Retrieval Engine — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

> **⛔ Query-expansion step RETIRED 2026-06-23** (see `docs/decisions/decision-log.md`). The `query-expansion → …` stage described below, its `expansion` serving role, the `[oracle.query_expansion]` config, and `test_query_expansion.py` were removed; the as-built pipeline starts at hybrid retrieve. This archived plan is left as historical record.

**Goal:** Build a config-gated, in-repo Python retrieval aggregator (`engines/oracle/`) that composes deterministic run-state lookup + semantic lesson/knowledge retrieval (QMD-shaped) + Honcho memory, serves per-role models by the precedence `url override > embedded default > floor`, and exposes a READ-ONLY `uacp_oracle_query` governed tool that injects ranked prior-art into the decision phases.

**Architecture:** A pure-domain layer (tier_config + provider-packet/trust-class dataclasses, zero I/O) sits below three independent, non-fatal source tiers — a deterministic run-state source (reusing `engines.io.loaders`), a semantic source backed by a thin LanceDB store interface, and a Honcho memory source. The semantic source runs a QMD pipeline (query-expansion → dense+keyword hybrid → RRF fusion → rerank → BES/tag overlay) whose embedding/rerank/expansion roles each resolve through a serving resolver (`url override > embedded default > floor`). Heavy ML deps (LanceDB, the llama.cpp binding) are optional + lazily imported so the keyword+structured+BES **floor** works with zero ML deps installed. The aggregator gates sources per phase via `PHASE_TIERS` and is surfaced read-only through `uacp_oracle_query` registered alongside the existing governed writers in the Hermes adapter.

**Tech Stack:** Python, pytest, ruff, LanceDB, llama.cpp binding (embedded GGUF), httpx (URL mode), the .uacp corpus

**Depends on:** the lesson/knowledge corpus (plan B) for its semantic corpus + BES. Related: design `2026-06-17-oracle-engine-design.md`.

---

## Build sequencing

**External dependencies (must land before this plan):**
- **Plan B** (corpus paths / schema / BES) must be merged — this plan reads the OKF corpus files, the `bes_bonus` function, and the `.uacp/knowledge/` paths that Plan B defines.
- **Plan A** must precede this plan for any skill edits — Plan A rewrites `skills/uacp-brainstorm/SKILL.md` wholesale; the edits in Task 13 are additive on top of the Plan-A version (see Fix 6 note in Task 13).

**Ship in two sub-slices to isolate concentrated risk (embedded llama.cpp runtime + bake-off):**

### C-floor (build first — zero ML deps, zero embedded runtime risk)
Tasks 1, 2, 3, 5, 9, 10, 11, 12, and the retrieval-led/advisory skill hooks in Task 13.
Delivers: tier_config, provider packets/trust classes, deterministic run-state source, serving resolver returning FLOOR, Honcho source, aggregator compose + per-phase gating, `[oracle]` config (default `enabled=false`), the read-only `uacp_oracle_query` tool, and the skill integration docs. Keyword + structured + BES floor works with ZERO ML deps.

### C-semantic (defer — gated on embedding-runtime choice + eval set)
Tasks 4, 6, 7, 8, and 14.
Delivers: LanceDB store impl, embedded embedding/rerank clients, the dense+hybrid pipeline leg, and the reranker bake-off. Gate on: choosing the embedded-runtime binding and being able to seed an eval set from real `.uacp/lessons` + `.uacp/knowledge` data.

Each task below is tagged `[C-floor]` or `[C-semantic]`.

---

## Conventions for every task

**Where code lives:** all engine code under `skills/uacp-core/scripts/engines/oracle/`. The governed tool registration + handler go in `runtime-adapters/hermes/plugins/uacp_guardian/__init__.py` (the `register(ctx)` pattern — see Task 11). Config goes in `config/uacp.toml`. Tests under `tests/unit/uacp_oracle/`.

**Running tests:** the repo `tests/conftest.py` already puts `skills/uacp-core/scripts`, `skills/uacp-state/scripts`, and the Hermes adapter dir on `sys.path`. So imports in tests are bare: `from engines.oracle import ...`. Run a single file with:
```bash
python -m pytest tests/unit/uacp_oracle/test_<x>.py -q
```
Run the whole new suite + lint at any checkpoint:
```bash
python -m pytest tests/unit/uacp_oracle -q && ruff check skills/uacp-core/scripts/engines/oracle tests/unit/uacp_oracle
```

**Import-guard pattern (use verbatim for every heavy dep):**
```python
def _try_import(name: str):
    try:
        import importlib
        return importlib.import_module(name)
    except Exception:
        return None
```
Never `import lancedb` / the llama.cpp binding at module top level. Resolve them lazily inside the function that needs them, and degrade to the floor when `_try_import` returns `None`.

**Engine style to mirror:** `engines/base.py` (frozen dataclasses, "never raise" contract), `engines/domain/scope.py` (pydantic read-models, `extra="allow"`), `engines/io/loaders.py` (the `Loaded[T]` result wrapper, `_safe_load_yaml`, `resolve_in_workspace`, `glob_in_workspace`). The Oracle reuses `engines.io.loaders` for the deterministic tier — do not re-implement YAML loading.

**Commit after each task** with a message like `feat(oracle): <task summary>` ending with the Co-Authored-By trailer. Do NOT push; do NOT branch unless asked.

---

## Task 1 `[C-floor]` — Package skeleton + `tier_config.PHASE_TIERS`

Create the package and the per-phase gating table (design §"Per-phase gating").

**1a. Failing test** — `tests/unit/uacp_oracle/test_tier_config.py`:
```python
from engines.oracle.tier_config import PHASE_TIERS, RetrievalMode, phase_tier

def test_every_lifecycle_phase_has_an_entry():
    expected = {"brainstorm", "triage", "propose", "plan", "execute", "verify", "resolve"}
    assert set(PHASE_TIERS) == expected

def test_decision_phases_are_retrieval_led():
    for phase in ("propose", "plan", "verify"):
        assert PHASE_TIERS[phase].mode is RetrievalMode.RETRIEVAL_LED

def test_advisory_phases():
    for phase in ("brainstorm", "triage"):
        assert PHASE_TIERS[phase].mode is RetrievalMode.ADVISORY

def test_execute_has_no_external_retrieval():
    assert PHASE_TIERS["execute"].mode is RetrievalMode.NONE
    assert PHASE_TIERS["execute"].sources == ()

def test_resolve_is_writeback_only():
    assert PHASE_TIERS["resolve"].mode is RetrievalMode.WRITEBACK

def test_propose_sources_include_lessons_and_knowledge():
    s = PHASE_TIERS["propose"].sources
    assert "lessons" in s and "knowledge" in s and "run_history" in s

def test_phase_tier_unknown_phase_is_inert_not_error():
    # Unknown phase -> a NONE tier, never a raise (engine must not block).
    assert phase_tier("not_a_phase").mode is RetrievalMode.NONE
```
Run → **FAIL** (no module).

**1b. Minimal impl** — create `skills/uacp-core/scripts/engines/oracle/__init__.py` (empty docstring) and `skills/uacp-core/scripts/engines/oracle/tier_config.py`:
```python
"""Per-phase retrieval gating for the Oracle. PURE: no I/O, no ML deps.

Codifies design doc C's "Per-phase gating" table. Mirrors the codify-grammar-
to-code convention used by engines/domain/phase_transitions.py: the table is the
code default; a project may override knobs via [oracle] in config (later task),
but the phase->mode/source mapping itself is structural and lives here.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field


class RetrievalMode(enum.Enum):
    RETRIEVAL_LED = "retrieval_led"   # mandatory-before-reasoning when enabled (propose/plan/verify)
    ADVISORY = "advisory"             # surfaced, non-blocking (brainstorm/triage)
    NONE = "none"                     # execute: intra-run only; unknown phases
    WRITEBACK = "writeback"           # resolve: writes lessons, no retrieval


@dataclass(frozen=True)
class PhaseTier:
    mode: RetrievalMode
    sources: tuple[str, ...] = field(default_factory=tuple)


PHASE_TIERS: dict[str, PhaseTier] = {
    "brainstorm": PhaseTier(RetrievalMode.ADVISORY, ("knowledge", "lessons", "run_history", "honcho")),
    "triage": PhaseTier(RetrievalMode.ADVISORY, ("lessons", "knowledge", "run_history", "scope_overlap", "honcho")),
    "propose": PhaseTier(RetrievalMode.RETRIEVAL_LED, ("lessons", "knowledge", "run_history", "honcho")),
    "plan": PhaseTier(RetrievalMode.RETRIEVAL_LED, ("lessons", "knowledge", "scope_overlap")),
    "execute": PhaseTier(RetrievalMode.NONE, ()),
    "verify": PhaseTier(RetrievalMode.RETRIEVAL_LED, ("lessons", "knowledge", "run_history", "gate_ledger")),
    "resolve": PhaseTier(RetrievalMode.WRITEBACK, ()),
}


def phase_tier(phase: str) -> PhaseTier:
    """Return the tier for a phase; unknown phase -> inert NONE (never raises)."""
    return PHASE_TIERS.get(phase, PhaseTier(RetrievalMode.NONE, ()))
```
Run → **PASS**. Commit.

---

## Task 2 `[C-floor]` — Provider packets + trust classes

Normalized source output with trust classes (design §"provider packets"; ported from Trustless ACP `providers.py`).

**2a. Failing test** — `tests/unit/uacp_oracle/test_packets.py`:
```python
import pytest
from engines.oracle.packets import (
    ProviderPacket, TrustClass, advisory_requires_evidence,
)

def test_trust_classes_exist():
    assert {t.value for t in TrustClass} == {
        "authoritative_record", "normative_reference", "advisory_signal",
    }

def test_advisory_packet_requires_evidence():
    p = ProviderPacket(
        source="lessons", trust_class=TrustClass.ADVISORY_SIGNAL,
        payload={"id": "L1"}, repo_commit="abc123",
    )
    assert p.evidence_required is True

def test_authoritative_packet_does_not_require_evidence():
    p = ProviderPacket(
        source="run_history", trust_class=TrustClass.AUTHORITATIVE_RECORD,
        payload={"run_id": "r1"}, repo_commit="abc123",
    )
    assert p.evidence_required is False

def test_evidence_required_cannot_be_forced_false_for_advisory():
    # A hint can never be smuggled in as proof.
    p = ProviderPacket(
        source="lessons", trust_class=TrustClass.ADVISORY_SIGNAL,
        payload={}, repo_commit="x", evidence_required=False,
    )
    assert p.evidence_required is True

def test_cache_key_zeroes_timestamps():
    # Determinism discipline: timestamps removed before cache-prefix injection.
    p = ProviderPacket(
        source="lessons", trust_class=TrustClass.ADVISORY_SIGNAL,
        payload={"id": "L1", "extracted_at": "2026-06-17T00:00:00Z", "score": 0.4},
        repo_commit="abc123",
    )
    ck = p.cache_payload()
    assert "extracted_at" not in ck and ck["id"] == "L1"
```
Run → **FAIL**.

**2b. Minimal impl** — `skills/uacp-core/scripts/engines/oracle/packets.py`:
```python
"""Normalized source output: provider packets + trust classes. PURE, no I/O.

Ported from Trustless ACP providers.py. A source returns packets; advisory
packets ALWAYS carry evidence_required=True so a phase cannot treat a hint as
proof (design doc C). Timestamps are stripped for the deterministic cache prefix.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

_TS_KEYS = frozenset({"extracted_at", "timestamp", "started_at", "ended_at", "ts"})


class TrustClass(enum.Enum):
    AUTHORITATIVE_RECORD = "authoritative_record"   # run-state, ledger: fact
    NORMATIVE_REFERENCE = "normative_reference"     # knowledge: how-it-should-be
    ADVISORY_SIGNAL = "advisory_signal"             # lessons/Honcho hints: needs corroboration


@dataclass(frozen=True)
class ProviderPacket:
    source: str
    trust_class: TrustClass
    payload: dict[str, Any]
    repo_commit: str
    evidence_required: bool = field(default=False)
    score: float | None = None

    def __post_init__(self) -> None:
        # Two-line rule (advisory hints can NEVER be marked evidence-satisfying):
        # • advisory  → always True (a hint cannot serve as proof)
        # • authoritative/normative → respect the caller's value as-is
        if self.trust_class is TrustClass.ADVISORY_SIGNAL:
            object.__setattr__(self, "evidence_required", True)

    def cache_payload(self) -> dict[str, Any]:
        """Payload with timestamps zeroed out, for the stable cache prefix."""
        return {k: v for k, v in self.payload.items() if k not in _TS_KEYS}


def advisory_requires_evidence(trust_class: TrustClass) -> bool:
    return trust_class is TrustClass.ADVISORY_SIGNAL
```
> Implementation note: the `__post_init__` uses the two-line rule: advisory ⇒ `evidence_required=True` (forced); authoritative/normative ⇒ respect the caller's `evidence_required` value as designed. Keep Task-2 tests as the binding contract.

Run → **PASS**. Commit.

---

## Task 3 `[C-floor]` — Deterministic run-state source

The deterministic tier: prefix/structured-key lookup over run-state, reusing `engines.io.loaders`. **No embeddings, no ML deps** (design tier table row 1).

**3a. Failing test** — `tests/unit/uacp_oracle/test_source_runstate.py`:
```python
from engines.oracle.sources.runstate import query_run_history
from engines.oracle.packets import TrustClass

def test_returns_authoritative_packets_for_matching_runs(temp_uacp_root):
    base = temp_uacp_root / ".uacp"
    (base / "state" / "runs" / "r1.yaml").write_text(
        "run_id: r1\ndomains: [auth]\nphase: resolved\n")
    packets = query_run_history(temp_uacp_root, domains=["auth"])
    assert packets and packets[0].trust_class is TrustClass.AUTHORITATIVE_RECORD
    assert packets[0].evidence_required is False
    assert packets[0].payload["run_id"] == "r1"

def test_no_match_returns_empty_never_raises(temp_uacp_root):
    assert query_run_history(temp_uacp_root, domains=["nonexistent"]) == []

def test_missing_state_dir_is_empty_not_error(tmp_path):
    # Cold clone: no .uacp/state -> "no active run", not a crash.
    assert query_run_history(tmp_path, domains=["auth"]) == []

def test_uses_no_ml_deps(monkeypatch):
    # Hard guard: importing/calling the deterministic source must not import lancedb.
    import sys
    monkeypatch.setitem(sys.modules, "lancedb", None)  # poison
    from engines.oracle.sources import runstate  # noqa: F401  must import clean
```
Run → **FAIL**.

**3b. Minimal impl** — `skills/uacp-core/scripts/engines/oracle/sources/__init__.py` (empty) and `skills/uacp-core/scripts/engines/oracle/sources/runstate.py`:
```python
"""Deterministic run-state source. Reuses engines.io.loaders. No ML deps.

Looks up resolved/in-flight runs by structured key (domain/phase/run_id) for the
run_history / scope_overlap / gate_ledger active sources. Returns AUTHORITATIVE
packets (facts, evidence_required=False). Never raises (design: sources are
non-fatal; a missing source is logged to sources_skipped, never blocks).
"""
from __future__ import annotations

from pathlib import Path

from engines.io import loaders
from engines.oracle.packets import ProviderPacket, TrustClass
from engines.oracle.repo import repo_commit


def query_run_history(workspace: str | Path, *, domains: list[str] | None = None,
                      run_id: str | None = None) -> list[ProviderPacket]:
    ws = Path(str(workspace))
    out: list[ProviderPacket] = []
    commit = repo_commit(ws)
    want = {d.lower() for d in (domains or [])}
    for manifest_path in loaders.glob_in_workspace(ws, "state/runs/*.yaml"):
        rid = manifest_path.stem
        loaded = loaders.load_manifest(ws, rid)
        if loaded.error is not None or loaded.value is None:
            continue
        raw = loaded.value.raw
        run_domains = {str(d).lower() for d in (raw.get("domains") or [])}
        if want and not (want & run_domains):
            continue
        if run_id and rid != run_id:
            continue
        out.append(ProviderPacket(
            source="run_history",
            trust_class=TrustClass.AUTHORITATIVE_RECORD,
            payload={"run_id": rid, **{k: raw.get(k) for k in ("phase", "domains")}},
            repo_commit=commit,
        ))
    return out
```
Also add `skills/uacp-core/scripts/engines/oracle/repo.py` with a tiny, never-raises `repo_commit(workspace) -> str` (shell out to `git -C <ws> rev-parse HEAD`, return `""` on failure). Keep it dependency-free.

> Note: `glob_in_workspace` globs under `.uacp/`, so `"state/runs/*.yaml"` is correct relative to the governed base — matches `loaders.load_manifest`'s `state/runs/<id>.yaml`.

Run → **PASS**. Commit.

---

## Task 4 `[C-semantic]` — Store interface + LanceDB impl (lazy)

The retrieval store behind a thin interface so `sqlite-vec + FTS5` stays a swap-in (design §"Store"). LanceDB import is **lazy + optional**.

**4a. Failing test** — `tests/unit/uacp_oracle/test_store.py`:
```python
import pytest
from engines.oracle.store import get_store, StoreUnavailable

def test_store_interface_has_required_methods():
    from engines.oracle.store import VectorStore
    for m in ("upsert", "dense_search", "fts_search", "rrf_hybrid", "available"):
        assert hasattr(VectorStore, m)

def test_lancedb_store_reports_unavailable_when_dep_missing(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "lancedb", None)  # simulate not installed
    store = get_store("lancedb", index_path="/tmp/does-not-matter")
    assert store.available() is False

def test_get_store_unknown_backend_raises():
    with pytest.raises(StoreUnavailable):
        get_store("redis-vector", index_path="/tmp/x")

def test_floor_path_does_not_require_store(monkeypatch):
    # The store module must import with no ML deps present.
    import sys
    monkeypatch.setitem(sys.modules, "lancedb", None)
    import importlib
    import engines.oracle.store as s
    importlib.reload(s)
```
Run → **FAIL**.

**4b. Minimal impl** — `skills/uacp-core/scripts/engines/oracle/store.py`:
```python
"""Vector+FTS store behind a thin interface. LanceDB is the default; sqlite-vec
is the documented lighter swap-in. The store dep is OPTIONAL + lazily imported —
available() is the single gate the resolver checks before using semantic legs.
Index lives at .uacp/knowledge/indexes/ and is DERIVED/REBUILDABLE from the OKF
corpus files (design doc B). Never raises on a missing dep -> available()==False.
"""
from __future__ import annotations

import importlib
from typing import Any, Protocol


class StoreUnavailable(RuntimeError):
    pass


class VectorStore(Protocol):
    def available(self) -> bool: ...
    def upsert(self, rows: list[dict[str, Any]]) -> None: ...
    def dense_search(self, vector: list[float], k: int) -> list[dict[str, Any]]: ...
    def fts_search(self, query: str, k: int) -> list[dict[str, Any]]: ...
    def rrf_hybrid(self, vector: list[float] | None, query: str, k: int) -> list[dict[str, Any]]: ...


def _lancedb():
    try:
        return importlib.import_module("lancedb")
    except Exception:
        return None


class LanceDBStore:
    def __init__(self, index_path: str) -> None:
        self.index_path = index_path
        self._db = None

    def available(self) -> bool:
        return _lancedb() is not None

    def _conn(self):
        lancedb = _lancedb()
        if lancedb is None:
            raise StoreUnavailable("lancedb not installed")
        if self._db is None:
            self._db = lancedb.connect(self.index_path)
        return self._db

    def upsert(self, rows): self._conn()  # ... table create/add; native FTS index
    def dense_search(self, vector, k): ...
    def fts_search(self, query, k): ...
    def rrf_hybrid(self, vector, query, k): ...  # LanceDB native hybrid + RRF (k=60)


def get_store(backend: str, *, index_path: str) -> VectorStore:
    if backend == "lancedb":
        return LanceDBStore(index_path)
    if backend == "sqlite-vec":
        # documented alternate behind the same interface; brute-force KNN suffices
        from engines.oracle.store_sqlite import SqliteVecStore
        return SqliteVecStore(index_path)
    raise StoreUnavailable(f"unknown store backend: {backend!r}")
```
Leave `dense_search`/`fts_search`/`rrf_hybrid`/`upsert` bodies as TODO stubs that raise `StoreUnavailable` when the dep is missing — flesh them out under the hybrid-pipeline task (Task 8). `store_sqlite.py` may be a stub class for now (only `available()` needs to work); note RRF k=60 lives here per design §pipeline step 3.

Run → **PASS**. Commit.

---

## Task 5 `[C-floor]` — Serving resolver (`url override > embedded > floor`), per role, lazy

The heart of the model-stack decision (design §"Model stack" + §Degradation). Per role: URL override wins; else embedded GGUF; else floor. **Floor must work with NO ML deps.**

**5a. Failing test** — `tests/unit/uacp_oracle/test_resolver.py`:
```python
import pytest
from engines.oracle.serving import resolve_role, ServingMode

def _cfg(**roles):
    return {"enabled": True, "store": "lancedb", **roles}

def test_url_override_wins(monkeypatch):
    cfg = _cfg(embedding={"model": "bge-m3", "url": "http://localhost:8000/v1/embeddings"})
    r = resolve_role("embedding", cfg, deps_present=True)
    assert r.mode is ServingMode.URL and r.url.endswith("/v1/embeddings")

def test_embedded_when_no_url_and_deps_present():
    cfg = _cfg(embedding={"model": "bge-m3", "url": ""})
    r = resolve_role("embedding", cfg, deps_present=True)
    assert r.mode is ServingMode.EMBEDDED and r.model == "bge-m3"

def test_floor_when_no_url_and_deps_absent():
    # No URL + llama.cpp binding absent -> FLOOR (keyword+structured+BES).
    cfg = _cfg(embedding={"model": "bge-m3", "url": ""})
    r = resolve_role("embedding", cfg, deps_present=False)
    assert r.mode is ServingMode.FLOOR

def test_floor_when_oracle_disabled():
    cfg = {"enabled": False, "embedding": {"model": "bge-m3", "url": ""}}
    r = resolve_role("embedding", cfg, deps_present=True)
    assert r.mode is ServingMode.FLOOR

def test_never_both_url_and_embedded():
    cfg = _cfg(rerank={"model": "qwen3-reranker-0.6b", "url": "http://x/v1/rerank"})
    r = resolve_role("rerank", cfg, deps_present=True)
    assert r.mode is ServingMode.URL  # exactly one, never both
```
Run → **FAIL**.

**5b. Minimal impl** — `skills/uacp-core/scripts/engines/oracle/serving.py`:
```python
"""Per-role serving resolver. Precedence: url override > embedded default > floor.

Per role it is one OR the other, never both (design §Model stack). The embedded
default needs the optional in-process llama.cpp binding (deps_present); absent it
(and with no URL) the role degrades to the FLOOR (keyword+structured+BES, no
models). enabled=false forces FLOOR for every role.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass


class ServingMode(enum.Enum):
    URL = "url"
    EMBEDDED = "embedded"
    FLOOR = "floor"


@dataclass(frozen=True)
class RoleServing:
    role: str
    mode: ServingMode
    model: str = ""
    url: str = ""


def embedded_runtime_present() -> bool:
    """True iff the in-process llama.cpp binding can be imported. Lazy + never raises."""
    import importlib
    for cand in ("llama_cpp",):  # exact binding settled at impl; keep behind this helper
        try:
            importlib.import_module(cand)
            return True
        except Exception:
            continue
    return False


def resolve_role(role: str, oracle_cfg: dict, *, deps_present: bool | None = None) -> RoleServing:
    if not oracle_cfg.get("enabled", False):
        return RoleServing(role, ServingMode.FLOOR)
    role_cfg = oracle_cfg.get(role) or {}
    url = str(role_cfg.get("url") or "").strip()
    model = str(role_cfg.get("model") or "")
    if url:
        return RoleServing(role, ServingMode.URL, model=model, url=url)
    present = embedded_runtime_present() if deps_present is None else deps_present
    if present:
        return RoleServing(role, ServingMode.EMBEDDED, model=model)
    return RoleServing(role, ServingMode.FLOOR, model=model)
```
Run → **PASS**. Commit.

---

## Task 6 `[C-semantic]` — Embedding client (embedded + URL)

Dense vectors via embedded GGUF (BGE-M3 default) or a `/v1/embeddings` URL (design §Model stack: TEI `/embed`, vLLM `/v1/embeddings`, Ollama). Both deps lazy.

**6a. Failing test** — `tests/unit/uacp_oracle/test_embedding_client.py`:
```python
import pytest
from engines.oracle.embedding import embed_texts, EmbeddingUnavailable
from engines.oracle.serving import RoleServing, ServingMode

def test_floor_mode_has_no_embeddings():
    with pytest.raises(EmbeddingUnavailable):
        embed_texts(["hi"], RoleServing("embedding", ServingMode.FLOOR))

def test_url_mode_posts_to_endpoint(monkeypatch):
    calls = {}
    class _Resp:
        def raise_for_status(self): pass
        def json(self): return {"data": [{"embedding": [0.1, 0.2]}]}
    class _Client:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, json, headers=None):
            calls["url"] = url; calls["json"] = json; return _Resp()
    import engines.oracle.embedding as em
    monkeypatch.setattr(em, "_httpx_client", lambda *a, **k: _Client())
    out = embed_texts(["hi"], RoleServing("embedding", ServingMode.URL,
                                          model="bge-m3", url="http://x/v1/embeddings"))
    assert out == [[0.1, 0.2]] and calls["url"].endswith("/v1/embeddings")

def test_embedded_mode_unavailable_without_binding(monkeypatch):
    import engines.oracle.embedding as em
    monkeypatch.setattr(em, "_load_embedded_model", lambda model: None)
    with pytest.raises(EmbeddingUnavailable):
        embed_texts(["hi"], RoleServing("embedding", ServingMode.EMBEDDED, model="bge-m3"))
```
Run → **FAIL**.

**6b. Minimal impl** — `skills/uacp-core/scripts/engines/oracle/embedding.py`. URL mode posts `{"input": texts, "model": model}` to `serving.url` via a lazily-imported httpx client (`_httpx_client()` wrapper so tests can monkeypatch it); reads `api_key_env` from env only in URL mode (never the key itself). Embedded mode calls `_load_embedded_model(model)` (lazy llama.cpp binding) and returns `None` when absent → raise `EmbeddingUnavailable`. FLOOR mode always raises `EmbeddingUnavailable` (the pipeline catches it and uses the keyword leg only). Run → **PASS**. Commit.

---

## Task 7 `[C-semantic]` — Rerank client (embedded + URL)

Cross-encoder/LLM rerank: embedded (Qwen3-Reranker-0.6B default) or URL. Note the servability matrix (design §Model stack): TEI `/rerank` uses `{query, texts}`; vLLM is Cohere-compatible `/v1/rerank`. **Ollama has no rerank endpoint — not a target here.**

**7a. Failing test** — `tests/unit/uacp_oracle/test_rerank_client.py`:
```python
import pytest
from engines.oracle.rerank import rerank, RerankUnavailable
from engines.oracle.serving import RoleServing, ServingMode

def test_floor_returns_input_order_unchanged():
    # Rerank disabled/unavailable -> skip rerank, keep RRF-fused order (design Degradation).
    docs = [{"id": "a"}, {"id": "b"}]
    with pytest.raises(RerankUnavailable):
        rerank("q", docs, RoleServing("rerank", ServingMode.FLOOR))

def test_url_mode_tei_shape(monkeypatch):
    seen = {}
    class _Resp:
        def raise_for_status(self): pass
        def json(self): return [{"index": 1, "score": 0.9}, {"index": 0, "score": 0.1}]
    class _Client:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, json, headers=None): seen["json"] = json; return _Resp()
    import engines.oracle.rerank as rr
    monkeypatch.setattr(rr, "_httpx_client", lambda *a, **k: _Client())
    out = rerank("q", [{"id": "a"}, {"id": "b"}],
                 RoleServing("rerank", ServingMode.URL, model="bge-reranker-v2-m3", url="http://x/rerank"))
    assert [d["id"] for d in out] == ["b", "a"]  # reordered by score desc
    assert "query" in seen["json"] and "texts" in seen["json"]
```
Run → **FAIL**.

**7b. Minimal impl** — `skills/uacp-core/scripts/engines/oracle/rerank.py`. URL mode sends the TEI `{query, texts}` shape (note in a docstring that vLLM Cohere `/v1/rerank` is a config-selected variant), reorders docs by returned score desc. Embedded mode uses the lazy binding; absent → `RerankUnavailable`. FLOOR → `RerankUnavailable`. The **pipeline** (Task 8) catches `RerankUnavailable` and returns the RRF order untouched (design Degradation: "Rerank disabled/unavailable → skip rerank; return RRF-fused order"). Run → **PASS**. Commit.

---

## Task 8 `[C-semantic]` — Query expansion (optional) + the hybrid pipeline

Assemble the QMD-shaped semantic pipeline: **expand → hybrid(dense+keyword) → RRF → rerank → BES/tag overlay** (design §"Retrieval pipeline").

**8a. Failing test (query expansion)** — `tests/unit/uacp_oracle/test_query_expansion.py`:
```python
from engines.oracle.expansion import expand_query
from engines.oracle.serving import RoleServing, ServingMode

def test_floor_or_disabled_returns_raw_query_only():
    # optional; skip -> raw query (design step 1).
    assert expand_query("auth bug", RoleServing("query_expansion", ServingMode.FLOOR)) == ["auth bug"]

def test_disabled_via_enabled_false_returns_raw():
    assert expand_query("auth bug", RoleServing("query_expansion", ServingMode.EMBEDDED), enabled=False) == ["auth bug"]
```

**8b. Failing test (pipeline)** — `tests/unit/uacp_oracle/test_pipeline.py`:
```python
from engines.oracle.pipeline import semantic_retrieve
from engines.oracle.packets import TrustClass

class _FakeStore:
    def available(self): return True
    def rrf_hybrid(self, vector, query, k):
        return [{"id": "L1", "type": "lesson", "domains": ["auth"], "invariants": ["I1"],
                 "bes": 0.9, "severity": "CRITICAL", "body": "..."},
                {"id": "K1", "type": "pattern", "domains": ["auth"], "body": "..."}]

def test_pipeline_runs_floor_when_no_models(monkeypatch):
    # deps absent -> dense leg skipped, FTS/keyword leg + RRF only, no rerank.
    out = semantic_retrieve(
        query="auth", store=_FakeStore(), domains=["auth"], invariants=["I1"],
        embedding=None, reranker=None, repo_commit="abc",
    )
    assert out and out[0].payload["id"] in {"L1", "K1"}

def test_bes_overlay_gates_and_ranks_lessons(monkeypatch):
    # relevance gate (>=1) then rank by relevance + bes_bonus (design doc B).
    out = semantic_retrieve(
        query="auth", store=_FakeStore(), domains=["auth"], invariants=["I1"],
        embedding=None, reranker=None, repo_commit="abc",
    )
    lessons = [p for p in out if p.payload.get("type") == "lesson"]
    assert lessons and lessons[0].trust_class is TrustClass.ADVISORY_SIGNAL
    assert lessons[0].evidence_required is True
```
Run → **FAIL**.

**8c. Minimal impl** — `skills/uacp-core/scripts/engines/oracle/expansion.py` (raw-query passthrough when FLOOR/disabled; else multi-query via the chat endpoint / embedded binding) and `skills/uacp-core/scripts/engines/oracle/pipeline.py`:
- `semantic_retrieve(query, store, domains, invariants, file=None, embedding, reranker, repo_commit, intra_run=False)`:
  1. expand (optional);
  2. dense leg only if `embedding` is usable (else skip — keyword leg still runs);
  3. `store.rrf_hybrid(...)` (k=60) for fused candidates;
  4. rerank via `reranker` if usable, catching `RerankUnavailable` → keep RRF order;
  5. **BES/tag overlay for lessons only:** compute `relevance = intra_run(+5) + domain(+1·n) + invariant(+2·n) + path(+3)`, **gate `relevance >= 1`**, then rank by `relevance + bes_bonus` importing the tier function from Plan B — `from engines.domain.corpus import bes_bonus` — do NOT re-implement the 5-tier table (it would drift from Plan B's source of truth). Knowledge items skip BES.
- Lessons → `ADVISORY_SIGNAL` packets (evidence_required True via `__post_init__`); knowledge → `NORMATIVE_REFERENCE`.

Run → **PASS**. Commit.

---

## Task 9 `[C-floor]` — Honcho memory source

Memory packets (operator/arch prefs); read all phases, write prefs only at resolve (design tier table row 3 + Degradation "No Honcho → skip memory packets").

**9a. Failing test** — `tests/unit/uacp_oracle/test_source_honcho.py`:
```python
from engines.oracle.sources.honcho import query_honcho
from engines.oracle.packets import TrustClass

def test_disabled_honcho_returns_empty():
    assert query_honcho("prefs", {"enabled": False, "url": ""}, repo_commit="x") == []

def test_unreachable_honcho_is_skipped_not_fatal(monkeypatch):
    import engines.oracle.sources.honcho as h
    def _boom(*a, **k): raise OSError("connection refused")
    monkeypatch.setattr(h, "_httpx_client", _boom)
    assert query_honcho("prefs", {"enabled": True, "url": "http://x"}, repo_commit="x") == []

def test_packets_are_advisory(monkeypatch):
    import engines.oracle.sources.honcho as h
    class _C:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, *a, **k):
            class R:
                def raise_for_status(self): pass
                def json(self): return {"memories": [{"text": "prefers worktree isolation"}]}
            return R()
    monkeypatch.setattr(h, "_httpx_client", lambda *a, **k: _C())
    out = query_honcho("prefs", {"enabled": True, "url": "http://x"}, repo_commit="x")
    assert out and out[0].trust_class is TrustClass.ADVISORY_SIGNAL
```
Run → **FAIL**.

**9b. Minimal impl** — `skills/uacp-core/scripts/engines/oracle/sources/honcho.py`. Lazy httpx via `_httpx_client()`; `enabled=False` or empty url → `[]`; any exception → `[]` (non-fatal, caller logs `sources_skipped`). Returns `ADVISORY_SIGNAL` packets. Run → **PASS**. Commit.

> OPEN ITEM (carry forward, do not block): exact Honcho query API + how memory packets rank against lessons/knowledge (design §Open items). Stub the query shape; mark TODO.

---

## Task 10 `[C-floor]` — Aggregator compose + per-phase gating

Compose the three tiers under `PHASE_TIERS`; emit ranked packets + `metadata.sources_skipped` (design §Architecture, §"Each source is independent and non-fatal").

**10a. Failing test** — `tests/unit/uacp_oracle/test_aggregator.py`:
```python
from engines.oracle.aggregator import oracle_query

def test_execute_phase_returns_no_external_retrieval(temp_uacp_root):
    res = oracle_query(workspace=temp_uacp_root, phase="execute", project="p", query="x")
    assert res["packets"] == []
    assert "execute" in res["metadata"].get("note", "execute")

def test_propose_phase_collects_configured_sources(temp_uacp_root):
    base = temp_uacp_root / ".uacp"
    (base / "state" / "runs" / "r1.yaml").write_text("run_id: r1\ndomains: [auth]\nphase: resolved\n")
    res = oracle_query(workspace=temp_uacp_root, phase="propose", project="p",
                       domains=["auth"], query="auth bug")
    sources = {p.source for p in res["packets"]}
    assert "run_history" in sources

def test_unreachable_source_is_logged_not_fatal(temp_uacp_root, monkeypatch):
    import engines.oracle.aggregator as agg
    monkeypatch.setattr(agg, "_semantic_packets", lambda *a, **k: (_ for _ in ()).throw(OSError("down")))
    res = oracle_query(workspace=temp_uacp_root, phase="plan", project="p", query="x", domains=["auth"])
    assert "semantic" in res["metadata"]["sources_skipped"]

def test_disabled_oracle_serves_floor(temp_uacp_root):
    # enabled=false -> floor: structured run-state + keyword + BES, no models, no crash.
    res = oracle_query(workspace=temp_uacp_root, phase="propose", project="p",
                       query="x", oracle_cfg={"enabled": False})
    assert "packets" in res and "sources_skipped" in res["metadata"]
```
Run → **FAIL**.

**10b. Minimal impl** — `skills/uacp-core/scripts/engines/oracle/aggregator.py`:
- `oracle_query(*, workspace, phase, project, domains=None, invariants=None, file=None, query=None, oracle_cfg=None) -> dict`.
- Load `oracle_cfg` from `get_config(workspace).model_extra.get("oracle", {"enabled": False})` when not passed (Task 12 adds the config). Use `get_config` (cached, mtime-aware) rather than `load_config(...)` per query — calling `load_config` on every query re-parses the TOML file each time.
- Look up `phase_tier(phase)`; if `mode is NONE` or `WRITEBACK`, return `{"packets": [], "metadata": {...}}`.
- For each source named in the tier, call its function inside `try/except` → on any exception append the source name to `sources_skipped` (never raise).
- `run_history`/`scope_overlap`/`gate_ledger` → `runstate`; `lessons`/`knowledge` → `_semantic_packets` (resolves roles via `serving.resolve_role`, builds the store via `store.get_store`, runs `pipeline.semantic_retrieve`); `honcho` → `sources.honcho`.
- Return `{"packets": [...sorted...], "metadata": {"phase": phase, "mode": mode.value, "sources_skipped": [...], "repo_commit": ...}}`.

Run → **PASS**. Commit.

---

## Task 11 `[C-floor]` — `uacp_oracle_query` READ-ONLY governed tool

Register the tool in the Hermes adapter exactly like the existing governed writers, but **read-only — no state writes** (design §"The governed tool"). Input `{phase, project, domains?, invariants?, file?, query?}`; output ranked packets + `metadata.sources_skipped`.

**11a. Failing test** — `tests/unit/uacp_oracle/test_oracle_tool.py`:
```python
import json

def test_handler_is_read_only_no_writers_invoked(temp_uacp_root, monkeypatch):
    # The handler must NOT call any uacp_*_write / ledger / registry / escalation writer.
    import uacp_guardian as plugin  # the Hermes adapter package (__init__.py)
    forbidden = [
        "_handle_uacp_state_write", "_handle_uacp_gate_ledger_append",
        "_handle_uacp_run_registry_update", "_handle_uacp_escalation_event",
        "_handle_uacp_artifact_write", "_handle_uacp_doc_write", "_handle_uacp_config_write",
    ]
    for name in forbidden:
        if hasattr(plugin, name):
            monkeypatch.setattr(plugin, name,
                lambda *a, **k: (_ for _ in ()).throw(AssertionError("write attempted")))
    out = plugin._handle_uacp_oracle_query({"phase": "propose", "project": "p", "query": "x"})
    parsed = json.loads(out)
    assert "packets" in parsed and "metadata" in parsed

def test_tool_requires_phase_and_project(temp_uacp_root):
    import uacp_guardian as plugin
    parsed = json.loads(plugin._handle_uacp_oracle_query({"query": "x"}))
    assert "error" in parsed

def test_tool_schema_has_no_write_authority_fields():
    # read-only: no authority_artifact / content / target_path / declared_side_effects in schema.
    import uacp_guardian as plugin
    schema = plugin._oracle_query_schema()
    props = set(schema["parameters"]["properties"])
    assert props.isdisjoint({"content", "target_path", "authority_artifact", "declared_side_effects"})
    assert "phase" in props and "project" in props

def test_registered_in_register(monkeypatch):
    import uacp_guardian as plugin
    names = []
    class _Ctx:
        def register_hook(self, *a, **k): pass
        def register_tool(self, *, name, **k): names.append(name)
    plugin.register(_Ctx())
    assert "uacp_oracle_query" in names
```
Run → **FAIL**.

**11b. Minimal impl** — in `runtime-adapters/hermes/plugins/uacp_guardian/__init__.py`:
- Add a lazy import path to the oracle package (the adapter already inserts `uacp-state/scripts`; add `engines` is importable via the core scripts dir — confirm `engines.oracle` imports; if not, push `skills/uacp-core/scripts` onto `sys.path` the same way `_STATE_SCRIPTS` is added).
- Add `_oracle_query_schema()` returning a schema whose `properties` are ONLY `{phase, project, domains, invariants, file, query}` with `required = ["phase", "project"]` — no write/authority/side-effect fields.
- Add `_handle_uacp_oracle_query(args, **_)`: validate `phase`+`project` present (else `{"error": ...}`); call `engines.oracle.aggregator.oracle_query(workspace=_policy().uacp_root, ...)`; serialize packets to plain dicts; return `json.dumps({"packets": [...], "metadata": {...}})`. It calls **no writer**.
- In `register(ctx)`, add a `ctx.register_tool(name="uacp_oracle_query", toolset="uacp_guardian", schema=_oracle_query_schema(), handler=_handle_uacp_oracle_query, description="UACP read-only retrieval aggregator")`.

> DESIGN-VS-CODE NOTE for the implementer: governed tools are NOT registered in `core.py` (that is the kernel: `Guardian`/`Heartgate` classes). They are registered in the Hermes adapter `__init__.py` via `register(ctx)` + `ctx.register_tool(...)`. Because `uacp_oracle_query` is read-only it does NOT go through `_validate_common_write_args` and is NOT added to `[guardian] self_attesting_tools` (that list is for path-bounded writers).

**REQUIRED — classification is not optional:** `uacp_oracle_query` is a plugin-registered tool, so `classification_by_provider["plugin"] = "require_explicit_classification"` applies. Without an explicit entry, the Guardian falls through to `runtime.extension` → treats it as protected → Layer-B blocks it with `allowlist_miss` whenever it is called during propose/plan/verify (those calls carry `uacp_phase` and the tool is not in their `allowed_tools`).

**Required step in this task:** add `uacp_oracle_query = "read.local"` under `[guardian.tool_classification]` in `config/uacp.toml`. This makes Guardian classify the tool as a local read, so Layer-B's "reads pass" guard skips it and it need not appear in any phase `allowed_tools` list.

Also add a test asserting the classification (add to `test_oracle_tool.py`):
```python
def test_oracle_query_classified_read_local():
    # Guardian must see read.local so Layer-B's "reads pass" guard skips it.
    from config import load_config
    cfg = load_config(project_root=None)
    classifications = cfg.model_extra.get("guardian", {}).get("tool_classification", {})
    assert classifications.get("uacp_oracle_query") == "read.local", (
        "uacp_oracle_query must be classified read.local in [guardian.tool_classification] "
        "so Guardian Layer-B does not block it with allowlist_miss during propose/plan/verify"
    )
```

Do NOT add `uacp_oracle_query` to `[guardian] self_attesting_tools` and do NOT add it to `_validate_common_write_args` — those are for path-bounded writers only.

Run → **PASS**. Commit.

---

## Task 12 `[C-floor]` — `[oracle]` config + degradation wiring

Add the config sections (design §Config) and wire `aggregator` to read them.

**12a. Failing test** — `tests/unit/uacp_oracle/test_oracle_config.py`:
```python
from config import load_config

def test_oracle_section_defaults_to_disabled_floor():
    cfg = load_config(project_root=None)
    oracle = cfg.model_extra["oracle"]
    assert oracle["enabled"] is False
    assert oracle["store"] == "lancedb"
    assert oracle["index_path"] == ".uacp/knowledge/indexes/"

def test_per_role_url_empty_means_embedded_default():
    cfg = load_config(project_root=None)
    oracle = cfg.model_extra["oracle"]
    assert oracle["embedding"]["url"] == "" and oracle["embedding"]["model"] == "bge-m3"
    assert oracle["rerank"]["model"] == "qwen3-reranker-0.6b"
    assert oracle["query_expansion"]["enabled"] is True

def test_project_override_can_enable_and_set_url(tmp_path):
    (tmp_path / ".uacp").mkdir()
    (tmp_path / ".uacp" / "config.toml").write_text(
        '[oracle]\nenabled = true\n[oracle.embedding]\nurl = "http://localhost:8000/v1/embeddings"\n')
    cfg = load_config(project_root=tmp_path)
    oracle = cfg.model_extra["oracle"]
    assert oracle["enabled"] is True
    assert oracle["embedding"]["url"].endswith("/v1/embeddings")
    # deep merge preserves sibling defaults
    assert oracle["embedding"]["model"] == "bge-m3"
```
Run → **FAIL**.

**12b. Minimal impl** — append to `config/uacp.toml` (after `[memory...]`, before/near other reserved sections), verbatim from design §Config (`[oracle]`, `[oracle.embedding]`, `[oracle.rerank]`, `[oracle.query_expansion]`, `[oracle.honcho]`). `[oracle]` is retained via `UacpConfig`'s `extra="allow"` (no new pydantic field needed — mirror how `[council]`/`[bridges]` are kept). Then update `aggregator.oracle_query` to default `oracle_cfg` from `get_config(workspace).model_extra.get("oracle", {"enabled": False})` (cached accessor — see Task 10 note). Confirm Degradation table holds: `enabled=false` → floor; URL set → URL; no URL + binding present → embedded; rerank unavailable → RRF order; no Honcho → skip.

**FIX — `index_path` is a raw config string, not a resolver key.** Read `oracle["index_path"]` directly as a string (default `.uacp/knowledge/indexes/`). Do NOT route it through `cfg.resolve(...)` — the resolver hard-raises on unknown `[paths]` keys, and Plan B does NOT add an `indexes` path key. The index location is Plan C's concern entirely; resolve it relative to `workspace` with `Path(workspace) / index_path`.

Run → **PASS** (and re-run the full suite). Commit.

---

## Task 13 `[C-floor]` — Retrieval-led integration hooks (propose/plan/verify) + advisory (brainstorm/triage)

Document the integration points in the lifecycle skills (design §Per-phase gating). These are SKILL.md edits, not kernel code — the enforcement that propose/plan/verify are retrieval-led lives in the phase contract; the Oracle is the mechanism.

**13a. Failing test** — `tests/unit/uacp_oracle/test_skill_integration_docs.py`:
```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def _skill(name): return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")

def test_retrieval_led_phases_reference_oracle_query():
    for name in ("uacp-propose", "uacp-plan", "uacp-verify"):
        body = _skill(name)
        assert "uacp_oracle_query" in body
        assert "retrieval-led" in body.lower()

def test_advisory_phases_reference_oracle_as_advisory():
    for name in ("uacp-brainstorm", "uacp-triage"):
        body = _skill(name)
        assert "uacp_oracle_query" in body
        assert "advisory" in body.lower()
```
Run → **FAIL**.

**13b. Minimal impl** — add a short `## Retrieval-led prior-art (Oracle)` section to `skills/uacp-propose/SKILL.md`, `skills/uacp-plan/SKILL.md`, `skills/uacp-verify/SKILL.md` (call `uacp_oracle_query` with the phase + project + domains/invariants/file BEFORE reasoning; treat advisory packets as `evidence_required`), and a shorter `## Advisory prior-art (Oracle)` note to `skills/uacp-triage/SKILL.md` (surface packets, non-blocking). Keep skill bodies free of `docs/` refs per the skill-convention rule; reference only the tool + this design.

**FIX — brainstorm skill: APPEND, do not rewrite.** The edit to `skills/uacp-brainstorm/SKILL.md` must **APPEND** to the post-Plan-A version of that file. Plan A rewrites `uacp-brainstorm/SKILL.md` wholesale; if this plan lands before Plan A, the edit would be lost in Plan A's rewrite. **Plan A must land first.** The edit here is strictly additive: insert an `## Advisory prior-art (Oracle)` section at the end of the Plan-A version of the file. Do NOT rewrite or restructure the rest of the skill body.

Run → **PASS**. Commit.

---

## Task 14 `[C-semantic]` — Reranker bake-off harness (EXECUTE-phase validation step)

The empirical model bake-off (design §"Validation — empirical model bake-off"). This is an **EXECUTE-phase script**, not a unit-tested kernel path — but ship a thin tested core (metrics) + a runnable harness. **Explicitly NOT Ollama** for rerankers (no rerank endpoint); use TEI / vLLM / direct-Python.

**14a. Failing test (metrics core)** — `tests/unit/uacp_oracle/test_bakeoff_metrics.py`:
```python
from engines.oracle.bakeoff import ndcg_at_k, mrr

def test_ndcg_perfect_ranking_is_one():
    # ranked ids vs relevant set
    assert round(ndcg_at_k(["a", "b", "c"], {"a", "b"}, k=3), 6) == 1.0

def test_ndcg_worse_ranking_is_lower():
    good = ndcg_at_k(["a", "b", "c"], {"a"}, k=3)
    bad = ndcg_at_k(["c", "b", "a"], {"a"}, k=3)
    assert good > bad

def test_mrr_first_relevant_rank():
    assert mrr(["x", "a", "b"], {"a"}) == 0.5  # first relevant at rank 2
    assert mrr(["a"], {"a"}) == 1.0
    assert mrr(["x", "y"], {"a"}) == 0.0
```
Run → **FAIL**.

**14b. Minimal impl (metrics)** — `skills/uacp-core/scripts/engines/oracle/bakeoff.py` with pure `ndcg_at_k(ranked_ids, relevant_set, k)` and `mrr(ranked_ids, relevant_set)`. Run → **PASS**. Commit.

**14c. Harness (no new unit test; smoke via `__main__`)** — extend `bakeoff.py` with a `run_bakeoff(eval_set, rerankers, harness)` + a `python -m engines.oracle.bakeoff --eval <path> --harness {tei,vllm,direct} --rerankers qwen3-reranker-0.6b,bge-reranker-v2-m3` CLI that:
- loads a **seed eval set** (a small hand-labeled `query → relevant doc ids` JSON drawn from real `.uacp/lessons` + `.uacp/knowledge`; the design notes this must be bootstrapped since runs haven't produced enough lessons — ship `tests/fixtures/oracle/seed_eval.json` with a handful of synthetic pairs);
- drives each reranker through one of three harnesses — **TEI** (`/rerank`, bge-class), **vLLM** (`/score` or `/v1/rerank`, Qwen3 seq-cls), or **direct FlagEmbedding/sentence-transformers Python** (no server — simplest for a one-off) — and **explicitly refuses `--harness ollama`** with a clear error ("Ollama has no rerank endpoint; use tei|vllm|direct");
- reports nDCG@k / MRR + p50/p95 latency across scenarios: short-query/long-doc (exercises the bge ≤512 cap), multilingual/CJK, exact-keyword vs paraphrase.

Add a `## EXECUTE-phase validation: reranker bake-off` note to the design's companion or this plan's runbook section (below). Commit.

---

## Out of scope (YAGNI / OPEN ITEMS — do NOT build now)

Carried from design §Open items + doc B §Open items. Note these explicitly in code TODOs; do not implement:

- **ColBERT / multi-vector** (PyLate/Qdrant) — opt-in future mode (~2× storage), not in the default pipeline.
- **Cross-project shared knowledge store** (`cross_project_recall` / a user-level shared knowledge dir) — config flag is wired (defaults `false`) but the cross-project recall path is deferred until multi-project is exercised.
- **BGE-M3 sparse leg** via `/pooling` — start with store FTS/BM25 as the lexical leg; add sparse only if recall needs it.
- **Promotion thresholds / distillation loop** — that is doc B's RESOLVE-side machinery; the Oracle only *reads* lessons/knowledge + BES, it does not write them.
- **Honcho retrieval shape / ranking against lessons** — stubbed; confirm the real query API later.
- **vLLM vs TEI+Ollama "blessed" quickstart** — support both via `[oracle.*].url`; pick the documented default during the bake-off.

---

## Final verification checkpoint

```bash
python -m pytest tests/unit/uacp_oracle -q
ruff check skills/uacp-core/scripts/engines/oracle tests/unit/uacp_oracle
# Floor-with-no-ML-deps guard (the load-bearing claim): the suite must pass green
# even in an env where neither lancedb nor the llama.cpp binding is installed.
python -c "import sys; sys.modules['lancedb']=None; import engines.oracle.aggregator as a; print('floor imports clean')"
```
All green + the read-only tool tests (Task 11) passing is the completion bar.
