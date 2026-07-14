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
  excluded from family grouping. **Sorted best-to-worst by family average** (owner's rule,
  2026-07-13 — not by family size); the digest prints it in that order.
- **Report card** = Σ z across a roster. Bar widths = |z| ÷ scale × 50%; scale = max(6, ⌈max|z|⌉),
  stated in each page's legend. Letter grades are editorial, assigned monotonically.
- **Meter bars** (round averages): width = avg × 100%. Histogram bars: width = count ÷ max × 100%.
- **Min-AB filters** (stated in each page's footnote): current-edition sleepers 15 AB / outliers
  10 AB; early-season editions used 10 / 6. Movers: 8+ AB at the old snapshot AND 15+ at the new.
  Period bats: 10+ period ABs. Scale these sensibly as the season accumulates at-bats.
- **Period rate** ("what did they hit between snapshots") = (ΔH − ΔCO) ÷ ΔAB.
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

Masthead (kicker · title · methodology sub · edition nav) → "Jump to" TOC nav → The Headlines →
**Team Temperature** (unnumbered "This Week" section at the top — the week-over-week team
diverging bars live HERE, not in What Changed; rebuild it each edition. **Thermal palette,
owner's rule 2026-07-13: red = warmer, blue = cooler**, via the `.rc-card.temp` CSS override;
its value text is plain ink, no zpos/zneg. The Report Card keeps the default mapping,
blue = outperformed) → **The Batting Race**
(unnumbered "The Chase" section, id `race` — top 3 by avg with "hits back"; note any lead
change against the ARCS race history) → **The Standings** (unnumbered "Scoreboard" section,
id `standings` — W-L-T/PF/PA/diff/**Pyth/Luck** joined to team batting, from the weekly
standings snapshot; `--standings NEW.csv --prev-standings OLD.csv` prints the digest + emits the
table rows, with movement arrows ▲▼ once a previous snapshot exists) → S1 League at a Glance (tiles) →
S2 Draft Board round averages → S3 Sleeper File → S4 Team breakdown +
Draft-Day Report Card → S5 Draft Board Second Look (risk-only: spread/bust-rate/discipline +
early-vs-late team split; re-pricing belongs to the Verdict) → S6 The Back Office (id
`missing-pages` — caused-out ledger, **Clean Hands Club**, workload, distribution) → S7 What Changed
(week-over-week, incl. **Streaks & Slides** (needs `--prev2`), Dynasty of the Week + **the
Records Board** — weekly bests that future
editions try to break; update it whenever a record falls) → S8 Team Sheets (best/worst pick per
team by z; hot/cold bat of the week per team vs the round's period rate) → S9 The Verdict
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

**Anchors:** every section has a stable id (`temperature`, `race`, `standings`, `glance`,
`draft-board`, `sleepers`, `teams`, `second-look`, `missing-pages`, `what-changed`,
`team-sheets`, `verdict`, `round-rooms`, `dynasty`, `watch`) with a self-linking
`<h2><a href="#id">`; each round-room h3 is
`round-1`…`round-12` (the `--html-tables` emitter produces these). **Every table also has an
h3 anchor** listed in the Jump-to nav (grouped into four lines): `tier-1`, `tier-2`,
`report-card`, `mined-rounds`, `caused-outs`, `clean-hands`, `iron-horses`, `league-shape`,
`hot-bats`, `cold-bats`, `movers`, `streaks`, `dynasty-week`, `records`, `team-picks`,
`team-week`, `priced-right`,
`bargains`, `didnt-justify`, `dream-team`, `captains-mirror`, `full-docket`. New tables must
get an id + nav entry. Keep ids stable across
editions — people share deep links. The "Jump to" TOC after the masthead lists every section;
add new sections to it.

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
   Then generate the bulk tables: the same command with `--html-tables` emits page-ready HTML for
   the Standings table (with ▲▼ movement arrows and Pyth/Luck), the Batting Race, Clean Hands,
   Team Sheets A/B, the Verdict tables, all 12
   Round Rooms (with This Week column, nicknames, hl/lo tinted rows), Dynasty-of-the-Week rows,
   and Streaks & Slides rows —
   splice these into the page wholesale instead of hand-typing the tables.
   (`--names-from COMMA_FORMAT.csv` canonicalizes names when the target file is the no-comma schema.)
4. **Rewrite `index.html`** from the current-snapshot digest: headlines, tiles, every table,
   report card, dynasty ledger, the Back Office, Second Look. Write a **fresh What Changed** from
   the comparison + ARCS digests against the
   just-archived edition (check the Records Board — update any record that fell, including the
   CO categories). Replace the Team Sheets / Verdict / Round Rooms
   table bodies with the freshly emitted HTML and rewrite their editorial notes. Rewrite
   **What to Watch** with next edition's stakes (only already-printed numbers). Update the masthead
   nav and the footnote's Editions list (add the new archive link; keep old ones).
5. **Transcribe, don't compute.** Every number on a page must appear in script output. If a number
   you want isn't printed, extend `analysis.py` rather than doing arithmetic by hand.
6. **Verify** (checklist below), then STOP and hand off — **do not commit, do not push.**
   Tell Curtis what changed (new CSV + new archive + index + any script changes) and leave
   everything in the working tree; he commits and pushes himself.

## Verification checklist

- Re-run both script modes; spot-check each page section against the printed digest.
- `python3 -c "import html.parser, pathlib; ..."` — parse every HTML page (index + all
  archives) for tag balance (or any HTML validator available). Void/self-closing tags
  (`<meta/>`, `<link/>`) need a parser that handles `handle_startendtag`, or they false-alarm.
- `grep -n 'href=' *.html` — every internal link relative; new archive reachable from index
  (masthead + footnote) and index reachable from the archive.
- `python3 -m http.server` from the repo root and eyeball index and the newest archive, light
  and dark (`prefers-color-scheme`), plus the ≤560px mobile breakpoint. Wide tables (the
  13-column Standings, the Full Docket) must scroll inside `.table-scroll`, not the page.
- Archive page: masthead shows its snapshot date; no references to data newer than that date.
- `git status` — nothing intended left untracked, then hand off. **Never run `git commit` or
  `git push` — Curtis handles all git operations himself.**
