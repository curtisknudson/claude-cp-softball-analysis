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
| `favicon.svg` · `apple-touch-icon.png` · `og.png` | Site chrome (og.png referenced absolutely as `https://softball.best/og.png` from every page's meta block). An edition MAY ship a special OG card as `og-YYYY-MM-DD.png` (first: `og-2026-07-24.png`, the "Ryan Hammon bat 1.000" tease, rendered with Pillow in the site palette scanned from og.png) — only that edition's index points at it; when the edition archives it keeps its card, and the next index reverts to og.png unless it ships its own |

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
- Counters can be revised **downward** site-side between snapshots (0724: Merlek Timpson's CO
  went 2→1, and the page's reprinted AVG confirmed the revision). Cross-check the new harvest
  against the previous CSV on (team, pick); a formula-confirmed revision is a note for the
  handoff, not an error — but an unconfirmed decrease is a misread. (Revisions also surface as
  oddities downstream: Merlek's afternoon printed `4-for-6 · -1 CO`.)
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
  deleted per the archive rule. (Archived 2026-07-29 as 2026-07-17.html — watch deleted,
  gauntlet AND alibi kept, and three "fortafternoon" typos left over from the night→afternoon
  rename repaired at archive time.)
- **2026-07-24 — THE LEDGER**: accounts-desk broadsheet — serif voice, monospaced figures,
  double rules and dotted leaders, section heads numbered "Ledger Nº 1…13". Same background
  tokens as the tabloid (deliberate: the validated arc palette stays valid); the identity
  change is typographic. Cover story = the standings, not the race: **`invoice`** (one-off,
  `emit_invoice`, sub-id `statement`) — a statement of account addressed to whichever club
  leads the standings (record, win%, pyth, LUCK as "balance due", SOS played, bat rank, the
  afternoon's results, balance carried forward from prev standings) — the invoice-gag payoff
  ("First place, on credit"). **`debits`** (one-off, `emit_debits`, sub-ids `debits-clubs`,
  `debits-players`) — the caused-out epidemic ledger (club table worst-first with clean
  sheets shaded, individual table +2-or-worse then the erased). Page order: invoice,
  scoreboard (ticket entries, hand-written t-notes), debits, race (crown held), weeklies,
  records (promoted to the front of book — three records fell), arcs (5 snapshots; emphasis
  reassigned to Stafford/Sefton/Horatio, a page-CSS edit), rebound, clubhouse, standings,
  gauntlet, value, watch. `alibi` retired from the registry (one-off, done; `emit_alibi`
  stays defined in case the verdict ever flips). Game-record rows now print a muted "—"
  status (the "NEW CATEGORY" labels were a debut-edition artifact). Late addition
  (2026-07-29, owner request): **`thousand-club`** — a framed bulletin (`.bulletin`) of two
  punch-card membership cards (fields incl. a deadpan Age line, punched-hole rows, a rotated
  1.000 stamp), hand-written with no emitter (numbers transcribed from the digest's PERFECT
  WEEKS lines), celebrating the reopened 1.000 club and Ryan Hammon's forty-plus perfect
  afternoon. Placed ABOVE Ledger Nº 1, directly after the contents nav — the owner wants it
  the first thing readers see this edition. The edition also ships a special OG card,
  `og-2026-07-24.png` ("Ryan Hammon bat 1.000" · seven punches · AGE: FORTY-PLUS
  (UNDISPUTED)) — og:image/twitter:image point at it; every share of this edition is the
  tease. Revert og:image to og.png next edition (or ship a new card). Second late addition
  (same day): **`trainers-table`** — "Ledger Special · The Trainer's Table," an
  injury-report parody (hand-written, no emitter; lines from the digest) teasing the
  editor's brothers and Sam Guy — see the gag ledger for the owner facts and the tone
  mandate. Debuted between `weeklies` and `records`, then moved up to sit directly after
  `mw-benchmark`/`second-opinion` (owner request) — the front now runs a continuous
  medical block: benchmark → the doctor's chart → the ward. Third late addition (same day): **`the-disclaimer`**,
  an h3 notice at the foot of `scoreboard` recording the overturned-in-spirit home run in
  the upset game (owner facts in the gag ledger; linked from the upset ticket). Fourth
  late addition (same day): **`mw-benchmark`** — the Mike Williams Benchmark honor roll, placed
  directly after `thousand-club` and before `invoice` (owner wants it high); hand-written,
  numbers from the stats file via a FEMALE_GIVEN query — see the gag ledger for the
  framing mandate and the Sidney/Leslie caveat. Fifth late addition (same day):
  **`second-opinion`** — the Dr. Ben Williams prescription-pad coda at the foot of
  `mw-benchmark` (owner facts in the gag ledger).

**Retired ids** (pre-2026-07-17; they resolve in the archives, never reuse for new meanings):
`the-week, week-bats, temperature, glance, draft-board, sleepers, teams, second-look,
missing-pages, what-changed, team-sheets, verdict, round-rooms, dynasty, hot-bats, cold-bats,
week-co, playing-time, perfect-weeks, team-box, tier-1, tier-2, team-notes, report-card,
mined-rounds, caused-outs, clean-hands, iron-horses, league-shape, movers, streaks,
dynasty-week, bookkeeping, team-picks, team-week, priced-right, bargains, didnt-justify,
captains-mirror, full-docket, outliers, round-1…round-12`.

## Gag ledger (keep bits consistent and escalating, not reset)

- **The caused-out tragedy** (Gideon's team): act four (2026-07-17) was "a remission" — +3 on
  the afternoon, season 24 still league-worst. Act five (2026-07-24): +1, tied for the day's
  gentlest line — "the remission entered its second week" — season 25 still league-worst.
  Track act six honestly; remissions end or hold.
- **The recusal bit** (Curtis Knudson, site owner): budget ≤ 2 per edition, vary the wording.
  2026-07-17 used "declines to recuse himself" (crown chase) and "offers no further comment"
  (dynasty). 2026-07-24 used the debits page (13-for-14 · 3 CO — "entered under assets and
  liabilities alike; he declines to recuse himself from either column") and the dynasty note
  (the Knudsons took the first-family title BACK, .618 to the Williams .594 — "records the
  finding and offers no further comment"); the crown section pointedly played him straight
  ("the desk refers readers to the debits page").
- **Sean Hammon's fairy tale is CLOSED** (2026-07-17: hitless afternoon, lost the R12 Dream Team
  seat to Sharon Hammon; "the mean he was regressing toward is above him"). Do not resurrect
  without a genuine second act — a comeback would BE the story, not the gag. The 2026-07-28
  alibi audit **acquitted** his June of schedule inflation (hot block vs the D2/D4 defenses;
  his club never met Michael's team; slate 11.19 ≈ league mean) — "the audit merely corrects
  the cause of death." The file stays closed; cite the audit rather than reopening it.
  2026-07-24: he REBOUNDED in the ledger (3-for-6, .500 vs his .429) — handled in one dry
  line ("the desk notes the pulse and moves on"), file still closed. A .500 afternoon is not
  a second act.
- **Becky Wood, #144**: "still technically a bargain" is now "doing heavy lifting" (0-for-5,
  #139). 2026-07-28: the audit found she has also faced the league's softest slate (12.36 opp
  RA/G, most generous among 15+ AB regulars) — "no alibi in either direction." 2026-07-24:
  1-for-4, swing exactly .000 against her own .250, rank #141 — "files another extension."
  Keep tracking; never invent numbers for her.
- **The invoice** (Stafford's team's luck): opened +.243 (July 10), first installment
  collected 2026-07-17 (+.200, slid #2→#4). **2026-07-24 — THE PAYOFF: re-inflated to +.220
  AND took first place** (2-0 day, the 11–10 escape past Caleb's club; SOS played .423,
  softest in the league) — the whole edition ("The Ledger") was built around the bill.
  Each edition: pay it down or re-inflate it, with the actual Luck number. The rematch
  collateral: Caleb–Stafford twice more (Jul 31, Aug 14), Jeremy–Stafford never yet met
  (first meeting Jul 31).
- **New seeds from 2026-07-17**, updated 2026-07-24: "the league owes Ephraims Daniel's club"
  — PAID AGAIN (luck −.233 worst in book; batted .627, second-best of the day, and went 0-2
  to run the slide to five). Jeremy's team "the quietest hot team" — the bill came due:
  streak stretched to a record 7 then snapped the same afternoon, season line down .621→.576
  while the standings barely noticed. "The 1.000 club is closed" — REOPENED 2026-07-24 with
  two members (Gideon Hammon 6-for-6, Ryan Hammon 7-for-7); the club now opens and closes by
  the week, and got its own front-of-book bulletin box (`thousand-club`) at the owner's
  request (2026-07-29). **Owner fact: Ryan Hammon is over 40** — the bit is the forty-plus
  elder running circles around the young guys, prouder of the 1.000 than of the birthdays.
  Keep the age qualitative ("forty-plus") unless Curtis ever supplies a number. New seed:
  **the Cawley family record** — .800, best family week ever, set by a
  family of three with one bat swinging (Lorenzo 4-for-5; Seth and Sophia sat) — the
  smallest-family absurdity is the bit; keep it honest.
- **The Disclaimer** (2026-07-24 edition, owner facts 2026-07-29): in the Jul 24
  Horatio-vs-Claude upset (the 3:30 South game, 7–5), **the umpire ruled a home run foul;
  the batting club objected; SOME on the other team agree it was a bad call; the umpire
  acknowledged the bad call. Per the owner, Horatio's team should have won.** Owner
  refinement (same day): do NOT claim the winning club agrees they should have won, and do
  NOT infer the umpire's or the opponents' feelings — print acknowledgments as facts, no
  attitudes. Filed as `the-disclaimer`, an h3 notice at the foot of the scoreboard,
  linked from the upset ticket's t-note. **Tone (owner's instruction, 2026-07-29: "make it
  seem like I'm a little more jaded"): strained neutrality** — the editor bats for the
  wronged club, and the desk insists it is calm at slightly elevated volume ("Fine.
  Entered." / "a neutrality unrelated to which club the editor bats for"). Rules of the
  bit: the umpire stays anonymous and is treated kindly (acknowledgment stated as fact,
  never dramatized); the score/standings/data NEVER change — the ledger prints the game as officiated and
  the testimony beside it. The note ends with a standing vow to re-raise the matter "in
  every future edition in which these two clubs appear on the same line" — HONOR IT: any
  future Horatio-vs-Claude line gets a dry callback.
- **The Mike Williams Benchmark** (debuted 2026-07-24 as "The Williams Line," renamed same
  day at the owner's request): the Mendoza-Line parody — a "league benchmark" set at Michael Williams's season average (.556 at debut;
  R1, captain, SS), with an honor-roll table of every confirmed woman batting above it
  (women rows shaded, a dashed `.wline` row draws the benchmark, Mike sits muted beneath as
  "the benchmark"). At debut: Violet Barlow (.655), Maureen Williams (.615), Deborah
  Timpson (.571 — the owner asked for Debbie by name). **Framing mandate: FEMALE
  EMPOWERMENT** — celebrate the women (the Violet/Maureen top-two-underdrafted fact is the
  engine), crack wise at Mike gently; never "batting better than a girl" energy. The SS
  courtesy is extended per house rule, with the kicker "Debbie Timpson does not need it."
  Selection is computed from `FEMALE_GIVEN` + rank above Michael's — **Sidney Dockstader
  and Leslie Williams (both on Michael's OWN roster) also sat above the line at debut but
  are on the never-guess-gender list; ask Curtis before ever adding them.** If the bit
  recurs, the benchmark moves with Mike's average — recompute honestly.
- **The Trainer's Table** (debuted 2026-07-24, owner request 2026-07-29): the editor's
  brothers teased as men of eighty outperforming their charts — **owner facts: Derrick
  Knudson has a weak ankle; Nathan Knudson cramps constantly; Levi Knudson is heavier set
  with weak knees (and is the Slamma Jammas' SHORTSTOP — the best joke writes itself)** —
  plus Sam Guy, included "for fun" with **no ailment supplied: never invent one for him**;
  he is the "suspiciously fit control group." Tone mandate from the owner: "nothing
  tasteless" — keep it kind; the caption's "the batting is real; the medicine is editorial"
  is the standing disclaimer. Statuses (DAY-TO-DAY / PROBABLE / QUESTIONABLE / SUSPICIOUSLY
  FIT) are the desk's own. Recurring only if Curtis feeds it; escalate the charts honestly
  (a bad afternoon = a setback in physio, a hot one = medically unexplained).
- **The Second Opinion** (debuted 2026-07-24, owner request 2026-07-29; `second-opinion`,
  an h3 coda at the foot of `mw-benchmark` — moved there from `trainers-table` at the
  owner's request — styled as a prescription pad, `.rx-card`; the lead-in frames it as a
  medical review of the benchmark's condition, referred to the league's only physician,
  who is also a Williams): **owner
  facts: Ben Williams (Boyds Daniel's team, R4) is a doctor — a great one; his father is
  Charles "Charlie" Williams (Stafford's team), age 65 exactly (owner-supplied, printable,
  unlike Ryan's qualitative "forty-plus").** The bit: praise the doctoring, roast the
  batting — the physician who can treat everyone but the hitter in his own mirror, while
  dad posts league-leading workloads at 65. The father-son link is owner-sourced, not in
  the data. If it recurs: a Ben hot week = "responding to treatment"; Charlie stays the
  elder-statesman engine alongside Ryan Hammon.
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
