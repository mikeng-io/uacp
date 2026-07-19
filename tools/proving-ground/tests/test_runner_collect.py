"""Collection-side honesty: exit codes of still-running containers and destroyed-git visibility."""

from __future__ import annotations

import json
import subprocess

import runner
from cells import hermes_bare


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
    assert runner._collect_container("pg-test", tmp_path, docker="docker") is None


def test_stopped_container_exit_code_is_reported(tmp_path, monkeypatch):
    payload = json.dumps([{"State": {"Running": False, "ExitCode": 137}}])
    monkeypatch.setattr(runner, "_run", _fake_run_factory(payload))
    assert runner._collect_container("pg-test", tmp_path, docker="docker") == 137


def test_workspace_made_world_writable_for_container_user(tmp_path):
    """A Linux host with uid != 1000 bind-mounts a workspace the container's `agent` user cannot
    write into — and outcomes-only smoke would count the resulting no-op as `completed`. The
    runner must open the workspace up before the container starts (Codex P1 on PR #158)."""
    ws = tmp_path / "ws"
    sub = ws / "seeded"
    sub.mkdir(parents=True)
    f = sub / "file.txt"
    f.write_text("x")
    f.chmod(0o444)
    sub.chmod(0o755)
    ws.chmod(0o755)

    runner._make_world_writable(ws)

    assert ws.stat().st_mode & 0o777 == 0o777
    assert sub.stat().st_mode & 0o777 == 0o777
    assert f.stat().st_mode & 0o666 == 0o666


def test_uacp_export_never_dereferences_sut_symlinks(tmp_path):
    """Exfiltration guard (Codex P1 on PR #158): the SUT controls the workspace, so a symlink
    planted under .uacp (or .uacp itself as a symlink) must never be dereferenced by the
    runner-host collector — skipped, with a visible skip record."""
    secret = tmp_path / "host-secret.txt"
    secret.write_text("runner-host private data\n")

    # Case 1: symlinked child inside a real .uacp dir.
    ws1 = tmp_path / "ws1"
    (ws1 / ".uacp").mkdir(parents=True)
    (ws1 / ".uacp" / "state.json").write_text("{}")
    (ws1 / ".uacp" / "planted").symlink_to(secret)
    out1 = tmp_path / "out1"
    out1.mkdir()
    runner._collect_workspace(ws1, out1)
    assert (out1 / "uacp" / "state.json").exists()
    assert not (out1 / "uacp" / "planted").exists()
    exported = [str(p) for p in (out1 / "uacp").rglob("*")]
    assert all("planted" not in p for p in exported)
    assert "planted" in (out1 / "uacp-SKIPPED.txt").read_text()

    # Case 2: .uacp itself is a symlink to a host directory.
    hostdir = tmp_path / "hostdir"
    hostdir.mkdir()
    (hostdir / "leak.txt").write_text("leak")
    ws2 = tmp_path / "ws2"
    ws2.mkdir()
    (ws2 / ".uacp").symlink_to(hostdir)
    out2 = tmp_path / "out2"
    out2.mkdir()
    runner._collect_workspace(ws2, out2)
    assert not (out2 / "uacp").exists()
    assert "symlink" in (out2 / "uacp-SKIPPED.txt").read_text()


def test_git_capture_failure_is_visible_not_empty(tmp_path):
    """If the SUT destroyed .git, the exported file must carry a marker, not an empty string."""
    out = runner._git_capture(tmp_path, ["log", "--oneline", "--all"])  # tmp_path is not a git repo
    assert out.startswith("[git log --oneline --all failed:")


def test_missing_docker_is_an_error_replicate_not_a_crash(tmp_path):
    """Docker absent end-to-end: drive AND collection must both survive (Codex P1 on PR #158).

    run_prompt maps the spawn failure to an `error` outcome; collection then invokes
    `docker inspect` with the same missing binary and must record that instead of raising —
    otherwise the sweep aborts and the aggregate is lost anyway.
    """
    out_dir = tmp_path / "rep-000"
    cell = hermes_bare()
    task = runner.Task(name="probe", prompt="x")
    result = runner.run_cell(cell, task, out_dir, timeout=5, docker="/nonexistent-docker-binary")

    assert result.outcome == "error"
    assert result.detail is not None and result.detail.startswith("spawn failed:")
    assert result.exit_code is None
    # The trail is still written: inspect failure recorded, meta.json present.
    inspect = json.loads((out_dir / "runner-side" / "container-inspect.json").read_text())
    assert "spawn failed" in inspect["error"]
    meta = json.loads((out_dir / "runner-side" / "meta.json").read_text())
    assert meta["outcome"] == "error"
    # Containment honesty: every S1 record must self-report that the declared egress policy is
    # NOT yet enforced at the container boundary (enforcement = S2 proxy sidecar, 50-plan).
    assert meta["egress"] == "host-model"
    assert meta["egress_enforced"] is False


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
    task = runner.Task(name="probe", prompt="x")
    result = runner.run_cell(cell, task, out_dir, timeout=5, docker="/bin/echo")

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


def test_inspect_env_credentials_are_redacted(tmp_path, monkeypatch):
    """docker inspect echoes the full env; a real provider key must never persist raw into the
    (committed) evidence artifact (Codex P1 on PR #158)."""
    payload = json.dumps(
        [
            {
                "State": {"Running": False, "ExitCode": 0},
                "Config": {
                    "Env": [
                        "OPENAI_API_KEY=sk-super-secret-value",
                        "MY_AUTH_TOKEN=tok123",
                        "UACP_MODEL_ID=qwen3.5:4b",
                        "PATH=/usr/bin",
                    ]
                },
            }
        ]
    )
    monkeypatch.setattr(runner, "_run", _fake_run_factory(payload))
    exit_code = runner._collect_container("pg-test", tmp_path, docker="docker")
    assert exit_code == 0
    written = (tmp_path / "container-inspect.json").read_text()
    assert "sk-super-secret-value" not in written
    assert "tok123" not in written
    assert "OPENAI_API_KEY=[REDACTED]" in written
    assert "MY_AUTH_TOKEN=[REDACTED]" in written
    # Non-secret env stays intact — the evidence remains useful.
    assert "UACP_MODEL_ID=qwen3.5:4b" in written
    assert "PATH=/usr/bin" in written


def test_git_capture_neutralizes_sut_planted_exec_config(tmp_path):
    """Container-escape guard (Codex P1 on PR #158): a SUT that plants an exec-capable git
    config key (core.fsmonitor) into its workspace must NOT get that command run on the runner
    host when the collector reads git status/diff."""
    ws = tmp_path / "ws"
    ws.mkdir()
    subprocess.run(["git", "-C", str(ws), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(ws), "commit", "-q", "--allow-empty", "-m", "base"], check=True
    )
    # The SUT plants a payload: fsmonitor points at a command that would touch a runner-host file.
    canary = tmp_path / "PWNED"
    ws_config = ws / ".git" / "config"
    ws_config.write_text(ws_config.read_text() + f'\n[core]\n\tfsmonitor = "touch {canary}"\n')
    # Collection reads git status/diff via the hardened helper.
    out = runner._git_capture(ws, ["status", "--porcelain"])
    runner._git_capture(ws, ["diff", "--no-ext-diff", "--no-textconv", "HEAD"])
    assert not canary.exists(), "SUT-planted core.fsmonitor executed on the runner host"
    assert "failed" not in out  # status still works with the override


def test_uacp_export_skips_special_files_without_hanging(tmp_path):
    """A SUT-planted FIFO under .uacp would block copy2's open() forever (this collector runs
    after the watchdog with no timeout). Special files must be skipped, not opened (Codex P1)."""
    import os
    import threading

    ws = tmp_path / "ws"
    (ws / ".uacp").mkdir(parents=True)
    (ws / ".uacp" / "state.json").write_text("{}")
    os.mkfifo(ws / ".uacp" / "pipe")  # the blocking trap

    out = tmp_path / "out"
    out.mkdir()
    done = threading.Event()

    def run():
        runner._collect_workspace(ws, out)
        done.set()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    # If the FIFO were opened, this collector would hang forever; a real timeout catches that.
    assert done.wait(timeout=15), "collector hung on a SUT-planted FIFO"
    assert (out / "uacp" / "state.json").exists()
    assert not (out / "uacp" / "pipe").exists()
    assert "pipe" in (out / "uacp-SKIPPED.txt").read_text()
