# Review 15a brief: milestone 15a, containment and reproducibility (stage 1: the build)

**Reviewer:** ChatGPT (Astra), reviewing the pull request on GitHub and posting its
findings there. Claude Code reads them from the PR and records them, with the action
taken on each, in `eval/review15a/REPORT.md`.

sim_waves is an engine for JEE wave problems (Python and SymPy, `engine/simwaves/`). Its
rule: **one correct answer or a clear error, never a silent wrong answer, and no invented
facts.**

This milestone changes **how scenes run, not what they compute**. Apply the
supported-class review policy in `CLAUDE.md`.

- **Background:** `eval/m15a_containment/PLAN.md` (plan, supported class, cost
  hypothesis), and issue #15 (finding 1 and the builder's reply, which lists the
  acceptance criteria).
- **The reserved scenes** (`eval/m15a_containment/reserved/`) test this milestone after
  the freeze. They are not in the branch; do not ask for them.

## What changed
| Change | Where |
|---|---|
| **Portable time budgets:** a watchdog thread raises a per-budget exception in the evaluating thread (`PyThreadState_SetAsyncExc`). It replaces `SIGALRM`, which Windows lacks. The exception derives from BaseException, so no `except Exception` on the way can swallow it. Its own `within` turns it into the caller's `Budget` (inner) or `ResourceLimitError` (whole request); a deadline that fires as fn returns is cleared. | `budget.py` (new); `scene.py` `_within` |
| **Inner budgets count memory too:** a `MemoryError` inside an inner budget is treated as that budget running out, so its numerical fallback runs once the attempt's memory is freed. | `budget.py` `within(memory=True)` |
| **`ResourceLimitError`** (BaseException, not a SceneError): reported as `RESOURCE LIMIT (time … / memory …)`, exit status 3, test status `LIMIT`. | `errors.py`; `__main__.py`; `harness.py` |
| **Whole-request containment:** `run`, `test` and `view` run in spawn-started worker processes. The parent enforces the time limit (budget, then a hard kill after a 10 s grace) and the memory limit. Windows uses a Job Object: per-process and job memory caps, kill-on-close, so the worker dies with the parent. Linux uses `RLIMIT_AS`, its own process group and `PR_SET_PDEATHSIG`. A worker is recycled after 20 requests or once its peak memory passes half its limit. | `contain.py` (new) |
| The per-solve `SIGALRM` limit in `_evaluate_once` is gone. Only the symbolic proof attempts (the `nearest` proof, the comparison proof) keep a 60 s cap, whose running out means "not proved". | `run.py` |
| `MemoryError` is re-raised ahead of every `except Exception` in the engine (19 handlers), so a memory limit is never turned into a refusal, a fallback or an "internal error". | `energy.py`, `expr.py`, `harness.py`, `run.py`, `scene.py` |
| **Test harness:** contained workers, at most `-j N` at once, output in file order. `expect: {limits: {time, memory}}` may lower a scene's limits, never raise them; `error: limit` expects a stop. The run lists the scenes stopped by a limit. | `harness.py` `run_dir`, `scene_limits`, `_outcome`; `contain.py` `run_many` |
| **CLI:** `--time S`, `--memory MB`; a warning when the installed SymPy is not the qualified 1.12. | `__main__.py` |
| **Pinned environment** and **Linux CI** on every pull request and on pushes to main: all suites, r84, r93 and r96 included, plus `test_limits.py`. | `engine/requirements.txt`, `requirements-dev.txt`, `.github/workflows/tests.yml` |
| **Test-only observables** (`test_spin`, `test_alloc`, `test_c_spin`), registered only when `SIMWAVES_TEST_HOOKS=1`. | `testhooks.py`; `run.py` (last lines) |

## What to hunt for (most important first)
1. **A limit presented as physics:** a `ResourceLimitError`, a `_Budget` or a `MemoryError` that ends up as a value, an "inconsistent", "undetermined" or "unsupported" result, or a fallback it was not meant to cause. Look at every broad handler, and at the inner-budget/outer-budget interplay in `budget.py`.
2. **A changed result:** any scene whose value differs from before m15a, apart from the numerical fallbacks Windows now shares with Linux. `eval/m15a_containment/engine_before/` is the engine before this milestone.
3. **Escapes:** a worker or a descendant that survives the parent, a Ctrl-C, a limit, or a recycle; more than N workers with `-j N`; a request with no limit (for example `view` or a path that bypasses `contain.py`).
4. **Races in `budget.py`:** an exception delivered after its `within` has returned, into unrelated code; nested budgets with the same or crossing deadlines; budgets on threads other than the main one.
5. **Platform differences:** Job Object flags and struct layout on 64-bit Windows; `RLIMIT_AS` against NumPy's or OpenBLAS's virtual reservations on Linux; macOS is untested.

Please give each finding a minimal reproduction and say whether you ran it or predicted it from the source.
