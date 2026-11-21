# sim_waves: notes for Claude Code

A simulation engine for JEE wave problems (Python and SymPy in `engine/`), plus the scene
format (`format/FORMAT.md`), a corpus of problems (`corpus/`) and evaluations (`eval/`).
The engine stays close to physics: one correct answer or a clear error, never a silent
wrong answer, and no invented facts.

Start with `HANDOFF.md` (current state, next milestone, setup).

## Roles
- **Claude Code** implements: plan, build, tests, runs, commits, PRs.
- **ChatGPT (Astra)** is the independent architectural advisor and reviewer. It publishes
  its reviews directly on the GitHub PR.
- **The user** approves milestones and merges. Never merge without the user's approval.

## Milestone process (charter)
PLAN with a cost hypothesis → reserved problems by a separate agent (unread) → build →
**stage 1 PR and review** → fix every confirmed finding with a regression test → freeze
(`FROZEN.md5`) → fresh author on the reserved problems → RESULT.md → FINDINGS.md →
**stage 2: same PR updated** → the user merges.

Each milestone works on its own branch (`feat/mNN-...`) and one PR:
1. Read the docs and the relevant source first. Preserve existing code, uncommitted
   changes, evidence and regression tests. Do not rewrite unrelated files or widen the
   task without approval.
2. **Stage 1 (build):** commit the code, tests and docs; push; open the PR. Then stop
   and report the PR URL for review.
3. **When told to continue,** read Astra's review from the PR with `gh` (reviews, review
   comments and issue comments; e.g. `gh pr view N --comments` and
   `gh api repos/{owner}/{repo}/pulls/N/comments`). Fix each required correction on the
   same branch with a regression test, rerun the relevant tests, push, report the new
   commit SHA, and stop for re-review.
4. **Stage 2 (only after the build is approved):** freeze, blind run, RESULT.md and
   FINDINGS.md on the same branch; push; update the PR; stop for the user to merge.
   Never merge, and never freeze, without the relevant approval.

**Reserved problems stay out of git until the blind run is done** (they are excluded in
`.git/info/exclude`), so no reviewer reading the PR can see them. Commit them in stage 2.

## PR contents
Concise, but enough for independent verification:
- a summary of the changes, by file;
- the exact commit SHA under review;
- test evidence: each suite's command and result, and anything skipped and why;
- limitations and unresolved issues;
- the review brief (`eval/reviewNN/BRIEF.md`): what to hunt for, silent wrong answers
  first; expected values computed by hand; never read the reserved problems.
Copy each round of Astra's findings, with what was done about each, to
`eval/reviewNN/REPORT.md`, naming the reviewer and the commit reviewed.

## Tests
From `engine/`:
- `python -m simwaves test tests/regression -j 2`
- `python -m simwaves test ../format/examples`
- `python -m simwaves test tests/negative`
- `python tests/test_export.py`

On Windows there is no wall-clock limit per scene (it uses SIGALRM), and some scenes are
slow there (r84, r93), or grow without limit in memory (r96: past 4.6 GB): leave them
out of the suite run, run r84 and r93 on their own with a time cap, do not run r96 on
this 8 GB machine, and report all three in the PR.
GitHub from the shell: `gh` (signed in as the repository owner).

## Content rules
- Never commit the book files: the numbered folders `11_*`, `22_*`, `23_*`, `24_*`,
  `*.pdf` and `.export/` (see `.gitignore`).
- Work on branches. The user merges PRs into `main`.
