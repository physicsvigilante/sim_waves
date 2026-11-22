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
"""
import ctypes
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
            live = [e for e in _active if not e.fired]
            if not live:
                _lock.wait()
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


def within(seconds, fn, public=None, memory=False):
    """Run fn() with a deadline `seconds` from now. If the deadline passes first, raise
    `public` (an exception instance or class; default Budget). An earlier deadline of an
    enclosing budget passes through untouched, to be raised by its own `within`.
    memory=True (inner budgets only): running out of memory inside fn also counts as this
    budget running out. The attempt's memory is freed as the exception unwinds, and the
    caller takes the same fallback as for a time-out; a memory limit reached anywhere
    else still ends the request."""
    if seconds is None:
        return fn()
    entry = _Entry(time.monotonic() + max(0.0, float(seconds)), threading.get_ident(),
                   public if public is not None else Budget)
    with _lock:
        _ensure_watchdog()
        _active.append(entry)
        _lock.notify()
    try:
        return fn()
    except _Expired as exc:
        if type(exc).entry is entry:
            pub = entry.public
            raise (pub() if isinstance(pub, type) else pub) from None
        raise
    except MemoryError:
        if not memory:
            raise
        import gc
        exc_ = None                                     # drop the attempt's frames, then its memory
        gc.collect()
        pub = entry.public
        raise (pub() if isinstance(pub, type) else pub) from exc_
    finally:
        with _lock:
            _active.remove(entry)
            if entry.fired:
                # it fired just as fn() returned: clear an exception not yet delivered
                _set_async(entry.tid, None)
            _lock.notify()
