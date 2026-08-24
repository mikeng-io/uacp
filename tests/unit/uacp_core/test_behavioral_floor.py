"""Unit tests for the M3 behavioral FLOOR engine (design/verify-substrate/02).

``validate_behavioral_floor`` grounds VERIFY on a FACT the git witness reports —
"the change set touched code" — not on an agent-declared class. When the witness
shows code changed, the run must carry >=1 ``uacp.check.behavioral`` node (which
replay then RUNS into substrate), else ``CHK_BEHAVIORAL_FLOOR_UNMET`` at a
config-gated severity (default ``warn``, flips to ``block`` in a later release).

Fixtures use a REAL git-init'd tmp repo for the fire paths (so the git witness has
something to observe) and a plain tmp dir for the noop path.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from engines.graph_projection import validate_behavioral_floor


def _prop(items: list) -> dict:
    return {"kind": "uacp.proposal", "scope": {"in_scope": items, "out_of_scope": []}}


def _plan(wus: list) -> dict:
    return {"kind": "uacp.plan", "work_units": wus}


def _check(check_id: str, target: str, kind: str = "uacp.check.field_present") -> dict:
    # A frozen uacp.check.* doc — projects as a `check` node whose `check_kind` is `kind`.
    # The behavioral floor only reads (kind == "check" AND check_kind == "uacp.check.behavioral");
    # the bind/expect payload is the replay engine's concern, kept minimal here.
    return {
        "kind": kind,
        "id": check_id,
        "from": {"target": target, "basis": f"{target} proven"},
        "bind": {"plane": "artifact", "ref": {"artifact": "plans/p.yaml", "path": "kind"}},
        "expect": {},
        "severity": "block",
    }


def _ws(tmp_path: Path, run: str = "r", checks: list | None = None) -> Path:
    """A minimal projectable .uacp workspace: proposal si-1 <- plan wu-1, plus the given checks."""
    base = tmp_path / ".uacp"
    (base / "state" / "runs").mkdir(parents=True)
    (base / "proposals").mkdir()
    (base / "plans").mkdir()
    arts = {"proposal": "proposals/p.yaml", "plan": "plans/p.yaml"}
    (base / "proposals" / "p.yaml").write_text(yaml.safe_dump(_prop([{"id": "si-1"}])))
    (base / "plans" / "p.yaml").write_text(
        yaml.safe_dump(_plan([{"id": "wu-1", "derives_from": ["si-1"]}]))
    )
    for i, doc in enumerate(checks or [], 1):
        (base / "plans" / f"c{i}.yaml").write_text(yaml.safe_dump(doc))
        arts[f"c{i}"] = f"plans/c{i}.yaml"
    (base / "state" / "runs" / f"{run}.yaml").write_text(
        yaml.safe_dump({"kind": "uacp.run_state", "run_id": run, "artifacts": arts})
    )
    return tmp_path


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)


def _add_code_file(path: Path, rel: str = "src/mod.py") -> None:
    f = path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("def x():\n    return 1\n")
    subprocess.run(["git", "-C", str(path), "add", rel], check=True)


def _codes(vs: list) -> list[str]:
    return [v.code for v in vs]


def test_non_git_dir_is_noop(tmp_path):
    # No git witness available -> nothing to ground -> [] (mirrors scope_conformance's noop).
    ws = _ws(tmp_path, checks=[_check("chk-1", "wu-1")])
    assert validate_behavioral_floor(ws, "r") == []


def test_code_change_without_behavioral_check_fires_warn(tmp_path):
    # The witness shows a .py changed and the run carries only a NON-behavioral check ->
    # exactly one CHK_BEHAVIORAL_FLOOR_UNMET at the default severity (warn).
    ws = _ws(tmp_path, checks=[_check("chk-1", "wu-1")])
    _git_init(ws)
    _add_code_file(ws)
    vs = validate_behavioral_floor(ws, "r")
    assert _codes(vs) == ["CHK_BEHAVIORAL_FLOOR_UNMET"], _codes(vs)
    assert vs[0].severity == "warn"
    assert vs[0].detail["code_changed"] == 1
    assert "src/mod.py" in vs[0].detail["examples"]


def test_code_change_with_behavioral_check_passes(tmp_path):
    # A uacp.check.behavioral node is present -> the floor is met -> [] (non-vacuity: the SAME
    # fixture WITHOUT the behavioral kind fires, per the test above).
    ws = _ws(tmp_path, checks=[_check("chk-1", "wu-1", kind="uacp.check.behavioral")])
    _git_init(ws)
    _add_code_file(ws)
    assert validate_behavioral_floor(ws, "r") == []


def test_non_code_change_is_exempt(tmp_path):
    # Only docs/config changed (the .md plus the run's own .uacp yaml) -> no code in the change
    # set -> no behavioral obligation -> [].
    ws = _ws(tmp_path, checks=[_check("chk-1", "wu-1")])
    _git_init(ws)
    note = ws / "docs" / "note.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("just docs\n")
    subprocess.run(["git", "-C", str(ws), "add", "docs/note.md"], check=True)
    assert validate_behavioral_floor(ws, "r") == []


def test_config_block_flips_severity(tmp_path):
    # [verification] behavioral_floor = "block" -> the same fire is severity block (the migration
    # flip works).
    ws = _ws(tmp_path, checks=[_check("chk-1", "wu-1")])
    (ws / ".uacp" / "config.toml").write_text('[verification]\nbehavioral_floor = "block"\n')
    _git_init(ws)
    _add_code_file(ws)
    vs = validate_behavioral_floor(ws, "r")
    assert _codes(vs) == ["CHK_BEHAVIORAL_FLOOR_UNMET"], _codes(vs)
    assert vs[0].severity == "block"


def test_config_garbage_falls_back_to_warn(tmp_path):
    # A non-{warn,block} value is fail-closed to the SAFE migration default (warn), never block.
    ws = _ws(tmp_path, checks=[_check("chk-1", "wu-1")])
    (ws / ".uacp" / "config.toml").write_text('[verification]\nbehavioral_floor = "loud"\n')
    _git_init(ws)
    _add_code_file(ws)
    vs = validate_behavioral_floor(ws, "r")
    assert _codes(vs) == ["CHK_BEHAVIORAL_FLOOR_UNMET"], _codes(vs)
    assert vs[0].severity == "warn"


def test_unobservable_repo_is_unwitnessed_warn(tmp_path):
    # An EXPECTED witness that cannot testify: a .git gitfile pointing at a broken gitdir makes
    # `git status` fail -> CHK_BEHAVIORAL_FLOOR_UNWITNESSED at warn (never a silent pass).
    from engines.io import changed_files

    ws = _ws(tmp_path, checks=[_check("chk-1", "wu-1")])
    (ws / ".git").write_text("gitdir: /nonexistent/broken-gitdir\n")
    if changed_files(Path(ws)).error is None:
        pytest.skip("platform git did not error on a malformed .git gitfile")
    vs = validate_behavioral_floor(ws, "r")
    assert _codes(vs) == ["CHK_BEHAVIORAL_FLOOR_UNWITNESSED"], _codes(vs)
    assert vs[0].severity == "warn"


def test_code_suffixes_are_runtime_neutral():
    # screening #172 P2 / lens 10: UACP is runtime-neutral, so the code-change detector must not be
    # Python-only -- a C#/PHP/Kotlin/Swift/... source change must count as code.
    from engines.manifest.projection import _CODE_SUFFIXES

    for ext in (".py", ".cs", ".php", ".kt", ".swift", ".scala", ".ex", ".lua", ".rb", ".go"):
        assert ext in _CODE_SUFFIXES, ext
        assert ("mod" + ext).endswith(_CODE_SUFFIXES), ext
