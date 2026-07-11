#!/usr/bin/env python3
"""Single-source generator for the governed-writer doc tables (#111).

Kills the propagation loop flagged by the #97 integration checker (findings 1/2):
the governed-writer list and the writer-to-path mapping were hand-restated in
canonical docs and had drifted from the kernel (phantom writers, omitted
run-lifecycle writers, a mapping that existed nowhere). This script DERIVES both
from code and injects them between sentinel comments, so docs reference the
kernel instead of restating it:

  * the governed-writer list — from ``tool_specs()`` (the actual registry;
    writers are the ``read_only=False`` specs) → AGENTS.md Invariant #3;
  * the writer-to-path table — writer names from ``tool_specs()``, state-plane
    path templates from ``engines.domain.layout``, artifact/doc/config roots
    parsed from ``governed_handlers.py``'s path validation, exclusivity
    carve-outs grounded against ``state.py``'s handler source (each documented
    carve-out must still exist in the source or generation FAILS — fail-closed)
    → docs/runtime/runtime-enforcement.md.

Modes:
  (default)   print both generated blocks to stdout
  --write     inject the blocks into the two docs (idempotent)
  --check     drift lint: regenerate, diff against the committed blocks, and
              validate the docs/INDEX.md repository inventory against the tree
              (non-`.uacp/` rows must exist; `.uacp/` rows are runtime-created).
              Exit 1 on any drift. Wired into `make lint` (CI quality job).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_CORE = ROOT / "skills" / "uacp-core" / "scripts"
_STATE = ROOT / "skills" / "uacp-state" / "scripts"
for _p in (_CORE, _STATE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from engines.domain import layout  # noqa: E402
from tool_specs import tool_specs  # noqa: E402

AGENTS_MD = ROOT / "AGENTS.md"
RUNTIME_DOC = ROOT / "docs" / "runtime" / "runtime-enforcement.md"
INDEX_MD = ROOT / "docs" / "INDEX.md"

WRITERS_BEGIN = (
    "<!-- BEGIN GENERATED: governed-writers — derived from "
    "skills/uacp-core/scripts/tool_specs.py by scripts/gen_doc_tables.py; "
    "do not edit by hand -->"
)
WRITERS_END = "<!-- END GENERATED: governed-writers -->"
TABLE_BEGIN = (
    "<!-- BEGIN GENERATED: writer-path-map — derived from tool_specs.py + "
    "state.py carve-outs + governed_handlers.py path validation + "
    "engines/domain/layout.py by scripts/gen_doc_tables.py; do not edit by hand -->"
)
TABLE_END = "<!-- END GENERATED: writer-path-map -->"


class DriftError(SystemExit):
    """Raised (as a non-zero SystemExit) when generation cannot be grounded."""

    def __init__(self, message: str) -> None:
        super().__init__(f"gen_doc_tables: {message}")


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------


def governed_writers() -> list[str]:
    """Writer names (read_only=False) in registry order — the single source."""
    return [s.name for s in tool_specs() if not s.read_only]


def read_only_tools() -> list[str]:
    """Read-only governed tool names in registry order."""
    return [s.name for s in tool_specs() if s.read_only]


def _require(src: str, pattern: str, what: str, where: str) -> re.Match[str]:
    """Ground a documented behavior in handler source, or fail closed."""
    m = re.search(pattern, src)
    if not m:
        raise DriftError(
            f"cannot ground {what} in {where} — the handler behavior this table "
            "documents has moved or changed; update scripts/gen_doc_tables.py"
        )
    return m


def _artifact_roots() -> list[str]:
    """uacp_artifact_write's allowed top-level roots, parsed from its handler."""
    src = (_CORE / "governed_handlers.py").read_text()
    m = _require(
        src,
        r"allowed_roots = \{([^}]*)\}",
        "uacp_artifact_write allowed_roots",
        "governed_handlers.py",
    )
    return sorted(re.findall(r'"(\w+)"', m.group(1)))


def _canonical_boundary(top: str) -> list[str]:
    """The suffix set for the docs/config canonical write boundary."""
    src = (_CORE / "governed_handlers.py").read_text()
    m = _require(
        src,
        rf'allowed_top="{top}", suffixes=\{{([^}}]*)\}}',
        f"allowed_top={top!r} canonical boundary",
        "governed_handlers.py",
    )
    return sorted(re.findall(r'"(\.\w+)"', m.group(1)))


def _state_carveouts() -> None:
    """Assert every carve-out the table documents still exists in state.py."""
    src = (_STATE / "state.py").read_text()
    for pattern, what in (
        (r"use uacp_gate_ledger_append", "gate-ledger carve-out"),
        (r"use uacp_run_registry_update", "run-registry carve-out"),
        (r"use uacp_escalation_event", "escalations carve-out"),
        (r"may not write under state/runs/", "run-manifest carve-out"),
        (r"current-pointer mutations must be caller-owned", "current.yaml caller binding"),
    ):
        _require(src, pattern, what, "skills/uacp-state/scripts/state.py")


def _secondary_writes() -> None:
    """Assert every SECONDARY write the table documents still exists in source
    (Codex P2, PR #124: under-reporting in a CI-blessed authoritative map is
    worse than absence — enforcement/docs consuming the table would believe
    those state paths are exclusive to other writers)."""
    sm = (_STATE / "state_machine.py").read_text()
    _require(
        sm,
        r"# Create current\.yaml pointer if none exists",
        "run_init pointer seeding",
        "skills/uacp-state/scripts/state_machine.py",
    )
    _require(
        sm,
        r"emit the canonical FROM->TO gate-ledger record",
        "transition-emitted canonical ledger records",
        "skills/uacp-state/scripts/state_machine.py",
    )
    gh_src = (_CORE / "governed_handlers.py").read_text()
    _require(
        gh_src,
        r"from engines\.domain\.artifact_hashes import record_hash",
        "artifact-write watermark recording",
        "governed_handlers.py",
    )
    ew = (_CORE / "engines" / "manifest" / "entity_writer.py").read_text()
    _require(
        ew,
        r"from engines\.domain\.artifact_hashes import .*record_hash",
        "entity-write watermark recording",
        "engines/manifest/entity_writer.py",
    )


def _template(kind: str, base: str) -> str:
    tmpl = layout.template(kind)
    if tmpl is None:
        raise DriftError(f"kind {kind!r} vanished from the layout registry")
    return f"{base}/{tmpl}"


def _relation_dirs() -> list[str]:
    return sorted(
        {
            layout.dir_of(k) or ""
            for k in layout.all_kinds()
            if layout.plane_of(k) == layout.RELATION
        }
    )


def writers_fragment() -> str:
    """The inline governed-writer list injected into AGENTS.md Invariant #3."""
    return ", ".join(f"`{name}`" for name in governed_writers())


def _default_base() -> str:
    """The governed namespace root name, from config/uacp.toml [paths]."""
    from config import load_config

    return load_config().paths.base


def writer_path_table(base: str | None = None) -> str:
    """The writer-to-path markdown table injected into runtime-enforcement.md."""
    if base is None:
        base = _default_base()
    _state_carveouts()
    _secondary_writes()
    artifact_roots = _artifact_roots()
    doc_suffixes = "/".join(f"`{s}`" for s in _canonical_boundary("docs"))
    config_suffixes = "/".join(f"`{s}`" for s in _canonical_boundary("config"))
    relation_dirs = ", ".join(f"`{base}/{d}/`" for d in _relation_dirs())
    artifact_cell = ", ".join(f"`{base}/{r}/`" for r in artifact_roots)
    run_lifecycle = [
        w
        for w in governed_writers()
        if w.startswith("uacp_run_") and w != "uacp_run_registry_update"
    ]

    covered: list[str] = []

    def row(writers: list[str], writes: str, notes: str) -> str:
        covered.extend(writers)
        cell = ", ".join(f"`{w}`" for w in writers)
        return f"| {cell} | {writes} | {notes} |"

    lines = [
        "| Governed writer | Writes | Exclusivity / notes |",
        "|---|---|---|",
        row(
            ["uacp_state_write"],
            f"`{base}/state/**`",
            "Generic state writer. Refuses the exclusive carve-outs below "
            "(`state/gate-ledger/`, `state/run-registry.yaml`, `state/escalations/`, "
            "`state/runs/`); writes to `state/current.yaml` are caller-bound "
            "(`active_run_id` must match the caller's `uacp_run_id`).",
        ),
        row(
            ["uacp_gate_ledger_append"],
            f"`{_template('uacp.gate_ledger', base)}`",
            "Exclusive append-only ledger writer.",
        ),
        row(
            ["uacp_run_registry_update"],
            f"`{_template('uacp.run_registry', base)}`",
            "Exclusive registry mutator (`op=register`/`deregister`).",
        ),
        row(
            ["uacp_escalation_event"],
            f"`{_template('uacp.escalations', base)}`",
            "Exclusive append-only escalation writer.",
        ),
        row(
            run_lifecycle,
            f"`{_template('uacp.run_manifest', base)}` "
            f"+ `{base}/state/current.yaml` (seeded by `uacp_run_init` when absent) "
            f"+ `{_template('uacp.gate_ledger', base)}` (canonical `FROM->TO`/"
            "`TRIAGE_COMPLETE` records emitted by `uacp_run_transition`)",
            "Exclusive owners of the run manifest (the uacp-state run-lifecycle "
            "operations). The pointer seed and canonical ledger emits are "
            "SECONDARY writes: the manifest is the primary surface.",
        ),
        row(
            ["uacp_entity_write"],
            f"RELATION-plane manifest kinds → {relation_dirs} per the layout "
            "registry (`skills/uacp-core/scripts/engines/domain/layout.py`)",
            "The ONLY writer for manifest documents: validates by `kind`, "
            f"records watermarks under `{base}/state/hashes/`, and registers "
            f"the entity into the run manifest (`{_template('uacp.run_manifest', base)}`).",
        ),
        row(
            ["uacp_artifact_write"],
            artifact_cell,
            "Non-manifest artifacts only; rejects `state/`, `docs/`, `config/` "
            "and any RELATION-plane manifest kind (use `uacp_entity_write`). "
            f"Records watermarks under `{base}/state/hashes/`.",
        ),
        row(
            ["uacp_corpus_write"],
            f"`{base}/lessons/**` + `{base}/knowledge/**` (OKF `.md`)",
            "Oracle corpus writer (lessons + knowledge). Parses the authored OKF "
            "into a `Lesson`/`KnowledgeItem` and persists via `uacp_artifact_write` "
            "(the Oracle owns corpus read + write).",
        ),
        row(
            ["uacp_doc_write"],
            f"`docs/**` ({doc_suffixes}; repo-root-relative, not under `{base}/`)",
            "Canonical docs boundary.",
        ),
        row(
            ["uacp_config_write"],
            f"`config/**` ({config_suffixes}; repo-root-relative, not under `{base}/`)",
            "Canonical config boundary.",
        ),
        row(
            ["uacp_contained_shell"],
            "the declared execution workspace only",
            "Contained shell surface (bwrap read-only root); mints state, not a namespace writer.",
        ),
        "",
        "Read-only governed tools (no write path): "
        + ", ".join(f"`{t}`" for t in read_only_tools())
        + ".",
    ]

    if sorted(covered) != sorted(governed_writers()):
        missing = set(governed_writers()) - set(covered)
        extra = set(covered) - set(governed_writers())
        raise DriftError(
            "writer-path table no longer covers the registry exactly "
            f"(missing rows: {sorted(missing)}; stale rows: {sorted(extra)}); "
            "update scripts/gen_doc_tables.py"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Injection (idempotent) + drift check
# ---------------------------------------------------------------------------


def inject(text: str, begin: str, end: str, payload: str) -> str:
    """Replace the region between sentinels with payload. Idempotent."""
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(text):
        raise DriftError(f"sentinel pair not found: {begin[:60]}...")
    return pattern.sub(lambda _m: f"{begin}{payload}{end}", text, count=1)


def extract(text: str, begin: str, end: str) -> str | None:
    pattern = re.compile(re.escape(begin) + r"(.*?)" + re.escape(end), re.DOTALL)
    m = pattern.search(text)
    return m.group(1) if m else None


def _targets() -> list[tuple[Path, str, str, str]]:
    return [
        (AGENTS_MD, WRITERS_BEGIN, WRITERS_END, writers_fragment()),
        (RUNTIME_DOC, TABLE_BEGIN, TABLE_END, "\n" + writer_path_table() + "\n"),
    ]


def write() -> None:
    for path, begin, end, payload in _targets():
        path.write_text(inject(path.read_text(), begin, end, payload))
        print(
            f"gen_doc_tables: injected {begin.split(':')[1].split('—')[0].strip()} into {path.relative_to(ROOT)}"
        )


# --- inventory validation (docs/INDEX.md "Repository inventory") -------------

_LEGACY_TOP_LEVEL = (
    "state/",
    "plans/",
    "proposals/",
    "executions/",
    "verification/",
    "resolutions/",
    ".outputs/",
    "knowledge/",
    "lessons/",
)


def inventory_paths() -> list[str]:
    """First-cell paths of the INDEX.md repository-inventory table."""
    text = INDEX_MD.read_text()
    m = re.search(r"## Repository inventory.*?\n(\|.*?)\n\n", text, re.DOTALL)
    if not m:
        raise DriftError("could not locate the Repository inventory table in docs/INDEX.md")
    paths: list[str] = []
    for line in m.group(1).splitlines()[2:]:  # skip header + separator
        cell = line.split("|")[1].strip()
        for chunk in cell.split(","):
            p = chunk.strip().strip("`").strip()
            # `config/uacp.toml ([guardian])`-style rows: check the file part.
            p = p.split(" (")[0].strip().strip("`")
            if p:
                paths.append(p)
    return paths


def _runtime_created(p: str) -> bool:
    """A `.uacp/` inventory row is exempt from tree-existence ONLY when it is
    runtime-created — i.e. gitignored. Committed rows under the namespace (the
    tracked knowledge/lesson/handoff corpus dirs) must exist: a blanket
    exemption would let typos/deletions in those rows pass the drift lint
    unchecked (Codex P2, PR #124)."""
    if not (p.startswith(".uacp/") or p == ".uacp"):
        return False
    if p == ".uacp":
        return True  # the namespace root itself is runtime-seeded in a fresh clone
    # Keep the trailing slash: `dir/`-style gitignore patterns only match
    # directories, and for a not-yet-created path git can only know it's a
    # directory from the probe's own trailing slash.
    probe = p if p.endswith("/") else p + "/"
    for candidate in (probe, p.rstrip("/")):
        result = subprocess.run(
            ["git", "check-ignore", "-q", candidate],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return True
    return False


def check_inventory() -> list[str]:
    """Inventory drift: ghost rows + rows whose path is absent from the tree."""
    errors: list[str] = []
    for p in inventory_paths():
        if _runtime_created(p):
            continue  # gitignored = runtime-created; absent in a fresh clone by design
        if p in _LEGACY_TOP_LEVEL:
            errors.append(f"docs/INDEX.md inventory row `{p}` is the pre-.uacp ghost layout")
            continue
        if not (ROOT / p).exists():
            errors.append(f"docs/INDEX.md inventory row `{p}` does not exist in the tree")
    return errors


def check() -> int:
    errors: list[str] = []
    for path, begin, end, payload in _targets():
        committed = extract(path.read_text(), begin, end)
        if committed is None:
            errors.append(f"{path.relative_to(ROOT)}: sentinel block missing ({begin[:50]}...)")
        elif committed != payload:
            errors.append(
                f"{path.relative_to(ROOT)}: generated block drifted from the kernel — "
                "run `python3 scripts/gen_doc_tables.py --write` and commit"
            )
    errors.extend(check_inventory())
    if errors:
        for e in errors:
            print(f"DRIFT: {e}", file=sys.stderr)
        return 1
    print("gen_doc_tables: no drift (writer list, writer-path map, inventory all current)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="inject generated blocks into the docs")
    mode.add_argument("--check", action="store_true", help="fail (exit 1) on drift")
    args = parser.parse_args()
    if args.write:
        write()
        return 0
    if args.check:
        return check()
    print(WRITERS_BEGIN + writers_fragment() + WRITERS_END)
    print()
    print(TABLE_BEGIN + "\n" + writer_path_table() + "\n" + TABLE_END)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
