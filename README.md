# softball.best

A weekly editorial stats site for a church softball league, published at
**[softball.best](https://softball.best/)**.

Every week the league posts new batting numbers. This repo harvests them, runs them through a
single Python script, and turns the output into a hand-written newspaper-style page: who collapsed,
who surged, which draft picks were a steal, and which captain should not have picked himself.

**The entire site is written by Claude.** Every page, every table, every joke, and the analysis
script itself. A human (the repo owner) says "the new numbers are up," reviews the result, and
commits it. That's the whole workflow. If you're here to see what a Claude-maintained project
actually looks like over many iterations, [`CLAUDE.md`](CLAUDE.md) is the interesting file — it's
the accumulated house style, editorial rules, and hard-won corrections that keep each edition from
reading like the last one.

## How it works

There is **no build step and no JavaScript** (one exception: a privacy-friendly GoatCounter
analytics snippet). Every page is static, hand-authored HTML with inline CSS, served straight from
`main` by **GitHub Pages**. You can open any `.html` file in a browser and it just works.

The data pipeline is deliberately boring:

1. The league's numbers are harvested from cpsoftball.com into a CSV snapshot (`0710-stats.csv`).
2. `analysis.py` reads the snapshot (plus previous ones) and prints a digest of *every* number the
   page could want — z-scores, draft value, week swings, streaks, standings luck.
3. The page is written from that digest. **Numbers are transcribed, never computed by hand.** If a
   number isn't in the script's output, the rule is to extend the script, not to do arithmetic in
   your head.

`analysis.py` is stdlib-only Python 3 and can also emit page-ready HTML tables (`--html-tables`),
so the big tables are generated rather than typed.

```bash
# just this week's numbers
python3 analysis.py 0710-stats.csv

# the full weekly digest: this week vs last, two-week arcs, standings
python3 analysis.py 0710-stats.csv --prev 0703-stats.csv --prev2 0612-stats.csv \
  --standings 0710-standings.csv --prev-standings 0706-standings.csv
```

The script validates as it goes and exits loudly on bad data: the adjusted-average formula must
hold for every row, the draft grid must be 12 teams × 12 rounds, and snapshots must join cleanly.

## Repo layout

| Path | What it is |
|---|---|
| `index.html` | The **current edition** — always the newest snapshot |
| `YYYY-MM-DD.html` | Frozen **archive editions**, named for their data snapshot date |
| `analysis.py` | The single source of truth for every number on every page |
| `MMDD-stats.csv` | Raw weekly batting snapshots |
| `MMDD-standings.csv` | Weekly standings snapshots |
| `CLAUDE.md` | The house rules: data facts, editorial conventions, weekly procedure, style |
| `CNAME` | GitHub Pages custom-domain file |
| `favicon.svg` · `apple-touch-icon.png` · `og.png` | Site chrome |

Two ideas worth knowing before you touch anything:

- **The adjusted average is `(hits − caused outs) ÷ at-bats`.** A "caused out" (a baserunning
  mistake, roughly) erases a hit. This league stat is why nobody's numbers match a normal box score.
- **Archives are frozen.** An archive page is honest to its date — it never mentions data newer
  than its own snapshot, and it's never retro-edited when the design or the rules change.

## Contributing

**Please do.** This is a small, low-stakes, genuinely fun repo, and there's no gatekeeping here — if
you found this because you play in the league, because you like baseball statistics, or because you
wanted to see how far an LLM can carry a project, you're welcome to open a PR.

Things that would be great to have:

- **New statistics.** The script already knows draft value, z-scores by round, Pythagorean luck, and
  two-week arcs. It does *not* yet know anything about game results — `schedule.php` on the league
  site has every final score, which would unlock win/loss streaks, head-to-head grids, close-game
  splits, and strength of schedule. That's the biggest open door.
- **Design and accessibility.** The CSS is hand-written and lives inline in each page. Light and
  dark mode, the mobile breakpoint, table scrolling, contrast, focus states — all fair game.
- **Bugs in the numbers.** If a figure on a page looks wrong, it probably is, and a bug report with
  the row and the snapshot is a real gift. Same for a broken link or an anchor that doesn't resolve.
- **Better prose.** Genuinely. If an edition reads flat, say so.

A few ground rules that keep the site coherent:

1. **Read [`CLAUDE.md`](CLAUDE.md) first.** It's long, but it's the spec — the data invariants, the
   analysis conventions, the page anatomy, and the rules about what may be said where.
2. **No build step, no JavaScript, no frameworks.** Static HTML and inline CSS. This constraint is
   the point, not an accident.
3. **Every number on a page must come from `analysis.py` output.** New stat? Add it to the script,
   then transcribe it.
4. **Internal links are relative** (`2026-07-03.html`), never root-absolute.
5. **Don't retro-edit the archives.**
6. Run `python3 analysis.py <snapshot>.csv` before you open a PR. It must exit 0 with no `WARN`
   lines.

Issues and questions are just as welcome as code. If you're not sure whether an idea fits, open an
issue and ask — the answer is usually yes.

## Credits

Numbers from the league at [cpsoftball.com](https://cpsoftball.com/). Analysis, prose, jokes, and
questionable draft verdicts by Claude. Any resemblance between a player's adjusted average and their
actual softball ability is coincidental and, in several documented cases, cruel.
