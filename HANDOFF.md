# Handoff: moving sim_waves to Claude Code (2026-11-21)

## Where things stand
- **Engine:** milestones 1–13 are done and merged.
  - strings, pulses, sound media, resonators;
  - rays and interference, energy, scale-free/arbitrary values, comparisons;
  - Doppler from first principles, light (`type: em`, relativistic);
  - tension from mechanics, frequency bands, output units (`in cm`).
- **Last evaluation:** run 7, a blind test of 44 book problems.
  - **PR #12 is open (not merged).** It holds only the run 7 write-up.
  - No wrong engine value, no misrepresentation, and 77% full coverage.
  - 14% of answers were decided by hand, mostly physics outside the model.
  - See `eval/run7/SCORECARD.md` and `eval/run7/GRADES.md`.
- **Tests (all passing):** regression 176, examples 42, negative 12, export 32.
- **New in this folder, not yet on GitHub:** `.codex/config.toml`, `CLAUDE.md`, and this
  file.

## This folder is not a git repository
The previous sessions committed from a separate clone. To make this folder track GitHub
without touching your files (the book files stay untracked, thanks to `.gitignore`), run:
```powershell
cd C:\Users\samee\Documents\sim_waves
git init
git remote add origin https://github.com/physicsvigilante/sim_waves.git
git fetch origin
git reset --mixed origin/main     # index = main; working files unchanged
git status                        # expect: CLAUDE.md, HANDOFF.md, .codex/ new; eval/run7 etc. if PR #12 is not merged
```
Merge PR #12 first, or expect `eval/run7/` and the corpus additions to show as untracked
until it is merged.

## Next milestone (suggested): m14, service repairs (light)
Seven defects that run 7 found. All are refusals or wrong messages, none a wrong value;
see `eval/run7/SCORECARD.md`, "Engine defects", for the evidence.
1. **`nearest()` refuses values that depend on solved unknowns** ("needs numbers").
   It refuses a bare unknown, but accepts a ray frequency with a solved source frequency,
   so it is inconsistent. This hit 7 scenes.
2. **`in <unit>` inside `nearest()`** gives "comparison not allowed here".
3. **A quoted zero in a position list is rejected:** `"0[m]"` gives "needs a unit".
4. **`_check_comparisons` over-scales arbitrary values.** It uses `COMPARISON_SCALES` up
   to ×1000, while the docs say ×89, and that trips the "not sound" guard on an arbitrary
   sound speed.
5. **`limit()` refuses a symbol that has a stated bound.** Bounded symbols become
   expressions; see `Scene.bound_variable`.
6. **An unknown k and phase with both points off the origin are refused,** even when a
   bound leaves one branch (run 7, integer/5).
7. **Missing units:** km/h and μm (`um`).

After m14, the recurring physics gaps are pressure at a point (P0 ± p) and accelerating
sources in Doppler. Then a run 8 blind test. Run 7's sampling found 9 more Doppler
problems that are still sealed.

## How a milestone is run (charter; also in CLAUDE.md)
1. PLAN with a cost hypothesis (`eval/mNN_*/PLAN.md`), and a copy of the engine in
   `engine_before/`.
2. Reserved problems, written by a separate agent that has read only the PLAN. You never
   read `reserved/`.
3. Build, add regression tests, and update `format/FORMAT.md` and `format/FINDINGS.md`.
4. Review: now by Codex, gpt-6.2-astra at medium effort (`.codex/config.toml`).
   - Write the brief to `eval/reviewNN/BRIEF.md`.
   - Run `/codex:adversarial-review`.
   - Save the findings to `eval/reviewNN/REPORT.md`.
   - Fix every confirmed finding and add a test for each.
5. Freeze: copy `reserved/R*.yaml` to `run/problems/`, write `run/TASK.md` (copy it from a
   previous milestone), copy the engine to `run/engine_at_run/`, and write
   `run/FROZEN.md5`.
6. A fresh author agent works on the reserved problems, using FORMAT.md and the examples
   only.
7. Write `RESULT.md`: key matches, the hypothesis compared with the actual result, and
   the production changes by reason. Add an entry to `FINDINGS.md`.
8. Commit on a branch and open a PR. The user merges.

Blind runs (run 5–7) follow `eval/run7/README.md`:
- a transcription agent uses `corpus/book4_waves/TRANSCRIBE.md` and `candidates.json`,
  seed 20261115;
- three author agents each run only their own files;
- an independent grader follows the `eval/run6/GRADES.md` conventions;
- `eval/grade.py` gives the raw key check.

## Codex setup (one-time, on this computer)
1. Check Node.js with `node -v`. If it is missing, run `winget install
   OpenJS.NodeJS.LTS` and reopen PowerShell.
2. Run `npm install -g @openai/codex@latest`, then `codex login`.
3. In this folder, run `codex`. Trust the folder, and check that `/model` shows
   gpt-6.2-astra at medium.
4. In Claude Code, run `/plugin marketplace add openai/codex-plugin-cc`, then `/plugin
   install codex@openai-codex`, `/reload-plugins` and `/codex:setup`.

## Practical notes
- **Running the engine:** run it from `engine/`. For example, `python -m simwaves run
  <scene.yaml>`, or `python -m simwaves test <folder> -j 2`. The full regression suite
  takes about 100 s.
- **Expressions:** times and quantities inside expressions need brackets, like `t=2[s]`;
  a bare `2 s` works only as a field value.
- **Safe to delete** (leftovers that could not be removed before):
  - `eval/review10/regsub/`
  - `corpus/book4_waves/_to_delete_run6_dupes/`
  - `.export/gen6/`, `.export/gen7/`
  - `.export/book_pages/zz_crop_tmp.png`
- **Never commit the book files:** the numbered folders `11_*`, `22_*`, `23_*`, `24_*`,
  `*.pdf` and `.export/`.
