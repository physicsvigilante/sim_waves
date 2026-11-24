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

## Review policy (supported class)
Adopted after milestone 14, from Astra's assessment (issue #15).
1. **Declare the supported class first.** Before implementation, each new service states
   in its PLAN and in FORMAT.md:
   - its physical model;
   - the expression class it accepts;
   - any variable and domain restrictions;
   - its result guarantee (exact, proved or sampled);
   - its resource budget.
   "Any expression SymPy accepts" is not a support specification.
2. **What must be fixed.** Within the declared class, any of these is REQUIRED:
   - an accepted wrong result;
   - a lost valid branch;
   - an invented assumption;
   - an invalid unit or domain transformation;
   - a regression.
   A wrong answer in a touched path counts even if it predates the PR.
3. **How to fix it.** Fix it correctly, **or refuse the affected unsupported class** with
   a sound, documented rule. Such a rule must:
   - be checkable before any unbounded work;
   - cover equivalent ways of writing the same input;
   - have valid-neighbour controls in the tests.
   Never blacklist only the reported example. A wrong accepted answer is never waived as
   "not JEE".
4. **Extremes and roots.** These need the service's stated completeness guarantee.
   Unresolved regions, unorderable breakpoints, singularities and unbounded periodic sets
   must not silently disappear; where the guarantee cannot be met within budget, return a
   specific error. Sampled agreement never certifies an exact global result or a
   universal claim.
5. **Stop patching a repeated cause.** After two successive rounds with the same
   structural cause, stop patching locally and ask the user for a scope decision: a
   shared repair, or a declared supported-class reduction with its coverage cost
   recorded. There is no round cap that approves unresolved wrong answers.
6. **What a re-review covers:**
   - the changed paths;
   - earlier REQUIRED findings;
   - valid controls;
   - cross-cutting invariants.
   Capability outside the agreed class is OPTIONAL or a future milestone.

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
The environment is pinned in `engine/requirements.txt` (tests also need
`requirements-dev.txt`). From `engine/`:
- `python -m simwaves test tests/regression -j 3`
- `python -m simwaves test ../format/examples`
- `python -m simwaves test tests/negative`
- `python tests/test_export.py`
- `python tests/test_limits.py` and `python tests/test_limits_review.py` (containment)

Every scene runs in its own fresh process, owned from creation, with 120 s and 2048 MB
by default, start-up included (m15a). A scene that passes a limit is reported as LIMIT, never
as a physics result. With `-j 3` at most three run at once, so at most 6 GB in all on this
8 GB machine. Run the limit scenes with `python -m simwaves test tests/limits --time 6
--memory 512` (with `SIMWAVES_TEST_HOOKS=1`); `tests/test_limits.py` and
`tests/test_limits_review.py` do this for you.
Linux CI (`.github/workflows/tests.yml`) runs every suite on each pull request; report
its result in the PR.
GitHub from the shell: `gh` (signed in as the repository owner).

## Content rules
- Never commit the book files: the numbered folders `11_*`, `22_*`, `23_*`, `24_*`,
  `*.pdf` and `.export/` (see `.gitignore`).
- Work on branches. The user merges PRs into `main`.
