#!/usr/bin/env python3
"""CP Softball weekly stats digest.

Prints every number needed to hand-author the site's HTML pages.
Stdlib only. See CLAUDE.md for the weekly update procedure.

Usage:
  python3 analysis.py 0703-stats.csv
  python3 analysis.py 0703-stats.csv --prev 0612-stats.csv

With --prev, three digests print: the current snapshot, the previous
snapshot (with names canonicalized from the current file), and the
week-over-week comparison. All averages are the adjusted average
(hits - caused_outs) / at_bats, recomputed from raw counts and checked
against the file's own average column to catch format drift.
"""
import argparse
import csv
import math
import statistics
import sys

ROUNDS = 12

# ---------------------------------------------------------------- loading

NEW_COLS = {"player", "team", "draft_pick", "at_bats", "hits", "caused_outs", "adjusted_avg"}
OLD_COLS = {"Name", "Pick#", "AVG", "AB", "H", "CO", "Team"}


def load(path):
    """Load either CSV schema into a list of normalized player dicts."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit(f"{path}: no data rows")
    cols = set(rows[0])
    players = []
    if NEW_COLS <= cols:
        fmt = "new"
        for r in rows:
            players.append(dict(
                name=r["player"].strip(), team=r["team"].strip(),
                pick=int(r["draft_pick"]), ab=int(r["at_bats"]),
                h=int(r["hits"]), co=int(r["caused_outs"]),
                file_avg=float(r["adjusted_avg"]),
                file_rank=int(r["rank"]) if "rank" in cols else None))
    elif OLD_COLS <= cols:
        fmt = "old"
        for r in rows:
            players.append(dict(
                name=r["Name"].strip(), team=r["Team"].strip(),
                pick=int(r["Pick#"]), ab=int(r["AB"]),
                h=int(r["H"]), co=int(r["CO"]),
                file_avg=float(r["AVG"]), file_rank=None))
    else:
        sys.exit(f"{path}: unrecognized columns {sorted(cols)} — new schema? Update analysis.py.")

    for p in players:
        p["avg"] = (p["h"] - p["co"]) / p["ab"] if p["ab"] else 0.0
        if p["ab"] and abs(p["avg"] - p["file_avg"]) > 0.0015:
            sys.exit(f"{path}: {p['name']}: file avg {p['file_avg']:.3f} != "
                     f"(H-CO)/AB = {p['avg']:.3f} — formula drift, investigate before publishing")

    keys = [(p["team"], p["pick"]) for p in players]
    dups = sorted({k for k in keys if keys.count(k) > 1})
    if dups:
        sys.exit(f"{path}: duplicate (team, pick) keys: {dups}")

    # rank: use the file's rank column when present, else compute
    ranked = sorted(players, key=lambda p: (-p["avg"], -p["ab"], p["name"]))
    for i, p in enumerate(ranked, 1):
        p["rank"] = p["file_rank"] or i
    return players, fmt


def canonicalize_prev_names(prev, cur):
    """Give old-format rows "Surname, Given" names using the joined current row.

    The given name comes from the current file; the surname is recovered from
    the OLD file's own string so a player renamed between snapshots (e.g.
    Williams -> Musser Moroni) keeps the surname that was true on that date.
    Returns a list of (old_name, new_name, team, pick) renames detected.
    """
    cur_by_key = {(p["team"], p["pick"]): p for p in cur}
    renames = []
    for p in prev:
        c = cur_by_key.get((p["team"], p["pick"]))
        if c is None or "," in p["name"]:
            continue
        surname_now, _, given = c["name"].partition(",")
        given = given.strip()
        old = p["name"]
        if old.endswith(" " + given):
            surname_then = old[: -len(given) - 1].strip()
        else:  # given name itself changed; trust the current split
            surname_then = surname_now.strip()
        p["name"] = f"{surname_then}, {given}"
        if surname_then != surname_now.strip():
            renames.append((p["name"], c["name"], p["team"], p["pick"]))
    return renames


# ---------------------------------------------------------------- helpers

def A(v):
    """Format an average the way the pages print it: .726 / 1.000."""
    s = f"{v:.3f}"
    return s[1:] if s.startswith("0") else s


def Z(v):
    return f"{v:+.2f}".replace("-", "−")  # minus sign, like the pages


def surname(p):
    return p["name"].split(",")[0].strip()


def given(p):
    return p["name"].split(",")[1].strip() if "," in p["name"] else p["name"]


def add_z(players):
    """z within draft round, over players with AB > 0. DNP players get z = 0."""
    for rd in range(1, ROUNDS + 1):
        live = [p for p in players if p["pick"] == rd and p["ab"] > 0]
        m = statistics.mean(p["avg"] for p in live)
        s = statistics.stdev(p["avg"] for p in live)
        for p in players:
            if p["pick"] == rd:
                p["z"] = (p["avg"] - m) / s if p["ab"] else 0.0


# ---------------------------------------------------------------- digest

def digest(players, label, min_ab_sleeper, min_ab_outlier):
    P = [p for p in players if p["ab"] > 0]
    n_dnp = len(players) - len(P)
    teams = sorted({p["team"] for p in players})
    tot_ab = sum(p["ab"] for p in players)
    tot_h = sum(p["h"] for p in players)
    tot_co = sum(p["co"] for p in players)
    league_adj = (tot_h - tot_co) / tot_ab
    league_raw = tot_h / tot_ab
    avgs = [p["avg"] for p in P]
    med_player = statistics.median(avgs)
    add_z(players)

    print(f"\n{'=' * 72}\n=== SNAPSHOT DIGEST: {label} ===\n{'=' * 72}")
    print(f"players {len(players)} | teams {len(teams)} | AB {tot_ab:,} | H {tot_h:,} | CO {tot_co}")
    print(f"league raw avg {A(league_raw)} | league adj avg {A(league_adj)}")
    print(f"player avgs (AB>0, n={len(P)}): mean {A(statistics.mean(avgs))} | median {A(med_player)}")
    print(f"zero caused outs {sum(1 for p in players if p['co'] == 0)}/{len(players)} | "
          f"zero AB {n_dnp} | players at/above .500 {sum(1 for a in avgs if a >= 0.5)}/{len(P)}")

    # pick <-> avg correlation (AB>0)
    xs = [p["pick"] for p in P]
    mx, my = statistics.mean(xs), statistics.mean(avgs)
    r = (sum((x - mx) * (y - my) for x, y in zip(xs, avgs))
         / math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in avgs)))
    print(f"pick vs avg correlation r = {r:+.2f}")

    # ---- rounds table (with re-draft: rank order chunked into rounds of 12)
    redraft = {}
    for i, p in enumerate(sorted(players, key=lambda q: (-q["avg"], -q["ab"], q["name"]))):
        redraft[id(p)] = i // ROUNDS + 1
    print(f"\n--- ROUNDS (mean/median/min/max/sigma over AB>0; meter width = mean*100) ---")
    print("rd |  n | mean  med   min   max  sigma | mAB  | CO CO/100 | >=.500 <med | redraft keep")
    for rd in range(1, ROUNDS + 1):
        ps = [p for p in players if p["pick"] == rd]
        live = [p for p in ps if p["ab"] > 0]
        a = [p["avg"] for p in live]
        rab = sum(p["ab"] for p in ps)
        rco = sum(p["co"] for p in ps)
        rr = [redraft[id(p)] for p in ps]
        keep = sum(1 for p in ps if redraft[id(p)] <= rd)
        print(f"{rd:2d} | {len(live):2d} | {A(statistics.mean(a))} {A(statistics.median(a))} "
              f"{A(min(a))} {A(max(a))} {A(statistics.stdev(a))} | {sum(p['ab'] for p in live)/len(live):4.1f} "
              f"| {rco:2d} {100*rco/rab:5.1f} | {sum(1 for x in a if x >= .5):2d}/12  {sum(1 for x in a if x < med_player):2d}/12 "
              f"| {statistics.mean(rr):4.1f}  {keep:2d}/12")

    # ---- sleepers
    print(f"\n--- SLEEPERS (round >= 6, AB >= {min_ab_sleeper}, sorted by avg) ---")
    sl = sorted((p for p in P if p["pick"] >= 6 and p["ab"] >= min_ab_sleeper and p["avg"] >= med_player),
                key=lambda p: (-p["avg"], -p["ab"]))
    for p in sl:
        print(f"  {p['name']:30s} {p['team']:30s} rd{p['pick']:2d} {A(p['avg'])} on {p['ab']:2d} AB  "
              f"rank #{p['rank']:<3d} z {Z(p['z'])}")

    # ---- outliers per round
    print(f"\n--- OUTLIERS PER ROUND (AB >= {min_ab_outlier}; round mean in parens) ---")
    for rd in range(1, ROUNDS + 1):
        live = [p for p in P if p["pick"] == rd and p["ab"] >= min_ab_outlier]
        rm = statistics.mean([p["avg"] for p in P if p["pick"] == rd])
        hi = max(live, key=lambda p: p["z"])
        lo = min(live, key=lambda p: p["z"])
        print(f"{rd:2d} ({A(rm)})  UP {hi['name']:28s} {A(hi['avg'])} z {Z(hi['z'])}   "
              f"DOWN {lo['name']:28s} {A(lo['avg'])} z {Z(lo['z'])}")

    # ---- teams
    print("\n--- TEAMS (sorted by adj avg; sigma over player avgs AB>0) ---")
    trows = []
    for t in teams:
        ps = [p for p in players if p["team"] == t]
        live = [p for p in ps if p["ab"] > 0]
        ab = sum(p["ab"] for p in ps); h = sum(p["h"] for p in ps); co = sum(p["co"] for p in ps)
        best = max(live, key=lambda p: (p["avg"], p["ab"]))
        trows.append(dict(team=t, adj=(h - co) / ab, raw=h / ab, co=co, ab=ab,
                          club=sum(1 for p in live if p["avg"] >= .5), n=len(ps),
                          sigma=statistics.stdev([p["avg"] for p in live]), best=best,
                          z=sum(p["z"] for p in ps),
                          z_early=sum(p["z"] for p in ps if p["pick"] <= 6),
                          z_late=sum(p["z"] for p in ps if p["pick"] > 6)))
    for i, t in enumerate(sorted(trows, key=lambda x: -x["adj"]), 1):
        print(f"{i:2d} {t['team']:32s} adj {A(t['adj'])} raw {A(t['raw'])} CO {t['co']:2d} "
              f"AB {t['ab']:3d} club {t['club']:2d}/{t['n']} sig {A(t['sigma'])} "
              f"best {t['best']['name']} ({A(t['best']['avg'])})")

    # ---- report card
    zmax = max(abs(t["z"]) for t in trows)
    scale = max(6, math.ceil(zmax))
    print(f"\n--- REPORT CARD (total z; bar width % = |z|/{scale}*50, scale ±{scale}) ---")
    for t in sorted(trows, key=lambda x: -x["z"]):
        print(f"  {t['team']:32s} {Z(t['z'])}  width {abs(t['z'])/scale*50:.1f}%   "
              f"early(1-6) {Z(t['z_early'])}  late(7-12) {Z(t['z_late'])}")

    # ---- dynasty ledger (single-word surnames, >= 3 players)
    fams = {}
    for p in players:
        s = surname(p)
        if " " not in s:
            fams.setdefault(s, []).append(p)
    fams = {s: ps for s, ps in fams.items() if len(ps) >= 3}
    covered = sum(len(ps) for ps in fams.values())
    print(f"\n--- DYNASTY LEDGER ({len(fams)} families cover {covered}/{len(players)}; avg = mean of player avgs) ---")
    for s, ps in sorted(fams.items(), key=lambda kv: -len(kv[1])):
        live = [p for p in ps if p["ab"] > 0]
        best = max(live, key=lambda p: (p["avg"], p["ab"]))
        print(f"  {s:12s} n {len(ps):2d}  teams {len({p['team'] for p in ps})}  "
              f"best {given(best)} ({A(best['avg'])})  famavg {A(statistics.mean(p['avg'] for p in live))}")

    # ---- distribution
    print("\n--- DISTRIBUTION of adj avg (AB>0; .100 buckets; meter width = n/max*100) ---")
    buckets = [0] * 10
    for a in avgs:
        buckets[min(int(a * 10), 9)] += 1
    mx = max(buckets)
    for i, n in enumerate(buckets):
        print(f"  .{i}00-.{i}99: {n:3d}  width {100*n/mx:5.1f}%")
    below5 = sum(1 for a in avgs if a < .5)
    print(f"  .500 sits at the {100*below5/len(avgs):.0f}th percentile ({below5}/{len(avgs)} below)")

    # ---- leaderboards
    print("\n--- WORKLOAD (top 8 AB) ---")
    for p in sorted(P, key=lambda p: -p["ab"])[:8]:
        print(f"  {p['name']:30s} {p['ab']:2d} AB at {A(p['avg'])}  ({p['team']})")
    print("--- CAUSED OUTS (all CO >= 2) ---")
    for p in sorted((p for p in players if p["co"] >= 2), key=lambda p: (-p["co"], -p["ab"])):
        print(f"  {p['name']:30s} CO {p['co']}  on {p['ab']:2d} AB, avg {A(p['avg'])}  ({p['team']})")
    return players


# ---------------------------------------------------------------- compare

def compare(prev, cur, renames, min_old_ab=8, min_new_ab=15, min_dab=10):
    po = {(p["team"], p["pick"]): p for p in prev}
    pn = {(p["team"], p["pick"]): p for p in cur}
    if set(po) != set(pn):
        sys.exit(f"join failure: only-prev {set(po)-set(pn)} only-cur {set(pn)-set(po)}")
    print(f"\n{'=' * 72}\n=== COMPARISON: prev -> current ===\n{'=' * 72}")
    print(f"join OK: {len(po)}/{len(pn)} matched on (team, pick)")
    for old, new, team, pick in renames:
        print(f"RENAME: '{old}' -> '{new}' ({team}, pick {pick}) — same player, name corrected")

    rows = []
    for k, o in po.items():
        n = pn[k]
        dab, dh, dco = n["ab"] - o["ab"], n["h"] - o["h"], n["co"] - o["co"]
        if dab < 0:
            print(f"WARNING: {n['name']} AB decreased {o['ab']} -> {n['ab']} (data revision?)")
        rows.append(dict(name=n["name"], team=k[0], pick=k[1], o=o, n=n, dab=dab,
                         d=n["avg"] - o["avg"],
                         prate=(dh - dco) / dab if dab > 0 else None))

    oab = sum(r["o"]["ab"] for r in rows); nab = sum(r["n"]["ab"] for r in rows)
    onet = sum(r["o"]["h"] - r["o"]["co"] for r in rows); nnet = sum(r["n"]["h"] - r["n"]["co"] for r in rows)
    print(f"\nleague AB {oab:,} -> {nab:,} (+{nab-oab:,}) | adj avg {A(onet/oab)} -> {A(nnet/nab)}"
          f" | period rate {A((nnet-onet)/(nab-oab))}")

    q = [r for r in rows if r["o"]["ab"] >= min_old_ab and r["n"]["ab"] >= min_new_ab]
    q.sort(key=lambda r: -r["d"])
    print(f"\n--- SEASON-AVG MOVERS (AB >= {min_old_ab} then and >= {min_new_ab} now; top 10 each) ---")
    for r in q[:10]:
        print(f"  UP   {r['name']:30s} {A(r['o']['avg'])} -> {A(r['n']['avg'])} ({r['d']:+.3f})  "
              f"AB {r['o']['ab']}->{r['n']['ab']}  ({r['team']}, rd{r['pick']})")
    for r in q[:-11:-1]:
        print(f"  DOWN {r['name']:30s} {A(r['o']['avg'])} -> {A(r['n']['avg'])} ({r['d']:+.3f})  "
              f"AB {r['o']['ab']}->{r['n']['ab']}  ({r['team']}, rd{r['pick']})")

    pq = sorted((r for r in rows if r["dab"] >= min_dab), key=lambda r: -r["prate"])
    print(f"\n--- PERIOD BATS ((dH-dCO)/dAB, dAB >= {min_dab}; {len(pq)} qualify; top 10 each) ---")
    for r in pq[:10]:
        print(f"  HOT  {r['name']:30s} {A(r['prate'])} on {r['dab']:2d} period AB  "
              f"season {A(r['o']['avg'])} -> {A(r['n']['avg'])}  ({r['team']})")
    for r in pq[:-11:-1]:
        print(f"  COLD {r['name']:30s} {A(r['prate'])} on {r['dab']:2d} period AB  "
              f"season {A(r['o']['avg'])} -> {A(r['n']['avg'])}  ({r['team']})")

    deb = [r for r in rows if r["o"]["ab"] == 0 and r["n"]["ab"] > 0]
    print(f"\n--- DEBUTS ({len(deb)} first appeared this period) ---")
    for r in sorted(deb, key=lambda r: -r["n"]["avg"]):
        print(f"  {r['name']:30s} {A(r['n']['avg'])} on {r['n']['ab']:2d} AB  ({r['team']}, rd{r['pick']})")

    print("\n--- PLAYING-TIME SURGES (top 8 dAB) ---")
    for r in sorted(rows, key=lambda r: -r["dab"])[:8]:
        print(f"  {r['name']:30s} +{r['dab']} AB ({r['o']['ab']} -> {r['n']['ab']})  "
              f"period {A(r['prate'])}  ({r['team']})")

    print("\n--- TEAM SHIFTS (delta adj avg; bar width % = |delta|/0.125*50) ---")
    tt = {}
    for r in rows:
        a = tt.setdefault(r["team"], [0, 0, 0, 0])
        a[0] += r["o"]["h"] - r["o"]["co"]; a[1] += r["o"]["ab"]
        a[2] += r["n"]["h"] - r["n"]["co"]; a[3] += r["n"]["ab"]
    for t, (on, oa, nn_, na) in sorted(tt.items(), key=lambda kv: -(kv[1][2]/kv[1][3] - kv[1][0]/kv[1][1])):
        d = nn_/na - on/oa
        print(f"  {t:32s} {A(on/oa)} -> {A(nn_/na)}  ({d:+.3f})  width {abs(d)/0.125*50:.1f}%  "
              f"period {A((nn_-on)/(na-oa))}")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("snapshot")
    ap.add_argument("--prev", help="older snapshot CSV for week-over-week comparison")
    ap.add_argument("--min-ab-sleeper", type=int, default=15)
    ap.add_argument("--min-ab-outlier", type=int, default=10)
    ap.add_argument("--prev-min-ab-sleeper", type=int, default=10)
    ap.add_argument("--prev-min-ab-outlier", type=int, default=6)
    args = ap.parse_args()

    cur, _ = load(args.snapshot)
    digest(cur, args.snapshot, args.min_ab_sleeper, args.min_ab_outlier)
    if args.prev:
        prev, fmt = load(args.prev)
        renames = canonicalize_prev_names(prev, cur) if fmt == "old" else []
        digest(prev, f"{args.prev} (prev)", args.prev_min_ab_sleeper, args.prev_min_ab_outlier)
        compare(prev, cur, renames)


if __name__ == "__main__":
    main()
