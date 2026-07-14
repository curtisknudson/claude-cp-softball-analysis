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
import csv
import math
import statistics
import sys

ROUNDS = 12

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
    po = {(p["team"], p["pick"]): p for p in prev}
    out = {}
    for p in cur:
        o = po[(p["team"], p["pick"])]
        dab = p["ab"] - o["ab"]
        dnet = (p["h"] - p["co"]) - (o["h"] - o["co"])
        out[(p["team"], p["pick"])] = (dab, dnet / dab if dab > 0 else None)
    return out


def period_rows(prev, cur):
    """Per-player week record, joined on (team, pick).

    The single source of truth for "what happened this period" — the compare
    digest and every front-of-book HTML emitter read from this. Note that dh
    and dco are kept, not just their net: a week is reported as a *line*
    ("7-for-7"), where the hits are raw and only the rate is net of caused
    outs. That is why a 2-for-5 week with two caused outs is worth .000.
    """
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
    return rows


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
    po = {(p["team"], p["pick"]): p for p in prev}
    agg = {}
    for p in cur:
        o = po[(p["team"], p["pick"])]
        a = agg.setdefault(p["team"], dict(dab=0, dh=0, dco=0, onet=0, oab=0))
        a["dab"] += p["ab"] - o["ab"]
        a["dh"] += p["h"] - o["h"]
        a["dco"] += p["co"] - o["co"]
        a["onet"] += o["h"] - o["co"]
        a["oab"] += o["ab"]

    sn = {s["team"]: s for s in st} if st else {}
    so = {s["team"]: s for s in prev_st} if prev_st else {}
    _, brank, _ = team_batting(cur)
    _, obrank, _ = team_batting(prev)

    rows = []
    for t, a in agg.items():
        rate = (a["dh"] - a["dco"]) / a["dab"] if a["dab"] else None
        line = a["onet"] / a["oab"] if a["oab"] else None
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

    def G(v):
        """A signed three-decimal delta, leading zero stripped: '+.060', '−.163'."""
        return f"{v:+.3f}".replace("-", "−").replace("0.", ".", 1)

    def signed(v, text):
        return f'<span class="{"zpos" if v >= 0 else "zneg"}">{text}</span>'

    def rankcell(r):
        return f'#{r["o"]["rank"]} <span class="muted">→</span> #{r["n"]["rank"]}'

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

    def zspan(z):
        return f'<span class="{"zpos" if z >= 0 else "zneg"}">{Z(z)}</span>'

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

    def vspan(v):
        return f'<span class="{"zpos" if v >= 0 else "zneg"}">{f"{v:+.1f}".replace("-", "−")}</span>'

    def pname(p):
        return p["name"] + (
            ' <span class="muted">· SS</span>' if is_ss(p) else ""
        )

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

    def gapspan(p):
        gap = p["pick"] - p["vround"]
        if gap > 0:
            return f'<span class="zpos">+{gap}</span>'
        if gap < 0:
            return f'<span class="zneg">−{-gap}</span>'
        return '<span class="muted">=</span>'

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
    p2 = {(p["team"], p["pick"]): p for p in prev2}
    p1 = {(p["team"], p["pick"]): p for p in prev}
    heat, cool = [], []
    for p in cur:
        a, b = p2[(p["team"], p["pick"])], p1[(p["team"], p["pick"])]
        d1, d2 = b["ab"] - a["ab"], p["ab"] - b["ab"]
        if d1 < min_dab or d2 < min_dab:
            continue
        r1 = ((b["h"] - b["co"]) - (a["h"] - a["co"])) / d1
        r2 = ((p["h"] - p["co"]) - (b["h"] - b["co"])) / d2
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
        agg = {}
        for p in new:
            o = {(q["team"], q["pick"]): q for q in old}[(p["team"], p["pick"])]
            a = agg.setdefault(p["team"], [0, 0])
            a[0] += (p["h"] - p["co"]) - (o["h"] - o["co"])
            a[1] += p["ab"] - o["ab"]
        return {t: v[0] / v[1] for t, v in agg.items() if v[1] > 0}

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
    args = ap.parse_args()

    cur, cur_fmt = load(args.snapshot)
    if args.names_from and cur_fmt == "old":
        ref, _ = load(args.names_from)
        canonicalize_prev_names(cur, ref)

    prev, renames = None, []
    if args.prev:
        prev, fmt = load(args.prev)
        renames = canonicalize_prev_names(prev, cur) if fmt == "old" else []

    prev2 = None
    if args.prev2:
        if not prev:
            sys.exit("--prev2 requires --prev (it is the snapshot before --prev)")
        prev2, fmt2 = load(args.prev2)
        if fmt2 == "old":
            canonicalize_prev_names(prev2, cur)

    st = load_standings(args.standings) if args.standings else None
    prev_st = load_standings(args.prev_standings) if args.prev_standings else None

    if args.html_tables:
        html_tables(cur, prev, prev2, st, prev_st)
        return

    digest(cur, args.snapshot, args.min_ab_sleeper, args.min_ab_outlier)
    if st:
        standings_digest(st, cur, prev_st, prev)
    if prev:
        digest(
            prev,
            f"{args.prev} (prev)",
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


if __name__ == "__main__":
    main()
