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

Lifecycle (review 15a, R1 and F3):
- **Priority:** once a budget has fired on a thread, no other budget fires on that thread
  until the fired one's `within` has handled it. An expired enclosing budget is never
  replaced by a later inner one.
- **Registration and teardown** are protected. State is guarded by a plain C lock: a `with`
  on it always releases it, even if an exception arrives. Teardown first marks the thread
  "critical", and the watchdog never fires on a critical thread. Any expiry delivered while
  setting up or tearing down is caught there and classified as this budget's or an
  enclosing one's. No entry is ever left behind, and no private exception escapes.
- **No late values:** a `within` whose deadline has passed never returns a value, even if fn()
  finished just after the deadline.
"""
import ctypes
import gc
import threading
import time

POLL = 0.005                  # seconds between the watchdog's checks


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


_mutex = threading.Lock()     # a C lock: `with` on it is never left half-entered
_active = []
_critical = set()             # threads in a budget's teardown: never fired on
_watchdog = None


def _set_async(tid, exc):
    return ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(tid),
                                                      ctypes.py_object(exc) if exc is not None else None)


def _watch():
    while True:
        wait = POLL
        with _mutex:
            busy = {e.tid for e in _active if e.fired}
            live = [e for e in _active if not e.fired and e.tid not in busy and e.tid not in _critical]
            if live:
                first = min(live, key=lambda e: e.deadline)
                left = first.deadline - time.monotonic()
                if left <= 0:
                    first.fired = True
                    _set_async(first.tid, first.cls)
                else:
                    wait = min(POLL, left)
        time.sleep(wait)


def _ensure_watchdog():
    global _watchdog
    if _watchdog is None or not _watchdog.is_alive():
        _watchdog = threading.Thread(target=_watch, name="simwaves-budget", daemon=True)
        _watchdog.start()


def _flush():
    """A call: a pending asynchronous exception is delivered here, at the latest."""
    return None


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
    _ensure_watchdog()
    tid = threading.get_ident()
    entry = _Entry(time.monotonic() + seconds, tid, public if public is not None else Budget)
    ran_out = out_of_memory = False
    outer = other = None
    result = None

    def guarded():
        # fn's own return or exception passes through here, still inside the protected
        # region below: the thread becomes critical (no new expiry fired on it), then any
        # expiry already pending is delivered at _flush(), where it is still caught
        try:
            return fn()
        finally:
            with _mutex:
                _critical.add(tid)
            _flush()

    try:
        try:
            with _mutex:
                _active.append(entry)
            result = guarded()
        except _Expired as exc:
            if type(exc).entry is entry:
                ran_out = True
            else:
                outer = exc                             # an enclosing budget's: re-raised below
        except MemoryError as exc:
            if memory:
                out_of_memory = True
            else:
                other = exc
        except BaseException as exc:                    # noqa: BLE001 - re-raised after clean-up
            other = exc
    finally:
        # teardown: the thread is critical (or blocked by an expiry already delivered), so no
        # expiry arrives here; the loop is a second line of defence
        while True:
            try:
                with _mutex:
                    _critical.add(tid)
                    if entry in _active:
                        _active.remove(entry)
                    if entry.fired:
                        _set_async(tid, None)           # ours, if still undelivered
                break
            except _Expired as exc:
                if type(exc).entry is entry:
                    ran_out = True
                elif outer is None:
                    outer = exc
    with _mutex:
        _critical.discard(tid)
    if outer is not None:
        raise outer
    if out_of_memory:
        gc.collect()
        raise _public(entry)
    if other is not None:
        raise other
    if ran_out or entry.fired or time.monotonic() >= entry.deadline:
        raise _public(entry)                            # past the deadline: never a value
    return result
