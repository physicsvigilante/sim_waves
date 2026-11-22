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
