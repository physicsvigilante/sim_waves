"""Containment (m15a): every request runs in a worker process under a time and memory limit.

The parent process is the hard stop:
- the worker runs the request under a whole-request time budget (budget.py), which ends a
  slow request at a bytecode boundary with ResourceLimitError;
- if the worker does not answer within the limit plus a short grace (stuck inside a long C
  call), the parent kills it and everything it started;
- memory is capped by the operating system: a Job Object on Windows (which also kills the
  worker if the parent dies), RLIMIT_AS on Linux (with the worker in its own process group,
  and killed if the parent dies).
A limit is reported as such, never as a fact about the physics.
"""
import importlib
import multiprocessing as mp
import os
import sys
import threading
import time
import traceback

DEFAULT_TIME = 120            # seconds per request
DEFAULT_MEMORY = 2048         # MB per worker process
GRACE = 10                    # seconds beyond the time limit before the parent kills
RECYCLE_AFTER = 20            # requests per worker before a fresh one (bounds SymPy's caches)
RECYCLE_AT = 0.5              # ... or once its peak memory passes this share of its limit
WINDOWS = sys.platform == "win32"


# ---------------------------------------------------------------- the worker (child) side
def _resolve(target):
    mod, name = target.split(":")
    return getattr(importlib.import_module(mod), name)


def _posix_setup(memory_mb):
    import resource
    import signal
    os.setpgrp()                                          # its own process group: killed as one
    limit = memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    try:                                                  # killed if the parent dies (Linux)
        import ctypes
        ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGKILL)   # PR_SET_PDEATHSIG
    except (OSError, AttributeError):
        pass


def _peak_bytes():
    """This worker's peak memory so far (Linux; on Windows the parent asks its Job Object)."""
    if WINDOWS:
        return 0
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def _serve(conn, memory_mb):
    """The worker loop: run each (target, args, seconds) request under its time budget."""
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
            out = within(seconds, lambda: fn(*args), public=ResourceLimitError("time", f"{seconds} s"))
            conn.send(("ok", out, _peak_bytes()))
        except ResourceLimitError as exc:
            conn.send(("limit", exc.kind, str(exc)))
        except MemoryError:
            try:
                conn.send(("limit", "memory", f"RESOURCE LIMIT (memory {memory_mb} MB)"))
            finally:
                os._exit(3)                                # its state is not to be trusted
        except BaseException:                              # noqa: BLE001 - report, keep serving
            conn.send(("error", traceback.format_exc()))


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

    def kill(self):
        self.k.TerminateJobObject(self.h, 1)

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
    def __init__(self, message):
        self.message = message


class Worker:
    """One contained worker process. call() runs one request and returns its value, a
    LimitResult, or a CrashResult; a worker that was killed is restarted on the next call."""

    def __init__(self, memory_mb=DEFAULT_MEMORY):
        self.memory_mb = memory_mb
        self.proc = self.conn = self.job = None
        self.served = 0

    def _start(self):
        ctx = mp.get_context("spawn")
        self.conn, child = ctx.Pipe()
        self.proc = ctx.Process(target=_serve, args=(child, self.memory_mb), daemon=True)
        self.proc.start()
        child.close()
        if WINDOWS:
            self.job = _Job(self.memory_mb)
            self.job.assign(self.proc.pid)
        if not self.conn.poll(120):                        # imports take a few seconds
            self.kill()
            raise RuntimeError("the worker process did not start")
        msg = self.conn.recv()
        assert msg[0] == "ready", msg
        self.served = 0

    def kill(self):
        """Kill the worker and everything it started."""
        if self.proc is None:
            return
        if WINDOWS and self.job is not None:
            self.job.close()
            self.job = None
        else:
            import signal
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
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
        if self.proc is None or not self.proc.is_alive() or self.served >= RECYCLE_AFTER:
            if self.proc is not None:
                self.close()
            self._start()
        self.served += 1
        self.conn.send((target, tuple(args), seconds))
        try:
            ready = self.conn.poll(seconds + GRACE)
            msg = self.conn.recv() if ready else None
        except (EOFError, OSError):
            msg = ("died",)
        if msg is None:                                    # stuck past the limit: hard stop
            self.kill()
            return LimitResult("time", f"RESOURCE LIMIT (time {seconds} s)")
        kind = msg[0]
        if kind == "ok":
            # a worker that came close to its limit is replaced before the next request, so
            # that one scene's leftovers (SymPy's caches) cannot push the next one over
            peak = self.job.peak() if (WINDOWS and self.job is not None) else msg[2]
            if peak >= RECYCLE_AT * self.memory_mb * 1024 * 1024:
                self.served = RECYCLE_AFTER
            return msg[1]
        if kind == "limit":
            if msg[1] == "memory":
                self.kill()
            return LimitResult(msg[1], msg[2])
        if kind == "error":
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


def run_many(target, items, jobs, seconds_of, memory_mb=DEFAULT_MEMORY, on_result=None):
    """Run target(item) for each item on at most `jobs` contained workers at once. seconds_of
    gives each item's time limit. on_result(index, item, result) is called as each one
    finishes; returns the results in item order. Every worker is killed at the end, even
    after Ctrl-C."""
    items = list(items)
    results = [None] * len(items)
    nxt = [0]
    lock = threading.Lock()
    workers = [Worker(memory_mb) for _ in range(max(1, min(jobs, len(items) or 1)))]
    stop = threading.Event()

    def loop(w):
        while not stop.is_set():
            with lock:
                if nxt[0] >= len(items):
                    return
                i = nxt[0]
                nxt[0] += 1
            r = w.call(target, (items[i],), seconds_of(items[i]))
            results[i] = r
            if on_result is not None:
                with lock:
                    on_result(i, items[i], r)

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
    return results
