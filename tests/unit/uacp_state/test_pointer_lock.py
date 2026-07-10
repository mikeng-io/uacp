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
def test_uacp_state_write_pointer_update_acquires_the_lock(temp_uacp_root: Path):
    """NON-VACUOUS guard that the uacp_state_write current.yaml branch actually takes the
    pointer lock: while the lock is held externally, a pointer update MUST block until
    release. (A vacuous version — two full-content writers of the same run — passes on
    W1-a's atomic replace alone even with the lock removed; this one fails if the lock is
    dropped from that code path, because the update would not block.)"""
    root = temp_uacp_root
    seed = _state_write(root, "state/current.yaml", "active_run_id: r1\nphase: execute\n")
    assert seed.get("ok") is True, seed

    lock_held = threading.Event()
    release = threading.Event()
    done = threading.Event()

    def hold_lock():
        with _workspace_state_lock(root, _POINTER_LOCK_NAME):
            lock_held.set()
            release.wait(timeout=5)

    def update():
        lock_held.wait(timeout=5)  # only write once the lock is definitely held
        _state_write(root, "state/current.yaml", "active_run_id: r1\nphase: execute\nmark: x\n")
        done.set()

    th = threading.Thread(target=hold_lock)
    tu = threading.Thread(target=update)
    th.start()
    tu.start()
    assert lock_held.wait(timeout=5)
    time.sleep(0.2)
    assert not done.is_set(), (
        "pointer update completed while the pointer lock was held — the lock is missing "
        "from the uacp_state_write current.yaml write path"
    )
    release.set()
    th.join(timeout=5)
    tu.join(timeout=5)
    assert done.is_set(), "pointer update never completed after lock release"
    assert _pointer(root).get("mark") == "x", _pointer(root)


def test_pointer_noncanonical_variant_never_desyncs(temp_uacp_root: Path):
    """Codex #140 P2 (a+b): a case-variant spelling (state/CURRENT.yaml) case-folds into the
    pointer branch but must never desync the pointer. On a case-sensitive FS the exact-case
    guard REJECTS it (writing the caller's distinct file, or redirecting via .resolve()
    through a symlink, are both refused); on a case-insensitive FS it resolves to the same
    inode and is serviced as the canonical pointer. Either way: no stale pointer, no stray
    file — FS-robust invariant."""
    root = temp_uacp_root
    assert _state_write(root, "state/current.yaml", "active_run_id: r1\n").get("ok") is True
    out = _state_write(root, "state/CURRENT.yaml", "active_run_id: r1\nmark: x\n")
    if "error" in out:
        # case-sensitive FS: rejected as non-canonical, pointer left untouched.
        assert "canonical" in out["error"], out
        assert _pointer(root).get("mark") is None, _pointer(root)
    else:
        # case-insensitive FS: serviced as THE canonical pointer (same inode).
        assert out["path"].endswith("state/current.yaml"), out
        assert _pointer(root).get("mark") == "x", _pointer(root)


def test_pointer_write_never_escapes_worktree_via_symlink(temp_uacp_root: Path, tmp_path: Path):
    """Codex #140 P2b: if state/current.yaml is a symlink to an out-of-tree file, the pointer
    write must NOT follow it out of the worktree. _resolve_uacp_path rejects symlinked
    components and the write targets that contained path — never a re-resolved one. Proven by
    the out-of-tree file staying pristine (the old .resolve()-write would have clobbered it)."""
    root = temp_uacp_root
    state = root / ".uacp" / "state"
    state.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "escape-target.yaml"
    outside.write_text("PRISTINE\n", encoding="utf-8")
    (state / "current.yaml").symlink_to(outside)
    # Attempt to write the pointer via both the exact and the variant spelling.
    _state_write(root, "state/current.yaml", "active_run_id: r1\n")
    _state_write(root, "state/CURRENT.yaml", "active_run_id: r1\n")
    assert outside.read_text(encoding="utf-8") == "PRISTINE\n", (
        "pointer write escaped the worktree through a symlinked current.yaml"
    )


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
