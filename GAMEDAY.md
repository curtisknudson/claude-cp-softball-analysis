# GAMEDAY — the live playoff runbook (Fri Aug 21 – Sat Aug 22, 2026)

This is Claude's own reference for running the site live from the field. Curtis
will ssh into this laptop from the park, open `claude` in this repo, and send
results as they happen. He should only have to say "it's time for standings" or
"G3 Claude, push" and the right thing happens. **Read this whole file before
touching anything tomorrow; then keep it open.** CLAUDE.md is still law — this
file only adds the gameday procedure on top of it.

---

## 0 · State of the build (tick these off as they land — tomorrow-me must check)

- [x] **Live page built** 2026-08-20 — `playoffs-live.html`, UNTRACKED, staged at
      repo root (see §4). Rebuild from source with `build-live.py` only if the
      live-src changes; otherwise it is final. It must not be served at the
      `playoffs.html` route until cut-over (owner's instruction).
- [x] **analysis.py extended** 2026-08-20 (uncommitted in the working tree until
      Curtis says otherwise): `live: {updated, played}` in the island and entries
      always scored when `--playoff-results` is given (even 0 of 0). The results
      schema is `game,winner` and STAYS that way — Curtis sends winners only,
      never runs (his call, 2026-08-20). pyright 0/0; the prediction-era island
      is byte-identical to before, so the published page is unaffected.
- [x] **Tooling staged** in `~/.claude/projects/-Users-cube-Developer-cp-softball/gameday-tools/`
      (survives reboots; /private/tmp scratchpads may not):
      `emit.sh` · `splice.py` · `fix-result.py` · `live-test.js` · `shots-live.js` ·
      `build-live.py` + `live-src/` · `prediction-test.js` (the old 367-check suite)
      · `fixtures/` · `node_modules` (jsdom + playwright; browsers in
      `~/Library/Caches/ms-playwright`). All honour `REPO=` for a scratch clone.
- [x] **Full rehearsal done** 2026-08-20 in a local clone: cut-over, G1–G3 cycles,
      a wrong winner corrected in place, duplicate / non-participant / too-early
      rows refused, a 15:01 entry refused and a 14:59 one accepted, then all 23
      games of a decider bracket filed one at a time — every island passed the
      suite, 0.7 s per cycle. Screenshots (desktop light/dark, phone, entry
      open, final) eyeballed.
- [ ] **Git authorization wording settled** (§6) — Curtis either uses the push word
      per message or amended CLAUDE.md with a day-scoped authorization.

---

## 1 · The shape of the day

```
                 PRE            CUT-OVER                LIVE                     FINAL
  now ──────────────► 15:00 Fri ─────────► first result (~16:00) ──────► G22/G23 Sat ~14:00+
  entries still open   entries CLOSE        one cycle per result        champion; leaderboard
  (0821-brackets.csv)  swap in live page    (§2 loop)                   final; prize line
```

- **PRE (until 15:00 Friday):** the page is the prediction page as published.
  New entries: append to `0821-brackets.csv`, re-emit, splice, verify, commit,
  push — exactly the procedure used all week (§2 with no results file).
  `load_brackets()` REFUSES any `received` ≥ `2026-08-21T15:00` (local clock).
  A borderline entry (mail arrived 14:5x, pasted to me after 15:00) needs the
  MAIL's own arrival time from Curtis, and he vouches for it; I do not invent it.
- **CUT-OVER (once Curtis says entries are closed, ≥ 15:00):** swap the live page
  in (§3). There is a natural hour before the first result lands — use it.
- **LIVE:** every result is one cycle: CSV row → emit → splice → verify →
  (commit → push if authorized). Target: under two minutes from his message to
  "pushed".
- **FINAL:** G22 decides it unless the elimination-road club wins G22 — then G23
  is owed and played. The page crowns the champion and names the leader of the
  leaderboard as the winner of the 75,000 sats (ties → earliest `received`).
  Paying out is Curtis's; the page just says who.

**Always start a session (and every reconnect) with:** `git status --short && git log --oneline -3`
— an ssh drop mid-cycle can leave a half-done update in the tree. Finish or
`git checkout -- playoffs.html` the half-done one before starting the next.

---

## 2 · The result cycle (the thing I do ~22 times)

Curtis's message will look like one of these — parse generously, then ECHO
back exactly what I filed, by game number and captain, so he can correct it:

- `G3 Claude` · `Claude beat Danny` · `4:00 South: Pliggas over Danites` ·
  `Stafford won` · `Elliot over Michael`
- **Winners only.** He cannot source runs reliably and will not send them; the
  schema has no runs column and the page prints none. If a number ever appears
  in a message, it is not filed anywhere.
- **No ties on playoff day** — the league plays a sudden-death finish and he
  reports the winner. If a message is ambiguous about WHO won, ask; never guess.
- Two results in one message (3:00 games both finish ~4:00) — file both.

**Game identification:** the pair of clubs (or the field+time) identifies the
game; see the schedule in §8. The loader rejects a winner that did not play in
that game and a result whose participants are not yet decided, so a wrong game
number almost always fails loudly — but a result can still be filed into the
wrong game when a club plays twice in a row (e.g. Elliot wins G1, then G5):
**say the game number back every time.**

### 2a · Append the row

`0821-playoff-results.csv` — CRLF, trailing CRLF, raw league team names
(loader key), winner spelled exactly as in `CAPTAINS`:

```
game,winner
1,The Ellites
2,The Fellowship of the Swing
```

```sh
printf '3,The Pliggas\r\n' >> 0821-playoff-results.csv
```
Raw-name lookup: Jeremy → The Diamonds and Dirtbags · Caleb → The Pure Breads ·
Horatio → Youre Saying Theres A Chance · Sefton → The Lefty Looseys ·
Stafford → The Fellowship of the Swing · Claude → The Pliggas · Gideon → The Good
Guys · Elliot → The Ellites · Michael ("Mike W") → The Playas · Boyds Daniel
("Dan Boyds") → The Slamma Jammas · Ephraims Daniel ("Danny") → The Danites ·
Seth → The Stars and Strikes.

### 2b · Emit + splice

```sh
S=/Users/cube/Developer/cp-softball
T=~/.claude/projects/-Users-cube-Developer-cp-softball/gameday-tools
cd $S && $T/emit.sh 0821-playoff-results.csv $T/emit.html && echo EMIT-OK   # wraps the full --html-afternoon command
python3 $T/splice.py $T/emit.html playoffs.html   # replaces the machine-data line; asserts one island each side + JSON parses
```
`emit.sh` prints `GAMES OK … BRACKETS OK … 14 verified entries` and exits
non-zero on any loader refusal (the AssertionError is in `$T/emit.err`) —
anything but EMIT-OK is a stop; read the error, it names the row. The
long-hand command it wraps, if the script is gone:
`python3 analysis.py 0814-stats.csv --history 0612-stats.csv 0703-stats.csv 0710-stats.csv 0717-stats.csv 0724-stats.csv 0807-stats.csv --games 0814-schedule.csv --standings 0814-standings.csv --prev-standings 0807-standings.csv --brackets 0821-brackets.csv --playoff-results 0821-playoff-results.csv --html-afternoon`.
The emit is ~0.1 s. `splice.py` asserts one island on each side, parses the
JSON, rewrites only that line, and prints `spliced … N entries, M results,
results='…'` (or `island unchanged`). If the tools dir is gone, the same ten
lines are in §11 — recreate it there first, do not improvise a splice live.

### 2c · Verify (fast — under ten seconds, every cycle)

```sh
cd $S
python3 - <<'PY'                                    # island sanity, printed for the reply
import re,json
d=json.loads(re.search(r'id="machine-data">(.*?)</script>',open('playoffs.html').read()).group(1))
r=d['results']; played=[i+1 for i,c in enumerate(r) if c!='0']
print('results', r, '| played', played)
print('live', d.get('live'))
for e in d['entries'][:5]: print(f"  #{d['entries'].index(e)+1} {e['n']:22s} {e.get('s')} of {e.get('p')}  {e['r']}")
assert all(d['entries'][i]['s']>=d['entries'][i+1]['s'] for i in range(len(d['entries'])-1))
PY
grep -nE 'The Good Guys|Youre Saying|Lefty Looseys|The Ellites|The Pliggas|The Playas|Stars and Strikes|The Danites|Pure Breads|Slamma Jammas|Fellowship of the Swing|Diamonds and Dirtbags' playoffs.html && echo 'RAW TEAM NAME ON PAGE — STOP' || echo 'team-name grep clean'
LIVE_PAGE=playoffs.html node $T/live-test.js $T/emit.html   # ~350 checks in <1 s: boots, scores re-derived, ✓ == score per entry, winners drawn, #e= opens
```
**Do not pipe the test through `tail`** — the exit code is the verdict; read
the last line (`N passed, 0 failed`). `LIVE_PAGE=playoffs.html` points it at
the deployed page (its default is the staged `playoffs-live.html`).
Every reply to Curtis carries the echo line: **"Filed G3 — Claude's team d.
Ephraims Daniel's team · 3 of 22 played · leader: Nathan Knudson 3/3 (ties: 5)"**
— taken from the verify output, not from memory.

### 2d · Commit + push — ONLY with authorization (see §6)

```sh
git add 0821-playoff-results.csv playoffs.html        # explicit paths, never -A (playoffs-live.html / GAMEDAY.md stay untracked unless asked)
git commit -m "G3: Claude's team over Ephraims Daniel's team"
git push origin main
```
Commit message: plain text, captain labels, game number first. **No Claude
attribution line, ever.** A push is a public deploy: GitHub Pages rebuilds in
~30–90 s; `curl -s https://softball.best/playoffs.html | grep -o '"results":"[0-2]*"'`
confirms the live digits once it lands (curl may be blocked for me — then Curtis
checks on his phone; say so).

**Corrections:** a result already pushed that was wrong →
`python3 $T/fix-result.py 0821-playoff-results.csv 3 "The Pliggas"` (edits the
row in place, keeps CRLF, drops blank lines), re-run 2b–2d, commit message
`Correction G3: …`. **Never `sed` this file: it is CRLF, a `$`-anchored pattern
silently matches nothing, and the rehearsal's first correction committed an
unchanged file that way.** Never append a second row for the same game (the
loader rejects duplicates). If the correction changes a LATER game's
participants, the loader will fail on the later row — fix both.

**What the loader refuses, by name (all rehearsed):** a winner that did not
play in that game (`G5 winner 'caleb' did not play in it (jeremy v elliot)`);
a game whose participants are not yet decided (the early-round losers' games
need BOTH feeders — G9 needs G1 and G4; G5 only needs G1, so G5 before G4 is
legal); a duplicate game; a G23 row when G22 went to the undefeated club; a
misspelled raw name (did-you-mean printed).

---

## 3 · Cut-over (once, when Curtis says entries are closed)

Pre-conditions: it is ≥ 15:00 local; Curtis has said the inbox is closed or
given me the last entries; `playoffs-live.html` exists (§0).

```sh
cd $S && git status --short                          # clean, or only the last entry's changes (+ the tracked __pycache__ noise, see below)
printf 'game,winner\r\n' > 0821-playoff-results.csv     # header only; 0 played
cp playoffs-live.html playoffs.html
$T/emit.sh 0821-playoff-results.csv $T/emit.html && python3 $T/splice.py $T/emit.html playoffs.html
LIVE_PAGE=playoffs.html node $T/live-test.js $T/emit.html      # want: N passed, 0 failed
git add analysis.py 0821-playoff-results.csv playoffs.html      # analysis.py: the `live` island change, uncommitted since 08-20
git commit -m "Playoffs live: entries closed at first pitch, 14 brackets in play"
git push origin main
```
(`__pycache__/analysis.cpython-314.pyc` is TRACKED in this repo and shows as
modified after every run — never add it; explicit paths keep it out.)
Then in the browser / by screenshot: the entry desk and the field table are
GONE, the bracket draws with every card "up next"/pending, the leaderboard lists
every entry at 0 of 0 in arrival order, `#e=nathan-knudson` opens an entry.
If anything is off and cannot be fixed in ten minutes: `git checkout -- playoffs.html`
(back to the prediction page, which still works fine with a results island — it
just shows scores on the cards) and run the day under §9.

---

## 4 · The live page (what `playoffs-live.html` IS — build spec)

One page, one chain, no modes (the standing rule). Same design language as the
prediction page — dark scorebug + gold, Avenir Next Condensed display over the
house type, figures monospace — same CSS tokens, so nothing needs re-validating.
**Three colours, one meaning each, unchanged:** gold = advancing, rust =
eliminated, everything else neutral. A ✗ on a missed call wears rust (it is a
loss); a ✓ wears plain ink, never gold.

**Top to bottom:**

1. **Topbar** — brand "Playoff Prediction Brackets"; `tb-state` reads
   `Live · 8 of 22 played · updated Fri 6:52 PM` (from `data.live`); one link,
   "The paper". No Reset.
2. **Lede** — h1 "The bracket is being played. *Here is where it stands.*" and a
   computed paragraph (`sayLive()`): N brackets in play, closed at first pitch,
   games played so far, who leads and on what score (ties listed, tie rule
   stated). Every number from the island.
3. **Prize band** (compressed) — "75,000 sats to the best bracket · Presented by
   yggr · coffee for sats" + one line: entries closed at first pitch Friday
   August 21; N brackets in play; a tie goes to whoever entered first. No enter
   button. yggr link stays. (The `.adv` unit at the bottom stays too, unchanged.)
4. **§01 The bracket — live.** The drawn bracket, read-only: slots are `<span>`s,
   no click handlers. Played games `.done` with `.won`/`.lost` — no runs, the
   desk only ever has the winner. A game whose participants are known but unplayed is `.next`
   ("up next" ring — replaces "ready to pick" in the legend). The plaque reads
   "Pennant · not yet decided · 8 of 22 played", then the champion's name, gold,
   with the one confetti burst when the final result lands (reduced-motion
   guarded, as before). The decider card keeps its dormant/live behaviour,
   driven by the REAL G22 result. Under the canvas: **"Played so far"**, an
   `<ol>` in game order — `G3 · Claude's team d. Ephraims Daniel's team ·
   Aug 21 4:00 PM South` — which is the phone-friendly view and the one a reader
   at the park actually wants. The Horatio-v-Claude vow banner stays and fires
   on the real bracket.
5. **Looking at an entry** (the thing Curtis asked for: "show where their
   prediction went wrong on each game"). The bracket keeps the REAL results as
   its skeleton; the entry is an annotation on every card:
   - played, pick correct → chip `✓ called it`;
   - played, pick wrong → chip `✗ had Caleb's team` in rust (covers cascades: a
     pick for a club that was never in the real game is simply a miss, scored 0,
     and the chip says what they had);
   - unplayed → chip `picks Caleb's team` neutral, or `✗ pick already out` in
     rust when the club they picked has two real losses (the game cannot go
     their way any more — this is where "went wrong" shows before it scores).
   The viewing bar reads "Looking at **Nathan Knudson**'s bracket — #1 · 8 of 8
   right · pennant pick Caleb's team" with a Close button; `#e=<name-slug>` is
   written with `replaceState` and an inbound `#e=` opens the entry on arrival —
   slug is the NAME, never the index (the list re-sorts). No "your bracket", no
   localStorage, no `#b=` codec, no stash/fork.
6. **§02 The leaderboard.** "Who the room likes" tally stays (one vote per entry,
   `champion(resolveCode(k))`), with clubs on two real losses marked `out` in
   rust. Then the ranked cards: rank, name, club or Guest, **8 of 8 right**,
   pennant pick (+ `out` if eliminated), "See this bracket". `.lead` on the
   leader(s). Caption restates: one point per game called right; ties to the
   earlier entry; the clock is the mail's `received`. When the bracket is
   complete the heading becomes "Final — the 75,000 sats go to **Name**"
   (computed: entries[0] after Python's `(-score, received)` sort, which the page
   re-checks).
7. **Footer + `<noscript>`** — rewritten honestly: updated from the field by the
   desk as games finish; entries closed at first pitch; there is no ink edition;
   the season's numbers are in the paper.

**Built as specified, 2026-08-20** (`build-live.py` assembles it from the
current page's head + CSS minus the prediction-era rules, plus `live-src/`:
`extra.css`, `body.html`, `script.js`; island from an emit made with
`--playoff-results`). Live jsdom suite: `live-test.js` (≈300 checks per
island; 1,815 over six game states at build). The only design deviation from
the spec above: while an entry is open, the call REPLACES the card's date line
(`.bg-when.call`) rather than riding beside it — three things on a 128-px
card did not fit — and a picked club that really is in an unplayed game also
gets a neutral inset ring (`.bg-s.pick`). On phones the two lists go two-line
per game (clubs, then call + time).

**Removed outright** (markup AND script): `#field` and the seed table, `#enter`
and everything in it (who/datalist/mail/copy/slip/sendto), chalk/random/clear,
`#bk-enter`, Reset, pick click handlers, `fillBracket`, `applyCode`, `save`,
`STORE`/localStorage, the `#b=` codec, `prize-deadline`, the "you" chip. Keep:
GoatCounter, `confetti.min.js`, og-playoffs.png meta, `islandIsSound()` —
extended to require `typeof data.results === "string" && data.results.length === 23`
and `data.live` — FATAL notice as before if it fails.

**Island additions (analysis.py `emit_playoff_seeds`):**
- `live: {"updated": "Friday 6:52 PM", "played": 8}` — `updated` is the clock at
  emit time (the desk's clock, which is when the result was filed); `played`
  counts non-zero digits.
- entries carry `s`/`p` whenever `--playoff-results` is given, even at 0 played
  (today's code skips scoring on an all-zero code — change `if any(d != "0")` to
  `if results is not None`, passing the flag through `c`).
- everything else unchanged; the OLD prediction page still boots against the
  new island (it ignores unknown keys), which is what makes §9 a safe fallback.

**`load_playoff_results` is unchanged:** header `game,winner`, every existing
guard kept. Winners only.

---

## 5 · The jsdom smoke test (`live-test.js`) — what it must assert

Boots `playoffs.html` (the file in the repo, as it stands) under jsdom with
`runScripts: "dangerously"` (do NOT eval the script a second time — double-boot
makes phantom failures). Three islands: the page's own, and two emitted by
`analysis.py --brackets --playoff-results` against scratch results files (3
played; 22 played + a decider). Asserts:
- no page errors; no `Reset`, `Random`, `Enter your bracket`, `<datalist`, or
  `mailto:` anywhere in the DOM; the team-name grep is clean;
- every played game's card is `.done` and its `.won` slot is the CSV winner;
  the "Played so far" list has `played` items;
- leaderboard order and every card's "s of p" equal Python's island; ties in
  arrival order;
- opening each entry: the number of `✓` chips equals that entry's `s`, the
  number of `✗` chips equals `p − s`; closing restores the real bracket;
- `#e=<slug>` on arrival opens that entry; an unknown slug toasts;
- with 22 (or 23) played: the plaque is crowned with the right club, the
  leaderboard heading names the winner;
- the decider card is dormant until the real G22 goes to the bottom slot.
Then `shots.js` (playwright, served over http): desktop light/dark, 390-px
mobile, one shot with an entry open — **look at them**; jsdom cannot see a bar
that renders at zero width (it has happened).

---

## 6 · Git: the authorization protocol for the day

CLAUDE.md (amended 2026-08-20): commit/push ONLY on explicit, per-request
authorization in the current conversation; an authorization covers the one
action it names and does not carry forward. Tomorrow that means:

- **A result message that contains a push word** — `push`, `ship`, `commit and
  push`, `send it` — authorizes THAT update's commit AND push. I do 2a–2d and
  reply "pushed: <echo line>".
- **A result message without one** → I do 2a–2c, leave it in the working tree,
  reply "staged — say push". Nothing goes out.
- `commit` alone = commit only, no push. `push` alone when there is an
  uncommitted update = commit + push (a push implies the commit of the staged
  work it names).
- I never batch silently: if two results arrive and he says push once, both
  go in one commit and I say so.

If Curtis would rather not type the word twenty-two times, he amends CLAUDE.md
TODAY (not me, unless he asks) — suggested wording for the git rule:
> *Gameday exception, Aug 21–22 2026 only: for playoff results filed per
> GAMEDAY.md, Curtis's message carrying a result is itself the authorization to
> commit and push that result to origin main.*
Either way I state what is being committed and where, every time, and push only
to `origin main`.

---

## 7 · Rehearsal (today, before he leaves for the park)

In a scratch copy of the repo (`git worktree add` or `cp -r` to the scratchpad —
NOT the real tree):
1. Cut-over per §3 against a header-only results file; screenshots.
2. File G1, G2, G3 per §2 — three cycles, timed.
3. File a wrong G4 winner, then correct it in place; confirm the loader catches
   a duplicate row and a non-participant.
4. Try G5 before G4 is filed → loader must refuse ("participants not decided").
5. Fill all 22 with the elimination club winning G22 → decider card goes live;
   file G23 → crowned; heading names the winner; then the variant where the
   undefeated club wins G22 and a G23 row is REJECTED.
6. A tie on the leaderboard between two entries → earlier `received` first.
7. Late entry (`received` 15:01) → refused by name.
8. Kill the shell mid-splice and confirm the recovery line (`git status`, then
   `git checkout -- playoffs.html`, redo) works.
Record timings; the cycle should be well under two minutes including verification.

**Done 2026-08-20** (see §0). Measured: 0.7 s per full cycle before the git
push. Lessons folded into §2: corrections via `fix-result.py` not sed; the
test's exit code not its tail; G5-before-G4 is legal (only G1 feeds it).
To rehearse again: `git clone /Users/cube/Developer/cp-softball <scratch>`,
copy `analysis.py` and `playoffs-live.html` in, `export REPO=<scratch>`, and
every tool follows; never push from the clone.

---

## 8 · The bracket, for mapping his messages (sheet order; top/bottom is NOT home/away)

Seeds: 1 Jeremy · 2 Caleb · 3 Horatio · 4 Sefton · 5 Stafford · 6 Claude ·
7 Gideon · 8 Elliot · 9 Michael ("Mike W") · 10 Boyds Daniel ("Dan Boyds") ·
11 Ephraims Daniel ("Danny") · 12 Seth.

| G | Top | Bottom | When | Field |
|---|---|---|---|---|
| 1 | 8 Elliot | 9 Michael | Fri 3:00 PM | South |
| 2 | 5 Stafford | 12 Seth | Fri 3:00 PM | North |
| 3 | 6 Claude | 11 Ephraims Daniel | Fri 4:00 PM | South |
| 4 | 7 Gideon | 10 Boyds Daniel | Fri 4:00 PM | North |
| 5 | 1 Jeremy | W1 | Fri 5:00 PM | North |
| 6 | W2 | 4 Sefton | Fri 5:00 PM | South |
| 7 | 3 Horatio | W3 | Fri 6:00 PM | North |
| 8 | W4 | 2 Caleb | Fri 6:00 PM | South |
| 15 | W5 | W6 | Fri 7:00 PM | North |
| 16 | W7 | W8 | Fri 7:00 PM | South |
| 9 | L1 | L4 | Sat 8:00 AM | North |
| 10 | L2 | L3 | Sat 8:00 AM | South |
| 11 | L5 | L8 | Sat 9:00 AM | North |
| 12 | L6 | L7 | Sat 9:00 AM | South |
| 13 | W9 | W10 | Sat 10:00 AM | South |
| 14 | W11 | W12 | Sat 10:00 AM | North |
| 17 | W13 | L15 | Sat 11:00 AM | South |
| 18 | W14 | L16 | Sat 11:00 AM | North |
| 19 | W15 | W16 | Sat 12:00 PM | North |
| 20 | W17 | W18 | Sat 12:00 PM | South |
| 21 | W20 | L19 | Sat 1:00 PM | North |
| 22 | W19 | W21 | Sat 2:00 PM | North |
| 23 | W22 | L22 | only if the bottom club wins G22 | — |

Digit codec: `1` = top club won, `2` = bottom club won, `0` = not played. The
chalk code (`11111212122112122212210`) is the "higher seed wins out" reference.
Friday = the whole winners' road (G1–8, 15, 16). Saturday = everything else.
A Horatio-v-Claude line anywhere → the vow banner shows; that is intended.

**Things the bracket cannot do:** a tie — and the league plays none on playoff
day (sudden death; Curtis reports the winner). If a message does not say who
won, ask.
A forfeit is a win for the club awarded it, filed like any other result.

---

## 9 · Minimum viable gameday (fallback if the live page is NOT built)

The prediction page as published already accepts a results island: entries
gain "s of p right", the section re-heads "The leaderboard", and the tally
stays. So with nothing built, the day still works: §2 cycles with the old
`game,winner` schema, and the entry desk stays on the page (still usable, which
is the one honesty problem — mails after 15:00 are simply refused by the loader
and never appear). If that is the day we get, say so to Curtis at cut-over
time, and hand-edit ONLY the prize band's deadline sentence to "Entries closed
at first pitch" — nothing else.

**Owner's instruction (2026-08-20): the live page is built TODAY as
`playoffs-live.html` and must NOT be served at the `playoffs.html` route until
he says entries are closed tomorrow.** Preview: `cd $T && node preview.js
preview-0.html preview-8.html preview-final.html` → `http://localhost:8766/`
(0 results), `/eight`, `/final` — staged islands, repo assets, real route
untouched. It is untracked; it is committed only if he asks, and only under
that name or at cut-over as `playoffs.html`.

---

## 10 · After the last out (Saturday evening / Sunday)

Not gameday work, but so it is not forgotten: the page is then a record, not a
contest. CLAUDE.md's playoffs section needs a "played" paragraph (results file
name, champion, the prize winner, the tie rule as applied); the live page stays
as the permanent playoffs page (no archive copy — it is already dated by its
island); `og-playoffs.png` can stay. The season-final paper (index.html) is
untouched by all of this — the owner's standing rule: the paper carries no
playoff material and does not link to this page.

---

## 11 · `splice.py` (recreate verbatim if the tools dir is gone)

```python
#!/usr/bin/env python3
"""splice.py EMITTED_HTML PAGE_HTML — copy the machine-data island from an
analysis.py --html-afternoon emit into the page, in place."""
import json, re, sys
emit_path, page_path = sys.argv[1], sys.argv[2]
pat = re.compile(r'(<script type="application/json" id="machine-data">)(.*?)(</script>)')
emit = open(emit_path, encoding="utf-8").read()
page = open(page_path, encoding="utf-8").read()
a = pat.findall(emit); b = pat.findall(page)
assert len(a) == 1, f"{emit_path}: expected one island, found {len(a)}"
assert len(b) == 1, f"{page_path}: expected one island, found {len(b)}"
island = a[0][1]
d = json.loads(island)
if island == b[0][1]:
    print("island unchanged — nothing to splice"); sys.exit(0)
out = pat.sub(lambda m: m.group(1) + island + m.group(3), page, count=1)
assert pat.findall(out)[0][1] == island
open(page_path, "w", encoding="utf-8").write(out)
played = sum(1 for c in d.get("results", "") if c != "0")
print(f"spliced {len(island)} bytes into {page_path}: {len(d.get('entries', []))} entries, "
      f"{played} results, results={d.get('results')!r}")
```
