"""Unit tests for the Layer 2 correctness-screening FLOOR (design/grounded-governance/03).

``validate_correctness_screening`` makes a correctness screening non-skippable, grounded, and
fixpoint-enforced: when the git witness shows the run changed CODE, VERIFY may not clear unless a
correctness-screening artifact EXISTS, RESOLVES, and COVERS the kernel-produced substrate
(``gitio.diff_content`` over ``merge-base..HEAD``). The substrate identity is a sha256 over the
base + HEAD + diff text, so any fix that moves HEAD makes a prior screening STALE — the fixpoint.

Fixtures use a REAL git-init'd tmp repo for the fire paths (base commit on ``main``, the change on
a feature branch that is HEAD, so there is a real merge-base and a real diff) plus a minimal
projectable ``.uacp`` workspace, mirroring ``test_behavioral_floor.py``.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import yaml

from engines.graph_projection import validate_correctness_screening
from engines.io import diff_content


# --------------------------------------------------------------------------- workspace fixture
def _ws(tmp_path: Path, run: str = "r") -> Path:
    """A minimal .uacp workspace with a registered run manifest (no screening artifact)."""
    base = tmp_path / ".uacp"
    (base / "state" / "runs").mkdir(parents=True)
    (base / "verification" / run).mkdir(parents=True)
    (base / "state" / "runs" / f"{run}.yaml").write_text(
        yaml.safe_dump({"kind": "uacp.run_state", "run_id": run, "artifacts": {}})
    )
    return tmp_path


def _write_screening(tmp_path: Path, run: str, substrate_hash: str, name: str = "screening") -> None:
    """Place a lenient correctness-screening artifact under verification/{run}/ (slice 3 will add
    the governed writer + schema; this gate loads leniently, keying on kind + substrate_hash)."""
    p = tmp_path / ".uacp" / "verification" / run / f"{name}.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "kind": "uacp.correctness_screening",
                "run_id": run,
                "substrate_hash": substrate_hash,
            }
        )
    )


# --------------------------------------------------------------------------- git fixture
def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def _init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    _git(path, "config", "user.email", "t@example.com")
    _git(path, "config", "user.name", "Test")
    _git(path, "config", "commit.gpgsign", "false")


def _commit(path: Path, rel: str, body: str, msg: str) -> None:
    f = path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body)
    _git(path, "add", rel)
    _git(path, "commit", "-q", "-m", msg)


def _code_change_repo(ws: Path, head_body: str = "def x():\n    return 999\n") -> None:
    """A repo whose HEAD (feature) is one CODE change ahead of the default branch (main), so the
    correctness gate sees code changed AND a real merge-base/diff substrate exists."""
    _init(ws)
    _git(ws, "checkout", "-q", "-b", "main")
    _commit(ws, "src/mod.py", "def x():\n    return 1\n", "base")
    _git(ws, "checkout", "-q", "-b", "feature")
    _commit(ws, "src/mod.py", head_body, "change")


def _current_hash(ws: Path) -> str:
    dc = diff_content(Path(ws))
    payload = f"{dc.base_commit or ''}\n{dc.head_commit or ''}\n{dc.text}"
    return hashlib.sha256(payload.encode()).hexdigest()


def _codes(vs: list) -> list[str]:
    return [v.code for v in vs]


# =========================================================================== tests
def test_non_git_dir_is_noop(tmp_path):
    # No git witness / no substrate -> [] (synthetic fixtures).
    ws = _ws(tmp_path)
    assert validate_correctness_screening(ws, "r") == []


def test_code_change_without_screening_fires_missing_warn(tmp_path):
    # Code changed and NO screening artifact -> exactly one CHK_CORRECTNESS_SCREENING_MISSING at
    # the default severity (warn).
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    vs = validate_correctness_screening(ws, "r")
    assert _codes(vs) == ["CHK_CORRECTNESS_SCREENING_MISSING"], _codes(vs)
    assert vs[0].severity == "warn"
    assert vs[0].detail["code_changed"] == 1
    assert vs[0].detail["substrate_hash"] == _current_hash(ws)


def test_matching_screening_passes(tmp_path):
    # A screening whose substrate_hash matches the CURRENT diff covers it -> [] (non-vacuity: the
    # SAME fixture without the artifact fires MISSING, per the test above).
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    _write_screening(tmp_path, "r", _current_hash(ws))
    assert validate_correctness_screening(ws, "r") == []


def test_stale_screening_fires_stale(tmp_path):
    # A screening built for an OLD diff, then HEAD advances -> the old hash no longer covers ->
    # CHK_CORRECTNESS_SCREENING_STALE (the fixpoint: re-screen the moved delta).
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    stale = _current_hash(ws)
    _write_screening(tmp_path, "r", stale)
    # HEAD advances (a fix moves the diff) — the screening's hash is now stale.
    _commit(ws, "src/mod.py", "def x():\n    return 12345\n", "fix")
    assert _current_hash(ws) != stale  # the substrate identity moved
    vs = validate_correctness_screening(ws, "r")
    assert _codes(vs) == ["CHK_CORRECTNESS_SCREENING_STALE"], _codes(vs)
    assert vs[0].severity == "warn"
    assert stale in vs[0].detail["found_hashes"]


def test_docs_only_change_is_exempt(tmp_path):
    # Only docs changed (no code suffix in the change set) -> no screening obligation -> [].
    ws = _ws(tmp_path)
    _init(ws)
    _git(ws, "checkout", "-q", "-b", "main")
    _commit(ws, "README.md", "# base\n", "base")
    _git(ws, "checkout", "-q", "-b", "feature")
    _commit(ws, "docs/note.md", "just docs\n", "change")
    assert validate_correctness_screening(ws, "r") == []


def test_config_block_flips_severity(tmp_path):
    # [verification] correctness_screening = "block" -> the MISSING fire is severity block.
    ws = _ws(tmp_path)
    (ws / ".uacp" / "config.toml").write_text(
        '[verification]\ncorrectness_screening = "block"\n'
    )
    _code_change_repo(ws)
    vs = validate_correctness_screening(ws, "r")
    assert _codes(vs) == ["CHK_CORRECTNESS_SCREENING_MISSING"], _codes(vs)
    assert vs[0].severity == "block"


def test_config_garbage_falls_back_to_warn(tmp_path):
    # A non-{warn,block} value is fail-closed to the SAFE migration default (warn), never block.
    ws = _ws(tmp_path)
    (ws / ".uacp" / "config.toml").write_text(
        '[verification]\ncorrectness_screening = "loud"\n'
    )
    _code_change_repo(ws)
    vs = validate_correctness_screening(ws, "r")
    assert _codes(vs) == ["CHK_CORRECTNESS_SCREENING_MISSING"], _codes(vs)
    assert vs[0].severity == "warn"


def test_no_merge_base_reports_substrate_unavailable(tmp_path):
    # Code changed but NO default-branch merge-base (only a uniquely-named branch) -> the substrate
    # cannot be produced -> CHK_CORRECTNESS_SUBSTRATE_UNAVAILABLE, ALWAYS warn (env fact).
    # The witness sees code via a STAGED (uncommitted) change; HEAD still resolves (base commit),
    # but with no main/master/origin there is no merge-base for diff_content to precipitate.
    ws = _ws(tmp_path)
    _init(ws)
    _git(ws, "checkout", "-q", "-b", "topic-only")
    _commit(ws, "src/mod.py", "def x():\n    return 1\n", "base")
    (ws / "src" / "mod.py").write_text("def x():\n    return 2\n")
    _git(ws, "add", "src/mod.py")
    vs = validate_correctness_screening(ws, "r")
    assert _codes(vs) == ["CHK_CORRECTNESS_SUBSTRATE_UNAVAILABLE"], _codes(vs)
    assert vs[0].severity == "warn"
    assert vs[0].detail["error"] == "no merge-base"
