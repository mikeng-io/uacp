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

Executable trust root (design node 02 / K1): the command is resolved from the
KERNEL-DEFAULT config ONLY (``config/uacp.toml`` ``[witness].codeflair_cli``, read via
:func:`_operator_config_path` and parsed directly — NO workspace ``.uacp/config.toml``
merge). The adversarial council round proved an override-wins merge would hand the
*pointer* to the witnessed agent: a workspace ``[witness]`` naming a friendly script
would beat any safe operator value. ``argv[0]`` is resolved to an ABSOLUTE path before
exec (``shutil.which`` against the scrubbed child ``PATH`` for bare names) and REJECTED
(→ unavailable, naming the reason) if it resolves UNDER the run workspace — a tampered
witness must not be one work-product edit away. The resolved argv is recorded in
``WitnessResult.command`` so the trust root is auditable. Absent key → unconfigured →
``available=False`` (the witness ships inert).

The witness reports FACTS ONLY; the gate computes every verdict (see
``engines.scope_conformance._check_cascade_witness``). A CLI that returned
"undeclared"/"over-declared" sets would move the comparison into the witness, making
a coverage bug invisible and unrecomputable kernel-side.

Reuse: derivations are memoized in-process keyed on ``(root, tree_token,
normalized code_refs)`` where the token is a CONTENT-SENSITIVE kernel-side
approximation computed BEFORE exec — HEAD sha + sha256 over the sorted
``git status --porcelain -uall`` lines PLUS a content hash of every changed file's
bytes (K2). A HEAD+status-only token is byte-identical across a content-only edit to
an already-dirty file and would serve stale facts; hashing the changed bytes closes
that. The stdout is a function of BOTH the tree AND the claim (the ``declared`` echo
depends on ``code_refs``), so an unchanged tree with an unchanged claim reuses the
account (a retried finalize does not pay N×index), while changing either re-derives.
A missing/un-gitted tree — or a change set larger than ``_MEMO_MAX_CHANGED_FILES`` —
yields no token and simply re-derives every time. :func:`clear_witness_memo` resets
it (tests).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import shlex
import shutil
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import _default_toml_path

from .gitio import _scrubbed_env

# 120s (design node 02): gitio's 10s would kill a legitimate ~18s index build at 590
# files; 120s gives headroom for larger repos while still bounding the sweep.
_WITNESS_TIMEOUT_SECONDS = 120.0
# Short bound for the cheap token probe — this is git metadata, not an index build.
_GIT_TIMEOUT_SECONDS = 10.0
# Above this many changed files the content-token probe is skipped entirely (no memo,
# derive every time): hashing thousands of file bodies on every sweep is not worth the
# reuse win, and a sweep that large is rare (design node 02 / K2).
_MEMO_MAX_CHANGED_FILES = 500

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

# The BASELINE facts mode (design node 04 — prevention forecast). A diff-independent
# derivation on the committed baseline (HEAD): it echoes the declared refs, resolves
# them, and reports their hop-1 neighborhood — but NO symbols_touched / unresolved_touched
# (at PLAN there is no diff). ``mode`` is a REQUIRED key AND must equal this literal, so a
# diff-mode ("witness") response can never be mistaken for a baseline one (and vice versa).
_BASELINE_MODE = "baseline_refs"
_BASELINE_REQUIRED_KEYS = (
    "mode",
    "graph_stamp",
    "ingestion",
    "declared",
    "neighborhood",
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
    inbound_counts     — per-touched-symbol inbound fan-in (class witness, node 03):
                         ``{"<file>:<name>": <int>}``. Counts DISTINCT (src, dst, rel) inbound
                         edges whose rel is ``calls``/``references`` only — ``defines`` excluded
                         (see engines.domain.verification_floor.witness_class). Zero is present for
                         every touched symbol. OPTIONAL on the wire (absent -> ``{}``); the scope
                         witness (02) does not read it, so it is never a required key.
    """

    graph_stamp: dict
    ingestion: str | None
    symbols_touched: tuple[dict, ...]
    neighborhood: tuple[dict, ...]
    declared: tuple[dict, ...]
    unresolved_touched: tuple[dict, ...]
    inbound_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class BaselineFacts:
    """The codeflair BASELINE facts (design node 04) — mirrors the ``baseline_refs`` wire.

    graph_stamp    — {commit, tree_token}: HEAD the baseline index was built at.
    ingestion      — the provenance floor (the gate rejects anything weaker than ``scip``).
    declared       — the claim echoed back and resolved: {file, name, resolved: bool},
                     carrying the witness's CANONICAL names.
    neighborhood   — hop-1 edges {src:{file,name}, dst:{file,name}, reason} of the RESOLVED
                     refs on the committed baseline. There is no diff, so ``symbols_touched``
                     / ``unresolved_touched`` do NOT appear (and are not read).
    inbound_counts — per-symbol inbound fan-in (OPTIONAL on the wire; absent -> {}).
    workspace_dirty— whether the working tree was dirty when the baseline was derived
                     (the forecast is then a prediction from the last clean state).
    """

    graph_stamp: dict
    ingestion: str | None
    declared: tuple[dict, ...]
    neighborhood: tuple[dict, ...]
    inbound_counts: dict[str, int] = field(default_factory=dict)
    workspace_dirty: bool = False


@dataclass(frozen=True)
class WitnessResult:
    """Outcome of deriving the codeflair account. Never carries an exception.

    available — the account was derived and parsed cleanly.
    facts     — the parsed facts (only meaningful when ``available``). Either the
                diff-mode :class:`WitnessFacts` or the baseline :class:`BaselineFacts`,
                depending on which derivation produced this result.
    error     — human-readable failure when the witness could not testify; the
                engine surfaces this (fail-closed), never treats it as "no cascade".
    command   — the resolved argv (recorded in the violation detail — the trust
                root is auditable).
    """

    available: bool
    facts: WitnessFacts | BaselineFacts | None = None
    error: str | None = None
    command: tuple[str, ...] = ()


# In-process derivation memo, keyed on (resolved-root, tree_token, normalized
# code_refs). Populated only when a token is computable. The stdout is a function of
# BOTH the tree AND the claim (the `declared` echo depends on code_refs), so a retry
# that changed only code_refs on an unchanged tree MUST re-derive — else the gate
# would compute coverage/over-declaration/unresolved against a stale declaration
# (GitHub Codex P2). A token mismatch OR a refs mismatch re-derives.
_MEMO: dict[tuple[str, str, tuple[tuple[str, str], ...]], WitnessResult] = {}

# The BASELINE derivation memo (design node 04). Keyed on (resolved-root, HEAD sha,
# normalized refs, mode) — NOT the content-sensitive tree token, because the baseline is
# derived on the committed HEAD, so a dirty tree with an unchanged HEAD legitimately reuses
# the same account (``workspace_dirty`` still reports the dirtiness). The ``mode`` element
# and the distinct dict guarantee this key never collides with the diff-mode ``_MEMO``.
_BASELINE_MEMO: dict[tuple[str, str, tuple[tuple[str, str], ...], str], WitnessResult] = {}


def clear_witness_memo() -> None:
    """Drop BOTH in-process derivation memos (test isolation)."""
    _MEMO.clear()
    _BASELINE_MEMO.clear()


def _operator_config_path() -> Path:
    """Path to the KERNEL-DEFAULT config the witness trust root is read from.

    A module-level injectable seam (tests monkeypatch it to a temp toml so real
    ``tomllib`` parsing is still exercised without a workspace merge). Points at
    ``config/uacp.toml`` — the workspace ``.uacp/config.toml`` is NEVER consulted for
    the ``[witness]`` table (K1: an override-wins merge would hand the witnessed agent
    the pointer)."""
    return _default_toml_path()


def _read_operator_cli() -> str | None:
    """Read ``[witness].codeflair_cli`` from the kernel-default config ONLY.

    Parses :func:`_operator_config_path` directly with ``tomllib`` — no workspace
    merge, no :mod:`config` caching that could fold in a project override. Returns the
    configured command string (may contain args) or ``None`` when unconfigured/blank.
    Never raises."""
    try:
        with _operator_config_path().open("rb") as fh:
            data = tomllib.load(fh)
    except Exception:
        return None
    witness = data.get("witness")
    if not isinstance(witness, dict):
        return None
    cli = witness.get("codeflair_cli")
    if isinstance(cli, str) and cli.strip():
        return cli.strip()
    return None


def _resolve_executable(
    argv0: str, child_env: dict[str, str], root: Path
) -> tuple[str | None, str]:
    """Resolve ``argv0`` to an ABSOLUTE executable path, rejecting run-mutable ones.

    Bare names (no path separator) resolve via ``shutil.which`` against the SCRUBBED
    child ``PATH``; a path (absolute or relative-with-separator) is made absolute and
    must exist. The resolved path is REJECTED (returns ``(None, reason)``) if it lands
    UNDER the run workspace ``root`` — the trust root must be an installed artifact or
    pinned checkout, never one work-product edit away (ADR-0019 does not raw-block
    work-product writes). Returns ``(resolved_abs, "")`` on success. Never raises."""
    has_sep = ("/" in argv0) or ("\\" in argv0)
    try:
        if has_sep or Path(argv0).is_absolute():
            candidate = Path(argv0)
            if not candidate.is_absolute():
                candidate = Path.cwd() / candidate
            resolved = candidate.resolve()
            if not resolved.exists():
                return None, f"witness CLI not found at {resolved}"
        else:
            found = shutil.which(argv0, path=child_env.get("PATH"))
            if not found:
                return None, f"witness CLI '{argv0}' not found on PATH"
            resolved = Path(found).resolve()
    except Exception as exc:  # defensive: resolution never raises to the caller
        return None, f"witness CLI unresolvable ({type(exc).__name__})"

    try:
        root_r = Path(root).resolve()
        if resolved == root_r or root_r in resolved.parents:
            return None, (
                f"witness CLI resolves under the run workspace ({resolved}); refusing to "
                f"exec a run-mutable prober — configure an installed/pinned path outside {root_r}"
            )
    except Exception:
        pass  # unresolvable root is defended elsewhere; do not block on it here
    return str(resolved), ""


def _screen_configured_tail(tail: list[str], root: Path) -> str | None:
    """Reject a CONFIGURED argv tail that smuggles a run-mutable path (P1 review).

    ``_resolve_executable`` screens argv[0], but a launcher-style configuration —
    ``python <workspace>/cli.py`` or ``uv --project <workspace> run codeflair`` —
    carries the workspace-resident script/project in the TAIL, and the launcher
    itself resolves safely outside the workspace. Every configured token (after
    stripping a ``--key=`` prefix) that contains a path separator is resolved and
    must not land under the run workspace. Only the OPERATOR-CONFIGURED tokens are
    screened — the kernel-appended ``--repo <root>`` legitimately names the
    workspace. Returns a rejection reason, or None. Never raises."""
    try:
        root_r = Path(root).resolve()
    except Exception:
        return None  # unresolvable root is defended elsewhere
    for token in tail:
        probe = token.split("=", 1)[1] if token.startswith("--") and "=" in token else token
        if "/" not in probe and "\\" not in probe:
            continue
        try:
            candidate = Path(probe)
            if not candidate.is_absolute():
                candidate = Path.cwd() / candidate
            resolved = candidate.resolve()
            if resolved == root_r or root_r in resolved.parents:
                return (
                    f"witness CLI argument '{token}' resolves under the run workspace "
                    f"({resolved}); refusing a run-mutable prober component"
                )
        except Exception:
            continue  # non-path token; screening is best-effort, never raises
    return None


def _run_git(root: Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run(  # noqa: S603 — fixed argv, no shell
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SECONDS,
        env=_scrubbed_env(),
    )
    return proc.returncode, proc.stdout


def _porcelain_paths(status_lines: list[str]) -> list[str]:
    """Repo-relative paths out of ``git status --porcelain`` lines (rename -> the NEW
    path). Best-effort — matches gitio's parser; exotic quoted paths are left verbatim."""
    out: list[str] = []
    for line in status_lines:
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip()
        if len(path) >= 2 and path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        if path:
            out.append(path)
    return out


def _compute_tree_token(root: Path) -> str | None:
    """A CONTENT-SENSITIVE kernel-side token of the working tree, or None when the tree
    is not a readable git repo (or the change set is too large to hash cheaply — K2).

    HEAD sha + sha256 over the sorted ``git status --porcelain -uall`` lines PLUS a
    content hash of every changed file's bytes (sorted by path; a missing/deleted file
    hashes to a fixed marker). The per-file content hashes make the token move on a
    content-only edit to an already-dirty file (status letter unchanged) — a
    HEAD+status-only token would not. Above ``_MEMO_MAX_CHANGED_FILES`` changed files
    the probe returns None (skip memo, derive every time). Never raises."""
    try:
        rc, head = _run_git(root, "rev-parse", "HEAD")
        if rc != 0:
            return None
        rc, status = _run_git(root, "status", "--porcelain", "-uall")
        if rc != 0:
            return None
    except Exception:
        return None

    lines = sorted(ln for ln in status.splitlines() if ln)
    paths = _porcelain_paths(lines)
    if len(paths) > _MEMO_MAX_CHANGED_FILES:
        return None  # bound token cost — a huge sweep re-derives rather than hashing all bodies

    h = hashlib.sha256()
    h.update(head.strip().encode("utf-8", "replace"))
    h.update(b"\n")
    for line in lines:
        h.update(line.encode("utf-8", "replace"))
        h.update(b"\n")
    for rel in sorted(set(paths)):
        try:
            with (Path(root) / rel).open("rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
        except OSError:
            digest = "__missing__"  # deleted/unreadable — porcelain already moved the token
        h.update(f"{rel}:{digest}\n".encode("utf-8", "replace"))
    return h.hexdigest()


def _head_sha(root: Path) -> str | None:
    """The committed HEAD sha, or None when the tree is not a readable git repo (design
    node 04: the baseline memo keys on HEAD, not the content-sensitive tree token, because
    the forecast derives on the committed baseline). Never raises."""
    try:
        rc, head = _run_git(root, "rev-parse", "HEAD")
        if rc != 0:
            return None
    except Exception:
        return None
    return head.strip() or None


def _workspace_dirty(root: Path) -> bool | None:
    """Recompute — kernel-side, FRESH — whether the working tree is dirty (design node 04 /
    K1). ``git status --porcelain -uall`` (scrubbed env) filtered of the witness's own
    ``.codeflair/`` index cache (the gate-owned store must never read as run dirtiness,
    mirroring the codeflair-side ``porcelain_lines`` filter). Returns the fresh bool, or
    None when the tree is not a readable git repo (the caller then keeps the witness's
    reported value). Never raises.

    The baseline account is memoized on HEAD, so a memo hit serves the dirtiness observed at
    the ORIGINAL derivation — stale across a clean->dirty transition at the same HEAD. The
    caller replaces the memoized flag with this fresh value on EVERY call."""
    try:
        rc, status = _run_git(root, "status", "--porcelain", "-uall")
        if rc != 0:
            return None
    except Exception:
        return None
    lines = [ln for ln in status.splitlines() if ln]
    for path in _porcelain_paths(lines):
        if not path.startswith(".codeflair/"):
            return True
    return False


def _with_fresh_workspace_dirty(root: Path, result: WitnessResult) -> WitnessResult:
    """Return ``result`` with its :class:`BaselineFacts` ``workspace_dirty`` recomputed
    kernel-side (K1). A no-op when the result is unavailable, is not a baseline account, or
    the tree is unreadable (fresh value None). Never raises."""
    facts = result.facts
    if not result.available or not isinstance(facts, BaselineFacts):
        return result
    fresh = _workspace_dirty(root)
    if fresh is None or fresh == facts.workspace_dirty:
        return result
    return dataclasses.replace(result, facts=dataclasses.replace(facts, workspace_dirty=fresh))


# The edge relations the witness may report (mirrors codeflair.witness._REASONS).
_WIRE_REASONS = frozenset({"calls", "references", "defines"})


def _is_sym(entry: Any, *, allow_null_name: bool = False) -> bool:
    """A wire ``{file, name}`` node: ``file`` a non-empty str, ``name`` a non-empty str
    (or ``null`` when ``allow_null_name`` — the file-level ``unresolved_touched`` case)."""
    if not isinstance(entry, dict):
        return False
    f = entry.get("file")
    if not (isinstance(f, str) and f):
        return False
    n = entry.get("name")
    if allow_null_name and n is None:
        return True
    return isinstance(n, str) and bool(n)


def _parse_facts(stdout: str) -> tuple[WitnessFacts | None, str | None]:
    """Strictly parse AND SHAPE-VALIDATE the facts JSON (K5). Returns (facts, None) or
    (None, error). A shallow "is it a list of dicts" check would let a malformed entry
    be silently dropped gate-side (fail-open); here ANY malformed entry → error →
    the engine reports SC_WITNESS_UNAVAILABLE (fail-closed)."""
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

    def _as_list(key: str) -> tuple[list | None, str | None]:
        val = data[key]
        if not isinstance(val, list):
            return None, f"witness {key} is not a list"
        return val, None

    # symbols_touched / declared: {file, name} (+ declared adds resolved:bool).
    symbols_raw, err = _as_list("symbols_touched")
    if err is not None:
        return None, err
    for entry in symbols_raw:
        if not _is_sym(entry):
            return None, f"witness symbols_touched has a malformed entry: {entry!r}"

    declared_raw, err = _as_list("declared")
    if err is not None:
        return None, err
    for entry in declared_raw:
        if not _is_sym(entry) or not isinstance(entry.get("resolved"), bool):
            return None, f"witness declared has a malformed entry: {entry!r}"

    # neighborhood: {src:{file,name}, dst:{file,name}, reason in {calls,references,defines}}.
    neighborhood_raw, err = _as_list("neighborhood")
    if err is not None:
        return None, err
    for entry in neighborhood_raw:
        if not isinstance(entry, dict):
            return None, f"witness neighborhood has a non-object entry: {entry!r}"
        if not _is_sym(entry.get("src")) or not _is_sym(entry.get("dst")):
            return None, f"witness neighborhood has a malformed endpoint: {entry!r}"
        if entry.get("reason") not in _WIRE_REASONS:
            return None, f"witness neighborhood has an invalid reason: {entry!r}"

    # unresolved_touched: {file, name} with name NULLABLE (file-level for unparseable code).
    unresolved_raw, err = _as_list("unresolved_touched")
    if err is not None:
        return None, err
    for entry in unresolved_raw:
        if not _is_sym(entry, allow_null_name=True):
            return None, f"witness unresolved_touched has a malformed entry: {entry!r}"

    # inbound_counts (class witness, node 03): OPTIONAL — NOT in _REQUIRED_KEYS, so a witness
    # that predates it (or the 02 scope-only path) parses byte-identically. Read LENIENTLY: only
    # well-formed str->int entries are kept (bool excluded — bool is an int subclass); a malformed
    # entry is dropped, not fatal, because the class-witness fallback recomputes a missing count
    # from the neighborhood. A non-dict value degrades to {} (fallback everywhere).
    inbound_counts: dict[str, int] = {}
    ic_raw = data.get("inbound_counts")
    if isinstance(ic_raw, dict):
        for k, v in ic_raw.items():
            if isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool):
                inbound_counts[k] = v

    facts = WitnessFacts(
        graph_stamp=graph_stamp,
        ingestion=ingestion_val,
        symbols_touched=tuple(symbols_raw),
        neighborhood=tuple(neighborhood_raw),
        declared=tuple(declared_raw),
        unresolved_touched=tuple(unresolved_raw),
        inbound_counts=inbound_counts,
    )
    return facts, None


def _parse_neighborhood_endpoints(raw: list) -> str | None:
    """Shape-validate a neighborhood edge list's ENDPOINTS. Returns an error string, or
    None when every edge has ``src``/``dst`` {file, name} nodes. ``reason`` is validated
    LENIENTLY here (must be a str if present) — the diff-mode parser restricts it to the
    edge-reason enum, but the baseline forecast reasons over hop-1 MEMBERSHIP regardless of
    edge kind, so an over-strict reason check would needlessly reject the sibling wire."""
    for entry in raw:
        if not isinstance(entry, dict):
            return f"neighborhood has a non-object entry: {entry!r}"
        if not _is_sym(entry.get("src")) or not _is_sym(entry.get("dst")):
            return f"neighborhood has a malformed endpoint: {entry!r}"
        reason = entry.get("reason")
        if reason is not None and not isinstance(reason, str):
            return f"neighborhood has a non-string reason: {entry!r}"
    return None


def _parse_inbound_counts(raw: Any) -> dict[str, int]:
    """Lenient str->int parse of ``inbound_counts`` (bool excluded — bool is an int
    subclass). A non-dict degrades to {}. Mirrors :func:`_parse_facts`."""
    out: dict[str, int] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool):
                out[k] = v
    return out


def _parse_baseline_facts(stdout: str) -> tuple[BaselineFacts | None, str | None]:
    """Strictly parse AND SHAPE-VALIDATE the BASELINE facts JSON (design node 04). Returns
    (facts, None) or (None, error). Strict on the structural keys (``mode`` present AND ==
    ``baseline_refs``; ``graph_stamp`` an object; ``declared`` entries {file, name,
    resolved:bool}; ``neighborhood`` endpoints valid) so a garbled or diff-mode response
    fails closed → SC_WITNESS_UNAVAILABLE. ``workspace_dirty`` / ``inbound_counts`` are
    OPTIONAL (a bool flag / an advisory count is not worth failing an otherwise-valid
    account over)."""
    try:
        data = json.loads(stdout)
    except Exception as exc:
        return None, f"baseline witness stdout is not valid JSON ({type(exc).__name__})"
    if not isinstance(data, dict):
        return None, "baseline witness stdout JSON is not an object"
    missing = [k for k in _BASELINE_REQUIRED_KEYS if k not in data]
    if missing:
        return None, f"baseline witness JSON missing required keys: {missing}"
    if data["mode"] != _BASELINE_MODE:
        return None, (
            f"baseline witness reported mode {data['mode']!r}, expected {_BASELINE_MODE!r} "
            "(a diff-mode account cannot be read as a baseline one)"
        )

    graph_stamp = data["graph_stamp"]
    if not isinstance(graph_stamp, dict):
        return None, "baseline witness graph_stamp is not an object"

    ingestion = data["ingestion"]
    ingestion_val = ingestion if isinstance(ingestion, str) else None

    declared_raw = data["declared"]
    if not isinstance(declared_raw, list):
        return None, "baseline witness declared is not a list"
    for entry in declared_raw:
        if not _is_sym(entry) or not isinstance(entry.get("resolved"), bool):
            return None, f"baseline witness declared has a malformed entry: {entry!r}"

    neighborhood_raw = data["neighborhood"]
    if not isinstance(neighborhood_raw, list):
        return None, "baseline witness neighborhood is not a list"
    err = _parse_neighborhood_endpoints(neighborhood_raw)
    if err is not None:
        return None, f"baseline witness {err}"

    wd = data.get("workspace_dirty")
    facts = BaselineFacts(
        graph_stamp=graph_stamp,
        ingestion=ingestion_val,
        declared=tuple(declared_raw),
        neighborhood=tuple(neighborhood_raw),
        inbound_counts=_parse_inbound_counts(data.get("inbound_counts")),
        workspace_dirty=wd if isinstance(wd, bool) else False,
    )
    return facts, None


def _exec_and_parse(
    command: tuple[str, ...],
    child_env: dict[str, str],
    parse: Any = _parse_facts,
) -> tuple[WitnessResult, bool]:
    """One exec attempt. Never raises — every failure is a typed unavailable result.

    Returns ``(result, transient)`` where ``transient`` is True ONLY for a subprocess
    TIMEOUT (K6): a timeout may be a slow-index race worth ONE retry, but a non-zero
    exit or malformed/garbled JSON is DETERMINISTIC — retrying it buys latency, not
    signal, so those fail immediately.

    ``cwd`` is pinned to a NEUTRAL directory (post-merge P1): launcher-style
    witnesses (``python -m codeflair``, ``uv run codeflair``) resolve their
    module/project from the current directory, so inheriting the validator's cwd
    — which may be the run workspace — would let agent-editable files supply the
    witness implementation even though argv screening passed. The repo the
    witness observes is always named explicitly via ``--repo``."""
    try:
        proc = subprocess.run(  # noqa: S603 — resolved absolute argv from operator config, no shell
            list(command),
            capture_output=True,
            text=True,
            timeout=_WITNESS_TIMEOUT_SECONDS,
            env=child_env,
            cwd=tempfile.gettempdir(),
        )
    except FileNotFoundError:
        nf = WitnessResult(available=False, error="witness CLI binary not found", command=command)
        return nf, False
    except subprocess.TimeoutExpired:
        return (
            WitnessResult(
                available=False,
                error=f"witness timed out after {_WITNESS_TIMEOUT_SECONDS}s",
                command=command,
            ),
            True,  # transient — retry once
        )
    except Exception as exc:  # defensive: the io layer never raises
        err = WitnessResult(available=False, error=f"{type(exc).__name__}: {exc}", command=command)
        return err, False

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        return (
            WitnessResult(
                available=False,
                error=f"witness exited rc={proc.returncode}: {detail[:200]}",
                command=command,
            ),
            False,  # deterministic — no retry
        )

    facts, err = parse(proc.stdout)
    if err is not None:
        return WitnessResult(available=False, error=err, command=command), False  # deterministic
    return WitnessResult(available=True, facts=facts, command=command), False


def _prepare_command(
    root: Path,
    code_refs: list[dict[str, Any]],
    child_env: dict[str, str],
    extra_flags: tuple[str, ...],
) -> tuple[tuple[str, ...] | None, WitnessResult | None]:
    """The SHARED 02 envelope (design node 02 / K1): resolve the CLI from the
    KERNEL-DEFAULT config only, resolve ``argv[0]`` to an absolute path and REJECT one
    under the run workspace, screen the configured tail, then build ``<cli> witness --repo
    <root> [extra_flags…] [--code-ref file:name …]``. Returns ``(command, None)`` on
    success, or ``(None, unavailable_result)`` recording the SAME command context the
    diff-mode path recorded (unconfigured → command=(); a rejected argv → the raw parts).
    Never raises. Both :func:`derive_witness` and :func:`derive_baseline_neighborhood`
    build on this so the trust root / screening / neutral env are byte-identical."""
    cli = _read_operator_cli()
    if cli is None:
        return None, WitnessResult(available=False, error="witness CLI not configured", command=())
    parts = shlex.split(cli)
    if not parts:
        return None, WitnessResult(available=False, error="witness CLI not configured", command=())
    resolved0, reason = _resolve_executable(parts[0], child_env, root)
    if resolved0 is None:
        return None, WitnessResult(available=False, error=reason, command=tuple(parts))
    tail_reason = _screen_configured_tail(parts[1:], root)
    if tail_reason is not None:
        return None, WitnessResult(available=False, error=tail_reason, command=tuple(parts))
    argv: list[str] = [resolved0, *parts[1:], "witness", "--repo", str(root), *extra_flags]
    for ref in code_refs:
        argv += ["--code-ref", f"{ref.get('file', '')}:{ref.get('name', '')}"]
    return tuple(argv), None


def _normalized_refs_key(code_refs: list[dict[str, Any]]) -> tuple[tuple[str, str], ...]:
    """The claim normalized (sorted, deduped) for a memo key."""
    return tuple(sorted({(str(r.get("file", "")), str(r.get("name", ""))) for r in code_refs}))


def derive_witness(root: Path, code_refs: list[dict[str, Any]]) -> WitnessResult:
    """Derive the codeflair account of the run's change. NEVER raises.

    Resolves the CLI from the KERNEL-DEFAULT config only (unconfigured → unavailable),
    resolves ``argv[0]`` to an absolute path and REJECTS a path under the run workspace
    (K1), computes a content-sensitive tree token and returns the memoized result on an
    unchanged tree AND an unchanged claim, else execs ``<cli> witness --repo <root>
    [--code-ref file:name ...]`` (120s) with a scrubbed env, parsing stdout JSON
    strictly. A TIMEOUT retries ONCE; deterministic failures report unavailable
    immediately (K6)."""
    child_env = _scrubbed_env()
    command, unavailable = _prepare_command(root, code_refs, child_env, ())
    if unavailable is not None or command is None:
        return unavailable  # type: ignore[return-value]

    token = _compute_tree_token(root)
    # Normalize the claim (sorted, deduped) into the memo key — the stdout depends on
    # BOTH tree and claim, so same-tree/different-refs must re-derive.
    refs_key = _normalized_refs_key(code_refs)
    key = (str(Path(root).resolve()), token, refs_key) if token is not None else None
    if key is not None and key in _MEMO:
        return _MEMO[key]

    result, transient = _exec_and_parse(command, child_env)
    if not result.available and transient:
        # One retry — ONLY on a transient timeout (deterministic failures do not retry).
        result, _ = _exec_and_parse(command, child_env)

    if key is not None:
        _MEMO[key] = result
    return result


def derive_baseline_neighborhood(root: Path, code_refs: list[dict[str, Any]]) -> WitnessResult:
    """Derive the codeflair BASELINE neighborhood of ``code_refs`` (design node 04 — the
    prevention forecast). NEVER raises.

    Same FULL 02 envelope as :func:`derive_witness` (kernel-default trust root, argv[0] +
    tail screening, scrubbed env, neutral cwd, 120s, retry-on-timeout-only) but adds the
    ``--baseline-refs`` mode flag and parses the ``baseline_refs`` wire STRICTLY (incl. the
    ``mode`` key check). The memo keys on the committed HEAD sha (not the content-sensitive
    tree token) + the normalized claim + the mode literal, in a SEPARATE dict — so it never
    collides with the diff-mode memo, and a dirty tree with an unchanged HEAD reuses the
    baseline account (``workspace_dirty`` still testifies to the dirtiness)."""
    child_env = _scrubbed_env()
    command, unavailable = _prepare_command(root, code_refs, child_env, ("--baseline-refs",))
    if unavailable is not None or command is None:
        return unavailable  # type: ignore[return-value]

    head = _head_sha(root)
    refs_key = _normalized_refs_key(code_refs)
    key = (str(Path(root).resolve()), head, refs_key, _BASELINE_MODE) if head is not None else None
    if key is not None and key in _BASELINE_MEMO:
        # Memo hit still recomputes workspace_dirty (K1): the cached account carries the
        # dirtiness observed at its ORIGINAL derivation, which goes stale on a
        # clean->dirty transition at the same HEAD.
        return _with_fresh_workspace_dirty(root, _BASELINE_MEMO[key])

    result, transient = _exec_and_parse(command, child_env, _parse_baseline_facts)
    if not result.available and transient:
        result, _ = _exec_and_parse(command, child_env, _parse_baseline_facts)

    if key is not None:
        _BASELINE_MEMO[key] = result
    # Recompute on the fresh derivation too — the witness observes dirtiness at exec time,
    # but the kernel re-observes at RETURN time so both paths behave identically (K1).
    return _with_fresh_workspace_dirty(root, result)
