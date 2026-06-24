#!/usr/bin/env python3
"""Codeflair spike — multi-language FUSION test.

Usage:  python3 fuse.py index_go.scip index_ts.scip [...]

Proves: SCIP indexes from different languages fuse into ONE SQLite graph,
namespaced by scheme (no collision), each queryable, within-language edges
precise, cross-language = no symbol edge (the co-change/grep boundary).
"""
import sys, json, sqlite3, subprocess, os, time, bisect

DB = "fused.db"
SCIP = "./scip"
DEF = 0x1

def lang_of(symbol: str) -> str:
    # SCIP symbol scheme is the first token: "scip-go ..." / "scip-typescript ..."
    head = symbol.split(" ", 1)[0]
    return {"scip-go": "go", "scip-typescript": "ts", "scip-python": "py"}.get(head, head or "?")

def name_of(sym): return sym.split(" ")[-1].split("/")[-1] or sym

def load_index(con, scip_path):
    raw = subprocess.run([SCIP, "print", "--json", scip_path], capture_output=True, text=True).stdout
    data = json.loads(raw)
    occ = []
    for d in data["documents"]:
        path = d.get("relative_path", "")
        for o in d.get("occurrences", []):
            rng = o.get("range", [])
            sym = o.get("symbol", "")
            if not rng or not sym or sym.startswith("local "):
                continue
            occ.append((sym, lang_of(sym), path, rng[0], 1 if o.get("symbol_roles", 0) & DEF else 0))
    con.executemany("INSERT INTO occ(symbol,lang,path,line,is_def) VALUES (?,?,?,?,?)", occ)
    con.commit()
    return len(data["documents"]), len(occ)

def build_edges(con):
    defs = {}
    for sym, path, line in con.execute("SELECT symbol,path,line FROM occ WHERE is_def=1"):
        defs.setdefault(path, []).append((line, sym))
    for p in defs: defs[p].sort()
    edges = []
    for sym, path, line in con.execute("SELECT symbol,path,line FROM occ WHERE is_def=0"):
        arr = defs.get(path)
        if not arr: continue
        i = bisect.bisect_right(arr, (line, "￿")) - 1
        if i >= 0 and arr[i][1] != sym:
            edges.append((arr[i][1], sym))
    con.executemany("INSERT INTO edges(src,dst) VALUES (?,?)", edges)
    con.commit()
    return len(edges)

def main():
    if os.path.exists(DB): os.remove(DB)
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE occ(symbol TEXT, lang TEXT, path TEXT, line INT, is_def INT)")
    con.execute("CREATE TABLE edges(src TEXT, dst TEXT)")

    print("=== FUSION INGEST ===")
    for idx in sys.argv[1:]:
        nd, no = load_index(con, idx)
        print(f"  {idx:24s} -> {nd:>5,} docs, {no:>7,} occurrences")
    con.execute("CREATE INDEX i_sym ON occ(symbol)")
    con.execute("CREATE INDEX i_src ON edges(src)")
    con.execute("CREATE INDEX i_dst ON edges(dst)")
    ne = build_edges(con)
    con.commit()

    print(f"\n=== ONE STORE, BY LANGUAGE ===")
    for lang, n, nd in con.execute(
        "SELECT lang, COUNT(*), COUNT(DISTINCT path) FROM occ GROUP BY lang ORDER BY 2 DESC"):
        print(f"  {lang:4s}: {n:>7,} occurrences across {nd:,} files")
    print(f"  edges (within-language): {ne:,}")
    print(f"  db size: {os.path.getsize(DB)/1e6:.1f} MB")

    # namespacing: a Go symbol and a TS symbol coexist with zero collision
    print(f"\n=== NAMESPACING (no collision) ===")
    for lang in ("go", "ts"):
        r = con.execute("SELECT symbol FROM occ WHERE lang=? AND is_def=1 LIMIT 1", (lang,)).fetchone()
        if r: print(f"  [{lang}] {r[0][:90]}")

    # both languages queryable in the SAME store, same query shape
    print(f"\n=== SAME QUERY SHAPE, EITHER LANGUAGE (blast radius) ===")
    for lang in ("go", "ts"):
        top = con.execute("""
            SELECT symbol, COUNT(*) c FROM occ
            WHERE lang=? AND is_def=0 GROUP BY symbol ORDER BY c DESC LIMIT 1
        """, (lang,)).fetchone()
        if not top:
            print(f"  [{lang}] (no symbols)"); continue
        t0 = time.time()
        n = con.execute("SELECT COUNT(*) FROM occ WHERE symbol=? AND is_def=0", (top[0],)).fetchone()[0]
        ms = (time.time()-t0)*1000
        print(f"  [{lang}] {name_of(top[0]):30s} -> {n} refs in {ms:.2f} ms")

    # cross-language: are there ANY edges spanning go<->ts? (expected: none — the honest boundary)
    x = con.execute("""
        SELECT COUNT(*) FROM edges e
        JOIN occ s ON s.symbol=e.src JOIN occ d ON d.symbol=e.dst
        WHERE s.lang != d.lang
    """).fetchone()[0]
    print(f"\n=== CROSS-LANGUAGE symbol edges: {x} (expected ~0 — SCIP can't see across the wire) ===")
    con.close()

if __name__ == "__main__":
    main()
