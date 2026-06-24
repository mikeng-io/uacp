"""Grep probe: distinctive-literal extraction + cross-language shared-string coupling."""
from codeflair import Store
from codeflair.grep_probe import extract_string_literals, ingest_shared_strings


def test_extract_keeps_structured_literals_drops_trivial():
    text = '''
    route = "/api/v1/users"
    event = "user.created"
    short = "hi"
    prose = "the quick brown fox jumps"
    n = "12345"
    '''
    toks = extract_string_literals(text)
    assert "/api/v1/users" in toks      # route -> structured
    assert "user.created" in toks       # event -> structured
    assert "hi" not in toks             # too short
    assert "the quick brown fox jumps" not in toks  # prose, no separator
    assert "12345" not in toks          # pure digits


def test_shared_string_couples_cross_language_files():
    # a Go handler and a TS client share the same route literal -> coupling
    files = {
        "api/handler.go": 'r.GET("/api/v1/orders", listOrders)',
        "web/client.ts": 'fetch("/api/v1/orders")',
        "unrelated.py": 'x = "/different/path"',
    }
    s = Store()
    pairs = ingest_shared_strings(s, files)
    assert pairs == 1
    coupled = s.coupled_files("api/handler.go", kind="shared_string")
    assert coupled == [("web/client.ts", "shared_string", 1)]
    assert s.coupled_files("unrelated.py", kind="shared_string") == []


def test_ubiquitous_literal_is_dropped():
    # a token in more than max_files files is boilerplate, not coupling
    files = {f"f{i}.go": 'h = "application/json"' for i in range(12)}
    s = Store()
    pairs = ingest_shared_strings(s, files, max_files_per_token=8)
    assert pairs == 0
    assert s.coupled_files("f0.go") == []


def test_single_file_token_makes_no_coupling():
    s = Store()
    pairs = ingest_shared_strings(s, {"only.go": 'x = "/unique/route/here"'})
    assert pairs == 0


def test_weight_accumulates_over_multiple_shared_tokens():
    files = {
        "a.go": '"/api/orders" ; "order.shipped"',
        "b.ts": '"/api/orders" ; "order.shipped"',
    }
    s = Store()
    ingest_shared_strings(s, files)
    assert s.coupled_files("a.go", kind="shared_string") == [("b.ts", "shared_string", 2)]
