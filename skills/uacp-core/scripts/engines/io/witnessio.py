"""Codeflair scope-witness read-access for the engines — the independent code-plane account.

Same doctrine as :mod:`engines.io.gitio`: this module NEVER raises. Every failure
mode (CLI unconfigured/absent, non-zero rc, timeout, garbled JSON, missing required
keys) is returned inside :class:`WitnessResult` so the calling engine converts it
into the right ``Violation`` (fail-closed ``SC_WITNESS_UNAVAILABLE``) instead of
crashing the sweep.

Seam (design node 02 — LOCKED for #85): the agent AUTHORS ``code_refs`` (the
falsifiable claim); the GATE derives the independent account here by exec'ing the
codeflair CLI across a PROCESS boundary (CF-D9: the kernel never imports/links the
code plane — it gains only an optional external prober, same trust posture as git).

Executable trust root: the command is resolved from OPERATOR-owned kernel config
(``config/uacp.toml`` ``[witness].codeflair_cli``), NEVER from the run workspace and
never from a PATH entry under it — a tampered witness must not be one work-product
edit away. Absent key → unconfigured → ``available=False`` (the witness ships inert).

The witness reports FACTS ONLY; the gate computes every verdict (see
``engines.scope_conformance._check_cascade_witness``). A CLI that returned
"undeclared"/"over-declared" sets would move the comparison into the witness, making
a coverage bug invisible and unrecomputable kernel-side.

Reuse: derivations are memoized in-process keyed on ``(root, tree_token,
normalized code_refs)`` where the token is a cheap kernel-side approximation (HEAD
sha + sha256 of ``git status --porcelain``) computed BEFORE exec. The stdout is a
function of BOTH the tree AND the claim (the ``declared`` echo depends on
``code_refs``), so an unchanged tree with an unchanged claim reuses the account (a
retried finalize does not pay N×index), while changing either re-derives. A
missing/un-gitted tree yields no token and simply re-derives.
:func:`clear_witness_memo` resets it (tests).
"""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import get_config

# 120s (design node 02): gitio's 10s would kill a legitimate ~18s index build at 590
# files; 120s gives headroom for larger repos while still bounding the sweep.
_WITNESS_TIMEOUT_SECONDS = 120.0
# Short bound for the cheap token probe — this is git metadata, not an index build.
_GIT_TIMEOUT_SECONDS = 10.0

# The facts contract's required top-level keys (design node 02 wire schema). A
# response missing any of these is garbled → unavailable.
_REQUIRED_KEYS = (
    "graph_stamp",
    "ingestion",
    "symbols_touched",
    "neighborhood",
    "declared",
    "unresolved_touched",
)


@dataclass(frozen=True)
class WitnessFacts:
    """The codeflair witness's FACTS — mirrors the contract JSON exactly.

    graph_stamp        — {commit, tree_token}: HEAD the index was built at + the
                         content token of the working tree at witness time.
    ingestion          — the provenance floor the account was derived under
                         (the gate rejects anything weaker than ``scip``).
    symbols_touched    — {file, name} symbols in the ACTUAL diff's files.
    neighborhood       — hop-1 edges {src:{file,name}, dst:{file,name}, reason}.
    declared           — the claim echoed back: {file, name, resolved: bool}.
    unresolved_touched — touched but unresolvable {file, name} (new/unparseable code).
    """

    graph_stamp: dict
    ingestion: str | None
    symbols_touched: tuple[dict, ...]
    neighborhood: tuple[dict, ...]
    declared: tuple[dict, ...]
    unresolved_touched: tuple[dict, ...]


@dataclass(frozen=True)
class WitnessResult:
    """Outcome of deriving the codeflair account. Never carries an exception.

    available — the account was derived and parsed cleanly.
    facts     — the parsed facts (only meaningful when ``available``).
    error     — human-readable failure when the witness could not testify; the
                engine surfaces this (fail-closed), never treats it as "no cascade".
    command   — the resolved argv (recorded in the violation detail — the trust
                root is auditable).
    """

    available: bool
    facts: WitnessFacts | None = None
    error: str | None = None
    command: tuple[str, ...] = ()


# In-process derivation memo, keyed on (resolved-root, tree_token, normalized
# code_refs). Populated only when a token is computable. The stdout is a function of
# BOTH the tree AND the claim (the `declared` echo depends on code_refs), so a retry
# that changed only code_refs on an unchanged tree MUST re-derive — else the gate
# would compute coverage/over-declaration/unresolved against a stale declaration
# (GitHub Codex P2). A token mismatch OR a refs mismatch re-derives.
_MEMO: dict[tuple[str, str, tuple[tuple[str, str], ...]], WitnessResult] = {}


def clear_witness_memo() -> None:
    """Drop the in-process derivation memo (test isolation)."""
    _MEMO.clear()


def _resolve_cli(root: Path) -> str | None:
    """Resolve the witness command from OPERATOR-owned config, never the workspace.

    Returns the ``[witness].codeflair_cli`` string (may contain args) or ``None``
    when unconfigured/blank. Never raises."""
    try:
        cli = get_config(root).witness.codeflair_cli
    except Exception:
        return None
    if isinstance(cli, str) and cli.strip():
        return cli.strip()
    return None


def _run_git(root: Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run(  # noqa: S603 — fixed argv, no shell
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SECONDS,
    )
    return proc.returncode, proc.stdout


def _compute_tree_token(root: Path) -> str | None:
    """A cheap kernel-side content token of the working tree, or None when the tree
    is not a readable git repo. HEAD sha + sha256(git status --porcelain) — cheap,
    and captures both committed and uncommitted state. Never raises."""
    try:
        rc, head = _run_git(root, "rev-parse", "HEAD")
        if rc != 0:
            return None
        rc, status = _run_git(root, "status", "--porcelain")
        if rc != 0:
            return None
    except Exception:
        return None
    digest = hashlib.sha256(status.encode("utf-8", "replace")).hexdigest()
    return f"{head.strip()}:{digest}"


def _parse_facts(stdout: str) -> tuple[WitnessFacts | None, str | None]:
    """Strictly parse the facts JSON. Returns (facts, None) or (None, error)."""
    try:
        data = json.loads(stdout)
    except Exception as exc:
        return None, f"witness stdout is not valid JSON ({type(exc).__name__})"
    if not isinstance(data, dict):
        return None, "witness stdout JSON is not an object"
    missing = [k for k in _REQUIRED_KEYS if k not in data]
    if missing:
        return None, f"witness JSON missing required keys: {missing}"

    graph_stamp = data["graph_stamp"]
    if not isinstance(graph_stamp, dict):
        return None, "witness graph_stamp is not an object"

    ingestion = data["ingestion"]
    ingestion_val = ingestion if isinstance(ingestion, str) else None

    def _as_dict_tuple(key: str) -> tuple[tuple[dict, ...] | None, str | None]:
        val = data[key]
        if not isinstance(val, list):
            return None, f"witness {key} is not a list"
        items: list[dict] = []
        for entry in val:
            if not isinstance(entry, dict):
                return None, f"witness {key} contains a non-object entry"
            items.append(entry)
        return tuple(items), None

    symbols_touched, err = _as_dict_tuple("symbols_touched")
    if err is not None:
        return None, err
    neighborhood, err = _as_dict_tuple("neighborhood")
    if err is not None:
        return None, err
    declared, err = _as_dict_tuple("declared")
    if err is not None:
        return None, err
    unresolved_touched, err = _as_dict_tuple("unresolved_touched")
    if err is not None:
        return None, err

    facts = WitnessFacts(
        graph_stamp=graph_stamp,
        ingestion=ingestion_val,
        symbols_touched=symbols_touched or (),
        neighborhood=neighborhood or (),
        declared=declared or (),
        unresolved_touched=unresolved_touched or (),
    )
    return facts, None


def _exec_and_parse(command: tuple[str, ...]) -> WitnessResult:
    """One exec attempt. Never raises — every failure is a typed unavailable result."""
    try:
        proc = subprocess.run(  # noqa: S603 — fixed argv from operator config, no shell
            list(command),
            capture_output=True,
            text=True,
            timeout=_WITNESS_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return WitnessResult(available=False, error="witness CLI binary not found", command=command)
    except subprocess.TimeoutExpired:
        return WitnessResult(
            available=False,
            error=f"witness timed out after {_WITNESS_TIMEOUT_SECONDS}s",
            command=command,
        )
    except Exception as exc:  # defensive: the io layer never raises
        return WitnessResult(available=False, error=f"{type(exc).__name__}: {exc}", command=command)

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        return WitnessResult(
            available=False,
            error=f"witness exited rc={proc.returncode}: {detail[:200]}",
            command=command,
        )

    facts, err = _parse_facts(proc.stdout)
    if err is not None:
        return WitnessResult(available=False, error=err, command=command)
    return WitnessResult(available=True, facts=facts, command=command)


def derive_witness(root: Path, code_refs: list[dict[str, Any]]) -> WitnessResult:
    """Derive the codeflair account of the run's change. NEVER raises.

    Resolves the CLI from operator config (unconfigured → unavailable), computes a
    cheap tree token and returns the memoized result on an unchanged tree AND an
    unchanged claim, else execs ``<cli> witness --repo <root> [--code-ref file:name
    ...]`` (120s), parsing stdout JSON strictly. Any failure retries ONCE, then
    reports unavailable."""
    cli = _resolve_cli(root)
    if cli is None:
        return WitnessResult(available=False, error="witness CLI not configured", command=())

    argv: list[str] = [*shlex.split(cli), "witness", "--repo", str(root)]
    for ref in code_refs:
        argv += ["--code-ref", f"{ref.get('file', '')}:{ref.get('name', '')}"]
    command = tuple(argv)

    token = _compute_tree_token(root)
    # Normalize the claim (sorted, deduped) into the memo key — the stdout depends on
    # BOTH tree and claim, so same-tree/different-refs must re-derive.
    refs_key = tuple(sorted({(str(r.get("file", "")), str(r.get("name", ""))) for r in code_refs}))
    key = (str(Path(root).resolve()), token, refs_key) if token is not None else None
    if key is not None and key in _MEMO:
        return _MEMO[key]

    result = _exec_and_parse(command)
    if not result.available:
        # One retry before reporting unavailable (transient index/lock races).
        result = _exec_and_parse(command)

    if key is not None:
        _MEMO[key] = result
    return result
