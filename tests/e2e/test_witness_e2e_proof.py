"""E2E proof for issue #85 (run via pytest from the scope-verify worktree root).

Faithful operator path, no stubs: real git workspace + seeded coherent run,
code_refs declared on the run's own scope artifact, [witness].codeflair_cli
configured via .uacp/config.toml pointing at a shim that execs the REAL
`codeflair witness` (uv project, vendored scip-python), validate() derives +
compares at sweep time.
"""

import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml
from engines.io import clear_witness_memo
from engines.scope_conformance import validate

from tests.e2e.test_coherence import seed_coherent_run

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCIP_PYTHON = REPO_ROOT / "codeflair" / "vendor" / "node_modules" / ".bin" / "scip-python"

pytestmark = pytest.mark.skipif(
    shutil.which("uv") is None or not _SCIP_PYTHON.exists(),
    reason="real-witness e2e needs uv + the vendored scip-python "
    "(npm install in codeflair/vendor); the stubbed teeth tests cover the gate logic",
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def test_e2e_real_codeflair_witness_advisory(temp_uacp_root: Path, valid_run_id: str, monkeypatch):
    root = temp_uacp_root
    seed_coherent_run(root, valid_run_id)

    scope_path = root / ".uacp" / "plans" / f"{valid_run_id}-scope.yaml"
    scope = yaml.safe_load(scope_path.read_text())
    scope["write_paths"] = ["src/**"]
    scope["code_refs"] = [{"file": "src/calc.py", "name": "helper"}]
    scope_path.write_text(yaml.safe_dump(scope, sort_keys=False))
    reg_path = root / ".uacp" / "state" / "run-registry.yaml"
    reg = yaml.safe_load(reg_path.read_text())
    reg["active_runs"][0]["write_paths"] = ["src/**"]
    reg_path.write_text(yaml.safe_dump(reg, sort_keys=False))

    # A shim outside the run workspace that execs the REAL codeflair CLI.
    shim = Path(tempfile.mkdtemp(prefix="witness-cli-")) / "codeflair-shim"
    shim.write_text(f'#!/bin/sh\nexec uv run --project "{REPO_ROOT}/codeflair" codeflair "$@"\n')
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
    # K1: the trust root is the KERNEL-DEFAULT config, resolved via the operator-config seam
    # (NOT the workspace .uacp/config.toml, which is now ignored for [witness]). Point the
    # seam at a temp operator toml naming the shim.
    import engines.io.witnessio as witnessio

    op = Path(tempfile.mkdtemp(prefix="witness-op-")) / "operator-uacp.toml"
    op.write_text(f'[witness]\ncodeflair_cli = "{shim}"\n')
    monkeypatch.setattr(witnessio, "_operator_config_path", lambda: op)

    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed", "--no-verify")

    (root / "src").mkdir()
    (root / "src" / "calc.py").write_text(
        "def helper():\n    return 1\n\n\ndef caller():\n    return helper()\n"
    )
    (root / "src" / "other.py").write_text("def lonely():\n    return 42\n")

    clear_witness_memo()
    violations = validate(root, valid_run_id)

    print("\n=== violations ===")
    for v in violations:
        print(f"[{v.severity}] {v.code}: {v.message[:160]}")

    codes = {v.code for v in violations}
    cascade = [v for v in violations if v.code == "SC_UNDECLARED_CASCADE"]
    assert cascade, f"expected SC_UNDECLARED_CASCADE, got {codes}"
    assert any("lonely" in v.message for v in cascade), cascade[0].message
    assert not any("caller" in v.message for v in cascade), (
        "caller is hop-1 of declared helper and must be covered: " + cascade[0].message
    )
    assert "SC_WITNESS_UNAVAILABLE" not in codes, codes
    assert "SC_DIFF_OUT_OF_SCOPE" not in codes, codes
    assert all(v.severity == "warn" for v in cascade)
