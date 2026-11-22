"""Containment checks (m15a). Run from engine/:
    python tests/test_limits.py
Needs psutil (requirements-dev.txt) to see processes. Uses the test-only observables
(SIMWAVES_TEST_HOOKS=1); see simwaves/testhooks.py and tests/limits/.
"""
import os
import subprocess
import sys
import tempfile
import time

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


def workers_now():
    """Live multiprocessing workers started by the engine (spawn_main), by pid."""
    out = set()
    for p in psutil.process_iter(["pid", "cmdline"]):
        cmd = " ".join(p.info.get("cmdline") or [])
        if "spawn_main" in cmd or "multiprocessing.forkserver" in cmd or "multiprocessing.spawn" in cmd:
            out.add(p.info["pid"])
    return out


def cli(*args, timeout=300):
    t0 = time.monotonic()
    r = subprocess.run([sys.executable, "-m", "simwaves", *args], cwd=HERE, env=ENV, capture_output=True,
                       text=True, encoding="utf-8", timeout=timeout)
    return r.returncode, r.stdout + r.stderr, time.monotonic() - t0


if __name__ == "__main__":
    before = workers_now()

    # 1. the limit scenes and controls, in parallel
    code, out, dt = cli("test", "tests/limits", "-j", "2")
    check("limit scenes all pass", code == 0 and "summary: PASS 5" in out, out[-600:])

    # 2. no worker survives a run
    time.sleep(1)
    left = workers_now() - before
    check("no worker left after a test run", not left, str(left))

    # 3. `run` reports a limit as a limit, with its own exit code, never as a physics error
    code, out, dt = cli("run", "tests/limits/l01_time.yaml", "--time", "3")
    check("run: time limit reported as RESOURCE LIMIT", code == 3 and "RESOURCE LIMIT (time 3 s)" in out,
          f"code {code}: {out[-400:]}")
    check("run: within the limit plus the shutdown", dt < 3 + 5 + 15, f"{dt:.1f} s (includes start-up)")
    check("run: not reported as a scene error",
          not any(w in out for w in ("InconsistentError", "UndeterminedError", "SceneError", "unsupported")), out)
    code, out, _ = cli("run", "tests/limits/l02_memory.yaml", "--memory", "512")
    check("run: memory limit reported as RESOURCE LIMIT", code == 3 and "RESOURCE LIMIT (memory 512 MB)" in out,
          f"code {code}: {out[-400:]}")

    # 4. the parent dies: its worker dies with it (Job Object / parent-death signal)
    p = subprocess.Popen([sys.executable, "-m", "simwaves", "run", "tests/limits/l01_time.yaml", "--time", "60"],
                         cwd=HERE, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    kids = []
    for _ in range(60):
        time.sleep(0.5)
        try:
            kids = psutil.Process(p.pid).children(recursive=True)
        except psutil.NoSuchProcess:
            break
        if kids:
            break
    time.sleep(1)
    p.kill()
    p.wait(10)
    time.sleep(3)
    alive = [k.pid for k in kids if k.is_running() and k.status() != psutil.STATUS_ZOMBIE]
    check("worker found while the request ran", bool(kids))
    check("worker killed with its parent", not alive, str(alive))

    # 5. -j N: never more than N workers at once
    from simwaves.contain import run_many
    res = run_many("simwaves.testhooks:report_pid", list(range(6)), 2, lambda _: 30)
    pids = {r[0] for r in res}
    events = sorted([(r[1], 1) for r in res] + [(r[2], -1) for r in res])
    peak = cur = 0
    for _, d in events:
        cur += d
        peak = max(peak, cur)
    check("-j 2: at most 2 workers", len(pids) <= 2 and peak <= 2, f"pids {pids}, peak {peak}")

    # 6. an expect block may lower its limits, never raise them
    from simwaves.harness import scene_limits
    with tempfile.TemporaryDirectory() as d:
        low, high = os.path.join(d, "low.yaml"), os.path.join(d, "high.yaml")
        open(low, "w").write("observe: {v: '1'}\nexpect: {limits: {time: 5, memory: 256}, v: 1}\n")
        open(high, "w").write("observe: {v: '1'}\nexpect: {limits: {time: 999}, v: 1}\n")
        t, m, err, _ = scene_limits(low, 120, 2048)
        check("expect lowers the limits", (t, m, err) == (5, 256, None), str((t, m, err)))
        t, m, err, _ = scene_limits(high, 120, 2048)
        check("expect cannot raise the limits", err is not None and "may only be lowered" in err, str(err))

    time.sleep(1)
    left = workers_now() - before
    check("no worker left at the end", not left, str(left))
    print(f"\nsummary: {passed}/{passed + failed} passed")
    sys.exit(0 if failed == 0 else 1)
