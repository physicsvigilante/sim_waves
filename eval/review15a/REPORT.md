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

## Round 4
- **Reviewer:** ChatGPT (Astra), posted on PR #18 on 2026-11-23.
- **Commit reviewed:** `c0297fb1c08386f987f4963d35706d00fa1c86da`.
- **Verdict:** FAIL.
  - Linux CI failed at this commit (run 45078530560), in the G2 check only.
  - Resolved: G1, G3, G4, G6.
  - Five findings, H1–H5. Astra records that these are containment failures, not wrong physics answers.
- **Scope decision (review policy, point 5):** this was the fourth round with the same cause, ownership at the operating-system level. The user chose **option A on 2026-11-23**: declare the threat model and its out-of-class cases, then fix the rest. The class is set out in the PLAN under "Containment class" and in FORMAT.md.

| # | Severity | Finding | Fix | Tests (`test_limits_review.py`) |
|---|---|---|---|---|
| H1 | high | Linux: the child was unowned until its first Python line. Windows: carried on without the supervisor job. | **Windows fails closed:** with no supervisor job, no request process is started. **Linux, declared out of class:** a parent killed during the child's interpreter start-up, before its first line sets the parent-death signal. The child then exits at that first line (it sees its parent is gone), before reading any request, so it never runs a request unowned. | Windows: without the supervisor job, a CrashResult and no process started; Linux: the earlier-window test (G5) still passes |
| H2 | high | Linux: a descendant that detaches into a new session escapes clean-up. | **Declared out of class:** clean-up covers the request's process group (Linux) or Job (Windows). A process deliberately detached into a new session is outside it; the engine starts no processes. | the same-group descendants (R6) are still cleaned up in every case |
| H3 | high | Process set-up was not under the deadline: a hang blocked; a late failure was a crash. | Set-up runs on its own thread under the request's deadline: a set-up that never completes ends at the hard stop; one that fails after the deadline is a limit. | a slow set-up (0.5 s against 0.3 s) is a limit, and within 30 s gives the value; a late failure is a limit, and a prompt failure a crash; a set-up that never completes stops at `1 + GRACE` |
| H4 | high | Linux: the memory cap came after the request was unpickled; requests were unbounded. | The child's memory cap comes from its **command line** and is set before it reads the request (on Windows the Job is assigned while the process is suspended). A request over **16 MB** (pickled) is refused as a memory limit before any process starts. | a 20 MB request is refused with no process started, and 1 MB runs; Linux: the child's `RLIMIT_AS` is the requested cap; oversized `export` data is refused |
| H5 | medium | The G2 check assumed start-up takes over 0.05 s; it fails on fast Linux. | Fixed in `9223498` (a target whose imports are slow everywhere), and now **deterministic**: injected, measured set-up delays with fast and slow controls. | 6 set-up timing checks (see H3) |

## Round 5
- **Reviewer:** ChatGPT (Astra), posted on PR #18 on 2026-11-23.
- **Commit reviewed:** `562c961aa3524b6c17c7bbe581be41c5e4cfdc1e`.
- **Verdict:** FAIL.
  - Linux CI was green at this commit (run 45114596307: 339 scenes, 59/59 review checks).
  - Resolved: H1 (Windows fails closed), H3 (set-up deadline), H4, H5. H1 (Linux) and H2 were accepted as declared exclusions.
  - Two required findings (I1, I2) and one optional (O1).
- **Owner's decision:** the user approved the recommended shared fix, one cancellation state per request, on 2026-11-23, after an explanation of the review history.

| # | Severity | Finding | Fix | Tests (`test_limits_review.py`) |
|---|---|---|---|---|
| I1 | high | A launch that timed out kept running and could create the request's process after the limit was returned. | One **cancellation state** per request, shared by set-up and clean-up (`_Request`): `kill()` marks it cancelled under a lock. Set-up checks it before starting a process and records each process or owner through `_attach`, which kills everything at once if the request was cancelled meanwhile. After a cancel, `run_request` gives the set-up `CANCEL_WAIT` (2 s) to finish, so its process is gone before the result returns; a set-up that never completes still ends by the deadline + `GRACE` + `CANCEL_WAIT`. | your delayed launch: no process after the result; a process creation that finishes after the stop is killed before the result returns; a job (Windows) or guardian (Linux) set up after the stop: process killed before return; a fast control |
| I2 | medium | A caught Ctrl-C around `run_dir` left the in-flight requests running. | `run_many` keeps the set of active requests (`run_request(..., _registry=...)`). On Ctrl-C it cancels them all, kills their processes, waits for its threads, and only then passes the interrupt on; no callbacks run after the interrupt. | a caught Ctrl-C around `run_dir` with two running requests: no request process left |
| O1 | medium, optional | The 16 MB check pickled the whole input first, with no bound, in the parent. | A request carries **plain data only** (dicts, lists, strings, bytes, numbers, booleans, None). It is sized by a walk that copies nothing and stops past 16 MB or 2 million items; anything else is refused before pickling. A `MemoryError` while preparing it is a memory limit. | non-plain data refused; 20 MB of nested strings refused as a memory limit; 3 million items refused; plain data exports |

## Round 6
- **Reviewer:** ChatGPT (Astra), posted on PR #18 on 2026-11-23.
- **Commit reviewed:** `ddaa5fb59fe5c4376d59541af55a01237e60cd61`.
- **Verdict:** FAIL.
  - Linux CI was green at this commit (run 45117572593: 339 scenes, 68/68 review checks).
  - Three required findings: J1 and J2 continue I1 and I2; J3 is new. There were two optional hardening notes.
- **Scope decision (review policy, point 5):** J1 and J2 had the same cause as round 5. The user chose **option 1 on 2026-11-23**:
  - fix J2 and J3 properly;
  - **declare J1's case out of class:** an operating-system process-creation call that stalls past the deadline. The PLAN states it precisely.

| # | Severity | Finding | Fix | Tests (`test_limits_review.py`) |
|---|---|---|---|---|
| J1 | high | A process-creation call still in progress when the request is cancelled can create a process after the limit returns. | **Declared out of class.** Such a process is never sent the request (on Windows it is created suspended and never runs). It is killed the moment the creation call returns, because the request is already cancelled. Every other set-up step checks the cancellation first. | the declared case: a creation call returning 13 s after a 0.1 s limit gives a limit, and the late process is gone once creation returns |
| J2 | medium | A request still in its data check when Ctrl-C came was not yet registered, so it could start its process after `run_dir` returned. | One `_Registry` per `run_many`, with a lock and a stop state. A request **joins before any of its work**, its data check included; once stopped, nothing can join, and every request that joined is cancelled. `run_request` checks the cancellation again after the data check. | Ctrl-C while a request is blocked in its data check, then released: no process starts afterwards; a normal run as control |
| J3 | medium | The 16 MB check counted characters, not bytes (4.5 million emoji count as 4.5 MB but are 18 MB as sent). | **Exact bytes as sent:** the data is first validated as exactly the built-in plain types (no subclasses, at most 2 million items) without copying. It is then counted by a pickler that writes into a byte counter and stops as soon as the count passes 16 MB minus 256 bytes (the frame's other fields). A `MemoryError` during the check is a memory limit. | 4.5 million emoji refused with no process started; 16 000 000 ASCII characters run, and 16 800 000 are refused; repeated references count once (as sent); a `str` subclass refused; a `MemoryError` in the check gives a memory limit |
| (optional) | — | `isinstance` let subclasses with slow reducers through; a `MemoryError` in the check was not a limit. | Both fixed: exact type matching, and the `MemoryError` handler now covers the check. | as above |
