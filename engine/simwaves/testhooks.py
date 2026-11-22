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


_payload = b""


def prepare_big(n):
    """Review 15a F2: keep n bytes in this worker for the next request."""
    global _payload
    _payload = b"x" * int(n)
    return len(_payload)


def get_big():
    """Review 15a F2: a reply of the prepared size (its transfer takes time)."""
    return _payload


def sleep_then_big(delay, n):
    """Review 15a F2: wait, then reply with n bytes (for a transfer stalled part-way)."""
    time.sleep(float(delay))
    return b"x" * int(n)


def late_big(n):
    """Review 15a G1/F2: work until just before the request's deadline, then reply with n bytes,
    so the reply is complete only after the deadline."""
    from . import contain
    left = contain.remaining() or 0
    time.sleep(max(0.0, left - 0.02))
    return b"x" * int(n)


def stall_reply():
    """Review 15a F2: start a reply frame on the reply stream, then stall forever, so the parent
    is left holding a partial frame."""
    import struct
    from . import contain
    with contain._reply_lock:
        contain._reply.write(struct.pack("<Q", 10 ** 6) + b"partial")
        contain._reply.flush()
    while True:
        time.sleep(1)


def nested_budget_at_edge():
    """Review 15a R1 in a request: an inner budget whose fallback would come after the
    request's own deadline. The request's limit must win."""
    from . import contain
    from .budget import Budget, within
    left = contain.remaining() or 0
    time.sleep(max(0.0, left - 0.05))
    try:
        within(0.10, lambda: time.sleep(0.20))
    except Budget:
        return "normal fallback value"
    return "inner finished"


def slow_then_raise():
    """Review 15a G4: block in C past the request's deadline, then raise an ordinary error.
    The request's limit must win."""
    from . import contain
    time.sleep((contain.remaining() or 0) + 0.3)
    raise ValueError("an ordinary error, raised after the deadline")
