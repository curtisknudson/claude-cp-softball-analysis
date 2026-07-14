# CP Softball — Weekly Stats Site

Editorial stats site for a church softball league, published on **GitHub Pages** from
`curtisknudson/claude-cp-softball-analysis` (remote `origin`, SSH). Roughly weekly Curtis says
the new numbers are up; Claude harvests them from cpsoftball.com into a fresh stats CSV (see
**Harvesting stats** below), and each snapshot becomes a new "edition" of the site.

- **No build step, no JS** (single exception: the GoatCounter analytics snippet before `</body>`
  on every page — `https://cp-softball.goatcounter.com/count`; keep it when creating archives).
  Every page is hand-authored static HTML with inline CSS.
- **Custom domain:** the site is served at **https://softball.best/** (the `CNAME` file; GitHub
  Pages serves custom domains at the domain root, so the old `/claude-cp-softball-analysis/`
  project-pages prefix no longer applies). Internal links must still be **relative**
  (`2026-06-12.html`), never root-absolute (`/foo.html`) — that keeps every page working at any
  serving root. The head's canonical/OG/Twitter URLs are deliberately absolute on
  `https://softball.best/` (og.png lives at the repo root); update them only if the domain changes.
- **Claude NEVER commits or pushes — no `git commit`, no `git push`, ever. Curtis handles all
  git operations himself** (owner's explicit rule, 2026-07-13). Leave finished work in the
  working tree and stop. If Curtis ever asks for a suggested commit message: plain text, no
  Claude co-author or attribution lines.

## Files

| File | What it is |
|---|---|
| `index.html` | The **current edition** — always the latest snapshot, includes a "What Changed" section vs the previous one |
| `YYYY-MM-DD.html` | Frozen **archive editions**, named by data snapshot date (e.g. `2026-06-12.html`) |
| `MMDD-stats.csv` | Raw snapshots as uploaded (e.g. `0612-stats.csv`, `0703-stats.csv`) |
| `MMDD-standings.csv` | Weekly standings snapshots hand-saved from https://cpsoftball.com/standings.php (`rank,team,w,l,t,gp,win_pct,pf,pa,diff`; first one: `0706-standings.csv`) |
| `analysis.py` | **The single source of truth for every number on every page.** Stdlib-only Python 3 |
| `pyrightconfig.json` | Type-checker settings (`typeCheckingMode: "standard"`). basedpyright's *default* mode assumes a fully-annotated codebase and fires ~1,500 `reportUnknown*` warnings at this script's plain-dict records — none of them defects. Under `standard` it's 0 errors / 0 warnings. Schema is enforced at **runtime** instead (`load()` exits loudly), which is the right tool for external CSVs |
| `CNAME` | GitHub Pages custom-domain file (`softball.best`) — never edit or delete |
| `favicon.svg` · `apple-touch-icon.png` · `og.png` | Site chrome: favicon, iOS home-screen icon, social-share card (og.png is referenced absolutely as `https://softball.best/og.png` from every page's meta block) |

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

## Harvesting stats (source: https://cpsoftball.com/stats.php)

The weekly numbers are read off the league's live **Complete Batting Statistics** table (all 144
players), not emailed as a file. To produce `MMDD-stats.csv`:

- **Ask Curtis for the name of the file before querying.** He gives the `MMDD` (e.g.
  `0710-stats.csv`); that `MMDD` is the data-snapshot date and his "go" that the week is posted.
  Never guess the date or assume today's — wait for the filename.
- The page's columns `# · Player · Team · Pick# · AB · H · CO · AVG` map **exactly** onto CSV
  **schema 1**: `rank,player,team,draft_pick,at_bats,hits,caused_outs,adjusted_avg`. Names already
  read `"Last, First"` — keep the comma (it forces CSV quoting, so quote every name field). This
  is the schema to emit; don't reshape to the no-comma schema 2.
- **Match the existing `-stats.csv` files byte-for-byte in style:** averages 3-decimal padded
  (`0.700`, `0.500`, `0.091`, never `0.7`), and **CRLF** line endings including a trailing CRLF.
  (Existing files are CRLF; the Write tool emits LF, so convert — e.g. write with
  `open(dst,'w',newline='').write('\r\n'.join(lines)+'\r\n')`.)
- Fetch with **WebFetch** (curl is blocked in this sandbox). Its extractor is a small model, so
  **validate before trusting the numbers** — do not skip this:
  - Formula holds for every row: `adjusted_avg == round((H − CO) / AB, 3)`. The site rounds half
    **up**, so exact-half cases (0.5625→`.563`, 0.3125→`.313`) look like a 0.001 "mismatch" under
    Python's round-half-to-even. Keep the **site's** value; these are not transcription errors.
  - **Totals must equal the page's own Season Summary footer** (Σ AB / Σ H / Σ CO / league avg) —
    the strongest end-to-end check that no row was dropped or misread. (0710: 4,003 AB · 2,364 H ·
    136 CO · league adj .557.)
  - `(team, draft_pick)` unique across a 12×12 grid; every team holds picks 1–12; ranks 1–144
    contiguous; 12 teams. Then run `python3 analysis.py MMDD-stats.csv` — it must **exit 0 with no
    WARN lines** (it independently re-asserts schema, formula, and join keys).
- Grab the standings the same day too: https://cpsoftball.com/standings.php → `MMDD-standings.csv`
  (columns per the Files table / weekly procedure step 3).

**Known unharvested source** (verified 2026-07-13): https://cpsoftball.com/schedule.php lists
every **completed game with its final score** — date, both teams, score, time, field,
FINAL/TIE, and notes like "Sub Rule Infraction Forfeit" (60 of 120 games done at that date).
Harvesting it would unlock win/loss streaks, close-game vs blowout splits, head-to-head grids,
and strength of schedule. **Ask Curtis before harvesting it** (same discipline as stats.php);
if harvested, the built-in check is that each team's summed scores must equal the same-day
standings PF/PA exactly.

## Captains (source: https://cpsoftball.com/teams.php — fetched 2026-07-06, no need to refetch)

**RULE CHANGED 2026-07-14 (owner): the league's team names are NOT used on the page at all.
Every club is named by its captain — `Gideon's team`, `Horatio's team` — and nothing else.**
Curtis doesn't like the team names ("I hate the usage of the team name anyway"), and the old form
(`Good Guys (Gideon's team)`) made every sentence in the week prose open with a six-word noun
phrase. So: no `Good Guys`, no `Pliggas`, no `Youre Saying Theres A Chance` anywhere in a page —
not in tables, bars, prose, captions or tooltips. `team_label()` in analysis.py is the single
implementation (it warns if a team is missing from `CAPTAINS`, i.e. a roster change — refetch
teams.php only then). **Verify with a grep**: no stripped team name may survive in `index.html`.

The raw names still key every join and still print in the **text digest**, where they match the
CSVs — that's the author's tool, not the page. Archives stay frozen in the old style; don't
retro-edit them.

**Possessives:** the old "possessive forms are exempt" carve-out is retired along with the team
names — there's no suffix left to omit. Just avoid the double possessive: write "the six caused
outs on Gideon's team" or "the regret seat on Ephraims Daniel's team", not
"Gideon's team's six caused outs". `team_label()`'s output is a noun phrase; treat it like one.

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

Shortstop is the league's premium defensive position; 11 of the 12 are round-1 picks. A
shortstop's draft price partly buys defense that batting stats can't see — **temper
"overdrafted/didn't justify" verdicts for these names** and tag them `· SS` in Verdict tables
(`SHORTSTOPS` set + `is_ss()` in analysis.py):

Hammon, Gideon (GG) · Williams, Horatio (YS) · Dockstader, Sefton (LL) · Hammon, Elliot (EL) ·
Timpson, Claude (PL) · Williams, Michael (PLA) · Guy, Sam (SS) · Dockstader Ephraims, Daniel
(DA, R4) · Williams, Daniel (PB) · Knudson, Levi (SJ) · Dockstader, Adam (FS) ·
Dockstader Boyds, Jeremy (DD)

**Change 2026-07-13 (per Curtis): Stafford Hammon no longer plays shortstop; Adam Dockstader
(the Fellowship's R1 pick) does.** Editions before July 10 tagged Stafford `· SS` — archives
stay frozen as published; don't retro-edit them.

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
  excluded from family grouping. **Sorted best-to-worst by family average** (owner's rule,
  2026-07-13 — not by family size); the digest prints it in that order.
- **Report card** = Σ z across a roster. Bar widths = |z| ÷ scale × 50%; scale = max(6, ⌈max|z|⌉),
  stated in each page's legend. Letter grades are editorial, assigned monotonically.
- **Meter bars** (round averages): width = avg × 100%. Histogram bars: width = count ÷ max × 100%.
- **Min-AB filters** (stated in each page's footnote): current-edition sleepers 15 AB / outliers
  10 AB; early-season editions used 10 / 6. Movers: 8+ AB at the old snapshot AND 15+ at the new.
  Scale these sensibly as the season accumulates at-bats.
  **Period tables (rescaled 2026-07-14):** perfect weeks and week swings **4+ ΔAB**
  (`--min-ab-perfect`, `--min-ab-swing`); the hot/cold period-rate digest list **6+**
  (`--min-ab-period`, default changed 10 → 6); the **Records Board keeps its stricter 10+**.
  Justification: in a two-game week ΔABs run 3–17, median 7, and nobody takes 1 or 2 — a 10-AB
  gate left **6 of 121 batters**, which also made the digest print the same six players as both
  HOT and COLD (fixed 2026-07-14; `k = min(10, len(pq) // 2)`).
- **Period rate** ("what did they hit between snapshots") = (ΔH − ΔCO) ÷ ΔAB.
- **Week swing** (added 2026-07-14) = period rate − the player's/team's **own season average at
  the previous snapshot**. This is the front of book's governing statistic — the Collapse, the
  Surge and the Team Temperature bars all draw it. It is **not** Δ season average:
  `Δ season avg = swing × (ΔAB ÷ total AB)` — the same signal damped by how small the week is
  next to the season (0.21 on July 10, and shrinking every edition).
  **Never put Δ season average on a chart: it measures the calendar as much as the softball.**
  Δ season average belongs in `#movers`, where the season line is the subject.
- **Team Temperature bars** (rule changed 2026-07-14): width = |swing| ÷ scale × 50%;
  scale = `max(.200, next .05 above max|swing|)`, stated in the legend (mirrors the Report Card's
  `max(6, ⌈max|z|⌉)` idiom). The old Δ-season-average scoping is **retired** — it put the biggest
  bar at 11% of its track and got *less* sensitive every week. `temp_scale()` in analysis.py.
- **Week-line notation** (added 2026-07-14): a week is written as a line — `7-for-7`, or
  `2-for-5 · 2 CO` when caused outs erased hits. **The hits are raw; the rate is net.** That is
  why a 2-for-5 week with two caused outs is worth .000 — any table that can show this **must**
  explain it in its caption. `week_line()` in analysis.py.
- **League rank**: the file's `rank` column when present, else avg desc → AB desc → name asc.
- **Pyth / Luck** (standings, added 2026-07-13): Pyth = PF² ÷ (PF² + PA²) — the win% a team's
  points profile "earns"; **Luck = actual win% − Pyth** (positive: out-running the points;
  negative: owed wins). Printed by the standings digest and emitted as two columns.
- **Batting Race**: top 3 by avg, min 15 AB. **"Hits back" = (leader avg − avg) × own AB** —
  the gap at the chaser's own volume. Digest prints it; ARCS prints each snapshot's leader
  (min 10 AB) for the lead-change history.
- **Streaks & Slides** (needs three snapshots; `--prev2 OLDEST.csv`): a streak = second-period
  rate above BOTH the first period's rate and the player's own season avg (slide = mirror),
  6+ period ABs in each period. Page shows top 6 each; the ARCS digest also prints team arcs
  (same rule at team level) and the race history.
- **Clean Hands Club**: zero CO all season, ranked by AB desc (top 8 shown). The praise-side
  counterweight to the caused-out ledger — keep both.
- **Records Board CO categories** (added 2026-07-13): most caused outs in a week, team (+9,
  Good Guys, Jun 12→Jul 3) and player (+3 shared, Roy Hammon Jun 12→Jul 3 / Noah Dockstader
  Jul 3→Jul 10). The CO WATCH block in the compare digest prints each period's numbers.
- **True-round Move arrows** (added 2026-07-13): every Verdict table with a True Rd column
  (Priced Right, Bargains, Didn't Justify, Captain's Mirror, Full Docket) carries a ▲▼= Move
  cell = previous snapshot's true round − current true round, each snapshot ranked against its
  **own** league average (i.e. what each edition published). Emitted only when `--prev` is
  given — archive pages have no Move column. The compare digest's TRUE-ROUND MOVERS block
  prints the churn count and top movers; most moves are ±1 (noise), ±3+ is news.
- **Dream Team seat changes** (added 2026-07-13): with `--prev`, any Dream Team row whose
  (team, pick) differs from the previous edition's occupant for that round is tagged
  `· in for <prev name>` inline in the player cell (both editions' teams computed on their own
  values, coed rule enforced). The compare digest's DREAM TEAM CHANGES block prints each IN/OUT
  pair with both editions' values. No `--prev` → no tags (archive pages).
- **Digest-only outputs** (printed for reference; on no page since 2026-07-13): the ROUNDS
  table's re-draft/keep columns and the OUTLIERS PER ROUND block. The page retired them —
  Second Look is risk-only, and each round's best/worst live in the Round Rooms' tinted rows —
  but keep them in the digest: they still inform the room notes and hl/lo commentary.

## Page anatomy (index.html)

**Restructured 2026-07-14, and this is now the template.** Readers said the July 10 edition read
like the July 3 one; the cause was structural, not stylistic. The page opened with season-to-date
content and buried the week two-thirds down, and every week fact on it was expressed as a *delta
on a season aggregate* — a signal damped by ΔAB/total AB (0.21 and falling), which is why Team
Temperature's range was ±.028 when the week's was ±.163. The paper now runs in **four movements**:

| | Movement | Sections | Scope rule |
|---|---|---|---|
| **I** | **The Week** | `the-week` · `week-bats` · `temperature` · `standings` | Prose narrates **only this week's games** |
| **II** | **The Season** | `glance` · `race` · `draft-board` · `sleepers` · `teams` · `second-look` · `missing-pages` | **Prose may not narrate the week.** May carry a This Week *column* |
| **III** | **The Ledger** | `what-changed` | What the week *did to* the season lines |
| **IV** | **The Book** | `team-sheets` · `verdict` · `round-rooms` · `dynasty` · `watch` | Reference |

Movement II's scope rule is the biggest de-duplication lever on the page — enforce it.

Masthead (kicker · title · methodology sub · edition nav) → "Jump to" TOC nav → The Headlines
(**week-first**; write them LAST, and apply the same-y test in the procedure below) →

**MOVEMENT I — THE WEEK.**
**The Week** (id `the-week`, eyebrow names the games — "Games 9 and 10") — the week's own box
score: `.tiles` (games · ABs · league avg this week · caused outs/season · perfect weeks · never
batted), callouts, then h3 `week-co` (**the caused-out ledger for the week**, 12 rows, `hl` on the
clean clubs / `lo` on the worst) and h3 `playing-time` (who played, who sat — notes only; the
ΔAB=0 list and the rep-surge list are one story) →
**The Week's Bats** (id `week-bats`) — h3 `perfect-weeks` (rate 1.000: no out made, none caused),
h3 `cold-bats` = **The Collapse** and h3 `hot-bats` = **The Surge**. ⚠️ `hot-bats`/`cold-bats` kept
their ids when they moved here from What Changed (people deep-link them) but **changed metric**:
they now rank by **week swing**, not raw period rate. A .875 week from a .833 hitter is not news →
**Team Temperature** (id `temperature`) — the diverging bars now draw **swing** (week rate − the
club's own season line), NOT Δ season average; see Analysis conventions. **Thermal palette,
owner's rule 2026-07-13: red = warmer, blue = cooler**, via the `.rc-card.temp` CSS override; its
value text is plain ink, no zpos/zneg. (The Report Card keeps the default mapping,
blue = outperformed.) Carries h3 `team-box` — the week team by team (ΔAB/ΔH/ΔCO, week avg, own
season line, gap, week record, week run diff, rank move): the receipts under the bars, and the
home of the bats-vs-points correlation →
**The Standings** (id `standings`) — the 13-column season table (W-L-T/PF/PA/diff/**Pyth/Luck**
joined to team batting; `--standings NEW.csv --prev-standings OLD.csv` prints the digest + emits
the rows with ▲▼ movement arrows). **The table is the season; its notes are the week** — who
moved, who took first, who finally won. The week's *records* do not go in this table; they live in
`team-box`, which keeps the Standings at 13 columns.

**MOVEMENT II — THE SEASON.** Opens with S1 League at a Glance (tiles; its lede marks the pivot —
"That was the week. Here is the season."), then **The Batting Race** (id `race` — top 3 by avg
with "hits back"; note any lead change against the ARCS race history). **`glance` and `race` are
reference, not news** — the race's top three rarely change week to week, and leading with an
unchanged leaderboard *is* the sameness problem. Then
S2 Draft Board round averages → S3 Sleeper File → S4 Team breakdown +
Draft-Day Report Card → S5 Draft Board Second Look (risk-only: spread/bust-rate/discipline +
early-vs-late team split; re-pricing belongs to the Verdict) → S6 The Back Office (id
`missing-pages` — **season** caused-out ledger, **Clean Hands Club**, workload, distribution; the
*week's* caused outs belong to `week-co`, not here) →

**MOVEMENT III — THE LEDGER.** S7 What Changed (id `what-changed`, eyebrow "The Ledger", h2
"What Changed: the Season Lines") — **what the week did to the season, not what the week was.**
Its hot/cold period-bat tables moved to `week-bats` in 2026-07-14; **do not re-add them**, and do
not restore its tiles strip or its "the league cooled" callouts (those facts belong to `the-week`).
It keeps `movers` (Δ season avg — literally "how the season stats changed because of this week",
which is exactly what belongs *here* and not up front; its lede should say so), **Streaks & Slides**
(id `streaks`, needs `--prev2` — the only thing on the page that knows trajectory, and the sole
home of the Sean Hammon gag), Dynasty of the Week, + **the Records Board** — weekly bests *and
worsts* that future editions try to break; update it whenever a record falls →

**MOVEMENT IV — THE BOOK.** S8 Team Sheets (best/worst pick per
team by z; hot/cold bat of the week per team vs **the round's** period rate — this table is
*round*-relative, and is NOT the same as `team-box`, which is *self*-relative. Don't conflate
them) → S9 The Verdict
(**value** = (avg − league adj) × ABs = net hits above a league-average bat, volume-weighted by
design; "true round" = value rank dealt into rounds of 12; tables: Priced Exactly Right,
Bargains/underdrafted, Didn't Justify/overdrafted, Dream Team = best value per round (rows tag
weekly seat changes `· in for <prev occupant>`), and the
**Captain's Mirror** = each captain's self-pick graded against their true round, and the
**Full Docket** = all 144 players in true snake-draft pick order (#1–#144) with
true-round/gap verdicts and a League # value-rank column, so every player can find their
own row; every True Rd column carries a ▲▼= **Move** cell vs the previous edition's true
rounds; shortstops tagged · SS with a defense caveat) → S10 The Round Rooms (12 tables, every player by round,
season z + This Week column; each room's h3 carries its standing nickname from
`ROUND_NICKNAMES` in analysis.py — Penthouse/Second Story/Money Pit/Suburbs/Flats/Bump/
Mezzanine/Casino/Spill Zone/Pothole/Attic/Floor — and the emitter tints the top row `hl` and
the cellar row `lo`) → Appendix Dynasty Ledger → **What to Watch** (unnumbered "Next Week"
section, id `watch` — three concrete stakes for the next edition, built only from
already-printed numbers) → methodology footnote.

(The old S4 "Outliers per round" section was retired 2026-07-13 — its content lives in the
Round Rooms' tinted rows and section notes. Don't reuse the `outliers` id.)

**Anchors:** every section has a stable id (`the-week`, `week-bats`, `temperature`, `standings`,
`glance`, `race`, `draft-board`, `sleepers`, `teams`, `second-look`, `missing-pages`,
`what-changed`, `team-sheets`, `verdict`, `round-rooms`, `dynasty`, `watch`) with a self-linking
`<h2><a href="#id">`; each round-room h3 is
`round-1`…`round-12` (the `--html-tables` emitter produces these). **Every table also has an
h3 anchor** listed in the Jump-to nav: `week-co`, `playing-time`, `perfect-weeks`, `cold-bats`,
`hot-bats`, `team-box`, `tier-1`, `tier-2`,
`report-card`, `mined-rounds`, `caused-outs`, `clean-hands`, `iron-horses`, `league-shape`,
`movers`, `streaks`, `dynasty-week`, `records`, `team-picks`,
`team-week`, `priced-right`,
`bargains`, `didnt-justify`, `dream-team`, `captains-mirror`, `full-docket`. New tables must
get an id + nav entry. Keep ids stable across
editions — people share deep links. The "Jump to" TOC after the masthead lists every section;
add new sections to it.

⚠️ **Ids that moved on 2026-07-14 and kept their names** (deep links must keep working):
`hot-bats` and `cold-bats` moved from What Changed to **The Week's Bats** and changed metric
(raw period rate → **week swing**); `playing-time` moved from What Changed to **The Week**.
`team-week` (Team Sheets, round-relative) and `team-box` (Temperature, self-relative) are
**different tables** — check which one you mean.

**De-duplication rules (added 2026-07-14 — this is what actually fixes "it reads the same").**
The July 10 edition narrated Cuervo's 6-for-6 in six separate prose blocks, the Diamonds' .667
team week in six, and the Good Guys' .421 in five. Readers don't hear a motif; they hear filler.
So:
1. **A number is narrated in prose exactly once.** Tables may echo what prose owns; two prose
   blocks (`.callouts` / `ul.notes` / `.lede`) may never narrate the same number. A two-period
   *arc* may restate an endpoint (`.591 → .421`) — that's a different claim from "they hit .421."
2. **The Headlines are the one licensed exception**, but a headline states a fact in one line and
   its section must then *develop* it with material the headline doesn't have.
3. **Movement II sections may not narrate the week.** They may carry a This Week *column* (the
   Round Rooms do). Their prose stays on the season.
4. **Break the mould.** Ban `**Bolded subject + verdict:** number, number, wry aside` from
   Movement I — the July 10 edition used it in nearly every paragraph and the eye learns it in
   thirty seconds. Rotate: bare declarative ("Lorenzo Cawley batted seven times in two games and
   did not reach base."), the reversal ("The Lefty Looseys went 2-0. They also hit seventy-two
   points below their own season line."), the list-as-indictment ("Rounds one, five, seven, nine,
   eleven. Five players, six caused outs, two games."), the withheld subject.
5. **Week prose is reportorial, season prose is judicial.** Week verbs: *went, hit, fell, sat,
   caused* — short, declarative, past tense, reporting events. Season verbs: *is, ranks, holds,
   prices*. Keep the season sections exactly as they are; they're right for what they do.
6. **Anchor every week fact to what it replaced** — `.765 → .675`, `#17 → #63`, `1st → 2nd`.
   A .333 week means nothing until you know the man was a .708 hitter.
6b. **Never write "points" without saying what they're points OF.** A point is a thousandth of an
   average, and there are TWO different quantities in play every week — they are not the same
   number and the prose must never blur them:
   - the **swing**: what a player hit *this week* vs his own season line (Evan Williams, −**598**);
   - the **season-line move**: what that did to his cumulative average (only −**90**).
   `swing × (ΔAB ÷ total AB) = season-line move`. Say "batted 598 points *below his own line*",
   never "lost 598 points *off his average*" — the second is simply false, and the July 10 draft
   shipped it in the headline next to `.765 → .675`, which made the two look like one number.
6c. **Every cross-edition superlative must be checked against EVERY prior period, with the
   script.** "The biggest X this paper has recorded" is a claim about all snapshots, not this one.
   Run `python3 analysis.py PREV.csv --prev PREV-PREV.csv` and compare. The July 10 draft claimed
   Riley Barlow's 46-place fall was the biggest ever; Lorenzo Cawley had fallen **68** the period
   before. Cheap check, and the true version is usually the better story — Cawley turned out to be
   on both collapse lists. (Verified for this edition: Evan's −.598 swing, the Diamonds' .667 team
   week, and the Good Guys' .421 / −.163 **are** records; the rank claims were not.)
7. **Say the games, not "the period."** "Games 9 and 10", never "between snapshots" /
   "week-over-week", in Movement I. It turns an abstraction into a thing that happened on a field.
8. **Name clubs by their captain, never by the team name** (owner's rule, 2026-07-14 — see
   Captains above). "Gideon's team hit .421 in games 9 and 10. Their season line is .584." Two
   words, not six. Lean on pronouns and possessives for the second reference; avoid the double
   possessive ("Gideon's team's six caused outs" → "the six caused outs on Gideon's team").

Archive pages mirror the above minus anything weekly (2026-06-12.html has S1–S5, S6 Team Sheets
season-only, S7 Round Rooms without the week column, + Appendix) — **no week-over-week content
and no foreshadowing**; each archive is honest to its date. **When archiving, delete the
What to Watch section outright** (it is pure foreshadowing) and remove its TOC entry.
Archives are fully self-contained (own copy of the CSS) so
they stay frozen if the current design evolves.

**Gag ledger** (keep bits consistent and escalating, not reset): the Good Guys' caused-out
tragedy is numbered in acts (July 10 edition = "act three"); the analyst "offers no further
comment" on Curtis Knudson (site owner) — at most twice per edition, vary the wording elsewhere
("declines to recuse himself"); the Sean Hammon R12 steal is now a *deflating* fairy tale —
track it down, not up; the round-6 bump; Becky Wood (pick #144) "still technically a bargain";
the Fellowship's luck is "an invoice in the mail" (opened 2026-07-13 at +.243 — pay it off or
double it next edition).

A gag that only works as a *season* observation stays in the season sections: Sean Hammon's
deflating fairy tale is narrated in `streaks` (its two-period arc is the joke) and nowhere else —
the Collapse table carries his row with no joke attached. The Curtis Knudson bit has to *earn* a
front-of-book mention with an actual week; if he doesn't make a week table, the gag stays in
`race` and `dynasty-week` and that's the whole budget.

## Weekly update procedure

1. **Harvest the new snapshot** into `MMDD-stats.csv` per **Harvesting stats** above (ask Curtis
   for the filename first; pull stats.php via WebFetch; validate formula + totals-vs-Season-Summary
   + join keys; match CRLF/3-decimal style). Run `python3 analysis.py NEW.csv` alone — it validates
   schema, formula, and join keys, and will exit with an error on format drift.
   Also fetch https://cpsoftball.com/standings.php and save it as `MMDD-standings.csv` (same
   columns as 0706-standings.csv; the loader asserts W+L+T=GP, PF/PA balance, win% = (W+T/2)/GP).
2. **Archive the current edition**: copy `index.html` to `YYYY-MM-DD.html` named for **its** data
   snapshot date (not today). In the copy: re-title/kicker it as an archived edition, add the
   "frozen snapshot" notice linking to `index.html`, and **delete the What to Watch section and
   its TOC entry** (foreshadowing doesn't archive). Keep whatever What Changed section it shipped
   with — it compares against an even older edition and remains true. Don't touch its numbers;
   only the masthead/nav framing changes.
3. **Run the full digest**: `python3 analysis.py NEW.csv --prev PREVIOUS.csv --prev2
   PREV-PREVIOUS.csv --standings NEW-standings.csv --prev-standings OLD-standings.csv`.
   Digests print for both snapshots, the comparison (incl. CO WATCH), the standings join
   (movement, Pyth/Luck, bat-rank deltas, win%↔batting correlation), and the ARCS digest
   (streaks & slides, team arcs, race history).
   The compare digest leads with the week — THE WEEK (league box score), PERFECT WEEKS, HITLESS
   WEEKS, WEEK SWINGS (the Collapse/the Surge + biggest rank climb & fall), PERIOD BATS, CO WATCH
   (incl. the ERASED list), WHO SAT, TEAM WEEK — and only then the ledger (SEASON-AVG MOVERS,
   TRUE-ROUND MOVERS, DREAM TEAM CHANGES). The standings digest adds STANDINGS WEEK (ΔW/ΔL, ΔPF/ΔPA,
   rank move, **bat-rank move**) and the week's bats↔points correlation.
   Then generate the bulk tables: the same command with `--html-tables` emits page-ready HTML,
   **in page order**, for the front of book (Week CO by team, Perfect Weeks, the Collapse, the
   Surge, the **whole Team Temperature `.rc-card`** including bar widths and legend scale, the
   Team Box), then the Standings (with ▲▼ arrows and Pyth/Luck), the Batting Race, Clean Hands,
   Team Sheets A/B, the Verdict tables, all 12
   Round Rooms (with This Week column, nicknames, hl/lo tinted rows), Dynasty-of-the-Week rows,
   and Streaks & Slides rows —
   splice these into the page wholesale instead of hand-typing the tables. **Nothing in the front
   of book is hand-typed.** (Before 2026-07-14 the hot/cold tables and the Temperature bars *were*
   hand-typed, because the digest was unusable at its own default gate — that is how the rule got
   broken and how a wrong "hottest bat of the week" reached print.)
   (`--names-from COMMA_FORMAT.csv` canonicalizes names when the target file is the no-comma schema.)
4. **Rewrite `index.html` in movement order — the week FIRST.** Write The Week, The Week's Bats,
   Team Temperature and the Standings notes from the compare digest, while the week is the only
   thing in your head. Then the season sections (tiles, report card, dynasty ledger, the Back
   Office, Second Look). Then the ledger: a **fresh What Changed** from the comparison + ARCS
   digests against the just-archived edition (check the Records Board — update any record that
   fell). Replace the Team Sheets / Verdict / Round Rooms table bodies with the freshly emitted
   HTML and rewrite their editorial notes. Rewrite
   **What to Watch** with next edition's stakes (only already-printed numbers). Update the masthead
   nav and the footnote's Editions list (add the new archive link; keep old ones).
   **Write the Headlines LAST** — they are an index of the week sections, not a preview of the
   season.
4b. **The same-y test.** Put the new headlines beside the previous edition's. **If any headline
   could be turned into last edition's by changing only the digits, cut it and go find a week
   fact.** (The July 3 and July 10 editions both opened on the draft-correlation r — a cumulative
   statistic over 4,000 at-bats. It *cannot* say anything new, ever.) Then run the de-dup grep in
   the checklist: if two prose blocks narrate the same number, one of them is wrong.
5. **Transcribe, don't compute.** Every number on a page must appear in script output. If a number
   you want isn't printed, extend `analysis.py` rather than doing arithmetic by hand.
6. **Verify** (checklist below), then STOP and hand off — **do not commit, do not push.**
   Tell Curtis what changed (new CSV + new archive + index + any script changes) and leave
   everything in the working tree; he commits and pushes himself.

## Verification checklist

- Re-run both script modes; **exit 0 with no WARN lines**; spot-check each page section against
  the printed digest. Confirm PERIOD BATS doesn't print anyone as both HOT and COLD (if it does,
  the gate is too high for the week — see Min-AB filters).
- **De-dup grep.** For each marquee number of the week, confirm it appears in **at most one**
  prose block (`.callouts` / `ul.notes` / `.lede`), plus optionally once in the Headlines. Tables
  don't count. A script that maps prose blocks → owning section id and greps each number across
  them takes two minutes and catches exactly the failure readers complained about.
- **Same-y test** (procedure step 4b): diff the new headlines against the previous edition's.
  No shared skeleton, no shared first fact.
- `python3 -c "import html.parser, pathlib; ..."` — parse every HTML page (index + all
  archives) for tag balance (or any HTML validator available). Void/self-closing tags
  (`<meta/>`, `<link/>`) need a parser that handles `handle_startendtag`, or they false-alarm.
- `grep -n 'href=' *.html` — every internal link relative; new archive reachable from index
  (masthead + footnote) and index reachable from the archive. Every `href="#id"` resolves, and
  no id is defined twice (`hot-bats` / `cold-bats` / `playing-time` moved once already — make
  sure a rewrite didn't leave a copy behind in What Changed).
- `python3 -m http.server` from the repo root and eyeball index and the newest archive, light
  and dark (`prefers-color-scheme`), plus the ≤560px mobile breakpoint. Wide tables (the
  13-column Standings, the Full Docket) must scroll inside `.table-scroll`, not the page.
- Archive page: masthead shows its snapshot date; no references to data newer than that date.
- `git status` — nothing intended left untracked, then hand off. **Never run `git commit` or
  `git push` — Curtis handles all git operations himself.**
