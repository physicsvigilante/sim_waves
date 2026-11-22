"""Test harness: compare engine results with the book answers in a scene's `expect` block.

`expect` is never read by the engine itself.
"""
import glob
import os
import traceback

import sympy as sp

from .errors import AmbiguousError, InconsistentError, SceneError, UndeterminedError
from .run import evaluate, load, show
from .scene import equivalent
from .units import split_quantity

ERRORS = {"inconsistent": InconsistentError, "ambiguous": AmbiguousError,
          "undetermined": UndeterminedError, "rejected": SceneError}


def _parse_expected(sc, value, conv=None):
    text, unit, factor, _ = split_quantity(value)
    v = sp.sympify(sc.expr(text)) * factor
    if conv is not None and unit is not None:
        v = (v - conv[1]) / conv[0]
    return v


def _tol(spec):
    if spec is None:
        return 1e-9
    s = str(spec).strip()
    return float(s[:-1]) / 100 if s.endswith("%") else float(s)


def check(sc, got, exp, conv=None):
    """Return (ok, detail). conv: (factor, offset) of an observable reported 'in <unit>': an
    expected value written with a unit is converted to that unit; a bare number is taken as
    already in it."""
    tol = None
    if isinstance(exp, dict):
        tol, exp = exp.get("tol"), exp.get("value")
    if isinstance(exp, bool):
        ok = isinstance(got, sp.logic.boolalg.BooleanAtom) and bool(got) == exp
        return ok, ""
    s = str(exp).strip()
    if s == "even integer":
        q = sp.simplify(got / 2)
        return bool(q.is_integer) or (q.is_number and abs(float(q) - round(float(q))) < 1e-9), ""
    if s.startswith("(") and s.endswith(")") and (s.count(",") or s == "()"):
        items = [i for i in s[1:-1].split(",") if i.strip()]
        if not isinstance(got, sp.Tuple) or len(got) != len(items):
            return False, f"want {s}"
        return all(check(sc, g, i, conv)[0] for g, i in zip(got, items)), f"want {s}"
    if s[:1] in "<>":
        target = _parse_expected(sc, s[1:], conv)
        d = sp.simplify(got - target)
        return bool(d.is_positive if s[0] == ">" else d.is_negative), ""
    want = _parse_expected(sc, s, conv)
    if isinstance(got, sp.logic.boolalg.BooleanAtom):
        return False, "got a truth value"
    if got.is_number and want.is_number:
        g, w = complex(sp.N(got)), complex(sp.N(want))
        return abs(g - w) <= _tol(tol) * max(1.0, abs(w)), f"want {sp.N(want, 6)}"
    return equivalent(got, want), f"want {want}"


def _run_file_local(path):
    """Check one scene's expect block in this process (a contained worker's step; the public,
    bounded form is run_file)."""
    lines, status = [], "PASS"
    name = os.path.basename(path)
    import yaml
    with open(path, encoding="utf-8") as fh:
        expect = dict((yaml.safe_load(fh) or {}).get("expect") or {})
    expect.pop("limits", None)              # read by the parent (run_dir), not a result
    if expect.get("error") == "limit":      # the parent judges a limit; here, just run it
        expect = {}
    if "error" in expect:
        kind = ERRORS[expect["error"]]
        try:
            sc_ = load(path)
            evaluate(sc_)
            for oname, oexc in getattr(sc_, "obs_errors", {}).items():
                if isinstance(oexc, kind):        # an observable refused for the expected reason
                    raise oexc
        except kind as exc:
            want = expect.get("message")
            if want and want not in str(exc):
                return "FAIL", [f"{name}: rejected, but not for the expected reason "
                                f"({want!r}): {type(exc).__name__}: {exc}"]
            return "PASS", [f"{name}: rejected as expected ({expect['error']}): {exc}"]
        except SceneError as exc:
            return "FAIL", [f"{name}: wrong rejection: {type(exc).__name__}: {exc}"]
        return "FAIL", [f"{name}: expected {expect['error']} but the scene ran"]
    try:
        sc = load(path)
    except SceneError as exc:
        return "ERROR", [f"{name}: scene rejected: {exc}"]
    try:
        sol, res = evaluate(sc)
    except SceneError as exc:
        return "FAIL", [f"{name}: {type(exc).__name__}: {exc}"]
    except MemoryError:                  # a memory limit is never swallowed (m15a)
        raise
    except Exception:  # engine bug
        return "CRASH", [f"{name}: engine crashed\n{traceback.format_exc()}"]
    if sol:
        lines.append(f"{name}: solved " + ", ".join(f"{k}={show(v)}" for k, v in sol.items()))
    ver = getattr(sc, "verification", [])
    if ver:
        kinds = {}
        for _, _, b in ver:
            kinds[b] = kinds.get(b, 0) + 1
        lines.append("  re-checked facts: " + ", ".join(f"{v} {k}" for k, v in sorted(kinds.items())))
    errs = getattr(sc, "obs_errors", {})
    for key, exp in expect.items():
        if key in errs:
            lines.append(f"  {key}: NOT AVAILABLE ({type(errs[key]).__name__}: {errs[key]})")
            status = "FAIL"
            continue
        if key not in res:
            lines.append(f"  {key}: no such observable")
            status = "FAIL"
            continue
        try:
            ok, detail = check(sc, res[key], exp, getattr(sc, "unit_conv", {}).get(key))
        except SceneError as exc:
            ok, detail = False, f"(expected value unreadable: {exc})"
        disputed = isinstance(exp, dict) and exp.get("status") == "disputed"
        tag = "ok" if ok else "MISMATCH"
        if disputed:
            tag += f" (book disputed: {exp.get('book')}, {exp.get('why')})"
        if not ok:
            status = "FAIL"
        basis = getattr(sc, "basis", {}).get(key, "exact")
        btag = "" if basis == "exact" else f" <{basis}>"
        lines.append(f"  {key} = {show(res[key])}{btag}  [{tag}] {detail if not ok else ''}".rstrip())
    return status, lines


def timed_run(f):
    """One scene's check with its duration (what a contained worker runs for each scene)."""
    import time
    t0 = time.time()
    status, lines = _run_file_local(f)
    return status, lines, time.time() - t0


def scene_limits(path, seconds, memory_mb):
    """The limits for one scene: the run's, lowered (never raised) by its expect block's
    `limits: {time: s, memory: MB}`. Returns (seconds, memory_mb, error or None, whether the
    scene expects to be stopped by a limit (`error: limit`)). The file's size is checked
    before it is parsed, so the parent never parses an unbounded document."""
    import yaml
    from .contain import LimitError, check_limits, check_scene_size
    try:
        seconds, memory_mb = check_limits(seconds, memory_mb)
        check_scene_size(path)
    except (LimitError, OSError) as exc:
        return seconds, memory_mb, str(exc), False
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except MemoryError:                  # a memory limit is never swallowed (m15a)
        raise
    except Exception:                                   # noqa: BLE001 - the worker reports it
        return seconds, memory_mb, None, False
    expect = data.get("expect") if isinstance(data, dict) else None
    expect = expect if isinstance(expect, dict) else {}
    lim = expect.get("limits", {})
    if lim is None:
        lim = {}
    if not isinstance(lim, dict) or set(lim) - {"time", "memory"}:
        return (seconds, memory_mb, f"expect.limits must be a mapping with only time: and memory:, not {lim!r}",
                False)
    try:
        t, m = check_limits(lim.get("time", seconds), lim.get("memory", memory_mb), seconds, memory_mb)
    except LimitError as exc:
        return seconds, memory_mb, f"expect.limits: {exc}", False
    return t, m, None, expect.get("error") == "limit"


def _outcome(name, result, expects_limit):
    """(status, lines) from a contained result."""
    from .contain import CrashResult, LimitResult
    if isinstance(result, LimitResult):
        if expects_limit:
            return "PASS", [f"{name}: stopped by a limit as expected: {result.message}"]
        return "LIMIT", [f"{name}: {result.message} (the scene was stopped; this says nothing about the "
                         f"physics)"]
    if isinstance(result, CrashResult) or not isinstance(result, tuple):
        return "CRASH", [f"{name}: {getattr(result, 'message', result)}"]
    status, lines, _ = result
    if expects_limit:
        return "FAIL", [f"{name}: expected to be stopped by a limit, but it finished ({status})"] + lines[1:]
    return status, lines


def run_file(path, seconds=None, memory_mb=None):
    """Check one scene's expect block, bounded: in a contained worker, under the run's limits
    lowered by the scene's own `expect.limits`, and honouring `error: limit`. Returns
    (status, lines), status one of PASS, FAIL, ERROR, CRASH, LIMIT."""
    from . import contain
    name = os.path.basename(path)
    t, m, err, expects_limit = scene_limits(path, seconds or contain.DEFAULT_TIME,
                                            memory_mb or contain.DEFAULT_MEMORY)
    if err:
        return "ERROR", [f"{name}: {err}"]
    if contain.IN_WORKER:                 # already contained: under this worker's budget
        from .budget import within
        from .errors import ResourceLimitError
        try:
            result = within(t, lambda: timed_run(path), public=ResourceLimitError("time", f"{t:g} s"))
        except ResourceLimitError as exc:
            result = contain.LimitResult(exc.kind, str(exc))
    else:
        result = contain.run_contained("simwaves.harness:timed_run", (path,), t, m)
    return _outcome(name, result, expects_limit)


def run_dir(path, jobs=None, seconds=None, memory_mb=None):
    """Run every scene's expect block, each in a contained worker process under the time
    and memory limits (contain.py), at most `jobs` at once (default: the number of CPUs).
    A scene stopped by a limit is LIMIT, unless its expect block says `error: limit`.
    Every scene gets exactly one status. Output keeps file order. Returns the counts per
    status; the CLI succeeds only if every scene of a non-empty folder passed."""
    import time
    from .contain import (DEFAULT_MEMORY, DEFAULT_TIME, CrashResult, LimitError, check_limits, run_contained,
                          run_many)
    try:
        seconds, memory_mb = check_limits(seconds or DEFAULT_TIME, memory_mb or DEFAULT_MEMORY)
    except LimitError as exc:
        print(f"ERROR: {exc}")
        return {"ERROR": 1}
    files = sorted(glob.glob(os.path.join(path, "*.yaml")))
    if not files:
        print(f"ERROR: no scenes (*.yaml) in {path}")
        return {"ERROR": 1}
    jobs = jobs or os.cpu_count() or 1
    counts, times = {}, []
    plan = {f: scene_limits(f, seconds, memory_mb) for f in files}
    shared = [f for f in files if plan[f][1] == memory_mb and plan[f][2] is None]
    own = [f for f in files if f not in shared]
    done, printed = {}, [0]
    started = {}

    def emit():
        while printed[0] < len(files) and files[printed[0]] in done:
            f = files[printed[0]]
            status, lines, dt = done[f]
            counts[status] = counts.get(status, 0) + 1
            times.append((dt, os.path.basename(f)))
            print(f"[{status}] " + "\n".join(lines), flush=True)
            printed[0] += 1

    def record(f, result):
        name = os.path.basename(f)
        t, m, err, expects_limit = plan[f]
        if err:
            done[f] = ("ERROR", [f"{name}: {err}"], 0.0)
        else:
            status, lines = _outcome(name, result, expects_limit)
            dt = result[2] if isinstance(result, tuple) else time.time() - started.get(f, time.time())
            done[f] = (status, lines, dt)

    for f in own:                         # its own limits (or an error in them): its own worker
        t, m, err, _ = plan[f]
        started[f] = time.time()
        try:
            r = None if err else run_contained("simwaves.harness:timed_run", (f,), t, m)
        except BaseException as exc:      # noqa: BLE001 - every scene gets a status
            r = CrashResult(f"the test runner failed on this scene ({type(exc).__name__}: {exc})")
        record(f, r)
    emit()

    def on_result(i, f, result):
        record(f, result)
        emit()

    def seconds_of(f):
        started[f] = time.time()
        return plan[f][0]
    if shared:
        run_many("simwaves.harness:timed_run", shared, jobs, seconds_of, memory_mb, on_result)
    for f in files:                       # accounting: no scene may end without a status
        if f not in done:
            done[f] = ("CRASH", [f"{os.path.basename(f)}: no result was recorded for this scene"], 0.0)
    emit()
    if sum(counts.values()) != len(files):
        counts["CRASH"] = counts.get("CRASH", 0) + len(files) - sum(counts.values())
    slow = sorted(times, reverse=True)[:5]
    print("\nslowest: " + ", ".join(f"{n} {dt:.1f}s" for dt, n in slow))
    print("summary: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    limited = sorted(os.path.basename(f) for f in files if done[f][0] == "LIMIT")
    if limited:
        print("stopped by a limit: " + ", ".join(limited))
    return counts
