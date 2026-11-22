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
    from simwaves.harness import run_dir, run_file

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

    # ---- R3: limits are validated: finite, positive, typed, whole MB (round 2: run-wide only)
    for label, (t, m) in {"neg memory": (120, -1), "zero memory": (120, 0), "bool time": (True, 512),
                          "nan time": (float("nan"), 512), "inf time": (float("inf"), 512), "neg time": (-5, 512),
                          "fractional memory": (120, 300.5), "text": ("fast", 512),
                          "below the start-up minimum": (120, 100)}.items():
        try:
            check_limits(t, m)
            check(f"R3 refused: {label}", False)
        except LimitError:
            check(f"R3 refused: {label}", True)
    check("R3 control: valid limits", check_limits(5, 512.0) == (5.0, 512))
    try:
        Worker(-1)
        check("R3 refused at the containment boundary: Worker(-1)", False)
    except LimitError:
        check("R3 refused at the containment boundary: Worker(-1)", True)

    with tempfile.TemporaryDirectory() as d:
        # ---- R4: an oversized file is refused before it is parsed (now inside the worker too)
        big = write(d, "big.yaml", "assume: ['" + "x" * 4_000_000 + "']\nobserve: {v: '1'}\nexpect: {v: 1}\n")
        status, lines = run_file(big)
        check("R4 oversized scene refused", status == "ERROR" and "limited to" in lines[0], f"{status} {lines}")

        # ---- F1: the parent never parses a scene: a tiny alias-expanding file is bounded
        bomb = os.path.join(d, "bomb")
        os.mkdir(bomb)
        a = "&a0 {v: 1}"
        for i in range(1, 23):
            a = f"&a{i} {{<<: [{a}, *a{i - 1}]}}"
        write(bomb, "alias.yaml", 'observe: {v: "1"}\nexpect: ' + a + "\n")
        write(bomb, "plain.yaml", 'observe: {v: "1"}\nexpect: {v: 1}\n')
        t0 = time.monotonic()
        counts = run_dir(bomb, 1, 2, 512)
        dt = time.monotonic() - t0
        check("F1 alias-expanding scene bounded by the run's limit; neighbour passes",
              counts.get("PASS") == 1 and sum(counts.values()) == 2 and "PASS" in counts and dt < 2 * (2 + 10) + 60,
              f"{counts} in {dt:.1f} s")
        import simwaves.harness as hmod
        check("F1 no per-scene limits reader in the parent", not hasattr(hmod, "scene_limits"))

        # ---- R2: every scene gets exactly one status; no result is never success
        one = os.path.join(d, "one")
        os.mkdir(one)
        write(one, "a.yaml", "observe: {v: '1'}\nexpect: {v: 1}\n")
        write(one, "b.yaml", "observe: {v: '1'}\nexpect: {limits: {time: 5}, v: 1}\n")
        r = subprocess.run([sys.executable, "-m", "simwaves", "test", one, "-j", "1"], cwd=HERE, env=ENV,
                           capture_output=True, text=True, encoding="utf-8", timeout=300)
        check("R2 a scene's own limits give an ERROR and a non-zero exit",
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
        p = write(d, "direct.yaml", "observe: {v: 'test_spin(5)'}\nexpect: {error: limit}\n")
        status, lines = run_file(p, seconds=1)
        check("R5 run_file enforces its limit and error: limit",
              status == "PASS" and "stopped by a limit" in lines[0], f"{status} {lines}")
        p = write(d, "direct2.yaml", "observe: {v: 'test_spin(5)'}\nexpect: {v: 0}\n")
        status, _ = run_file(p, seconds=1)
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

    # ---- F5: only None selects a default; 0 and False are refused, never replaced
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "ordinary.yaml", "observe: {v: '1'}\nexpect: {v: 1}\n")
        for label, kw in {"seconds=0": {"seconds": 0}, "seconds=False": {"seconds": False},
                          "memory_mb=0": {"memory_mb": 0}, "memory_mb=False": {"memory_mb": False}}.items():
            status, lines = run_file(p, **kw)
            check(f"F5 run_file({label}) refused", status == "ERROR", f"{status} {lines}")
        status, _ = run_file(p, seconds=None, memory_mb=None)
        check("F5 control: run_file with None uses the defaults", status == "PASS", status)
        check("F5 run_dir(seconds=0) refused", run_dir(d, 1, 0) == {"ERROR": 1})
        check("F5 run_dir(seconds=False) refused", run_dir(d, 1, False) == {"ERROR": 1})
        try:
            export({"observe": {"v": "1"}}, seconds=0)
            check("F5 export(seconds=0) refused", False)
        except LimitError:
            check("F5 export(seconds=0) refused", True)

    # ---- F2: the parent's deadline covers the whole reply, and a stalled transfer is stopped
    w = Worker()
    w.call("simwaves.testhooks:prepare_big", (64 * 1024 * 1024,), 30)
    t0 = time.monotonic()
    r = w.call("simwaves.testhooks:get_big", (), 0.05)
    dt = time.monotonic() - t0
    check("F2 a reply complete only after its limit is a limit", isinstance(r, LimitResult),
          f"{type(r).__name__} {dt:.2f} s")
    r = w.call("simwaves.testhooks:prepare_big", (16,), 30)
    check("F2 control: a small reply within its limit", r == 16, repr(r))
    from simwaves.contain import GRACE
    # a reply that never completes: the receive blocks (as with a transfer stalled part-way);
    # the parent must still stop at its hard stop and return a limit
    original_recv = w.conn.recv
    blocked = []

    def stalled_recv():
        blocked.append(True)
        time.sleep(3600)
        return original_recv()
    w.conn.recv = stalled_recv
    box = {}

    def stalled():
        box["r"] = w.call("simwaves.testhooks:sleep_then_big", (0.2, 1024), 2)
    t = threading.Thread(target=stalled, daemon=True)
    t0 = time.monotonic()
    t.start()
    t.join(2 + GRACE + 20)
    dt = time.monotonic() - t0
    r = box.get("r")
    check("F2 a stalled transfer ends at the hard stop",
          bool(blocked) and not t.is_alive() and isinstance(r, LimitResult) and dt < 2 + GRACE + 20,
          f"blocked={bool(blocked)} {type(r).__name__} {dt:.1f} s")
    w.close()

    # ---- F3: an expiry at any line of within() (set-up or teardown) is handled
    from simwaves import budget
    codes = [budget.within.__code__] + [c for c in budget.within.__code__.co_consts if hasattr(c, "co_lines")]
    problems = []
    for code in codes:
        for target in sorted({ln for _, _, ln in code.co_lines() if ln}):
            st = {"used": False}

            def tr(frame, event, arg, code=code, target=target, st=st):
                if frame.f_code is code and event == "line" and frame.f_lineno == target and not st["used"]:
                    st["used"] = True
                    time.sleep(0.10)
                return tr
            sys.settrace(tr)
            try:
                v = budget.within(0.025, lambda: 17, public=ResourceLimitError("time", ".025 s"))
                out = f"value {v}"
            except ResourceLimitError:
                out = "limit"
            except BaseException as exc:                  # noqa: BLE001
                out = type(exc).__name__
            finally:
                sys.settrace(None)
            time.sleep(0.03)
            if out not in ("limit", "value 17") or budget._active or budget._critical:
                problems.append((code.co_name, target, out, len(budget._active)))
                budget._active.clear()
                budget._critical.clear()
    check("F3 expiry at every line of within(): classified, no state left", not problems, str(problems))

    # ---- F4: the worker is owned from its start, before its imports
    with tempfile.TemporaryDirectory() as d:
        marker = os.path.join(d, "startup.json")
        write(d, "startup_parent.py", (
            "import json, os, sys, time\n"
            "class DelayRunImport:\n"
            "    def find_spec(self, fullname, path=None, target=None):\n"
            "        if fullname == 'simwaves.run' and getattr(sys.modules.get('simwaves.contain'), 'IN_WORKER',"
            " False):\n"
            "            with open(os.environ['REVIEW_STARTUP_MARKER'], 'w') as f:\n"
            "                json.dump({'worker': os.getpid()}, f)\n"
            "            time.sleep(60)\n"
            "        return None\n"
            "sys.meta_path.insert(0, DelayRunImport())\n"
            "if __name__ == '__main__':\n"
            "    from simwaves.contain import Worker\n"
            "    Worker().call('os:getpid', (), 30)\n"))
        env = dict(ENV, REVIEW_STARTUP_MARKER=marker, PYTHONPATH=os.pathsep.join([d, HERE]))
        caller = subprocess.Popen([sys.executable, "-m", "startup_parent"], cwd=d, env=env)
        got = pids_from(marker, 60) or {}
        caller.kill()
        caller.wait(10)
        time.sleep(3)
        check("F4 parent killed during the worker's start-up: worker gone", got and not alive(got["worker"]),
              str(got))
        for pid in got.values():
            kill_quietly(pid)

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
