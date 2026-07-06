# CP Softball — Weekly Stats Site

Editorial stats site for a church softball league, published on **GitHub Pages** from
`curtisknudson/claude-cp-softball-analysis` (remote `origin`, SSH). Curtis uploads a fresh
stats CSV roughly weekly; each upload becomes a new "edition" of the site.

- **No build step, no JS** (single exception: the GoatCounter analytics snippet before `</body>`
  on every page — `https://cp-softball.goatcounter.com/count`; keep it when creating archives).
  Every page is hand-authored static HTML with inline CSS.
- **Project Pages URL prefix:** the site is served under `/claude-cp-softball-analysis/`,
  so every internal link must be **relative** (`2026-06-12.html`), never root-absolute (`/foo.html`).
- **Commits: plain messages, no Claude co-author or attribution lines** (owner's explicit rule).

## Files

| File | What it is |
|---|---|
| `index.html` | The **current edition** — always the latest snapshot, includes a "What Changed" section vs the previous one |
| `YYYY-MM-DD.html` | Frozen **archive editions**, named by data snapshot date (e.g. `2026-06-12.html`) |
| `MMDD-stats.csv` | Raw snapshots as uploaded (e.g. `0612-stats.csv`, `0703-stats.csv`) |
| `MMDD-standings.csv` | Weekly standings snapshots hand-saved from https://cpsoftball.com/standings.php (`rank,team,w,l,t,gp,win_pct,pf,pa,diff`; first one: `0706-standings.csv`) |
| `analysis.py` | **The single source of truth for every number on every page.** Stdlib-only Python 3 |

## The data

Two CSV schemas have appeared so far; `analysis.py` autodetects both by header:

1. `rank,player,team,draft_pick,at_bats,hits,caused_outs,adjusted_avg` — names are `"Last, First"` (quoted, comma).
2. `Name,Pick#,AVG,AB,H,CO,Team` — names are `Last First` (no comma), and **AVG is already the
   adjusted average**, not a raw batting average.

Facts that hold for every snapshot so far (the script asserts them and dies loudly if violated):

- **Adjusted average = (hits − caused outs) ÷ at-bats.** A caused out erases a hit.
- 144 players, 12 teams, 12 draft rounds, 12 players per team — one pick per team per round.
- **The canonical join key across snapshots is `(team, draft_pick)`.** It is unique (12×12).
  **Never match players by name across snapshots** — names get corrected between uploads
  (known case: "Williams Moroni" on 06/12 became "Musser, Moroni" on 07/03, same team/pick —
  Pliggas, round 6). The script flags any joined rows whose names disagree.
- Surnames can be two words ("Dockstader Marvins", "Hammon Legrands", "Barlow Jr", "Timpson Rays",
  "Hammon Hebers", "Dockstader Boyds") and given names can be multi-token ("Joanne Sis", "J Daunt",
  "Jason W", "Amie Z"). In the no-comma schema you cannot split names reliably on whitespace;
  the script recovers the split by joining to a comma-schema snapshot on (team, pick).
- Team names carry a "The " prefix except "Youre Saying Theres A Chance". Pages drop the "The "
  in tables but keep full names in prose.

## Captains (source: https://cpsoftball.com/teams.php — fetched 2026-07-06, no need to refetch)

**Every displayed team name carries the captain in parentheses**: `Good Guys (Gideon's team)`.
The rule applies everywhere a team is named — tables, bars, prose, tooltips — EXCEPT possessive
forms ("the Good Guys' 15 caused outs" stays unannotated; the grammar breaks otherwise).
`team_label()` in analysis.py implements this for generated tables and warns if a team is missing
from `CAPTAINS` (i.e., a roster change — refetch teams.php only then).

| Team | Captain | Label |
|---|---|---|
| The Good Guys | Gideon Hammon | Gideon's team |
| Youre Saying Theres A Chance | Horatio Williams | Horatio's team |
| The Lefty Looseys | Sefton Dockstader | Sefton's team |
| The Ellites | Elliot Hammon | Elliot's team |
| The Pliggas | Claude Timpson | Claude's team |
| The Playas | Michael Williams | Michael's team |
| The Stars and Strikes | Seth Cawley | Seth's team |
| The Danites | Daniel Dockstader Ephraims | Ephraims Daniel's team |
| The Pure Breads | Caleb Barlow | Caleb's team |
| The Slamma Jammas | Daniel Dockstader Boyds | Boyds Daniel's team |
| The Fellowship of the Swing | Stafford Hammon | Stafford's team |
| The Diamonds and Dirtbags | Jeremy Dockstader Marvins | Jeremy's team |

The two Daniels are disambiguated patronymic-style ("Ephraims Daniel", "Boyds Daniel"),
matching how the league's own rosters write compound names (e.g. "Dockstader Boyds, Daniel").

## Shortstops (per Curtis, 2026-07-06 — one per team; no need to re-ask)

Shortstop is the league's premium defensive position; 10 of the 12 were round-1 picks. A
shortstop's draft price partly buys defense that batting stats can't see — **temper
"overdrafted/didn't justify" verdicts for these names** and tag them `· SS` in Verdict tables
(`SHORTSTOPS` set + `is_ss()` in analysis.py):

Hammon, Gideon (GG) · Williams, Horatio (YS) · Dockstader, Sefton (LL) · Hammon, Elliot (EL) ·
Timpson, Claude (PL) · Williams, Michael (PLA) · Guy, Sam (SS) · Dockstader Ephraims, Daniel
(DA, R4) · Williams, Daniel (PB) · Knudson, Levi (SJ) · Hammon, Stafford (FS, R3) ·
Dockstader Boyds, Jeremy (DD)

## Draft order (per Curtis, 2026-07-06 — the draft SNAKED)

Captains drafted in this order, and each captain also drafted **themselves** somewhere:
Gideon Hammon → Horatio Williams → Sefton Dockstader → Elliot Hammon → Claude Timpson →
Michael Williams → Seth Cawley → Ephraims Daniel → Caleb Barlow → Boyds Daniel →
Stafford Hammon → Marvins Jeremy. Odd rounds run in that order, even rounds reverse
(snake). Overall pick # = (round−1)×12 + position (odd rounds) or + (13−position) (even).
`DRAFT_ORDER`, `CAPTAIN_PLAYER`, and `add_picks()` in analysis.py implement this; verified
anchors: Gideon Hammon = pick #1 (took himself), Jairus Hammon = #24, Sean Hammon = #140
(5th-to-last, NOT last), **Becky Wood = #144, the last pick of the draft**. The Verdict's
Full Docket lists players in true pick order, and the Captain's Mirror table
(`captains-mirror`) grades each captain's self-pick.

## Coed rule (per Curtis, 2026-07-06)

**Every roster must carry two women — including the Dream Team.** `dream_team()` in analysis.py
enforces this: if the pure-value team has fewer than two women, it swaps in the best-value woman
from whichever rounds cost the least total value, and tags swapped rows `· coed` (digest prints
`legal as-is` when no swap was needed — true of the July 3 edition: Maureen Williams and Jayla
Dockstader make it on value alone; say so in the page notes when it holds). Gender is deduced
from given names via `FEMALE_GIVEN` in analysis.py. **Confirmed male despite ambiguous names:
Taylor (Timpson) and Riley (Barlow)** — Curtis confirmed the current Dream Team's only women are
Maureen and Jayla. If Avery, Kendall, Sidney, Leslie, or J Daunt ever matter for the rule, ask
Curtis; never guess a gender into print.

## Analysis conventions

- **z-score** = standard deviations above/below the mean **within a player's draft round**
  (sample stdev over players with AB > 0). Zero-AB players get z = 0 and are excluded from
  round/family averages (0-for-0 is undefined, not .000).
- **Team/league averages are aggregate**: Σ(H−CO)/ΣAB — *not* the mean of player averages.
  **Family (dynasty) averages are the mean of player averages.** Don't mix these up.
- **Dynasty ledger**: single-word surnames with ≥ 3 players (9 families). Compound surnames are
  excluded from family grouping.
- **Report card** = Σ z across a roster. Bar widths = |z| ÷ scale × 50%; scale = max(6, ⌈max|z|⌉),
  stated in each page's legend. Letter grades are editorial, assigned monotonically.
- **Meter bars** (round averages): width = avg × 100%. Histogram bars: width = count ÷ max × 100%.
- **Min-AB filters** (stated in each page's footnote): current-edition sleepers 15 AB / outliers
  10 AB; early-season editions used 10 / 6. Movers: 8+ AB at the old snapshot AND 15+ at the new.
  Period bats: 10+ period ABs. Scale these sensibly as the season accumulates at-bats.
- **Period rate** ("what did they hit between snapshots") = (ΔH − ΔCO) ÷ ΔAB.
- **League rank**: the file's `rank` column when present, else avg desc → AB desc → name asc.

## Page anatomy (index.html)

Masthead (kicker · title · methodology sub · edition nav) → "Jump to" TOC nav → The Headlines →
**Team Temperature** (unnumbered "This Week" section at the top — the week-over-week team
diverging bars live HERE, not in S8; rebuild it each edition) → **The Standings** (unnumbered
"Scoreboard" section, id `standings` — W-L-T/PF/PA/diff joined to team batting, from the weekly
standings snapshot; `--standings NEW.csv --prev-standings OLD.csv` prints the digest + emits the
table rows, with movement arrows ▲▼ once a previous snapshot exists) → S1 League at a Glance (tiles) →
S2 Draft Board round averages → S3 Sleeper File → S4 Outliers per round → S5 Team breakdown +
Draft-Day Report Card → S6 Draft Board Second Look (risk/re-draft/discipline + early-vs-late
team split) → S7 Missing Pages (caused-out ledger, workload, distribution) → S8 What Changed
(week-over-week, incl. Dynasty of the Week + **the Records Board** — weekly bests that future
editions try to break; update it whenever a record falls) → S9 Team Sheets (best/worst pick per
team by z; hot/cold bat of the week per team vs the round's period rate) → S10 The Verdict
(**value** = (avg − league adj) × ABs = net hits above a league-average bat, volume-weighted by
design; "true round" = value rank dealt into rounds of 12; tables: Priced Exactly Right,
Bargains/underdrafted, Didn't Justify/overdrafted, Dream Team = best value per round, and the
**Captain's Mirror** = each captain's self-pick graded against their true round, and the
**Full Docket** = all 144 players in true snake-draft pick order (#1–#144) with
true-round/gap verdicts and a League # value-rank column, so every player can find their
own row; shortstops tagged · SS with a defense caveat) → S11 The Round Rooms (12 tables, every player by round,
season z + This Week column) → Appendix Dynasty Ledger → methodology footnote.

**Anchors:** every section has a stable id (`temperature`, `standings`, `glance`, `draft-board`, `sleepers`,
`outliers`, `teams`, `second-look`, `missing-pages`, `what-changed`, `team-sheets`, `verdict`,
`round-rooms`, `dynasty`) with a self-linking `<h2><a href="#id">`; each round-room h3 is
`round-1`…`round-12` (the `--html-tables` emitter produces these). **Every table also has an
h3 anchor** listed in the Jump-to nav (grouped into four lines): `tier-1`, `tier-2`,
`report-card`, `mined-rounds`, `caused-outs`, `iron-horses`, `league-shape`, `hot-bats`,
`cold-bats`, `movers`, `dynasty-week`, `records`, `team-picks`, `team-week`, `priced-right`,
`bargains`, `didnt-justify`, `dream-team`, `captains-mirror`, `full-docket`. New tables must
get an id + nav entry. Keep ids stable across
editions — people share deep links. The "Jump to" TOC after the masthead lists every section;
add new sections to it.

Archive pages mirror the above minus anything weekly (2026-06-12.html has S1–S5, S6 Team Sheets
season-only, S7 Round Rooms without the week column, + Appendix) — **no week-over-week content
and no foreshadowing**;
each archive is honest to its date. Archives are fully self-contained (own copy of the CSS) so
they stay frozen if the current design evolves. Recurring bits of voice: the Good Guys'
caused-out tragedy, the round-6 bump, the Sean Hammon R12 steal, and the running gag that the
analyst "offers no further comment" on Curtis Knudson's stats (he's the site owner).

## Weekly update procedure

1. **Save the new upload** as `MMDD-stats.csv`. Run `python3 analysis.py NEW.csv` alone first —
   it validates schema, formula, and join keys, and will exit with an error on format drift.
   Also fetch https://cpsoftball.com/standings.php and save it as `MMDD-standings.csv` (same
   columns as 0706-standings.csv; the loader asserts W+L+T=GP, PF/PA balance, win% = (W+T/2)/GP).
2. **Archive the current edition**: copy `index.html` to `YYYY-MM-DD.html` named for **its** data
   snapshot date (not today). In the copy: re-title/kicker it as an archived edition and add the
   "frozen snapshot" notice linking to `index.html`. Keep whatever What Changed section it shipped
   with — it compares against an even older edition and remains true. Don't touch its numbers;
   only the masthead/nav framing changes.
3. **Run the full digest**: `python3 analysis.py NEW.csv --prev PREVIOUS.csv --standings
   NEW-standings.csv --prev-standings OLD-standings.csv`. Digests print for both snapshots, the
   comparison, and the standings join (movement, bat-rank deltas, win%↔batting correlation).
   Then generate the bulk tables: the same command with `--html-tables` emits page-ready HTML for
   the Standings table (with ▲▼ movement arrows), Team Sheets A/B, the Verdict tables, all 12
   Round Rooms (with This Week column), and Dynasty-of-the-Week rows —
   splice these into the page wholesale instead of hand-typing the tables.
   (`--names-from COMMA_FORMAT.csv` canonicalizes names when the target file is the no-comma schema.)
4. **Rewrite `index.html`** from the current-snapshot digest: headlines, tiles, every table,
   report card, dynasty ledger, S6/S7. Write a **fresh S8** from the comparison digest against the
   just-archived edition (check the Records Board — update any record that fell). Replace the S9/S10
   table bodies with the freshly emitted HTML and rewrite their editorial notes. Update the masthead
   nav and the footnote's Editions list (add the new archive link; keep old ones).
5. **Transcribe, don't compute.** Every number on a page must appear in script output. If a number
   you want isn't printed, extend `analysis.py` rather than doing arithmetic by hand.
6. **Verify** (checklist below), then commit everything (new CSV + new archive + index + any script
   changes) with a plain message like `Publish July 10 edition` and push to `main`.

## Verification checklist

- Re-run both script modes; spot-check each page section against the printed digest.
- `python3 -c "import html.parser, pathlib; ..."` — parse both HTML files for tag balance
  (or any HTML validator available).
- `grep -n 'href=' *.html` — every internal link relative; new archive reachable from index
  (masthead + footnote) and index reachable from the archive.
- `python3 -m http.server` from the repo root and eyeball both pages, light and dark
  (`prefers-color-scheme`), plus the ≤560px mobile breakpoint.
- Archive page: masthead shows its snapshot date; no references to data newer than that date.
- `git status` — nothing intended left untracked; **no Claude attribution in the commit message**.
