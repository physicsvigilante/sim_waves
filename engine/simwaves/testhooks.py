"""Test-only observables for the containment tests (m15a). Registered only when the
environment variable SIMWAVES_TEST_HOOKS is "1"; never available to authors otherwise.

- test_spin(s): a pure-Python loop for s seconds (a budget interrupts it between bytecodes);
- test_alloc(mb): allocates and holds mb megabytes;
- test_c_spin(): one long C-level call (sum(range(10**10))), which no budget can interrupt:
  only the parent's hard stop ends it.
Each returns 0 when it finishes.
"""
import time

import sympy as sp

from .scene import OBS_DIMS, OBSERVABLES
from .units import DIMLESS


def _spin(_sc, s):
    t = time.monotonic()
    while time.monotonic() - t < float(s):
        pass
    return sp.Integer(0)


def _alloc(_sc, mb):
    keep = [bytearray(1024 * 1024) for _ in range(int(mb))]
    return sp.Integer(0 if keep else 0)


def _c_spin(_sc):
    sum(range(10 ** 10))
    return sp.Integer(0)


OBSERVABLES.update({"test_spin": _spin, "test_alloc": _alloc, "test_c_spin": _c_spin})
OBS_DIMS.update({"test_spin": DIMLESS, "test_alloc": DIMLESS, "test_c_spin": DIMLESS})


def report_pid(_item):
    """For the -j test: which worker ran this item, and when (it works for 0.5 s)."""
    import os
    t0 = time.monotonic()
    while time.monotonic() - t0 < 0.5:
        pass
    return os.getpid(), t0, time.monotonic()


def _start_descendant(marker):
    """Start a sleeping child process and record (worker pid, descendant pid) in marker."""
    import json
    import os
    import subprocess
    import sys
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    with open(marker, "w") as fh:
        json.dump({"worker": os.getpid(), "descendant": child.pid}, fh)
    return child


def spawn_then_spin(marker):
    """Review 15a R6: start a descendant, then spin until a time limit stops the request."""
    _start_descendant(marker)
    while True:
        pass


def spawn_then_c_spin(marker):
    """Review 15a R6: start a descendant, then block in C until the parent's hard stop."""
    _start_descendant(marker)
    return sum(range(10 ** 10))


def spawn_then_return(marker):
    """Review 15a R6: start a descendant and return normally (cleaned when the worker retires)."""
    _start_descendant(marker)
    return "returned"


def nested_budget(_item=None):
    """Review 15a R1: an inner budget (0.10 s) around a 0.20 s C call, whose fallback must not
    replace an earlier whole-request expiry."""
    from .budget import Budget, within
    try:
        within(0.10, lambda: time.sleep(0.20))
    except Budget:
        return "normal fallback value"
    return "inner finished"
