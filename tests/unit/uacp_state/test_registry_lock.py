"""TDD tests for #103-W1b: cross-writer advisory lock on the shared run-registry.

The run registry is read-modify-written by multiple UNSERIALIZED writers
(uacp_run_registry_update register/deregister + handle_abort's deregister). Without a
shared lock, two concurrent writers each read the active_runs list, modify their own
copy, and write back — a lost update where the second write clobbers the first. W1-b
serializes every registry writer on one workspace-level advisory lock.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import yaml
from state import _handle_uacp_run_registry_update, _workspace_state_lock


def _registry(root: Path) -> dict:
    return yaml.safe_load((root / ".uacp" / "state" / "run-registry.yaml").read_text())


# --------------------------------------------------------------- the lock serializes
def test_workspace_state_lock_serializes_threads(temp_uacp_root: Path):
    """flock is per open-file-description, so two threads each opening the lockfile get
    distinct fds and are serialized: while A holds the lock, B blocks until A releases."""
    root = temp_uacp_root
    order: list[str] = []
    a_locked = threading.Event()
    a_may_release = threading.Event()

    def thread_a():
        with _workspace_state_lock(root, "run-registry.yaml"):
            order.append("a-acquire")
            a_locked.set()
            a_may_release.wait(timeout=5)
            order.append("a-release")

    def thread_b():
        a_locked.wait(timeout=5)  # only race for the lock once A definitely holds it
        with _workspace_state_lock(root, "run-registry.yaml"):
            order.append("b-acquire")

    ta, tb = threading.Thread(target=thread_a), threading.Thread(target=thread_b)
    ta.start()
    tb.start()
    assert a_locked.wait(timeout=5)
    time.sleep(0.15)  # give B a window to (fail to) acquire while A holds it
    assert order == ["a-acquire"], f"B acquired while A held the lock: {order}"
    a_may_release.set()
    ta.join(timeout=5)
    tb.join(timeout=5)
    # B acquired only AFTER A released — strict serialization.
    assert order == ["a-acquire", "a-release", "b-acquire"], order


# --------------------------------------------------------------- no lost update
def _register(root: Path, rid: str) -> dict:
    import json

    return json.loads(
        _handle_uacp_run_registry_update(
            {
                "op": "register",
                "entry": {
                    "run_id": rid,
                    "phase": "execute",
                    "write_paths": [],
                    "no_writes_intended": True,
                    "scope_artifact_path": "",
                    "started_at": 0,
                },
                "reason": "concurrency test",
                "authority_artifact": "plans/test.yaml",
                "workspace": str(root),
                "uacp_run_id": rid,
                "uacp_phase": "execute",
                "policy_version": "0.1",
                "declared_side_effects": [],
            }
        )
    )


def test_concurrent_registers_do_not_lose_updates(temp_uacp_root: Path):
    """N threads each register a DISTINCT run at the same instant. Under the shared
    registry lock every registration's read-modify-write is serialized, so ALL N
    entries survive — no second write clobbers a first (the lost-update this closes)."""
    root = temp_uacp_root
    n = 8
    barrier = threading.Barrier(n)
    errors: list[dict] = []

    def worker(i: int):
        barrier.wait()  # release all threads together to maximize RMW overlap
        out = _register(root, f"run-{i}")
        if out.get("ok") is not True:
            errors.append(out)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert errors == [], errors
    ids = {e["run_id"] for e in _registry(root)["active_runs"]}
    assert ids == {f"run-{i}" for i in range(n)}, f"lost registrations: {ids}"


def test_concurrent_register_and_deregister_serialize(temp_uacp_root: Path):
    """A tool deregister and abort's _deregister_run_from_registry share the SAME lock,
    so a register racing a deregister of a DIFFERENT run cannot lose either result."""
    from state import _deregister_run_from_registry

    root = temp_uacp_root
    # Seed two runs.
    _register(root, "keep")
    _register(root, "drop")
    assert {e["run_id"] for e in _registry(root)["active_runs"]} == {"keep", "drop"}

    barrier = threading.Barrier(2)

    def do_register():
        barrier.wait()
        _register(root, "new")

    def do_deregister():
        barrier.wait()
        _deregister_run_from_registry(root, "drop")

    t1, t2 = threading.Thread(target=do_register), threading.Thread(target=do_deregister)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)
    # 'new' added AND 'drop' removed, both survived the race; 'keep' untouched.
    ids = {e["run_id"] for e in _registry(root)["active_runs"]}
    assert ids == {"keep", "new"}, ids


# --------------------------------------------------- lockfile inode is not swappable
def _state_write(root: Path, target_path: str, content: str) -> dict:
    """Drive the generic governed state writer, the only writer that reaches state/."""
    import json

    from state import _handle_uacp_state_write

    return json.loads(
        _handle_uacp_state_write(
            {
                "target_path": target_path,
                "content": content,
                "reason": "codex-p2 test",
                "authority_artifact": "plans/test.yaml",
                "workspace": str(root),
                "uacp_run_id": "r1",
                "uacp_phase": "execute",
                "policy_version": "0.1",
                "declared_side_effects": [],
            }
        )
    )


def test_state_write_refuses_registry_lockfile(temp_uacp_root: Path):
    """The advisory lock only serializes if its sidecar keeps a STABLE inode. The atomic
    _write_uacp_file (os.replace) would mint a fresh inode, letting a holder of the old
    inode and an opener of the new one both 'hold' the lock. uacp_state_write — the one
    generic writer that reaches state/ — must therefore REFUSE the lockfile path so the
    inode can never be swapped out from under _workspace_state_lock (#103-W1b, Codex P2)."""
    root = temp_uacp_root
    out = _state_write(root, "state/.run-registry.yaml.lock", "{}\n")
    assert "error" in out and ".lock" in out["error"], out
    # And the reserve is general, not one hard-coded name — future sidecars (e.g. the
    # W1-b2 current.yaml lock) are covered by the same rule.
    out2 = _state_write(root, "state/.current.yaml.lock", "{}\n")
    assert "error" in out2 and ".lock" in out2["error"], out2
    # Case-insensitive: on a case-insensitive FS (default macOS/Windows) a `.LOCK`
    # spelling resolves to the SAME inode as `.lock`, so it must be refused too — a
    # case-sensitive check would be a full bypass on the platform this actually runs on.
    out3 = _state_write(root, "state/.run-registry.yaml.LOCK", "{}\n")
    assert "error" in out3 and ".lock" in out3["error"], out3
    # Path COMPONENT, not just basename: `.../.run-registry.yaml.lock/payload` would
    # (via _write_uacp_file's mkdir-parents) materialize the lockfile path as a DIRECTORY,
    # so the next _workspace_state_lock os.open raises IsADirectoryError and bricks the
    # registry workspace-wide. A final-component-only guard would miss this.
    out4 = _state_write(root, "state/.run-registry.yaml.lock/payload", "{}\n")
    assert "error" in out4 and ".lock" in out4["error"], out4
    # The lockfile path must NOT have been materialized as a directory by the rejected write.
    assert not (root / ".uacp" / "state" / ".run-registry.yaml.lock").exists(), (
        "rejected nested write must not have created the lockfile directory"
    )


def test_state_write_still_allows_ordinary_state_file(temp_uacp_root: Path):
    """The .lock carve-out must not over-refuse: a normal state write still succeeds."""
    root = temp_uacp_root
    out = _state_write(root, "state/scratch.yaml", "k: v\n")
    assert out.get("ok") is True, out
