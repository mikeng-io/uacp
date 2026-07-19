"""The runner: spawn a cell container, drive it over ACP, collect the trail. No judgments.

Per 20-runner the runner does four things and only these: bake (out of scope here -- the image is
pre-built by the entry gate), spawn a fresh SUT container per run, drive over ACP stdio, and
collect the trail on terminal state (or watchdog timeout -- an L3 signal, not a crash). It returns
artifacts, never verdicts (the runner/observer seam is the same declared-vs-witnessed seam the
framework governs).

The output layout keeps 10-topology's **two evidence classes** physically separate:

* ``runner-side/`` -- ground truth the SUT cannot author: the ACP transcript captured on the
  runner's side of the boundary, ``docker inspect`` (exit code + timestamps), and run metadata.
* ``sut-authored/`` -- weighted evidence written *inside* the container and exported at collection
  time: the workspace git log/diff/tree and any ``.uacp/`` directory.

stdlib only.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from acp_client import run_prompt
from cells import EGRESS_ENFORCED, Cell


@dataclass(frozen=True)
class Task:
    """A pinned probe task. ``setup`` seeds the fresh workspace before the container runs."""

    name: str
    prompt: str

    def setup(self, workspace: Path) -> None:  # noqa: B027 (intentionally overridable no-op)
        """Populate a fresh workspace. Default: leave it empty (git is init'd by the runner)."""


@dataclass
class RunResult:
    """Artifacts + terminal-state facts for one replicate. Deliberately carries NO verdict."""

    cell: str
    task: str
    model_id: str
    outcome: str  # completed | timeout | error
    started_at: str
    ended_at: str
    wall_clock_s: float
    artifact_dir: str
    exit_code: int | None = None
    stop_reason: str | None = None
    detail: str | None = None
    container: str | None = None
    extra: dict = field(default_factory=dict)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _run(cmd: list[str], timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
    """Run a collection/setup command; NEVER raise. A missing executable or a hung command is a
    per-replicate fact to record (returncode 127/124 + stderr), not an exception — an unhandled
    raise here would abort the whole serial sweep and lose the aggregate."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except OSError as exc:
        return subprocess.CompletedProcess(cmd, 127, stdout="", stderr=f"spawn failed: {exc}")
    except subprocess.TimeoutExpired as exc:
        out = (
            exc.stdout.decode(errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        err = (
            exc.stderr.decode(errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        return subprocess.CompletedProcess(
            cmd, 124, stdout=out, stderr=err + f"\n[timed out after {timeout}s]"
        )


def _make_world_writable(workspace: Path) -> None:
    """The container runs as its own unprivileged user (uid 1000), which on a Linux host with a
    different uid cannot write into a bind-mounted 755 workspace — and an outcomes-only smoke
    would then count a can't-write-anything run as `completed` (vacuous pass). The workspace is
    throwaway evidence scratch, so open it up: dirs 0o777, files 0o666."""
    workspace.chmod(0o777)
    for p in workspace.rglob("*"):
        if p.is_symlink():
            continue
        p.chmod(0o777 if p.is_dir() else 0o666)


def run_cell(
    cell: Cell,
    task: Task,
    output_dir: str | Path,
    *,
    timeout: float = 240.0,
    docker: str = "docker",
) -> RunResult:
    """Spawn ``cell`` on ``task`` once, drive it, and export the trail into ``output_dir``."""
    output_dir = Path(output_dir)
    runner_side = output_dir / "runner-side"
    sut_authored = output_dir / "sut-authored"
    workspace = output_dir / "workspace"
    for path in (runner_side, sut_authored, workspace):
        # Freshness is an evidence-integrity requirement, not hygiene: a stale workspace from a
        # prior run gets swallowed into the baseline commit, and the exported diff/status then
        # UNDER-report what the agent did (observed live on a smoke re-run into records/).
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)

    # Fresh, git-initialised workspace so a diff/log can witness the agent's tool actions.
    task.setup(workspace)
    _run(["git", "-C", str(workspace), "init", "-q"])
    _run(["git", "-C", str(workspace), "config", "user.email", "runner@proving-ground.local"])
    _run(["git", "-C", str(workspace), "config", "user.name", "proving-ground-runner"])
    # Baseline commit: HEAD must exist so the exported `git diff HEAD` witnesses exactly what the
    # agent changed relative to the seeded initial state.
    _run(["git", "-C", str(workspace), "add", "-A"])
    _run(["git", "-C", str(workspace), "commit", "-q", "--allow-empty", "-m", "runner: baseline"])
    _make_world_writable(workspace)

    container = f"pg-{cell.name}-{uuid.uuid4().hex[:12]}"
    docker_cmd = [
        docker,
        "run",
        "-i",
        "--name",
        container,
        "--add-host=host.docker.internal:host-gateway",
        "-v",
        f"{workspace.resolve()}:{cell.workspace_mount}",
        "-w",
        cell.workspace_mount,
    ]
    for key, value in cell.render_env().items():
        docker_cmd += ["-e", f"{key}={value}"]
    docker_cmd.append(cell.image)

    transcript = runner_side / "acp-exchange.log"
    started = _utcnow()
    t0 = time.monotonic()
    result = run_prompt(
        docker_cmd,
        task.prompt,
        cwd=str(workspace),
        session_cwd=cell.workspace_mount,
        timeout=timeout,
        transcript_path=transcript,
    )
    wall_clock = time.monotonic() - t0
    ended = _utcnow()

    exit_code = _collect_container(container, runner_side, docker=docker)
    _collect_workspace(workspace, sut_authored)

    run_result = RunResult(
        cell=cell.name,
        task=task.name,
        model_id=cell.model_id,
        outcome=result.outcome,
        started_at=started,
        ended_at=ended,
        wall_clock_s=round(wall_clock, 3),
        artifact_dir=str(output_dir),
        exit_code=exit_code,
        stop_reason=result.stop_reason,
        detail=result.detail,
        container=container,
        extra={
            "agent_text": result.text,
            "update_count": result.update_count,
            "stderr_tail": result.stderr_tail,
            "acp_error": result.error,
        },
    )
    (runner_side / "meta.json").write_text(
        json.dumps(_meta(cell, task, run_result), indent=2), encoding="utf-8"
    )
    return run_result


def _meta(cell: Cell, task: Task, result: RunResult) -> dict:
    return {
        "cell": cell.name,
        "image": cell.image,
        "task": task.name,
        "model_id": cell.model_id,
        "egress": cell.egress,
        "egress_enforced": EGRESS_ENFORCED,
        "uacp": cell.uacp,
        "outcome": result.outcome,
        "stop_reason": result.stop_reason,
        "detail": result.detail,
        "exit_code": result.exit_code,
        "started_at": result.started_at,
        "ended_at": result.ended_at,
        "wall_clock_s": result.wall_clock_s,
        "container": result.container,
        "agent_text": result.extra.get("agent_text"),
        "update_count": result.extra.get("update_count"),
        "stderr_tail": result.extra.get("stderr_tail"),
        "acp_error": result.extra.get("acp_error"),
    }


# Env names whose values must never reach the persisted evidence (docker inspect echoes the
# full env in Config.Env; with a real provider key the raw dump would leak the credential to
# disk and — under the committed-evidence contract — into version control).
_SENSITIVE_ENV_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")


def _redact_env_line(line: str) -> str:
    name, sep, _ = line.partition("=")
    if sep and any(marker in name.upper() for marker in _SENSITIVE_ENV_MARKERS):
        return f"{name}=[REDACTED]"
    return line


def _redact_inspect(data: list) -> list:
    for entry in data:
        if not isinstance(entry, dict):
            continue
        config = entry.get("Config")
        if isinstance(config, dict) and isinstance(config.get("Env"), list):
            config["Env"] = [
                _redact_env_line(e) if isinstance(e, str) else e for e in config["Env"]
            ]
    return data


def _collect_container(container: str, runner_side: Path, *, docker: str) -> int | None:
    """Capture ``docker inspect`` (exit code + timestamps, secrets redacted) then remove the
    container. Fail-closed: unparseable inspect output is never persisted raw — it could carry
    the credential we redact."""
    exit_code: int | None = None
    inspect = _run([docker, "inspect", container])
    if inspect.returncode == 0:
        try:
            data = json.loads(inspect.stdout)
            state = data[0].get("State", {}) if data else {}
            # A watchdog kill terminates the `docker run` CLI but can orphan the container;
            # Docker reports ExitCode 0 for a still-Running container, which would masquerade
            # as a clean exit. Only trust ExitCode once the container has actually stopped.
            exit_code = None if state.get("Running") else state.get("ExitCode")
            (runner_side / "container-inspect.json").write_text(
                json.dumps(_redact_inspect(data), indent=2), encoding="utf-8"
            )
        except (json.JSONDecodeError, IndexError, KeyError):
            exit_code = None
            (runner_side / "container-inspect.json").write_text(
                json.dumps({"error": "inspect output unparseable; not persisted (may carry env)"}),
                encoding="utf-8",
            )
    else:
        (runner_side / "container-inspect.json").write_text(
            json.dumps({"error": inspect.stderr.strip()}), encoding="utf-8"
        )
    _run([docker, "rm", "-f", container])
    return exit_code


# Post-run, workspace/.git/config is SUT-CONTROLLED, and these git commands run on the RUNNER
# host: config keys that name an executable (core.fsmonitor for `status`, external diff /
# textconv drivers for `diff`, hooksPath) would hand the SUT code execution with runner
# privileges — a container escape through the evidence collector. Command-line `-c` overrides
# take precedence over every config file (including ones pulled in via include.path).
_GIT_UNTRUSTED_OVERRIDES = [
    "-c", "core.fsmonitor=false",
    "-c", "core.hooksPath=/dev/null",
    "-c", "core.pager=cat",
]  # fmt: skip


def _git_capture(workspace: Path, args: list[str]) -> str:
    """Run a git command for export, with SUT-set exec-capable config neutralized. A failure
    (e.g. the SUT destroyed .git) must be VISIBLE in the exported file, not an indistinguishable
    empty string — this evidence class is weighted precisely because the SUT can tamper with it."""
    proc = _run(["git", *_GIT_UNTRUSTED_OVERRIDES, "-C", str(workspace), *args])
    if proc.returncode != 0:
        return f"[git {' '.join(args)} failed: exit {proc.returncode}: {proc.stderr.strip()}]\n"
    return proc.stdout


def _collect_workspace(workspace: Path, sut_authored: Path) -> None:
    """Export the SUT-authored trail: git log/status/diff, file tree, and any .uacp/."""
    (sut_authored / "git-log.txt").write_text(
        _git_capture(workspace, ["log", "--oneline", "--all"]), encoding="utf-8"
    )
    (sut_authored / "git-status.txt").write_text(
        _git_capture(workspace, ["status", "--porcelain"]), encoding="utf-8"
    )
    (sut_authored / "git-diff.txt").write_text(
        # --no-ext-diff/--no-textconv: diff drivers are the diff-side exec vector (attributes +
        # SUT config can name arbitrary commands to render the diff).
        _git_capture(workspace, ["diff", "--no-ext-diff", "--no-textconv", "HEAD"]),
        encoding="utf-8",
    )
    tree = sorted(
        str(p.relative_to(workspace))
        for p in workspace.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(workspace).parts
    )
    (sut_authored / "workspace-tree.txt").write_text("\n".join(tree) + "\n", encoding="utf-8")

    # The workspace tree is SUT-CONTROLLED and this collector runs on the runner host: a
    # malicious agent could plant `.uacp` (or children) as symlinks to host paths, and a
    # dereferencing copy would exfiltrate runner-readable files into the evidence export.
    # Never dereference — skip every symlink and export a visible skip record instead.
    uacp_dir = workspace / ".uacp"
    if uacp_dir.is_symlink():
        (sut_authored / "uacp-SKIPPED.txt").write_text(
            f"[.uacp is a symlink -> {uacp_dir.readlink()}; not exported]\n", encoding="utf-8"
        )
    elif uacp_dir.is_dir():
        skipped: list[str] = []

        def _ignore_symlinks(src: str, names: list[str]) -> list[str]:
            bad = [n for n in names if (Path(src) / n).is_symlink()]
            skipped.extend(
                f"{(Path(src) / n).relative_to(uacp_dir)} -> {(Path(src) / n).readlink()}"
                for n in bad
            )
            return bad

        shutil.copytree(
            uacp_dir, sut_authored / "uacp", ignore=_ignore_symlinks, dirs_exist_ok=True
        )
        if skipped:
            (sut_authored / "uacp-SKIPPED.txt").write_text(
                "[symlinks inside .uacp are never exported]\n" + "\n".join(skipped) + "\n",
                encoding="utf-8",
            )
