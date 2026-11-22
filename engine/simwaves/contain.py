"""Containment (m15a): every request runs in a worker process under a time and memory limit.

One request lifecycle, owned by the parent (review 15a):
1. **Admission:** limits are validated (finite, positive, typed, never above the run's), and
   a scene file larger than MAX_SCENE_BYTES is refused before it is parsed.
2. **Start-up:** a spawn-started worker. If it fails to start, that is the request's result.
3. **Evaluation:** under a whole-request time budget (budget.py), which ends a slow request
   at a bytecode boundary with ResourceLimitError. If the worker does not answer within the
   limit plus a short grace (stuck inside a long C call), the parent kills it.
4. **Exactly one terminal result** per request: a value, a re-raised scene exception, a
   LimitResult or a CrashResult, never nothing.
5. **Clean-up of the whole process tree:**
   - Windows: a Job Object holds the worker and everything it starts, with memory caps and
     kill-on-close, so they all die with the job, or with the parent.
   - Linux: the worker leads its own process group, under RLIMIT_AS. A small guardian
     process, outside that group, holds a pipe from the parent. It kills the whole group as
     soon as the pipe closes: the parent retired the worker, or the parent died.
   A worker that hit any limit is retired before the next request.
A limit is reported as such, never as a fact about the physics.
"""
import importlib
import math
import multiprocessing as mp
import os
import pickle
import subprocess
import sys
import threading
import traceback

DEFAULT_TIME = 120            # seconds per request
DEFAULT_MEMORY = 2048         # MB per worker process
MIN_MEMORY = 256              # MB: the engine needs about 150 MB just to start
GRACE = 10                    # seconds beyond the time limit before the parent kills
RECYCLE_AFTER = 20            # requests per worker before a fresh one (bounds SymPy's caches)
RECYCLE_AT = 0.5              # ... or once its peak memory passes this share of its limit
MAX_SCENE_BYTES = 64 * 1024   # a scene file above this is refused before parsing
WINDOWS = sys.platform == "win32"
IN_WORKER = False             # True inside a worker: public entry points call through directly


class LimitError(ValueError):
    """A limit value that is not a finite positive number of the right type."""


def check_limits(seconds, memory_mb, max_seconds=None, max_memory=None):
    """Validate a time limit (seconds) and a memory limit (MB). Returns (float seconds, int MB).
    Booleans, NaN, infinities, zero, negatives and non-numbers are refused. Memory must be a
    whole number of MB, at least MIN_MEMORY. A maximum, when given, may not be exceeded."""
    def number(v, what):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise LimitError(f"{what} must be a finite positive number, not {v!r}")
        return v
    s = float(number(seconds, "the time limit"))
    m = number(memory_mb, "the memory limit")
    if isinstance(m, float):
        if not m.is_integer():
            raise LimitError(f"the memory limit must be a whole number of MB, not {memory_mb!r}")
        m = int(m)
    if m < MIN_MEMORY:
        raise LimitError(f"the memory limit must be at least {MIN_MEMORY} MB (the engine needs about 150 MB to "
                         f"start), not {m}")
    if max_seconds is not None and s > max_seconds:
        raise LimitError(f"the time limit {s:g} s is above the run's {max_seconds:g} s; it may only be lowered")
    if max_memory is not None and m > max_memory:
        raise LimitError(f"the memory limit {m} MB is above the run's {max_memory} MB; it may only be lowered")
    return s, m


def check_scene_size(path):
    """Refuse a scene file too large to be a scene, before anything parses it."""
    size = os.path.getsize(path)
    if size > MAX_SCENE_BYTES:
        raise LimitError(f"{os.path.basename(path)}: the file is {size} bytes; scene files are limited to "
                         f"{MAX_SCENE_BYTES // 1024} KB")


# ---------------------------------------------------------------- the worker (child) side
def _resolve(target):
    mod, name = target.split(":")
    return getattr(importlib.import_module(mod), name)


def _posix_setup(memory_mb):
    import resource
    os.setpgrp()                                          # its own process group: killed as one
    limit = memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def _peak_bytes():
    """This worker's peak memory so far (Linux; on Windows the parent asks its Job Object)."""
    if WINDOWS:
        return 0
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def _send_raise(conn, exc):
    """Carry an exception back to the parent; if it cannot be pickled, its traceback."""
    try:
        pickle.dumps(exc)
        conn.send(("raise", exc))
    except Exception:                                     # noqa: BLE001
        conn.send(("error", traceback.format_exc()))


def _serve(conn, memory_mb):
    """The worker loop: run each (target, args, seconds) request under its time budget."""
    global IN_WORKER
    IN_WORKER = True
    for var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(var, "1")                   # no large per-thread buffers
    if not WINDOWS:
        _posix_setup(memory_mb)
    from .budget import within
    from .errors import ResourceLimitError
    import simwaves.run          # noqa: F401  (imports outside any request's time)
    import simwaves.harness      # noqa: F401
    conn.send(("ready", os.getpid()))
    while True:
        try:
            msg = conn.recv()
        except (EOFError, OSError):
            return
        if msg is None:
            return
        target, args, seconds = msg
        try:
            fn = _resolve(target)
            out = within(seconds, lambda: fn(*args), public=ResourceLimitError("time", f"{seconds:g} s"))
            conn.send(("ok", out, _peak_bytes()))
        except ResourceLimitError as exc:
            conn.send(("limit", exc.kind, str(exc)))
        except MemoryError:
            try:
                conn.send(("limit", "memory", f"RESOURCE LIMIT (memory {memory_mb} MB)"))
            finally:
                os._exit(3)                                # its state is not to be trusted
        except Exception as exc:                           # noqa: BLE001 - the caller's exception
            _send_raise(conn, exc)
        except BaseException:                              # noqa: BLE001 - report, keep serving
            conn.send(("error", traceback.format_exc()))


# ---------------------------------------------------------------- Linux guardian
_GUARD = """
import os, signal, sys
pgid, fd = int(sys.argv[1]), int(sys.argv[2])
try:
    while os.read(fd, 1):
        pass
finally:
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
"""


class _Guardian:
    """Linux: a small process outside the worker's group that kills the whole group when the
    pipe from the parent closes (worker retired, or parent dead)."""

    def __init__(self, pgid):
        rfd, self.wfd = os.pipe()
        self.proc = subprocess.Popen([sys.executable, "-c", _GUARD, str(pgid), str(rfd)], pass_fds=(rfd,),
                                     start_new_session=True, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.close(rfd)

    def fire(self):
        """Close the pipe: the guardian kills the group and exits."""
        if self.wfd is not None:
            os.close(self.wfd)
            self.wfd = None
        try:
            self.proc.wait(10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


# ---------------------------------------------------------------- Windows Job Objects
class _Job:
    """A Windows Job Object: a memory limit for the worker and everything it starts, and
    kill-on-close, so they all die with the job (or with the parent)."""

    def __init__(self, memory_mb):
        import ctypes
        from ctypes import wintypes
        self.ct = ctypes
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.k = k
        k.CreateJobObjectW.restype = wintypes.HANDLE
        k.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
        k.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
        k.QueryInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                                                ctypes.c_void_p)
        k.OpenProcess.restype = wintypes.HANDLE
        k.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        k.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
        k.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
        k.CloseHandle.argtypes = (wintypes.HANDLE,)

        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in ("r", "w", "o", "rb", "wb", "ob")]

        class Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class Extended(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", IO), ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]
        self.Extended = Extended
        self.limit = memory_mb * 1024 * 1024
        self.h = k.CreateJobObjectW(None, None)
        if not self.h:
            raise OSError(ctypes.get_last_error(), "CreateJobObject failed")
        info = Extended()
        info.BasicLimitInformation.LimitFlags = 0x2000 | 0x0100 | 0x0200   # KILL_ON_JOB_CLOSE, PROCESS_, JOB_MEMORY
        info.ProcessMemoryLimit = self.limit
        info.JobMemoryLimit = self.limit
        if not k.SetInformationJobObject(self.h, 9, ctypes.byref(info), ctypes.sizeof(info)):
            raise OSError(ctypes.get_last_error(), "SetInformationJobObject failed")

    def assign(self, pid):
        hp = self.k.OpenProcess(0x0100 | 0x0001, False, pid)      # PROCESS_SET_QUOTA | TERMINATE
        if not hp:
            raise OSError(self.ct.get_last_error(), "OpenProcess failed")
        try:
            if not self.k.AssignProcessToJobObject(self.h, hp):
                raise OSError(self.ct.get_last_error(), "AssignProcessToJobObject failed")
        finally:
            self.k.CloseHandle(hp)

    def peak(self):
        info = self.Extended()
        if self.k.QueryInformationJobObject(self.h, 9, self.ct.byref(info), self.ct.sizeof(info), None):
            return max(info.PeakProcessMemoryUsed, info.PeakJobMemoryUsed)
        return 0

    def close(self):
        if self.h:
            self.k.TerminateJobObject(self.h, 1)
            self.k.CloseHandle(self.h)
            self.h = None


# ---------------------------------------------------------------- the parent side
class LimitResult:
    """The request was stopped by a limit: kind 'time' or 'memory'."""

    def __init__(self, kind, message):
        self.kind, self.message = kind, message

    def __repr__(self):
        return self.message


class CrashResult:
    """The request has no result: the worker failed to start, died, or the runner failed."""

    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return self.message


_start_lock = threading.Lock()


class Worker:
    """One contained worker process. call() runs one request and returns its value, a
    LimitResult or a CrashResult, or re-raises the request's own exception. A worker that hit
    a limit, died, or came near its memory limit is retired, with everything it started,
    before the next request."""

    def __init__(self, memory_mb=DEFAULT_MEMORY):
        self.memory_mb = check_limits(1, memory_mb)[1]
        self.proc = self.conn = self.job = self.guard = None
        self.served = 0

    def _start(self):
        ctx = mp.get_context("spawn")
        self.conn, child = ctx.Pipe()
        self.proc = ctx.Process(target=_serve, args=(child, self.memory_mb), daemon=True)
        # The worker needs only simwaves, never the caller's script. A script run directly
        # would otherwise be re-run in the worker (spawn imports __main__ from its path).
        main = sys.modules.get("__main__")
        hidden = None
        with _start_lock:
            if main is not None and getattr(main, "__spec__", None) is None and hasattr(main, "__file__"):
                hidden = main.__dict__.pop("__file__")
            try:
                self.proc.start()
            finally:
                if hidden is not None:
                    main.__file__ = hidden
        child.close()
        if WINDOWS:
            self.job = _Job(self.memory_mb)
            self.job.assign(self.proc.pid)
        if not self.conn.poll(120):                        # imports take a few seconds
            raise RuntimeError("the worker process did not start within 120 s")
        msg = self.conn.recv()                             # EOFError if it died while starting
        if msg[0] != "ready":
            raise RuntimeError(f"the worker process sent {msg!r} instead of starting")
        if not WINDOWS:
            self.guard = _Guardian(self.proc.pid)
        self.served = 0

    def kill(self):
        """Kill the worker and everything it started."""
        if self.proc is None:
            return
        if WINDOWS and self.job is not None:
            self.job.close()
            self.job = None
        if not WINDOWS:
            import signal
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            if self.guard is not None:
                self.guard.fire()
                self.guard = None
        self.proc.join(10)
        try:
            self.conn.close()
        except OSError:
            pass
        self.proc = self.conn = None

    def close(self):
        if self.proc is not None and self.proc.is_alive():
            try:
                self.conn.send(None)
                self.proc.join(5)
            except (OSError, BrokenPipeError):
                pass
        self.kill()

    def pid(self):
        return self.proc.pid if self.proc is not None else None

    def call(self, target, args=(), seconds=DEFAULT_TIME):
        seconds = check_limits(seconds, self.memory_mb)[0]
        if self.proc is None or not self.proc.is_alive() or self.served >= RECYCLE_AFTER:
            if self.proc is not None:
                self.close()
            try:
                self._start()
            except Exception as exc:                       # noqa: BLE001 - a result, not a hang
                self.kill()
                return CrashResult(f"the worker process could not start ({type(exc).__name__}: {exc})")
        self.served += 1
        try:
            self.conn.send((target, tuple(args), seconds))
            ready = self.conn.poll(seconds + GRACE)
            msg = self.conn.recv() if ready else None
        except (EOFError, OSError):
            msg = ("died",)
        if msg is None:                                    # stuck past the limit: hard stop
            self.kill()
            return LimitResult("time", f"RESOURCE LIMIT (time {seconds:g} s)")
        kind = msg[0]
        if kind == "ok":
            # a worker that came close to its limit is replaced before the next request, so
            # that one scene's leftovers (SymPy's caches) cannot push the next one over
            peak = self.job.peak() if (WINDOWS and self.job is not None) else msg[2]
            if peak >= RECYCLE_AT * self.memory_mb * 1024 * 1024:
                self.served = RECYCLE_AFTER
            return msg[1]
        if kind == "limit":
            self.kill()                                    # retire it, and anything it started
            return LimitResult(msg[1], msg[2])
        if kind == "raise":
            raise msg[1]
        if kind == "error":
            self.kill()
            return CrashResult(msg[1])
        # the worker died without answering: over its memory, or a crash
        peak = self.job.peak() if (WINDOWS and self.job is not None) else 0
        code = self.proc.exitcode if self.proc is not None else None
        self.kill()
        if peak >= 0.9 * self.memory_mb * 1024 * 1024 or code in (-9, 3):
            return LimitResult("memory", f"RESOURCE LIMIT (memory {self.memory_mb} MB)")
        return CrashResult(f"the worker process ended unexpectedly (exit code {code})")


def run_contained(target, args=(), seconds=DEFAULT_TIME, memory_mb=DEFAULT_MEMORY):
    """Run one request in a fresh contained worker and close it afterwards."""
    w = Worker(memory_mb)
    try:
        return w.call(target, args, seconds)
    finally:
        w.close()


_shared = {}
_shared_lock = threading.Lock()


def _close_shared():
    for w in list(_shared.values()):
        w.close()
    _shared.clear()


def call_bounded(target, args=(), seconds=DEFAULT_TIME, memory_mb=DEFAULT_MEMORY):
    """The bounded form of a public entry point. Inside a worker the request is already
    contained, so the target runs directly (under the worker's budget). Outside, it runs in a
    shared contained worker of this process (one per memory limit), retired after any limit.
    A LimitResult or CrashResult is raised as ResourceLimitError or RuntimeError, so that a
    direct caller cannot mistake it for a value."""
    if IN_WORKER:
        return _resolve(target)(*args)
    from .errors import ResourceLimitError
    seconds, memory_mb = check_limits(seconds, memory_mb)
    with _shared_lock:
        if not _shared:
            import atexit
            atexit.register(_close_shared)
        w = _shared.setdefault(memory_mb, Worker(memory_mb))
        r = w.call(target, args, seconds)
    if isinstance(r, LimitResult):
        raise ResourceLimitError(r.kind, f"{seconds:g} s" if r.kind == "time" else f"{memory_mb} MB")
    if isinstance(r, CrashResult):
        raise RuntimeError(r.message)
    return r


def run_many(target, items, jobs, seconds_of, memory_mb=DEFAULT_MEMORY, on_result=None):
    """Run target(item) for each item on at most `jobs` contained workers at once. seconds_of
    gives each item's time limit. Every item gets exactly one result: a value, a LimitResult or
    a CrashResult (a start-up, transport or scheduler failure, or an item never reached).
    on_result(index, item, result) is called once per item. Returns the results in item order.
    Every worker is killed at the end, even after Ctrl-C."""
    items = list(items)
    results = [None] * len(items)
    reported = [False] * len(items)
    nxt = [0]
    lock = threading.Lock()
    workers = [Worker(memory_mb) for _ in range(max(1, min(jobs, len(items) or 1)))]
    stop = threading.Event()

    def report(i, r):
        with lock:
            if reported[i]:
                return
            results[i], reported[i] = r, True
            if on_result is not None:
                on_result(i, items[i], r)

    def loop(w):
        while not stop.is_set():
            with lock:
                if nxt[0] >= len(items):
                    return
                i = nxt[0]
                nxt[0] += 1
            try:
                r = w.call(target, (items[i],), seconds_of(items[i]))
            except BaseException as exc:                   # noqa: BLE001 - every item gets a result
                r = CrashResult(f"the test runner failed on this item ({type(exc).__name__}: {exc})")
                try:
                    w.kill()
                except BaseException:                      # noqa: BLE001
                    pass
            report(i, r)

    threads = [threading.Thread(target=loop, args=(w,), daemon=True) for w in workers]
    try:
        for t in threads:
            t.start()
        while any(t.is_alive() for t in threads):
            for t in threads:
                t.join(0.2)
    except KeyboardInterrupt:
        stop.set()
        raise
    finally:
        for w in workers:
            w.kill()
        for i in range(len(items)):
            if not reported[i]:
                report(i, CrashResult("never run (the test runner stopped before reaching it)"))
    return results
