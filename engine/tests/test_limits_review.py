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

    # ---- G2: the deadline starts at admission, so start-up counts
    r = run_request("os:getpid", (), 0.05)
    check("G2 start-up counts against the limit", isinstance(r, LimitResult), repr(r))
    r = run_request("os:getpid", (), 30)
    check("G2 control: the same request with time to start", isinstance(r, int), repr(r))

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
