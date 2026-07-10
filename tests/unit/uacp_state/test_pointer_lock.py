"""TDD tests for #103-W1b2 (current.yaml pointer lock) + #103-W1 carve-out hardening.

W1-b2: the active-run pointer state/current.yaml is read-modify-written unlocked by
handle_init (seed), handle_abort (release), and uacp_state_write (caller-bound update).
Two concurrent writers lost-update the pointer (e.g. an abort release resurrected by a
racing update). W1-b2 serializes every pointer writer on one workspace-level advisory
lock, mirroring W1-b's registry lock.

Carve-out hardening: uacp_state_write's reserved-path guards were exact/case-sensitive.
On a case-insensitive FS (default macOS APFS / Windows) a case-variant spelling resolves
to the same inode and bypassed the guard; and a reserved FILE name as a non-final path
component would (via mkdir-parents) materialize the reserved path as a DIRECTORY (DoS).
The guards now match case-folded, on any component for the file reserves + lock sidecars.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import yaml
from state import _POINTER_LOCK_NAME, _handle_uacp_state_write, _workspace_state_lock


def _pointer(root: Path) -> dict:
    return yaml.safe_load((root / ".uacp" / "state" / "current.yaml").read_text())


def _state_write(root: Path, target_path: str, content: str, run_id: str = "r1") -> dict:
    return json.loads(
        _handle_uacp_state_write(
            {
                "target_path": target_path,
                "content": content,
                "reason": "w1b2 test",
                "authority_artifact": "plans/test.yaml",
                "workspace": str(root),
                "uacp_run_id": run_id,
                "uacp_phase": "execute",
                "policy_version": "0.1",
                "declared_side_effects": [],
            }
        )
    )


# ------------------------------------------------------------- the pointer lock serializes
def test_pointer_lock_serializes_threads(temp_uacp_root: Path):
    """While thread A holds the pointer lock, B blocks until A releases (strict order)."""
    root = temp_uacp_root
    order: list[str] = []
    a_locked = threading.Event()
    a_may_release = threading.Event()

    def thread_a():
        with _workspace_state_lock(root, _POINTER_LOCK_NAME):
            order.append("a-acquire")
            a_locked.set()
            a_may_release.wait(timeout=5)
            order.append("a-release")

    def thread_b():
        a_locked.wait(timeout=5)
        with _workspace_state_lock(root, _POINTER_LOCK_NAME):
            order.append("b-acquire")

    ta, tb = threading.Thread(target=thread_a), threading.Thread(target=thread_b)
    ta.start()
    tb.start()
    assert a_locked.wait(timeout=5)
    time.sleep(0.15)
    assert order == ["a-acquire"], f"B acquired while A held the lock: {order}"
    a_may_release.set()
    ta.join(timeout=5)
    tb.join(timeout=5)
    assert order == ["a-acquire", "a-release", "b-acquire"], order


def test_pointer_lock_distinct_from_registry_lock(temp_uacp_root: Path):
    """The pointer and registry locks are SEPARATE files — holding one must NOT block the
    other (they are acquired sequentially, never nested, so they must be independent)."""
    from state import _REGISTRY_LOCK_NAME

    root = temp_uacp_root
    acquired = threading.Event()

    def hold_pointer():
        with _workspace_state_lock(root, _POINTER_LOCK_NAME):
            acquired.wait(timeout=5)  # hold it

    t = threading.Thread(target=hold_pointer)
    t.start()
    # Registry lock must be immediately acquirable while the pointer lock is held.
    got = threading.Event()

    def take_registry():
        with _workspace_state_lock(root, _REGISTRY_LOCK_NAME):
            got.set()

    tr = threading.Thread(target=take_registry)
    tr.start()
    tr.join(timeout=5)
    assert got.is_set(), "registry lock blocked on the pointer lock — they must be distinct"
    acquired.set()
    t.join(timeout=5)


# ------------------------------------------------------------- no lost update on the pointer
def test_concurrent_pointer_writes_serialize(temp_uacp_root: Path):
    """Two concurrent caller-bound pointer updates for the SAME run serialize under the
    lock: each read-modify-write completes atomically, leaving a valid single mapping (not
    a torn/interleaved one). Without the lock the two RMWs race on current.yaml."""
    root = temp_uacp_root
    # Bootstrap the pointer for run r1.
    seed = _state_write(root, "state/current.yaml", "active_run_id: r1\nphase: execute\n")
    assert seed.get("ok") is True, seed

    barrier = threading.Barrier(2)
    errors: list[dict] = []

    def writer(marker: str):
        barrier.wait()
        out = _state_write(
            root, "state/current.yaml", f"active_run_id: r1\nphase: execute\nmark: {marker}\n"
        )
        if out.get("ok") is not True:
            errors.append(out)

    t1 = threading.Thread(target=writer, args=("a",))
    t2 = threading.Thread(target=writer, args=("b",))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)
    assert errors == [], errors
    # Final pointer is a valid mapping for r1 carrying exactly one of the two markers.
    final = _pointer(root)
    assert final["active_run_id"] == "r1", final
    assert final.get("mark") in {"a", "b"}, final


# ------------------------------------------------------------- carve-out hardening
def test_state_write_reserved_paths_are_case_insensitive(temp_uacp_root: Path):
    """Case-variant spellings of the reserved paths resolve to the same inode on a
    case-insensitive FS and must be refused too (a case-sensitive guard is a full bypass)."""
    root = temp_uacp_root
    cases = [
        ("state/RUN-REGISTRY.yaml", "{}\n", "run-registry"),
        ("state/GATE-LEDGER/x.yaml", "{}\n", "gate-ledger"),
        ("state/Escalations/x.yaml", "{}\n", "escalations"),
        ("state/RUNS/x.yaml", "{}\n", "runs"),
    ]
    for target, content, needle in cases:
        out = _state_write(root, target, content)
        assert "error" in out and needle in out["error"], (target, out)


def test_state_write_reserved_file_as_directory_component_refused(temp_uacp_root: Path):
    """A reserved FILE name as a non-final path component would (via _write_uacp_file's
    mkdir-parents) materialize the reserved path as a DIRECTORY, breaking every reader.
    Refuse it, and prove the reserved path was NOT created as a directory."""
    root = temp_uacp_root
    reg = _state_write(root, "state/run-registry.yaml/payload", "{}\n")
    assert "error" in reg and "run-registry" in reg["error"], reg
    assert not (root / ".uacp" / "state" / "run-registry.yaml").exists(), (
        "rejected write must not have created run-registry.yaml as a directory"
    )
    cur = _state_write(root, "state/current.yaml/payload", "{}\n")
    assert "error" in cur and "current.yaml" in cur["error"], cur
    assert not (root / ".uacp" / "state" / "current.yaml").exists(), (
        "rejected write must not have created current.yaml as a directory"
    )


def test_state_write_ordinary_pointer_still_allowed(temp_uacp_root: Path):
    """The hardening must not over-refuse: the normal caller-bound pointer write succeeds."""
    root = temp_uacp_root
    out = _state_write(root, "state/current.yaml", "active_run_id: r1\nphase: execute\n")
    assert out.get("ok") is True, out
