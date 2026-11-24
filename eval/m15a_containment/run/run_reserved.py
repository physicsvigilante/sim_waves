"""Run each reserved m15a scene alone through the CLI with the default limits; record its output,
exit code, wall time, and any simwaves.child process left afterwards. Usage (from engine/):
    python run_reserved.py <reserved dir> <out dir>"""
import os
import subprocess
import sys
import time

import psutil

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)


def children():
    left = []
    for pr in psutil.process_iter(["cmdline"]):
        try:
            if "simwaves.child" in " ".join(pr.info["cmdline"] or []):
                left.append(pr.pid)
        except psutil.Error:
            pass
    return left


env = dict(os.environ, PYTHONIOENCODING="utf-8")
for n in range(1, 7):
    scene = os.path.join(src, f"S{n}.yaml")
    t0 = time.monotonic()
    p = subprocess.run([sys.executable, "-m", "simwaves", "run", scene], capture_output=True, text=True,
                       encoding="utf-8", env=env, timeout=400)
    dt = time.monotonic() - t0
    time.sleep(1)
    left = children()
    text = (f"# S{n}: exit {p.returncode}, {dt:.1f} s, simwaves.child left: {left or 'none'}\n"
            f"## stdout\n{p.stdout}\n## stderr\n{p.stderr}\n")
    open(os.path.join(out, f"S{n}.txt"), "w", encoding="utf-8").write(text)
    print(f"S{n}: exit {p.returncode}, {dt:.1f} s, left: {left or 'none'}", flush=True)
