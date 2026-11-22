"""Time budgets that work the same on every platform (m15a).

A budget is a deadline on the thread that sets it. One watchdog thread watches every active
deadline and, when the earliest passes, raises an exception in that thread
(`PyThreadState_SetAsyncExc`). SymPy is pure Python, so the exception arrives at the next
bytecode. A long call inside C code delays it, and the parent process (`contain.py`) is the
hard stop for that.

The injected exception is private to its budget and derives from BaseException. No
`except Exception` between the deadline and its own `within` can swallow it and turn a
time-out into a numerical fallback or a refusal it was not meant to cause. Its own `within`
turns it into the public exception chosen for that budget: an inner budget gives `Budget`,
which the caller handles (its numerical fallback or a specific refusal). The whole-request
budget gives `ResourceLimitError`.

Priority (review 15a, R1): once a budget has fired on a thread, no other budget fires on
that thread until the fired one's `within` has finished with it. So an expired enclosing
budget is never replaced by a later inner one, and never turned into an inner fallback.
A `within` whose deadline has passed never returns a value, even if fn() finished just after
the deadline: the deadline is checked again on return.
"""
import ctypes
import gc
import threading
import time


class Budget(Exception):
    """An inner time budget ran out; the caller takes its fallback or refuses."""


class _Expired(BaseException):
    """Raised in the target thread when a budget's deadline passes (one subclass per budget)."""
    entry = None


class _Entry:
    __slots__ = ("deadline", "tid", "cls", "public", "fired")

    def __init__(self, deadline, tid, public):
        self.deadline, self.tid, self.public, self.fired = deadline, tid, public, False
        self.cls = type("_ExpiredHere", (_Expired,), {"entry": self})


_lock = threading.Condition()
_active = []
_watchdog = None


def _set_async(tid, exc):
    return ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(tid),
                                                      ctypes.py_object(exc) if exc is not None else None)


def _watch():
    with _lock:
        while True:
            # a thread with a fired budget still in force takes no further exception until
            # that budget's within has handled it (an earlier expiry is never overwritten)
            busy = {e.tid for e in _active if e.fired}
            live = [e for e in _active if not e.fired and e.tid not in busy]
            if not live:
                _lock.wait(None if not _active else 0.05)
                continue
            first = min(live, key=lambda e: e.deadline)
            wait = first.deadline - time.monotonic()
            if wait > 0:
                _lock.wait(wait)
                continue
            first.fired = True
            _set_async(first.tid, first.cls)


def _ensure_watchdog():
    global _watchdog
    if _watchdog is None or not _watchdog.is_alive():
        _watchdog = threading.Thread(target=_watch, name="simwaves-budget", daemon=True)
        _watchdog.start()


def _public(entry):
    pub = entry.public
    return pub() if isinstance(pub, type) else pub


def within(seconds, fn, public=None, memory=False):
    """Run fn() with a deadline `seconds` from now. If the deadline passes first, raise
    `public` (an exception instance or class; default Budget). An earlier deadline of an
    enclosing budget passes through untouched, to be raised by its own `within`.
    memory=True (inner budgets only): running out of memory inside fn also counts as this
    budget running out. The exception is raised after the failed attempt's frames are
    released, so the caller's fallback runs with that memory free. A memory limit reached
    anywhere else still ends the request."""
    if seconds is None:
        return fn()
    seconds = float(seconds)
    if not seconds > 0 or seconds != seconds or seconds == float("inf"):
        raise ValueError(f"a time budget must be a finite positive number of seconds, not {seconds}")
    entry = _Entry(time.monotonic() + seconds, threading.get_ident(),
                   public if public is not None else Budget)
    with _lock:
        _ensure_watchdog()
        _active.append(entry)
        _lock.notify()
    ran_out = out_of_memory = False
    result = None
    try:
        result = fn()
    except _Expired as exc:
        if type(exc).entry is not entry:
            raise                                       # an enclosing budget's: not ours
        ran_out = True
    except MemoryError:
        if not memory:
            raise
        out_of_memory = True
    finally:
        with _lock:
            _active.remove(entry)
            if entry.fired and not ran_out:
                # it fired as fn() was returning or unwinding: clear it if not yet delivered
                _set_async(entry.tid, None)
            _lock.notify()
    # outside every handler: the failed attempt's traceback and frames are released here
    if out_of_memory:
        gc.collect()
        raise _public(entry)
    if ran_out or entry.fired or time.monotonic() >= entry.deadline:
        raise _public(entry)                            # past the deadline: never a value
    return result
