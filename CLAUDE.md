# CP Softball — Weekly Stats Site

Editorial stats site for a church softball league, published on **GitHub Pages** from
`curtisknudson/claude-cp-softball-analysis` (remote `origin`, SSH). Roughly weekly Curtis says
the new numbers are up; Claude harvests them from cpsoftball.com (stats, standings, and — since
2026-07-24 — the full game schedule with scores), and each snapshot becomes a new "edition" of
the site.

- **No build step; the PAPER pages carry no JS** (exceptions: the GoatCounter analytics
  snippet before `</body>` on every page — `https://cp-softball.goatcounter.com/count`; keep
  it when creating archives — and, since 2026-08-14, **owner-authorized interactive script,
  quarantined to dedicated app pages**: Playoff Prediction Brackets lives at `playoffs.html`,
  a stand-alone playoff bracket runner with its own broadcast-style design language
  (deliberate identity break, owner's brief: "not just within the standards of the app…
  make this fantastic" — then, on seeing v1, a full rejection and rebuild; read **The
  machine's second design** before touching that page). The standing terms: the owner opts in per feature; every number a
  script *displays* must derive from an analysis.py-emitted data island
  (`<script type="application/json">`, captain labels/slugs only — the team-name grep covers
  app pages too); libraries are **vendored locally, never CDN-hotlinked**
  (confetti.min.js — ISC, in the repo root); the page must degrade to an honest
  `<noscript>` notice pointing back at the paper; no network calls beyond GoatCounter, no
  accounts, state in URL hash + localStorage only. The newspaper pages themselves stay
  script-free and link to the app; do NOT reach for JS on ordinary modules.)
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
| `MMDD-brackets.csv` | **Contest entries** (`name,club,code,received`; first: `0821-brackets.csv`) — the desk's inbox, by hand. One row per verified entry: the player as the roster spells them, their captain slug, a 22-digit bracket code, and the ISO time the entry mail arrived. `load_brackets()` rejects a non-rostered name, a wrong club, an incomplete code, a duplicate player or a bad timestamp — hard exit, row named. **The prize is real money; a silently mangled entry is not an option** |
| `MMDD-playoff-results.csv` | **Played playoff games** (`game,winner` — bracket game number 1–22, raw team name; any subset, any order). This is the schema question the 08-14 notes left open: results ride their own file keyed by BRACKET GAME NUMBER, because `MMDD-schedule.csv` is a date/field slate with no game-number column. `load_playoff_results()` rejects a winner that did not play in that game, a result whose participants are not yet decided, a duplicate or an out-of-range game |
| `pyrightconfig.json` | `typeCheckingMode: "standard"` — 0 errors / 0 warnings must hold. basedpyright's default mode fires ~1,500 false `reportUnknown*` on this plain-dict script; standard is the right mode. Schema is enforced at **runtime** (loaders exit loudly) |
| `CNAME` | GitHub Pages custom-domain file (`softball.best`) — never edit or delete |
| `favicon.svg` · `apple-touch-icon.png` · `og.png` | Site chrome (og.png referenced absolutely as `https://softball.best/og.png` from every page's meta block). An edition MAY ship a special OG card as `og-YYYY-MM-DD.png` (first: `og-2026-07-24.png`, the "Ryan Hammon bat 1.000" tease, rendered with Pillow in the site palette scanned from og.png) — only that edition's index points at it; when the edition archives it keeps its card, and the next index reverts to og.png unless it ships its own |
| `dewegeli.png` | **The site's first content photograph** (owner-supplied 2026-08-12): Karl Franz Dewegeli Jr., 190×343 — the portrait framed in the Dewegeli Divide module (`.divide-fig`). Keep it when the edition archives; never crop, filter, or re-encode it |
| `darlene.jpg` · `marie-thomas-davis-dewegeli.png` | The rest of **the gallery** in the Divide module (`.divide-gallery`, `.dg-frame`): **Marie Thomas Davis Dewegeli**, 120×163 — Karl's wife, Elliot's **great-grandmother** (owner-supplied 2026-08-18) — and **Darlene Marie Dewegeli**, 578×760, their daughter, Elliot's **great-aunt** (she shipped 2026-08-14 mislabeled "grandmother"; corrected 2026-08-18 at the owner's instruction — she stays in the gallery, as the great-aunt watching too). Marie's scan is small, so her frame wears `.dg-sm` (215px tall, 168px on mobile) instead of the gallery's 275px; never upscale or re-encode the file itself. Same keep-on-archive rule as `dewegeli.png` |
| `yggr-og.png` | The **house-ad card** (1200×630, downloaded from yggr.xyz/images/og.png, 2026-08-12): "yggr — coffee for sats," the owner's company. Used by every `.adv` unit; self-hosted on purpose — never hotlink it |
| `playoffs.html` | **Playoff Prediction Brackets** — "the Seeding Machine" at debut, then "the Scenario Simulator", renamed again by the owner 2026-08-18 (2026-08-14; REBUILT the same day — see **The machine's second design** — and NARROWED 2026-08-18 once the finale was played — see **The machine's third cut**). Today it is a pure bracket-prediction page: the twelve posted seeds as a reference table, and the league's real 22-game double-elimination bracket, drawn, that you click through to a champion. Own design language (dark scorebug + gold; light scheme included). All numbers from the spliced `machine-data` island; self-checks against it. See the playoffs section below |
| `confetti.min.js` | Vendored library for playoffs.html (canvas-confetti 1.9.3 ISC — the pennant moment). Local on purpose, never CDN; app pages only, never the paper. (`anime.min.js` drove the seed table's FLIP reorder and was DELETED 2026-08-18 at the owner's instruction, once the posted seeding stopped moving.) |
| `og-playoffs.png` | The page's share card (1200×630, Pillow at 3× in a scratchpad venv — Pillow is NOT installed system-wide — then downsampled LANCZOS; simulator palette, Avenir Next Condensed Heavy + Menlo). **Re-cut 2026-08-19** at the owner's request to advertise the contest: gold top bar, the wordmark split ink/gold exactly as the page's topbar splits it, a filled GOLD PLAQUE reading **75,000 SATS** as the hero. The plaque is a BAND, deliberately wider than its words — the trailing gold is what gives it presence — so its right edge is chosen (616px) rather than measured, and two asserts guard it: that it still clears the bracket column at 654, and that the copy has not outgrown the band. Both fired for real when the satoshi sign was briefly added, and a PRESENTED BY yggr lockup in the footer. **Footer discipline (owner called the first attempt out, 2026-08-19): it is ONE row, everything centred on a single line — url left, sponsor right — at 19% of the card.** The rejected version stacked PRESENTED BY above the lockup and left a 64px dead zone beneath, spending a quarter of the card on 62px of ink. If it is ever re-cut, measure the bands before shipping (`np.abs(img-bg).sum(2)` per row finds the dead air immediately) and give reclaimed space to the plaque and the bracket, which are the message. **The yggr helm-of-awe mark and wordmark are LIFTED from `yggr-og.png` and recoloured** (alpha taken from the source's darkness so the antialiasing survives) — never redrawn, it is somebody's brand; "sats" keeps their own Bitcoin orange `#F7931A`, sampled from that file. **The standing principle survives both cuts: the visual DEMONSTRATES the mechanic rather than describing it** — the bracket is the one the page really draws (G1 5v12 and G2 6v11 feeding G8 and G7, which is genuinely where those winners go), two games already picked, one an 11-over-6 upset, ending on a gold YOUR CALL grand final. The two runs into G22 are drawn BROKEN, deliberately: G8 and G7 do not feed the final directly, and a trailer must not diagram a bracket the league is not playing. Keep both principles if it is re-cut. Referenced by playoffs.html only |

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
- **Players can be REPLACED mid-season; the (team, pick) slot carries on** with its cumulative
  counters (known case, owner-confirmed 2026-08-12: Layla Hammon left the league and Emmerson
  Hammon took the Slamma Jammas R10 slot — surfaced at 0807, where the slot's season line mixes
  both players; the 0724→0807 delta, 3-for-9, is Emmerson's play). So a cross-snapshot name
  mismatch is either a site-side correction or a replacement — ask Curtis which before anything
  prints. The slot's draft price bought the ORIGINAL pick; a replacement inherits the ledger,
  not the draft verdict — say so if their value line ever prints. (The site spells the new
  player "Emmerson"; the CSVs transcribe the site.)
- Surnames can be two words and given names multi-token; in the no-comma schema you cannot split
  names on whitespace — the script recovers the split by joining on (team, pick).
- Team names carry a "The " prefix except "Youre Saying Theres A Chance".
- **Display averages transcribe the FILE, never a recompute** — the site rounds half **up**
  (13-for-16 = .8125 prints **.813**); Python's round-half-even says .812. `disp()` in
  analysis.py exists for exactly this; the page must never show a .812-style artifact.

**The 0807 snapshot is a DOUBLE WEEK (the asterisk):** the league posted two weeks of stats at
once — the Jul 31 and Aug 7 afternoons — and no snapshot exists between them; per Curtis it is
filed as `0807-*.csv`. Every 0724→0807 "period" stat therefore pools TWO afternoons (four games
per club, roughly double the usual AB volume). The schedule still carries per-game scores, but
batting cannot be attributed to either afternoon separately — never invent a per-afternoon
split, and say the two dates (not "the afternoon of Aug 7") when that period's numbers print.
Scale AB gates and any per-afternoon framing accordingly when the 0807 edition builds.

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
Jun 5, 12, 19, Jul 3, 10, 17, 24, 31, Aug 7 (Aug 14 remains) — note there were NO games the
week of Jun 26, and the 0807 stats snapshot covers TWO game days (see the double-week note in
The data), so snapshots and afternoons don't align 1:1; trust the date inventory, not
assumptions. Each game day: 12 games,
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

## The playoffs (source: https://cpsoftball.com/playoffs.php — first fetched 2026-08-14)

- **12-club double elimination, August 21–22, 22 games as posted** (no if-necessary game in
  the book). Seeds 1–4 draw first-round byes; the opening round pairs 5v12 (G1), 6v11 (G2),
  7v10 (G3), 8v9 (G4); the byes host the winners (G5 = 1 v W4, G6 = 2 v W3, G7 = 3 v W2,
  G8 = 4 v W1); losers thread G9–G21; G22 is the grand final (W15 v W21). The full topology
  lives, identically, in the page JS `BR` table and the scratch generator used to build the
  bracket cards — every slot reference points at a lower-numbered game, so one forward pass
  resolves. **The bracket lists home/away designations — the first the league's paperwork has
  carried** (the regular-season schedule is listing-order only).
- **Seeding follows the standings** — the bracket posted before the Aug 14 finale matched the
  0807 standings exactly, and the RE-SEEDED bracket fetched 2026-08-18 matches the 0814
  standings rank column exactly (both verified against playoffs.php). **The final seeds:**
  1 Jeremy · 2 Caleb · 3 Horatio · 4 Sefton · 5 Stafford · 6 Claude · 7 Gideon · 8 Elliot ·
  9 Michael · 10 Boyds Daniel · 11 Ephraims Daniel · 12 Seth. Only 11/12 moved from the
  pre-finale posting (Ephraims Daniel's club up, Seth's down); the topology is unchanged and
  the site's own G1–G22 rows were re-transcribed to confirm it. **Two pairs finished level on
  points and the league separated them itself** (3/4 at 28, 11/12 at 8) — the pages say the
  league broke them and stop there. Do NOT print a theory of how: the tiebreaker is still
  unpublished, and with the seeds posted there is nothing left to guess. Re-fetch before
  harvesting playoff results.
- **analysis.py playoff desk** (added 2026-08-14): `playoff_futures()` exactly enumerates
  every remaining W/T/L outcome (guard: only when ≤ 13 games are SCHEDULED — a final-slate
  instrument, NOT midseason; returns None otherwise). Seeding by points (2W+T); the league's
  tiebreaker is NOT published, so every bound is doubled — optimistic (all ties break for the
  club) / pessimistic (all against) — and the gap is "tiebreak territory," said wherever the
  numbers print. **Never guess or invent the tiebreak**; the display convention for
  hypotheticals is "seated by the August 7 order and flagged ‡." `playoff_digest()` prints
  the PLAYOFF DESK block at the end of the AFTERNOON DESK digest (seed bounds, bye-miss
  counts, forced-result requirements via condition intersection, level-pair own-game races,
  R1 bracket as the table stands); `emit_playoffs` (registered FIRST in AFTERNOON_EMITTERS)
  emits clinch-board table rows AND the `machine-data` JSON island. **Only the island is
  live**: it is spliced into playoffs.html, which is the one page carrying playoff
  material (owner's call, 2026-08-14 — see the edition log). The clinch rows stay in the
  emitter in case the paper ever wants the board back in ink; today they go unspliced.
  The island carries asof/slate labels, final GP, the
  futures total, per-club records + ranks + best/worst seed + bye-miss counts (mo/mp), and
  the unplayed slate (captain labels + `cap_slug` slugs ONLY — raw team names must never
  reach any page, the island included).
- **The desk has TWO eras and `emit_playoffs` picks between them automatically** (2026-08-18).
  With a slate still unplayed it emits the futures island above. With the season complete
  `playoff_futures()` returns None and it delegates to **`emit_playoff_seeds`**, which emits
  the FINAL island — `{final, asof, days, bracket, teams:[{s, label, seed, w, l, t, pts, pf,
  pa, diff}]}`, nothing enumerated, captain labels and slugs only. It asserts the standings
  are seed-ordered 1..12, that games played are uniform, and that no game is still SCHEDULED,
  so a half-harvested book cannot cut an island. **`PLAYOFF_BRACKET`** (module constant) is
  the bracket topology and **ships INSIDE the island** — the page no longer carries its own
  copy, it does `var BR = data.bracket`, so the topology has exactly one home. The emitter
  checks it before it goes: every seed walks in exactly once, and every winner/loser
  reference points at a lower-numbered game (which is what lets one forward pass resolve
  the whole prophecy).
- **playoffs.html duties:** splice the new island in and the whole page follows — the UI is
  script-built from it, so there is no hand-typed seed anywhere. The self-check now runs on
  the island itself at **two severities**: FATAL is structural (twelve clubs carrying seeds
  1–12 exactly once each) and the page refuses to draw a bracket at all, replacing the field
  with an honest notice — a bracket with the wrong club in it is worse than no bracket; a
  WARNING is a smell (points disagreeing with the record, or a club seeded above one with
  more points) and it warns but still draws, deliberately, because the league seeds by its
  own unpublished tiebreaker and may separate clubs in a way points do not explain. The
  jsdom suite (session scratchpad, ephemeral) asserted the twelve seeds against the league's
  posted bracket, the opening-round and quarterfinal pairings card by card, cascade +
  downstream unwind, that no club plays on after a second loss, the state-codec round trip,
  an inbound `#b=` link, the vow easter egg, and both self-check severities — 51 checks.
  (Note when re-running it: jsdom with `runScripts: "dangerously"` ALREADY executes the
  inline script; eval-ing it again double-boots the page and produces phantom failures.)
  localStorage keys off the island's `asof` date, so a re-cut island auto-invalidates old
  saved brackets. **After the playoffs are actually played**, the prediction premise dies
  too: either carry the results (which needs a schema decision — see the next bullet) or
  retire the page to a notice. Ask Curtis which.
- Playoff results are NOT yet in any CSV schema — when they land, decide with Curtis how the
  game book carries them (`MMDD-schedule.csv` has no bracket/game-number column).

### The machine's second design (owner's rejection + rebuild, 2026-08-14)

**The first build shipped and the owner rejected the design outright** — his words: "weirdly
centered and doesn't make usage of desktop space… noisy and confusing. None of it is clear…
as an engineer myself didn't feel intuitive or helpful." What he asked for, verbatim in
substance: a **scenario runner** that **explains the scenario and how to make the scenario in
plain language**; **updated BRACKETS — not a list that represents brackets**; and the ability
to **run the playoff scenario too, with the clubs auto-moving through the bracket** as picks
are made. Mobile still matters, but the desktop must earn its width.

What was wrong (do not rebuild any of it): a 720px column centred on a 1440px screen; a
phone-style bottom tab bar (Afternoon / Bracket / Odds) that hid two thirds of the causal
chain behind taps; a "guided run" that showed **one game at a time** on a giant card; a
"map" view that was really a list of columns of chips; gold, berry, dashed borders, pills
and a huge ghost numeral all competing at once.

The rebuild's rules, which hold for any future version of this page:

- **One page, one causal chain, no modes.** Read top-to-bottom: a question → today's twelve
  results → the twelve seeds → the twenty-two game bracket → a champion. Every control is
  visible at once and every edit updates everything downstream live. No tabs, no wizard.
- **The bracket is DRAWN, not listed.** Absolute positions computed in JS from a `POS`
  table (column, row in card units) with SVG connectors generated from the same numbers —
  never from `getBoundingClientRect`. Winners' road along the top, elimination road along
  the bottom, grand final at the right where the two converge, the pennant plaque filling
  the top-right dead space. Clicking a club advances it, drops its opponent to the
  elimination road, and fills every later game in one forward pass; a pick whose premise
  changed is dropped rather than left lying (the prophecy unwinds). Loser ("drop") wires are
  hidden until you hover a game, so the default state stays quiet — the `Loser G5`
  placeholders already say where clubs come from.
- **Plain language is a computed output, not decoration.** `sayAnswer` / `sayAfternoon` /
  `sayBracket` write sentences from the enumeration. The answer panel gives a verdict
  (*Already settled · In their own hands · Needs help · Only by tiebreak · Cannot happen*),
  the three exact counts (outright / level on points / missed), **Must happen** (results
  forced in every qualifying future), **Cannot afford** (outcomes that appear in none of
  them), **By itself** (whether some arrangement of the club's OWN games settles it, and if
  not, the clubs that must ALL finish level-or-better in every future where winning out
  isn't enough — a necessary condition, stated as "only if"), and **Set an afternoon that
  does it**, which wires a concrete qualifying afternoon into the docket. One sweep of
  3^n futures serves the seed bounds and the question together (~110ms at n=12).
- **Three colours, one meaning each, stated in the legend:** gold = advancing / holding a
  bye; rust = eliminated; berry = level on points, where the unpublished tiebreaker takes
  over and the machine stops talking. Everything else is neutral. Figures are monospace,
  prose is not.
- **The seed table's clinch column reproduces `emit_playoffs`' board digit for digit**
  (`0–486`, `1,458–13,122`, …) — the live JS enumeration and the Python one must agree,
  and the jsdom suite asserts it against those literals.

### The contest (owner's brief, 2026-08-18) — 75,000 sats, sponsored by yggr

The owner turned the page into a prize contest: **yggr pays 75,000 sats to whoever
predicts the most accurate bracket.** Decisions he made when asked:

- **Submission = `mailto:`, verification = the desk.** The page prefills an entry in the
  reader's OWN mail app; they send it; it arrives from their real address. **A magic link
  was considered and rejected on the facts: sending email needs a server, so "magic link,
  browser only, no backend" is not achievable.** The inversion is better anyway — a magic
  link proves somebody controls an inbox, whereas mail from Shem proves it is Shem,
  because Curtis knows Shem. Say this plainly on the page; do not dress it up as
  cryptography.
- **Scoring is FLAT: one point per game whose winner the entry called**, over the games
  played so far. A game only scores if the entry named the club that actually won it — so
  a wrong early pick costs more than one point without any weighting being invented.
- **Ties go to WHOEVER ENTERED FIRST, and that is the whole rule** (owner, 2026-08-19). An
  earlier draft ranked a correct champion ahead of an earlier entry; that step was DROPPED
  when the owner asked for the tie rule to be printed, because a prize paying real money
  must not be settled by a step nobody was told about. The rule appears twice on the page —
  in the prize band and in the leaderboard caption — and `score_entries` sorts on
  `(-score, received)` and nothing else. The clock is the `received` timestamp on the mail,
  the same clock the deadline is read on.
- **Entries are public as soon as the desk verifies them**, in arrival order; the section
  re-heads itself "The leaderboard" and re-sorts by score the moment results exist.
- **Deadline: first pitch, Friday August 21.** The clock is the `received` timestamp on
  the mail, which is also the last tiebreak.

How it is built: `emit_playoff_seeds` carries `prize` (sats, sponsor, `to`, deadline), the
144-player `roster` (name → captain slug, club by club in seed order). **The entry field is
a TYPED name with the roster behind it as a `<datalist>`** (owner's call, 2026-08-18 — it
replaced a 144-option `<select>`, which was accurate but a chore on a phone). The page
resolves what is typed against the roster ignoring case and doubled spaces, echoes back the
roster's own spelling plus the club it derived, and mails THAT — so a sloppy "shem  HAMMON"
still arrives as "Shem Hammon · Sefton's team". An unmatched name is **not blocked**: someone
may spell their own name differently than the league does, so it sends with the club marked
unmatched and the desk sorts it out. `load_brackets()` resolves names the same forgiving way
and stores the canonical spelling, so the two ends of the contest never disagree about
whether two strings are the same person; a genuine miss is rejected with `difflib`
did-you-mean suggestions. The typed name is remembered in localStorage under
`<STORE>-who`. **`renderEntry` keeps COMPLETE and SENDABLE apart, and must keep doing so**
(bug found in the wild 2026-08-19, after publishing): a finished bracket fills the entry
preview in, and a name on it is what enables the buttons. The old `<select>` always carried
a name so the two could be conflated; a text field starts empty, and gating the preview on
it meant a reader who finished all twenty-two games was shown nothing at all. Unnamed, the
slip prints `Name: — type your name above —`, the input takes a gold `.wanted` ring, and the
buttons stay disabled. Also carried: `entries` and `results`. `resolve_code()` in Python mirrors `resolveBracket()`
in the page; both produce the identical chalk code `1111111122111111121211`, which is how
we know the arithmetic that pays out a prize agrees in both languages. Looking at another
reader's entry stashes your own bracket and hands it back — **looking is never losing your
work**, and localStorage keeps YOURS while somebody else's is on screen; editing theirs
forks it and says so. Opening an entry also writes `#e=<name-slug>` into the address bar
(`history.replaceState`, so no history spam), and an inbound `#e=` link auto-populates
that reader's bracket on arrival — **the slug is the NAME, never the list index, because
the list re-sorts by score the moment results land and an index link would silently
repoint at somebody else.** The seed table's last column re-heads itself "In this bracket"
while you are looking at someone else's. **This is still not a share button** — the owner
removed that 2026-08-14 and the rule stands; the URL merely tells the truth about what is
on screen, so copying the address happens to work. `scrollIntoView` is guarded: it is a
courtesy and must never take the hash, the toast or the bracket down with it (jsdom does
not implement it, which is how that got caught).

**`ENTRY_EMAIL` in analysis.py is `curtis@yggr.xyz`** (owner-supplied 2026-08-19 — his
company address, chosen deliberately over a softball.best one). It ships in the island and
the page assembles the mailto from it at runtime, so the address never sits in the markup
for scrapers; the only copy in the file is inside the JSON island. Change it in analysis.py
and re-splice — never hand-edit the address into the page.
**The address must be VISIBLE, not just wired into the mail button** (owner, 2026-08-19,
after publishing): the mail button addresses itself, but anyone taking the "Copy my entry"
route was left holding an entry with nowhere to send it. So the entry desk carries a
`.sendto` line ("Send it to curtis@yggr.xyz", itself a mailto), the copied text is prefixed
`Send to: <address>` so a pasted entry stands on its own, and the copy toast names the
address too. All three are written at runtime from `data.prize.to` — keep them that way if
the address changes.

**The satoshi sign was TRIED AND REVERTED, 2026-08-19 — do not re-add it.** The owner
asked for the symbol plus the unit spelled "Satoshis" (supplying a Font Awesome kit,
`kit.fontawesome.com/090ca49637.js`, which was declined: a CDN hotlink and an extra network
call, both forbidden on app pages by this project's own terms, account-tied, and no help at
all to the PNG, which needs the shape drawn regardless — it shipped as five inline-SVG
rectangles and as rectangles in the Pillow render instead). Seeing it, he called it himself:
**"It's like saying dollars after using the dollar sign $."** He was right, and the desk
should have said so when the request came in rather than building the redundancy first.
The prize reads **`75,000 sats`** — figure, then unit, once. If a symbol is ever wanted
again it replaces the word, it does not accompany it.

**Advertising rules on this page:** the prize band is SPONSORSHIP and wears "Presented by
yggr · coffee for sats"; the separate `.adv` unit wears the honest "Advertisement" eyebrow
per house rule and carries ONE informative beat (debut: the myth-buster — people assume
they cannot check out with bitcoin, and they can, in a few taps over Lightning). The
no-digits-in-ad-copy rule still binds the `.adv` unit; the prize band deliberately carries
the figure, because the figure IS the message and this page has no de-dup grep. Never
"bean(s)" — always "coffee". Never claim a player endorses anything.

### The machine's third cut (the speculation comes out, 2026-08-18)

The August 14 finale was played, so the page's whole premise — *what does my club still
need?* — had an answer, and continuing to enumerate it would have been fiction. Curtis:
"remove all the speculative aspects of the edition as it exists. Keep only the playoff
bracket prediction setup with the actual results from last week accounted for. That way
people can just simply make their prediction."

**Deleted, and not to be rebuilt while the bracket is the story:** the ask-the-machine
question panel and every `say*` writer behind it (verdicts, Must happen / Cannot afford /
By itself, "Set an afternoon that does it"); the twelve-game afternoon docket with its
Favourites / Random / Clear presets; the `sweep()` 3^n enumerator; the seed table's *Can
finish* and *Misses the bye in* columns; the readout paragraph; the `.field-strip`
(folded into the seed table's live status column); and **berry as a colour**, because
nothing on the page is level on points any more — the league posted its seeds. The old
`#f=<12>.<22>` codec went with them: its bracket half was picked against seeds that have
since moved, so honouring an old link would silently advance the wrong club. The page
reads `#b=<22 digits>` now and localStorage keys off the island's date.

**What the page is:** one chain, still no tabs and no modes — the prize band, then **the
twelve posted seeds → the twenty-two game bracket → your entry → everyone else's.**

**Do not reorder these sections.** Putting the bracket first was tried 2026-08-19 at the
owner's request (so a reader meets the thing they are playing straight after the sponsor)
and reverted by him the same day: it pushed the seed table between the bracket and the
entry desk, so a reader who had just finished picking could not see how to submit. The fix
that survived is a standing route rather than a new order — **`#bk-enter`**, an anchor in
the bracket's own toolbar, on screen the whole time the reader is picking, counting down
("6 to go, then enter →") and turning gold at 22/22. If getting the bracket higher up the
page comes up again, reach for that pattern, not the section order. Section 01 is a real reference table (seed,
club, record, points, run differential, *Enters at* — computed from the bracket, so seed 5
reads "G1 home v Seth" and seed 1 reads "Bye · G5 home v Winner G4" — and a last column
that follows your picks live). Section 02 is the drawn bracket, unchanged: absolute
positions from `POS`, SVG connectors from the same numbers, click a club to advance it,
the loser drops to the elimination road, one forward pass fills everything behind it, and
a pick whose premise changed unwinds rather than lying.

**Rules that carried over and still hold:** the bracket is DRAWN, never listed; every
number derives from the island; clubs are named by captain; there is no Share button (the
owner removed it 2026-08-14 — do not re-add one); the Disclaimer vow easter egg still
fires on any Horatio-vs-Claude line; and the page still says plainly, in its footer and
`<noscript>`, that there is no ink edition of the bracket.

**Renamed again 2026-08-18 — the page is now "Playoff Prediction Brackets"** (owner's
instruction; the brand lockup is "Playoff Prediction" + gold "Brackets"). `anime.min.js`
was deleted the same day, unused. **The owner also closed the standing question about
linking the paper to this page: he does not want one — do not add it, and do not raise it
again.** `og-playoffs.png` still reads SIMULATOR and is STALE — re-cut it with the next
substantive change to the page.

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
and Riley (Barlow).** If Avery, Kendall, Sidney, Leslie, J Daunt, or Emmerson (Hammon, Slamma
Jammas R10 — a NEW player who replaced Layla Hammon when she left the league, per Curtis
2026-08-12) ever matter for the rule, ask Curtis; never guess a gender into print. ("Layla"
stays in `FEMALE_GIVEN` — she was real and appears in pre-0807 snapshots; the Slamma Jammas
stay coed-legal either way: Maureen Williams and Alyssa Zitting.)

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

- **Masthead** with kicker (source · data date · compiled date). **Owner amendment
  2026-08-12: the masthead carries NO methodology sub and NO editions nav** — the masthead
  runs kicker → nameplate → sponsor strip and gets straight to the sections; the
  methodology lives only in the footnote, and the editions nav sits at the BOTTOM of the
  page (directly above the footnote), where the footnote's editions list also remains.
  **GoatCounter** before `</body>`. A compact contents nav.
- **House advertisements** (standing feature, owner request 2026-08-12): `.adv` units for
  **yggr — coffee for sats** (the owner's coffee company, https://yggr.xyz; card image
  `yggr-og.png`), placed roughly every three sections with the last one after `watch` as the
  classic back-cover ad (six placements at debut). Rules: every unit wears the honest
  "Advertisement" eyebrow — the labeling IS part of the joke; copy is desk-voiced and riffs
  on the neighboring section; **no digits in ad copy** (keeps the de-dup and display gates
  clean); **never claim a player endorses the product**; the one standing disclosure lives in
  the invoice-adjacent ad ("bitcoin-priced coffee from the editor's other desk … the desk
  drinks the inventory"). Write FRESH copy each edition — same-y test applies to ads too.
  Ads archive with their edition: period advertising is part of the artifact. The masthead
  also carries a **presenting-sponsor strip** (`.sponsor`, berry-ruled, directly under the
  nameplate; owner request 2026-08-12): the yggr card image at ~136px beside an eyebrow
  ("This Double Issue is presented by") and the line "yggr · coffee for sats — the paper is
  free; the coffee is priced in bitcoin." The whole strip is one link. Re-word each edition
  ("presented by" is the constant; the quip rotates), swap the edition name in the eyebrow.
  **COPY RULE (owner, 2026-08-12): never write "bean(s)" in any yggr copy — it is always
  "coffee."** **Informative beats (owner, 2026-08-12): the ads must carry, spread ONE per ad
  so the one-liners stay primary: (1) checkout is quick/easy — "a few clicks"; (2) a Cash
  App holding bitcoin checks out in a few taps; (3) payment rides the Bitcoin Lightning
  Network; (4) local delivery is free; (5) the myth-buster — people see "bitcoin" and assume
  they can't check out, and they can ("if you can read a box score, you can check out").**
  Rotate which ad carries which beat each edition.
- **The anchor contract:** `race`, `standings`, `records`, `watch`, and `dream-team` exist on
  every edition, whatever form their sections take. Every table carries an h3 anchor. Module
  ids that recur keep their names across editions (`scoreboard`, `weeklies`, `arcs`, `rebound`,
  `clubhouse`, `chase`, `crown-history`, `arcs-table`, `value`, `value-movers`, `club-<slug>`,
  `gauntlet`, `full-docket`).
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
  double rules and dotted leaders, section heads numbered "Ledger Nº 1…14". Same background
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
  `mw-benchmark` (owner request) — the front now runs a continuous
  medical block: benchmark → the ward. Third late addition (same day): **`the-disclaimer`**,
  an h3 notice at the foot of `scoreboard` recording the overturned-in-spirit home run in
  the upset game (owner facts in the gag ledger; linked from the upset ticket). Fourth
  late addition (same day): **`mw-benchmark`** — the Mike Williams Benchmark honor roll, placed
  directly after `thousand-club` and before `invoice` (owner wants it high); hand-written,
  numbers from the stats file via a FEMALE_GIVEN query — see the gag ledger for the
  framing mandate and the Sidney/Leslie caveat. Fifth late addition (2026-07-30, owner
  request): **`full-docket`** RETURNS from the archive as a recurring reference module —
  `emit_full_docket` (all 144 players in snake-draft order: Pick, Rd, True Rd, Move vs the
  previous edition, Gap verdict, League # = value rank, Season/AB/Value), registered
  between VALUE DESK and WATCH; on the page it is Ledger Nº 13 (the Next Slate renumbered
  to Nº 14), with the `.table-scroll.tall` sticky-header pane ported from the 07-10 CSS.
  The id came OFF the retired list — same meaning as its archive appearances, so the
  revival is legal; the masthead sub no longer lists the docket as resting. When this
  edition archives, the docket stays (season reference, not foreshadowing).
- **2026-08-07 — THE DOUBLE ISSUE** (built 2026-08-12): newsweekly combined number
  ("Combined Nº 6–7 · Two afternoons, one paper") for the league's two-weeks-at-once posting.
  Identity: condensed display caps (`--display: Avenir Next Condensed…`) over the house serif,
  berry accent, doubled rules; background + arc tokens unchanged (palette stays valid). A
  **"Notice to Subscribers"** box (id `notice`, above the contents nav) carries the apology gag
  AND the methodology asterisk in one breath: fortnight figures pool Jul 31 + Aug 7;
  per-afternoon splits do not exist. analysis.py emitters became **period-aware** (`pnoun` /
  `pdates` in the html ctx — visible text says "fortnight" when the period spans 2+ game days
  and auto-reverts to "afternoon" next single-Friday edition). Hand-written front of book:
  **`seventeen`** (the cover, one-off) — Michael Williams 17-for-17 · 1 CO = .941, with
  `.cover-tiles` stat tiles; **`thousand-club`** (bulletin, now recurring) — Nathan Knudson's
  punched card beside Mike's 17-punch card stamped VOID; **`departures`** (one-off, could
  recur when a long tenure ends) — "The Departures Desk," headline **"Cuervo's Crashout"**
  (owner's title, 2026-08-12 — the one place the tease is allowed to be loud; the prose stays
  oblique), a hotel-register bit for Cuervo Timpson's fall from the leaders' table: a
  `.reg-strip` of five rank tiles (Jul 3 #1 crown ·
  Jul 10 #1 crown · Jul 17 #4 · Jul 24 #3 · Aug 7 #7 checked-out, debit-tinted) over one
  short dek — "no incident on file, luggage carried without assistance, forwarding address
  of seventh… The suite above is now available. The pressure is included in the rate."
  Owner asked for the pressure tease OBLIQUE, never direct; if Cuervo re-enters the top
  four, the re-check-in is the story; **`blotter`** (after the cover) and **`in-memoriam`**
  (after the Divide) — the two `.record` cards of the conduct file (Tammy's ejection,
  Gideon's bat — see the gag ledger); **`citation`** (after the crown) — the Horatio
  Williams proclamation, Citation Nº 1 (see the gag ledger for the grand-slam testimony
  and the never-let-him-gloat rule); **`paternal-approval`** — "The Family Desk," Form 3B
  (the Ben/Charlie Williams father-son bit, on the invoice stationery — see the gag
  ledger; on the page it sits directly AFTER the Divide, closing the family suite);
  **`dewegeli-divide`** (briefly
  `eh-benchmark` in the working tree — renamed before publishing, owner request 2026-08-12) —
  the benchmark re-chartered from Mike (vacated at .705) to **Elliot Hammon, .548** — also
  captain, R1, SS, so the charter transferred intact — and renamed **the Dewegeli Divide**
  for his great-grandfather, with the Karl Franz Dewegeli Jr. portrait (`dewegeli.png`)
  framed beside the honor roll (`mw-benchmark` id now resolves only in the 07-24 archive;
  never reuse it). Registry order: crown, scoreboard (24 tickets split into
  `scoreboard-jul31` / `scoreboard-aug7` date groups), weeklies, records, debits (recurring
  while the CO epidemic lasts), rebound (+ the Becky Wood charter note), clubhouse, standings,
  **invoice (now recurring — "second notice," auto-addressed to whoever leads)**, gauntlet,
  value, full-docket, arcs (6 snapshots; emphasis reassigned Jeremy/Stafford/Horatio =
  arc-1/2/3, page-CSS only), watch (the Aug 14 season finale — the Jeremy–Caleb 3:30 pennant
  decider — plus the Disclaimer vow honored with a dry callback linking
  `2026-07-24.html#the-disclaimer`). **The invoice was REDESIGNED mid-edition (owner request,
  2026-08-12): `emit_invoice` now emits a full stationery document** — letterhead, "Billed
  to" addressee, dotted-leader `dl` line items, a **results-on-account docket** (one chip
  per game — this is what fixed the old layout, which crammed all four results into one
  nowrap table cell and broke on both desktop and mobile), the balance-due band, and terms
  fine print; the rotated stamp is the module's one hand-written word per the t-note pattern
  (`<!-- one hand-written stamp -->`; this edition: "Second notice", in debit red at the
  house −6°). Future editions inherit the document form; the 07-24 archive keeps the old
  table markup, frozen. The records section referees the double week honestly:
  workload +46 (Stafford) broke a mark itself set across June's two-Friday block —
  like-for-like; team CO +16 (Ellites) broke a single-afternoon mark — the real asterisk.
  Clubhouse Form now shows every period (five glyphs; emitter caption made count-agnostic).
  **The edition ships its own OG card, `og-2026-08-07.png`** (owner request, 2026-08-12): the
  Dewegeli Divide tease — Karl's framed portrait at left, the dashed Divide diagram at right
  (honor roll above the line, "Elliot Hammon — R1, captain, shortstop" below it), footer "He
  crossed an ocean so he could watch this." Rendered with Pillow (scratchpad venv — Pillow is
  NOT installed system-wide) in the Double Issue palette; fonts Avenir Next Condensed Heavy /
  Menlo / Georgia Italic; og:image + twitter:image point at it. Revert to og.png next edition
  unless it ships its own card; the card stays with this edition when it archives. **House
  ads debut this edition** (six `.adv` units for yggr — see the standing-feature bullet in
  the spine). **THE PAPER CARRIES NO PLAYOFF MATERIAL. (2026-08-14.)** A playoff extra was
  built into this edition that morning — section id `playoffs` at the top of the page with a
  launch ticket, stat tiles, the emitted `clinch` board and an `elimination-certificate` —
  and the owner had **all of it reverted the same day**: "remove any changes to the index.html
  about the playoffs… just want this confined to its own html page and leave the current
  edition of the newsletter how it is." index.html was checked back out to its committed
  state (all 367 added lines were playoff-only: a CSS block, a contents-nav entry, the
  section, and a footnote passage), so the Double Issue stands exactly as published on
  2026-08-12. **Consequences to respect:** the paper does not link to playoffs.html at all and
  should not be made to; `emit_playoffs`' clinch-board rows are currently emitted but spliced
  nowhere (the `machine-data` island is the live half of that emitter); the ids `playoffs`,
  `clinch` and `elimination-certificate` never published, so they are free rather than
  retired; there is no playoff section to delete when this edition archives; and the
  Certificate of Mathematical Elimination never ran in ink (see the gag ledger). **The
  gameday feature is the stand-alone page and nothing else:**
  **playoffs.html** (see the files table and the playoffs section) — at the time, the
  scenario runner: an ask-the-machine panel answering in plain English, the twelve finals as
  a docket beside a live seed table, and a drawn double-elimination bracket you click
  through to a confetti pennant. **All of the speculative half was cut 2026-08-18 once the
  finale was played — see "The machine's third cut"; what survives is the drawn bracket, the
  posted seeds, and the pennant.** **There is no Share
  button — the owner had it removed 2026-08-14; a state codec stays, because it is what
  localStorage holds and it still reads a bracket out of an inbound URL (the codec itself is
  now `#b=…`, bracket-only). Do not re-add a share affordance unless he asks.** **The page was named "the Seeding Machine" at debut
  and renamed **the Scenario Simulator** the same day, also at the owner's request; the
  analysis.py comments and the share card carry the new name. The localStorage key alone
  still says `seeding-machine-`,
  deliberately, so readers' saved scenarios survived the rename.** **The
  page's first design was rejected by the owner the day it shipped and rebuilt from first
  principles the same day — see "The machine's second design" for what he objected to and
  the rules that replaced it; do not reach for the tabbed phone-app shape again.** The
  Disclaimer vow easter egg lives there: any Horatio-vs-Claude bracket line reveals the
  `#vow` banner linking `2026-07-24.html#the-disclaimer`. The page links out to
  `index.html` (unanchored) and says plainly in its footer and `<noscript>` that there is no
  ink edition of the bracket — keep those honest if the paper ever carries playoff material
  again. When this edition archives: delete `watch` only. playoffs.html is handled
  separately per "playoffs.html duties" above. The back-cover ad
  after `watch` moves up to close the page; the notice, cover, bulletin, divide, Form 3B,
  debits, invoice, gauntlet, docket, portrait, and ads all stay.

**Retired ids** (pre-2026-07-17; they resolve in the archives, never reuse for new meanings):
`the-week, week-bats, temperature, glance, draft-board, sleepers, teams, second-look,
missing-pages, what-changed, team-sheets, verdict, round-rooms, dynasty, hot-bats, cold-bats,
week-co, playing-time, perfect-weeks, team-box, tier-1, tier-2, team-notes, report-card,
mined-rounds, caused-outs, clean-hands, iron-horses, league-shape, movers, streaks,
dynasty-week, bookkeeping, team-picks, team-week, priced-right, bargains, didnt-justify,
captains-mirror, outliers, round-1…round-12`. (`full-docket` left this list 2026-07-30 —
revived, same meaning, as a recurring module.)

## Gag ledger (keep bits consistent and escalating, not reset)

- **The caused-out tragedy** (Gideon's team): act four (2026-07-17) was "a remission" — +3 on
  the afternoon, season 24 still league-worst. Act five (2026-07-24): +1, tied for the day's
  gentlest line — "the remission entered its second week" — season 25 still league-worst.
  **Act six (2026-08-07): the remission held (+5, gentlest among the big-volume clubs) and the
  disease found two new hosts — the season board is now a THREE-WAY tie at 30 (Gideon's,
  Elliot's, Michael's clubs), with Elliot's club setting the +16 fortnight record on the way
  in. "The original patient is merely tied for worst, which the desk supposes is what recovery
  looks like around here."** Act seven: the tie breaks one way or the other; report it
  straight.
- **The recusal bit** (Curtis Knudson, site owner): budget ≤ 2 per edition, vary the wording.
  2026-08-07 spends: the crown notes (he sits fifth at the fourth-place average on the same
  at-bats — "the desk prints the coincidence and vacates the paragraph") and the Dream Team R2
  seat he now holds ("publish the table and exit the paragraph. He has.").
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
  a second act. 2026-08-07: another 3-for-6 .500 fortnight — passed in TOTAL SILENCE (silence
  is a valid handling; the file needs no annual report).
- **Becky Wood, #144**: "still technically a bargain" is now "doing heavy lifting" (0-for-5,
  #139). 2026-07-28: the audit found she has also faced the league's softest slate (12.36 opp
  RA/G, most generous among 15+ AB regulars) — "no alibi in either direction." 2026-07-24:
  1-for-4, swing exactly .000 against her own .250, rank #141 — "files another extension."
  2026-08-07: 1-for-7, season down to .226, rank #141 — the bit now lives in the rebound
  notes as the "tracked by charter" clause ("'still technically a bargain' survives on the
  technicality alone — she still out-ranks three names in the book"). Keep tracking; never
  invent numbers for her.
- **The invoice** (the luck account — now attached to the CHAIR, not the man): opened +.243
  on Stafford's club (July 10), installment collected 2026-07-17 (+.200), re-inflated to
  +.220 with first place attached 2026-07-24. **2026-08-07 — COLLECTED AND TRANSFERRED:**
  Stafford's club dropped 3 of 4 (lost the Caleb rematch 8–7 AND the first-ever Jeremy
  meeting 16–10), fell #1→#5, balance written down to +.094 — and the statement re-issued
  itself to the new leaders: Jeremy's club, luck +.149 (league's highest), SOS played .421
  (league's softest). "The first invoice in league history to follow the chair rather than
  the man." The module is now RECURRING (emit_invoice auto-addresses the standings leader).
  Collateral on file: Jeremy–Caleb meet head-to-head Aug 14 3:30 South, ½ game apart — the
  pennant decider; Stafford–Caleb close their season series at 2:30 the same day.
- **New seeds from 2026-07-17**, updated 2026-08-07: "the league owes Ephraims Daniel's club"
  — AN INSTALLMENT PAID: two wins in the fortnight (as many as the whole season prior),
  including the 17–15 UPSET of then-#1 Stafford's club ("the desk records a payment"); luck
  still league-worst −.156, so the debt survives. Jeremy's team "the quietest hot team" —
  RESOLVED LOUD: 4–0 fortnight, took first place #5→#1 while captain/SS Boyds Jeremy sat
  every game (the Ghost at rank #13) — new seed: **"took first from the bench."** "The 1.000
  club": 2026-08-07 membership = Nathan Knudson alone (6-for-6 — the cramping brother; the
  physio-desk crossover is the bit) with Michael Williams DENIED at the door (17-for-17 ·
  1 CO = .941 — the VOID card, longest application in club history); Gideon's and Ryan's
  memberships lapsed silently. The bulletin box is now a recurring module. **Owner fact:
  Ryan Hammon is over 40** — keep the age qualitative ("forty-plus") unless Curtis supplies
  a number. **The Cawley family record** — .800 HELD at 2026-08-07 while the same three
  Cawleys finished the fortnight dead last among the nine families ("both facts in the same
  drawer"); the smallest-family absurdity is the bit; keep it honest.
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
  future Horatio-vs-Claude line gets a dry callback. **Honored 2026-08-07** (the clubs share
  the Aug 14 5:30 line in `watch`; the callback links `2026-07-24.html#the-disclaimer` and
  re-states the "calm entirely unrelated to which club the editor bats for"). NOTE: they
  actually PLAY Aug 14 — the season-final edition's scoreboard ticket for that game must
  carry the callback too.
- **The Benchmark / THE DEWEGELI DIVIDE** (debuted 2026-07-24 as "The Williams Line," renamed
  the Mike Williams Benchmark same day; re-chartered 2026-08-07 to Elliot Hammon's .548;
  **renamed THE DEWEGELI DIVIDE at the owner's request, 2026-08-12** — after **Karl Franz
  Dewegeli Jr., Elliot's great-grandfather, an Ellis Island immigrant** (owner facts +
  photo supplied same day; canonical spelling "Karl Franz Dewegeli Jr." — the owner's message
  contained typo variants, do not propagate them). Elliot's name stays prominent: he DRAWS the
  Divide (h2, wline row, bench row all carry him); the module id is `dewegeli-divide`
  (`eh-benchmark` was renamed before ever publishing — it never shipped, so it is not a
  retired id). The portrait (`dewegeli.png`, `.divide-fig`, floated right / centered on
  mobile) runs with the Ellis Island caption: the brave ancestor who crossed an ocean for his
  posterity "now keeps his appointed watch over the divide that bears the family name,
  checking in … on how his great-grandson Elliot is coming along at the plate. The desk
  prints the figure below and lets the family settle it privately." Tone: the ancestor is
  treated with full reverence — ALL the teasing lands on Elliot; never mock Karl, the
  immigration, or the family. **The gallery is now THREE frames** (owner correction,
  2026-08-18): Karl (great-grandfather) · **Marie Thomas Davis Dewegeli** (great-grandmother,
  his wife) · **Darlene Marie Dewegeli** (their daughter, Elliot's GREAT-AUNT — not his
  grandmother, which is how the Aug 14 edition first printed her). Get the relations right
  every edition; the ancestors keep the watch, the great-grandson keeps the average. Elsewhere on the page the bit's handle is "the Divide" /
  "draws the Divide."): the Mendoza-Line parody — a "league benchmark"
  set at the season average of the league's lowest-batting FIRST-ROUND pick, with an
  honor-roll table of every confirmed woman batting above it (women rows shaded, a dashed
  `.wline` row draws the benchmark, the namesake sits muted beneath as "the benchmark").
  Mike Williams vacated by batting 17-for-17 and rising to .705/#17 — "the benchmark is
  dead; long live the benchmark"; the succession itself is now part of the bit ("the
  instrument survives its founder"). Elliot is ALSO captain + R1 + SS, so the charter
  transferred intact. Elliot-specific material used 2026-08-07 (don't repeat, escalate):
  drafted himself #4 overall; the only R1 pick with negative value (−0.7); his club set the
  +16 CO record and tied the season-worst 30. Honor roll at re-charter: Violet .585,
  Deborah .571, Maureen .568. **Framing mandate: FEMALE EMPOWERMENT** — celebrate the women
  (the discount-round engine), tease the namesake with warmth ("Encouraging precedent,
  freely offered" — Mike's escape is the roadmap). SS courtesy extended per house rule,
  kicker "Debbie Timpson does not need it" is tradition now. Selection = `FEMALE_GIVEN` +
  rank above the namesake's — **Sidney Dockstader and Leslie Williams sat above the line
  again at 0807 but stay OFF (owner's explicit call, 2026-08-12: "leave them off"; still on
  the never-guess list).** The benchmark moves with its namesake's average — and the
  namesake itself changes whenever a new R1 pick bats lowest; recompute both honestly.
- **The conduct file** (both entries owner-supplied 2026-08-12, both from GIDEON'S clubhouse —
  the pattern line is part of the bit): **(1) Tammy Williams took the season's FIRST
  EJECTION** — no particulars supplied; never invent when/why/which game; the desk "records
  the milestone, not the particulars, which remain between her and the umpire" (id
  `blotter`, a `.record` card with debit trim, placed right after the cover). **(2) Gideon
  Hammon BROKE HIS BAT in anger** — and **Gideon is Elliot's OLDER BROTHER**, making him
  Karl Franz Dewegeli Jr.'s great-grandson too (owner authorized the rope-in). Filed as an
  equipment OBITUARY (id `in-memoriam`, `.memorial` — a proper black-bordered mourning
  notice, prettied at owner request 2026-08-12: 5px black band + inner hairline, centered,
  berry printer's ornament ❦, and the punchline promoted to a ruled EPITAPH band — "It had
  done nothing wrong — the average is the proof"; placed directly after the Divide).
  The standing joke: **composure in the Hammon line runs inverse to batting average** —
  Elliot (.548) serene, Gideon (a hit off the crown) splintering lumber. Track both bits
  honestly: ejection Nº 2 whenever it comes; Gideon's next fortnight is either "the new bat
  answers" or "the bat was not the problem."
- **The Citation / Horatio Williams** (owner request 2026-08-12): **owner facts — Horatio hit
  TWO GRAND SLAMS on the afternoon of August 7** (the book has no home-run column, so the
  desk prints them as SWORN TESTIMONY, same device as the disclaimer — never fold them into
  any computed number), **and he is saintly humble: won't say a bad word, would never gloat.
  The standing rule: the desk gloats FOR him; never portray Horatio boasting, complaining,
  or even accepting the praise** ("disputed only, and inevitably, by its honoree"). The form:
  a berry-double-framed PROCLAMATION (id `citation`, `.citation`, placed after the crown) —
  eyebrow "By order of the desk · Citation Nº 1," ornament row ❧ ❦ ❧, WHEREAS clauses
  (numbers real: .780/#3, 14-for-17, most runs scored + fewest allowed, pyth .786 league
  best), a NOW-THEREFORE resolve band, and an attest line. Numbered device — Citation Nº 2
  awaits whoever earns it; if Horatio does something modest again, that is not news, that is
  Tuesday.
- **Sam Guy & Cuervo Timpson are BROTHERS** (owner fact, 2026-08-12) — different surnames,
  same club (Seth's team); never speculate in print about why the names differ. The 0807
  crown section is built on the fact: the fortnight one brother checked out of the leaders'
  table (Cuervo's Crashout), the other took the batting crown while their club went 0-4.
  The section's devices, both reusable: the **crown-hero card** (`.crown-hero` — huge display
  name + the average in accent, chips beneath: club / AB / 0 CO all season / hardest slate)
  and **THE WIRE** (`.wire` — a telegram "as received": TO the clubhouse, COPY to "Mr. C.
  Timpson — family; lately of the leaders' table"; body in caps with berry STOPs — "GETTING
  ON BASE REMAINS LEGAL AND POSSIBLE STOP … NO FURTHER INSTRUCTIONS, ONLY THE EXAMPLE STOP").
  **Rule for invented artifacts: the footer must say the desk wrote it** ("Mr. Guy sent no
  actual wire; the batting was considered sufficient") — same principle as the invoice stamp
  and the physio statuses: numbers real, paperwork editorial, stated as such. h2 is
  deliberately declarative ("Sam Guy is the best bat in this league. It's official.") —
  owner wanted the emphasis loud, 2026-08-12.
- **The Trainer's Table** (debuted 2026-07-24, owner request 2026-07-29): the editor's
  brothers teased as men of eighty outperforming their charts — **owner facts: Derrick
  Knudson has a weak ankle; Nathan Knudson cramps constantly; Levi Knudson is heavier set
  with weak knees (and is the Slamma Jammas' SHORTSTOP — the best joke writes itself)** —
  plus Sam Guy, included "for fun" with **no ailment supplied: never invent one for him**;
  he is the "suspiciously fit control group." Tone mandate from the owner: "nothing
  tasteless" — keep it kind; the caption's "the batting is real; the medicine is editorial"
  is the standing disclaimer. Statuses (DAY-TO-DAY / PROBABLE / QUESTIONABLE / SUSPICIOUSLY
  FIT) are the desk's own. Recurring only if Curtis feeds it; escalate the charts honestly
  (a bad afternoon = a setback in physio, a hot one = medically unexplained). 2026-08-07: no
  standalone section (no new owner material) — recurred via callbacks only, and they landed
  big: **Sam Guy, the control group, TOOK THE BATTING CROWN** ("the file stays open; the
  chart stays blank; the suspicion stays warranted"), and Nathan Knudson's 6-for-6 made him
  the 1.000 Club's sole member ("upgraded to medically unexplained"). Levi's setback
  (5-for-11, −.269 swing) went unremarked — banked for the ward's next convening.
  **New owner facts (2026-08-12): Nathan is the owner's brother, and Derrick is Nathan's
  OLDER (and more injured) brother.** The sibling-rivalry seed planted this edition: Nathan's
  perfect fortnight vaulted him past Derrick — they now sit ADJACENT in the league table
  (#21/#22 at 0807; at 0724 it was Derrick #15, Nathan #30). **The rung has TRADED all
  season** (Nathan above at 0612 and 0710; Derrick above at 0703, 0717, 0724) — never print
  "first time"; the prose says "retaking a family rung the two have traded all summer," and
  the dek names Derrick EXPLICITLY (readers were confused by the unnamed-brother version;
  owner fix 2026-08-12). Card field: "Next of kin: Derrick Knudson, older brother — #22,
  one rung down this edition."
  The cramping rhetoric is now the UNION-SHOP bit (muscles staging "whole-body work stoppages
  without notice … and management batted a flawless fortnight anyway"; medical file: "cramps —
  whole-body, unannounced, and 0-for-6 at stopping him"). Standing line to honor and escalate:
  **"Membership, like family seniority, is reviewed weekly"** — track the brothers' order
  every edition now; if Derrick retakes the rung, that is the story.
- **Charlie Williams** (Charles Williams, Stafford's team): **born 1958** — owner-supplied
  2026-07-29, correcting an earlier "65"; he's 67–68 in the 2026 season, so if his age ever
  prints, write "born 1958" / "b. 1958" rather than guessing which side of his birthday he's
  on. The elder-statesman engine alongside Ryan Hammon — league-leading workloads in his
  late sixties. (A prescription-pad physician bit that debuted alongside this fact was
  scrubbed from the edition and from this file at the owner's request, 2026-07-30 — do not
  revive it; no medical bits for Charlie, ever.) **Family-links rule AMENDED 2026-08-12:**
  the owner supplied one link — **Ben Williams (Boyds Daniel's team, 3B) is Charlie's SON** —
  and it is fair game (see "A Father's Disappointment" below). No OTHER family links for
  Charlie may be printed or inferred beyond the surname-based dynasty ledger.
- **A Father's Disappointment / Form 3B** (debuted 2026-08-07 edition, owner request
  2026-08-12): the family desk's "application for paternal approval" — Ben Williams,
  applicant; Charles Williams, reviewing officer. **Owner facts: Ben is Charlie's son; Ben
  showed up to play IN JEANS; Ben plays THIRD BASE** (positions aren't in the data — 3B is
  owner-supplied; the form number "Form 3B" is the joke). Built on the invoice stationery
  (`.statement` classes reused; stamp "SEE ME"; finding "WITHHELD" in the due band).
  Conditions for reapplication, per the owner: bat better (nearer the family line) and hold
  "a position of greater consequence than third base"; the fine print adds "trousers."
  Tone rules: ALL teasing lands on Ben; Charlie is never quoted and never files —
  the standing line is "the father has filed nothing, and did not need to" (same
  no-invented-attitudes principle as the umpire). Track honestly: if Ben's line climbs
  toward Charlie's, the form gets re-reviewed on the page; the jeans remain a permanent
  exhibit either way.
- **The schedule alibi is dead** (2026-07-28 audit): the league batted *better* against the
  harder slates. If a club or player blames the schedule in a future edition, cite the audit
  ("the alibi desk settled this in July") instead of re-running it — unless the verdict has
  actually flipped, which would be a story. Related standing fact: the Gauntlet showed the
  top four all rode sub-.500 slates while Sefton's club (5th) walked the hardest and drew
  the softest run-in — the August run-in is loaded (Caleb–Stafford ×3, Jeremy–Boyds ×3).
- **The Certificate of Mathematical Elimination** (written for the 2026-08-14 playoff extra
  and **never published** — the extra was pulled from the paper the same day; the device is
  unused and Nº 1 is still available to whoever earns it):
  the Long Shot Desk's official paper — Nº 1 denied Seth's team a first-round bye ("Denied ·
  by arithmetic" stamp at the house −6°; findings: zero bye futures of 531,441; best
  available finish ninth, four named results required; disposition "Returned, with sympathy —
  the batting crown already lives in this clubhouse"). A numbered device like the Citation —
  **Nº 2 awaits the next club the arithmetic closes on** (candidates: any future clinch/
  elimination moment worth official paper). Rules: same invented-artifact law as the wire and
  Form 3B — numbers real (from the playoff desk digest), paperwork editorial, the footer says
  so ("the application is imaginary — Seth's team asked for nothing, which the desk
  respects"); filed "to the same drawer as the wire, the invoice, and Form 3B." The
  Sefton/Stafford four-five coin ("31-31-19 of 81, level in the league office's unpublished
  hands") is the extra's live cliffhanger — whichever club takes the fourth chair, the next
  edition reports how the coin landed; if it lands on the 19, the unpublished-tiebreaker
  mystery finally has a face and IS the story.

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
