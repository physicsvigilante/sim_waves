"""Review 15a regressions (R1-R6, O1). Run from engine/:
    python tests/test_limits_review.py
Needs psutil (requirements-dev.txt). Uses the test-only hooks (SIMWAVES_TEST_HOOKS=1).
Expected outcomes are the containment contract, not engine output: a limit is a limit, every
scene gets one status, limits are validated, and no process outlives its request.
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
        print(f"FAIL {name} {detail}")


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


if __name__ == "__main__":
    from simwaves.budget import Budget, within
    from simwaves.contain import (CrashResult, LimitError, LimitResult, Worker, run_contained, run_many,
                                  check_limits)
    from simwaves.errors import ResourceLimitError
    from simwaves.harness import run_file, scene_limits

    # ---- R1: an earlier whole-request deadline is never replaced by an inner fallback
    ok = 0
    for _ in range(5):
        try:
            within(0.05, lambda: __import__("simwaves.testhooks", fromlist=["x"]).nested_budget(),
                   public=ResourceLimitError("time", "0.05 s"))
        except ResourceLimitError:
            ok += 1
    check("R1 outer deadline wins over the inner fallback (5 trials)", ok == 5, f"{ok}/5")
    try:
        r = within(5, lambda: __import__("simwaves.testhooks", fromlist=["x"]).nested_budget())
        check("R1 control: inner-only expiry takes its fallback", r == "normal fallback value", repr(r))
    except Budget:
        check("R1 control: inner-only expiry takes its fallback", False, "outer fired")
    w = Worker()
    r = w.call("simwaves.testhooks:nested_budget", (None,), 0.05)
    check("R1 in a worker: a LimitResult, not the fallback", isinstance(r, LimitResult), repr(r))
    w.close()
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
    try:
        within(0.05, lambda: (time.sleep(0.1), "late")[1])
        check("R1 a value finished past its deadline is refused", False)
    except Budget:
        check("R1 a value finished past its deadline is refused", True)

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

    # ---- R3: limits are validated: finite, positive, typed, whole MB, never above the run's
    with tempfile.TemporaryDirectory() as d:
        bad = {"neg memory": "{memory: -1}", "zero memory": "{memory: 0}", "bool time": "{time: true}",
               "nan time": "{time: .nan}", "inf time": "{time: .inf}", "neg time": "{time: -5}",
               "fractional memory": "{memory: 300.5}", "text": "{time: fast}", "list": "[1, 2]",
               "extra key": "{time: 5, cpu: 1}", "raised time": "{time: 999}", "raised memory": "{memory: 4096}",
               "below the start-up minimum": "{memory: 100}"}
        for label, lim in bad.items():
            p = write(d, "s.yaml", f"observe: {{v: '1'}}\nexpect: {{limits: {lim}, v: 1}}\n")
            _, _, err, _ = scene_limits(p, 120, 2048)
            check(f"R3 refused: {label}", err is not None, lim)
        p = write(d, "s.yaml", "observe: {v: '1'}\nexpect: {limits: {time: 5, memory: 512.0}, v: 1}\n")
        check("R3 control: valid lower limits", scene_limits(p, 120, 2048) == (5.0, 512, None, False))
        for label, args in {"Worker(-1)": (lambda: Worker(-1)), "check_limits nan": (lambda: check_limits(
                float("nan"), 512))}.items():
            try:
                args()
                check(f"R3 refused at the containment boundary: {label}", False)
            except LimitError:
                check(f"R3 refused at the containment boundary: {label}", True)

        # ---- R4: an oversized file is refused before it is parsed
        big = write(d, "big.yaml", "assume: ['" + "x" * 4_000_000 + "']\nobserve: {v: '1'}\nexpect: {v: 1}\n")
        t0 = time.monotonic()
        _, _, err, _ = scene_limits(big, 120, 2048)
        dt = time.monotonic() - t0
        check("R4 oversized scene refused before parsing", err is not None and "limited to" in err and dt < 0.2,
              f"{err} in {dt:.2f} s")

        # ---- R2: every scene gets exactly one status; no result is never success
        one = os.path.join(d, "one")
        os.mkdir(one)
        write(one, "a.yaml", "observe: {v: '1'}\nexpect: {v: 1}\n")
        write(one, "b.yaml", "observe: {v: '1'}\nexpect: {limits: {time: .nan}, v: 1}\n")
        r = subprocess.run([sys.executable, "-m", "simwaves", "test", one, "-j", "1"], cwd=HERE, env=ENV,
                           capture_output=True, text=True, encoding="utf-8", timeout=300)
        check("R2 an invalid limit gives an ERROR and a non-zero exit",
              r.returncode != 0 and "ERROR 1" in r.stdout and "PASS 1" in r.stdout, r.stdout[-400:])
        empty = os.path.join(d, "empty")
        os.mkdir(empty)
        r = subprocess.run([sys.executable, "-m", "simwaves", "test", empty], cwd=HERE, env=ENV,
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
        check("R2 an empty folder is not a success", r.returncode != 0, r.stdout)

    # start-up failure and a scheduler failure part-way: every item still gets a result
    orig = Worker._start
    Worker._start = lambda self: (_ for _ in ()).throw(EOFError("injected start-up failure"))
    out = run_many("simwaves.testhooks:report_pid", list(range(3)), 2, lambda _: 30)
    Worker._start = orig
    check("R2 start-up failure: one CrashResult per item", len(out) == 3 and all(isinstance(x, CrashResult)
                                                                                 for x in out), repr(out))
    calls = [0]
    orig_call = Worker.call

    def flaky(self, *a, **k):
        calls[0] += 1
        if calls[0] == 3:
            raise RuntimeError("injected transport failure")
        return orig_call(self, *a, **k)
    Worker.call = flaky
    out = run_many("simwaves.testhooks:report_pid", list(range(5)), 1, lambda _: 30)
    Worker.call = orig_call
    kinds = [type(x).__name__ for x in out]
    check("R2 partial completion then a failure: all 5 accounted for",
          len(out) == 5 and kinds.count("CrashResult") == 1 and kinds.count("tuple") == 4, str(kinds))

    # ---- R5: the public entry points are bounded
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "direct.yaml", "observe: {v: 'test_spin(5)'}\nexpect: {limits: {time: 1}, error: limit}\n")
        status, lines = run_file(p)
        check("R5 run_file enforces expect.limits and error: limit",
              status == "PASS" and "stopped by a limit" in lines[0], f"{status} {lines}")
        p = write(d, "direct2.yaml", "observe: {v: 'test_spin(5)'}\nexpect: {limits: {time: 1}, v: 0}\n")
        status, _ = run_file(p)
        check("R5 run_file reports an unexpected limit as LIMIT", status == "LIMIT", status)
    from simwaves.export import export
    try:
        export({"observe": {"v": "test_spin(10)"}}, seconds=1)
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

    # ---- R6: no descendant outlives its request
    with tempfile.TemporaryDirectory() as d:
        for label, target, secs in (("soft time limit", "spawn_then_spin", 1),
                                    ("hard kill in C", "spawn_then_c_spin", 1)):
            marker = os.path.join(d, f"{target}.json")
            w = Worker()
            r = w.call(f"simwaves.testhooks:{target}", (marker,), secs)
            got = pids_from(marker, 5) or {}
            time.sleep(2)
            gone = got and not alive(got["worker"]) and not alive(got["descendant"])
            check(f"R6 {label}: worker and descendant gone", isinstance(r, LimitResult) and gone,
                  f"{r!r} {got}")
            w.close()
            for pid in got.values():
                kill_quietly(pid)
        marker = os.path.join(d, "ret.json")
        w = Worker()
        r = w.call("simwaves.testhooks:spawn_then_return", (marker,), 30)
        got = pids_from(marker, 5) or {}
        w.close()
        time.sleep(2)
        check("R6 retire after a normal request: descendant gone", r == "returned" and got and
              not alive(got["descendant"]), f"{r!r} {got}")
        for pid in got.values():
            kill_quietly(pid)
        # the supervising parent dies
        marker = os.path.join(d, "parent.json")
        code = ("import sys; sys.path.insert(0, %r)\n"
                "from simwaves.contain import Worker\n"
                "if __name__ == '__main__':\n"
                "    Worker().call('simwaves.testhooks:spawn_then_spin', (%r,), 60)\n") % (HERE, marker)
        script = write(d, "parent.py", code)
        caller = subprocess.Popen([sys.executable, script], cwd=HERE, env=ENV)
        got = pids_from(marker, 60) or {}
        caller.kill()
        caller.wait(10)
        time.sleep(3)
        check("R6 parent killed: worker and descendant gone",
              got and not alive(got["worker"]) and not alive(got["descendant"]), str(got))
        for pid in got.values():
            kill_quietly(pid)

    print(f"\nsummary: {passed}/{passed + failed} passed")
    sys.exit(0 if failed == 0 else 1)
