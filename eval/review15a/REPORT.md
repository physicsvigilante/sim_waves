# Review 15a report: milestone 15a, containment and reproducibility

## Round 1
- **Reviewer:** ChatGPT (Astra), posted on PR #18 on 2026-11-23.
- **Commit reviewed:** `bb3c56338924b4d131aa2cd9251139a9acd670b4`.
- **Verdict:** FAIL. Six required findings, one optional.
- **Astra's evidence:** CI run 45068188807 green on Linux. Astra probed the four changed modules on Linux with CPython 3.13 and SymPy 1.14 (not the qualified environment); full-engine commands were derived from the source.
- **Reproduction here (Windows, Python 3.10.6):**
  - **R1:** reproduced, the fallback returned after the outer deadline.
  - **R2:** reproduced by fault injection.
  - **R3:** reproduced, `-1` accepted.
  - **R4:** reproduced, the parent parsed a 4 MB file.
  - **R5:** reproduced, `run_file` and `export` uncontained.
  - **R6:** the soft-timeout case reproduced. On Windows the Job Object already kills descendants on parent death; the Linux case is covered in CI.
  - **O1:** reproduced, the payload was alive in the fallback.

| # | Severity | Finding | Fix | Tests |
|---|---|---|---|---|
| R1 | high | An inner budget's expiry could overwrite an earlier whole-request expiry; the inner fallback then returned a normal value. | Once a budget has fired on a thread, no other budget fires on that thread until the fired one's `within` has handled it. A `within` whose deadline has passed never returns a value, even if fn finished just after it (`budget.py`). | `test_limits_review.py`: outer wins (5 trials); inner-only control takes the fallback; in a worker, a `LimitResult`; another thread; a late return refused |
| R2 | high | A worker that failed to start, or a scheduler failure, left scenes without a result, and the test run could exit 0. | Every item gets exactly one result. A start-up failure, a transport failure or an item never reached gives a `CrashResult` (`contain.py` `Worker.call`, `run_many`). `run_dir` records a CRASH for any scene without a status. An empty folder, or an invalid run limit, is an ERROR (`harness.py`). | an invalid limit gives ERROR and exit ≠ 0; an empty folder is not a success; injected start-up failure (3 items, 3 crashes); injected failure part-way (5 accounted for) |
| R3 | high | A negative memory limit raised `RLIMIT_AS` to almost 2⁶⁴ bytes. Zero, booleans, NaN, negative time and fractional memory were also accepted. | `check_limits`: finite, positive, typed (no booleans), whole MB, at least 256 MB, never above the run's. Applied to `expect.limits`, to the CLI, and at the containment boundary (`Worker`, `Worker.call`). The `limits` mapping may hold only `time` and `memory`. | 13 refused inputs; a valid lower control; `Worker(-1)` and NaN refused at the boundary |
| R4 | high | The parent parsed every whole YAML file, with no limit, before any worker started. | **Bounded admission:** a scene file larger than 64 KB (the largest scene in the repository is 2.5 KB) is refused before it is parsed, in `scene_limits` and in `load` (`contain.check_scene_size`). The parent parses at most 64 KB. | a 4 MB file refused in under 0.2 s |
| R5 | high | The public `harness.run_file` and `export.export` ran in-process with no limit, and `evaluate(timeout=…)` ignored its timeout. | `run_file` runs in a contained worker, honouring `expect.limits` and `error: limit`. `export` runs through `contain.call_bounded`: a shared contained worker, retired after any limit, with the worker's exceptions carried back to the caller. Inside a worker both call through directly, never nesting a worker. `evaluate(timeout=…)` enforces its time budget. A spawned worker no longer re-runs the caller's own script. | `run_file` with `error: limit` gives PASS, without it LIMIT; `export(…, seconds=1)` raises `ResourceLimitError`; `evaluate(…, timeout=0.5)` raises it; `test_export.py` 33/33 through the bounded `export` |
| R6 | high | Descendants survived a soft time limit, the worker being reused, and, on Linux, the parent's death (`PR_SET_PDEATHSIG` covers the worker only). | A worker that hits any limit is retired with everything it started before the next request. On Linux, a **guardian** process outside the worker's process group holds a pipe from the parent and kills the whole group when the pipe closes: worker retired, or parent dead. On Windows the Job Object does this. | soft time limit, hard kill in C, retire after a normal request, parent killed: worker and descendant gone in each (run in CI on Linux too) |
| O1 | medium, optional | The memory fallback kept the failed attempt's traceback and locals alive inside the caller's handler. | The budget's exception is raised after the `except` block, so the attempt's frames are released first, with no `__context__`. | a weak reference to the attempt's payload is dead inside the fallback |
