"""Co-change probe: git-log parse + support-thresholded coupling."""
from codeflair import Store
from codeflair.cochange import parse_git_log, ingest_cochange, _COMMIT_MARK


def _log(*commits: list[str]) -> str:
    return "".join(f"{_COMMIT_MARK}\n" + "\n".join(files) + "\n" for files in commits)


def test_parse_git_log_splits_commits_and_files():
    text = _log(["a.go", "b.go"], ["c.go"])
    assert parse_git_log(text) == [["a.go", "b.go"], ["c.go"]]


def test_cochange_stores_pairs_meeting_min_support():
    s = Store()
    # a.go & b.go change together twice; a.go & c.go once
    commits = [["a.go", "b.go"], ["a.go", "b.go"], ["a.go", "c.go"]]
    stored = ingest_cochange(s, commits, min_support=2)
    assert stored == 1                                  # only (a,b) clears support=2
    coupled = s.coupled_files("a.go", kind="co_change")
    assert coupled == [("b.go", "co_change", 2)]         # weight = co-change count
    assert s.coupled_files("c.go", kind="co_change") == []


def test_cochange_skips_mega_commits():
    s = Store()
    mega = [f"f{i}.go" for i in range(60)]               # 60 files > cap -> noise, skipped
    ingest_cochange(s, [mega, mega], min_support=1)
    assert s.coupled_files("f0.go") == []


def test_cochange_path_suffix_filter():
    s = Store()
    commits = [["a.go", "b.go", "README.md"], ["a.go", "b.go", "notes.txt"]]
    ingest_cochange(s, commits, min_support=2, path_suffixes=(".go",))
    coupled = {f for f, _, _ in s.coupled_files("a.go")}
    assert coupled == {"b.go"}                           # md/txt filtered out


def test_cochange_pair_is_order_independent():
    s = Store()
    ingest_cochange(s, [["b.go", "a.go"], ["a.go", "b.go"]], min_support=2)
    assert s.coupled_files("b.go") == [("a.go", "co_change", 2)]
