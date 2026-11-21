# sim_waves: notes for Claude Code

A simulation engine for JEE wave problems (Python and SymPy in `engine/`), plus the scene
format (`format/FORMAT.md`), a corpus of problems (`corpus/`) and evaluations (`eval/`).
The engine stays close to physics: one correct answer or a clear error, never a silent
wrong answer, and no invented facts.

Start with `HANDOFF.md` (current state, next milestone, setup).

## Milestone process (charter)
PLAN with a cost hypothesis → reserved problems by a separate agent (unread) → build →
review → fix every confirmed finding with a regression test → freeze (`FROZEN.md5`) →
fresh author on the reserved problems → RESULT.md → FINDINGS.md → branch and PR. The user
merges.

## Review
Reviews are done by Codex (GPT-6.2 Astra, medium effort; see `.codex/config.toml`)
through the Codex plugin for Claude Code.
1. Write the review brief to `eval/reviewNN/BRIEF.md`. It says:
   - what changed and which files;
   - what to hunt for, with silent wrong answers first;
   - that expected values are computed by hand;
   - that the reviewer must never read the reserved problems.
2. Run `/codex:adversarial-review` with the brief as its focus. Use `/codex:review` for a
   plain code review of uncommitted changes.
3. Save the findings to `eval/reviewNN/REPORT.md`. Name the reviewer (Codex,
   gpt-6.2-astra, medium).
4. Fix every confirmed finding and add a regression test (`engine/tests/regression/`)
   before freezing.

## Tests
From `engine/`:
- `python -m simwaves test tests/regression -j 2`
- `python -m simwaves test ../format/examples`
- `python -m simwaves test tests/negative`
- `python tests/test_export.py`

## Content rules
- Never commit the book files: the numbered folders `11_*`, `22_*`, `23_*`, `24_*`,
  `*.pdf` and `.export/` (see `.gitignore`).
- Work on branches. The user merges PRs into `main`.
