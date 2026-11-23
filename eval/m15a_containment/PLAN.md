# Milestone 15a: containment and reproducibility

**Charter tier:** tooling. This plan is written BEFORE implementation.
**Source:** the open limitations of m14 (`eval/m14_repairs/RESULT.md`), Astra's
assessment (issue #15, finding 1), and the containment criteria accepted in the builder's
reply there. Agreed with the user as its own milestone; it does not change any physics.

## What is wrong now, and where
- **No limit at all on Windows.** Both time limits use `SIGALRM`, which Windows lacks:
  - the whole-scene limit (`run.py` `_evaluate_once`, 120 s);
  - the inner budgets (`scene.py` `_within`).
  So on Windows a slow SymPy call runs for minutes: SymPy 1.12 on
  `sin(10**17*(x - 1))` in m14 review round 21. r84 and r93 take minutes, and r96 grows past
  4.6 GB on an 8 GB machine.
- **The engine's results differ by platform.** The inner budgets do more than stop work:
  - in `scene.py` `_within`, a budget that runs out falls back to a numerical method or a
    specific refusal (`_peak_of`, `_peak_position`, `_numeric_extremum`);
  - `energy.py` does the same in `_integrate`, `mean_over` and `max_in`/`min_in`.
  On Linux a scene can give a numerical answer where Windows keeps computing, so the same
  scene does not behave the same everywhere.
- **No memory limit anywhere.** It is not enforced on Linux either.
- **The limit covers only part of a request.** `_evaluate_once` times each solve on its
  own: the arbitrary-value reruns (`run.py` `_evaluate_arbitrary`), the `nearest` proof
  and the comparison checks each get a fresh 120 s or 60 s. Nothing bounds the whole
  request.
- **The test harness can be wedged.** `harness.run_dir` uses a `multiprocessing.Pool`
  with `maxtasksperchild=20`. A worker that hangs or exhausts memory is never killed.
  Stopping the run leaves orphaned `spawn_main` workers holding memory (seen twice on this
  machine).
- **No CI, and no pinned environment.** No `.github/workflows`; no requirements file.
  Tests ran on Python 3.10.6, SymPy 1.12, PyYAML 6.0.1, NumPy 1.26.2 and mpmath 1.3.0,
  by convention only.

## Scope (smallest shared change)
1. **One parent-enforced budget per scene request.** `python -m simwaves run` and each
   test scene run in a **child process**. The parent:
   - enforces a wall-clock limit and a memory limit on the **whole request**: load, solve,
     arbitrary-value reruns, the `nearest` proof, comparison checks, observables and exports;
   - kills the child **and its descendants** when either limit is passed;
   - on Windows, uses a Job Object (kill-on-close, a process-memory limit, via `ctypes`, no
     new dependency);
   - on Linux, uses `RLIMIT_AS` and a process group.
2. **Resource errors are their own result.** A new `ResourceLimitError`, which is not a
   subclass of `SceneError`. It is reported as `RESOURCE LIMIT (time 120 s)` or
   `RESOURCE LIMIT (memory 2 GB)`. It is never presented as "inconsistent",
   "undetermined" or "unsupported". In the test harness it is its own status, `LIMIT`,
   counted apart from PASS and FAIL.
3. **Inner budgets that work the same on every platform.** `_within` gets a portable
   implementation: a watchdog thread interrupts the evaluating thread with `_Budget` at the
   deadline (`PyThreadState_SetAsyncExc`; SymPy is pure Python, so the interrupt lands
   between bytecodes). POSIX and Windows then take the same numerical fallbacks and
   refusals. `SIGALRM` stays only if the watchdog fails a test.
4. **A contained test harness.** `run_dir` starts at most `-j N` children, each under the
   per-scene limits, and collects results as they finish. No pool is left behind:
   - Ctrl-C or a killed parent takes every child with it (Job Object or process group);
   - the run ends with a count of LIMIT results and the slowest scenes.
5. **A pinned, qualified environment.** `engine/requirements.txt` with exact versions
   (Python 3.10, sympy 1.12, PyYAML 6.0.1, numpy 1.26.2, mpmath 1.3.0). The engine prints
   a warning at start if the installed SymPy differs. A newer SymPy is a separate decision,
   made only when the full suite passes on it.
6. **Linux CI.** `.github/workflows/tests.yml` on push and pull request:
   - Ubuntu, the pinned environment;
   - the four suites in full (regression, examples, negative, export);
   - r84, r93 and r96 **included**, under the per-scene limits;
   - a job timeout.
   The repository is private, so the job must stay within the free Actions minutes: target
   under 15 minutes per run.
7. **r84, r93 and r96 on Windows.** Each either finishes with its expected result or
   stops with a `LIMIT` result within the budget, without exhausting the machine. They are
   no longer left out of the suite totals; the totals report them by name.

## Supported class (per the review policy)
- **Contained:**
  - every request made through `python -m simwaves run`, `test` and `view`;
  - `harness.run_file` and `run_dir`;
  - the export entry point used by `tests/test_export.py`.
- **Budgets:**
  - defaults of 120 s wall clock and 2 GB of memory per scene request (the current 120 s
    kept);
  - both can be set with `--time` and `--memory` on the command line;
  - a scene's `expect` block may lower its own limit, never raise it.
- **Platforms:** Windows 10 and 11 and Linux (Ubuntu in CI), Python 3.10. macOS is not
  targeted: it should work through the POSIX path, but it is not tested.
- **Guarantee:**
  - a request returns its normal output or a `ResourceLimitError` within the time limit
    plus a few seconds of shutdown;
  - no process it started survives it;
  - results within the limits are identical across the two platforms for the whole suite.

## Containment class (decided in review rounds 2 to 4)
The user narrowed and fixed what containment promises, under the review policy:
- **Round 2, option B:** limits apply to the whole run. A scene cannot set its own
  (`expect.limits` is refused), and the parent never parses a scene.
- **Round 3, option C:** one fresh process per request, owned by the operating system from
  creation. There are no reused workers.
- **Round 4, option A: the threat model.** Containment protects against the engine's own
  runaway computation (too slow, too much memory) and against a request's processes
  outliving it. Its guarantees:
  - **Time:** one deadline from admission covers process set-up, start-up, evaluation and
    the whole reply. Anything complete after it is a limit, and a set-up that hangs ends at
    the deadline plus the grace.
  - **Memory:** the cap applies before the request is read. On Windows the Job is assigned
    while the process is suspended; on Linux the child sets `RLIMIT_AS` from its command
    line before reading. A request whose pickled arguments exceed 16 MB is refused before
    any process starts.
  - **Clean-up:** every process in the request's **process group** (Linux) or **Job**
    (Windows) is gone before the result is returned. If the parent dies, the request's
    process dies too.
  - **Windows fails closed:** if the parent cannot join its kill-on-close supervisor job, no
    request process is started.
- **Outside the class (documented, not guaranteed):**
  - **A process the request deliberately detaches** into a new session or process group
    (Linux `setsid`). The engine itself starts no processes, so this needs code written to
    escape.
  - **The parent killed during the first instants of the child's interpreter start-up on
    Linux**, before its first line of Python sets the parent-death signal. The child then
    exits by itself at that first line, because it sees its parent is gone, before reading
    any request. It never runs a request unowned.

## Excluded
- Any change to physics, maths services or scene format. Result values must not change.
  The only allowed differences are:
  - Windows scenes that used to run without limit now hit a `LIMIT`;
  - Windows now takes the numerical fallbacks Linux already took.
  Each difference is listed in RESULT.md.
- Speeding up slow scenes. r84 and r93 are contained, not optimised.
- A SymPy upgrade.
- CI on Windows (Actions minutes); Windows is verified locally.
- The core consolidation (m15b) and the error-hunt fixes from issue #17. Those go to
  their own milestones.

## Implementation-cost hypothesis
After this milestone, these need no further tooling work:
- **(a)** running any scene on Windows or Linux, including r84, r93 and r96, with a
  bounded time and memory and a clear `LIMIT` result instead of a hang;
- **(b)** stopping a test run (Ctrl-C) without orphaned processes;
- **(c)** a pull request getting its full test results from CI without a local run;
- **(d)** the same scene giving the same result on both platforms, slow numerical
  fallbacks included;
- **(e)** a reviewer reproducing the exact environment from `requirements.txt`.

## Tests (new, with hand-checked expectations)
- A scene that loops beyond the time limit gives `LIMIT (time)`, within the limit plus
  5 s.
- A scene that allocates beyond the memory limit gives `LIMIT (memory)`, and the machine
  stays responsive.
- An inner `_within` budget runs out on Windows and takes the same numerical fallback as
  on Linux: a peak of overlapping Gaussians, as in r84.
- A `LIMIT` result is never reported as `InconsistentError`, `UndeterminedError` or a
  plain `SceneError`.
- After a run is interrupted and after a `LIMIT`, no child process remains.
- `-j N` never has more than N scene children alive at once.
- An `expect` block that lowers the limit is obeyed; one that raises it is refused.
- The whole existing suite passes with the same values, apart from the listed
  differences.
- In CI, the workflow runs green on the branch, with its duration recorded.

## Stage 2 (agreed with the user, 2026-11-23: reserved scenes)
m15a changes how scenes run, not what authors write, so a blind **authoring** run does
not test it.
- **Reserved set:** a separate agent writes about 6 reserved **scenes**. It reads only
  this PLAN, FORMAT.md and the examples, and does not run the engine. The scenes are
  realistic JEE scenes plus scenes designed to be slow, memory-hungry or deeply nested.
  Each key lists the acceptable outcomes: the hand-computed value, or `LIMIT`. It never
  accepts a wrong value, a hang or a surviving process.
- **After the freeze,** they run on Windows and in CI. The transfer evidence is that each
  gets an acceptable outcome on both platforms, with no orphaned process.
