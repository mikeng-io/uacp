"""C-1 guard: loaders resolve state under .uacp/, never the flat root."""

from engines.io import loaders


def test_manifest_path_is_under_uacp(tmp_path):
    # A manifest at the OLD flat location must NOT be found.
    (tmp_path / "state" / "runs").mkdir(parents=True)
    (tmp_path / "state" / "runs" / "r1.yaml").write_text("run_id: r1\n")
    assert loaders.load_manifest(tmp_path, "r1").error is not None

    # A manifest under .uacp/ IS found.
    (tmp_path / ".uacp" / "state" / "runs").mkdir(parents=True)
    (tmp_path / ".uacp" / "state" / "runs" / "r1.yaml").write_text("run_id: r1\n")
    loaded = loaders.load_manifest(tmp_path, "r1")
    assert loaded.error is None and loaded.value.raw["run_id"] == "r1"


def test_resolve_in_workspace_resolves_under_uacp(tmp_path):
    # Base-relative artifact refs resolve under .uacp/, not the flat root.
    resolved = loaders.resolve_in_workspace(tmp_path, "proposals/r1-intent.md")
    assert resolved == (tmp_path / ".uacp" / "proposals" / "r1-intent.md").resolve()
    # Traversal escaping the governed base is rejected (None, never raises).
    assert loaders.resolve_in_workspace(tmp_path, "../../etc/passwd") is None


def test_glob_in_workspace_globs_under_uacp(tmp_path):
    # A file under flat proposals/ must NOT match; one under .uacp/ must.
    (tmp_path / "proposals").mkdir(parents=True)
    (tmp_path / "proposals" / "r1-x.yaml").write_text("x: 1\n")
    assert loaders.glob_in_workspace(tmp_path, "proposals/r1-*.yaml") == []

    (tmp_path / ".uacp" / "proposals").mkdir(parents=True)
    target = tmp_path / ".uacp" / "proposals" / "r1-x.yaml"
    target.write_text("x: 1\n")
    matches = loaders.glob_in_workspace(tmp_path, "proposals/r1-*.yaml")
    assert matches == [target]


def test_load_text_under_root_reads_contained_markdown(tmp_path):
    # A markdown manifest doc under .uacp/ is read as raw text (not YAML-parsed).
    d = tmp_path / ".uacp" / "proposals"
    d.mkdir(parents=True)
    (d / "r1-intent.md").write_text("# Intent\n\n- not: a, mapping\n", encoding="utf-8")
    loaded = loaders.load_text_under_root(tmp_path, "proposals/r1-intent.md")
    assert loaded.error is None
    assert loaded.value == "# Intent\n\n- not: a, mapping\n"


def test_load_text_under_root_missing_is_error(tmp_path):
    loaded = loaders.load_text_under_root(tmp_path, "proposals/nope.md")
    assert loaded.value is None
    assert loaded.error is not None and "not found" in loaded.error


def test_load_text_under_root_rejects_escape(tmp_path):
    # Containment: a traversal escaping the governed base is an error, never a raise.
    loaded = loaders.load_text_under_root(tmp_path, "../../etc/passwd")
    assert loaded.value is None
    assert loaded.error is not None and "escapes UACP root" in loaded.error
