#!/usr/bin/env python3
"""Codeflair spike: ingest a SCIP index -> SQLite, then prove blast-radius queries.

Usage:  ./scip print --json index.scip | python3 ingest.py [seed_name_substring]

Proves the thesis on a real codebase:
  - ingest occurrences (symbol/file/line/role) into SQLite
  - 1-hop blast radius: who references symbol S (direct from occ table)
  - N-hop blast radius: recursive CTE over caller->callee edges
    (caller = the nearest preceding definition in the same file; a spike heuristic)
"""
import sys, json, sqlite3, time, os

DB = "codeflair.db"
DEF = 0x1  # symbol_roles bit: Definition

def parse_and_load(con):
    t0 = time.time()
    data = json.load(sys.stdin)               # whole index as JSON (tens of MB — fine)
    docs = data["documents"]
    occ = []                                  # (symbol, path, line, is_def)
    for d in docs:
        path = d.get("relative_path", "")
        for o in d.get("occurrences", []):
            rng = o.get("range", [])
            if not rng:
                continue
            line = rng[0]
            sym = o.get("symbol", "")
            if not sym or sym.startswith("local "):
                continue
            is_def = 1 if (o.get("symbol_roles", 0) & DEF) else 0
            occ.append((sym, path, line, is_def))
    con.executemany("INSERT INTO occ(symbol,path,line,is_def) VALUES (?,?,?,?)", occ)
    con.commit()
    return len(docs), len(occ), time.time() - t0

def build_edges(con):
    """caller->callee edge: for each reference, the nearest preceding def in the same file."""
    t0 = time.time()
    # defs per file, sorted by line
    defs = {}
    for sym, path, line in con.execute("SELECT symbol,path,line FROM occ WHERE is_def=1"):
        defs.setdefault(path, []).append((line, sym))
    for p in defs:
        defs[p].sort()
    import bisect
    edges = []
    for sym, path, line in con.execute("SELECT symbol,path,line FROM occ WHERE is_def=0"):
        arr = defs.get(path)
        if not arr:
            continue
        i = bisect.bisect_right(arr, (line, "￿")) - 1   # nearest preceding def
        if i >= 0:
            caller = arr[i][1]
            if caller != sym:
                edges.append((caller, sym))
    con.executemany("INSERT INTO edges(src,dst) VALUES (?,?)", edges)
    con.commit()
    return len(edges), time.time() - t0

def name_of(sym):
    """last descriptor of a SCIP symbol string, for human display."""
    return sym.split(" ")[-1].split("/")[-1] or sym

def main():
    seed = sys.argv[1] if len(sys.argv) > 1 else None
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE occ(symbol TEXT, path TEXT, line INT, is_def INT)")
    con.execute("CREATE TABLE edges(src TEXT, dst TEXT)")

    ndocs, nocc, t_load = parse_and_load(con)
    con.execute("CREATE INDEX i_sym ON occ(symbol)")
    con.execute("CREATE INDEX i_def ON occ(is_def, symbol)")
    nedges, t_edges = build_edges(con)
    con.execute("CREATE INDEX i_src ON edges(src)")
    con.execute("CREATE INDEX i_dst ON edges(dst)")
    con.commit()
    dbsize = os.path.getsize(DB) / 1e6

    print(f"\n=== INGEST ===")
    print(f"documents      : {ndocs:,}")
    print(f"occurrences    : {nocc:,}   (load {t_load:.1f}s)")
    print(f"caller->callee : {nedges:,} edges   (build {t_edges:.1f}s)")
    print(f"sqlite size    : {dbsize:.1f} MB")

    # pick a seed: highest-referenced TRUSTLESS-owned symbol (or the CLI arg)
    if seed:
        row = con.execute(
            "SELECT symbol FROM occ WHERE is_def=1 AND symbol LIKE ? LIMIT 1", (f"%{seed}%",)
        ).fetchone()
        target = row[0] if row else None
    else:
        target = con.execute("""
            SELECT o.symbol FROM occ o
            JOIN occ d ON d.symbol=o.symbol AND d.is_def=1
            WHERE o.is_def=0 AND o.symbol LIKE '%trustless%' AND o.symbol LIKE '%().'
            GROUP BY o.symbol ORDER BY COUNT(*) DESC LIMIT 1
        """).fetchone()
        target = target[0] if target else None
    if not target:
        print("no seed symbol found"); return

    print(f"\n=== SEED ===\n{name_of(target)}\n  {target}")

    # 1-hop blast radius
    t0 = time.time()
    refs = con.execute(
        "SELECT path, line FROM occ WHERE symbol=? AND is_def=0 ORDER BY path, line", (target,)
    ).fetchall()
    t1 = (time.time() - t0) * 1000
    print(f"\n=== 1-HOP (direct references) : {len(refs)} refs in {t1:.1f} ms ===")
    for p, l in refs[:8]:
        print(f"  {p}:{l}")
    if len(refs) > 8:
        print(f"  … +{len(refs)-8} more")

    # N-hop blast radius via recursive CTE
    t0 = time.time()
    rows = con.execute("""
        WITH RECURSIVE blast(sym, hop) AS (
            SELECT ?, 0
            UNION
            SELECT e.src, blast.hop+1
            FROM edges e JOIN blast ON e.dst = blast.sym
            WHERE blast.hop < 3
        )
        SELECT sym, MIN(hop) FROM blast GROUP BY sym
    """, (target,)).fetchall()
    t2 = (time.time() - t0) * 1000
    print(f"\n=== N-HOP (recursive CTE, ≤3 hops) : {len(rows)} symbols in {t2:.1f} ms ===")
    for sym, hop in sorted(rows, key=lambda r: r[1])[:12]:
        if sym != target:
            print(f"  hop {hop}: {name_of(sym)}")
    con.close()

if __name__ == "__main__":
    main()
