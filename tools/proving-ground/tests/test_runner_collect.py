"""Collection-side honesty: exit codes of still-running containers and destroyed-git visibility."""

from __future__ import annotations

import json
import subprocess

import runner
from cells import hermes_bare
from runner import Task, _collect_container, _git_capture, run_cell


def _fake_run_factory(inspect_payload: str):
    """Fake runner._run: `docker inspect` returns the payload; everything else exits 0."""

    def fake_run(cmd, timeout=60.0):
        if cmd[1] == "inspect":
            return subprocess.CompletedProcess(cmd, 0, stdout=inspect_payload, stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return fake_run


def test_running_container_yields_no_exit_code(tmp_path, monkeypatch):
    """A watchdog-orphaned container reports ExitCode 0 while Running -- must NOT be trusted."""
    payload = json.dumps([{"State": {"Running": True, "ExitCode": 0}}])
    monkeypatch.setattr(runner, "_run", _fake_run_factory(payload))
    assert _collect_container("pg-test", tmp_path, docker="docker") is None


def test_stopped_container_exit_code_is_reported(tmp_path, monkeypatch):
    payload = json.dumps([{"State": {"Running": False, "ExitCode": 137}}])
    monkeypatch.setattr(runner, "_run", _fake_run_factory(payload))
    assert _collect_container("pg-test", tmp_path, docker="docker") == 137


def test_git_capture_failure_is_visible_not_empty(tmp_path):
    """If the SUT destroyed .git, the exported file must carry a marker, not an empty string."""
    out = _git_capture(tmp_path, ["log", "--oneline", "--all"])  # tmp_path is not a git repo
    assert out.startswith("[git log --oneline --all failed:")


def test_stale_workspace_is_wiped_before_baseline(tmp_path):
    """Reusing an output dir must NOT leak a prior run's files into the baseline commit.

    Observed live: a re-run into records/smoke-out inherited the previous run's hello.txt, the
    baseline commit swallowed it, and the exported diff/status reported "no changes" for a run
    that wrote a file. `docker` is faked with /bin/echo -- the ACP exchange errors out fast, but
    workspace setup and trail collection still execute for real.
    """
    out_dir = tmp_path / "rep-000"
    stale = out_dir / "workspace" / "stale-from-prior-run.txt"
    stale.parent.mkdir(parents=True)
    stale.write_text("left over\n")

    cell = hermes_bare()
    task = Task(name="probe", prompt="x")
    result = run_cell(cell, task, out_dir, timeout=5, docker="/bin/echo")

    workspace = out_dir / "workspace"
    assert not (workspace / "stale-from-prior-run.txt").exists()
    log = subprocess.run(
        ["git", "-C", str(workspace), "log", "--stat", "--all"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "runner: baseline" in log.stdout
    assert "stale-from-prior-run" not in log.stdout
    assert result.outcome in ("error", "timeout")  # /bin/echo is not an ACP agent
