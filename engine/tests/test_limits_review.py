"""Review 15a regressions (rounds 1-3: R1-R6, O1, F1-F5, G1-G6). Run from engine/:
    python tests/test_limits_review.py
Needs psutil (requirements-dev.txt). Uses the test-only hooks (SIMWAVES_TEST_HOOKS=1).
Expected outcomes are the containment contract, not engine output: a limit is a limit and
outranks everything after the deadline, every scene gets one status, limits are validated,
the request's deadline starts at admission, and no process outlives its request.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import weakref

import psutil

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.environ["SIMWAVES_TEST_HOOKS"] = "1"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", SIMWAVES_TEST_HOOKS="1")

passed = failed = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"PASS {name}")
    else:
        failed += 1
        print(f"FAIL {name} {detail}"[:600])


def alive(pid):
    try:
        p = psutil.Process(pid)
        return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def pids_from(marker, wait=60):
    for _ in range(wait * 4):
        if os.path.exists(marker) and os.path.getsize(marker) > 0:
            try:
                return json.load(open(marker))
            except ValueError:
                pass
        time.sleep(0.25)
    return None


def kill_quietly(pid):
    try:
        psutil.Process(pid).kill()
    except psutil.NoSuchProcess:
        pass


def write(d, name, text):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def child_pid(result):
    """The pid the request's process noted first (on a LimitResult or CrashResult)."""
    for n in getattr(result, "notes", []):
        if isinstance(n, tuple) and n and n[0] == "pid":
            return n[1]
    return None


def cli(*args, timeout=300):
    return subprocess.run([sys.executable, "-m", "simwaves", *args], cwd=HERE, env=ENV, capture_output=True,
                          text=True, encoding="utf-8", timeout=timeout)


EARLY_PARENT = """import json, os, subprocess, sys, time
sys.path.insert(0, {here!r})
from simwaves import contain
orig = subprocess.Popen
class Rec(orig):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        if 'simwaves.child' in a[0]:
            json.dump({{'child': self.pid}}, open({marker!r}, 'w'))
contain.subprocess.Popen = Rec
if contain.WINDOWS:
    contain._ensure_supervisor()                    # the parent's own job, joined normally
    contain._Job.assign_handle = lambda self, h: time.sleep(600)
else:
    contain._Guardian.__init__ = lambda self, pgid: time.sleep(600)
if __name__ == '__main__':
    contain.run_request('os:getpid', (), 600)
"""

PARENT = """import sys
sys.path.insert(0, {here!r})
from simwaves.contain import run_request
if __name__ == '__main__':
    run_request({target!r}, {args}, 120)
"""

SLOW_IMPORT = """import json, os, time
json.dump({{'worker': os.getpid(), 'descendant': os.getpid()}}, open({marker!r}, 'w'))
time.sleep(120)
def f(*a):
    return 1
"""


if __name__ == "__main__":
    from simwaves import contain
    from simwaves.budget import Budget, within
    from simwaves.contain import (GRACE, CrashResult, LimitError, LimitResult, check_limits, run_many,
                                  run_request)
    from simwaves.errors import ResourceLimitError
    from simwaves.export import export
    from simwaves.harness import run_dir, run_file
    import simwaves.testhooks as hooks

    # ---- R1: an earlier deadline is never replaced by an inner fallback
    ok = 0
    for _ in range(5):
        try:
            within(0.05, hooks.nested_budget, public=ResourceLimitError("time", "0.05 s"))
        except ResourceLimitError:
            ok += 1
    check("R1 outer deadline wins over the inner fallback (5 trials)", ok == 5, f"{ok}/5")
    check("R1 control: inner-only expiry takes its fallback", within(5, hooks.nested_budget) == "normal fallback value")
    r = run_request("simwaves.testhooks:nested_budget_at_edge", (), 5)
    check("R1 in a request: the request's limit, not the inner fallback", isinstance(r, LimitResult), repr(r))
    res = []

    def on_thread():
        try:
            within(0.1, lambda: time.sleep(0.3))
            res.append("value")
        except Budget:
            res.append("budget")
    t = threading.Thread(target=on_thread)
    t.start()
    t.join()
    check("R1 a budget on another thread", res == ["budget"], str(res))

    # ---- O1: the memory fallback runs with the failed attempt released
    class Payload:
        pass
    ref = [None]

    def attempt():
        p = Payload()
        ref[0] = weakref.ref(p)
        raise MemoryError
    try:
        within(5, attempt, memory=True)
    except Budget as b:
        check("O1 attempt released inside the fallback", ref[0]() is None and b.__context__ is None)

    # ---- F3, G4: an expiry at any line of within() is classified, and once the deadline has
    #      passed the limit outranks a late ordinary error as well as a late value
    from simwaves import budget
    codes = [budget.within.__code__] + [c for c in budget.within.__code__.co_consts if hasattr(c, "co_lines")]
    problems = []
    for code in codes:
        for target in sorted({ln for _, _, ln in code.co_lines() if ln}):
            for kind in ("value", "error"):
                st = {"used": False}

                def tr(frame, event, arg, code=code, target=target, st=st):
                    if frame.f_code is code and event == "line" and frame.f_lineno == target and not st["used"]:
                        st["used"] = True
                        time.sleep(0.10)
                    return tr

                def fn(kind=kind):
                    if kind == "error":
                        raise ValueError("ordinary")
                    return 17
                sys.settrace(tr)
                try:
                    v = budget.within(0.025, fn, public=ResourceLimitError("time", ".025 s"))
                    out = f"value {v}"
                except ResourceLimitError:
                    out = "limit"
                except ValueError:
                    out = "ValueError"
                except BaseException as exc:              # noqa: BLE001
                    out = type(exc).__name__
                finally:
                    sys.settrace(None)
                time.sleep(0.03)
                allowed = ("limit", "value 17") if kind == "value" else ("limit", "ValueError")
                if out not in allowed or budget._active or budget._critical:
                    problems.append((code.co_name, target, kind, out))
                    budget._active.clear()
                    budget._critical.clear()
    check("F3/G4 expiry at every line of within(), for a value and an error: classified, nothing left",
          not problems, str(problems[:6]))
    late = []
    for kind in ("value", "error"):
        def fn(kind=kind):
            time.sleep(0.1)                               # finishes or fails only after the deadline
            if kind == "error":
                raise ValueError("ordinary")
            return 17
        try:
            budget.within(0.025, fn, public=ResourceLimitError("time", ".025 s"))
            late.append("value")
        except ResourceLimitError:
            late.append("limit")
        except ValueError:
            late.append("ValueError")
    check("G4 after the deadline, a late value and a late error are both the limit", late == ["limit", "limit"],
          str(late))
    r = run_request("simwaves.testhooks:slow_then_raise", (), 3)
    check("G4 in a request: an ordinary error after the deadline is a limit", isinstance(r, LimitResult), repr(r))

    # ---- R3, F5: limits are validated; only None selects a default
    for label, (t_, m_) in {"neg memory": (120, -1), "zero memory": (120, 0), "bool time": (True, 512),
                            "nan time": (float("nan"), 512), "inf time": (float("inf"), 512), "neg time": (-5, 512),
                            "fractional memory": (120, 300.5), "text": ("fast", 512),
                            "below the start-up minimum": (120, 100)}.items():
        try:
            check_limits(t_, m_)
            check(f"R3 refused: {label}", False)
        except LimitError:
            check(f"R3 refused: {label}", True)
    check("R3 control: valid limits", check_limits(5, 512.0) == (5.0, 512))

    with tempfile.TemporaryDirectory() as d:
        p = write(d, "ordinary.yaml", "observe: {v: '1'}\nexpect: {v: 1}\n")
        for label, kw in {"seconds=0": {"seconds": 0}, "seconds=False": {"seconds": False},
                          "memory_mb=0": {"memory_mb": 0}, "memory_mb=False": {"memory_mb": False}}.items():
            status, lines = run_file(p, **kw)
            check(f"F5 run_file({label}) refused", status == "ERROR", f"{status} {lines}")
        status, _ = run_file(p)
        check("F5 control: run_file with None uses the defaults", status == "PASS", status)
        check("F5 run_dir(seconds=0) refused", run_dir(d, 1, 0) == {"ERROR": 1})
        check("F5 run_dir(seconds=False) refused", run_dir(d, 1, False) == {"ERROR": 1})
        try:
            export({"observe": {"v": "1"}}, seconds=0)
            check("F5 export(seconds=0) refused", False)
        except LimitError:
            check("F5 export(seconds=0) refused", True)

        # ---- R4, F1, G6: no parsing in the parent; one budget for a scene's whole check
        big = write(d, "big.yaml", "assume: ['" + "x" * 4_000_000 + "']\nobserve: {v: '1'}\nexpect: {v: 1}\n")
        status, lines = run_file(big)
        check("R4 oversized scene refused", status == "ERROR" and "limited to" in lines[0], f"{status} {lines}")
        bomb = os.path.join(d, "bomb")
        os.mkdir(bomb)
        a = "&a0 {v: 1}"
        for i in range(1, 24):
            a = f"&a{i} {{<<: [{a}, *a{i - 1}]}}"
        alias = write(bomb, "alias.yaml", 'observe: {v: "1"}\nexpect: ' + a + "\n")
        write(bomb, "plain.yaml", 'observe: {v: "1"}\nexpect: {v: 1}\n')
        t0 = time.monotonic()
        counts = run_dir(bomb, 1, 4, 512)
        dt = time.monotonic() - t0
        check("F1 an alias-expanding scene is stopped by the run's limit; its neighbour passes",
              counts == {"LIMIT": 1, "PASS": 1} and dt < 2 * (4 + GRACE) + 10, f"{counts} in {dt:.1f} s")
        import simwaves.harness as hmod
        check("F1 no per-scene limits reader in the parent", not hasattr(hmod, "scene_limits"))
        t0 = time.monotonic()
        status, lines = run_file(alias, seconds=4, memory_mb=512)
        dt = time.monotonic() - t0
        check("G6 run_file: reading and running share one budget", status == "LIMIT" and dt < 4 + GRACE + 5,
              f"{status} in {dt:.1f} s")

        # ---- R2: every scene gets exactly one status; no result is never success
        one = os.path.join(d, "one")
        os.mkdir(one)
        write(one, "a.yaml", "observe: {v: '1'}\nexpect: {v: 1}\n")
        write(one, "b.yaml", "observe: {v: '1'}\nexpect: {limits: {time: 5}, v: 1}\n")
        r = cli("test", one, "-j", "1")
        check("R2 a scene's own limits give an ERROR and a non-zero exit",
              r.returncode != 0 and "ERROR 1" in r.stdout and "PASS 1" in r.stdout, r.stdout[-400:])
        empty = os.path.join(d, "empty")
        os.mkdir(empty)
        check("R2 an empty folder is not a success", cli("test", empty).returncode != 0)

    orig_launch = contain._Request.launch
    contain._Request.launch = lambda self: (_ for _ in ()).throw(OSError("injected start-up failure"))
    out = run_many("simwaves.testhooks:report_pid", list(range(3)), 2, 30)
    contain._Request.launch = orig_launch
    check("R2 start-up failure: one CrashResult per item", len(out) == 3 and all(isinstance(x, CrashResult)
                                                                                 for x in out), repr(out))
    calls = [0]
    orig_run = contain.run_request

    def flaky(*a, **k):
        calls[0] += 1
        if calls[0] == 3:
            raise RuntimeError("injected runner failure")
        return orig_run(*a, **k)
    contain.run_request = flaky
    out = run_many("simwaves.testhooks:report_pid", list(range(5)), 1, 30)
    contain.run_request = orig_run
    kinds = [type(x).__name__ for x in out]
    check("R2 partial completion then a failure: all 5 accounted for",
          len(out) == 5 and kinds.count("CrashResult") == 1 and kinds.count("tuple") == 4, str(kinds))

    # ---- R5: the public entry points are bounded
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "direct.yaml", "observe: {v: 'test_spin(30)'}\nexpect: {error: limit}\n")
        status, lines = run_file(p, seconds=5)
        check("R5 run_file enforces its limit and error: limit", status == "PASS" and "stopped by a limit" in lines[0],
              f"{status} {lines}")
        p = write(d, "direct2.yaml", "observe: {v: 'test_spin(30)'}\nexpect: {v: 0}\n")
        status, _ = run_file(p, seconds=5)
        check("R5 run_file reports an unexpected limit as LIMIT", status == "LIMIT", status)
    try:
        export({"observe": {"v": "test_spin(30)"}}, seconds=5)
        check("R5 export is bounded", False, "returned")
    except ResourceLimitError:
        check("R5 export is bounded", True)
    from simwaves.run import evaluate
    from simwaves.scene import Scene
    try:
        evaluate(Scene({"observe": {"v": "test_spin(5)"}}), timeout=0.5)
        check("R5 evaluate honours its timeout", False, "returned")
    except ResourceLimitError:
        check("R5 evaluate honours its timeout", True)

    # ---- G2, H5, H3: the deadline starts at admission and covers process set-up; checked with
    #      injected, measured set-up delays (deterministic on any machine)
    orig_launch = contain._Request.launch

    def timed(seconds, launch=None):
        if launch is not None:
            contain._Request.launch = launch
        t0 = time.monotonic()
        try:
            r = run_request("os:getpid", (), seconds)
        except BaseException as exc:                      # noqa: BLE001
            r = exc
        finally:
            contain._Request.launch = orig_launch
        return r, time.monotonic() - t0

    def slow_ok(self):
        time.sleep(0.5)
        return orig_launch(self)

    def slow_fail(self):
        time.sleep(0.5)
        raise OSError("injected delayed set-up failure")

    def fast_fail(self):
        raise OSError("injected set-up failure")

    def never(self):
        time.sleep(3600)
    r, dt = timed(30)
    check("H5 control: a fast request with time to spare gives its value", isinstance(r, int), f"{r!r} {dt:.2f} s")
    r, dt = timed(0.3, slow_ok)
    check("G2/H5 a set-up slower than the limit (0.5 s against 0.3 s) is a limit", isinstance(r, LimitResult),
          f"{r!r} {dt:.2f} s")
    r, dt = timed(30, slow_ok)
    check("H5 control: the same slow set-up within its limit gives its value", isinstance(r, int), f"{r!r} {dt:.2f} s")
    r, dt = timed(0.3, slow_fail)
    check("H3 a set-up failing after the deadline is a limit, not a crash", isinstance(r, LimitResult),
          f"{r!r} {dt:.2f} s")
    r, dt = timed(30, fast_fail)
    check("H3 control: a set-up failing within the deadline is a crash", isinstance(r, CrashResult), f"{r!r}")
    r, dt = timed(1, never)
    check("H3 a set-up that never completes ends at the hard stop", isinstance(r, LimitResult) and
          dt < 1 + GRACE + contain.CANCEL_WAIT + 3,
          f"{r!r} {dt:.1f} s")

    # ---- H4: the request's size is bounded before any process starts; the memory cap comes first
    launched = []
    contain._Request.launch = lambda self: (launched.append(1), orig_launch(self))[1]
    r = run_request("builtins:len", (b"x" * (20 * 1024 * 1024),), 30, 256)
    contain._Request.launch = orig_launch
    check("H4 a 20 MB request is refused as a memory limit before any process starts",
          isinstance(r, LimitResult) and r.kind == "memory" and not launched, f"{r!r} launched={bool(launched)}")
    r = run_request("builtins:len", (b"x" * (1024 * 1024),), 30, 256)
    check("H4 control: a 1 MB request runs", r == 1024 * 1024, repr(r))
    if not contain.WINDOWS:
        r = run_request("resource:getrlimit", (9,), 30, 300)          # RLIMIT_AS
        check("H4 the child's memory cap is in place (Linux)", tuple(r) == (300 * 1024 * 1024,) * 2, repr(r))
    try:
        export({"id": "x" * (20 * 1024 * 1024), "observe": {"v": "1"}}, memory_mb=256)
        check("H4 export of oversized data is refused", False, "returned")
    except ResourceLimitError:
        check("H4 export of oversized data is refused", True)

    # ---- H1 (Windows): no request process without the supervisor job
    if contain.WINDOWS:
        spawned = []
        orig_sup = contain._ensure_supervisor
        orig_popen2 = subprocess.Popen

        class Rec2(orig_popen2):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                spawned.append(self.pid)
        contain._ensure_supervisor = lambda: False
        contain.subprocess.Popen = Rec2
        r = run_request("os:getpid", (), 30)
        contain._ensure_supervisor = orig_sup
        contain.subprocess.Popen = orig_popen2
        check("H1 Windows refuses to start a request process without the supervisor job",
              isinstance(r, CrashResult) and not spawned and "refused" in r.message, f"{r!r} {spawned}")

    # ---- G1, F2: a reply complete only after the deadline is a limit, and the process is gone
    r = run_request("simwaves.testhooks:late_big", (64 * 1024 * 1024,), 3)
    pid = child_pid(r)
    check("G1/F2 a late complete reply is a limit, and its process is gone at once",
          isinstance(r, LimitResult) and pid is not None and not alive(pid), f"{r!r} pid {pid}")
    t0 = time.monotonic()
    r = run_request("simwaves.testhooks:stall_reply", (), 2)
    dt = time.monotonic() - t0
    pid = child_pid(r)
    check("F2 a reply stalled part-way ends at the hard stop, process gone",
          isinstance(r, LimitResult) and dt < 2 + GRACE + 10 and pid is not None and not alive(pid),
          f"{r!r} {dt:.1f} s pid {pid}")

    # ---- G3: view never multiplies the limit
    with tempfile.TemporaryDirectory() as d:
        slow = write(d, "slow.yaml", "observe: {v: 'test_spin(8)'}\n")
        plain = write(d, "plain.yaml", "observe: {v: '1'}\n")
        page = os.path.join(d, "out.html")
        r = cli("view", page, slow, plain, "--time", "4", "--memory", "512")
        check("G3 view: a slow scene is stopped by the limit, and no page is written",
              r.returncode == 3 and "RESOURCE LIMIT (time 4 s)" in r.stdout and not os.path.exists(page),
              r.stdout[-300:])
        r = cli("view", page, plain, plain, "--time", "30", "--memory", "512")
        check("G3 control: two ordinary scenes give a page", r.returncode == 0 and os.path.exists(page),
              r.stdout[-300:])

    # ---- G5: ownership from creation; a failed set-up leaves no process
    pids = []
    orig_popen = subprocess.Popen

    class Recording(orig_popen):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            pids.append(self.pid)
    contain.subprocess.Popen = Recording
    if contain.WINDOWS:
        contain._ensure_supervisor()
        orig_assign = contain._Job.assign_handle
        contain._Job.assign_handle = lambda self, h: (_ for _ in ()).throw(OSError("injected job failure"))
    else:
        orig_guard = contain._Guardian.__init__
        contain._Guardian.__init__ = lambda self, pgid: (_ for _ in ()).throw(OSError("injected guardian failure"))
    r = run_request("os:getpid", (), 30)
    if contain.WINDOWS:
        contain._Job.assign_handle = orig_assign
    else:
        contain._Guardian.__init__ = orig_guard
    contain.subprocess.Popen = orig_popen
    time.sleep(1)
    check("G5 a failed ownership set-up: a CrashResult and no process left",
          isinstance(r, CrashResult) and pids and not any(alive(p) for p in pids), f"{r!r} {pids}")

    with tempfile.TemporaryDirectory() as d:
        # the parent dies right after creating the process, before the child's own job
        # (Windows) or guardian (Linux) exists: the supervisor job / parent-death signal own it
        marker = os.path.join(d, "early.json")
        script = write(d, "early_parent.py", EARLY_PARENT.format(here=HERE, marker=marker))
        caller = subprocess.Popen([sys.executable, script], cwd=HERE, env=ENV)
        got = pids_from(marker, 60) or {}
        time.sleep(1)
        caller.kill()
        caller.wait(10)
        time.sleep(3)
        check("G5 parent killed before the child's own job/guardian: child gone",
              got and not alive(got["child"]), str(got))
        for pid in got.values():
            kill_quietly(pid)

    # ---- I1: a request cancelled during set-up cannot leave a process behind
    def child_procs():
        out = []
        for pr in psutil.Process().children(recursive=True):
            try:
                if "simwaves.child" in " ".join(pr.cmdline()):
                    out.append(pr.pid)
            except psutil.Error:
                pass
        return out

    made = []
    orig_popen3 = subprocess.Popen

    class Rec3(orig_popen3):
        delay = 0.0

        def __init__(self, *a, **k):
            if "simwaves.child" in " ".join(a[0]) and Rec3.delay:
                time.sleep(Rec3.delay)
            super().__init__(*a, **k)
            made.append(self.pid)
    contain.subprocess.Popen = Rec3
    orig_launch = contain._Request.launch

    def delayed_launch(self):
        time.sleep(GRACE + 0.6)
        return orig_launch(self)
    contain._Request.launch = delayed_launch
    made.clear()
    r = run_request("os:getpid", (), 0.1, 512)
    contain._Request.launch = orig_launch
    time.sleep(1.2)
    check("I1 a launch delayed past the hard stop starts no process after the result",
          isinstance(r, LimitResult) and not any(alive(p) for p in made) and not child_procs(), f"{r!r} {made}")
    made.clear()
    Rec3.delay = GRACE + 0.6                              # process creation itself finishes after the stop
    r = run_request("os:getpid", (), 0.1, 512)
    Rec3.delay = 0.0
    check("I1 a process created after the stop is killed before the result returns",
          isinstance(r, LimitResult) and made and not any(alive(p) for p in made), f"{r!r} {made}")
    made.clear()
    if contain.WINDOWS:
        contain._ensure_supervisor()
        orig_job_init = contain._Job.__init__

        def slow_job(self, memory_mb=None):
            time.sleep(GRACE + 0.6)
            orig_job_init(self, memory_mb)
        contain._Job.__init__ = slow_job
        r = run_request("os:getpid", (), 0.1, 512)
        contain._Job.__init__ = orig_job_init
        what = "job"
    else:
        orig_guard_init = contain._Guardian.__init__

        def slow_guard(self, pgid):
            time.sleep(GRACE + 0.6)
            orig_guard_init(self, pgid)
        contain._Guardian.__init__ = slow_guard
        r = run_request("os:getpid", (), 0.1, 512)
        contain._Guardian.__init__ = orig_guard_init
        what = "guardian"
    time.sleep(1)
    check(f"I1 a {what} set up after the stop: the process is killed before the result returns",
          isinstance(r, LimitResult) and made and not any(alive(p) for p in made), f"{r!r} {made}")
    contain.subprocess.Popen = orig_popen3
    r = run_request("os:getpid", (), 30)
    check("I1 control: a normal request with time to set up", isinstance(r, int), repr(r))

    # ---- I2: a Ctrl-C caught around run_dir leaves no request running
    import _thread
    with tempfile.TemporaryDirectory() as d:
        for n in ("a", "b"):
            write(d, f"{n}.yaml", "observe: {v: 'test_spin(30)'}\nexpect: {error: limit}\n")
        fired = []

        def interrupter():
            for _ in range(200):
                if child_procs():
                    time.sleep(0.5)
                    fired.append(True)
                    _thread.interrupt_main()
                    return
                time.sleep(0.1)
        threading.Thread(target=interrupter, daemon=True).start()
        caught = False
        try:
            run_dir(d, 2, 30, 512)
        except KeyboardInterrupt:
            caught = True
        left = child_procs()
        check("I2 Ctrl-C caught around run_dir: no request process left running",
              fired and caught and not left, f"fired={bool(fired)} caught={caught} left={left}")

    # ---- O1: a request carries plain data only, bounded before it is copied
    try:
        export({"observe": {"v": "1"}, "extra": object()})
        check("O1 non-plain data refused", False, "returned")
    except RuntimeError as exc:
        check("O1 non-plain data refused", "plain data" in str(exc), str(exc))
    try:
        export({"observe": {"v": "1"}, "notes": [("y" * (1024 * 1024)) + str(i) for i in range(20)]},
               memory_mb=256)
        check("O1 oversized nested data refused as a memory limit", False, "returned")
    except ResourceLimitError as exc:
        check("O1 oversized nested data refused as a memory limit", exc.kind == "memory", str(exc))
    r = run_request("builtins:len", ([0] * 3_000_000,), 30)
    check("O1 data with too many items refused", isinstance(r, LimitResult) and r.kind == "memory", repr(r))
    out = export({"observe": {"v": "1"}})
    check("O1 control: plain data exports", isinstance(out, dict), type(out).__name__)

    # ---- J3: the 16 MB ceiling is in bytes as sent, checked before any process starts
    launched = []
    orig_launch_j = contain._Request.launch
    contain._Request.launch = lambda self: (launched.append(1), orig_launch_j(self))[1]
    r = run_request("builtins:len", ("\U0001F600" * 4_500_000,), 30, 512)
    check("J3 4.5 million emoji (18 MB as sent) refused before any process starts",
          isinstance(r, LimitResult) and r.kind == "memory" and not launched, f"{r!r} launched={bool(launched)}")
    launched.clear()
    r = run_request("builtins:len", ("a" * 16_000_000,), 60, 512)
    check("J3 control: 16 000 000 ASCII characters (under 16 MB as sent) run", r == 16_000_000 and launched, repr(r))
    launched.clear()
    r = run_request("builtins:len", ("a" * 16_800_000,), 60, 512)
    check("J3 16 800 000 ASCII characters (over 16 MB as sent) refused", isinstance(r, LimitResult) and not launched,
          repr(r))
    launched.clear()
    shared = "y" * (1024 * 1024)
    r = run_request("builtins:len", ([shared] * 20,), 60, 512)
    check("J3 repeated references to one string count once, as sent", r == 20 and launched, repr(r))
    contain._Request.launch = orig_launch_j

    class MyStr(str):
        pass
    r = run_request("builtins:len", (MyStr("abc"),), 30)
    check("J3 a str subclass is not plain data", isinstance(r, CrashResult) and "plain data" in r.message, repr(r))
    orig_rb = contain._request_bytes
    contain._request_bytes = lambda obj, limit: (_ for _ in ()).throw(MemoryError())
    r = run_request("os:getpid", (), 30)
    contain._request_bytes = orig_rb
    check("J3 running out of memory while checking the data is a memory limit",
          isinstance(r, LimitResult) and r.kind == "memory", repr(r))

    # ---- J2: Ctrl-C while a request is still in its data check: no process starts afterwards
    import _thread
    with tempfile.TemporaryDirectory() as d:
        write(d, "a.yaml", "observe: {v: 'test_spin(120)'}\nexpect: {error: limit}\n")
        entered, release = threading.Event(), threading.Event()
        orig_rb2 = contain._request_bytes

        def blocking(obj, limit):
            entered.set()
            release.wait(120)
            return orig_rb2(obj, limit)
        contain._request_bytes = blocking

        def interrupter():
            if entered.wait(60):
                _thread.interrupt_main()
        threading.Thread(target=interrupter, daemon=True).start()
        caught = False
        try:
            run_dir(d, 1, 60, 512)
        except KeyboardInterrupt:
            caught = True
        release.set()                                    # let the blocked data check continue
        time.sleep(3)
        contain._request_bytes = orig_rb2
        left = child_procs()
        check("J2 Ctrl-C during a request's data check: no process starts afterwards", caught and not left,
              f"caught={caught} left={left}")
    with tempfile.TemporaryDirectory() as d:
        write(d, "a.yaml", "observe: {v: '1'}\nexpect: {v: 1}\n")
        check("J2 control: a normal run_dir completes", run_dir(d, 1, 60, 512) == {"PASS": 1})

    # ---- J1 (declared out of class): a process whose creation returns after the stop never gets
    #      the request and is killed as soon as creation returns
    sent = []
    orig_popen4 = subprocess.Popen

    class LateReturn(orig_popen4):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            if "simwaves.child" in " ".join(a[0]):
                sent.append(self.pid)
                time.sleep(GRACE + contain.CANCEL_WAIT + 1)
    contain.subprocess.Popen = LateReturn
    t0 = time.monotonic()
    r = run_request("simwaves.testhooks:report_pid", (None,), 0.1, 512)
    contain.subprocess.Popen = orig_popen4
    time.sleep(GRACE + contain.CANCEL_WAIT + 3)          # until creation has returned, plus margin
    check("J1 declared case: a limit is returned, and the late process is killed once creation returns",
          isinstance(r, LimitResult) and sent and not any(alive(p) for p in sent), f"{r!r} {sent}")

    # ---- R6, F4: no process outlives its request (descendants included)
    with tempfile.TemporaryDirectory() as d:
        for label, target, secs in (("soft time limit", "spawn_then_spin", 3),
                                    ("hard kill in C", "spawn_then_c_spin", 3),
                                    ("normal end", "spawn_then_return", 30)):
            marker = os.path.join(d, f"{target}.json")
            r = run_request(f"simwaves.testhooks:{target}", (marker,), secs)
            got = pids_from(marker, 5) or {}
            gone = got and not alive(got["worker"]) and not alive(got["descendant"])
            check(f"R6 {label}: process and descendant gone when the result returns", gone, f"{r!r} {got}")
            for pid in got.values():
                kill_quietly(pid)
        for label, target, with_marker in (("while running", "simwaves.testhooks:spawn_then_spin", True),
                                           ("during the target's import", "slowimport:f", False)):
            marker = os.path.join(d, "parent.json")
            if os.path.exists(marker):
                os.remove(marker)
            write(d, "slowimport.py", SLOW_IMPORT.format(marker=marker))
            args = "(%r,)" % marker if with_marker else "()"
            script = write(d, "parent.py", PARENT.format(here=HERE, target=target, args=args))
            env = dict(ENV, PYTHONPATH=os.pathsep.join([d, HERE]))
            caller = subprocess.Popen([sys.executable, script], cwd=HERE, env=env)
            got = pids_from(marker, 60) or {}
            caller.kill()
            caller.wait(10)
            time.sleep(3)
            check(f"R6/F4 parent killed {label}: process and descendant gone",
                  got and not alive(got["worker"]) and not alive(got["descendant"]), str(got))
            for pid in got.values():
                kill_quietly(pid)

    print(f"\nsummary: {passed}/{passed + failed} passed")
    sys.exit(0 if failed == 0 else 1)
