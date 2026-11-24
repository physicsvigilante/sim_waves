# Milestone 15a (containment and reproducibility): result

## Transfer evidence (reserved scenes)
- **Setup:** six reserved scenes with keys, S1–S6 (`reserved/`). A separate agent wrote
  them, reading only the PLAN, FORMAT.md and the examples, and without running the engine.
  Three are ordinary JEE scenes that should finish quickly (S1–S3). The other three are
  designed to be slow (S4), memory-hungry (S5) or deeply nested (S6). Each key lists its
  acceptable outcomes: the hand-computed values, or `LIMIT` where the scene was designed to
  hit one. It never accepts a wrong value, a hang or a surviving process.
- **Disclosure:** when it finished, the scene-writer agent's reply described the structure
  of S4–S6 (12 Gaussians plus sin(10¹⁷ x), a billion modes, nesting) but no values. The
  developer saw that summary; the scenes and keys themselves were not read before the freeze.
- **Freeze:** `run/FROZEN.md5`, taken at `2fe4ecb`, the commit Astra passed in review
  round 12 (freeze commit `b1b5c0d`). It covers FORMAT.md, every engine source file,
  `requirements.txt` and the CI workflow; `run/engine_at_run/` is the engine at the freeze.
  The hashes were rechecked after the run: unchanged.
- **Run:** each scene alone through the CLI with the default limits (120 s, 2048 MB), by
  `run/run_reserved.py`, which records the output, the exit code, the time, and any
  `simwaves.child` process left afterwards. The outputs are in `run/windows/`. The keys
  were then also graded by the engine's own checker (each key's values written as an
  `expect` block).

| Scene | Designed to test | Windows (Python 3.10.6) | Time | Left running | Acceptable |
|---|---|---|---|---|---|
| S1 | closed pipe: length solved from the fundamental; a mode count in a band | 17/20 m, 300 Hz, 17/15 m, 4: all exact | 2.7 s | none | **yes** |
| S2 | Doppler (moving source) and beats | 2125/4 Hz, 16/25 m, 125/4 Hz: all exact | 2.2 s | none | **yes** |
| S3 | intensity and decibels, power solved from a level | π/25 W, 80 dB, 100: all exact | 2.4 s | none | **yes** |
| S4 | peak of 12 overlapping Gaussians (a numerical fallback, as in r84) and of sin(10¹⁷(x − 1)) | `peak_p` 0.0529445743 m and `where_p` 0.55000001 m, within the key's 0.1%; **`peak_h` 0.999999911344 m, key exactly 1 m** | 63 s | none | **no** (`peak_h`) |
| S5 | a count over a billion modes, and a degree-100 expansion in 5 variables | `LIMIT (memory 2048 MB)`, exit 3 | 46 s | none | **yes** (the key accepts LIMIT) |
| S6 | 17 observables: nearest inside nearest, max/min chains, 12 nested abs, a standing wave's envelope, travel time across a junction | all 17 exact | 2.3 s | none | **yes** |

**On Windows, 5 of 6 outcomes are acceptable.** Every scene finished or stopped within its
limits, and no process was left behind after any of them. The engine's checker agrees:
S1, S2, S3 and S6 match their keys; S5 is stopped by a memory limit (its key's LIMIT
outcome); S4 fails on `peak_h` alone. S3's level shows as a mismatch only because the key
writes `80 dB` and an `expect` value cannot carry dB; the value is 80.

**Linux (CI):** not run yet. GitHub did not start the CI jobs on the freeze commit
("recent account payments have failed or your spending limit needs to be increased").
The run is ready as its own workflow (`.github/workflows/reserved15a.yml`, so the frozen
`tests.yml` is unchanged). It first checks that the engine is unchanged since `2fe4ecb`,
then runs the same script. Its outcome will be added here.

### S4: the one unacceptable outcome
The largest |y| of sin(10¹⁷(x − 1)) is exactly 1. The engine's symbolic search ran past its
15 s budget, so it took the numerical fallback that m15a makes Windows take as Linux does.
- That fallback cannot follow this wave. Its period (6.3 × 10⁻¹⁷ m) is smaller than the
  spacing of floating-point numbers near x = 1 (2.2 × 10⁻¹⁶), so the search can only
  return its best sample.
- It printed that sample to 12 digits, 0.999999911344, without saying how precise it is.
  It is 8.9 × 10⁻⁸ too low: right to the 6 digits shown in brackets, wrong in the 8th.
  The key gives no tolerance for it, and the engine's default is 10⁻⁹.
- This is a numerical defect of the peak service, not of containment. It came before m15a
  (Linux has always taken this fallback). **The user decided (2026-11-24) to record it and
  fix it in the error-fix milestone**, with the other confirmed findings. m15a excludes
  changes to the physics, and fixing it here would mean unfreezing. The fix: the numerical
  peak refuses a wave it cannot resolve, or reports its precision.

## Cost hypothesis vs actual
- **(a) Any scene, r84, r93 and r96 included, runs on Windows and Linux with bounded time
  and memory, and a clear `LIMIT` instead of a hang:** confirmed. r84, r93 and r96 run on
  Windows for the first time (3/3 pass, 10–20 s each). The reserved scenes all finished or
  stopped within their limits; S5 gave a clear memory LIMIT.
- **(b) Ctrl-C without orphaned processes:** confirmed by the review regressions (a caught
  Ctrl-C around `run_dir`, and Ctrl-C during a request's data check).
- **(c) A PR gets its full test results from CI without a local run:** confirmed through
  stage 1 (every commit sent for review was green in CI, Python 3.10.22). It is blocked at the
  moment only by the GitHub account's billing.
- **(d) The same scene gives the same result on both platforms:** confirmed for the
  regression suite (339/339 on Linux, 336/336 plus r84/r93/r96 on Windows). For the
  reserved scenes, pending the Linux run.
- **(e) A reviewer can reproduce the environment from `requirements.txt`:** confirmed;
  Astra's reviews used CI's pinned environment.
- **Cost:** the containment runner took **12 review rounds** with Astra
  (`eval/review15a/REPORT.md`), far beyond the plan. Five successive rounds (J1, K1, L1,
  M1, N1) had one cause: owning a process from the moment it exists, while cancellation
  can come at any instant. The user made scope decisions in rounds 2, 3, 4, 6, 8 and 10.

## Post-run fixes
None. The S4 defect is recorded for the error-fix milestone (see above and FINDINGS.md).

## Production changes by reason
- **Planned (PLAN.md scope):**
  - portable time budgets (`budget.py`, a watchdog thread) in place of SIGALRM;
  - `ResourceLimitError`, a result of its own, never a physics error;
  - every request (one `run`, each scene of `test`, each scene of `view`) in its own fresh,
    OS-owned process: a Job Object on Windows (inside a kill-on-close supervisor job), a
    new session with a parent-death signal and a guardian on Linux;
  - per-request limits, 120 s and 2048 MB by default, `--time` and `--memory`;
  - the pinned environment (`requirements.txt`, `requirements-dev.txt`) and Linux CI.
- **Review 15a fixes (12 rounds; `eval/review15a/REPORT.md`):**
  - a limit outranks any later outcome; the deadline starts at admission and covers set-up;
  - no per-scene limits in scenes (option B); one fresh process per request (option C);
  - a declared containment class (option A), stated in the PLAN;
  - one cancellation state per request; Ctrl-C cancels every active request;
  - plain, bounded request data: exact bytes as sent, serialised once, at most 16 MB;
  - the commit-point design: a creation either committed before the cancel or never begins;
  - `kill()` waits for a creation step in progress, so no process is alive after a result;
    the declared exception is the timing when a creation call stalls (option 1);
  - limits checked exactly: at most 1,000,000 s and 1,048,576 MB; integers never converted
    to float; the CLI converts only a limit's significant digits.
- **Post-run fixes:** none.

## Open limitations (to the project review and later milestones)
- **S4's numerical peak** (above): to the error-fix milestone.
- **The Linux run of the reserved scenes** waits for the GitHub account's billing.
- **Declared out of class (PLAN):** a process the request deliberately detaches; the parent
  killed in the first instants of the child's start-up on Linux; the result's timing when a
  creation call stalls inside the operating system.
- macOS is not tested. With `-j N`, memory can reach N × the per-request limit.
