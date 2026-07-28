# CP Softball — Weekly Stats Site

Editorial stats site for a church softball league, published on **GitHub Pages** from
`curtisknudson/claude-cp-softball-analysis` (remote `origin`, SSH). Roughly weekly Curtis says
the new numbers are up; Claude harvests them from cpsoftball.com (stats, standings, and — since
2026-07-24 — the full game schedule with scores), and each snapshot becomes a new "edition" of
the site.

- **No build step, no JS** (single exception: the GoatCounter analytics snippet before `</body>`
  on every page — `https://cp-softball.goatcounter.com/count`; keep it when creating archives).
  Every page is hand-authored static HTML with inline CSS. **Inline SVG is allowed** (static
  markup, not script) — the arcs chart is emitted by analysis.py, never hand-drawn.
- **Custom domain:** the site is served at **https://softball.best/** (the `CNAME` file; GitHub
  Pages serves custom domains at the domain root). Internal links must be **relative**
  (`2026-07-10.html`), never root-absolute — that keeps every page working at any serving root.
  The head's canonical/OG/Twitter URLs are deliberately absolute on `https://softball.best/`
  (og.png lives at the repo root); update them only if the domain changes.
- **Claude NEVER commits or pushes — no `git commit`, no `git push`, ever. Curtis handles all
  git operations himself** (owner's explicit rule, 2026-07-13). Leave finished work in the
  working tree and stop. If Curtis ever asks for a suggested commit message: plain text, no
  Claude co-author or attribution lines.

## Files

| File | What it is |
|---|---|
| `index.html` | The **current edition** — always the latest snapshot. Since 2026-07-17 its front is designed fresh each edition (see **The rotating front**) |
| `YYYY-MM-DD.html` | Frozen **archive editions**, named by data snapshot date (2026-06-12, 2026-07-03, 2026-07-10, …) |
| `MMDD-stats.csv` | Raw stats snapshots (e.g. `0717-stats.csv`) |
| `MMDD-standings.csv` | Standings snapshots from https://cpsoftball.com/standings.php (`rank,team,w,l,t,gp,win_pct,pf,pa,diff`; first one: `0706-standings.csv`) |
| `MMDD-schedule.csv` | **The season game book** (first one: `0717-schedule.csv`) — every game, completed and upcoming, from https://cpsoftball.com/schedule.php. See **Harvesting the schedule** |
| `analysis.py` | **The single source of truth for every number on every page.** Stdlib-only Python 3; digests + per-module HTML emitters (`--html-afternoon` registry, legacy `--html-tables` kept frozen for the archives' era) |
| `pyrightconfig.json` | `typeCheckingMode: "standard"` — 0 errors / 0 warnings must hold. basedpyright's default mode fires ~1,500 false `reportUnknown*` on this plain-dict script; standard is the right mode. Schema is enforced at **runtime** (loaders exit loudly) |
| `CNAME` | GitHub Pages custom-domain file (`softball.best`) — never edit or delete |
| `favicon.svg` · `apple-touch-icon.png` · `og.png` | Site chrome (og.png referenced absolutely as `https://softball.best/og.png` from every page's meta block) |

## The data

Two stats-CSV schemas have appeared so far; `analysis.py` autodetects both by header:

1. `rank,player,team,draft_pick,at_bats,hits,caused_outs,adjusted_avg` — names are `"Last, First"`.
2. `Name,Pick#,AVG,AB,H,CO,Team` — names are `Last First` (no comma), and **AVG is already the
   adjusted average**.

Facts that hold for every snapshot (the script asserts them and dies loudly if violated):

- **Adjusted average = (hits − caused outs) ÷ at-bats.** A caused out erases a hit.
- 144 players, 12 teams, 12 draft rounds, 12 players per team — one pick per team per round.
- **The canonical join key across snapshots is `(team, draft_pick)`.** It is unique (12×12).
  **Never match players by name across snapshots** — names get corrected between uploads
  (known case: "Williams Moroni" → "Musser, Moroni", Pliggas R6). The script flags joined rows
  whose names disagree.
- Surnames can be two words and given names multi-token; in the no-comma schema you cannot split
  names on whitespace — the script recovers the split by joining on (team, pick).
- Team names carry a "The " prefix except "Youre Saying Theres A Chance".
- **Display averages transcribe the FILE, never a recompute** — the site rounds half **up**
  (13-for-16 = .8125 prints **.813**); Python's round-half-even says .812. `disp()` in
  analysis.py exists for exactly this; the page must never show a .812-style artifact.

## Harvesting stats (source: https://cpsoftball.com/stats.php)

- **Ask Curtis for the filename before querying.** He gives the `MMDD` (the data-snapshot date
  and his "go"). Never guess the date. (He sometimes uploads the CSVs himself — validate them
  the same way.)
- The page's columns `# · Player · Team · Pick# · AB · H · CO · AVG` map exactly onto stats
  **schema 1**. Keep the `"Last, First"` comma (quote every name field).
- **Match existing CSV style byte-for-byte:** averages 3-decimal padded, **CRLF** line endings
  including a trailing CRLF. (The Write tool emits LF — convert.)
- Fetch with **WebFetch** (curl is blocked). The extractor is a small model — **validate before
  trusting**: formula holds per row (site rounds half up — exact halves are not errors); totals
  equal the page's Season Summary footer; `(team, draft_pick)` unique 12×12; ranks 1–144.
  Then `python3 analysis.py MMDD-stats.csv` must exit 0 with no WARN.
- Grab standings the same day: standings.php → `MMDD-standings.csv` (loader asserts W+L+T=GP,
  PF/PA balance, win% = (W+T/2)/GP).

## Harvesting the schedule (source: https://cpsoftball.com/schedule.php)

First harvested 2026-07-24 as `0717-schedule.csv` — **all 120 season games** (72 completed
through Jul 17 + the full future slate: Jul 24, Jul 31, Aug 7, Aug 14). Game days so far (all 2:30–7:30 PM):
Jun 5, 12, 19, Jul 3, 10, 17 — note there were NO games the week of Jun 26, so snapshots and
afternoons don't align 1:1; trust the date inventory, not assumptions. Each game day: 12 games,
two fields (North/South), 2:30–7:30 PM, every club playing twice. **The session is an
AFTERNOON, never "the night"** (owner's correction, 2026-07-24 — this edition briefly shipped
in the working tree as "the Night Final" and was renamed before publishing).

- **Schema:** `date,time,field,team_a,score_a,team_b,score_b,status,note` — ISO dates, times
  verbatim (`2:30 PM`), fields `North`/`South`, **canonical raw team names** (must match
  `CAPTAINS` keys), `status ∈ {FINAL, TIE, SCHEDULED}`, scores blank exactly when SCHEDULED.
  a/b is the site's listing order (no home/away concept). CRLF incl. trailing.
- **Forfeits stay FINAL rows** with the site's own score plus its note (the Jun 19 "Sub Rule
  Infraction Forfeit" is listed 10–0 and reconciles as a normal game).
- **The identity gate is what makes harvested scores trustworthy.** `validate_games()`
  reconciles completed games (through the standings snapshot's date) against the standings
  EXACTLY: per-team W/L/T, PF, PA, GP, and the league game count. It runs automatically with
  `--games` (which requires `--standings`) and hard-exits with a per-team diff table on any
  mismatch — that table names the teams to refetch. `0717-schedule.csv` reconciles against
  0717-, 0710-, AND 0706-standings at their cutoffs.
- **Harvest procedure:** WebFetch in per-date-range chunks. The extractor WILL lie about which
  dates exist (it once claimed no July 3 games, then no June 26 afternoon — one of each claim was
  wrong): when confused, force a **full date inventory** ("list every distinct date and its game
  count") before fetching ranges. Future (SCHEDULED) rows have no numeric gate — confirm them
  with a second independent fetch.
- **Each edition:** append the new afternoon's finals, refresh/extend future rows, re-run the gate.

## Captains (source: https://cpsoftball.com/teams.php — fetched 2026-07-06)

**Owner's rule (2026-07-14): league team names are NOT used on any page.** Every club is named
by its captain — `Gideon's team`, `Horatio's team` — in prose, tables, cards, tags, SVG labels
and SVG `<title>` tooltips. `team_label()` in analysis.py is the single implementation (warns
if a team is missing from `CAPTAINS` — refetch teams.php only then). **Verify with a grep:** no
raw team name may survive in `index.html`. Raw names still key every join and still print in
the **text digest** (the author's tool). Archives stay frozen in their era's style.

Avoid the double possessive: "the six caused outs on Gideon's team", never "Gideon's team's six
caused outs".

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

The two Daniels are disambiguated patronymic-style ("Ephraims Daniel", "Boyds Daniel").
Clubhouse anchors use captain slugs via `club_slug()`: `club-caleb`, `club-boyds-daniel`.

## Shortstops (per Curtis, 2026-07-06 — one per team)

Shortstop is the league's premium defensive position; 11 of 12 are round-1 picks. A shortstop's
draft price partly buys defense batting stats can't see — **temper "overdrafted" verdicts** and
tag them `· SS` (`SHORTSTOPS` + `is_ss()`):

Hammon, Gideon (GG) · Williams, Horatio (YS) · Dockstader, Sefton (LL) · Hammon, Elliot (EL) ·
Timpson, Claude (PL) · Williams, Michael (PLA) · Guy, Sam (SS) · Dockstader Ephraims, Daniel
(DA, R4) · Williams, Daniel (PB) · Knudson, Levi (SJ) · Dockstader, Adam (FS) ·
Dockstader Boyds, Jeremy (DD)

(2026-07-13: Stafford Hammon no longer plays SS; Adam Dockstader does. Pre-July-10 archives
tagged Stafford — frozen, don't retro-edit.)

## Draft order (per Curtis, 2026-07-06 — the draft SNAKED)

Gideon Hammon → Horatio Williams → Sefton Dockstader → Elliot Hammon → Claude Timpson →
Michael Williams → Seth Cawley → Ephraims Daniel → Caleb Barlow → Boyds Daniel →
Stafford Hammon → Marvins Jeremy. Odd rounds run in that order, even rounds reverse. Overall
pick # = (round−1)×12 + position (odd) or + (13−position) (even). `DRAFT_ORDER`,
`CAPTAIN_PLAYER`, `add_picks()`. Verified anchors: Gideon Hammon #1 (took himself), Jairus
Hammon #24, Sean Hammon #140, **Becky Wood #144 — the last pick of the draft**.

## Coed rule (per Curtis, 2026-07-06)

**Every roster must carry two women — including the Dream Team.** `dream_team()` enforces it
(swaps in the best-value woman from the cheapest rounds, tags `· coed`; prints `legal as-is`
when no swap needed — true on 2026-07-17: Maureen Williams and Jayla Dockstader make it on
value). Gender via `FEMALE_GIVEN`. **Confirmed male despite ambiguous names: Taylor (Timpson)
and Riley (Barlow).** If Avery, Kendall, Sidney, Leslie, or J Daunt ever matter for the rule,
ask Curtis; never guess a gender into print.

## Analysis conventions

Season (unchanged since the early editions):
- **z-score** = stdevs above/below the mean **within a player's draft round** (sample stdev,
  AB > 0; zero-AB players get z = 0 and are excluded from round/family averages).
- **Team/league averages are aggregate**: Σ(H−CO)/ΣAB. **Season family (dynasty) averages are
  the mean of player averages** — but **family WEEKS are aggregate** (`family_week()`), pooled
  like team weeks. Don't mix these up.
- **Dynasty ledger**: single-word surnames with ≥ 3 players (9 families), sorted best-to-worst
  by family average (owner's rule 2026-07-13).
- **Value** = (avg − league adj) × AB = net hits above a league-average bat; **true round** =
  value rank dealt into rounds of 12; the Dream Team = best value per round under the coed rule.
- **League rank**: the file's `rank` column when present.
- **Batting race**: min 15 AB; **"hits back" = (leader avg − avg) × own AB**. The crown chase
  prints the top 4 (`race_top`); **crown history** = each snapshot's leader at 10+ AB
  (`race_history` over the whole `--history` chain).

The week (one league afternoon between snapshots):
- **Period/afternoon rate** = (ΔH − ΔCO) ÷ ΔAB, joined on (team, pick). An afternoon is written as a
  line — `7-for-8`, or `5-for-6 · 2 CO` — **hits raw, rate net**; any table showing lines must
  explain that in a caption or lede.
- **Swing** = afternoon rate − the player's/club's **own season line at the previous snapshot**.
  Never chart Δ season average (it measures the calendar); Δ season avg = swing × (ΔAB ÷ AB).
- **HAE ("hits above the book")** = ΔH − ΔCO − ΔAB × own prior line — the swing made
  volume-aware; the Bat of the Afternoon statistic.
- **The Weeklies** (all computed, `afternoon_awards()`): Bat of the Afternoon = max HAE; the Anvil =
  worst swing (4+ AB); the Vacuum = most afternoon COs (ties broken by season CO); the Ghost =
  highest-ranked player with ΔAB 0; the Iron Week = most ΔAB; Clean Sweep = clubs with 0 afternoon
  CO; the Ladder/the Chute = extreme league-rank moves.
- **Rebound ledger**: last edition's Collapse cohort (swing ≤ −.300 on 4+ ABs) re-examined —
  REBOUNDED = afternoon rate above the player's own line at the previous snapshot; FELL AGAIN; SAT.
- **Form glyphs** (`form_glyphs`): one glyph per period over the last three — ↗ swing above
  +.050, ↘ below −.050, → inside the deadband (or no prior line), · sat.
- **Scoreboard tags** (computed, never editorial): `1-RUN` margin 1; `TIE`; `UPSET` winner ≥ 6
  standings places below the loser at the previous standings; forfeit notes print verbatim.
- **Games back** = ((leadW − W) + (L − leadL)) ÷ 2, `gb_str` renders ½-style; **streaks** =
  trailing W/L/T run from the game book; **Pyth** = PF²÷(PF²+PA²), **Luck** = win% − Pyth.
- **Min-AB gates**: swing/perfect lists 4+ (`--min-ab-swing/-perfect`), hot/cold period list 6+
  (`--min-ab-period`), weekly records 10+. Scale sensibly as the season accumulates.

The schedule desk (added 2026-07-28: `sos_rows` / `season_series_pairs` / `schedule_faced` /
`player_period_slates` / `alibi_verdict`; prints in the SCHEDULE DESK digest block):
- **SOS played** = mean over a club's completed games of that opponent's win% in its OTHER
  games (head-to-head excluded, one entry per game); **SOS left** = mean current win% of the
  clubs still on the slate. **Slate faced** (player) = AB-weighted mean opponent RA/G across
  periods — a period's ABs are charged to its **whole** opponent set (an afternoon is two
  games, early blocks four): attribution finer than the slate is impossible; never fake it.
- **Defense ledger** = runs allowed per game (standings PA/GP) — the only defense the book
  supports. **Audit verdict (through 0717 — recompute before citing):** opponent quality does
  NOT predict batting; the splits ran backwards (soft slates +.002 swing vs hard +.022; runs
  11.01/game vs generous defenses, 11.63 vs stingy). So: **never publish schedule-adjusted
  averages** — the alibi audit exists to kill that idea. The `gauntlet` (SOS) is standings
  context and recurs; the `alibi` was a one-off (bring it back only if the verdict flips).
- **Recomputed from the full `--history` chain every run** — player hot/cold week (10+ AB),
  team best/worst week, family best week, workload, team CO, player CO — plus **game records**
  from the schedule (biggest margin, highest/lowest-scoring game, longest win streak).
- `RECORDS_PUBLISHED` is the board **as last published** — a drift tripwire, not a source: a
  recompute-vs-constant mismatch means upstream data was revised (WARN on stderr; investigate).
  **Update the constant to the new board as the last step of each edition build.**
- Status per category: FELL / MATCHED / NEAR MISS (within .050 for rates, 2 for counts) / HELD.
  **Cross-edition superlatives are computed, never asserted** — that is the whole point.

The arcs chart (`emit_arcs_svg`):
- Inline SVG, byte-deterministic, emitted by the script — coordinates computed in Python. Every
  club's season line at every snapshot; y fixed .400–.640, x proportional to real dates;
  right-rail labels slot-stacked at a 15px minimum gap with leader lines; per-line `<title>`
  tooltips (captain labels only!); a **visible fallback table** always sits beneath it.
- **Emphasis, not rainbow:** at most 3 clubs carry color (`--arc-1..3`; currently Horatio/
  Jeremy/Caleb — light `#2a78d6/#eb6834/#1baf7a`, dark `#3987e5/#d95926/#199e70`, validated
  all-pairs in both modes with the dataviz skill's `validate_palette.js`); everyone else rides
  `--arc-dim`. Identity is carried by the labels, never color alone; text never wears series
  color. Changing which clubs are emphasized is a page-CSS edit, not a re-emission. Re-validate
  if the hues ever change.

## The rotating front (doctrine, adopted 2026-07-17)

Readers were bored because the structure repeated — same sections, new digits. The fix is
structural: **every edition designs its front page fresh around what actually happened that
week.** A crown change gets a tabloid cover; a record rout might get a broadsheet EXTRA; a
rain-shortened afternoon might get a two-paragraph bulletin over the reference tables. Do not reach
for last edition's layout; reach for the digest, find the story, and build the front that story
demands. (The pre-2026-07-17 fixed four-movement anatomy is retired; it lives on, frozen, in
the June/July archives.)

What stays stable underneath — the spine:

- **Masthead** with kicker (source · data date · compiled date), edition nav linking every
  archive, and a one-paragraph methodology sub naming the adjusted average. **GoatCounter**
  before `</body>`. A compact contents nav.
- **The anchor contract:** `race`, `standings`, `records`, `watch`, and `dream-team` exist on
  every edition, whatever form their sections take. Every table carries an h3 anchor. Module
  ids that recur keep their names across editions (`scoreboard`, `weeklies`, `arcs`, `rebound`,
  `clubhouse`, `chase`, `crown-history`, `arcs-table`, `value`, `value-movers`, `club-<slug>`,
  `gauntlet`).
- **The reference back**: standings, race, records, dream team, and a find-yourself surface
  (currently the clubhouse roster tables) appear in some form every edition. Anything deeper
  (full docket, round rooms, draft board…) may **rest** — say where it rests (the archive), and
  bring it back when it earns space.
- **One emitter per page module**, registered in `AFTERNOON_EMITTERS` (page order, banner names the
  module id). Future fronts add/swap/retire registry entries — never a second monolith, never a
  hand-typed number. `--html-tables` stays frozen for the archives' era; don't extend it.
- **Editorial law** (unchanged from the old anatomy, because it's about prose not layout):
  1. A marquee number is narrated in prose **exactly once** (tables, cards, tiles and captions
     may echo it). Run the scripted de-dup grep over `.dek/.lede/.notes/.callouts/.t-note`.
  2. Anchor every week fact to what it replaced (`.864 → .788`, `#1 → #4`).
  3. Say the games — "the afternoon of July 17", never "the period", in front-of-book prose.
  4. Clubs by captain, always. Week prose reportorial (*went, hit, fell, sat, beat*), season
     prose judicial (*is, ranks, holds*).
  5. Never write "points" without saying points of WHAT (swing vs season-line move).
  6. **The same-y test:** put the new front beside the previous edition's. If any headline
     could become last edition's by changing digits, cut it and find the week's own fact.
  7. Write the cover/headlines LAST.
- **Archives**: archive the outgoing index as `YYYY-MM-DD.html` first (retitle + kicker
  "Snapshot <date> · Archived Edition", canonical/og → the archive URL, og:type article,
  frozen-snapshot notice + footer archive line, editions links, keep GoatCounter and the full
  self-contained CSS). **Delete the forward-looking section** (`watch`, whatever it's titled)
  and its contents-nav entry — foreshadowing doesn't archive. Never retro-edit archives.

**Edition log** (what each front was, so the next one can be different):
- **2026-06-12 / 2026-07-03**: the original season-reference broadsheet (fixed anatomy).
- **2026-07-10**: the four-movement week-first paper (fixed anatomy, v2).
- **2026-07-17 — THE AFTERNOON FINAL**: tabloid sports final. Ink-plate masthead and section bars,
  mono scoreboard chrome. Modules: cover (`race` — the crown, chase + crown history), ticket
  `scoreboard` (12 stubs, hand-written one-line `t-note` per game), `weeklies` award cards,
  `arcs` centerfold (first chart the site ever ran) + fallback table, `rebound` ledger (paying
  off the July 10 stakes), `clubhouse` (12 club pages: card + roster with Form glyphs —
  replaced Team Sheets/Round Rooms/Full Docket), `standings` (+GB +Streak), `value` desk
  (Dream Team + churn only), `records` (recomputed board + new game categories), `watch`
  ("the next slate" — matchup-driven). Retired-that-edition: glance, draft-board, sleepers,
  teams/report-card, second-look, missing-pages, what-changed, team-sheets, verdict tables
  beyond the Dream Team, round-rooms, dynasty section (folded to a value-desk note).
  **Supplement 2026-07-28** (spliced into the live 07-17 edition between `standings` and
  `value`, plates marked "Supplement · July 28"): `gauntlet` — the SOS ledger (recurring
  module, `emit_gauntlet`) — and `alibi` — the schedule-alibi audit, a one-off feature
  (`emit_alibi`; sub-ids `defense-ledger`, `chase-slates`, `case-sean`). Both fed by the
  SCHEDULE DESK digest block. When this edition archives, the gauntlet stays (the fixture
  list was known on the data date — it is a ledger, not foreshadowing); only `watch` gets
  deleted per the archive rule.

**Retired ids** (pre-2026-07-17; they resolve in the archives, never reuse for new meanings):
`the-week, week-bats, temperature, glance, draft-board, sleepers, teams, second-look,
missing-pages, what-changed, team-sheets, verdict, round-rooms, dynasty, hot-bats, cold-bats,
week-co, playing-time, perfect-weeks, team-box, tier-1, tier-2, team-notes, report-card,
mined-rounds, caused-outs, clean-hands, iron-horses, league-shape, movers, streaks,
dynasty-week, bookkeeping, team-picks, team-week, priced-right, bargains, didnt-justify,
captains-mirror, full-docket, outliers, round-1…round-12`.

## Gag ledger (keep bits consistent and escalating, not reset)

- **The caused-out tragedy** (Gideon's team): act four (2026-07-17) was "a remission" — +3 on
  the afternoon, season 24 still league-worst. Track act five honestly; remissions end or hold.
- **The recusal bit** (Curtis Knudson, site owner): budget ≤ 2 per edition, vary the wording
  ("declines to recuse himself" / "offers no further comment"). 2026-07-17 used both: the
  crown chase (he sits third) and the dynasty note (his family lost the first-family title to
  the Williamses the same afternoon).
- **Sean Hammon's fairy tale is CLOSED** (2026-07-17: hitless afternoon, lost the R12 Dream Team
  seat to Sharon Hammon; "the mean he was regressing toward is above him"). Do not resurrect
  without a genuine second act — a comeback would BE the story, not the gag. The 2026-07-28
  alibi audit **acquitted** his June of schedule inflation (hot block vs the D2/D4 defenses;
  his club never met Michael's team; slate 11.19 ≈ league mean) — "the audit merely corrects
  the cause of death." The file stays closed; cite the audit rather than reopening it.
- **Becky Wood, #144**: "still technically a bargain" is now "doing heavy lifting" (0-for-5,
  #139). 2026-07-28: the audit found she has also faced the league's softest slate (12.36 opp
  RA/G, most generous among 15+ AB regulars) — "no alibi in either direction." Keep tracking;
  never invent numbers for her.
- **The invoice** (Stafford's team's luck): opened +.243 (July 10), **first installment
  collected** 2026-07-17 (+.200, slid #2→#4). Each edition: pay it down or re-inflate it, with
  the actual Luck number.
- **New seeds from 2026-07-17**: "the league owes Ephraims Daniel's club" (luck −.251 while
  their captain won Bat of the Afternoon); Jeremy's team "the quietest hot team in the league"
  (won six straight while batting worst on the day); "the 1.000 club is closed" (first
  zero-perfect afternoon). Use them only when the new data feeds them.
- **The schedule alibi is dead** (2026-07-28 audit): the league batted *better* against the
  harder slates. If a club or player blames the schedule in a future edition, cite the audit
  ("the alibi desk settled this in July") instead of re-running it — unless the verdict has
  actually flipped, which would be a story. Related standing fact: the Gauntlet showed the
  top four all rode sub-.500 slates while Sefton's club (5th) walked the hardest and drew
  the softest run-in — the August run-in is loaded (Caleb–Stafford ×3, Jeremy–Boyds ×3).

## Weekly update procedure

1. **Harvest** the new `MMDD-stats.csv` (ask Curtis for the filename first) and
   `MMDD-standings.csv` per the harvesting sections; **update `MMDD-schedule.csv`** (append the
   new afternoon's finals, refresh future rows — new file named for the new snapshot date; keep the
   old one). Gates: `python3 analysis.py NEW.csv` exits 0 no WARN; the schedule↔standings
   identity passes.
2. **Archive the current edition** to `YYYY-MM-DD.html` per the archive rules above (delete the
   forward-looking section + its nav entry).
3. **Run the full digest** —
   `python3 analysis.py NEW-stats.csv --history <every older stats CSV, oldest→newest>
   --games NEW-schedule.csv --standings NEW-standings.csv --prev-standings OLD-standings.csv`
   — legacy digests + compare + arcs print first, then the **AFTERNOON DESK** digest (scoreboard,
   crown, awards, family afternoon, rebound ledger, GB & streaks, game records, head-to-head, next
   afternoon, records watch, arcs series). `--prev/--prev2` still work standalone for cross-edition
   checks against arbitrary pairs.
4. **Design the front** (the doctrine step): read the digest, name the week's story, sketch the
   front it demands, keep the anchor contract and the spine. Reuse, retire, or add emitters —
   one per module — then run the same command with `--html-afternoon` and **splice the emitted
   modules wholesale**. Prose is transcribed from digest lines; hand-written ticket notes/prose
   carry no numbers that aren't in the digest. Cover last; same-y test against the previous
   front.
5. **Update `RECORDS_PUBLISHED`** in analysis.py to the board as this edition publishes it.
6. **Verify** (checklist below), then STOP and hand off — **do not commit, do not push.** Tell
   Curtis what changed and leave everything in the working tree.

## Verification checklist

- All command shapes exit 0 with no WARN: bare snapshot; legacy `--prev/--prev2/--standings/
  --prev-standings`; a cross-edition pair; the full `--history --games` run; `--html-afternoon`.
  The records tripwire (stderr) is silent.
- Schedule identity: per-team W/L/T, PF, PA, GP and league game count reconcile exactly.
- `npx -y basedpyright analysis.py` → 0 errors / 0 warnings (needs network for npx; note in
  the handoff if unavailable).
- Tag-balance parse (html.parser with `handle_startendtag`; treat SVG shape tags as void) over
  `index.html` **and every archive**.
- Anchor audit: every `href="#…"` resolves; no duplicate ids; the **anchor contract** ids all
  exist; internal links relative; newest archive ↔ index mutually reachable.
- **Team-name grep**: no raw league team name anywhere in `index.html` — including SVG
  `<title>`s and `title=` attributes.
- **De-dup grep** (scripted): each marquee number appears in ≤ 1 prose block
  (`.dek/.lede/.notes li/.callouts p/.t-note`); tables/cards/tiles/captions don't count.
- **Display tripwire**: no recomputed-rounding artifacts (`grep -c '\.812'` style checks for
  any average the file prints differently); every page number greps out of the saved digest or
  emitter output.
- `python3 -m http.server` and eyeball index + newest archive: light and dark, ≤560px; wide
  tables scroll inside `.table-scroll`; the SVG scrolls on mobile (min-width, not shrink) and
  its label rail resolves.
- Archive honesty: the new archive shows nothing newer than its date; no forward-looking
  section; masthead says Archived Edition.
- `git status` — nothing unintended; hand off. **Never `git commit` or `git push`.**
