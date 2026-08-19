#!/usr/bin/env python3
"""CP Softball weekly stats digest.

Prints every number needed to hand-author the site's HTML pages.
Stdlib only. See CLAUDE.md for the weekly update procedure.

Usage:
  python3 analysis.py 0703-stats.csv
  python3 analysis.py 0703-stats.csv --prev 0612-stats.csv
  python3 analysis.py 0710-stats.csv --prev 0703-stats.csv --prev2 0612-stats.csv

With --prev, three digests print: the current snapshot, the previous
snapshot (with names canonicalized from the current file), and the
week-over-week comparison. With --prev2 (the snapshot before --prev),
a two-week ARCS digest also prints: players/teams trending the same
direction across both periods, and the batting-race history. All
averages are the adjusted average (hits - caused_outs) / at_bats,
recomputed from raw counts and checked against the file's own average
column to catch format drift.
"""

import argparse
import bisect
import csv
import dataclasses
import datetime
import difflib
import itertools
import json
import math
import re
import statistics
import sys

ROUNDS = 12
SEASON_YEAR = 2026  # MMDD snapshot filenames carry no year; the season does

# Team captains, from https://cpsoftball.com/teams.php (fetched 2026-07-06).
# Every displayed team name carries "(<captain>'s team)". The two captains
# named Daniel are disambiguated patronymic-style, matching league usage.
CAPTAINS = {
    "The Good Guys": "Gideon",
    "Youre Saying Theres A Chance": "Horatio",
    "The Lefty Looseys": "Sefton",
    "The Ellites": "Elliot",
    "The Pliggas": "Claude",
    "The Playas": "Michael",
    "The Stars and Strikes": "Seth",
    "The Danites": "Ephraims Daniel",
    "The Pure Breads": "Caleb",
    "The Slamma Jammas": "Boyds Daniel",
    "The Fellowship of the Swing": "Stafford",
    "The Diamonds and Dirtbags": "Jeremy",
}

# ---------------------------------------------------------------- loading

NEW_COLS = {
    "player",
    "team",
    "draft_pick",
    "at_bats",
    "hits",
    "caused_outs",
    "adjusted_avg",
}
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
            players.append(
                dict(
                    name=r["player"].strip(),
                    team=r["team"].strip(),
                    pick=int(r["draft_pick"]),
                    ab=int(r["at_bats"]),
                    h=int(r["hits"]),
                    co=int(r["caused_outs"]),
                    file_avg=float(r["adjusted_avg"]),
                    file_rank=int(r["rank"]) if "rank" in cols else None,
                )
            )
    elif OLD_COLS <= cols:
        fmt = "old"
        for r in rows:
            players.append(
                dict(
                    name=r["Name"].strip(),
                    team=r["Team"].strip(),
                    pick=int(r["Pick#"]),
                    ab=int(r["AB"]),
                    h=int(r["H"]),
                    co=int(r["CO"]),
                    file_avg=float(r["AVG"]),
                    file_rank=None,
                )
            )
    else:
        sys.exit(
            f"{path}: unrecognized columns {sorted(cols)} — new schema? Update analysis.py."
        )

    for p in players:
        p["avg"] = (p["h"] - p["co"]) / p["ab"] if p["ab"] else 0.0
        if p["ab"] and abs(p["avg"] - p["file_avg"]) > 0.0015:
            sys.exit(
                f"{path}: {p['name']}: file avg {p['file_avg']:.3f} != "
                f"(H-CO)/AB = {p['avg']:.3f} — formula drift, investigate before publishing"
            )

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


# Draft order (per Curtis, 2026-07-06): captains drafted in this team order,
# SNAKED — odd rounds run 1->12, even rounds 12->1. So overall pick number =
# (round-1)*12 + position in odd rounds, (round-1)*12 + (13-position) in even.
# Verified anchors: Gideon Hammon = pick #1 (picked himself), Jairus Hammon =
# #24, Sean Hammon = #140 (5th-to-last), Becky Wood = #144 (last pick).
DRAFT_ORDER = [
    "The Good Guys",  # 1  Gideon Hammon
    "Youre Saying Theres A Chance",  # 2  Horatio Williams
    "The Lefty Looseys",  # 3  Sefton Dockstader
    "The Ellites",  # 4  Elliot Hammon
    "The Pliggas",  # 5  Claude Timpson
    "The Playas",  # 6  Michael Williams
    "The Stars and Strikes",  # 7  Seth Cawley
    "The Danites",  # 8  Daniel Dockstader Ephraims
    "The Pure Breads",  # 9  Caleb Barlow
    "The Slamma Jammas",  # 10 Daniel Dockstader Boyds
    "The Fellowship of the Swing",  # 11 Stafford Hammon
    "The Diamonds and Dirtbags",  # 12 Jeremy Dockstader Marvins
]

# Each captain as a roster player (team -> player name), for the Captain's Mirror.
CAPTAIN_PLAYER = {
    "The Good Guys": "Hammon, Gideon",
    "Youre Saying Theres A Chance": "Williams, Horatio",
    "The Lefty Looseys": "Dockstader, Sefton",
    "The Ellites": "Hammon, Elliot",
    "The Pliggas": "Timpson, Claude",
    "The Playas": "Williams, Michael",
    "The Stars and Strikes": "Cawley, Seth",
    "The Danites": "Dockstader Ephraims, Daniel",
    "The Pure Breads": "Barlow, Caleb",
    "The Slamma Jammas": "Dockstader Boyds, Daniel",
    "The Fellowship of the Swing": "Hammon, Stafford",
    "The Diamonds and Dirtbags": "Dockstader Marvins, Jeremy",
}


def add_picks(players):
    """Set p['pickno'] = overall draft pick number 1..144 from the snake order."""
    for p in players:
        pos = DRAFT_ORDER.index(p["team"]) + 1
        r = p["pick"]
        p["pickno"] = (r - 1) * ROUNDS + (pos if r % 2 else ROUNDS + 1 - pos)
    nos = sorted(p["pickno"] for p in players)
    assert nos == list(range(1, len(players) + 1)), "pick numbers not a clean 1..N"


# Standing nicknames for the Round Rooms — editorial lore, each grounded in a
# season-long stat (R1 tightest spread, R3 most overpriced, R6 the bump, R8 the
# widest sigma, R9 the sloppiest CO rate, R10 the dip below R11, R11 the odd
# overachiever directly above R12, the floor). Keep stable across editions.
ROUND_NICKNAMES = {
    1: "The Penthouse",
    2: "The Second Story",
    3: "The Money Pit",
    4: "The Suburbs",
    5: "The Flats",
    6: "The Bump",
    7: "The Mezzanine",
    8: "The Casino",
    9: "The Spill Zone",
    10: "The Pothole",
    11: "The Attic",
    12: "The Floor",
}


# Shortstops — one per team, per Curtis (2026-07-06). Shortstop is the league's
# premium defensive position: 11 of the 12 are round-1 picks, and a shortstop's
# draft price buys a glove the batting ledger can't see. Temper "overdrafted"
# verdicts for these names. (Updated 2026-07-13: Stafford Hammon no longer plays
# SS; Adam Dockstader, the Fellowship's R1 pick, is their shortstop now.)
SHORTSTOPS = {
    "Hammon, Gideon",  # Good Guys
    "Williams, Horatio",  # Youre Saying Theres A Chance
    "Dockstader, Sefton",  # Lefty Looseys
    "Hammon, Elliot",  # Ellites
    "Timpson, Claude",  # Pliggas
    "Williams, Michael",  # Playas
    "Guy, Sam",  # Stars and Strikes
    "Dockstader Ephraims, Daniel",  # Danites (R4)
    "Williams, Daniel",  # Pure Breads
    "Knudson, Levi",  # Slamma Jammas
    "Dockstader, Adam",  # Fellowship of the Swing
    "Dockstader Boyds, Jeremy",  # Diamonds and Dirtbags
}


def is_ss(p):
    return p["name"] in SHORTSTOPS


# Coed rule (per Curtis, 2026-07-06): every roster must carry two women — the
# Dream Team included. Gender is deduced from given names. Ambiguous names are
# treated as male unless confirmed; Taylor (Timpson) and Riley (Barlow) are
# confirmed male. If Avery, Kendall, Sidney, Leslie, or J Daunt ever matter for
# the rule, ask Curtis rather than guessing.
FEMALE_GIVEN = {
    "Maureen",
    "Jayla",
    "Tammy",
    "Marissa",
    "Violet",
    "Lexi",
    "Sophia",
    "Dorothy",
    "Isabel",
    "Alyssa",
    "Selena",
    "Kaitlyn",
    "Sarah",
    "Lindsey",
    "Layla",
    "Karen",
    "Lizzy",
    "Heather",
    "Sharon",
    "Pauline",
    "Becky",
    "Samantha",
    "Deborah",
    "Angeline",
    "Brenda",
    "Rebecca",
    "Sabrina",
    "Jazlin",
    "Amie Z",
    "Joanne Sis",
}


def is_female(p):
    return given(p) in FEMALE_GIVEN


# The coed rule only ever needed to know who IS a woman, so `is_female` treats
# every other name as male. That is fine for a roster gate and wrong for a
# board that prints a gender: six given names in this league have never been
# confirmed either way (Sidney and Leslie sit off the Divide's honour roll on
# the owner's explicit call, 2026-08-12; the rest are on the never-guess list),
# and the desk will not deal them into a men's table to round the numbers out.
# They are excluded from both sides and the count is disclosed wherever the
# split prints. Ask Curtis; never guess a gender into print.
UNCONFIRMED_GIVEN = {
    "Avery",
    "Kendall",
    "Sidney",
    "Leslie",
    "J Daunt",
    "Emmerson",
}


def is_unconfirmed(p):
    return given(p) in UNCONFIRMED_GIVEN


def is_male(p):
    """A CONFIRMED man — not in FEMALE_GIVEN and not on the never-guess list."""
    return not is_female(p) and not is_unconfirmed(p)


def dream_team(players):
    """Best value per round, then enforce the coed rule (>= 2 women).

    If the pure-value team has fewer than two women, swap in the best-value
    woman from whichever rounds cost the least total value. Returns
    (round -> player, set of swapped rounds).
    """
    team = {
        rd: max((p for p in players if p["pick"] == rd), key=lambda p: p["value"])
        for rd in range(1, ROUNDS + 1)
    }
    swapped = set()
    need = 2 - sum(1 for p in team.values() if is_female(p))
    options = []
    for rd in range(1, ROUNDS + 1):
        if is_female(team[rd]):
            continue
        fs = [p for p in players if p["pick"] == rd and is_female(p)]
        if fs:
            best = max(fs, key=lambda p: (p["value"], p["avg"], p["ab"]))
            options.append((team[rd]["value"] - best["value"], rd, best))
    for _, rd, f in sorted(options, key=lambda o: (o[0], o[1]))[: max(0, need)]:
        team[rd] = f
        swapped.add(rd)
    return team, swapped


def add_value(players):
    """Value = net hits above a league-average bat: (avg - league_adj) * AB.

    Rewards volume: .750 over 30 AB (+5.6) beats .780 over 20 AB (+4.4).
    Also deals every player a "true round" (vround): rank all by value,
    12 per round. Returns the league adjusted average used.
    """
    tot_ab = sum(p["ab"] for p in players)
    lg = (sum(p["h"] for p in players) - sum(p["co"] for p in players)) / tot_ab
    for p in players:
        p["value"] = (p["avg"] - lg) * p["ab"]
    ranked = sorted(
        players, key=lambda p: (-p["value"], -p["avg"], -p["ab"], p["name"])
    )
    for i, p in enumerate(ranked):
        p["vround"] = i // ROUNDS + 1
    return lg


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
    print(
        f"players {len(players)} | teams {len(teams)} | AB {tot_ab:,} | H {tot_h:,} | CO {tot_co}"
    )
    print(f"league raw avg {A(league_raw)} | league adj avg {A(league_adj)}")
    print(
        f"player avgs (AB>0, n={len(P)}): mean {A(statistics.mean(avgs))} | median {A(med_player)}"
    )
    print(
        f"zero caused outs {sum(1 for p in players if p['co'] == 0)}/{len(players)} | "
        f"zero AB {n_dnp} | players at/above .500 {sum(1 for a in avgs if a >= 0.5)}/{len(P)}"
    )

    # pick <-> avg correlation (AB>0)
    xs = [p["pick"] for p in P]
    mx, my = statistics.mean(xs), statistics.mean(avgs)
    r = sum((x - mx) * (y - my) for x, y in zip(xs, avgs)) / math.sqrt(
        sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in avgs)
    )
    print(f"pick vs avg correlation r = {r:+.2f}")

    # ---- rounds table (with re-draft: rank order chunked into rounds of 12)
    redraft = {}
    for i, p in enumerate(
        sorted(players, key=lambda q: (-q["avg"], -q["ab"], q["name"]))
    ):
        redraft[id(p)] = i // ROUNDS + 1
    print(
        f"\n--- ROUNDS (mean/median/min/max/sigma over AB>0; meter width = mean*100) ---"
    )
    print(
        "rd |  n | mean  med   min   max  sigma | mAB  | CO CO/100 | >=.500 <med | redraft keep"
    )
    for rd in range(1, ROUNDS + 1):
        ps = [p for p in players if p["pick"] == rd]
        live = [p for p in ps if p["ab"] > 0]
        a = [p["avg"] for p in live]
        rab = sum(p["ab"] for p in ps)
        rco = sum(p["co"] for p in ps)
        rr = [redraft[id(p)] for p in ps]
        keep = sum(1 for p in ps if redraft[id(p)] <= rd)
        print(
            f"{rd:2d} | {len(live):2d} | {A(statistics.mean(a))} {A(statistics.median(a))} "
            f"{A(min(a))} {A(max(a))} {A(statistics.stdev(a))} | {sum(p['ab'] for p in live) / len(live):4.1f} "
            f"| {rco:2d} {100 * rco / rab:5.1f} | {sum(1 for x in a if x >= 0.5):2d}/12  {sum(1 for x in a if x < med_player):2d}/12 "
            f"| {statistics.mean(rr):4.1f}  {keep:2d}/12"
        )

    # ---- sleepers
    print(f"\n--- SLEEPERS (round >= 6, AB >= {min_ab_sleeper}, sorted by avg) ---")
    sl = sorted(
        (
            p
            for p in P
            if p["pick"] >= 6 and p["ab"] >= min_ab_sleeper and p["avg"] >= med_player
        ),
        key=lambda p: (-p["avg"], -p["ab"]),
    )
    for p in sl:
        print(
            f"  {p['name']:30s} {p['team']:30s} rd{p['pick']:2d} {A(p['avg'])} on {p['ab']:2d} AB  "
            f"rank #{p['rank']:<3d} z {Z(p['z'])}"
        )

    # ---- outliers per round
    print(
        f"\n--- OUTLIERS PER ROUND (AB >= {min_ab_outlier}; round mean in parens) ---"
    )
    for rd in range(1, ROUNDS + 1):
        live = [p for p in P if p["pick"] == rd and p["ab"] >= min_ab_outlier]
        rm = statistics.mean([p["avg"] for p in P if p["pick"] == rd])
        hi = max(live, key=lambda p: p["z"])
        lo = min(live, key=lambda p: p["z"])
        print(
            f"{rd:2d} ({A(rm)})  UP {hi['name']:28s} {A(hi['avg'])} z {Z(hi['z'])}   "
            f"DOWN {lo['name']:28s} {A(lo['avg'])} z {Z(lo['z'])}"
        )

    # ---- teams
    print("\n--- TEAMS (sorted by adj avg; sigma over player avgs AB>0) ---")
    trows = []
    for t in teams:
        ps = [p for p in players if p["team"] == t]
        live = [p for p in ps if p["ab"] > 0]
        ab = sum(p["ab"] for p in ps)
        h = sum(p["h"] for p in ps)
        co = sum(p["co"] for p in ps)
        best = max(live, key=lambda p: (p["avg"], p["ab"]))
        trows.append(
            dict(
                team=t,
                adj=(h - co) / ab,
                raw=h / ab,
                co=co,
                ab=ab,
                club=sum(1 for p in live if p["avg"] >= 0.5),
                n=len(ps),
                sigma=statistics.stdev([p["avg"] for p in live]),
                best=best,
                z=sum(p["z"] for p in ps),
                z_early=sum(p["z"] for p in ps if p["pick"] <= 6),
                z_late=sum(p["z"] for p in ps if p["pick"] > 6),
            )
        )
    for i, t in enumerate(sorted(trows, key=lambda x: -x["adj"]), 1):
        print(
            f"{i:2d} {t['team']:32s} adj {A(t['adj'])} raw {A(t['raw'])} CO {t['co']:2d} "
            f"AB {t['ab']:3d} club {t['club']:2d}/{t['n']} sig {A(t['sigma'])} "
            f"best {t['best']['name']} ({A(t['best']['avg'])})"
        )

    # ---- report card
    zmax = max(abs(t["z"]) for t in trows)
    scale = max(6, math.ceil(zmax))
    print(
        f"\n--- REPORT CARD (total z; bar width % = |z|/{scale}*50, scale ±{scale}) ---"
    )
    for t in sorted(trows, key=lambda x: -x["z"]):
        print(
            f"  {t['team']:32s} {Z(t['z'])}  width {abs(t['z']) / scale * 50:.1f}%   "
            f"early(1-6) {Z(t['z_early'])}  late(7-12) {Z(t['z_late'])}"
        )

    # ---- dynasty ledger (single-word surnames, >= 3 players)
    fams = {}
    for p in players:
        s = surname(p)
        if " " not in s:
            fams.setdefault(s, []).append(p)
    fams = {s: ps for s, ps in fams.items() if len(ps) >= 3}
    covered = sum(len(ps) for ps in fams.values())
    print(
        f"\n--- DYNASTY LEDGER ({len(fams)} families cover {covered}/{len(players)}; avg = mean of player avgs) ---"
    )
    def famavg(ps):
        return statistics.mean(p["avg"] for p in ps if p["ab"] > 0)

    for s, ps in sorted(fams.items(), key=lambda kv: -famavg(kv[1])):
        live = [p for p in ps if p["ab"] > 0]
        best = max(live, key=lambda p: (p["avg"], p["ab"]))
        print(
            f"  {s:12s} n {len(ps):2d}  teams {len({p['team'] for p in ps})}  "
            f"best {given(best)} ({A(best['avg'])})  famavg {A(statistics.mean(p['avg'] for p in live))}"
        )

    # ---- distribution
    print(
        "\n--- DISTRIBUTION of adj avg (AB>0; .100 buckets; meter width = n/max*100) ---"
    )
    buckets = [0] * 10
    for a in avgs:
        buckets[min(int(a * 10), 9)] += 1
    mx = max(buckets)
    for i, n in enumerate(buckets):
        print(f"  .{i}00-.{i}99: {n:3d}  width {100 * n / mx:5.1f}%")
    below5 = sum(1 for a in avgs if a < 0.5)
    print(
        f"  .500 sits at the {100 * below5 / len(avgs):.0f}th percentile ({below5}/{len(avgs)} below)"
    )

    # ---- leaderboards
    print("\n--- WORKLOAD (top 8 AB) ---")
    for p in sorted(P, key=lambda p: -p["ab"])[:8]:
        print(f"  {p['name']:30s} {p['ab']:2d} AB at {A(p['avg'])}  ({p['team']})")
    print("--- CAUSED OUTS (all CO >= 2) ---")
    for p in sorted(
        (p for p in players if p["co"] >= 2), key=lambda p: (-p["co"], -p["ab"])
    ):
        print(
            f"  {p['name']:30s} CO {p['co']}  on {p['ab']:2d} AB, avg {A(p['avg'])}  ({p['team']})"
        )
    clean = sorted((p for p in players if p["co"] == 0 and p["ab"] > 0),
                   key=lambda p: (-p["ab"], -p["avg"]))
    print(f"--- CLEAN HANDS (zero CO all season, {len(clean)} qualify; top 8 by AB) ---")
    for p in clean[:8]:
        print(f"  {p['name']:30s} {p['ab']:2d} AB, avg {A(p['avg'])}  ({p['team']})")

    # ---- batting race (top 3 by average, min 15 AB; hits back at own volume)
    racers = sorted((p for p in P if p["ab"] >= 15), key=lambda p: (-p["avg"], -p["ab"]))[:3]
    lead = racers[0]
    print("--- BATTING RACE (top 3 by avg, AB >= 15; back = (leader avg - avg) * own AB) ---")
    for i, p in enumerate(racers, 1):
        back = "  lead" if p is lead else f"  back {(lead['avg'] - p['avg']) * p['ab']:.1f} hits"
        print(f"  {i}. {p['name']:30s} {A(p['avg'])} on {p['ab']:2d} AB{back}  ({p['team']})")

    # ---- verdict: value, true rounds, justified picks
    lg = add_value(players)
    just = sum(1 for p in players if p["vround"] <= p["pick"])
    exact = [p for p in players if p["vround"] == p["pick"]]
    print(
        f"\n--- VERDICT (value = (avg - {A(lg)}) * AB = net hits above a league-average bat) ---"
    )
    print(
        f"justified (true round <= drafted round): {just}/{len(players)} | priced exactly right: {len(exact)}"
    )
    print("VALUE TOP 12:")
    for p in sorted(players, key=lambda p: -p["value"])[:12]:
        print(
            f"  {p['name']:30s} value {p['value']:+5.1f}  {A(p['avg'])} on {p['ab']:2d} AB  "
            f"drafted R{p['pick']:<2d} true R{p['vround']:<2d} {'SS' if is_ss(p) else ''}  ({p['team']})"
        )
    print("PRICED EXACTLY RIGHT (true round == drafted round):")
    for p in sorted(exact, key=lambda p: p["pick"]):
        print(
            f"  R{p['pick']:<2d} {p['name']:30s} {A(p['avg'])} on {p['ab']:2d} AB  value {p['value']:+5.1f} "
            f"{'SS' if is_ss(p) else ''}  ({p['team']})"
        )
    under = sorted(
        (p for p in players if p["pick"] > p["vround"]),
        key=lambda p: (-(p["pick"] - p["vround"]), -p["value"]),
    )
    over = sorted(
        (p for p in players if p["pick"] < p["vround"]),
        key=lambda p: (p["pick"] - p["vround"], p["value"]),
    )
    print("UNDERDRAFTED top 8 (went later than their stats deserve):")
    for p in under[:8]:
        print(
            f"  {p['name']:30s} drafted R{p['pick']:<2d} true R{p['vround']:<2d} (+{p['pick'] - p['vround']} rounds)  "
            f"{A(p['avg'])} on {p['ab']:2d} AB  value {p['value']:+5.1f} {'SS' if is_ss(p) else ''}  ({p['team']})"
        )
    print("OVERDRAFTED top 8 (stats say they went too early):")
    for p in over[:8]:
        print(
            f"  {p['name']:30s} drafted R{p['pick']:<2d} true R{p['vround']:<2d} ({p['pick'] - p['vround']} rounds)  "
            f"{A(p['avg'])} on {p['ab']:2d} AB  value {p['value']:+5.1f} {'SS' if is_ss(p) else ''}  ({p['team']})"
        )
    team, swapped = dream_team(players)
    n_f = sum(1 for p in team.values() if is_female(p))
    total_value = sum(p["value"] for p in team.values())
    print(
        f"DREAM TEAM (best value per round; coed rule: {n_f} women"
        f"{', legal as-is' if not swapped else f', swapped rounds {sorted(swapped)}'}; "
        f"total value {total_value:+.1f}):"
    )
    for rd in range(1, ROUNDS + 1):
        p = team[rd]
        tags = " ".join(
            t
            for t in ("SS" if is_ss(p) else "", "COED-SWAP" if rd in swapped else "")
            if t
        )
        print(
            f"  R{rd:<2d} {p['name']:30s} {A(p['avg'])} on {p['ab']:2d} AB  value {p['value']:+5.1f} "
            f"{tags}  ({p['team']})"
        )
    return players


# ---------------------------------------------------------------- standings


def load_standings(path):
    """Load a standings snapshot CSV: rank,team,w,l,t,gp,win_pct,pf,pa,diff.

    Snapshots come from https://cpsoftball.com/standings.php, saved weekly as
    MMDD-standings.csv so future editions can show week-over-week movement.
    """
    st = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            st.append(
                dict(
                    rank=int(r["rank"]),
                    team=r["team"].strip(),
                    w=int(r["w"]),
                    l=int(r["l"]),
                    t=int(r["t"]),
                    gp=int(r["gp"]),
                    win_pct=float(r["win_pct"]),
                    pf=int(r["pf"]),
                    pa=int(r["pa"]),
                    diff=int(r["diff"]),
                )
            )
    assert sum(s["pf"] for s in st) == sum(s["pa"] for s in st), (
        f"{path}: PF/PA don't balance"
    )
    for s in st:
        assert s["w"] + s["l"] + s["t"] == s["gp"], f"{path}: {s['team']} W+L+T != GP"
        assert abs((s["w"] + 0.5 * s["t"]) / s["gp"] - s["win_pct"]) < 0.0015, (
            f"{path}: {s['team']} win_pct mismatch"
        )
    return st


def pythag(s):
    """Pythagorean expectation: the win% a team's points profile 'earns'.

    Classic exponent 2. luck = actual win% - pythag; positive luck means the
    record is out-running the point differential (close wins), negative means
    the record understates the team.
    """
    return s["pf"] ** 2 / (s["pf"] ** 2 + s["pa"] ** 2)


def team_batting(players):
    agg = {}
    for p in players:
        a = agg.setdefault(p["team"], [0, 0])
        a[0] += p["h"] - p["co"]
        a[1] += p["ab"]
    bat = {t: v[0] / v[1] for t, v in agg.items()}
    brank = {t: i for i, t in enumerate(sorted(bat, key=lambda t: -bat[t]), 1)}
    ab = {t: v[1] for t, v in agg.items()}
    return bat, brank, ab


def pearson(xs, ys):
    """Pearson r between two equal-length, non-degenerate series."""
    mx, my = statistics.mean(xs), statistics.mean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(
        sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)
    )


def standings_digest(st, players, prev_st=None, prev_players=None):
    bat, brank, ab = team_batting(players)
    prev = {s["team"]: s for s in prev_st} if prev_st else None
    print(
        f"\n--- STANDINGS (joined to team batting; bat-rank delta = bat rank − standings rank) ---"
    )
    for s in st:
        move = ""
        if prev:
            d = prev[s["team"]]["rank"] - s["rank"]
            move = f"  move {d:+d}" if d else "  move ="
        py = pythag(s)
        print(
            f"{s['rank']:2d} {s['team']:32s} {s['w']}-{s['l']}-{s['t']}  win% {s['win_pct']:.3f}  "
            f"PF {s['pf']:3d} PA {s['pa']:3d} diff {s['diff']:+4d} | "
            f"pyth {py:.3f} luck {s['win_pct'] - py:+.3f} | "
            f"bat {A(bat[s['team']])} rank {brank[s['team']]:2d} ({brank[s['team']] - s['rank']:+d}) | "
            f"PF/100AB {100 * s['pf'] / ab[s['team']]:.0f}{move}"
        )
    print(
        f"win% vs team adj avg: r = "
        f"{pearson([s['win_pct'] for s in st], [bat[s['team']] for s in st]):+.2f}"
    )

    if not (prev_st and prev_players):
        return

    # The week's own table: what each club did in the games between the two
    # standings snapshots, joined to what its bats did over the same stretch.
    tw = {r["team"]: r for r in team_week_rows(prev_players, players, st, prev_st)}
    gp = {r["dgp"] for r in tw.values()}
    label = f"{next(iter(gp))} games each" if len(gp) == 1 else "uneven games played"
    print(f"\n--- STANDINGS WEEK ({label}) ---")
    for s in st:
        r = tw[s["team"]]
        rec = f"{r['dw']}-{r['dl']}" + (f"-{r['dt']}" if r["dt"] else "")
        print(
            f"{s['rank']:2d} {s['team']:32s} {rec:5s} "
            f"PF {r['dpf']:+3d} PA {r['dpa']:+3d} diff {r['ddiff']:+4d} | "
            f"rank #{r['orank']} -> #{s['rank']} ({r['move']:+d}) | "
            f"week bat {A(r['rate'])} (line {A(r['line'])}, gap {r['gap']:+.3f}) | "
            f"bat rank #{r['obrank']} -> #{r['brank']}"
        )
    rate = [tw[s["team"]]["rate"] for s in st]
    print(
        f"week bat rate vs week points scored: r = {pearson(rate, [tw[s['team']]['dpf'] for s in st]):+.3f}\n"
        f"week bat rate vs week wins:          r = {pearson(rate, [tw[s['team']]['dw'] for s in st]):+.3f}"
    )


def html_standings(st, players, prev_st=None):
    bat, brank, _ = team_batting(players)
    prev = {s["team"]: s for s in prev_st} if prev_st else None
    print(
        "<!-- STANDINGS: rank, team, record, win% meter, PF, PA, diff, pyth, luck, team avg, bat rank -->"
    )
    for s in st:
        d = s["diff"]
        dcell = f'<span class="{"zpos" if d >= 0 else "zneg"}">{f"{d:+d}".replace("-", "−")}</span>'
        py = pythag(s)
        luck = s["win_pct"] - py
        lcell = f'<span class="{"zpos" if luck >= 0 else "zneg"}">{f"{luck:+.3f}".replace("-", "−")}</span>'
        move = ""
        if prev:
            m = prev[s["team"]]["rank"] - s["rank"]
            arrow = "=" if m == 0 else (f"▲{m}" if m > 0 else f"▼{-m}")
            cls = "zpos" if m > 0 else ("zneg" if m < 0 else "muted")
            move = f'<td class="ctr num"><span class="{cls}">{arrow}</span></td>'
        print(
            f'        <tr><td class="ctr num">{s["rank"]}</td>{move}<td class="player">{team_label(s["team"])}</td>'
            f'<td class="num">{s["w"]}-{s["l"]}-{s["t"]}</td><td class="num big">{A(s["win_pct"])}</td>'
            f'<td><span class="meter" title="{team_label(s["team"])}: win% {A(s["win_pct"])}"><span style="width:{s["win_pct"] * 100:.1f}%"></span></span></td>'
            f'<td class="num">{s["pf"]}</td><td class="num">{s["pa"]}</td><td class="num">{dcell}</td>'
            f'<td class="num">{A(py)}</td><td class="num">{lcell}</td>'
            f'<td class="num">{A(bat[s["team"]])}</td><td class="ctr num">{brank[s["team"]]}</td></tr>'
        )


# ---------------------------------------------------------------- games


def snap_date(path):
    """Data date of an MMDD-*.csv snapshot filename as a datetime.date."""
    m = re.search(r"(\d{2})(\d{2})-(?:stats|standings|schedule)", path)
    if not m:
        sys.exit(f"{path}: can't read MMDD from the filename (expected MMDD-stats.csv style)")
    return datetime.date(SEASON_YEAR, int(m.group(1)), int(m.group(2)))


GAME_STATUSES = {"FINAL", "TIE", "SCHEDULED"}


def load_games(path):
    """Load the season schedule CSV: one row per game, completed and upcoming.

    Columns: date,time,field,team_a,score_a,team_b,score_b,status,note —
    harvested from https://cpsoftball.com/schedule.php (see CLAUDE.md). a/b is
    the site's listing order (the league has no home/away concept). Scores are
    blank exactly on SCHEDULED rows. Forfeits stay FINAL rows carrying the
    site's own score plus its note; validate_games() is what makes any of
    these numbers trustworthy.
    """
    games = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            status = r["status"].strip()
            if status not in GAME_STATUSES:
                sys.exit(f"{path}: bad status {status!r}")
            sa, sb = r["score_a"].strip(), r["score_b"].strip()
            if (status == "SCHEDULED") != (sa == "" == sb):
                sys.exit(
                    f"{path}: {r['date']} {r['team_a']} vs {r['team_b']}: "
                    "scores must be blank exactly when SCHEDULED"
                )
            for t in (r["team_a"].strip(), r["team_b"].strip()):
                if t not in CAPTAINS:
                    sys.exit(f"{path}: unknown team {t!r} — must match the canonical roster names")
            games.append(
                dict(
                    d=datetime.date.fromisoformat(r["date"].strip()),
                    tm=datetime.datetime.strptime(r["time"].strip(), "%I:%M %p").time(),
                    date=r["date"].strip(),
                    time=r["time"].strip(),
                    field=r["field"].strip(),
                    a=r["team_a"].strip(),
                    b=r["team_b"].strip(),
                    sa=int(sa) if sa else None,
                    sb=int(sb) if sb else None,
                    status=status,
                    note=r["note"].strip(),
                )
            )
    if not games:
        sys.exit(f"{path}: no game rows")
    for g in games:
        if g["status"] == "TIE" and g["sa"] != g["sb"]:
            sys.exit(f"{path}: {g['date']} {g['a']} vs {g['b']}: TIE with unequal scores")
        if g["status"] == "FINAL" and g["sa"] == g["sb"]:
            sys.exit(f"{path}: {g['date']} {g['a']} vs {g['b']}: FINAL with equal scores")
    keys = [(g["d"], g["tm"], g["field"]) for g in games]
    dups = sorted({k for k in keys if keys.count(k) > 1})
    if dups:
        sys.exit(f"{path}: duplicate (date, time, field) rows: {dups}")
    games.sort(key=lambda g: (g["d"], g["tm"], g["field"]))
    # Game-day shape: on any date with games, every listed club plays twice.
    # A WARN, not an exit — a future rainout could legitimately break it.
    for d in sorted({g["d"] for g in games}):
        n = {}
        for g in games:
            if g["d"] == d:
                n[g["a"]] = n.get(g["a"], 0) + 1
                n[g["b"]] = n.get(g["b"], 0) + 1
        odd = sorted(t for t, c in n.items() if c != 2)
        if odd:
            print(f"WARNING: {path}: {d} is not a clean doubleheader day for: {', '.join(odd)}")
    return games


def completed(games):
    return [g for g in games if g["status"] != "SCHEDULED"]


def validate_games(games, st, label, cutoff=None):
    """The schedule's trust anchor.

    Completed games (through the standings snapshot's date) must reconcile
    with the standings EXACTLY — per team W/L/T, PF and PA, plus the league
    game count implied by GP. Harvested scores are only trusted because this
    holds; on failure the per-team diff printed to stderr is the refetch guide.
    """
    done = [g for g in completed(games) if cutoff is None or g["d"] <= cutoff]
    agg = {s["team"]: [0, 0, 0, 0, 0] for s in st}  # W L T PF PA
    for g in done:
        sa, sb = g["sa"], g["sb"]
        assert sa is not None and sb is not None  # load_games guarantees it
        for team, us, them in ((g["a"], sa, sb), (g["b"], sb, sa)):
            if team not in agg:
                sys.exit(f"{label}: {team!r} plays games but is missing from the standings")
            a = agg[team]
            a[0] += us > them
            a[1] += us < them
            a[2] += us == them
            a[3] += us
            a[4] += them
    bad = []
    for s in st:
        w, l, t, pf, pa = agg[s["team"]]
        if (w, l, t, pf, pa) != (s["w"], s["l"], s["t"], s["pf"], s["pa"]):
            bad.append(
                f"  {s['team']:32s} games say {w}-{l}-{t}, PF {pf} PA {pa}"
                f"  |  standings say {s['w']}-{s['l']}-{s['t']}, PF {s['pf']} PA {s['pa']}"
            )
    want = sum(s["gp"] for s in st) // 2
    if len(done) != want:
        bad.append(f"  {len(done)} completed games in the file vs {want} implied by standings GP")
    if bad:
        print(f"{label}: schedule does not reconcile with the standings:", file=sys.stderr)
        for line in bad:
            print(line, file=sys.stderr)
        sys.exit(f"{label}: schedule<->standings identity FAILED — refetch the named teams' date ranges")
    print(
        f"GAMES OK: {label}: {len(done)} completed games reconcile exactly with the standings "
        f"({len(games) - len(completed(games))} scheduled ahead)",
        file=sys.stderr,
    )


def team_games(games, team):
    """One club's completed games, chronological: opp, us/them, W/L/T, margin."""
    out = []
    for g in completed(games):
        if team == g["a"]:
            us, them, opp = g["sa"], g["sb"], g["b"]
        elif team == g["b"]:
            us, them, opp = g["sb"], g["sa"], g["a"]
        else:
            continue
        assert us is not None and them is not None
        out.append(
            dict(
                d=g["d"], date=g["date"], time=g["time"], field=g["field"],
                opp=opp, us=us, them=them,
                result="T" if us == them else ("W" if us > them else "L"),
                margin=us - them, note=g["note"],
            )
        )
    return out


# ---------------------------------------------------------------- afternoon desk
# Computations behind the Afternoon Final's modules. Everything here reads the
# shared primitives (period_rows/team_period) plus the games/standings loaders;
# nothing prints except afternoon_digest() and the emitters further down.


def enrich(players):
    """All per-snapshot derived fields (z, value/vround, pickno). Idempotent —
    each function recomputes from raw counts, so calling twice is harmless."""
    add_z(players)
    add_value(players)
    add_picks(players)


def period_label(da, db):
    return f"{da.strftime('%b')} {da.day} → {db.strftime('%b')} {db.day}"


def hae(rows):
    """Hits Above Expectation for each period row: dH − dCO − dAB × own line.

    'Expected hits' = what the player's own season average at the previous
    snapshot predicts for this many at-bats. Positive = beat his own book.
    Volume-aware where the swing is not: a .700 afternoon on 20 ABs out-earns a
    1.000 afternoon on 4. None when the player sat or had no prior line."""
    for r in rows:
        r["hae"] = (
            (r["dh"] - r["dco"]) - r["dab"] * r["o"]["avg"]
            if r["dab"] > 0 and r["o"]["ab"]
            else None
        )
    return rows


def afternoon_awards(rows, tw):
    """Ranked shortlists for the Weeklies; index 0 of each list is the winner."""
    hae(rows)
    return dict(
        bat=sorted(
            (r for r in rows if r["hae"] is not None),
            key=lambda r: (-r["hae"], -r["dab"]),
        ),
        anvil=sorted(
            (r for r in rows if r["dab"] >= 4 and r["swing"] is not None),
            key=lambda r: (r["swing"], -r["dab"]),
        ),
        # ties broken by season CO total: the deepest sinner leads the shortlist
        vacuum=sorted(
            (r for r in rows if r["dco"] > 0),
            key=lambda r: (-r["dco"], -r["n"]["co"], -r["dab"]),
        ),
        ghost=sorted((r for r in rows if r["dab"] == 0), key=lambda r: r["n"]["rank"]),
        iron=sorted(
            (r for r in rows if r["dab"] > 0),
            key=lambda r: (-r["dab"], -(r["rate"] or 0.0)),
        ),
        sweep=[r for r in tw if r["dco"] == 0],
        ladder=sorted(rows, key=lambda r: (-r["drank"], r["n"]["rank"])),
        chute=sorted(rows, key=lambda r: (r["drank"], r["n"]["rank"])),
    )


def collapse_list(prev, cur, thresh=-0.300, min_dab=4):
    """The published Collapse cohort: swing <= thresh on min_dab+ period ABs."""
    return sorted(
        (
            r
            for r in period_rows(prev, cur)
            if r["dab"] >= min_dab and r["swing"] is not None and r["swing"] <= thresh
        ),
        key=lambda r: r["swing"],
    )


def rebound_ledger(prev2, prev, cur):
    """Last edition's Collapse cohort re-examined against the new period.

    REBOUNDED = the new period's rate above the player's own season line as it
    stood when the afternoon began (his line at prev); FELL AGAIN = at or below it;
    SAT = no at-bats. The cohort rule matches what the previous edition printed
    (fell 300+ points on 4+ period ABs)."""
    new = {(r["team"], r["pick"]): r for r in period_rows(prev, cur)}
    out = []
    for c in collapse_list(prev2, prev):
        r = new[(c["team"], c["pick"])]
        if r["dab"] == 0:
            verdict = "SAT"
        elif r["rate"] is not None and r["rate"] > r["o"]["avg"]:
            verdict = "REBOUNDED"
        else:
            verdict = "FELL AGAIN"
        out.append(dict(prior=c, now=r, verdict=verdict))
    return out


def team_series(snaps):
    """{team: [season adj avg at each snapshot]} over [(date, players), ...]."""
    out = {}
    for _, players in snaps:
        agg = {}
        for p in players:
            a = agg.setdefault(p["team"], [0, 0])
            a[0] += p["h"] - p["co"]
            a[1] += p["ab"]
        for t in sorted(agg):
            out.setdefault(t, []).append(agg[t][0] / agg[t][1])
    return out


def form_glyphs(snaps, deadband=0.050):
    """{(team, pick): glyph string}, one glyph per period between snapshots:
    ↗ swing above +deadband, ↘ below −deadband, → inside (or no prior line),
    · sat the period."""
    glyphs = {}
    for (_, a), (_, b) in zip(snaps, snaps[1:]):
        for r in period_rows(a, b):
            if r["dab"] == 0:
                g = "·"
            elif r["swing"] is None or abs(r["swing"]) <= deadband:
                g = "→"
            elif r["swing"] > 0:
                g = "↗"
            else:
                g = "↘"
            glyphs.setdefault((r["team"], r["pick"]), []).append(g)
    return {k: "".join(v) for k, v in glyphs.items()}


def family_week(prev, cur):
    """Aggregate family period rates: (ΣdH − ΣdCO) ÷ ΣdAB over single-surname
    families of 3+ players. Aggregate, like team weeks — season family averages
    are mean-of-player-averages, but a week is pooled at-bats."""
    fams = {}
    for r in period_rows(prev, cur):
        s = surname(r["n"])
        if " " not in s:
            fams.setdefault(s, []).append(r)
    out = {}
    for s, rs in sorted(fams.items()):
        if len(rs) < 3:
            continue
        dab = sum(r["dab"] for r in rs)
        if dab:
            out[s] = dict(
                rate=sum(r["dh"] - r["dco"] for r in rs) / dab,
                dab=dab,
                n=len(rs),
            )
    return out


def games_back(st):
    """{team: games behind the rank-1 club}: ((leadW − W) + (L − leadL)) / 2."""
    lead = next(s for s in st if s["rank"] == 1)
    return {
        s["team"]: ((lead["w"] - s["w"]) + (s["l"] - lead["l"])) / 2 for s in st
    }


def gb_str(v):
    """Games back, scoreboard-style: '—' for the leader, then '½', '1', '1½'."""
    if v <= 0:
        return "—"
    whole, half = int(v), v % 1 >= 0.5
    if whole == 0:
        return "½"
    return f"{whole}½" if half else f"{whole}"


def streaks(games):
    """{team: current run over its completed games, e.g. 'W3', 'L2', 'T1'}."""
    out = {}
    for t in sorted(CAPTAINS):
        gs = team_games(games, t)
        if not gs:
            continue
        last = gs[-1]["result"]
        n = 0
        for g in reversed(gs):
            if g["result"] != last:
                break
            n += 1
        out[t] = f"{last}{n}"
    return out


def longest_win_streaks(games):
    """{team: (length, start date, end date)} of each club's longest W run."""
    out = {}
    for t in sorted(CAPTAINS):
        best = (0, None, None)
        run, start = 0, None
        for g in team_games(games, t):
            if g["result"] == "W":
                if run == 0:
                    start = g["d"]
                run += 1
                if run > best[0]:
                    best = (run, start, g["d"])
            else:
                run = 0
        out[t] = best
    return out


def game_records(games):
    """Season game extremes over completed games; ties all listed."""
    rows = []
    for g in completed(games):
        sa, sb = g["sa"], g["sb"]
        assert sa is not None and sb is not None
        rows.append((abs(sa - sb), sa + sb, g))
    mmax = max(m for m, _, _ in rows)
    tmax = max(t for _, t, _ in rows)
    tmin = min(t for _, t, _ in rows)
    return dict(
        margin=[g for m, _, g in rows if m == mmax],
        highest=[g for _, t, g in rows if t == tmax],
        lowest=[g for _, t, g in rows if t == tmin],
    )


def head_to_head(games, teams):
    """{(a, b): [W, L, T]} of a vs b among a team subset, from completed games."""
    m = {(x, y): [0, 0, 0] for x in teams for y in teams if x != y}
    for g in completed(games):
        if g["a"] in teams and g["b"] in teams:
            sa, sb = g["sa"], g["sb"]
            assert sa is not None and sb is not None
            for x, y, sx, sy in ((g["a"], g["b"], sa, sb), (g["b"], g["a"], sb, sa)):
                rec = m[(x, y)]
                rec[0] += sx > sy
                rec[1] += sx < sy
                rec[2] += sx == sy
    return m


def next_afternoon(games, after):
    """The first game date after `after`: (date, {team: [its games, in time
    order]}). (None, {}) with a NOTICE if the schedule lists nothing ahead."""
    future = sorted({g["d"] for g in games if g["d"] > after})
    if not future:
        print(f"NOTICE: no scheduled games after {after} in the schedule file", file=sys.stderr)
        return None, {}
    d = future[0]
    by = {}
    for g in games:
        if g["d"] == d:
            by.setdefault(g["a"], []).append(
                dict(opp=g["b"], time=g["time"], field=g["field"], tm=g["tm"])
            )
            by.setdefault(g["b"], []).append(
                dict(opp=g["a"], time=g["time"], field=g["field"], tm=g["tm"])
            )
    for v in by.values():
        v.sort(key=lambda x: x["tm"])
    return d, by


# ---------------------------------------------------------------- schedule desk
# The Gauntlet and the Alibi Audit (first ran as a late supplement to the
# 2026-07-17 edition). Everything reads the game book plus the standings.
# Honesty limits, stated wherever these numbers print: player stats arrive as
# period deltas and every afternoon is two games, so no player's line can be
# pinned to a single opponent — a week is charged to the whole slate it was
# batted against. And the only defense the book can see is run prevention.


def run_rates(st):
    """{team: (PF/G, RA/G)} from the standings — the per-game run environment."""
    return {s["team"]: (s["pf"] / s["gp"], s["pa"] / s["gp"]) for s in st}


def defense_rank(st):
    """{team: 1..12} by runs allowed per game, stingiest first (ties by name)."""
    rr = run_rates(st)
    return {t: i + 1 for i, t in enumerate(sorted(rr, key=lambda t: (rr[t][1], t)))}


def sos_rows(games, st, dcur):
    """The Gauntlet's ledger, hardest played slate first.

    sosp = the mean, over a club's completed games, of that opponent's win% in
    its OTHER games — head-to-head results excluded, so beating a club cannot
    soften the slate it represented. sosl = the mean, over the club's
    scheduled games, of the opponent's current win% (None once the slate is
    done). vtop4 = scheduled games against the standings' current top four.
    unmet/twice = opponents never met / met twice among completed games.
    """
    done = [g for g in completed(games) if g["d"] <= dcur]
    future = [g for g in games if g["status"] == "SCHEDULED"]
    winpct = {s["team"]: s["win_pct"] for s in st}
    rank = {s["team"]: s["rank"] for s in st}
    top4 = {s["team"] for s in st[:4]}
    keyed = []
    for t in sorted(CAPTAINS):
        met, sos = [], []
        for g in team_games(done, t):
            met.append(g["opp"])
            others = [o for o in team_games(done, g["opp"]) if o["opp"] != t]
            if others:
                w = sum(o["result"] == "W" for o in others)
                ti = sum(o["result"] == "T" for o in others)
                sos.append((w + ti / 2) / len(others))
        if not sos:
            sys.exit(f"{t}: no completed games — the Gauntlet needs a played slate")
        left = [g["b"] if g["a"] == t else g["a"] for g in future if t in (g["a"], g["b"])]
        sosp = sum(sos) / len(sos)
        keyed.append(
            (
                sosp,
                dict(
                    team=t,
                    rank=rank[t],
                    sosp=sosp,
                    sosl=sum(winpct[o] for o in left) / len(left) if left else None,
                    left=len(left),
                    vtop4=sum(o in top4 for o in left),
                    unmet=sorted(o for o in CAPTAINS if o != t and o not in met),
                    twice=sorted(o for o in set(met) if met.count(o) >= 2),
                ),
            )
        )
    return [r for _, r in sorted(keyed, key=lambda kv: -kv[0])]


def season_series_pairs(games, dcur):
    """Every pairing meeting 3+ times on the full slate: [(a, b, played, left)],
    plus the meeting-count distribution {meetings: pair count} over all 66."""
    cnt, played = {}, {}
    for x in sorted(CAPTAINS):
        for y in sorted(CAPTAINS):
            if x < y:
                cnt[(x, y)] = 0
                played[(x, y)] = 0
    for g in games:
        k = (g["a"], g["b"]) if g["a"] < g["b"] else (g["b"], g["a"])
        cnt[k] += 1
        if g["status"] != "SCHEDULED" and g["d"] <= dcur:
            played[k] += 1
    dist = {}
    for k, n in cnt.items():
        dist[n] = dist.get(n, 0) + 1
    triples = [
        (a, b, played[(a, b)], n - played[(a, b)])
        for (a, b), n in sorted(cnt.items())
        if n >= 3
    ]
    return triples, dist


def period_opponents(snaps, games):
    """Aligned with snaps: [(game dates in the period, {team: [opponents]})].
    Index 0 is the season-opening block through the first snapshot — remember
    the blocks and the calendar don't align 1:1 (two early blocks hold two
    afternoons each)."""
    out = []
    prev_d = None
    for d, _ in snaps:
        m = {t: [] for t in sorted(CAPTAINS)}
        dates = set()
        for g in completed(games):
            if (prev_d is None or g["d"] > prev_d) and g["d"] <= d:
                m[g["a"]].append(g["b"])
                m[g["b"]].append(g["a"])
                dates.add(g["d"])
        out.append((sorted(dates), m))
        prev_d = d
    return out


def schedule_faced(snaps, games, st):
    """(team, pick) -> (AB-weighted mean opponent RA/G over the season, AB).

    The only slate measure the book supports at player level: each period's
    at-bats are charged to that period's whole opponent set. High = soft."""
    rr = run_rates(st)
    maps = period_opponents(snaps, games)
    agg = {}
    for i, (_, players) in enumerate(snaps):
        if i == 0:
            rows = [dict(team=p["team"], pick=p["pick"], dab=p["ab"]) for p in players]
        else:
            rows = period_rows(snaps[i - 1][1], players)
        for r in rows:
            opps = maps[i][1][r["team"]]
            if r["dab"] <= 0 or not opps:
                continue
            od = sum(rr[o][1] for o in opps) / len(opps)
            ab, tot = agg.get((r["team"], r["pick"]), (0, 0.0))
            agg[(r["team"], r["pick"])] = (ab + r["dab"], tot + r["dab"] * od)
    return {k: (tot / ab, ab) for k, (ab, tot) in agg.items() if ab}


def player_period_slates(snaps, games, st, team, pick):
    """One player's case file: [(dates, dab, dh, dco, rate, [(opp, drank)])]."""
    drank = defense_rank(st)
    maps = period_opponents(snaps, games)
    out = []
    for i, (_, players) in enumerate(snaps):
        if i == 0:
            p = next(p for p in players if (p["team"], p["pick"]) == (team, pick))
            dab, dh, dco = p["ab"], p["h"], p["co"]
        else:
            r = next(
                r
                for r in period_rows(snaps[i - 1][1], players)
                if (r["team"], r["pick"]) == (team, pick)
            )
            dab, dh, dco = r["dab"], r["dh"], r["dco"]
        dates, m = maps[i]
        rate = (dh - dco) / dab if dab else None
        out.append((dates, dab, dh, dco, rate, [(o, drank[o]) for o in m[team]]))
    return out


def alibi_verdict(snaps, games, st):
    """The Alibi Audit's verdict: every measure of a week, split by whether the
    slate was softer or harder than the league mean (by season RA/G).

    players: AB-weighted mean swing over player-weeks, soft vs hard slates.
    clubs:   AB-weighted mean gap to own line over club-weeks, same split.
    runs:    each completed game's score against that defense's runs allowed
             in its OTHER games, split at the median opposing defense.
    """
    rr = run_rates(st)
    lg = sum(ra for _, ra in rr.values()) / len(rr)
    maps = period_opponents(snaps, games)
    ps = [0.0, 0]
    ph = [0.0, 0]
    cs = [0.0, 0]
    ch = [0.0, 0]
    for i in range(1, len(snaps)):
        prev, cur = snaps[i - 1][1], snaps[i][1]
        m = maps[i][1]
        for r in period_rows(prev, cur):
            opps = m[r["team"]]
            if r["swing"] is None or not opps:
                continue
            od = sum(rr[o][1] for o in opps) / len(opps)
            side = ps if od >= lg else ph
            side[0] += r["dab"] * r["swing"]
            side[1] += r["dab"]
        tp = team_period(prev, cur)
        for t, a in tp.items():
            opps = m[t]
            if a["rate"] is None or a["line"] is None or not opps:
                continue
            od = sum(rr[o][1] for o in opps) / len(opps)
            side = cs if od >= lg else ch
            side[0] += a["dab"] * (a["rate"] - a["line"])
            side[1] += a["dab"]
    done = [g for g in completed(games) if g["d"] <= snaps[-1][0]]
    by_team = {t: team_games(done, t) for t in sorted(CAPTAINS)}
    obs = []
    for g in done:
        sa, sb = g["sa"], g["sb"]
        assert sa is not None and sb is not None
        for us, opp in ((sa, g["b"]), (sb, g["a"])):
            gs = by_team[opp]
            if len(gs) < 2:
                continue
            obs.append(((sum(x["them"] for x in gs) - us) / (len(gs) - 1), us))
    med = statistics.median(loo for loo, _ in obs)
    stingy = [us for loo, us in obs if loo < med]
    generous = [us for loo, us in obs if loo >= med]
    return dict(
        lg=lg,
        p_soft=ps[0] / ps[1],
        p_soft_ab=ps[1],
        p_hard=ph[0] / ph[1],
        p_hard_ab=ph[1],
        c_soft=cs[0] / cs[1],
        c_hard=ch[0] / ch[1],
        r_stingy=statistics.mean(stingy),
        r_generous=statistics.mean(generous),
    )


# ---------------------------------------------------------------- playoff desk
# Playoff Prediction Brackets (the 2026-08-14 playoff extra). The league posted a
# 12-club double-elimination bracket at cpsoftball.com/playoffs.php (Aug
# 21–22): seeds 1–4 draw first-round byes, seeds 5–12 play an opening
# round (5v12, 6v11, 7v10, 8v9), and the byes host the winners (1 gets
# W4, 2 gets W3, 3 gets W2, 4 gets W1). Seeding follows the standings, so
# the final afternoon IS the seeding afternoon — this desk enumerates
# every remaining W/T/L future and reports what can still happen.
# Honesty limits: seeding here is by points (2W + T — the win% ordering
# once every club has the same games played); the league's tiebreaker is
# NOT in the book, so every bound is computed twice — optimistic (all
# ties break for the club) and pessimistic (all ties break against it) —
# and anything between the bounds is tiebreak territory, said wherever
# these numbers print.


@dataclasses.dataclass
class PlayoffRow:
    """One club's enumerated postseason arithmetic (see playoff_futures)."""

    team: str
    pts: int  # current points, 2W + T
    lo_pts: int  # points if the club loses out
    hi_pts: int  # points if the club wins out
    best: int  # best reachable seed (optimistic tiebreaks)
    worst: int  # worst reachable seed (pessimistic tiebreaks)
    bye_opt: int  # futures with a seed <= 4 read optimistically
    bye_pes: int  # futures with a seed <= 4 read pessimistically
    top_opt: int  # futures in which no club finishes above them on points
    need_bye: list[int] | None  # per-game outcome forced in every opt-bye future
    need_best: list[int] | None  # ... in every best-seed future (-1 = varies)


@dataclasses.dataclass
class PlayoffDesk:
    total: int  # 3 ** len(slate)
    slate: list[dict]  # the unplayed games, schedule order
    teams: list[str]  # standings order (= current seed order)
    rows: list[PlayoffRow]  # same order as teams
    final_gp: int | None  # uniform games-played at season's end, if uniform


def playoff_futures(st, games):
    """Enumerate every W/T/L outcome of the remaining SCHEDULED games.

    Returns None when nothing is scheduled, or when more than 13 games
    remain (3^n futures — this is a final-afternoon instrument, not a
    midseason one). Otherwise a PlayoffDesk, one PlayoffRow per club in
    standings order.
    """
    slate = [g for g in games if g["status"] == "SCHEDULED"]
    if not slate:
        return None
    if len(slate) > 13:
        print(
            f"NOTICE: {len(slate)} games still scheduled — the playoff desk "
            "enumerates only a final slate of 13 or fewer games",
            file=sys.stderr,
        )
        return None
    teams = [s["team"] for s in st]
    idx = {t: i for i, t in enumerate(teams)}
    base = [2 * s["w"] + s["t"] for s in st]
    n, m = len(teams), len(slate)
    ga = [idx[g["a"]] for g in slate]
    gb = [idx[g["b"]] for g in slate]
    left = [0] * n
    for gi in range(m):
        left[ga[gi]] += 1
        left[gb[gi]] += 1
    best = [n + 1] * n
    worst = [0] * n
    bye_opt = [0] * n
    bye_pes = [0] * n
    top_opt = [0] * n
    need_bye: list[list[int] | None] = [None] * n
    need_best: list[list[int] | None] = [None] * n
    rng, grng = range(n), range(m)
    for outcome in itertools.product((0, 1, 2), repeat=m):
        pts = base[:]
        for gi in grng:
            o = outcome[gi]
            if o == 0:
                pts[ga[gi]] += 2
            elif o == 2:
                pts[gb[gi]] += 2
            else:
                pts[ga[gi]] += 1
                pts[gb[gi]] += 1
        order = sorted(pts)
        for i in rng:
            p = pts[i]
            opt = 1 + n - bisect.bisect_right(order, p)
            pes = n - bisect.bisect_left(order, p)
            if opt < best[i]:
                best[i] = opt
                need_best[i] = list(outcome)
            elif opt == best[i]:
                nb = need_best[i]
                assert nb is not None
                for gi in grng:
                    if nb[gi] != outcome[gi]:
                        nb[gi] = -1
            if pes > worst[i]:
                worst[i] = pes
            if pes <= 4:
                bye_pes[i] += 1
            if opt <= 4:
                bye_opt[i] += 1
                nb = need_bye[i]
                if nb is None:
                    need_bye[i] = list(outcome)
                else:
                    for gi in grng:
                        if nb[gi] != outcome[gi]:
                            nb[gi] = -1
            if opt == 1:
                top_opt[i] += 1
    rows = [
        PlayoffRow(
            team=teams[i],
            pts=base[i],
            lo_pts=base[i],
            hi_pts=base[i] + 2 * left[i],
            best=best[i],
            worst=worst[i],
            bye_opt=bye_opt[i],
            bye_pes=bye_pes[i],
            top_opt=top_opt[i],
            need_bye=need_bye[i],
            need_best=need_best[i],
        )
        for i in rng
    ]
    gps = {st[i]["gp"] + left[i] for i in rng}
    return PlayoffDesk(
        total=3**m,
        slate=slate,
        teams=teams,
        rows=rows,
        final_gp=gps.pop() if len(gps) == 1 else None,
    )


def playoff_needs(fut, cond):
    """The results forced in every future a condition tracker survived:
    ['X over Y', 'X–Y tie', ...] — [] when nothing is forced, None when no
    future satisfied the predicate at all (the thing is impossible)."""
    if cond is None:
        return None
    out = []
    for gi, o in enumerate(cond):
        if o == -1:
            continue
        g = fut.slate[gi]
        if o == 0:
            out.append(f"{g['a']} over {g['b']}")
        elif o == 2:
            out.append(f"{g['b']} over {g['a']}")
        else:
            out.append(f"{g['a']}–{g['b']} tie")
    return out


def playoff_pair_race(fut, ta, tb):
    """Two clubs' own remaining games, jointly enumerated: (a-ahead,
    b-ahead, level-on-points, combos). Exact even when the pair share a
    game or an opponent — the union of their games is what's enumerated."""
    own = [
        gi
        for gi, g in enumerate(fut.slate)
        if ta in (g["a"], g["b"]) or tb in (g["a"], g["b"])
    ]
    ia = fut.teams.index(ta)
    ib = fut.teams.index(tb)
    ahead = behind = level = 0
    for outcome in itertools.product((0, 1, 2), repeat=len(own)):
        pa, pb = fut.rows[ia].pts, fut.rows[ib].pts
        for gi, o in zip(own, outcome):
            g = fut.slate[gi]
            for team, gain in ((g["a"], (2, 1, 0)[o]), (g["b"], (0, 1, 2)[o])):
                if team == ta:
                    pa += gain
                elif team == tb:
                    pb += gain
        if pa > pb:
            ahead += 1
        elif pa < pb:
            behind += 1
        else:
            level += 1
    return ahead, behind, level, 3 ** len(own)


def playoff_digest(st, games):
    """The PLAYOFF DESK digest block (prints nothing off-season / midseason)."""
    fut = playoff_futures(st, games)
    if not fut:
        return
    total = fut.total
    print(
        f"\n--- PLAYOFF DESK ({len(fut.slate)} games unplayed -> {total:,} "
        "futures; seeds by points = 2W+T; opt/pes = every tie breaks for/against "
        "the club) ---"
    )
    if fut.final_gp is not None:
        print(f"  every club finishes at {fut.final_gp} games played")
    print(
        f"  {'club':32s} pts (lo-hi)   seed      misses bye in (opt-pes)   shares top seed in"
    )
    for r in fut.rows:
        miss = f"{total - r.bye_opt:,}-{total - r.bye_pes:,}"
        top = f"{r.top_opt:,}" if r.top_opt else "—"
        print(
            f"  {r.team:32s} {r.pts:2d}  ({r.lo_pts:2d}-{r.hi_pts:2d})  "
            f"{r.best:2d}..{r.worst:2d}  {miss:>21s}   {top:>10s}"
        )
    print("  BEST-SEED REQUIREMENTS (results forced in every best-case future):")
    for r in fut.rows:
        needs = playoff_needs(fut, r.need_best)
        assert needs is not None  # the best seed is achieved somewhere by definition
        body = "; ".join(needs) if needs else "(no single result is forced)"
        print(f"    {r.team} (best {r.best}): {body}")
    alive = [r for r in fut.rows if r.bye_opt and r.bye_opt < total]
    if alive:
        print("  BYE REQUIREMENTS (results forced in every optimistic-bye future):")
        for r in alive:
            needs = playoff_needs(fut, r.need_bye)
            assert needs is not None
            body = "; ".join(needs) if needs else "(no single result is forced)"
            print(f"    {r.team}: {body}")
    # clubs level on points contesting the bye line: their own games, head to head
    cont = [r for r in fut.rows if r.best <= 4]
    for ra, rb in itertools.combinations(cont, 2):
        if ra.pts == rb.pts and (ra.worst > 4 or rb.worst > 4):
            a, b, lv, combos = playoff_pair_race(fut, ra.team, rb.team)
            print(
                f"  LEVEL AT THE LINE — {ra.team} vs {rb.team} "
                f"(both {ra.pts} pts): of {combos} own-result combos, "
                f"{ra.team} ahead in {a}, {rb.team} in {b}, "
                f"level (tiebreak territory) in {lv}"
            )
    print("  R1 BRACKET AS THE TABLE STANDS (5v12, 6v11, 7v10, 8v9; byes 1-4):")
    order = [r.team for r in fut.rows]
    for hi, lo in ((4, 11), (5, 10), (6, 9), (7, 8)):
        print(f"    #{hi + 1} {order[hi]}  vs  #{lo + 1} {order[lo]}")


def race_top(players, n=4, min_ab=15):
    """The batting race's top n: [(player, hits back at own volume)]."""
    racers = sorted(
        (p for p in players if p["ab"] >= min_ab), key=lambda p: (-p["avg"], -p["ab"])
    )[:n]
    lead = racers[0]
    return [
        (p, 0.0 if p is lead else (lead["avg"] - p["avg"]) * p["ab"]) for p in racers
    ]


def race_history(snaps, min_ab=10):
    """[(date, leader by avg at that snapshot)] across the whole history."""
    return [
        (d, max((p for p in ps if p["ab"] >= min_ab), key=lambda p: (p["avg"], p["ab"])))
        for d, ps in snaps
    ]


# The weekly record book. records_board() recomputes every category from the
# full snapshot chain each run — no hand-maintained state to drift. The
# constant below is the board as LAST PUBLISHED (stamped with its edition
# date): a tripwire, not a source of truth. Recomputing the board through
# that date must reproduce it exactly; a mismatch means an upstream data
# revision — investigate before printing. Update both the rows and the AS_OF
# date whenever an edition publishes a new board.
RECORDS_PUBLISHED_AS_OF = datetime.date(2026, 8, 7)
RECORDS_PUBLISHED = [
    ("hot_week", "Timpson, Cuervo", 0.957),
    ("cold_week", "Dockstader, Dorothy", 0.154),
    ("team_best", "Youre Saying Theres A Chance", 0.700),
    ("team_worst", "The Playas", 0.356),
    ("family_best", "Cawley", 0.800),
    ("workload", "Hammon, Stafford", 46),
    ("team_co", "The Ellites", 16),
    ("player_co", "Williams, Charles", 4),
]

RECORD_CATS = [
    ("hot_week", "Hottest week (10+ AB)"),
    ("cold_week", "Coldest week (10+ AB)"),
    ("team_best", "Best team week"),
    ("team_worst", "Worst team week"),
    ("family_best", "Best family week"),
    ("workload", "Biggest workload week"),
    ("team_co", "Most caused outs in a week, team"),
    ("player_co", "Most caused outs in a week, player"),
]

HI_CATS = {"hot_week", "team_best", "family_best", "workload", "team_co", "player_co"}
RATE_CATS = {"hot_week", "cold_week", "team_best", "team_worst", "family_best"}


def fmtv(cat, v):
    return A(v) if cat in RATE_CATS else f"+{v}"


def records_board(snaps, min_dab=10):
    """{category: (value, [(holder, period label), ...])} across every period."""
    cats = {}

    def post(cat, val, who, label, hi):
        got = cats.get(cat)
        if got is None or (val > got[0] if hi else val < got[0]):
            cats[cat] = (val, [(who, label)])
        elif val == got[0]:
            got[1].append((who, label))

    for (da, a), (db, b) in zip(snaps, snaps[1:]):
        label = period_label(da, db)
        for r in period_rows(a, b):
            if r["dab"] >= min_dab and r["rate"] is not None:
                post("hot_week", r["rate"], r["name"], label, True)
                post("cold_week", r["rate"], r["name"], label, False)
            if r["dab"] > 0:
                post("workload", r["dab"], r["name"], label, True)
            if r["dco"] > 0:
                post("player_co", r["dco"], r["name"], label, True)
        for t, a2 in sorted(team_period(a, b).items()):
            if a2["dab"]:
                post("team_best", a2["rate"], t, label, True)
                post("team_worst", a2["rate"], t, label, False)
            if a2["dco"]:
                post("team_co", a2["dco"], t, label, True)
        for s, f in family_week(a, b).items():
            post("family_best", f["rate"], s, label, True)
    return cats


def records_report(snaps, near_rate=0.050, near_count=2):
    """Per category: the all-time mark + what the LAST period did to it.

    status: FELL (the afternoon set a new mark), MATCHED (tied it), NEAR MISS
    (within near_rate for rates / near_count for counts), HELD. Also runs the
    RECORDS_PUBLISHED drift tripwire against the board as of the previous
    snapshot."""
    now = records_board(snaps)
    before = records_board(snaps[:-1]) if len(snaps) >= 3 else None
    last = records_board(snaps[-2:])

    # Drift tripwire: the board as published on RECORDS_PUBLISHED_AS_OF must
    # be reproducible from the data through that date. Only runs when the
    # history chain reaches the stamp.
    pub_snaps = [s for s in snaps if s[0] <= RECORDS_PUBLISHED_AS_OF]
    if len(pub_snaps) >= 2 and pub_snaps[-1][0] == RECORDS_PUBLISHED_AS_OF:
        pub = records_board(pub_snaps)
        for cat, who, val in RECORDS_PUBLISHED:
            bval, bhold = pub[cat]
            names = {h for h, _ in bhold}
            want = set(who) if isinstance(who, tuple) else {who}
            close = abs(bval - val) < 0.0015 if isinstance(val, float) else bval == val
            if not (close and want <= names):
                print(
                    f"WARNING: records tripwire: {cat} recomputes to "
                    f"{fmtv(cat, bval)} {sorted(names)} but the published board "
                    f"says {fmtv(cat, val)} {sorted(want)}",
                    file=sys.stderr,
                )

    out = []
    for cat, title in RECORD_CATS:
        val, holders = now[cat]
        lval, lhold = last.get(cat, (None, []))
        status, prev = "—", ""
        if before is not None:
            bval, bhold = before[cat]
            hi = cat in HI_CATS
            near = near_rate if cat in RATE_CATS else near_count
            if lval is not None and (lval > bval if hi else lval < bval):
                status = "FELL"
                prev = f"{bhold[0][0]} ({fmtv(cat, bval)})"
            elif lval is not None and lval == bval:
                status = "MATCHED"
            elif lval is not None and abs(bval - lval) <= near:
                status = "NEAR MISS"
            else:
                status = "HELD"
        out.append(
            dict(
                cat=cat,
                title=title,
                value=val,
                holders=holders,
                status=status,
                prev=prev,
                last=lval,
                last_holders=lhold,
            )
        )
    return out


def afternoon_digest(snaps, games, st, prev_st):
    """The Afternoon Desk digest: every number the front of the paper transcribes.
    Raw team names throughout — this is the author's tool, not the page."""
    dcur, cur = snaps[-1]
    dprev, prev = snaps[-2]
    rows = period_rows(prev, cur)
    hae(rows)
    tw = team_week_rows(prev, cur, st, prev_st)
    gpast = [g for g in games if g["d"] <= dcur]
    afternoon = [g for g in completed(games) if dprev < g["d"] <= dcur]
    print(f"\n{'=' * 72}\n=== AFTERNOON DESK: {period_label(dprev, dcur)} ===\n{'=' * 72}")

    ranks = {s["team"]: s["rank"] for s in prev_st} if prev_st else {}
    print(f"\n--- AFTERNOON SCOREBOARD ({len(afternoon)} games, in afternoon order) ---")
    for g in afternoon:
        sa, sb = g["sa"], g["sb"]
        assert sa is not None and sb is not None
        tags = []
        if g["status"] == "TIE":
            tags.append("TIE")
        if abs(sa - sb) == 1:
            tags.append("1-RUN")
        if ranks and g["status"] == "FINAL":
            wt, lt = (g["a"], g["b"]) if sa > sb else (g["b"], g["a"])
            if ranks[wt] - ranks[lt] >= 6:
                tags.append(f"UPSET #{ranks[wt]} over #{ranks[lt]}")
        if g["note"]:
            tags.append(g["note"])
        print(
            f"  {g['time']:>7s} {g['field']:5s} {g['a']:30s} {sa:2d}  "
            f"{g['b']:30s} {sb:2d}  {' · '.join(tags)}"
        )

    hist = race_history(snaps)
    print("\n--- AFTERNOON CROWN (race history; chase = top 4 by avg, AB >= 15) ---")
    for d, p in hist:
        print(
            f"  {d.strftime('%b')} {d.day:>2d}: {p['name']:30s} {disp(p)} "
            f"on {p['ab']:2d} AB  ({p['team']})"
        )
    old_lead, new_lead = hist[-2][1], hist[-1][1]
    if (old_lead["team"], old_lead["pick"]) != (new_lead["team"], new_lead["pick"]):
        r = next(
            r
            for r in rows
            if (r["team"], r["pick"]) == (old_lead["team"], old_lead["pick"])
        )
        firstco = (
            " — his FIRST caused out of the season"
            if r["dco"] > 0 and r["o"]["co"] == 0
            else ""
        )
        print(
            f"  LEAD CHANGE: {old_lead['name']} fell {disp(old_lead)} -> "
            f"{disp(r['n'])} (rank #{r['o']['rank']} -> #{r['n']['rank']}), "
            f"afternoon {week_line(r)}{firstco}"
        )
    for p, back in race_top(cur, 4):
        b = "lead" if back == 0 else f"back {back:.1f} hits"
        print(f"  {p['name']:30s} {disp(p)} on {p['ab']:2d} AB  {b:14s} ({p['team']})")

    aw = afternoon_awards(rows, tw)
    print("\n--- AFTERNOON AWARDS ---")
    print("  BAT OF THE AFTERNOON (HAE = dH − dCO − dAB × own prior line):")
    for r in aw["bat"][:3]:
        print(
            f"    {r['name']:30s} {week_line(r):16s} HAE {r['hae']:+.2f} "
            f"vs own {A(r['o']['avg'])}  ({r['team']})"
        )
    print("  THE ANVIL (worst swing, 4+ AB):")
    for r in aw["anvil"][:3]:
        print(
            f"    {r['name']:30s} {week_line(r):16s} swing {r['swing']:+.3f} "
            f"vs own {A(r['o']['avg'])}  ({r['team']})"
        )
    print("  THE VACUUM (afternoon caused outs; ties broken by season CO):")
    for r in aw["vacuum"][:3]:
        print(
            f"    {r['name']:30s} +{r['dco']} CO (season {r['n']['co']})  "
            f"{week_line(r):16s} ({r['team']})"
        )
    print("  THE GHOST (highest-ranked player who sat the afternoon):")
    for r in aw["ghost"][:3]:
        print(
            f"    {r['name']:30s} rank #{r['n']['rank']:<3d} {disp(r['n'])} "
            f"on {r['n']['ab']:2d} AB  ({r['team']})"
        )
    print("  THE IRON WEEK (most afternoon at-bats):")
    for r in aw["iron"][:3]:
        rate = A(r["rate"]) if r["rate"] is not None else "—"
        print(f"    {r['name']:30s} {week_line(r):16s} rate {rate}  ({r['team']})")
    sweep = " | ".join(f"{r['team']} ({r['dh']}-for-{r['dab']})" for r in aw["sweep"])
    print(f"  CLEAN SWEEP (zero afternoon CO): {sweep or 'none'}")
    lad, chu = aw["ladder"][0], aw["chute"][0]
    print(
        f"  THE LADDER: {lad['name']} #{lad['o']['rank']} -> #{lad['n']['rank']} "
        f"(▲{lad['drank']})  |  THE CHUTE: {chu['name']} #{chu['o']['rank']} -> "
        f"#{chu['n']['rank']} (▼{-chu['drank']})"
    )

    print("\n--- FAMILY AFTERNOON (aggregate (dH − dCO) / dAB, families of 3+) ---")
    fw = family_week(prev, cur)
    for s, f in sorted(fw.items(), key=lambda kv: -kv[1]["rate"]):
        print(f"  {s:12s} {A(f['rate'])} on {f['dab']:3d} afternoon AB  ({f['n']} players)")

    if len(snaps) >= 3:
        led = rebound_ledger(snaps[-3][1], prev, cur)
        n_r = sum(1 for e in led if e["verdict"] == "REBOUNDED")
        n_f = sum(1 for e in led if e["verdict"] == "FELL AGAIN")
        n_s = sum(1 for e in led if e["verdict"] == "SAT")
        print(
            f"\n--- REBOUND LEDGER ({len(led)} collapsed 300+ last period: "
            f"{n_r} rebounded / {n_f} fell again / {n_s} sat) ---"
        )
        for e in led:
            c, r = e["prior"], e["now"]
            rate = A(r["rate"]) if r["rate"] is not None else "—"
            print(
                f"  {e['verdict']:10s} {r['name']:30s} was {c['swing']:+.3f}  "
                f"afternoon {week_line(r):16s} {rate:5s} vs own {A(r['o']['avg'])}  "
                f"({r['team']})"
            )

    gb = games_back(st)
    stk = streaks(gpast)
    lws = longest_win_streaks(gpast)
    # ---- the better half: the women's league table and the split boards
    women = sorted((p for p in cur if is_female(p)), key=lambda q: q["rank"])
    men = [p for p in cur if is_male(p)]
    unconf = sorted((p for p in cur if is_unconfirmed(p)), key=lambda q: q["rank"])
    print(
        f"\n--- THE BETTER HALF ({len(women)} confirmed women, {len(men)} "
        f"confirmed men, {len(unconf)} unconfirmed on neither side) ---"
    )
    for lbl, grp in (("women", women), ("men", men)):
        ab = sum(p["ab"] for p in grp)
        print(
            f"  {lbl:5s} n {len(grp):3d}  aggregate "
            f"{A(sum(p['h'] - p['co'] for p in grp) / ab)}  AB {ab:5d}  "
            f"mean draft round {statistics.mean(p['pick'] for p in grp):5.2f}  "
            f"earliest R{min(p['pick'] for p in grp):<2d}  "
            f"value {sum(p['value'] for p in grp):+7.1f}  "
            f"CO/AB {sum(p['co'] for p in grp) / ab:.4f}"
        )
    print(
        "  women by draft round: "
        + "  ".join(
            f"R{rd}:{sum(1 for p in women if p['pick'] == rd)}"
            for rd in range(1, ROUNDS + 1)
        )
    )
    print(
        "  unconfirmed, never guessed: "
        + " | ".join(f"{p['name']} ({p['team']})" for p in unconf)
    )
    print(f"  the women's table ({len(women)}, best first; page prints the top 20):")
    for i, p in enumerate(women, 1):
        print(
            f"   {i:2d}. #{p['rank']:<4d} {p['name']:24s} {p['team']:32s} "
            f"R{p['pick']:<3d} {disp(p)}  AB {p['ab']:3d}  H {p['h']:3d}  "
            f"CO {p['co']:2d}  value {p['value']:+6.1f}"
        )
    for female, lbl in ((False, "men"), (True, "women")):
        rows = gender_family_rows(cur, female)
        print(f"  best surnames, {lbl}'s side (households with 2+ {lbl}):")
        for i, r in enumerate(rows, 1):
            print(
                f"   {i:2d}. {r['sn']:12s} n {r['n']:2d}  clubs {r['teams']}  "
                f"AB {r['ab']:4d}  best {display_name(r['best']['name']):22s} "
                f"{disp(r['best'])}  famavg {A(r['famavg'])}"
            )
    if len(snaps) > 1:
        opener = {(p["team"], p["pick"]): p for p in snaps[0][1]}
        climbs = []
        for p in women:
            q = opener.get((p["team"], p["pick"]))
            if q:
                climbs.append((q["rank"] - p["rank"], p, q))
        climbs.sort(key=lambda c: -c[0])
        print(
            f"  season climb, {snaps[0][0].strftime('%b %-d')} to the finish "
            f"(joined on (team, pick), best five):"
        )
        for mv, p, q in climbs[:5]:
            print(
                f"   {p['name']:24s} #{q['rank']:<4d} -> #{p['rank']:<4d} "
                f"({mv:+d})   {disp(q)} -> {disp(p)}"
            )
    both = {r["sn"]: r["famavg"] for r in gender_family_rows(cur, False)}
    print("  households on BOTH boards (men − women):")
    for r in gender_family_rows(cur, True):
        if r["sn"] in both:
            print(
                f"   {r['sn']:12s} men {A(both[r['sn']])}  women {A(r['famavg'])}  "
                f"gap {both[r['sn']] - r['famavg']:+.3f}"
            )

    print("\n--- GAMES BACK & STREAKS ---")
    for s in st:
        t = s["team"]
        ln, a, b = lws[t]
        span = f"{a.strftime('%b')} {a.day}–{b.strftime('%b')} {b.day}" if ln else "—"
        print(
            f"{s['rank']:2d} {t:32s} GB {gb_str(gb[t]):>4s}  now {stk.get(t, '—'):3s}  "
            f"longest W run {ln} ({span})"
        )

    gr = game_records(gpast)

    def gline(g):
        return f"{g['a']} {g['sa']}–{g['sb']} {g['b']} ({g['date']})"

    nmarg = max(afternoon, key=lambda g: abs(g["sa"] - g["sb"]))
    ntot = max(afternoon, key=lambda g: g["sa"] + g["sb"])
    print("\n--- GAME RECORDS (all completed games) ---")
    print("  biggest margin : " + " | ".join(gline(g) for g in gr["margin"]))
    print("  highest-scoring: " + " | ".join(gline(g) for g in gr["highest"]))
    print("  lowest-scoring : " + " | ".join(gline(g) for g in gr["lowest"]))
    print(f"  this afternoon's extremes: margin {gline(nmarg)} | total {gline(ntot)}")

    top4 = [s["team"] for s in st[:4]]
    m = head_to_head(gpast, set(top4))
    print("\n--- HEAD-TO-HEAD (current top four; W-L-T of row vs column) ---")
    for x in top4:
        cells = []
        for y in top4:
            if x == y:
                cells.append("—")
            else:
                w_, l_, t_ = m[(x, y)]
                cells.append(f"{w_}-{l_}" + (f"-{t_}" if t_ else ""))
        print(f"  {x:32s} " + "  ".join(f"{c:6s}" for c in cells))

    print(
        "\n--- SCHEDULE DESK: THE GAUNTLET (SOS = opponents' win% in games "
        "not vs the club; hardest played slate first) ---"
    )
    for r in sos_rows(games, st, dcur):
        sosl = A(r["sosl"]) if r["sosl"] is not None else "—"
        print(
            f"  #{r['rank']:>2} {r['team']:32s} played {A(r['sosp'])} | "
            f"left {sosl} ({r['left']} games, {r['vtop4']} vs top four)"
        )
        print(f"      never met: {', '.join(r['unmet']) or '—'}")
        print(f"      met twice: {', '.join(r['twice']) or '—'}")
    triples, dist = season_series_pairs(games, dcur)
    ds = ", ".join(f"{n} pairs meet {k}x" for k, n in sorted(dist.items()))
    print(f"  SERIES SHAPE (all 66 pairings, full slate): {ds}")
    print("  TRIPLE ROUNDS (3 meetings on the season; played + left, left dates):")
    for a, b, p, sched in triples:
        when = ", ".join(
            g["date"]
            for g in games
            if g["status"] == "SCHEDULED" and {g["a"], g["b"]} == {a, b}
        )
        print(f"    {a} vs {b}: {p} played + {sched} left ({when or 'none left'})")

    print("\n--- SCHEDULE DESK: THE ALIBI AUDIT ---")
    rr = run_rates(st)
    drank = defense_rank(st)
    print("  defense ledger (runs allowed per game, stingiest first; the only")
    print("  defense the book can see — descriptive, not predictive, see verdict):")
    for t in sorted(rr, key=lambda t: drank[t]):
        pf, ra = rr[t]
        print(f"    D{drank[t]:<2} {t:32s} allows {ra:5.2f} | scores {pf:5.2f}")
    v = alibi_verdict(snaps, games, st)
    print(f"  THE VERDICT (slates split at the league mean {v['lg']:.2f} RA/G):")
    print(
        f"    player-weeks: soft slates swing {v['p_soft']:+.3f} on "
        f"{v['p_soft_ab']} AB | hard slates {v['p_hard']:+.3f} on {v['p_hard_ab']} AB"
    )
    print(
        f"    club-weeks:   soft slates gap {v['c_soft']:+.3f} | "
        f"hard slates {v['c_hard']:+.3f} (vs own line)"
    )
    print(
        f"    runs: {v['r_stingy']:.2f}/game vs the stingier half of defenses | "
        f"{v['r_generous']:.2f} vs the more generous half (each game vs that "
        "defense's RA/G in its other games, median split)"
    )
    faced = schedule_faced(snaps, games, st)
    print("  THE CHASE, RE-READ (slate faced = AB-weighted opponent RA/G; high = soft):")
    chase_faced = [(p, faced[(p["team"], p["pick"])][0]) for p, _ in race_top(cur, 4)]
    soft_ix = max(range(len(chase_faced)), key=lambda i: chase_faced[i][1])
    hard_ix = min(range(len(chase_faced)), key=lambda i: chase_faced[i][1])
    for i, (p, od) in enumerate(chase_faced):
        tag = " (hardest of four)" if i == hard_ix else (
            " (softest of four)" if i == soft_ix else ""
        )
        print(f"    {p['name']:30s} {disp(p)} on {p['ab']:2d} AB  slate {od:5.2f}{tag}  ({p['team']})")
    reg = [(od, ab, k) for k, (od, ab) in faced.items() if ab >= 15]
    print("  SLATES FACED, 15+ AB (softest and hardest three):")
    byname = {(p["team"], p["pick"]): p for p in cur}
    for od, ab, k in sorted(reg, reverse=True)[:3] + sorted(reg)[:3]:
        p = byname[k]
        print(f"    {p['name']:30s} slate {od:5.2f} on {ab:3d} AB  ({p['team']})")
    print("  CASE FILE — Hammon, Sean (The Pliggas, R12):")
    sp = next(p for p in cur if p["name"] == "Hammon, Sean")
    for dates, dab, dh, dco, rate, opps in player_period_slates(
        snaps, games, st, sp["team"], sp["pick"]
    ):
        when = " + ".join(f"{d.strftime('%b')} {d.day}" for d in dates)
        line = f"{dh}-for-{dab}" + (f" · {dco} CO" if dco else "")
        rs = A(rate) if rate is not None else "sat"
        os_ = ", ".join(f"{o} (D{dr})" for o, dr in opps)
        print(f"    {when}: {line:14s} {rs:5s} vs {os_}")
    sod, sab = faced[(sp["team"], sp["pick"])]
    unmet = next(r for r in sos_rows(games, st, dcur) if r["team"] == sp["team"])["unmet"]
    print(
        f"    slate faced {sod:5.2f} on {sab} AB (league mean {v['lg']:.2f}); "
        f"his club never met: {', '.join(unmet)}"
    )
    bw = next(p for p in cur if p["name"] == "Wood, Becky")
    bod, bab = faced[(bw['team'], bw['pick'])]
    softest = max(reg)[2] if reg else None
    tagb = " — the softest slate among 15+ AB regulars" if softest == (bw["team"], bw["pick"]) else ""
    print(
        f"  CASE FILE — Wood, Becky (#144): {bw['h']}-for-{bw['ab']}, "
        f"rank #{bw['rank']}, slate faced {bod:5.2f} on {bab} AB{tagb}"
    )

    nd, _ = next_afternoon(games, dcur)
    if nd:
        print(f"\n--- NEXT AFTERNOON ({nd.strftime('%b')} {nd.day}) ---")
        for g in games:
            if g["d"] == nd:
                print(f"  {g['time']:>7s} {g['field']:5s} {g['a']} vs {g['b']}")

    print("\n--- RECORDS WATCH (the weekly record book vs this afternoon) ---")
    for row in records_report(snaps):
        hold = ", ".join(f"{h} ({lab})" for h, lab in row["holders"])
        print(f"  {row['title']:34s} {fmtv(row['cat'], row['value']):>6s}  "
              f"{row['status']:9s} {hold}")
        if row["status"] == "FELL":
            print(f"      previous record: {row['prev']}")
        elif row["status"] in ("NEAR MISS", "MATCHED") and row["last"] is not None:
            who = ", ".join(h for h, _ in row["last_holders"])
            print(f"      this afternoon: {fmtv(row['cat'], row['last'])} ({who})")

    series = team_series(snaps)
    hdr = "  ".join(f"{d.strftime('%b')} {d.day:>2d}" for d, _ in snaps)
    print("\n--- ARCS SERIES (season adj avg at each snapshot) ---")
    print(f"  {'team':32s} {hdr}")
    for t in sorted(series, key=lambda t: -series[t][-1]):
        print(f"  {t:32s} " + "    ".join(A(v) for v in series[t]))

    playoff_digest(st, games)


# ---------------------------------------------------------------- html tables


def strip_the(team):
    return team[4:] if team.startswith("The ") else team


def team_label(team):
    """Display form for a team: "Gideon's team".

    Owner's rule, 2026-07-14: the league's own team names are NOT used on the
    page — every club is named by its captain. (They used to be carried as
    "Good Guys (Gideon's team)", which made every sentence in the week prose
    open with a six-word noun phrase.) The raw names still key every join and
    still print in the text digest, where they match the CSVs.
    """
    cap = CAPTAINS.get(team)
    if cap is None:
        print(
            f"WARNING: no captain on file for {team!r} — update CAPTAINS",
            file=sys.stderr,
        )
        return strip_the(team)
    return f"{cap}'s team"


def period_map(prev, cur):
    """(team, pick) -> (period AB, period rate or None), joined on the key."""
    return {
        (r["team"], r["pick"]): (r["dab"], r["rate"]) for r in period_rows(prev, cur)
    }


_PERIOD_CACHE = {}


def period_rows(prev, cur):
    """Per-player week record, joined on (team, pick).

    The single source of truth for "what happened this period" — the compare
    digest and every front-of-book HTML emitter read from this. Note that dh
    and dco are kept, not just their net: a week is reported as a *line*
    ("7-for-7"), where the hits are raw and only the rate is net of caused
    outs. That is why a 2-for-5 week with two caused outs is worth .000.
    Memoized per (prev, cur) pair — the afternoon digest and emitters walk every
    consecutive snapshot pair repeatedly.
    """
    memo = _PERIOD_CACHE.get((id(prev), id(cur)))
    if memo is not None:
        return memo
    po = {(p["team"], p["pick"]): p for p in prev}
    pn = {(p["team"], p["pick"]): p for p in cur}
    if set(po) != set(pn):
        sys.exit(
            f"join failure: only-prev {set(po) - set(pn)} only-cur {set(pn) - set(po)}"
        )
    rows = []
    for n in cur:
        o = po[(n["team"], n["pick"])]
        dab, dh, dco = n["ab"] - o["ab"], n["h"] - o["h"], n["co"] - o["co"]
        if dab < 0:
            print(
                f"WARNING: {n['name']} AB decreased {o['ab']} -> {n['ab']} (data revision?)"
            )
        rate = (dh - dco) / dab if dab > 0 else None
        rows.append(
            dict(
                name=n["name"],
                team=n["team"],
                pick=n["pick"],
                o=o,
                n=n,
                dab=dab,
                dh=dh,
                dco=dco,
                rate=rate,
                # swing: the week against the player's OWN season line — the
                # front-of-book statistic. NOT the same as dseason, which is the
                # same signal damped by dAB/total AB (see CLAUDE.md).
                swing=(rate - o["avg"]) if rate is not None and o["ab"] else None,
                dseason=n["avg"] - o["avg"],
                drank=o["rank"] - n["rank"],  # positive = climbed toward #1
            )
        )
    _PERIOD_CACHE[(id(prev), id(cur))] = rows
    return rows


def team_period(prev, cur):
    """Per-team aggregate of a period: dab/dh/dco, week rate, own prior line."""
    agg = {}
    for r in period_rows(prev, cur):
        a = agg.setdefault(r["team"], dict(dab=0, dh=0, dco=0, onet=0, oab=0))
        a["dab"] += r["dab"]
        a["dh"] += r["dh"]
        a["dco"] += r["dco"]
        a["onet"] += r["o"]["h"] - r["o"]["co"]
        a["oab"] += r["o"]["ab"]
    for a in agg.values():
        a["rate"] = (a["dh"] - a["dco"]) / a["dab"] if a["dab"] else None
        a["line"] = a["onet"] / a["oab"] if a["oab"] else None
    return agg


def week_line(r, html=False):
    """A week as a line: '7-for-7', or '2-for-5 · 2 CO' when caused outs erased hits."""
    s = f"{r['dh']}-for-{r['dab']}"
    if not r["dco"]:
        return s
    return (
        f'{s} <span class="muted">· {r["dco"]} CO</span>'
        if html
        else f"{s} · {r['dco']} CO"
    )


def team_week_rows(prev, cur, st=None, prev_st=None):
    """Per-team week aggregate, sorted best-to-worst by week rate.

    gap = week rate − the team's own season average at the previous snapshot:
    how far a club played from its own normal. This is what the Team
    Temperature bars draw. With both standings snapshots, each row also
    carries the week's record, points, run differential and rank move.
    """
    agg = team_period(prev, cur)

    sn = {s["team"]: s for s in st} if st else {}
    so = {s["team"]: s for s in prev_st} if prev_st else {}
    _, brank, _ = team_batting(cur)
    _, obrank, _ = team_batting(prev)

    rows = []
    for t, a in agg.items():
        rate, line = a["rate"], a["line"]
        r = dict(
            team=t,
            dab=a["dab"],
            dh=a["dh"],
            dco=a["dco"],
            rate=rate,
            line=line,
            gap=None if rate is None or line is None else rate - line,
            brank=brank[t],
            obrank=obrank[t],
        )
        if t in sn and t in so:
            n, o = sn[t], so[t]
            r.update(
                dw=n["w"] - o["w"],
                dl=n["l"] - o["l"],
                dt=n["t"] - o["t"],
                dgp=n["gp"] - o["gp"],
                dpf=n["pf"] - o["pf"],
                dpa=n["pa"] - o["pa"],
                ddiff=(n["pf"] - o["pf"]) - (n["pa"] - o["pa"]),
                rank=n["rank"],
                orank=o["rank"],
                move=o["rank"] - n["rank"],
            )
        rows.append(r)
    rows.sort(key=lambda r: -(r["rate"] if r["rate"] is not None else -9))
    return rows


def temp_scale(tw):
    """Team Temperature bar scale: the next .05 above the biggest |gap|, floored
    at .200. Mirrors the Report Card's max(6, ceil(max|z|)) idiom."""
    m = max((abs(r["gap"]) for r in tw if r["gap"] is not None), default=0.0)
    return max(0.200, math.ceil(m * 20) / 20)


# Shared HTML formatters. Every emitter (the legacy --html-tables one and the
# per-module afternoon emitters) speaks the same cell vocabulary through these.


def G(v):
    """A signed three-decimal delta, leading zero stripped: '+.060', '−.163'."""
    return f"{v:+.3f}".replace("-", "−").replace("0.", ".", 1)


def signed(v, text):
    return f'<span class="{"zpos" if v >= 0 else "zneg"}">{text}</span>'


def rankcell(r):
    return f'#{r["o"]["rank"]} <span class="muted">→</span> #{r["n"]["rank"]}'


def zspan(z):
    return f'<span class="{"zpos" if z >= 0 else "zneg"}">{Z(z)}</span>'


def vspan(v):
    return f'<span class="{"zpos" if v >= 0 else "zneg"}">{f"{v:+.1f}".replace("-", "−")}</span>'


def pname(p):
    return p["name"] + (
        ' <span class="muted">· SS</span>' if is_ss(p) else ""
    )


def gapspan(p):
    gap = p["pick"] - p["vround"]
    if gap > 0:
        return f'<span class="zpos">+{gap}</span>'
    if gap < 0:
        return f'<span class="zneg">−{-gap}</span>'
    return '<span class="muted">=</span>'


def arrow(m):
    """A ▲▼= movement span with the standard classes (positive = climbed)."""
    if m == 0:
        return '<span class="muted">=</span>'
    return f'<span class="{"zpos" if m > 0 else "zneg"}">{"▲" if m > 0 else "▼"}{abs(m)}</span>'


def disp(p):
    """A player's season average exactly as the source file prints it.

    The site rounds half UP (13-for-16 = .8125 prints .813); Python's round
    half-to-even would print .812. Display always transcribes the file."""
    return A(p["file_avg"])


def cap_slug(team):
    return CAPTAINS[team].lower().replace(" ", "-")


def club_slug(team):
    """Anchor id for a club's page block: club-caleb, club-boyds-daniel."""
    return "club-" + cap_slug(team)


def html_tables(cur, prev=None, prev2=None, st=None, prev_st=None):
    """Emit page-ready HTML for every table on the page, in page order.

    With prev: the whole front of book (the week's caused-out ledger, the
    perfect weeks, the Collapse and the Surge, the Team Temperature card and
    the Team Box) plus the weekly variants further down (This Week columns,
    hot/cold sheet, dynasty-week rows). With prev2 as well: Streaks & Slides.
    Without prev: season-only variants, for archive pages.
    """
    add_z(cur)
    per = period_map(prev, cur) if prev else {}

    # ---- the front of book: the week (needs prev)
    if prev:
        wk = period_rows(prev, cur)
        wkt = team_week_rows(prev, cur, st, prev_st)
        scale = temp_scale(wkt)
        season_co = {}
        for p in cur:
            season_co[p["team"]] = season_co.get(p["team"], 0) + p["co"]

        print("<!-- WEEK CO BY TEAM: caused outs committed in the period, worst first -->")
        worst = max(r["dco"] for r in wkt)
        for r in sorted(wkt, key=lambda r: (-r["dco"], r["team"])):
            cls = (
                ' class="lo"'
                if r["dco"] == worst
                else (' class="hl"' if r["dco"] == 0 else "")
            )
            print(
                f'        <tr{cls}><td class="player">{team_label(r["team"])}</td>'
                f'<td class="num">{r["dco"]}</td><td class="num">{r["dab"]}</td>'
                f'<td class="num">{100 * r["dco"] / r["dab"]:.1f}</td>'
                f'<td class="num"><span class="muted">{season_co[r["team"]]}</span></td></tr>'
            )

        print("\n<!-- PERFECT WEEKS: rate 1.000 — no out made, none caused (min 4 period AB) -->")
        for r in sorted(
            (r for r in wk if r["dab"] >= 4 and r["rate"] == 1.0), key=lambda r: -r["dab"]
        ):
            print(
                f'        <tr class="hl"><td class="player">{r["name"]}</td>'
                f'<td class="team-name">{team_label(r["team"])}</td>'
                f'<td class="num">{week_line(r, html=True)}</td>'
                f'<td class="num big">{A(r["rate"])}</td>'
                f'<td class="num">{A(r["o"]["avg"])}</td><td class="num">{A(r["n"]["avg"])}</td>'
                f'<td class="ctr num">{rankcell(r)}</td></tr>'
            )

        sw = sorted(
            (r for r in wk if r["dab"] >= 4 and r["swing"] is not None),
            key=lambda r: r["swing"],
        )

        def swingrow(r, lead):
            cls = ""
            if lead:
                cls = ' class="lo"' if r["swing"] < 0 else ' class="hl"'
            return (
                f'        <tr{cls}><td class="player">{r["name"]}</td>'
                f'<td class="team-name">{team_label(r["team"])}</td>'
                f'<td class="num">{week_line(r, html=True)}</td>'
                f'<td class="num{" big" if lead else ""}">{A(r["rate"])}</td>'
                f'<td class="num">{A(r["o"]["avg"])}</td>'
                f'<td class="num">{signed(r["swing"], G(r["swing"]))}</td>'
                f'<td class="num">{A(r["n"]["avg"])}</td>'
                f'<td class="ctr num">{rankcell(r)}</td></tr>'
            )

        print("\n<!-- THE COLLAPSE: biggest drops below a player's own season line -->")
        for i, r in enumerate(sw[:10]):
            print(swingrow(r, i == 0))

        print("\n<!-- THE SURGE: biggest jumps above a player's own season line -->")
        for i, r in enumerate(sw[:-11:-1]):
            print(swingrow(r, i == 0))

        print(
            f"\n<!-- TEAM TEMPERATURE: week rate − own season line, bars scaled to ±{A(scale)} -->"
        )
        print('                <div class="rc-card temp">')
        for r in wkt:
            tip = (
                f'{team_label(r["team"])}: hit {A(r["rate"])} this week against a '
                f'{A(r["line"])} season line'
            )
            print(
                f'                    <div class="rc-row">\n'
                f'                        <div class="rc-team">{team_label(r["team"])}</div>\n'
                f'                        <div class="rc-track" title="{tip}">\n'
                f'                            <div class="rc-bar {"pos" if r["gap"] >= 0 else "neg"}"'
                f' style="width: {abs(r["gap"]) / scale * 50:.1f}%"></div>\n'
                f"                        </div>\n"
                f'                        <div class="rc-val">{G(r["gap"])}</div>\n'
                f"                    </div>"
            )
        print(
            f'                    <div class="rc-legend">Each team\'s week rate minus its own'
            f" season average at the previous edition, scaled to ±{A(scale)}."
            f'<span class="swatch swatch-pos"></span>hit above their own line'
            f'<span class="swatch swatch-neg"></span>below</div>'
        )
        print("                </div>")

        print(
            "\n<!-- TEAM BOX: the week team by team — week line, own season line, gap, week record -->"
        )
        for i, r in enumerate(wkt):
            cls = (
                ' class="hl"'
                if i == 0
                else (' class="lo"' if i == len(wkt) - 1 else "")
            )
            if "dw" in r:
                rec = f"{r['dw']}-{r['dl']}" + (f"-{r['dt']}" if r["dt"] else "")
                arrow = (
                    "="
                    if r["move"] == 0
                    else (f"▲{r['move']}" if r["move"] > 0 else f"▼{-r['move']}")
                )
                acls = "zpos" if r["move"] > 0 else ("zneg" if r["move"] < 0 else "muted")
                diff = f"{r['ddiff']:+d}".replace("-", "−")
                tail = (
                    f'<td class="ctr num">{rec}</td>'
                    f'<td class="num">{signed(r["ddiff"], diff)}</td>'
                    f'<td class="ctr num">#{r["rank"]} <span class="{acls}">{arrow}</span></td>'
                )
            else:
                tail = '<td class="ctr num"><span class="muted">—</span></td>' * 3
            print(
                f'        <tr{cls}><td class="player">{team_label(r["team"])}</td>'
                f'<td class="num">{r["dab"]}</td><td class="num">{r["dh"]}</td>'
                f'<td class="num">{r["dco"]}</td>'
                f'<td class="num big">{A(r["rate"])}</td>'
                f'<td class="num"><span class="muted">{A(r["line"])}</span></td>'
                f'<td class="num">{signed(r["gap"], G(r["gap"]))}</td>{tail}</tr>'
            )
        print()

    if st:
        html_standings(st, cur, prev_st)
        print()

    print("<!-- BATTING RACE: top 3 by avg (min 15 AB); back = (leader avg - avg) * own AB -->")
    racers = sorted((p for p in cur if p["ab"] >= 15), key=lambda p: (-p["avg"], -p["ab"]))[:3]
    lead = racers[0]
    for i, p in enumerate(racers, 1):
        back = (
            '<span class="muted">—</span>'
            if p is lead
            else f"{(lead['avg'] - p['avg']) * p['ab']:.1f}"
        )
        cls = ' class="hl"' if p is lead else ""
        print(
            f'        <tr{cls}><td class="ctr num">{i}</td><td class="player">{p["name"]}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="num{" big" if p is lead else ""}">{A(p["avg"])}</td>'
            f'<td class="num">{p["ab"]}</td><td class="num">{back}</td></tr>'
        )

    print("\n<!-- CLEAN HANDS: zero caused outs all season, top 8 by AB -->")
    clean = sorted(
        (p for p in cur if p["co"] == 0 and p["ab"] > 0), key=lambda p: (-p["ab"], -p["avg"])
    )
    for p in clean[:8]:
        print(
            f'        <tr><td class="player">{p["name"]}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="num">{p["ab"]}</td><td class="num">{A(p["avg"])}</td></tr>'
        )

    rper = {}
    if prev:
        for rd in range(1, ROUNDS + 1):
            vals = [per[(p["team"], p["pick"])] for p in cur if p["pick"] == rd]
            dab = sum(d for d, _ in vals)
            dnet = sum(d * r for d, r in vals if r is not None)
            rper[rd] = dnet / dab if dab else None

    teams = {}
    for p in cur:
        teams.setdefault(p["team"], []).append(p)
    order = sorted(
        teams,
        key=lambda t: (
            -(
                (sum(p["h"] for p in teams[t]) - sum(p["co"] for p in teams[t]))
                / sum(p["ab"] for p in teams[t])
            )
        ),
    )

    print(
        "<!-- TEAM SHEET A: best & worst pick per team, season z (standings order) -->"
    )
    for t in order:
        live = [p for p in teams[t] if p["ab"] > 0]
        b = max(live, key=lambda p: p["z"])
        w = min(live, key=lambda p: p["z"])
        print(
            f'        <tr><td class="player">{team_label(t)}</td>'
            f'<td class="team-name">{b["name"]} (R{b["pick"]})</td>'
            f'<td class="num">{A(b["avg"])}</td><td class="num">{zspan(b["z"])}</td>'
            f'<td class="team-name">{w["name"]} (R{w["pick"]})</td>'
            f'<td class="num">{A(w["avg"])}</td><td class="num">{zspan(w["z"])}</td></tr>'
        )

    if prev:
        print(
            "\n<!-- TEAM SHEET B: hot & cold bat of the week per team (min 6 period AB; muted = round period rate) -->"
        )
        for t in order:
            q = [p for p in teams[t] if per[(p["team"], p["pick"])][0] >= 6]

            def prate(p):
                rate = per[(p["team"], p["pick"])][1]
                assert rate is not None  # guaranteed by the >= 6 period-AB filter
                return rate

            hot = max(q, key=prate)
            cold = min(q, key=prate)

            def cell(p):
                dab, rate = per[(p["team"], p["pick"])]
                rrate = rper[p["pick"]]
                assert rate is not None and rrate is not None
                return (
                    f'<td class="team-name">{p["name"]} (R{p["pick"]})</td>'
                    f'<td class="num">{A(rate)} <span class="muted">(rd {A(rrate)})</span></td>'
                    f'<td class="num">{dab}</td>'
                )

            print(
                f'        <tr><td class="player">{team_label(t)}</td>{cell(hot)}{cell(cold)}</tr>'
            )

    # ---- verdict tables (value-based)
    add_value(cur)

    # Previous snapshot's true rounds (its own league average — i.e. exactly
    # what the previous edition published), for ▲▼= Move cells on every table
    # with a True Rd column. No prev -> no Move column (archive pages).
    vprev = None
    if prev:
        add_value(prev)
        vprev = {(q["team"], q["pick"]): q["vround"] for q in prev}

    def movecell(p):
        if vprev is None:
            return ""
        m = vprev[(p["team"], p["pick"])] - p["vround"]
        if m == 0:
            return '<td class="ctr num"><span class="muted">=</span></td>'
        arrow = f"▲{m}" if m > 0 else f"▼{-m}"
        return f'<td class="ctr num"><span class="{"zpos" if m > 0 else "zneg"}">{arrow}</span></td>'

    print(
        "\n<!-- DREAM TEAM: best value per round, coed rule enforced (>= 2 women); "
        "'in for' = seat change vs the prev edition's dream team -->"
    )
    dteam, dswapped = dream_team(cur)
    dprev = dream_team(prev)[0] if prev else None
    for rd in range(1, ROUNDS + 1):
        p = dteam[rd]
        coed = (
            ' <span class="muted">· coed</span>' if rd in dswapped else ""
        )
        change = ""
        if dprev is not None:
            o = dprev[rd]
            if (o["team"], o["pick"]) != (p["team"], p["pick"]):
                change = (
                    f' <span class="muted">· in for {o["name"]}</span>'
                )
        print(
            f'        <tr><td class="ctr num">{rd}</td><td class="player">{pname(p)}{coed}{change}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td><td class="num">{A(p["avg"])}</td>'
            f'<td class="num">{p["ab"]}</td><td class="num">{vspan(p["value"])}</td></tr>'
        )

    print("\n<!-- PRICED RIGHT: true round == drafted round (Move = true round vs prev snapshot) -->")
    for p in sorted(
        (q for q in cur if q["vround"] == q["pick"]),
        key=lambda q: (q["pick"], -q["value"]),
    ):
        print(
            f'        <tr><td class="ctr num">{p["pick"]}</td>{movecell(p)}<td class="player">{pname(p)}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td><td class="num">{A(p["avg"])}</td>'
            f'<td class="num">{p["ab"]}</td><td class="num">{vspan(p["value"])}</td></tr>'
        )

    print("\n<!-- UNDERDRAFTED top 8: went later than their stats deserve -->")
    under = sorted(
        (q for q in cur if q["pick"] > q["vround"]),
        key=lambda q: (-(q["pick"] - q["vround"]), -q["value"]),
    )
    for p in under[:8]:
        print(
            f'        <tr><td class="player">{pname(p)}</td><td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="ctr num">R{p["pick"]}</td><td class="ctr num big">R{p["vround"]}</td>{movecell(p)}'
            f'<td class="num"><span class="zpos">{p["pick"] - p["vround"]} early</span></td>'
            f'<td class="num">{A(p["avg"])}</td><td class="num">{p["ab"]}</td><td class="num">{vspan(p["value"])}</td></tr>'
        )

    print("\n<!-- OVERDRAFTED top 8: stats say they went too early -->")
    over = sorted(
        (q for q in cur if q["pick"] < q["vround"]),
        key=lambda q: (q["pick"] - q["vround"], q["value"]),
    )
    for p in over[:8]:
        print(
            f'        <tr><td class="player">{pname(p)}</td><td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="ctr num">R{p["pick"]}</td><td class="ctr num big">R{p["vround"]}</td>{movecell(p)}'
            f'<td class="num"><span class="zneg">{p["vround"] - p["pick"]} late</span></td>'
            f'<td class="num">{A(p["avg"])}</td><td class="num">{p["ab"]}</td><td class="num">{vspan(p["value"])}</td></tr>'
        )

    add_picks(cur)
    ranked = sorted(cur, key=lambda p: (-p["value"], -p["avg"], -p["ab"], p["name"]))
    vrank = {id(p): i for i, p in enumerate(ranked, 1)}

    print(
        "\n<!-- CAPTAINS MIRROR: where each captain drafted themselves vs their true round -->"
    )
    for team in DRAFT_ORDER:
        p = next(q for q in cur if q["name"] == CAPTAIN_PLAYER[team])
        print(
            f'        <tr><td class="player">{pname(p)}</td><td class="team-name">{team_label(team)}</td>'
            f'<td class="ctr num">#{p["pickno"]}</td><td class="ctr num">R{p["pick"]}</td>'
            f'<td class="ctr num">R{p["vround"]}</td>{movecell(p)}<td class="num">{gapspan(p)}</td>'
            f'<td class="num">{A(p["avg"])}</td><td class="num">{p["ab"]}</td>'
            f'<td class="num">{vspan(p["value"])}</td></tr>'
        )

    print(
        "\n<!-- FULL DOCKET: every player in true snake-draft order; League # = value rank -->"
    )
    prev_rd = None
    for p in sorted(cur, key=lambda p: p["pickno"]):
        brk = (
            ' class="rd-break"' if prev_rd is not None and p["pick"] != prev_rd else ""
        )
        prev_rd = p["pick"]
        print(
            f'        <tr{brk}><td class="ctr num">#{p["pickno"]}</td><td class="ctr num">{p["pick"]}</td>'
            f'<td class="player">{pname(p)}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="ctr num">R{p["vround"]}</td>{movecell(p)}<td class="num">{gapspan(p)}</td>'
            f'<td class="ctr num">#{vrank[id(p)]}</td><td class="num">{A(p["avg"])}</td>'
            f'<td class="num">{p["ab"]}</td><td class="num">{vspan(p["value"])}</td></tr>'
        )

    print("\n<!-- ROUND ROOMS: hl row = round valedictorian, lo row = the cellar -->")
    for rd in range(1, ROUNDS + 1):
        ps = sorted(
            (p for p in cur if p["pick"] == rd),
            key=lambda p: (-p["avg"], -p["ab"], p["name"]),
        )
        print(
            f'  <h3 id="round-{rd}"><a href="#round-{rd}">Round {rd} — {ROUND_NICKNAMES[rd]}</a></h3>'
        )
        print('  <div class="table-scroll">\n    <table>\n      <thead>')
        week_th = '<th class="num">This Week (ABs)</th>' if prev else ""
        print(
            f'        <tr><th>Player</th><th>Team</th><th class="num">Avg</th>'
            f'<th class="num">ABs</th><th class="num">z</th>{week_th}</tr>'
        )
        print("      </thead>\n      <tbody>")
        cellar = max((i for i, p in enumerate(ps) if p["ab"] > 0), default=0)
        for i, p in enumerate(ps):
            hl = ' class="hl"' if i == 0 else (' class="lo"' if i == cellar else "")
            if p["ab"]:
                avg_c = f'<td class="num{" big" if i == 0 else ""}">{A(p["avg"])}</td>'
                z_c = f'<td class="num">{zspan(p["z"])}</td>'
            else:
                avg_c, z_c = '<td class="num">—</td>', '<td class="num">—</td>'
            wk = ""
            if prev:
                dab, rate = per[(p["team"], p["pick"])]
                wk = (
                    f'<td class="num">{A(rate)} ({dab})</td>'
                    if rate is not None
                    else '<td class="num">—</td>'
                )
            print(
                f'        <tr{hl}><td class="player">{p["name"]}</td>'
                f'<td class="team-name">{team_label(p["team"])}</td>{avg_c}'
                f'<td class="num">{p["ab"]}</td>{z_c}{wk}</tr>'
            )
        season = statistics.mean([p["avg"] for p in ps if p["ab"] > 0])
        cap = f"Round {rd}: season average {A(season)}"
        if prev and rper[rd] is not None:
            cap += f" · hit {A(rper[rd])} as a group this period"
        print(
            f"      </tbody>\n      <caption>{cap}.</caption>\n    </table>\n  </div>"
        )

    if prev:
        print(
            "\n<!-- DYNASTY WEEK: family period rates (family, rate, period ABs, players) -->"
        )
        fams = {}
        for p in cur:
            s = surname(p)
            if " " not in s:
                fams.setdefault(s, []).append(p)
        rows = []
        for s, ps in fams.items():
            if len(ps) < 3:
                continue
            vals = [per[(p["team"], p["pick"])] for p in ps]
            dab = sum(d for d, _ in vals)
            dnet = sum(d * r for d, r in vals if r is not None)
            rows.append((s, dnet / dab, dab, len(ps)))
        for s, rate, dab, n in sorted(rows, key=lambda r: -r[1]):
            print(
                f'        <tr><td class="player">{s}</td><td class="num">{A(rate)}</td>'
                f'<td class="num">{dab}</td><td class="num">{n}</td></tr>'
            )

    if prev and prev2:
        print(
            "\n<!-- STREAKS & SLIDES: same direction both periods, 6+ ABs in each; "
            "heat rows then cool rows (rd-break starts the slides) -->"
        )
        heat, cool = two_week_trends(prev2, prev, cur)
        for kind, rows_ in (("zpos", heat[:6]), ("zneg", cool[:6])):
            for j, (p, r1, r2, d1, d2) in enumerate(rows_):
                brk = ' class="rd-break"' if kind == "zneg" and j == 0 else ""
                print(
                    f'        <tr{brk}><td class="player">{p["name"]}</td>'
                    f'<td class="team-name">{team_label(p["team"])}</td>'
                    f'<td class="ctr num">R{p["pick"]}</td>'
                    f'<td class="num">{A(r1)} ({d1})</td>'
                    f'<td class="num"><span class="{kind}">{A(r2)}</span> ({d2})</td>'
                    f'<td class="num">{A(p["avg"])}</td></tr>'
                )


# ---------------------------------------------------------------- afternoon html
# One emitter per page module, page order, registered in AFTERNOON_EMITTERS.
# Future editions add/swap registry entries instead of growing one monolith.
# Banner comments name the module id they feed. Digest prints raw team names;
# THESE emit team_label() — nothing else is allowed to name a club on a page.


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def emit_invoice(c):
    """Recurring module (debuted 2026-07-24; re-set as a paper document
    2026-08-12): a statement of account, addressed to whoever leads the
    standings. Emits the whole document — letterhead, addressee, dotted-leader
    line items, the period's results as their own docket, the balance-due
    band, and the terms fine print. Every value is computed; the stamp is the
    edition's one hand-written word, per the t-note pattern."""
    s = c["st"][0]
    t = s["team"]
    py = pythag(s)
    luck = s["win_pct"] - py
    bat, brank, _ = team_batting(c["cur"])
    sos = sos_rows(c["games"], c["st"], c["dcur"])
    pos = next(i for i, r in enumerate(sos, 1) if r["team"] == t)
    sosp = next(r["sosp"] for r in sos if r["team"] == t)
    soft = (
        '<span class="muted"> · the softest in the league</span>'
        if pos == len(sos)
        else f' <span class="muted">· {ordinal(pos)} hardest of {len(sos)}</span>'
    )
    afternoon_gs = [g for g in team_games(c["gpast"], t) if g["d"] > c["dprev"]]
    print(
        f"<!-- INVOICE (id invoice): statement of account for {team_label(t)}, "
        f"the standings leader -->"
    )

    def line(label, value):
        print(f"        <div class=\"st-line\"><dt>{label}</dt><dd>{value}</dd></div>")

    mv_html = ""
    if c["ranks"]:
        was = c["ranks"][t]
        if was != s["rank"]:
            mv_html = f' <span class="muted">(was {ordinal(was)})</span>'
    print('<div class="statement">')
    print(
        '    <div class="st-head"><span class="st-brand">CP Softball · the desk '
        f'of accounts</span><span class="st-no">Statement of account · the '
        f'{c["pnoun"]} of {c["pdates"]}</span></div>'
    )
    print(
        f'    <div class="st-to"><span class="st-tag">Billed to</span>'
        f'<strong>{team_label(t)}</strong> — occupant, first place'
        f'\n        <div class="st-stamp" aria-hidden="true"><!-- one hand-written stamp --></div>'
        f"\n    </div>"
    )
    print('    <dl class="st-lines">')
    line(
        "The standing",
        f'<strong>{ordinal(s["rank"])}</strong> of 12 · '
        f'{s["w"]}-{s["l"]}-{s["t"]}{mv_html}',
    )
    line("Win percentage", A(s["win_pct"]))
    line("Runs scored · runs allowed", f'{s["pf"]} · {s["pa"]}')
    line("Pythagorean expectation", A(py))
    line("League batting rank", f'{ordinal(brank[t])} at {A(bat[t])}')
    line("Slate played to date (SOS)", f"{A(sosp)}{soft}")
    print("    </dl>")
    print('    <div class="st-games">')
    print(
        f'        <div class="st-games-label">Results on account · '
        f'{len(afternoon_gs)} games</div>'
    )
    print("        <ul>")
    res_cls = {"W": "win", "L": "loss", "T": "tie"}
    for g in afternoon_gs:
        print(
            f'            <li><span class="st-res {res_cls[g["result"]]}">{g["result"]}</span>'
            f'<span class="st-score">{g["us"]}–{g["them"]}</span>'
            f'<span class="st-opp">vs {team_label(g["opp"])}</span></li>'
        )
    print("        </ul>")
    print("    </div>")
    if c["prev_st"]:
        ps = next((x for x in c["prev_st"] if x["team"] == t), None)
        if ps is not None:
            pl = ps["win_pct"] - pythag(ps)
            print('    <dl class="st-lines">')
            line(
                f'Balance carried forward '
                f'<span class="muted">(at {c["dprev"].strftime("%B")} {c["dprev"].day})</span>',
                signed(pl, G(pl)),
            )
            print("    </dl>")
    print(
        f'    <div class="st-due"><span class="st-due-label"><strong>Balance due</strong> '
        f'<span class="muted">— luck, the gap between the record and the runs</span></span>'
        f'<span class="st-due-amt">{signed(luck, G(luck))}</span></div>'
    )
    print(
        '    <p class="st-fine">Terms: luck = winning percentage minus the '
        "Pythagorean expectation (defined under the standings) — a large "
        "positive balance means winning games the run totals don't explain. "
        "SOS played = the mean of each opponent's winning percentage in its "
        "other games. Every line above is computed from the book; the desk "
        "adds nothing but the stamp.</p>"
    )
    print("</div>")


def emit_debits(c):
    """One-off module (2026-07-24): the caused-out ledger for an afternoon when
    the league's CO rate spiked. Club ledger worst-first, then the individual
    debits (every +2 or worse) and the erased (every hit cancelled)."""
    rows, tw, cur, prev = c["rows"], c["tw"], c["cur"], c["prev"]
    wab = sum(r["dab"] for r in rows)
    wco = sum(r["dco"] for r in rows)
    oab = sum(p["ab"] for p in prev)
    oco = sum(p["co"] for p in prev)
    nab = sum(p["ab"] for p in cur)
    nco = sum(p["co"] for p in cur)
    print(
        f"<!-- DEBITS (id debits): the caused-out ledger — {wco} CO on {wab} "
        f"afternoon AB ({wco / wab:.3f}/AB vs {oco / oab:.3f} season-to-date "
        f"coming in); season now {nco} CO on {nab} AB -->"
    )
    season_co = {}
    for p in cur:
        season_co[p["team"]] = season_co.get(p["team"], 0) + p["co"]
    worst = max(r["dco"] for r in tw)
    for r in sorted(tw, key=lambda r: (-r["dco"], r["team"])):
        cls = (
            ' class="lo"'
            if r["dco"] == worst
            else (' class="hl"' if r["dco"] == 0 else "")
        )
        line = f'{r["dh"]}-for-{r["dab"]}' + (
            f' <span class="muted">· {r["dco"]} CO</span>' if r["dco"] else ""
        )
        print(
            f'        <tr{cls}><td class="player">{team_label(r["team"])}</td>'
            f'<td class="num">{line}</td>'
            f'<td class="num">+{r["dco"]}</td>'
            f'<td class="num">{r["dco"] / r["dab"] * 100:.1f}</td>'
            f'<td class="num">{season_co[r["team"]]}</td></tr>'
        )
    ind = sorted(
        (r for r in rows if r["dco"] >= 2),
        key=lambda r: (-r["dco"], -r["n"]["co"], r["name"]),
    )
    erased = sorted(
        (
            r
            for r in rows
            if r["dab"] >= 4 and r["dh"] > 0 and r["dh"] == r["dco"] and r not in ind
        ),
        key=lambda r: r["name"],
    )
    print(
        "\n<!-- DEBITS individuals (same section): every +2 or worse, then the "
        "erased — a full afternoon whose every hit was cancelled (rd-break "
        "starts the erased) -->"
    )
    for j, r in enumerate(ind + erased):
        brk = ' class="rd-break"' if j == len(ind) else ""
        print(
            f'        <tr{brk}><td class="player">{r["name"]}</td>'
            f'<td class="team-name">{team_label(r["team"])}</td>'
            f'<td class="num">{week_line(r, html=True)}</td>'
            f'<td class="num">+{r["dco"]}</td>'
            f'<td class="num">{r["n"]["co"]}</td></tr>'
        )


def emit_scoreboard(c):
    print("<!-- SCOREBOARD (id scoreboard): the afternoon's games in time order; tags computed -->")
    print('<div class="tickets">')
    ranks = c["ranks"]
    for g in c["afternoon"]:
        sa, sb = g["sa"], g["sb"]
        assert sa is not None and sb is not None
        tags = []
        if g["status"] == "TIE":
            tags.append(("tie", "TIE"))
        if abs(sa - sb) == 1:
            tags.append(("one-run", "1-RUN"))
        if ranks and g["status"] == "FINAL":
            wt, lt = (g["a"], g["b"]) if sa > sb else (g["b"], g["a"])
            if ranks[wt] - ranks[lt] >= 6:
                tags.append(("upset", "UPSET"))
        if g["note"]:
            tags.append(("note", g["note"]))
        tag_html = "".join(f'<span class="tag {k}">{txt}</span>' for k, txt in tags)
        awin = " win" if sa > sb else ""
        bwin = " win" if sb > sa else ""
        hhmm = g["time"].replace(" PM", "")
        print(
            f'    <article class="ticket">\n'
            f'        <div class="t-meta">{hhmm} · {g["field"]}{tag_html}</div>\n'
            f'        <div class="t-row{awin}"><span class="t-team">{team_label(g["a"])}</span>'
            f'<span class="t-score">{sa}</span></div>\n'
            f'        <div class="t-row{bwin}"><span class="t-team">{team_label(g["b"])}</span>'
            f'<span class="t-score">{sb}</span></div>\n'
            f'        <p class="t-note"><!-- one hand-written line --></p>\n'
            f"    </article>"
        )
    print("</div>")


def emit_crown(c):
    print("<!-- CROWN (id race): the chase — top 4 by avg, AB >= 15 -->")
    for i, (p, back) in enumerate(race_top(c["cur"], 4), 1):
        b = '<span class="muted">—</span>' if back == 0 else f"{back:.1f}"
        r = c["bykey"][(p["team"], p["pick"])]
        wl = week_line(r, html=True) if r["dab"] else '<span class="muted">sat</span>'
        print(
            f'        <tr{" class=" + chr(34) + "hl" + chr(34) if i == 1 else ""}>'
            f'<td class="ctr num">{i}</td><td class="player">{p["name"]}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="num{" big" if i == 1 else ""}">{disp(p)}</td>'
            f'<td class="num">{p["ab"]}</td><td class="num">{wl}</td>'
            f'<td class="num">{b}</td></tr>'
        )
    print("\n<!-- CROWN HISTORY: the leader at every snapshot -->")
    for d, p in race_history(c["snaps"]):
        print(
            f'        <tr><td class="team-name">{d.strftime("%B")} {d.day}</td>'
            f'<td class="player">{p["name"]}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="num">{disp(p)}</td><td class="num">{p["ab"]}</td></tr>'
        )


def emit_weeklies(c):
    aw = c["aw"]

    def card(name, winner, club, cite, also):
        also_html = f'\n        <p class="a-also">then: {also}</p>' if also else ""
        print(
            f'    <article class="award">\n'
            f'        <div class="a-name">{name}</div>\n'
            f'        <div class="a-winner">{winner}</div>\n'
            f'        <div class="a-club">{club}</div>\n'
            f'        <p class="a-cite">{cite}</p>{also_html}\n'
            f"    </article>"
        )

    print("<!-- WEEKLIES (id weeklies): computed awards, winner + citation + runners-up -->")
    print('<div class="weeklies">')
    b = aw["bat"][0]
    card(
        f'Bat of the {c["pnoun"].title()}', b["name"], team_label(b["team"]),
        f'{week_line(b, html=True)} — <strong>{b["hae"]:+.1f} hits</strong> above '
        f'their own book (line {A(b["o"]["avg"])})',
        " · ".join(f'{r["name"]} {r["hae"]:+.1f}' for r in aw["bat"][1:3]),
    )
    a = aw["anvil"][0]
    card(
        "The Anvil", a["name"], team_label(a["team"]),
        f'{week_line(a, html=True)} — {signed(a["swing"], G(a["swing"]))} against '
        f'their own {A(a["o"]["avg"])}',
        " · ".join(f'{r["name"]} {G(r["swing"])}' for r in aw["anvil"][1:3]),
    )
    v = aw["vacuum"][0]
    card(
        "The Vacuum", v["name"], team_label(v["team"]),
        f'+{v["dco"]} caused outs on a {week_line(v, html=True)} {c["pnoun"]} — '
        f'season total now <strong>{v["n"]["co"]}</strong>',
        " · ".join(f'{r["name"]} +{r["dco"]}' for r in aw["vacuum"][1:3]),
    )
    gh = aw["ghost"][0]
    card(
        "The Ghost", gh["name"], team_label(gh["team"]),
        f'league <strong>#{gh["n"]["rank"]}</strong>, {disp(gh["n"])} on '
        f'{gh["n"]["ab"]} AB — did not bat',
        " · ".join(f'{r["name"]} #{r["n"]["rank"]}' for r in aw["ghost"][1:3]),
    )
    ir = aw["iron"][0]
    rate = A(ir["rate"]) if ir["rate"] is not None else "—"
    card(
        "The Iron Week", ir["name"], team_label(ir["team"]),
        f'{week_line(ir, html=True)} — {rate}, the {c["pnoun"]}\'s biggest workload '
        f'(season AB {ir["o"]["ab"]} → {ir["n"]["ab"]})',
        " · ".join(f'{r["name"]} +{r["dab"]}' for r in aw["iron"][1:3]),
    )
    sw = aw["sweep"]
    card(
        "Clean Sweep", " · ".join(team_label(r["team"]) for r in sw) or "nobody",
        f'zero caused outs on the {c["pnoun"]}',
        " · ".join(f'{r["dh"]}-for-{r["dab"]}' for r in sw),
        "",
    )
    lad, chu = aw["ladder"][0], aw["chute"][0]
    card(
        "The Ladder", lad["name"], team_label(lad["team"]),
        f'{rankcell(lad)} <span class="zpos">(▲{lad["drank"]})</span> — '
        f'{week_line(lad, html=True)}',
        "",
    )
    card(
        "The Chute", chu["name"], team_label(chu["team"]),
        f'{rankcell(chu)} <span class="zneg">(▼{-chu["drank"]})</span> — '
        f'{week_line(chu, html=True)}',
        "",
    )
    print("</div>")


def emit_arcs_svg(c):
    series = c["series"]
    dates = [d for d, _ in c["snaps"]]
    x0, x1, yt, yb = 44.0, 560.0, 16.0, 384.0
    vlo, vhi = 0.400, 0.640
    span = (dates[-1] - dates[0]).days

    def X(d):
        return x0 + (d - dates[0]).days / span * (x1 - x0)

    def Y(v):
        return yt + (vhi - v) / (vhi - vlo) * (yb - yt)

    order = sorted(series, key=lambda t: (-series[t][-1], t))
    slots = []
    for t in order:
        ideal = Y(series[t][-1]) + 4.0
        slots.append(max(ideal, slots[-1] + 15.0) if slots else ideal)
    for i in range(len(slots) - 1, -1, -1):
        cap = 400.0 - 15.0 * (len(slots) - 1 - i)
        if slots[i] > cap:
            slots[i] = cap

    print("<!-- ARCS (id arcs): the season, club by club — colors live in page CSS -->")
    print('<figure class="arcs-fig">')
    print('    <div class="arcs-scroll">')
    print(
        '    <svg viewBox="0 0 760 420" role="img" '
        'aria-labelledby="arcs-title arcs-desc">'
    )
    dhdr = " → ".join(f"{d.strftime('%B')} {d.day}" for d in dates)
    print("        <title id=\"arcs-title\">Season batting arcs, all twelve clubs</title>")
    print(
        f'        <desc id="arcs-desc">Each club\'s season adjusted average at '
        f"the {len(dates)} snapshots: {dhdr}.</desc>"
    )
    for v in (0.450, 0.500, 0.550, 0.600):
        yy = Y(v)
        print(
            f'        <line class="arc-grid" x1="{x0:.1f}" y1="{yy:.1f}" '
            f'x2="{x1:.1f}" y2="{yy:.1f}" />'
        )
        print(
            f'        <text class="arc-tick" x="{x0 - 6:.1f}" y="{yy + 3.5:.1f}" '
            f'text-anchor="end">{A(v)}</text>'
        )
    for d in dates:
        print(
            f'        <text class="arc-tick" x="{X(d):.1f}" y="404" '
            f'text-anchor="middle">{d.strftime("%b")} {d.day}</text>'
        )
    for i, t in enumerate(order):
        vals = series[t]
        pts = " ".join(f"{X(d):.1f},{Y(v):.1f}" for d, v in zip(dates, vals))
        tip = f"{team_label(t)}: " + " → ".join(A(v) for v in vals)
        ey, ly = Y(vals[-1]), slots[i]
        print(f'        <g class="arc t-{cap_slug(t)}">')
        print(f"            <title>{tip}</title>")
        print(f'            <polyline class="arc-line" points="{pts}" />')
        print(
            f'            <path class="arc-lead" d="M {x1:.1f} {ey:.1f} '
            f'L {x1 + 8:.1f} {ly - 3.5:.1f} L {x1 + 14:.1f} {ly - 3.5:.1f}" />'
        )
        print(
            f'            <rect class="arc-chip" x="{x1 + 18:.1f}" '
            f'y="{ly - 11.5:.1f}" width="10" height="10" rx="2" />'
        )
        print(
            f'            <text class="arc-label" x="{x1 + 34:.1f}" y="{ly:.1f}">'
            f'{team_label(t)} <tspan class="arc-val">{A(vals[-1])}</tspan></text>'
        )
        print("        </g>")
    print("    </svg>\n    </div>")
    print(
        "    <figcaption>Season adjusted average at each snapshot. Highlighted "
        "clubs carry color; the label rail names every line, best season line "
        "first. Hover a line for its numbers.</figcaption>"
    )
    print("</figure>")


def emit_arcs_table(c):
    print("<!-- ARCS TABLE: the chart's own numbers (and its no-SVG fallback) -->")
    for t in sorted(c["series"], key=lambda t: (-c["series"][t][-1], t)):
        cells = "".join(f'<td class="num">{A(v)}</td>' for v in c["series"][t])
        print(f'        <tr><td class="player">{team_label(t)}</td>{cells}</tr>')


def emit_rebound(c):
    print("<!-- REBOUND (id rebound): last edition's Collapse cohort, afternoon verdicts -->")
    spans = {
        "REBOUNDED": '<span class="zpos">REBOUNDED</span>',
        "FELL AGAIN": '<span class="zneg">FELL AGAIN</span>',
        "SAT": '<span class="muted">SAT</span>',
    }
    tint = {"REBOUNDED": ' class="hl"', "FELL AGAIN": ' class="lo"', "SAT": ""}
    for e in rebound_ledger(c["snaps"][-3][1], c["prev"], c["cur"]):
        p, r = e["prior"], e["now"]
        rate = A(r["rate"]) if r["rate"] is not None else '<span class="muted">—</span>'
        wl = week_line(r, html=True) if r["dab"] else '<span class="muted">sat</span>'
        print(
            f'        <tr{tint[e["verdict"]]}><td class="player">{r["name"]}</td>'
            f'<td class="team-name">{team_label(r["team"])}</td>'
            f'<td class="num">{signed(p["swing"], G(p["swing"]))}</td>'
            f'<td class="num">{wl}</td><td class="num">{rate}</td>'
            f'<td class="num"><span class="muted">{A(r["o"]["avg"])}</span></td>'
            f'<td>{spans[e["verdict"]]}</td></tr>'
        )


def emit_clubhouse(c):
    print("<!-- CLUBHOUSE (id clubhouse): twelve club blocks in standings order -->")
    twby = {r["team"]: r for r in c["tw"]}
    byteam = {}
    for p in c["cur"]:
        byteam.setdefault(p["team"], []).append(p)
    for s in c["st"]:
        t = s["team"]
        r = twby[t]
        slug = club_slug(t)
        afternoon_gs = [g for g in team_games(c["gpast"], t) if g["d"] > c["dprev"]]
        res = " · ".join(
            f'{g["result"]} {g["us"]}–{g["them"]} vs {team_label(g["opp"])}'
            for g in afternoon_gs
        )
        nxt = ", ".join(team_label(x["opp"]) for x in c["nby"].get(t, [])) or "—"
        luck = s["win_pct"] - pythag(s)
        mv = (c["ranks"][t] - s["rank"]) if c["ranks"] else 0
        luck_txt = f"{luck:+.3f}".replace("-", "−")
        print(f'  <h3 id="{slug}"><a href="#{slug}">{team_label(t)}</a></h3>')
        print(
            f'  <div class="club-card">\n'
            f'      <div class="c-line"><strong>{ordinal(s["rank"])}</strong> · '
            f'{s["w"]}-{s["l"]}-{s["t"]} · GB {gb_str(c["gb"][t])} · '
            f'afternoon {arrow(mv)} · streak {c["stk"].get(t, "—")} · '
            f'luck {signed(luck, luck_txt)}</div>\n'
            f'      <div class="c-line">The {c["pnoun"]}: {res} — '
            f'{r["dh"]}-for-{r["dab"]}'
            + (f' · {r["dco"]} CO' if r["dco"] else "")
            + f' ({A(r["rate"])}) against a {A(r["line"])} season line</div>\n'
            f'      <div class="c-line">Next: {nxt}</div>\n'
            f"  </div>"
        )
        roster = sorted(byteam[t], key=lambda p: p["pick"])
        live = [
            c["bykey"][(p["team"], p["pick"])]
            for p in roster
            if c["bykey"][(p["team"], p["pick"])]["dab"] > 0
        ]
        hi = max(live, key=lambda r2: r2["swing"] or -9) if live else None
        lo = min(live, key=lambda r2: r2["swing"] or 9) if live else None
        print('  <div class="table-scroll">\n    <table>\n      <thead>')
        print(
            '        <tr><th class="ctr">Rd</th><th>Player</th>'
            '<th class="num">Afternoon</th><th class="num">Swing</th>'
            '<th class="num">Season</th><th class="ctr">Rank</th>'
            "<th class=\"ctr\">Form</th></tr>"
        )
        print("      </thead>\n      <tbody>")
        for p in roster:
            r2 = c["bykey"][(p["team"], p["pick"])]
            cls = (
                ' class="hl"'
                if r2 is hi
                else (' class="lo"' if r2 is lo else "")
            )
            afternoon_c = (
                week_line(r2, html=True) if r2["dab"] else '<span class="muted">sat</span>'
            )
            swing_c = (
                signed(r2["swing"], G(r2["swing"]))
                if r2["swing"] is not None
                else '<span class="muted">—</span>'
            )
            rank_c = rankcell(r2) if r2["dab"] else f"#{p['rank']}"
            glyph = c["glyphs"].get((p["team"], p["pick"]), "")
            print(
                f'        <tr{cls}><td class="ctr num">{p["pick"]}</td>'
                f'<td class="player">{p["name"]}</td>'
                f'<td class="num">{afternoon_c}</td><td class="num">{swing_c}</td>'
                f'<td class="num">{disp(p)}</td><td class="ctr num">{rank_c}</td>'
                f'<td class="ctr form">{glyph}</td></tr>'
            )
        print(
            f"      </tbody>\n      <caption>{team_label(t)}, player by player. "
            f"Form reads each period of the season against the player's own "
            f"line, oldest first (↗ up, → flat, ↘ down, · sat).</caption>\n"
            f"    </table>\n  </div>"
        )


def emit_standings_afternoon(c):
    print(
        "<!-- STANDINGS+ (id standings): rank, move, club, record, GB, win%, "
        "PF, PA, diff, streak, pyth, luck, bat, bat rank -->"
    )
    bat, brank, _ = team_batting(c["cur"])
    for s in c["st"]:
        t = s["team"]
        py = pythag(s)
        luck = s["win_pct"] - py
        mv = (c["ranks"][t] - s["rank"]) if c["ranks"] else 0
        d = s["diff"]
        print(
            f'        <tr><td class="ctr num">{s["rank"]}</td>'
            f'<td class="ctr num">{arrow(mv)}</td>'
            f'<td class="player">{team_label(t)}</td>'
            f'<td class="num">{s["w"]}-{s["l"]}-{s["t"]}</td>'
            f'<td class="num">{gb_str(c["gb"][t])}</td>'
            f'<td class="num big">{A(s["win_pct"])}</td>'
            f'<td class="num">{s["pf"]}</td><td class="num">{s["pa"]}</td>'
            f'<td class="num">{signed(d, f"{d:+d}".replace("-", "−"))}</td>'
            f'<td class="ctr num">{c["stk"].get(t, "—")}</td>'
            f'<td class="num">{A(py)}</td>'
            f'<td class="num">{signed(luck, f"{luck:+.3f}".replace("-", "−"))}</td>'
            f'<td class="num">{A(bat[t])}</td>'
            f'<td class="ctr num">{brank[t]}</td></tr>'
        )


def emit_gauntlet(c):
    print(
        "<!-- THE GAUNTLET (id gauntlet): SOS ledger, hardest played slate "
        "first; vtop4 = scheduled games vs the current top four -->"
    )
    for r in sos_rows(c["games"], c["st"], c["dcur"]):
        sosl = A(r["sosl"]) if r["sosl"] is not None else "—"
        unmet = " · ".join(team_label(t) for t in r["unmet"]) or "—"
        twice = " · ".join(team_label(t) for t in r["twice"]) or "—"
        print(
            f'        <tr><td class="ctr num">{r["rank"]}</td>'
            f'<td class="player">{team_label(r["team"])}</td>'
            f'<td class="num big">{A(r["sosp"])}</td>'
            f'<td class="num">{sosl}</td>'
            f'<td class="ctr num">{r["vtop4"]}</td>'
            f"<td>{unmet}</td><td>{twice}</td></tr>"
        )


def emit_alibi(c):
    st, games, snaps, cur = c["st"], c["games"], c["snaps"], c["cur"]
    rr = run_rates(st)
    drank = defense_rank(st)
    print(
        "<!-- THE ALIBI AUDIT (id alibi): defense ledger — runs allowed per "
        "game, stingiest first; descriptive, not predictive (the verdict) -->"
    )
    for t in sorted(rr, key=lambda t: drank[t]):
        pf, ra = rr[t]
        print(
            f'        <tr><td class="ctr num">D{drank[t]}</td>'
            f'<td class="player">{team_label(t)}</td>'
            f'<td class="num big">{ra:.2f}</td>'
            f'<td class="num">{pf:.2f}</td></tr>'
        )
    faced = schedule_faced(snaps, games, st)
    print(
        "\n<!-- CHASE SLATES (id chase-slates): the crown chase re-read; "
        "slate faced = AB-weighted opponent RA/G, high = soft -->"
    )
    chase_faced = [(p, faced[(p["team"], p["pick"])][0]) for p, _ in race_top(cur, 4)]
    soft_ix = max(range(len(chase_faced)), key=lambda i: chase_faced[i][1])
    hard_ix = min(range(len(chase_faced)), key=lambda i: chase_faced[i][1])
    for i, (p, od) in enumerate(chase_faced):
        tag = (
            ' <span class="muted">· hardest of the four</span>'
            if i == hard_ix
            else (' <span class="muted">· softest of the four</span>' if i == soft_ix else "")
        )
        print(
            f'        <tr><td class="ctr num">{i + 1}</td>'
            f'<td class="player">{pname(p)}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="num">{disp(p)}</td><td class="num">{p["ab"]}</td>'
            f'<td class="num">{od:.2f}{tag}</td></tr>'
        )
    print(
        "\n<!-- CASE FILE (id case-sean): Sean Hammon block by block; "
        "slate = opponents with defense rank -->"
    )
    sp = next(p for p in cur if p["name"] == "Hammon, Sean")
    for dates, dab, dh, dco, rate, opps in player_period_slates(
        snaps, games, st, sp["team"], sp["pick"]
    ):
        when = " + ".join(f"{d.strftime('%b')} {d.day}" for d in dates)
        line = f"{dh}-for-{dab}" + (
            f' <span class="muted">· {dco} CO</span>' if dco else ""
        )
        rs = A(rate) if rate is not None else "—"
        os_ = " · ".join(f"{team_label(o)} (D{dr})" for o, dr in opps)
        print(
            f'        <tr><td class="player">{when}</td>'
            f'<td class="num">{line}</td><td class="num big">{rs}</td>'
            f"<td>{os_}</td></tr>"
        )


def emit_value_desk(c):
    cur, prev = c["cur"], c["prev"]
    print(
        "<!-- VALUE DESK (id value / dream-team): best value per round, coed "
        "rule; 'in for' = seat change vs the previous edition -->"
    )
    dteam, dswapped = dream_team(cur)
    dprev = dream_team(prev)[0]
    for rd in range(1, ROUNDS + 1):
        p = dteam[rd]
        coed = ' <span class="muted">· coed</span>' if rd in dswapped else ""
        o = dprev[rd]
        change = (
            f' <span class="muted">· in for {o["name"]}</span>'
            if (o["team"], o["pick"]) != (p["team"], p["pick"])
            else ""
        )
        print(
            f'        <tr><td class="ctr num">{rd}</td>'
            f'<td class="player">{pname(p)}{coed}{change}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="num">{disp(p)}</td>'
            f'<td class="num">{p["ab"]}</td><td class="num">{vspan(p["value"])}</td></tr>'
        )
    po = {(q["team"], q["pick"]): q for q in prev}
    moved = []
    for p in cur:
        m = po[(p["team"], p["pick"])]["vround"] - p["vround"]
        if m:
            moved.append((m, p))
    print(
        f"\n<!-- VALUE MOVERS: {len(moved)}/{len(cur)} changed true round; "
        "top climbs then slides (rd-break starts the slides) -->"
    )
    ups = sorted(moved, key=lambda t: (-t[0], -t[1]["value"]))[:4]
    downs = sorted(moved, key=lambda t: (t[0], t[1]["value"]))[:4]
    for j, (m, p) in enumerate(ups + downs):
        brk = ' class="rd-break"' if j == len(ups) else ""
        o = po[(p["team"], p["pick"])]
        print(
            f'        <tr{brk}><td class="player">{pname(p)}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="ctr num">R{o["vround"]} <span class="muted">→</span> R{p["vround"]}</td>'
            f'<td class="ctr num">{arrow(m)}</td>'
            f'<td class="num">{disp(p)}</td><td class="num">{p["ab"]}</td>'
            f'<td class="num">{vspan(p["value"])}</td></tr>'
        )


def emit_full_docket(c):
    cur, prev = c["cur"], c["prev"]
    po = {(q["team"], q["pick"]): q for q in prev}
    ranked = sorted(cur, key=lambda p: (-p["value"], -p["avg"], -p["ab"], p["name"]))
    vrank = {id(p): i for i, p in enumerate(ranked, 1)}
    just = sum(1 for p in cur if p["vround"] <= p["pick"])
    exact = sum(1 for p in cur if p["vround"] == p["pick"])
    print(
        f"<!-- FULL DOCKET (id full-docket): all {len(cur)} players in true "
        f"snake-draft order; League # = value rank; Move = true round vs the "
        f"previous edition; justified (true round <= drafted round) "
        f"{just}/{len(cur)}, priced exactly right {exact} -->"
    )
    prev_rd = None
    for p in sorted(cur, key=lambda q: q["pickno"]):
        brk = (
            ' class="rd-break"' if prev_rd is not None and p["pick"] != prev_rd else ""
        )
        prev_rd = p["pick"]
        m = po[(p["team"], p["pick"])]["vround"] - p["vround"]
        print(
            f'        <tr{brk}><td class="ctr num">#{p["pickno"]}</td>'
            f'<td class="ctr num">{p["pick"]}</td>'
            f'<td class="player">{pname(p)}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="ctr num">R{p["vround"]}</td>'
            f'<td class="ctr num">{arrow(m)}</td>'
            f'<td class="num">{gapspan(p)}</td>'
            f'<td class="ctr num">#{vrank[id(p)]}</td>'
            f'<td class="num">{disp(p)}</td>'
            f'<td class="num">{p["ab"]}</td>'
            f'<td class="num">{vspan(p["value"])}</td></tr>'
        )


def late_round_leaders(cur, min_round=6, top=10):
    """The late-round honour roll: players drafted in `min_round` or later,
    best first by the file's league rank (the authoritative order — display
    averages tie at three decimals where the underlying rates do not)."""
    late = [p for p in cur if p["pick"] >= min_round and p["ab"] > 0]
    return sorted(late, key=lambda q: q["rank"])[:top]


def dynasty_rows(cur):
    """The dynasty ledger: single-word surnames with 3+ players, best family
    average first. Family season average is the MEAN OF PLAYER AVERAGES (the
    house rule — family WEEKS are aggregate; do not mix the two)."""
    fams = {}
    for p in cur:
        sn = surname(p)
        if " " not in sn:
            fams.setdefault(sn, []).append(p)
    fams = {sn: ps for sn, ps in fams.items() if len(ps) >= 3}
    out = []
    for sn, ps in fams.items():
        live = [p for p in ps if p["ab"] > 0]
        if not live:
            continue
        best = max(live, key=lambda q: (q["avg"], q["ab"]))
        out.append(
            dict(
                sn=sn,
                n=len(ps),
                teams=len({p["team"] for p in ps}),
                ab=sum(p["ab"] for p in ps),
                famavg=statistics.mean(p["avg"] for p in live),
                best=best,
            )
        )
    return sorted(out, key=lambda r: -r["famavg"])


def emit_dynasty(c):
    cur = c["cur"]
    rows = dynasty_rows(cur)
    covered = sum(r["n"] for r in rows)
    print(
        f"<!-- DYNASTY (id dynasty): {len(rows)} families of 3+ cover {covered}/"
        f"{len(cur)} players; family average = mean of player averages -->"
    )
    for i, r in enumerate(rows, 1):
        cls = ' class="hl"' if i == 1 else (' class="lo"' if i == len(rows) else "")
        print(
            f'        <tr{cls}><td class="ctr num">{i}</td>'
            f'<td class="player">{r["sn"]}</td>'
            f'<td class="ctr num">{r["n"]}</td>'
            f'<td class="ctr num">{r["teams"]}</td>'
            f'<td class="num">{r["ab"]}</td>'
            f'<td class="player">{r["best"]["name"]} '
            f'<span class="muted">{disp(r["best"])}</span></td>'
            f'<td class="num big">{A(r["famavg"])}</td></tr>'
        )



def gender_family_rows(cur, female, min_n=2):
    """Best surnames on one side of the league — the dynasty ledger, split.

    Same arithmetic as `dynasty_rows` (family average is the MEAN OF PLAYER
    AVERAGES, the house rule) and deliberately the SAME gate on both sides: a
    household needs `min_n` confirmed members of that half to make its board.
    Two, not the ledger's three, because at three only four surnames in this
    league field enough women to appear, and a board built to celebrate one
    half should not be the thinner one by construction.

    Unconfirmed given names (`UNCONFIRMED_GIVEN`) are counted on neither side.
    """
    test = is_female if female else is_male
    fams = {}
    for p in cur:
        if not test(p):
            continue
        sn = surname(p)
        if " " in sn:
            continue
        fams.setdefault(sn, []).append(p)
    out = []
    for sn, ps in fams.items():
        live = [p for p in ps if p["ab"] > 0]
        if len(ps) < min_n or not live:
            continue
        out.append(
            dict(
                sn=sn,
                n=len(ps),
                teams=len({p["team"] for p in ps}),
                ab=sum(p["ab"] for p in ps),
                famavg=statistics.mean(p["avg"] for p in live),
                best=max(live, key=lambda q: (q["avg"], q["ab"])),
            )
        )
    return sorted(out, key=lambda r: -r["famavg"])


def women_board(cur, top=20):
    """The league table of confirmed women, best first by the file's league
    rank — the authoritative order, since display averages tie at three
    decimals where the rates underneath them do not. Returns (top N, all)."""
    women = sorted((p for p in cur if is_female(p)), key=lambda q: q["rank"])
    return women[:top], women


def _emit_family_side(c, female):
    """One half of the split dynasty board (three columns: rank, household
    with its meta line, family average)."""
    cur = c["cur"]
    rows = gender_family_rows(cur, female)
    side = "women" if female else "men"
    noun = "women" if female else "men"
    pool = [p for p in cur if (is_female if female else is_male)(p)]
    covered = sum(r["n"] for r in rows)
    print(
        f"<!-- DYNASTY {side.upper()} (id dynasty-{side}): {len(rows)} households "
        f"of 2+ {noun} cover {covered}/{len(pool)} confirmed {noun}; top "
        f"{rows[0]['sn']} {A(rows[0]['famavg'])}, bottom {rows[-1]['sn']} "
        f"{A(rows[-1]['famavg'])}; family average = mean of player averages -->"
    )
    for i, r in enumerate(rows, 1):
        cls = ' class="hl"' if i == 1 else (' class="lo"' if i == len(rows) else "")
        print(
            f'        <tr{cls}><td class="ctr num">{i}</td>'
            f'<td class="player">{r["sn"]}'
            f'<span class="fam-meta">{r["n"]} {noun} · {r["teams"]} '
            f'{"clubs" if r["teams"] > 1 else "club"} · {r["ab"]} AB · best '
            f'{display_name(r["best"]["name"])} {disp(r["best"])}</span></td>'
            f'<td class="num big">{A(r["famavg"])}</td></tr>'
        )


def emit_dynasty_men(c):
    _emit_family_side(c, female=False)


def emit_dynasty_women(c):
    _emit_family_side(c, female=True)


def emit_better_half(c):
    """The Better Half: the league table of confirmed women, top 20."""
    cur = c["cur"]
    top, women = women_board(cur)
    unconf = sorted((p for p in cur if is_unconfirmed(p)), key=lambda q: q["rank"])
    by_round = {rd: sum(1 for p in women if p["pick"] == rd) for rd in range(1, ROUNDS + 1)}
    first = min(women, key=lambda q: q["pickno"])
    tophalf = sum(1 for p in women if p["rank"] <= len(cur) // 2)
    clean = [p for p in women if p["co"] == 0 and p["ab"] > 0]
    leagueclean = sum(1 for p in cur if p["co"] == 0 and p["ab"] > 0)
    early = sum(n for rd, n in by_round.items() if rd <= 5)
    wab = sum(p["ab"] for p in women)
    print(
        f"<!-- BETTER HALF (id better-half): top {len(top)} of {len(women)} "
        f"confirmed women by league rank; cut line {top[-1]['name']} "
        f"{disp(top[-1])} at #{top[-1]['rank']}; leader {top[0]['name']} "
        f"{disp(top[0])} at #{top[0]['rank']}, drafted R{top[0]['pick']}; "
        f"{early} women drafted in rounds 1-5, the first off the board at "
        f"overall pick {first['pickno']} ({first['name']}, R{first['pick']}); "
        f"{by_round[ROUNDS]} of the {ROUNDS} round-{ROUNDS} picks are women; "
        f"women aggregate {A(sum(p['h'] - p['co'] for p in women) / wab)} on "
        f"{wab} AB, mean draft round "
        f"{statistics.mean(p['pick'] for p in women):.2f}; "
        f"{sum(p['h'] for p in women)} hits and {sum(p['co'] for p in women)} "
        f"caused outs between them; {tophalf} finish in the league's top half "
        f"(rank <= {len(cur) // 2}); {len(clean)} finish the season without "
        f"causing an out, out of {leagueclean} in the whole book; "
        f"{len(unconf)} given names unconfirmed and excluded -->"
    )
    for i, p in enumerate(top, 1):
        cls = ' class="hl"' if i <= 3 else ""
        print(
            f'        <tr{cls}><td class="ctr num">{i}</td>'
            f'<td class="ctr num">#{p["rank"]}</td>'
            f'<td class="player">{p["name"]}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="ctr num">R{p["pick"]}</td>'
            f'<td class="num big">{disp(p)}</td>'
            f'<td class="num">{p["ab"]}</td>'
            f'<td class="num">{p["co"]}</td></tr>'
        )


def emit_late_rounds(c):
    cur = c["cur"]
    lr = late_round_leaders(cur)
    picks_after = sum(1 for p in cur if p["pick"] >= 6)
    print(
        f"<!-- LATE ROUNDS (id late-rounds): the {len(lr)} best bats drafted "
        f"in round 6 or later, by league rank, out of {picks_after} such picks; "
        f"True Rd = where the season's value says they should have gone -->"
    )
    for p in lr:
        print(
            f'        <tr><td class="ctr num">#{p["rank"]}</td>'
            f'<td class="player">{pname(p)}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="ctr num">R{p["pick"]}</td>'
            f'<td class="ctr num">R{p["vround"]}</td>'
            f'<td class="num">{gapspan(p)}</td>'
            f'<td class="num big">{disp(p)}</td>'
            f'<td class="num">{p["ab"]}</td>'
            f'<td class="num">{vspan(p["value"])}</td></tr>'
        )


def divide_board(cur):
    """The Dewegeli Divide, recomputed honestly: the namesake is whichever
    first-round pick bats lowest, and the honour roll is every confirmed
    woman above that line. Both move; neither is ever asserted."""
    r1 = [p for p in cur if p["pick"] == 1 and p["ab"] > 0]
    namesake = min(r1, key=lambda q: q["avg"])
    roll = sorted(
        (p for p in cur if is_female(p) and p["ab"] > 0 and p["avg"] > namesake["avg"]),
        key=lambda q: -q["avg"],
    )
    runner_up = min((p for p in r1 if p is not namesake), key=lambda q: q["avg"])
    return namesake, roll, runner_up


def emit_divide(c):
    cur = c["cur"]
    namesake, roll, runner_up = divide_board(cur)
    print(
        f"<!-- DIVIDE (id dewegeli-divide): the line sits at the league's "
        f"lowest first-round average — {namesake['name']} {disp(namesake)} on "
        f"{namesake['ab']} AB, rank #{namesake['rank']}; next-lowest first "
        f"rounder {runner_up['name']} {disp(runner_up)}; {len(roll)} confirmed "
        f"women bat above the line -->"
    )
    for p in roll:
        print(
            f'        <tr class="hl"><td class="ctr num">#{p["rank"]}</td>'
            f'<td class="player">{p["name"]}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="ctr num">R{p["pick"]}</td>'
            f'<td class="num big">{disp(p)}</td>'
            f'<td class="num">{p["ab"]}</td></tr>'
        )
    print(
        f'        <tr class="wline"><td colspan="6">The Dewegeli Divide · '
        f'{namesake["name"].split(", ")[1]} {namesake["name"].split(",")[0]}\'s '
        f'{disp(namesake)}</td></tr>'
    )
    print(
        f'        <tr class="bench"><td class="ctr num">#{namesake["rank"]}</td>'
        f'<td class="player">{namesake["name"]} <span class="muted">· SS · '
        f'draws the Divide</span></td>'
        f'<td class="team-name">{team_label(namesake["team"])}</td>'
        f'<td class="ctr num">R{namesake["pick"]}</td>'
        f'<td class="num">{disp(namesake)}</td>'
        f'<td class="num">{namesake["ab"]}</td></tr>'
    )


TEAM_RECORD_CATS = {"team_best", "team_worst", "team_co"}


def emit_records_board(c):
    print("<!-- RECORDS (id records): the weekly record book + game records -->")
    status_html = {
        "FELL": '<span class="zpos">NEW RECORD</span>',
        "MATCHED": '<span class="zpos">MATCHED</span>',
        "NEAR MISS": '<span class="zneg">NEAR MISS</span>',
        "HELD": '<span class="muted">HELD</span>',
        "—": '<span class="muted">—</span>',
    }
    for row in c["report"]:
        names = "; ".join(
            (team_label(h) if row["cat"] in TEAM_RECORD_CATS else h)
            + f' <span class="muted">({lab})</span>'
            for h, lab in row["holders"]
        )
        extra = ""
        if row["status"] == "FELL":
            prev_who, _, prev_val = row["prev"].rpartition(" (")
            prev_who = (
                team_label(prev_who)
                if row["cat"] in TEAM_RECORD_CATS
                else prev_who
            )
            extra = f' <span class="muted">breaks {prev_who} ({prev_val}</span>'
        elif row["status"] in ("NEAR MISS", "MATCHED") and row["last"] is not None:
            who = ", ".join(
                team_label(h) if row["cat"] in TEAM_RECORD_CATS else h
                for h, _ in row["last_holders"]
            )
            extra = (
                f' <span class="muted">this {c["pnoun"]}: '
                f'{fmtv(row["cat"], row["last"])} ({who})</span>'
            )
        print(
            f'        <tr><td class="player">{row["title"]}</td>'
            f'<td class="num big">{fmtv(row["cat"], row["value"])}</td>'
            f"<td>{names}</td><td>{status_html[row['status']]}{extra}</td></tr>"
        )

    def gcell(g):
        return (
            f'{team_label(g["a"])} {g["sa"]}–{g["sb"]} {team_label(g["b"])} '
            f'<span class="muted">({g["d"].strftime("%b")} {g["d"].day})</span>'
        )

    gr = c["gr"]
    best_run = max(c["lws"].values(), key=lambda v: v[0])
    runners = sorted(t for t, v in c["lws"].items() if v[0] == best_run[0])
    run_names = "; ".join(
        f'{team_label(t)} <span class="muted">'
        f'({c["lws"][t][1].strftime("%b")} {c["lws"][t][1].day} – '
        f'{c["lws"][t][2].strftime("%b")} {c["lws"][t][2].day})</span>'
        for t in runners
    )
    print("\n<!-- GAME RECORDS rows (same table): computed from every completed game -->")
    for title, val, names in (
        ("Biggest win margin", f'+{abs(gr["margin"][0]["sa"] - gr["margin"][0]["sb"])}',
         "; ".join(gcell(g) for g in gr["margin"])),
        ("Highest-scoring game", f'{gr["highest"][0]["sa"] + gr["highest"][0]["sb"]} runs',
         "; ".join(gcell(g) for g in gr["highest"])),
        ("Lowest-scoring game", f'{gr["lowest"][0]["sa"] + gr["lowest"][0]["sb"]} runs',
         "; ".join(gcell(g) for g in gr["lowest"])),
        ("Longest win streak", f'{best_run[0]} games', run_names),
    ):
        print(
            f'        <tr><td class="player">{title}</td>'
            f'<td class="num big">{val}</td><td>{names}</td>'
            f'<td><span class="muted">—</span></td></tr>'
        )


def emit_watch(c):
    if not c["nd"]:
        print("<!-- WATCH (id watch): schedule lists no future games -->")
        return
    nd = c["nd"]
    print(
        f'<!-- WATCH (id watch): the next slate, {nd.strftime("%B")} {nd.day} -->'
    )
    for g in c["games"]:
        if g["d"] == nd:
            print(
                f'        <tr><td class="num">{g["time"].replace(" PM", "")}</td>'
                f'<td class="ctr"><span class="muted">{g["field"]}</span></td>'
                f'<td class="player">{team_label(g["a"])}</td>'
                f'<td class="ctr"><span class="muted">vs</span></td>'
                f'<td class="player">{team_label(g["b"])}</td></tr>'
            )


# The bracket the league posted (cpsoftball.com/playoffs.php): twelve clubs,
# double elimination, twenty-two games over August 21-22. [game, home slot,
# away slot, day]; s5 = the fifth seed, w4 / l4 = the winner / loser of Game 4.
# Every slot points at a lower-numbered game, so one forward pass resolves the
# whole thing. This is the same table playoffs.html carries in its BR constant
# and is re-verified against the league's page each time the island is cut.
PLAYOFF_BRACKET = [
    (1, "s5", "s12", 21), (2, "s6", "s11", 21), (3, "s7", "s10", 21), (4, "s8", "s9", 21),
    (5, "s1", "w4", 21), (6, "s2", "w3", 21), (7, "s3", "w2", 21), (8, "s4", "w1", 21),
    (9, "l1", "l4", 21), (10, "l2", "l3", 21),
    (11, "l5", "w9", 22), (12, "l6", "w10", 22),
    (13, "w5", "w6", 22), (14, "w7", "w8", 22),
    (15, "w13", "w14", 22),
    (16, "l7", "w11", 22), (17, "l8", "w12", 22),
    (18, "w16", "w17", 22),
    (19, "l13", "w18", 22), (20, "l14", "w19", 22),
    (21, "w20", "l15", 22),
    (22, "w15", "w21", 22),
]


# ------------------------------------------------------------- contest desk
#
# Playoff Prediction Brackets (playoffs.html) runs a prize contest: readers fill
# in the league's twenty-two game bracket and mail the entry to the desk FROM
# THEIR OWN ADDRESS, which is what verifies them — a magic link would only prove
# somebody controls an inbox, whereas mail from Shem Hammon proves it is Shem,
# because the desk knows Shem. Accepted entries are pasted into MMDD-brackets.csv
# and this desk validates, resolves and (once results land) scores them.
#
# Nothing here touches a network: the CSV is the inbox and the island is the page.

# The address entries are mailed to (owner's, supplied 2026-08-19). It ships in
# the island and the page assembles the mailto from it in JS, so the address is
# not sitting in the markup for scrapers to harvest.
ENTRY_EMAIL = "curtis@yggr.xyz"
PRIZE_SATS = 75000
PRIZE_SPONSOR = "yggr"
ENTRY_DEADLINE = "first pitch, Friday August 21"


def display_name(name):
    """"Hammon, Shem" -> "Shem Hammon".

    The comma is the split and whitespace never is: surnames in this league run
    to two words ("Dockstader Ephraims, Daniel") and given names to two tokens
    ("Timpson, Jason W").
    """
    if ", " in name:
        last, given = name.split(", ", 1)
        return f"{given} {last}"
    return name


def _slot_value(slot, occ, seed_slug):
    """Resolve one bracket slot: s5 = the fifth seed, w4 / l4 = G4's winner/loser."""
    if slot[0] == "s":
        return seed_slug[slot]
    g = occ[int(slot[1:])]
    return g["w"] if slot[0] == "w" else g["l"]


def resolve_code(code, seed_slug):
    """Run a 22-digit bracket code through the posted topology, one forward pass.

    Digits are the page's own codec: 1 = the home slot's club advances, 2 = the
    away slot's, 0 = not picked. Returns {game: {h, a, w, l}} with w/l None
    wherever the code stops. This mirrors resolveBracket() in playoffs.html and
    the two are checked against each other by the jsdom suite — the arithmetic
    that pays out a prize should not exist in only one language.
    """
    occ = {}
    for no, home, away, _day in PLAYOFF_BRACKET:
        h = _slot_value(home, occ, seed_slug)
        a = _slot_value(away, occ, seed_slug)
        d = code[no - 1]
        w = l = None
        if h and a and d in "12":
            w, l = (h, a) if d == "1" else (a, h)
        occ[no] = dict(h=h, a=a, w=w, l=l)
    return occ


def seed_slugs(st):
    """{"s1": "jeremy", ...} from the standings, which ARE the posted seeding."""
    return {f"s{s['rank']}": cap_slug(s["team"]) for s in st}


def load_brackets(path, st, cur):
    """Load contest entries: name,club,code,received.

    name      the player, spelled as the roster spells them ("Shem Hammon")
    club      the captain slug of the club they play for ("sefton")
    code      22 digits, one per bracket game: 1 = home club, 2 = away club
    received  when the entry mail arrived, ISO 8601 — this is the clock the
              deadline is read on and the last tiebreak is settled on

    Every field is checked: a COMPLETE code (all twenty-two games called), a
    real rostered player, the club that player actually plays for, and one entry
    per player. A bad row exits hard with the row named. These entries carry a
    prize; a silently mangled one is not an option.
    """
    roster = {display_name(p["name"]): cap_slug(p["team"]) for p in cur}
    # The page resolves a TYPED name against the roster ignoring case and
    # doubled spaces, and mails the roster's own spelling. This loader matches
    # the same way and stores the canonical spelling, so the two ends of the
    # contest never disagree about whether two strings are the same person.
    canon = {" ".join(k.lower().split()): k for k in roster}
    ss = seed_slugs(st)
    entries, seen = [], {}
    with open(path, newline="") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            who = r["name"].strip()
            where = r["club"].strip()
            code = r["code"].strip()
            at = r["received"].strip()
            tag = f"{path} line {i} ({who!r})"
            who = canon.get(" ".join(who.lower().split()), who)
            if who not in roster:
                near = difflib.get_close_matches(who, roster, n=3, cutoff=0.6)
                hint = f" — did you mean {' / '.join(near)}?" if near else ""
                raise AssertionError(f"{tag}: not a rostered player{hint}")
            assert roster[who] == where, (
                f"{tag}: entered under {where!r} but plays for {roster[who]!r}"
            )
            assert who not in seen, f"{tag}: already entered at line {seen[who]}"
            seen[who] = i
            assert len(code) == 22 and all(d in "12" for d in code), (
                f"{tag}: code must be 22 digits of 1/2 — every game called, got {code!r}"
            )
            occ = resolve_code(code, ss)
            assert occ[22]["w"], f"{tag}: code does not resolve to a champion"
            entries.append(
                dict(
                    name=who,
                    club=where,
                    code=code,
                    received=datetime.datetime.fromisoformat(at),
                    champ=occ[22]["w"],
                )
            )
    entries.sort(key=lambda e: e["received"])
    return entries


def load_playoff_results(path, st):
    """Load played playoff games: game,winner — any subset of 1..22, any order.

    Returns the same 22-digit codec the entries use, with 0 for games not yet
    played. **This is the schema question CLAUDE.md left open:** playoff results
    ride their own small file keyed by BRACKET GAME NUMBER, because
    MMDD-schedule.csv is a date/field slate with no game-number column and the
    bracket is not a slate. Winners are raw team names, as everywhere else in
    the CSVs.
    """
    ss = seed_slugs(st)
    want = {}
    with open(path, newline="") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            no = int(r["game"])
            assert 1 <= no <= 22, f"{path} line {i}: game {no} is not in the bracket"
            assert no not in want, f"{path} line {i}: game {no} listed twice"
            want[no] = cap_slug(r["winner"].strip())
    digits = ["0"] * 22
    occ = {}
    for no, home, away, _day in PLAYOFF_BRACKET:
        h = _slot_value(home, occ, ss)
        a = _slot_value(away, occ, ss)
        w = l = None
        if no in want:
            assert h and a, (
                f"{path}: G{no} has a result but its participants are not decided — "
                "an earlier game is missing"
            )
            assert want[no] in (h, a), (
                f"{path}: G{no} winner {want[no]!r} did not play in it ({h} v {a})"
            )
            w = want[no]
            l = a if w == h else h
            digits[no - 1] = "1" if w == h else "2"
        occ[no] = dict(h=h, a=a, w=w, l=l)
    return "".join(digits)


def score_entries(entries, res_code, st):
    """Flat scoring — the owner's rule, 2026-08-18: one point per game whose
    winner the entry called, over the games actually played so far.

    A game only scores if the entry named the club that really won it. An entry
    whose bracket has a different club in that game cannot be right about it,
    which is what makes a wrong early pick cost more than a single point without
    any weighting having to be invented.

    Ties go to WHOEVER ENTERED FIRST — the owner's rule, 2026-08-19, and the
    only tiebreak there is. An earlier draft also gave precedence to whoever
    called the champion; that was dropped so the rule the page prints is the
    whole rule, because a prize that pays real money should not be settled by a
    step nobody was told about. The clock is the `received` timestamp on the
    entry mail, which is the same clock the deadline is read on.
    """
    ss = seed_slugs(st)
    truth = resolve_code(res_code, ss)
    played = [no for no in range(1, 23) if truth[no]["w"]]
    for e in entries:
        occ = resolve_code(e["code"], ss)
        e["score"] = sum(1 for no in played if occ[no]["w"] == truth[no]["w"])
        e["played"] = len(played)
    entries.sort(key=lambda e: (-e["score"], e["received"]))
    return entries


def emit_playoff_seeds(c):
    """The FINAL island: the twelve posted playoff seeds, nothing enumerated.

    Cut for the first time 2026-08-18, once the August 14 finale was in the
    book and the seeding stopped being a question. The league's own
    playoffs.php was read the same day and its posted order matches the
    standings rank column exactly — including the two pairs that finished
    level on points, which the league broke itself. The desk does not print
    WHY it broke them: the tiebreaker is still unpublished, and with the seeds
    posted there is nothing left to guess.

    Feeds playoffs.html, whose UI is script-built from this data. Captain
    labels and slugs ONLY — raw team names never reach any page, this island
    included.
    """
    st = c["st"]
    seeds = [s["rank"] for s in st]
    assert seeds == list(range(1, len(st) + 1)), f"standings are not seed-ordered: {seeds}"
    gp = {s["gp"] for s in st}
    assert len(gp) == 1, f"clubs have played unequal games: {sorted(gp)}"
    left = [g for g in c["games"] if g["status"] == "SCHEDULED"]
    assert not left, f"{len(left)} games still unplayed — the seeds are not final"

    # The bracket ships WITH the seeds so the topology has one home. Check it
    # before it goes: every seed walks in exactly once, and every winner/loser
    # reference points at a lower-numbered game — which is what lets the page
    # resolve the whole prophecy in a single forward pass.
    seats = []
    for no, home, away, _day in PLAYOFF_BRACKET:
        for slot in (home, away):
            if slot[0] == "s":
                seats.append(int(slot[1:]))
            else:
                assert int(slot[1:]) < no, f"G{no} refers forward to {slot}"
    assert sorted(seats) == list(range(1, len(st) + 1)), f"bracket seats {sorted(seats)}"

    n_played = sum(1 for d in (c.get("results") or "") if d != "0")
    print(
        f"<!-- PLAYOFFS (id playoffs): season complete at {gp.pop()} games — "
        f"final seeding island, {len(PLAYOFF_BRACKET)} bracket games Aug 21-22, "
        f"{len(c.get('brackets') or [])} contest entries, {n_played} results in -->"
    )
    entries = c.get("brackets") or []
    res_code = c.get("results") or "0" * 22
    if any(d != "0" for d in res_code):
        score_entries(entries, res_code, st)
    seat = {cap_slug(s["team"]): s["rank"] for s in st}
    data = dict(
        final=True,
        asof=c["dcur"].strftime("%B ") + str(c["dcur"].day),
        days="August 21\u201322",
        bracket=[list(g) for g in PLAYOFF_BRACKET],
        # the contest: prize, where entries are mailed, and when they close
        prize=dict(
            sats=PRIZE_SATS,
            sponsor=PRIZE_SPONSOR,
            to=ENTRY_EMAIL,
            deadline=ENTRY_DEADLINE,
        ),
        # the 144 rostered players, club by club in seed order — the entry
        # panel picks from this, so an entry can only name a real player
        roster=[
            dict(n=display_name(p["name"]), c=cap_slug(p["team"]))
            for p in sorted(
                c["cur"],
                key=lambda p: (seat[cap_slug(p["team"])], display_name(p["name"])),
            )
        ],
        # verified entries, in the order the desk received them
        entries=[
            dict(
                n=e["name"],
                c=e["club"],
                k=e["code"],
                r=e["received"].isoformat(timespec="minutes"),
                **({"s": e["score"], "p": e["played"]} if "score" in e else {}),
            )
            for e in entries
        ],
        results=res_code,
        teams=[
            dict(
                s=cap_slug(s["team"]),
                label=team_label(s["team"]),
                seed=s["rank"],
                w=s["w"],
                l=s["l"],
                t=s["t"],
                pts=2 * s["w"] + s["t"],
                pf=s["pf"],
                pa=s["pa"],
                diff=s["pf"] - s["pa"],
            )
            for s in st
        ],
    )
    print("<!-- machine data island (captain labels and slugs only) -->")
    print(
        f'        <script type="application/json" id="machine-data">{json.dumps(data, separators=(",", ":"))}</script>'
    )


def emit_playoffs(c):
    """The playoff desk emitter — the machine-data island for playoffs.html.

    Two eras, one emitter. While a final slate is still unplayed it emits the
    clinch-board rows (the paper's static table) and a FUTURES island: the
    exact enumeration bounds the bracket page re-derived live while
    readers wired the last afternoon, and checked against at start-up.

    Once the season is complete the seeding stops being a question, the
    speculative half of the desk goes quiet, and emit_playoff_seeds cuts the
    FINAL island instead. Owner-authorized page script (2026-08-14); see
    CLAUDE.md.
    """
    fut = playoff_futures(c["st"], c["games"])
    if not fut:
        return emit_playoff_seeds(c)
    total = fut.total
    print(
        f"<!-- PLAYOFFS (id playoffs): the playoff desk — {len(fut.slate)} "
        f"unplayed games, {total:,} futures -->"
    )
    print("<!-- clinch rows: now, club, record, best/worst finish, futures missing a bye -->")
    for r, s in zip(fut.rows, c["st"]):
        assert r.team == s["team"]
        mo, mp = total - r.bye_opt, total - r.bye_pes
        if r.bye_opt == 0:
            miss = '<span class="muted">all of them</span>'
        elif mo == mp:
            miss = f"{mo:,}"
        else:
            miss = f"{mo:,}–{mp:,}"
        print(
            f'        <tr><td class="ctr num">{s["rank"]}</td>'
            f'<td class="player">{team_label(r.team)}</td>'
            f'<td class="num">{s["w"]}-{s["l"]}-{s["t"]}</td>'
            f'<td class="ctr num">{r.best}</td>'
            f'<td class="ctr num">{r.worst}</td>'
            f'<td class="num">{miss}</td></tr>'
        )
    data = dict(
        asof=c["dcur"].strftime("%B ") + str(c["dcur"].day),
        slate=fut.slate[0]["d"].strftime("%B ") + str(fut.slate[0]["d"].day),
        gp_final=fut.final_gp,
        total=total,
        teams=[
            dict(
                s=cap_slug(r.team),
                label=team_label(r.team),
                w=s["w"],
                l=s["l"],
                t=s["t"],
                rank=s["rank"],
                best=r.best,
                worst=r.worst,
                mo=total - r.bye_opt,
                mp=total - r.bye_pes,
            )
            for r, s in zip(fut.rows, c["st"])
        ],
        games=[
            dict(
                time=g["time"].replace(" PM", ""),
                field=g["field"],
                a=cap_slug(g["a"]),
                b=cap_slug(g["b"]),
            )
            for g in fut.slate
        ],
    )
    print("<!-- machine data island (captain labels and slugs only; spliced into BOTH pages) -->")
    print(
        f'        <script type="application/json" id="machine-data">{json.dumps(data, separators=(",", ":"))}</script>'
    )


# Page order for the 2026-08-07 edition (The Double Issue — the league
# posted the Jul 31 and Aug 7 afternoons as one snapshot), amended
# 2026-08-14 with the PLAYOFFS extra at the very top of the page (owner
# request — gameday scenarios + the interactive bracket; see CLAUDE.md).
# The hand-written front of book (notice, seventeen, thousand-club,
# dewegeli-divide) sits above CROWN and carries no emitters, per the
# bulletin precedent. INVOICE recurs — the statement re-addresses itself
# to whoever leads the standings, which is the whole gag; DEBITS recurs
# while the caused-out epidemic lasts. ALIBI stays retired (emit_alibi
# defined in case the verdict ever flips).
def emit_photo_finish(c):
    """Cover module (id photo-finish, debuted 2026-08-14): the closest crown in
    league history, drawn as a finish-line photo.

    The axis is the paper's own metric — hits back at the chaser's OWN volume —
    so it is zero-based and honest: the tape sits at the leader, and every
    marker is placed by computed geometry, never by eye. Emits the SVG, the
    gap annotation between first and second, and the fallback table beneath.
    Captain labels only, per the house rule; a per-lane <title> repeats them."""
    racers = race_top(c["cur"], 4)
    span = max(0.5, math.ceil(max(b for _, b in racers) * 2) / 2)
    LEFT, TAPE, TOP, LANE = 236, 660, 78, 54
    height = TOP + LANE * len(racers) + 34

    def x(back):
        return round(TAPE - (back / span) * (TAPE - LEFT), 1)

    lead, lead_back = racers[0]
    chase, chase_back = racers[1]
    print(
        f'<div class="finish-scroll">\n'
        f'<svg class="finish-svg" viewBox="0 0 720 {height}" width="720" '
        f'height="{height}" role="img" aria-label="The batting race at the tape: '
        f'{lead["name"]} wins the crown by {chase_back:.1f} hits over '
        f'{chase["name"]}, with the field measured in hits behind the leader '
        f'at each chaser\'s own volume.">'
    )
    print(f'  <text class="fn-axhead" x="{LEFT}" y="30">HITS BEHIND, AT OWN VOLUME</text>')
    print(f'  <text class="fn-tapelab" x="{TAPE}" y="30">THE TAPE</text>')
    # axis ticks, every half hit, drawn right-to-left from the tape
    t = 0.0
    while t <= span + 1e-9:
        tx = x(t)
        print(f'  <line class="fn-tick" x1="{tx}" y1="40" x2="{tx}" y2="{TOP + LANE * len(racers) + 4}" />')
        lab = "0" if t == 0 else f"{t:g}"
        print(f'  <text class="fn-ticklab" x="{tx}" y="{TOP + LANE * len(racers) + 24}">{lab}</text>')
        t += 0.5
    print(f'  <line class="fn-tape" x1="{TAPE}" y1="40" x2="{TAPE}" y2="{TOP + LANE * len(racers) + 4}" />')
    for i, (p, back) in enumerate(racers):
        y = TOP + LANE * i
        px = x(back)
        ss = " · SS" if is_ss(p) else ""
        club = team_label(p["team"])
        print(f'  <g class="fn-lane{" lead" if i == 0 else ""}">')
        print(
            f'    <title>{i + 1}. {p["name"]} — {club}, round {p["pick"]}, '
            f'{disp(p)} on {p["ab"]} at-bats, '
            f'{"the crown" if i == 0 else f"{back:.1f} hits back"}</title>'
        )
        print(f'    <text class="fn-rank" x="18" y="{y + 6}">{i + 1}</text>')
        print(f'    <text class="fn-name" x="44" y="{y + 1}">{p["name"]}</text>')
        print(f'    <text class="fn-meta" x="44" y="{y + 18}">{club} · R{p["pick"]}{ss} · {p["ab"]} AB</text>')
        print(f'    <line class="fn-track" x1="{x(span)}" y1="{y}" x2="{TAPE}" y2="{y}" />')
        print(f'    <circle class="fn-dot" cx="{px}" cy="{y}" r="7" />')
        anchor = "end" if i == 0 else "start"
        dx = -16 if i == 0 else 16
        print(f'    <text class="fn-avg" x="{px + dx}" y="{y + 5}" text-anchor="{anchor}">{disp(p)}</text>')
        print("  </g>")
    # the margin itself: a bracket between first and second
    gy = TOP + LANE - 18
    x1, x2 = x(chase_back), x(lead_back)
    print(
        f'  <g class="fn-gap">\n'
        f'    <line class="fn-gapline" x1="{x1}" y1="{gy}" x2="{x2}" y2="{gy}" />\n'
        f'    <line class="fn-gapline" x1="{x1}" y1="{gy - 5}" x2="{x1}" y2="{gy + 5}" />\n'
        f'    <line class="fn-gapline" x1="{x2}" y1="{gy - 5}" x2="{x2}" y2="{gy + 5}" />\n'
        f'    <text class="fn-gaplab" x="{round((x1 + x2) / 2, 1)}" y="{gy - 11}">'
        f'{chase_back:.1f} hits</text>\n'
        f"  </g>"
    )
    print("</svg>\n</div>")
    print("\n<!-- PHOTO FINISH fallback table (id race-tape) -->")
    for i, (p, back) in enumerate(racers, 1):
        r = c["bykey"][(p["team"], p["pick"])]
        wl = week_line(r, html=True) if r["dab"] else '<span class="muted">did not bat</span>'
        b = '<span class="muted">—</span>' if back == 0 else f"{back:.1f}"
        print(
            f'        <tr{" class=" + chr(34) + "hl" + chr(34) if i == 1 else ""}>'
            f'<td class="ctr num">{i}</td><td class="player">{p["name"]}</td>'
            f'<td class="team-name">{team_label(p["team"])}</td>'
            f'<td class="num">R{p["pick"]}</td>'
            f'<td class="num{" big" if i == 1 else ""}">{disp(p)}</td>'
            f'<td class="num">{p["ab"]}</td><td class="num">{wl}</td>'
            f'<td class="num">{b}</td></tr>'
        )


AFTERNOON_EMITTERS = [
    ("PLAYOFFS", emit_playoffs),
    ("PHOTO FINISH", emit_photo_finish),
    ("CROWN", emit_crown),
    ("SCOREBOARD", emit_scoreboard),
    ("WEEKLIES", emit_weeklies),
    ("RECORDS", emit_records_board),
    ("DEBITS", emit_debits),
    ("REBOUND", emit_rebound),
    ("CLUBHOUSE", emit_clubhouse),
    ("STANDINGS", emit_standings_afternoon),
    ("INVOICE", emit_invoice),
    ("GAUNTLET", emit_gauntlet),
    ("VALUE DESK", emit_value_desk),
    ("DIVIDE", emit_divide),
    ("DYNASTY", emit_dynasty),
    ("DYNASTY MEN", emit_dynasty_men),
    ("DYNASTY WOMEN", emit_dynasty_women),
    ("BETTER HALF", emit_better_half),
    ("LATE ROUNDS", emit_late_rounds),
    ("FULL DOCKET", emit_full_docket),
    ("ARCS SVG", emit_arcs_svg),
    ("ARCS TABLE", emit_arcs_table),
    ("WATCH", emit_watch),
]


def html_afternoon(snaps, games, st, prev_st, brackets=None, results=None):
    """Emit every Afternoon Final module, page order, one emitter per module."""
    for _, s in snaps:
        enrich(s)
    dcur, cur = snaps[-1]
    dprev, prev = snaps[-2]
    rows = period_rows(prev, cur)
    hae(rows)
    tw = team_week_rows(prev, cur, st, prev_st)
    nd, nby = next_afternoon(games, dcur)
    gpast = [g for g in games if g["d"] <= dcur]
    # The period is usually one game day ("the afternoon of August 7") but the
    # league can post two weeks at once (first case: 0807 = Jul 31 + Aug 7).
    # Every emitter that names the period in visible text reads these.
    pdays = sorted({g["d"] for g in completed(games) if dprev < g["d"] <= dcur})
    pnoun = "afternoon" if len(pdays) <= 1 else "fortnight"
    pdates = " and ".join(f'{d.strftime("%B")} {d.day}' for d in pdays)
    ctx = dict(
        snaps=snaps,
        dcur=dcur,
        dprev=dprev,
        cur=cur,
        prev=prev,
        rows=rows,
        bykey={(r["team"], r["pick"]): r for r in rows},
        tw=tw,
        games=games,
        gpast=gpast,
        afternoon=[g for g in completed(games) if dprev < g["d"] <= dcur],
        pnoun=pnoun,
        pdates=pdates,
        st=st,
        prev_st=prev_st,
        ranks={s["team"]: s["rank"] for s in prev_st} if prev_st else {},
        gb=games_back(st),
        stk=streaks(gpast),
        series=team_series(snaps),
        glyphs=form_glyphs(snaps),
        nd=nd,
        nby=nby,
        aw=afternoon_awards(rows, tw),
        report=records_report(snaps),
        gr=game_records(gpast),
        lws=longest_win_streaks(gpast),
        brackets=brackets,
        results=results,
    )
    for banner, fn in AFTERNOON_EMITTERS:
        print(f"\n\n<!-- ══════════════════ {banner} ══════════════════ -->")
        fn(ctx)


# ---------------------------------------------------------------- compare


def compare(
    prev,
    cur,
    renames,
    min_old_ab=8,
    min_new_ab=15,
    min_dab=6,
    min_perfect=4,
    min_swing=4,
):
    rows = period_rows(prev, cur)
    po = {(p["team"], p["pick"]): p for p in prev}
    pn = {(p["team"], p["pick"]): p for p in cur}
    print(f"\n{'=' * 72}\n=== COMPARISON: prev -> current ===\n{'=' * 72}")
    print(f"join OK: {len(po)}/{len(pn)} matched on (team, pick)")
    for old, new, team, pick in renames:
        print(
            f"RENAME: '{old}' -> '{new}' ({team}, pick {pick}) — same player, name corrected"
        )

    # ---- the week as its own box score (the front of book reads from here)
    oab = sum(r["o"]["ab"] for r in rows)
    nab = sum(r["n"]["ab"] for r in rows)
    oh = sum(r["o"]["h"] for r in rows)
    nh = sum(r["n"]["h"] for r in rows)
    oco = sum(r["o"]["co"] for r in rows)
    nco = sum(r["n"]["co"] for r in rows)
    dab, dh, dco = nab - oab, nh - oh, nco - oco
    wrate = (dh - dco) / dab
    played = [r for r in rows if r["dab"] > 0]
    sat = [r for r in rows if r["dab"] == 0]
    dabs = sorted(r["dab"] for r in played)
    ocorate, ncorate = oco / oab, dco / dab
    print("\n--- THE WEEK (league box score) ---")
    print(
        f"  AB {dab:,} | H {dh:,} | CO {dco} | raw {A(dh / dab)} | adjusted {A(wrate)}"
    )
    print(
        f"  season adj {A((oh - oco) / oab)} -> {A((nh - nco) / nab)}  "
        f"(league AB {oab:,} -> {nab:,})"
    )
    print(
        f"  CO rate {ncorate:.3f}/AB this week vs {ocorate:.3f} season-to-date "
        f"({(ncorate / ocorate - 1) * 100:+.0f}%)"
    )
    print(
        f"  {dco} of {nco} season caused outs ({dco / nco:.0%}) on {dab:,} of "
        f"{nab:,} at-bats ({dab / nab:.0%})"
    )
    print(
        f"  batted {len(played)}/{len(rows)} | sat {len(sat)} | period AB median "
        f"{statistics.median(dabs):.0f}, range {dabs[0]}–{dabs[-1]}"
    )
    print(
        f"  beat the week's league rate: {sum(1 for r in played if r['rate'] > wrate)}/{len(played)}"
    )

    perfect = sorted(
        (r for r in rows if r["dab"] >= min_perfect and r["rate"] == 1.0),
        key=lambda r: -r["dab"],
    )
    print(f"\n--- PERFECT WEEKS (rate 1.000, dAB >= {min_perfect}; {len(perfect)}) ---")
    for r in perfect:
        print(
            f"  {r['name']:30s} {week_line(r):14s} season {A(r['o']['avg'])} -> {A(r['n']['avg'])}"
            f"  rank #{r['o']['rank']} -> #{r['n']['rank']}  ({r['team']})"
        )

    hitless = sorted(
        (
            r
            for r in rows
            if r["dab"] >= min_perfect and r["rate"] is not None and r["rate"] <= 0
        ),
        key=lambda r: (r["rate"], -r["dab"]),
    )
    print(
        f"\n--- HITLESS WEEKS (rate <= .000, dAB >= {min_perfect}; {len(hitless)}) ---"
    )
    for r in hitless:
        print(
            f"  {r['name']:30s} {week_line(r):14s} season {A(r['o']['avg'])} -> {A(r['n']['avg'])}"
            f"  rank #{r['o']['rank']} -> #{r['n']['rank']}  ({r['team']})"
        )

    sw = sorted(
        (r for r in rows if r["dab"] >= min_swing and r["swing"] is not None),
        key=lambda r: r["swing"],
    )

    def swingline(r):
        return (
            f"{r['name']:30s} {week_line(r):14s} {A(r['rate'])}  was {A(r['o']['avg'])} "
            f"on {r['o']['ab']:2d} AB  swing {r['swing']:+.3f}  now {A(r['n']['avg'])}  "
            f"#{r['o']['rank']} -> #{r['n']['rank']}  ({r['team']})"
        )

    print(
        f"\n--- WEEK SWINGS (week rate − own season line at the prev snapshot; "
        f"dAB >= {min_swing}; {len(sw)} qualify; "
        f"{sum(1 for r in sw if r['swing'] <= -0.300)} fell 300+ points, "
        f"{sum(1 for r in sw if r['swing'] >= 0.300)} rose 300+; top 12 each) ---"
    )
    for r in sw[:12]:
        print(f"  FELL {swingline(r)}")
    for r in sw[:-13:-1]:
        print(f"  ROSE {swingline(r)}")
    climb, fall = max(rows, key=lambda r: r["drank"]), min(rows, key=lambda r: r["drank"])
    print(
        f"  biggest rank climb: {climb['name']} #{climb['o']['rank']} -> #{climb['n']['rank']} "
        f"(▲{climb['drank']})  |  biggest rank fall: {fall['name']} #{fall['o']['rank']} -> "
        f"#{fall['n']['rank']} (▼{-fall['drank']})"
    )

    pq = sorted((r for r in rows if r["dab"] >= min_dab), key=lambda r: -r["rate"])
    k = min(10, len(pq) // 2)  # never print the same player as both HOT and COLD
    print(
        f"\n--- PERIOD BATS ((dH-dCO)/dAB, dAB >= {min_dab}; {len(pq)} of {len(played)} "
        f"batters qualify; top {k} each) ---"
    )
    for r in pq[:k]:
        print(
            f"  HOT  {r['name']:30s} {A(r['rate'])} on {r['dab']:2d} period AB  "
            f"season {A(r['o']['avg'])} -> {A(r['n']['avg'])}  ({r['team']})"
        )
    for r in reversed(pq[-k:]):
        print(
            f"  COLD {r['name']:30s} {A(r['rate'])} on {r['dab']:2d} period AB  "
            f"season {A(r['o']['avg'])} -> {A(r['n']['avg'])}  ({r['team']})"
        )
    rq = sorted((r for r in rows if r["dab"] >= 10), key=lambda r: -r["rate"])
    if rq:
        print(
            f"  records gate (dAB >= 10; {len(rq)} qualify): "
            f"hottest {rq[0]['name']} {A(rq[0]['rate'])} ({rq[0]['dab']}) | "
            f"coldest {rq[-1]['name']} {A(rq[-1]['rate'])} ({rq[-1]['dab']})"
        )

    co_up = sorted((r for r in rows if r["dco"] > 0), key=lambda r: (-r["dco"], -r["dab"]))
    tco, tdab = {}, {}
    for r in rows:
        tco[r["team"]] = tco.get(r["team"], 0) + r["dco"]
        tdab[r["team"]] = tdab.get(r["team"], 0) + r["dab"]
    print(
        f"\n--- CO WATCH (+{dco} league-wide from {len(co_up)} players; {ncorate:.3f}/AB "
        f"vs {ocorate:.3f} season-to-date, {(ncorate / ocorate - 1) * 100:+.0f}%) ---"
    )
    for r in co_up:
        if r["dco"] < 2:
            break
        print(
            f"  {r['name']:30s} +{r['dco']} (CO {r['o']['co']} -> {r['n']['co']})  "
            f"{week_line(r):14s} ({r['team']})"
        )
    erased = [r for r in rows if r["dh"] > 0 and r["dh"] - r["dco"] <= 0]
    print(
        f"  ERASED (every hit cancelled; {len(erased)}): "
        + (
            " | ".join(
                f"{r['name']} {week_line(r)} -> {A(r['rate'])} ({strip_the(r['team'])})"
                for r in erased
            )
            or "none"
        )
    )
    print(
        "  by team (worst first): "
        + " | ".join(
            f"{strip_the(t)} +{d} ({100 * d / tdab[t]:.1f}/100 AB)"
            for t, d in sorted(tco.items(), key=lambda kv: (-kv[1], kv[0]))
        )
    )

    print(f"\n--- WHO SAT (dAB == 0; {len(sat)} players) ---")
    byteam = {}
    for r in sat:
        byteam.setdefault(r["team"], []).append(r)
    for t in sorted(byteam, key=lambda t: (-len(byteam[t]), t)):
        who = sorted(byteam[t], key=lambda r: r["n"]["rank"])
        print(
            f"  {strip_the(t):32s} {len(who)}  "
            + ", ".join(f"{r['name']} (#{r['n']['rank']})" for r in who)
        )
    notable = sorted((r for r in sat if r["n"]["rank"] <= 30), key=lambda r: r["n"]["rank"])
    print(
        "  notable (season rank <= 30): "
        + (
            " | ".join(
                f"{r['name']} #{r['n']['rank']} {A(r['n']['avg'])} on {r['n']['ab']} AB "
                f"({strip_the(r['team'])})"
                for r in notable
            )
            or "none"
        )
    )

    print("\n--- PLAYING-TIME SURGES (top 8 dAB) ---")
    for r in sorted(rows, key=lambda r: -r["dab"])[:8]:
        print(
            f"  {r['name']:30s} +{r['dab']} AB ({r['o']['ab']} -> {r['n']['ab']})  "
            f"week {A(r['rate']) if r['rate'] is not None else '—'}  ({r['team']})"
        )

    deb = [r for r in rows if r["o"]["ab"] == 0 and r["n"]["ab"] > 0]
    print(f"\n--- DEBUTS ({len(deb)} first appeared this period) ---")
    for r in sorted(deb, key=lambda r: -r["n"]["avg"]):
        print(
            f"  {r['name']:30s} {A(r['n']['avg'])} on {r['n']['ab']:2d} AB  "
            f"({r['team']}, rd{r['pick']})"
        )

    tw = team_week_rows(prev, cur)
    scale = temp_scale(tw)
    print(
        f"\n--- TEAM WEEK (sorted by week rate; temperature bars scaled to ±{scale:.3f}) ---"
    )
    for r in tw:
        print(
            f"  {strip_the(r['team']):30s} {r['dh']:3d}-for-{r['dab']:<3d} CO {r['dco']}  "
            f"week {A(r['rate'])}  line {A(r['line'])}  gap {r['gap']:+.3f}  "
            f"width {abs(r['gap']) / scale * 50:.1f}%  bat rank #{r['obrank']} -> #{r['brank']}"
        )

    # ---- the ledger: what the week did to the season lines
    q = [r for r in rows if r["o"]["ab"] >= min_old_ab and r["n"]["ab"] >= min_new_ab]
    q.sort(key=lambda r: -r["dseason"])
    print(
        f"\n--- SEASON-AVG MOVERS (AB >= {min_old_ab} then and >= {min_new_ab} now; top 10 each) ---"
    )
    for r in q[:10]:
        print(
            f"  UP   {r['name']:30s} {A(r['o']['avg'])} -> {A(r['n']['avg'])} ({r['dseason']:+.3f})  "
            f"AB {r['o']['ab']}->{r['n']['ab']}  ({r['team']}, rd{r['pick']})"
        )
    for r in q[:-11:-1]:
        print(
            f"  DOWN {r['name']:30s} {A(r['o']['avg'])} -> {A(r['n']['avg'])} ({r['dseason']:+.3f})  "
            f"AB {r['o']['ab']}->{r['n']['ab']}  ({r['team']}, rd{r['pick']})"
        )

    # true-round movers: re-run the value ranking on both snapshots (each with
    # its own league average, i.e. what each edition published) and diff vround
    add_value(prev)
    add_value(cur)
    moved = []
    for k, o in po.items():
        n = pn[k]
        m = o["vround"] - n["vround"]  # positive = climbed toward round 1
        if m:
            moved.append((m, n, o))
    print(
        f"\n--- TRUE-ROUND MOVERS ({len(moved)}/{len(po)} changed true round; top 8 each) ---"
    )
    for m, n, o in sorted(moved, key=lambda t: (-t[0], -t[1]["value"]))[:8]:
        print(
            f"  UP   {n['name']:30s} R{o['vround']:<2d} -> R{n['vround']:<2d} (▲{m})  "
            f"{A(n['avg'])} on {n['ab']:2d} AB  value {n['value']:+5.1f}  ({n['team']})"
        )
    for m, n, o in sorted(moved, key=lambda t: (t[0], t[1]["value"]))[:8]:
        print(
            f"  DOWN {n['name']:30s} R{o['vround']:<2d} -> R{n['vround']:<2d} (▼{-m})  "
            f"{A(n['avg'])} on {n['ab']:2d} AB  value {n['value']:+5.1f}  ({n['team']})"
        )

    # dream-team turnover: each snapshot's dream team on its own values,
    # seats compared by (team, pick)
    dt_o, _ = dream_team(prev)
    dt_n, _ = dream_team(cur)
    turns = [
        (rd, dt_o[rd], dt_n[rd])
        for rd in range(1, ROUNDS + 1)
        if (dt_o[rd]["team"], dt_o[rd]["pick"]) != (dt_n[rd]["team"], dt_n[rd]["pick"])
    ]
    print(f"\n--- DREAM TEAM CHANGES ({len(turns)}/12 seats turned over) ---")
    for rd, o, n in turns:
        print(
            f"  R{rd:<2d} IN  {n['name']:28s} value {n['value']:+5.1f}  "
            f"OUT {o['name']:28s} (value {o['value']:+5.1f} at the prev snapshot)"
        )


# ---------------------------------------------------------------- arcs


def two_week_trends(prev2, prev, cur, min_dab=6):
    """Players trending the same direction across both periods.

    Heating: period-2 rate > period-1 rate AND > their own season line.
    Cooling: the mirror image. Requires min_dab period at-bats in BOTH
    periods. Returns (heating, cooling) as lists of
    (player, rate1, rate2, dab1, dab2), sorted hottest/coldest first.
    """
    m1, m2 = period_map(prev2, prev), period_map(prev, cur)
    heat, cool = [], []
    for p in cur:
        d1, r1 = m1[(p["team"], p["pick"])]
        d2, r2 = m2[(p["team"], p["pick"])]
        if d1 < min_dab or d2 < min_dab:
            continue
        assert r1 is not None and r2 is not None  # guaranteed by the min_dab gate
        if r2 > r1 and r2 > p["avg"]:
            heat.append((p, r1, r2, d1, d2))
        elif r2 < r1 and r2 < p["avg"]:
            cool.append((p, r1, r2, d1, d2))
    heat.sort(key=lambda t: (-t[2], -(t[2] - t[1])))
    cool.sort(key=lambda t: (t[2], t[2] - t[1]))
    return heat, cool


def arcs(prev2, prev, cur, min_dab=6, top=6):
    """Two-week digest across three snapshots: streaks, team arcs, race history."""
    print(f"\n{'=' * 72}\n=== ARCS: two-week trends across three snapshots ===\n{'=' * 72}")
    heat, cool = two_week_trends(prev2, prev, cur, min_dab)
    print(
        f"\n--- STREAKS & SLIDES ({min_dab}+ ABs in both periods; "
        f"{len(heat)} heating / {len(cool)} cooling; top {top} each) ---"
    )
    for p, r1, r2, d1, d2 in heat[:top]:
        print(
            f"  HEAT {p['name']:30s} {A(r1)} ({d1}) -> {A(r2)} ({d2})  season {A(p['avg'])}  ({p['team']})"
        )
    for p, r1, r2, d1, d2 in cool[:top]:
        print(
            f"  COOL {p['name']:30s} {A(r1)} ({d1}) -> {A(r2)} ({d2})  season {A(p['avg'])}  ({p['team']})"
        )

    # team arcs: period rate per team per period, same direction both weeks
    def trates(old, new):
        return {
            t: a["rate"] for t, a in team_period(old, new).items() if a["dab"] > 0
        }

    t1, t2 = trates(prev2, prev), trates(prev, cur)
    season = {}
    for p in cur:
        a = season.setdefault(p["team"], [0, 0])
        a[0] += p["h"] - p["co"]
        a[1] += p["ab"]
    season = {t: v[0] / v[1] for t, v in season.items()}
    print("\n--- TEAM ARCS (period rates; same direction both weeks) ---")
    for t in sorted(t2, key=lambda t: -(t2[t] - t1[t])):
        tag = ""
        if t2[t] > t1[t] and t2[t] > season[t]:
            tag = "  HEATING"
        elif t2[t] < t1[t] and t2[t] < season[t]:
            tag = "  COOLING"
        print(f"  {t:32s} {A(t1[t])} -> {A(t2[t])}  season {A(season[t])}{tag}")

    print("\n--- RACE HISTORY (leader by avg, AB >= 10, each snapshot) ---")
    for label, snap in (("oldest", prev2), ("middle", prev), ("current", cur)):
        lead = max((p for p in snap if p["ab"] >= 10), key=lambda p: (p["avg"], p["ab"]))
        print(f"  {label:8s} {lead['name']:30s} {A(lead['avg'])} on {lead['ab']:2d} AB  ({lead['team']})")


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("snapshot")
    ap.add_argument("--prev", help="older snapshot CSV for week-over-week comparison")
    ap.add_argument(
        "--prev2",
        help="snapshot before --prev, for two-week arcs (streaks & slides)",
    )
    ap.add_argument(
        "--brackets",
        help="contest entries CSV (name,club,code,received) for playoffs.html",
    )
    ap.add_argument(
        "--playoff-results",
        help="played playoff games CSV (game,winner) — scores the contest entries",
    )
    ap.add_argument("--min-ab-sleeper", type=int, default=15)
    ap.add_argument("--min-ab-outlier", type=int, default=10)
    ap.add_argument("--prev-min-ab-sleeper", type=int, default=10)
    ap.add_argument("--prev-min-ab-outlier", type=int, default=6)
    ap.add_argument(
        "--min-ab-period",
        type=int,
        default=6,
        help="minimum period at-bats for the hot/cold period-bats lists",
    )
    ap.add_argument(
        "--min-ab-perfect",
        type=int,
        default=4,
        help="minimum period at-bats for the perfect / hitless week lists",
    )
    ap.add_argument(
        "--min-ab-swing",
        type=int,
        default=4,
        help="minimum period at-bats for the week-swing lists (the Collapse, the Surge)",
    )
    ap.add_argument(
        "--html-tables",
        action="store_true",
        help="emit page-ready HTML for Team Sheets / Round Rooms instead of digests",
    )
    ap.add_argument(
        "--names-from",
        metavar="CSV",
        help="canonicalize an old-format snapshot's names from this comma-format file",
    )
    ap.add_argument(
        "--standings",
        metavar="CSV",
        help="standings snapshot (MMDD-standings.csv) to join against team batting",
    )
    ap.add_argument(
        "--prev-standings",
        metavar="CSV",
        help="older standings snapshot for week-over-week movement arrows",
    )
    ap.add_argument(
        "--games",
        metavar="CSV",
        help="season schedule CSV (MMDD-schedule.csv) of game results; requires --standings",
    )
    ap.add_argument(
        "--history",
        metavar="CSV",
        nargs="+",
        help="ALL older snapshots oldest->newest; implies --prev/--prev2 and "
        "powers the arcs chart, form glyphs, the rebound ledger and the "
        "records board",
    )
    ap.add_argument(
        "--html-afternoon",
        action="store_true",
        help="emit page-ready HTML for the Afternoon Final modules (needs --history "
        "with 2+ snapshots, --games, --standings and --prev-standings)",
    )
    args = ap.parse_args()

    cur, cur_fmt = load(args.snapshot)
    if args.names_from and cur_fmt == "old":
        ref, _ = load(args.names_from)
        canonicalize_prev_names(cur, ref)

    history = []  # [(path, players, renames)] oldest -> newest
    if args.history:
        for path in args.history:
            snap, fmt = load(path)
            ren = canonicalize_prev_names(snap, cur) if fmt == "old" else []
            history.append((path, snap, ren))
        dates = [snap_date(p) for p, _, _ in history]
        if dates != sorted(set(dates)) or dates[-1] >= snap_date(args.snapshot):
            sys.exit(
                "--history must be strictly oldest->newest, all older than the "
                "current snapshot"
            )
        if args.prev and args.prev != history[-1][0]:
            sys.exit(
                "--prev conflicts with --history (the last history entry IS the prev)"
            )
        if args.prev2 and (len(history) < 2 or args.prev2 != history[-2][0]):
            sys.exit(
                "--prev2 conflicts with --history (the second-to-last history "
                "entry IS the prev2)"
            )

    prev, prev2, renames = None, None, []
    if history:
        prev, renames = history[-1][1], history[-1][2]
        if len(history) >= 2:
            prev2 = history[-2][1]
    else:
        if args.prev:
            prev, fmt = load(args.prev)
            renames = canonicalize_prev_names(prev, cur) if fmt == "old" else []
        if args.prev2:
            if not prev:
                sys.exit("--prev2 requires --prev (it is the snapshot before --prev)")
            prev2, fmt2 = load(args.prev2)
            if fmt2 == "old":
                canonicalize_prev_names(prev2, cur)

    st = load_standings(args.standings) if args.standings else None
    prev_st = load_standings(args.prev_standings) if args.prev_standings else None

    games = None
    if args.games:
        if not st:
            sys.exit(
                "--games requires --standings (the identity check against it "
                "is what makes harvested scores trustworthy)"
            )
        games = load_games(args.games)
        validate_games(games, st, args.games, snap_date(args.standings))

    snaps = (
        [(snap_date(p), s) for p, s, _ in history]
        + [(snap_date(args.snapshot), cur)]
        if history
        else None
    )

    if args.html_afternoon:
        if not (games and st and prev_st and snaps and len(snaps) >= 3):
            sys.exit(
                "--html-afternoon needs --games, --standings, --prev-standings and "
                "--history with at least two snapshots"
            )
        brackets = load_brackets(args.brackets, st, cur) if args.brackets else None
        results = load_playoff_results(args.playoff_results, st) if args.playoff_results else None
        if brackets is not None:
            print(
                f"BRACKETS OK: {args.brackets}: {len(brackets)} verified entries",
                file=sys.stderr,
            )
        html_afternoon(snaps, games, st, prev_st, brackets, results)
        return

    if args.html_tables:
        html_tables(cur, prev, prev2, st, prev_st)
        return

    digest(cur, args.snapshot, args.min_ab_sleeper, args.min_ab_outlier)
    if st:
        standings_digest(st, cur, prev_st, prev)
    if prev:
        digest(
            prev,
            f"{args.prev or (history[-1][0] if history else '?')} (prev)",
            args.prev_min_ab_sleeper,
            args.prev_min_ab_outlier,
        )
        compare(
            prev,
            cur,
            renames,
            min_dab=args.min_ab_period,
            min_perfect=args.min_ab_perfect,
            min_swing=args.min_ab_swing,
        )
    if prev2:
        arcs(prev2, prev, cur)
    if games is not None and st and snaps and len(snaps) >= 2:
        afternoon_digest(snaps, games, st, prev_st)


if __name__ == "__main__":
    main()
