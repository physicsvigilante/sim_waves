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

## Round 2
- **Reviewer:** ChatGPT (Astra), posted on PR #18 on 2026-11-23.
- **Commit reviewed:** `0ede32a34e4cbdced766165e4dcf61e1985f07f0`.
- **Verdict:** FAIL.
  - Linux CI was green (run 45071038418).
  - Resolved: the original R1 case, R2, the original R3 case, post-ready R6, and O1.
  - Five findings, F1–F5: four high, one medium.
- **Scope decision (review policy, point 5):** this was the second round with the same structural cause: the request lifecycle was not owned end to end. The user chose **option B on 2026-11-23**:
  - **reduce the supported class:** scene files can no longer set their own limits (`expect.limits`); the run's limits apply to every scene, and the parent never parses a scene;
  - **then one shared repair for the rest.**

| # | Severity | Finding | Fix | Tests (`test_limits_review.py`) |
|---|---|---|---|---|
| F1 | high | A 398-byte YAML file with nested merge aliases took 2.5 s to parse in the uncontained parent. A cap on file size does not bound parsing work. | **Class reduced (option B).** `expect.limits` is refused, so the parent never parses a scene. What a scene expects (`error: limit`) is read in a contained worker: one request for all scenes, or one per scene if that is stopped. | the alias-expanding file is stopped by the run's 2 s limit, and its neighbour passes; the parent has no YAML reader for limits |
| F2 | high | The deadline did not cover sending the reply: 8–32 MB replies were accepted after the limit, and a stalled transfer kept the parent in a blocking receive. | The parent owns one absolute deadline covering sending, evaluation and the **whole reply**. The transfer runs on its own thread; past the hard stop the worker tree is killed. A reply complete only after its deadline is a limit, never a value. | a 64 MB reply with a 0.05 s limit is a limit, and a small reply within its limit is a control; a blocked receive ends at the hard stop |
| F3 | medium | An expiry delivered while a budget was being set up or torn down escaped as `_ExpiredHere`, and left a fired entry behind. | State behind a C lock (always released). The thread becomes **critical**, so no new expiry is fired on it, inside the protected region as `fn` returns or raises. Anything pending is delivered there, where it is classified. Teardown is a second line of defence. | a pause at **every line** of `within` and of its inner function: classified each time, with nothing left behind |
| F4 | high | On Linux, a worker survived a parent killed while the worker was still importing; the guardian started only after `ready`. | Ownership from the start: the guardian (Linux) or Job Object (Windows) is set up right after the process starts, before its imports. The worker's first act sets the parent-death signal, and it exits if its parent is already gone. The guardian kills the worker even before it has its own process group. | the parent is killed during the worker's imports, and the worker is gone (also in CI on Linux) |
| F5 | medium | `seconds or DEFAULT` turned 0 and False into the defaults in `run_file`, `run_dir` and `export`. | `resolve_limits`: only `None` selects a default; any other value is validated as given. | `run_file` with 0 or False refused (×4); `None` uses the defaults; `run_dir` with 0 or False refused; `export` with 0 refused |

## Round 3
- **Reviewer:** ChatGPT (Astra), posted on PR #18 on 2026-11-23.
- **Commit reviewed:** `a9c8087e4da06550c2b313b0624a9f45c934a956`.
- **Verdict:** FAIL.
  - Linux CI was green (run 45075496661).
  - Resolved: F1, F3 (60 of 60 line probes), F5, and the earlier R and O items.
  - Six findings, G1–G6: five high, one medium.
- **Scope decision (review policy, point 5):** this was the third round with the same cause: request ownership fragmented across start-up, readiness, target resolution, preflight, evaluation, reply and clean-up. The user chose **option C on 2026-11-23**: **one fresh process per request, owned by the operating system from creation**. There are no reused workers, no recycling and no shared worker. The cost is about 1 s of start-up per request on Windows.

| # | Severity | Finding | Fix | Tests (`test_limits_review.py`) |
|---|---|---|---|---|
| G1 | high | A late reply was reported as a limit, but the worker stayed alive. | There are no reused workers. Every request's process tree is killed before its result is returned, whatever the outcome (`contain.run_request`). | a 64 MB reply complete just after its deadline is a limit, and its process is gone when the result returns |
| G2 | high | Worker start-up was outside the time limit. | The request's one monotonic deadline starts at **admission**, before the process exists; start-up, imports, target resolution and the whole reply count against it. | `os:getpid` with 0.05 s is a limit; with 30 s, a value |
| G3 | high | `view` multiplied the limit by the number of scenes. | Each scene of a view is its own request under the given limit, read inside its process (the parent never parses a scene). The page is written only if every scene finished. | a slow scene with `--time 4` gives a limit and no page; two ordinary scenes give a page |
| G4 | high | A late ordinary error outranked a fired time limit, in the budget and in the parent. | `budget.within` checks its deadline before passing on an ordinary error. The parent classifies **every** reply kind against its own deadline. Target resolution happens inside the budget. | every line of `within`, for a value and for an error; a late value and a late error both give the limit; in a request, an error raised after the deadline is a limit |
| G5 | high | The process ran before the Job or guardian owned it, and a failed job assignment had no kill fallback. | **Windows:** the parent joins a kill-on-close supervisor job, so every child is in it from creation. Children are created **suspended**, assigned their own memory-limited job, then resumed. **Linux:** a new session from creation, then the child's first act sets `PR_SET_PDEATHSIG` and exits if the parent is already gone; a guardian kills the group. Any failure while setting up ownership terminates the process directly. | an injected job/guardian failure gives a CrashResult with no process left; the parent killed before the child's own job/guardian exists leaves no child |
| G6 | medium | `run_file` gave the expectation read and the evaluation a full limit each. | One request per scene (`harness.check_scene`) reads the expectation and runs the scene under the one budget. The expectation is sent to the parent as a note first, so `error: limit` is still honoured. | an alias-expanding scene under `run_file(seconds=4)` is a limit within 4 s plus the grace |
