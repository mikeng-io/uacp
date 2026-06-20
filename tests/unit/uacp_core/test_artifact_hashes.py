"""Phase B increment 2a — the bounded per-run artifact hash index (detection).

A SHA-256 content watermark per governed artifact, stored as an overwrite-in-place
map under the guarded state/ namespace. Bounded by artifact COUNT (not write count),
so it can't grow without bound; git carries the change history.
"""
from __future__ import annotations

import sys
from pathlib import Path

_CORE_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

from engines.domain.artifact_hashes import (
    content_hash,
    hash_index_path,
    load_hash_index,
    record_hash,
)


def test_content_hash_is_sha256_hex_and_deterministic():
    h = content_hash("hello")
    assert h == content_hash("hello")
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)
    assert content_hash("hello") != content_hash("world")


def test_record_creates_index_under_guarded_state(tmp_path):
    record_hash(tmp_path, "r", "plans/p.yaml", "body-1")
    idx = load_hash_index(tmp_path, "r")
    assert idx["plans/p.yaml"] == content_hash("body-1")
    p = hash_index_path(tmp_path, "r")
    assert "state" in p.parts and p.name == "r.json"  # under .uacp/state/ -> guarded


def test_record_overwrites_in_place_not_appended(tmp_path):
    record_hash(tmp_path, "r", "plans/p.yaml", "v1")
    record_hash(tmp_path, "r", "plans/p.yaml", "v2")  # same artifact, new content
    idx = load_hash_index(tmp_path, "r")
    assert idx["plans/p.yaml"] == content_hash("v2")  # latest only
    assert len(idx) == 1  # bounded: one entry per artifact, not per write


def test_distinct_artifacts_get_distinct_entries(tmp_path):
    record_hash(tmp_path, "r", "plans/p.yaml", "a")
    record_hash(tmp_path, "r", "proposals/q.yaml", "b")
    idx = load_hash_index(tmp_path, "r")
    assert set(idx) == {"plans/p.yaml", "proposals/q.yaml"}


def test_load_index_empty_when_absent(tmp_path):
    assert load_hash_index(tmp_path, "nope") == {}
