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
