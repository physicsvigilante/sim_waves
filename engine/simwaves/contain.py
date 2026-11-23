"""Containment (m15a): every request runs in its own fresh process under a time and memory limit.

One request, one process (review 15a round 3, option C). The parent owns the request from
admission to the last byte of the reply:
1. **Admission:** the limits are validated (only None selects a default), and a scene file
   larger than MAX_SCENE_BYTES is refused before it is parsed. The request's single
   monotonic deadline starts here, so start-up counts against it.
2. **Ownership from creation:**
   - Windows: the parent joins a kill-on-close supervisor Job Object the first time it starts
     a request, so every child it creates is in that job from the moment it exists, and dies
     with the parent. Each child is created suspended, put in its own job (memory caps,
     kill-on-close) and only then resumed. If any step fails, it is terminated directly.
   - Linux: the child starts in its own session (set before it executes anything). Its first
     act sets the parent-death signal; it exits at once if its parent is already gone. It then
     caps its address space. A guardian process outside the group holds a pipe from the parent
     and kills the whole group when the pipe closes: request over, or parent dead.
3. **Evaluation** in the child under the remaining time (budget.py), from resolving the
   target onwards.
4. **One terminal result** from the parent's own deadline, whatever the child sends: a value,
   the request's own exception (re-raised), a LimitResult or a CrashResult. Anything complete
   only after the deadline is a limit. Past the deadline plus GRACE the tree is killed.
5. **Clean-up:** the child and everything it started are gone before the result is returned.
A limit is reported as such, never as a fact about the physics.
"""
import importlib
import math
import os
import pickle
import struct
import subprocess
import sys
import threading
import time
import traceback

DEFAULT_TIME = 120            # seconds per request (start-up included)
DEFAULT_MEMORY = 2048         # MB per request process
MIN_MEMORY = 256              # MB: the engine needs about 150 MB just to start
MAX_TIME = 1_000_000          # seconds (about 11.6 days): the largest time limit accepted; every
                              # platform's thread waits support it (Windows: about 4.29 million s)
GRACE = 10                    # seconds beyond the time limit before the parent kills
CANCEL_WAIT = 2               # seconds a cancelled set-up is given to finish before the result returns
MAX_SCENE_BYTES = 64 * 1024   # a scene file above this is refused before parsing
MAX_REQUEST_BYTES = 16 * 1024 * 1024   # a request (its pickled arguments) above this is refused
WINDOWS = sys.platform == "win32"
IN_WORKER = False             # True inside a request's process: public entry points run directly
ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class LimitError(ValueError):
    """A limit value that is not a finite positive number of the right type."""


def check_limits(seconds, memory_mb, max_seconds=None, max_memory=None):
    """Validate a time limit (seconds) and a memory limit (MB). Returns (float seconds, int MB).
    Booleans, NaN, infinities, zero, negatives and non-numbers are refused; the time limit is at
    most MAX_TIME (review 15a M2). Memory must be a
    whole number of MB, at least MIN_MEMORY. A maximum, when given, may not be exceeded."""
    def number(v, what):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise LimitError(f"{what} must be a finite positive number, not {v!r}")
        return v
    s = float(number(seconds, "the time limit"))
    if s > MAX_TIME:
        raise LimitError(f"the time limit must be at most {MAX_TIME} s (about 11.6 days), not {seconds!r}")
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


def resolve_limits(seconds=None, memory_mb=None):
    """The limits a caller asked for: None selects the default; any other value, including 0
    or False, is validated as given (review 15a F5). Returns (float seconds, int MB)."""
    return check_limits(DEFAULT_TIME if seconds is None else seconds,
                        DEFAULT_MEMORY if memory_mb is None else memory_mb)


def check_scene_size(path):
    """Refuse a scene file too large to be a scene, before anything parses it."""
    size = os.path.getsize(path)
    if size > MAX_SCENE_BYTES:
        raise LimitError(f"{os.path.basename(path)}: the file is {size} bytes; scene files are limited to "
                         f"{MAX_SCENE_BYTES // 1024} KB")


# ---------------------------------------------------------------- frames on a byte stream
def _write_frame(stream, obj):
    data = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
    stream.write(struct.pack("<Q", len(data)))
    stream.write(data)
    stream.flush()


def _read_exact(stream, n):
    chunks, got = [], 0
    while got < n:
        b = stream.read(n - got)
        if not b:
            raise EOFError("the stream ended")
        chunks.append(b)
        got += len(b)
    return b"".join(chunks)


def _read_frame(stream):
    (n,) = struct.unpack("<Q", _read_exact(stream, 8))
    return pickle.loads(_read_exact(stream, n))


# ---------------------------------------------------------------- the child side
_reply = None                 # the child's reply stream (its real stdout)
_deadline = None              # the child's own deadline (monotonic), for remaining()
_reply_lock = threading.Lock()


def _resolve(target):
    mod, name = target.split(":")
    return getattr(importlib.import_module(mod), name)


def note(obj):
    """In a request's process: send a note to the parent at once (it arrives even if the
    request is later stopped by a limit). Outside one: does nothing."""
    if _reply is not None:
        with _reply_lock:
            _write_frame(_reply, ("note", obj))


def remaining():
    """In a request's process: seconds left before its deadline (None outside one)."""
    return None if _deadline is None else _deadline - time.monotonic()


def _posix_first_steps():
    """Linux, the child's very first steps, before any import: die with the parent; leave at
    once if the parent is already gone (it died before this point)."""
    import signal
    try:
        import ctypes
        ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGKILL)   # PR_SET_PDEATHSIG
    except (OSError, AttributeError):
        pass
    expected = os.environ.get("SIMWAVES_PARENT")
    if expected is not None and os.getppid() != int(expected):
        os._exit(1)


def _cap_memory(memory_mb):
    import resource
    limit = memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def child_main():
    """The request's process: read one request, run it under its time, send one result. On
    Linux its memory cap comes from its command line and is set before the request is read
    (review 15a H4); on Windows the job holds it from before the process runs."""
    global IN_WORKER, _reply, _deadline
    if not WINDOWS:
        _posix_first_steps()
        try:
            _cap_memory(int(sys.argv[1]))
        except (IndexError, ValueError):
            os._exit(2)
    IN_WORKER = True
    _reply = sys.stdout.buffer
    sys.stdout = sys.stderr                               # the target's prints never reach the reply
    for var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(var, "1")
    try:
        target, args, deadline, memory_mb, nominal = _read_frame(sys.stdin.buffer)
    except Exception:                                     # noqa: BLE001 - nothing to run
        os._exit(2)
    _deadline = deadline                                  # the parent's, on the system-wide monotonic clock
    note(("pid", os.getpid()))
    from .budget import within
    from .errors import ResourceLimitError
    try:
        left = max(0.001, _deadline - time.monotonic())
        out = within(left, lambda: _resolve(target)(*args), public=ResourceLimitError("time", f"{nominal:g} s"))
        result = ("ok", out)
    except ResourceLimitError as exc:
        result = ("limit", exc.kind, str(exc))
    except MemoryError:
        result = ("limit", "memory", f"RESOURCE LIMIT (memory {memory_mb} MB)")
    except Exception as exc:                              # noqa: BLE001 - the caller's exception
        try:
            pickle.dumps(exc)
            result = ("raise", exc)
        except Exception:                                 # noqa: BLE001
            result = ("error", traceback.format_exc())
    except BaseException:                                 # noqa: BLE001
        result = ("error", traceback.format_exc())
    try:
        with _reply_lock:
            _write_frame(_reply, result)
    except MemoryError:
        os._exit(3)
    except Exception:                                     # noqa: BLE001 - e.g. the value cannot be pickled
        with _reply_lock:
            _write_frame(_reply, ("error", traceback.format_exc()))
    os._exit(0)


# ---------------------------------------------------------------- Linux guardian
_GUARD = """
import os, signal, sys
pgid, fd = int(sys.argv[1]), int(sys.argv[2])
try:
    while os.read(fd, 1):
        pass
finally:
    for kill in (os.killpg, os.kill):
        try:
            kill(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
"""


class _Guardian:
    """Linux: a small process outside the child's group that kills the whole group when the
    pipe from the parent closes (request over, or parent dead). Constructing it only prepares
    (the pipe and the command), before the request's commit point (review 15a L1). start() is
    the creation call alone, so the request records the guardian the moment it exists; closing
    the parent's copy of the read end comes after that (review 15a M1). Each descriptor is
    closed exactly once, whichever thread gets there first."""

    def __init__(self, pgid):
        self.proc = None
        self._fds = threading.Lock()
        self.rfd, self.wfd = os.pipe()
        self.cmd = [sys.executable, "-c", _GUARD, str(pgid), str(self.rfd)]

    def start(self):
        self.proc = subprocess.Popen(self.cmd, pass_fds=(self.rfd,), start_new_session=True,
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
        return self

    def _take(self, name):
        with self._fds:
            fd = getattr(self, name)
            setattr(self, name, None)
        if fd is not None:
            os.close(fd)

    def _close_read(self):
        """Housekeeping after the guardian is recorded: the parent's copy of the read end."""
        self._take("rfd")

    def fire(self):
        """Close the pipe (the guardian then kills the group and exits) and wait for it, killing
        it if it does not exit; a guardian never started only has its pipe closed. Safe to call
        more than once, and while another thread is still in its housekeeping."""
        self._take("wfd")
        if self.proc is not None:
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self._take("rfd")


# ---------------------------------------------------------------- Windows Job Objects
class _Win:
    """kernel32/ntdll entry points and the job structures."""
    _ready = None

    @classmethod
    def get(cls):
        if cls._ready is None:
            import ctypes
            from ctypes import wintypes
            k = ctypes.WinDLL("kernel32", use_last_error=True)
            k.CreateJobObjectW.restype = wintypes.HANDLE
            k.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
            k.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
            k.QueryInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                                                    ctypes.c_void_p)
            k.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
            k.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
            k.CloseHandle.argtypes = (wintypes.HANDLE,)
            k.GetCurrentProcess.restype = wintypes.HANDLE
            nt = ctypes.WinDLL("ntdll")
            nt.NtResumeProcess.argtypes = (wintypes.HANDLE,)

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
            cls._ready = (ctypes, k, nt, Extended)
        return cls._ready


class _Job:
    """A Windows Job Object with kill-on-close (and, given memory_mb, memory caps)."""

    def __init__(self, memory_mb=None):
        ct, k, _, Extended = _Win.get()
        self.ct, self.k, self.Extended = ct, k, Extended
        self.h = k.CreateJobObjectW(None, None)
        if not self.h:
            raise OSError(ct.get_last_error(), "CreateJobObject failed")
        info = Extended()
        flags = 0x2000                                    # KILL_ON_JOB_CLOSE
        if memory_mb is not None:
            flags |= 0x0100 | 0x0200                      # PROCESS_MEMORY, JOB_MEMORY
            info.ProcessMemoryLimit = info.JobMemoryLimit = memory_mb * 1024 * 1024
        info.BasicLimitInformation.LimitFlags = flags
        if not k.SetInformationJobObject(self.h, 9, ct.byref(info), ct.sizeof(info)):
            raise OSError(ct.get_last_error(), "SetInformationJobObject failed")

    def assign_handle(self, handle):
        if not self.k.AssignProcessToJobObject(self.h, handle):
            raise OSError(self.ct.get_last_error(), "AssignProcessToJobObject failed")

    def peak(self):
        info = self.Extended()
        if self.h and self.k.QueryInformationJobObject(self.h, 9, self.ct.byref(info), self.ct.sizeof(info), None):
            return max(info.PeakProcessMemoryUsed, info.PeakJobMemoryUsed)
        return 0

    def close(self):
        if self.h:
            self.k.TerminateJobObject(self.h, 1)
            self.k.CloseHandle(self.h)
            self.h = None


_supervisor = None
_supervisor_lock = threading.Lock()


def _ensure_supervisor():
    """Windows: put this process in a kill-on-close job, once. Every child created afterwards
    is in that job from creation, so it cannot outlive this process, whatever happens between
    its creation and its own job. Returns False if Windows refuses (then a child is owned only
    from the moment it is assigned its own job, while still suspended)."""
    global _supervisor
    with _supervisor_lock:
        if _supervisor is None:
            try:
                job = _Job()
                _, k, _, _ = _Win.get()
                job.assign_handle(k.GetCurrentProcess())
                _supervisor = job                         # kept open for this process's lifetime
            except OSError:
                _supervisor = False
        return bool(_supervisor)


# ---------------------------------------------------------------- the parent side
class LimitResult:
    """The request was stopped by a limit: kind 'time' or 'memory'."""

    def __init__(self, kind, message, notes=()):
        self.kind, self.message, self.notes = kind, message, list(notes)

    def __repr__(self):
        return self.message


class CrashResult:
    """The request has no result: its process failed to start, died, or the runner failed."""

    def __init__(self, message, notes=()):
        self.message, self.notes = message, list(notes)

    def __repr__(self):
        return self.message


class _Cancelled(Exception):
    """The request was cancelled (timed out or interrupted) while its process was being set up."""


class _Request:
    """One running request: the child process and its owners, with one state shared by set-up
    and clean-up (review 15a I1, K1, L1).

    The state (cancelled; a creation step in progress) changes only under one lock. Every step
    that creates a process, or lets one run, passes a commit point: under the lock, it either
    sees the cancel and stops, or marks itself in progress. kill() marks the request cancelled
    under the same lock. So each creation step either committed before the cancel or never
    begins: once kill() has set the cancel, no step can start a process. Everything that can
    be slow (the environment, the supervisor job, the child's job, the guardian's pipe) is
    prepared before the commit point; after it there is only the creation call itself.

    kill() waits at most CANCEL_WAIT for a step that committed before the cancel. If that step
    is still in progress then (its creation call stalled: the declared J1 case, which covers a
    creation committed before the cancel), what it creates is killed as soon as it returns,
    and it never receives the request."""

    def __init__(self, memory_mb):
        self.memory_mb = memory_mb
        self.popen = self.job = self.guard = None
        self._cond = threading.Condition(threading.Lock())
        self._cancelled = False
        self._creating = False

    @property
    def cancelled(self):
        with self._cond:
            return self._cancelled

    def _step(self, name, make):
        """Commit, then run make() (one creation call, nothing slow), then record its result as
        `name` (None: record nothing). Raises _Cancelled if the request was cancelled before the
        commit, or while the step was in progress (then what it made is killed first)."""
        with self._cond:
            if self._cancelled:
                raise _Cancelled("the request was cancelled before this set-up step")
            self._creating = True                         # the commit point
        obj = None
        try:
            obj = make()
        finally:
            with self._cond:
                if name is not None and obj is not None:
                    setattr(self, name, obj)
                self._creating = False
                late = self._cancelled
                self._cond.notify_all()
        if late:                                          # cancelled while the step was in progress
            self.kill()
            raise _Cancelled("the request was cancelled during set-up")
        return obj

    def launch(self):
        if self.cancelled:
            raise _Cancelled("the request was cancelled before its process was started")
        # preparation: everything that may be slow happens before any commit point
        cmd = [sys.executable, "-m", "simwaves.child", str(self.memory_mb)]
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([ENGINE_DIR] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        env["SIMWAVES_PARENT"] = str(os.getpid())
        pipes = dict(stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if WINDOWS:
            if not _ensure_supervisor():
                # without the supervisor job a child could outlive this process if it died
                # before the child's own job was assigned: refuse (review 15a H1)
                raise OSError("Windows refused to put this process in a job; a request's process could "
                              "outlive it, so none is started")
            self._step("popen", lambda: subprocess.Popen(cmd, env=env, creationflags=0x00000004 | 0x08000000,
                                                         **pipes))                 # SUSPENDED, NO_WINDOW
            job = None
            try:
                job = _Job(self.memory_mb)                # prepared: no process is created by it

                def assign():
                    job.assign_handle(int(self.popen._handle))
                    return job
                self._step("job", assign)

                def resume():                             # let it run only if still wanted
                    _, _, nt, _ = _Win.get()
                    if nt.NtResumeProcess(int(self.popen._handle)) != 0:
                        raise OSError("NtResumeProcess failed")
                self._step(None, resume)
            except BaseException:
                if job is not None:
                    job.close()                           # safe if kill() closed it already
                self.kill()
                raise
        else:
            self._step("popen", lambda: subprocess.Popen(cmd, env=env, start_new_session=True, **pipes))
            guard = None
            try:
                guard = _Guardian(self.popen.pid)         # prepared: the pipe, no process yet
                self._step("guard", guard.start)          # recorded the moment it exists
                guard._close_read()                       # housekeeping, after it is recorded
            except BaseException:
                if guard is not None:
                    guard.fire()                          # safe if kill() fired it already
                self.kill()
                raise

    def kill(self):
        """Cancel the request, kill its process and everything it started, and wait for it.
        Safe to call more than once, and from any thread."""
        with self._cond:
            self._cancelled = True                        # no step can commit after this
            if self._creating:                            # one committed before the cancel
                self._cond.wait_for(lambda: not self._creating, timeout=CANCEL_WAIT)
            job, popen, guard = self.job, self.popen, self.guard
            self.job = self.guard = None
        if job is not None:
            job.close()
        if popen is not None:
            if not WINDOWS:
                import signal
                try:
                    os.killpg(popen.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            try:
                popen.kill()
            except OSError:
                pass
            try:
                popen.wait(10)
            except subprocess.TimeoutExpired:
                pass
        if guard is not None:
            guard.fire()


_PLAIN_NODES = 2_000_000       # at most this many items in a request's data
_PLAIN_TYPES = (dict, list, tuple, str, bytes, bytearray, int, float, bool, type(None))


class _TooBig(Exception):
    pass


class _CappedBuffer:
    """A pickler's sink that keeps the bytes and stops as soon as they pass the limit."""

    def __init__(self, limit):
        self.limit, self.data = limit, bytearray()

    def write(self, b):
        if len(self.data) + len(b) > self.limit:
            raise _TooBig()
        self.data += b
        return len(b)


def _request_bytes(obj, limit):
    """The request frame serialised once, exactly as it will be sent, or None if it would pass
    `limit` bytes (review 15a J3, K2: what is checked is what is sent, so later changes to the
    caller's data cannot matter). The data must be plain: exactly the built-in types dict, list,
    tuple, str, bytes, bytearray, int, float, bool and None, no subclasses (review 15a O1), at
    most _PLAIN_NODES items. It is checked without copying, then serialised into a buffer that
    stops at the limit."""
    nodes, stack = 0, [obj]
    while stack:
        o = stack.pop()
        nodes += 1
        if nodes > _PLAIN_NODES:
            return None
        t = type(o)
        if t not in _PLAIN_TYPES:
            raise TypeError(f"a request carries plain data only (dicts, lists, strings, numbers), not {t.__name__}")
        if t in (list, tuple):
            stack.extend(o)
        elif t is dict:
            for k, v in o.items():
                stack.append(k)
                stack.append(v)
    buf = _CappedBuffer(limit)
    try:
        pickle.Pickler(buf, protocol=pickle.HIGHEST_PROTOCOL).dump(obj)
    except _TooBig:
        return None
    return bytes(buf.data)


class _Registry:
    """run_many's requests, with one stop state (review 15a J2). A request joins before any of
    its work (its data check included); once stopped, nothing can join, and every request that
    joined is cancelled, so none can start a process after the stop."""

    def __init__(self):
        self._lock = threading.Lock()
        self._reqs = set()
        self.stopped = False

    def join(self, req):
        with self._lock:
            if self.stopped:
                return False
            self._reqs.add(req)
            return True

    def leave(self, req):
        with self._lock:
            self._reqs.discard(req)

    def stop(self):
        with self._lock:
            self.stopped = True
            reqs = list(self._reqs)
        for req in reqs:
            req.kill()

    def active(self):
        with self._lock:
            return list(self._reqs)


def run_request(target, args=(), seconds=None, memory_mb=None, _registry=None):
    """Run target(*args) in a fresh contained process. Returns its value, a LimitResult or a
    CrashResult, or re-raises the request's own exception. The deadline starts now, before the
    process exists. The process and everything it started are gone when this returns (see the
    PLAN's containment class for the one documented exception). A request carries plain data
    only, at most MAX_REQUEST_BYTES as sent. `_registry` (run_many's) cancels requests together."""
    seconds, memory_mb = resolve_limits(seconds, memory_mb)
    t0 = time.monotonic()
    deadline = t0 + seconds
    req = _Request(memory_mb)
    if _registry is not None and not _registry.join(req):
        return CrashResult("the request was cancelled before it started")
    try:
        # the request's data is checked (plain, exact byte count) before any process exists
        # (review 15a H4, O1, J3)
        # the whole frame, deadline included (as a time on the system-wide monotonic clock), is
        # serialised once here; exactly these bytes are sent (review 15a K2)
        try:
            frame = _request_bytes((target, tuple(args), deadline, memory_mb, seconds), MAX_REQUEST_BYTES)
        except TypeError as exc:
            return CrashResult(f"the request cannot be sent: {exc}")
        if frame is None:
            return LimitResult("memory", f"RESOURCE LIMIT (request over {MAX_REQUEST_BYTES // (1024 * 1024)} MB "
                                         f"as sent)")
        if req.cancelled:
            return CrashResult("the request was cancelled before it started")
        return _run(req, frame, seconds, memory_mb, deadline)
    except MemoryError:
        req.kill()
        return LimitResult("memory", "RESOURCE LIMIT (memory: the request's data could not be prepared)")
    except BaseException:
        # anything else (the request's own exception, an interrupt, an unexpected runner
        # error): cancel the request and remove its processes before passing it on (review 15a M2)
        req.kill()
        raise
    finally:
        if _registry is not None:
            _registry.leave(req)


def _run(req, frame, seconds, memory_mb, deadline):
    notes, box, tail = [], {}, []

    # launching runs under the same deadline (review 15a H3): a set-up that hangs ends at the
    # hard stop, and one that fails after the deadline is a limit, not a crash
    started = {}

    def start():
        try:
            req.launch()
            started["ok"] = True
        except BaseException as exc:                      # noqa: BLE001 - classified below
            started["error"] = exc
    launcher = threading.Thread(target=start, daemon=True)
    launcher.start()
    launcher.join(max(0.0, deadline + GRACE - time.monotonic()))
    if launcher.is_alive():
        # cancel: from now no set-up step can commit, so none can start a process; one that
        # committed before the cancel is waited for briefly, and what it creates is killed the
        # moment it returns (review 15a I1, L1)
        req.kill()
        launcher.join(CANCEL_WAIT)
        req.kill()
        return LimitResult("time", f"RESOURCE LIMIT (time {seconds:g} s)")
    if req.cancelled and "error" in started:              # cancelled from outside (run_many on Ctrl-C)
        return CrashResult("the request was cancelled")
    if "error" in started:
        req.kill()
        if time.monotonic() > deadline:
            return LimitResult("time", f"RESOURCE LIMIT (time {seconds:g} s)")
        exc = started["error"]
        return CrashResult(f"the request's process could not start ({type(exc).__name__}: {exc})")

    def drain_stderr():                                   # never let a full stderr pipe block the child
        try:
            for line in iter(req.popen.stderr.readline, b""):
                tail.append(line.decode("utf-8", "replace"))
                del tail[:-40]
        except (OSError, ValueError):
            pass

    def transfer():
        try:
            req.popen.stdin.write(struct.pack("<Q", len(frame)))
            req.popen.stdin.write(frame)                   # exactly the bytes checked at admission
            req.popen.stdin.flush()
            req.popen.stdin.close()
            while True:
                reply = _read_frame(req.popen.stdout)
                if reply[0] == "note":
                    notes.append(reply[1])
                    continue
                box["msg"] = reply
                return
        except (EOFError, OSError, ValueError):
            box["msg"] = ("died",)
        except BaseException as exc:                      # noqa: BLE001 - a result, not a hang
            box["msg"] = ("transport", f"{type(exc).__name__}: {exc}")
    err = threading.Thread(target=drain_stderr, daemon=True)
    io = threading.Thread(target=transfer, daemon=True)
    err.start()
    io.start()
    io.join(max(0.0, deadline + GRACE - time.monotonic()))
    if io.is_alive():                                     # no complete reply by the hard stop
        req.kill()
        io.join(10)
        return LimitResult("time", f"RESOURCE LIMIT (time {seconds:g} s)", notes)
    arrived = time.monotonic()
    msg = box.get("msg", ("died",))
    peak = req.job.peak() if req.job is not None else 0
    try:
        code = req.popen.wait(5)
    except subprocess.TimeoutExpired:
        code = None
    req.kill()                                            # whatever the outcome: the tree is gone
    kind = msg[0]
    if kind == "limit":
        return LimitResult(msg[1], msg[2], notes)
    if arrived > deadline:                                # complete only after its time: a limit
        return LimitResult("time", f"RESOURCE LIMIT (time {seconds:g} s)", notes)
    if kind == "ok":
        return msg[1]
    if kind == "raise":
        raise msg[1]
    if kind == "error":
        return CrashResult(msg[1], notes)
    if kind == "transport":
        return CrashResult(f"the reply could not be received ({msg[1]})", notes)
    if peak >= 0.9 * memory_mb * 1024 * 1024 or code in (3, -9):
        return LimitResult("memory", f"RESOURCE LIMIT (memory {memory_mb} MB)", notes)
    return CrashResult(f"the request's process ended unexpectedly (exit code {code})"
                       + (": " + "".join(tail[-8:]).strip() if tail else ""), notes)


def call_bounded(target, args=(), seconds=None, memory_mb=None):
    """The bounded form of a public entry point. Inside a request's process the target runs
    directly (already contained). Outside, it runs as its own request. A limit or a crash is
    raised (ResourceLimitError, RuntimeError), so a direct caller cannot take it for a value."""
    seconds, memory_mb = resolve_limits(seconds, memory_mb)
    if IN_WORKER:
        return _resolve(target)(*args)
    from .errors import ResourceLimitError
    r = run_request(target, args, seconds, memory_mb)
    if isinstance(r, LimitResult):
        raise ResourceLimitError(r.kind, f"{seconds:g} s" if r.kind == "time" else f"{memory_mb} MB")
    if isinstance(r, CrashResult):
        raise RuntimeError(r.message)
    return r


def run_many(target, items, jobs, seconds, memory_mb=None, on_result=None):
    """Run target(item) for each item, each as its own request, at most `jobs` at once. Every
    item gets exactly one result (a value, a LimitResult or a CrashResult). on_result(index,
    item, result) is called once per item. Returns the results in item order. On Ctrl-C the
    running requests are stopped and their processes killed."""
    items = list(items)
    results = [None] * len(items)
    reported = [False] * len(items)
    nxt = [0]
    lock = threading.Lock()
    stop = threading.Event()
    registry = _Registry()                                # the requests running now (review 15a I2, J2)

    def report(i, r):
        with lock:
            if reported[i]:
                return
            results[i], reported[i] = r, True
            if on_result is not None and not stop.is_set():   # no callbacks after an interrupt
                on_result(i, items[i], r)

    def loop():
        while not stop.is_set():
            with lock:
                if nxt[0] >= len(items):
                    return
                i = nxt[0]
                nxt[0] += 1
            try:
                r = run_request(target, (items[i],), seconds, memory_mb, _registry=registry)
            except BaseException as exc:                  # noqa: BLE001 - every item gets a result
                r = CrashResult(f"the runner failed on this item ({type(exc).__name__}: {exc})")
            report(i, r)

    threads = [threading.Thread(target=loop, daemon=True) for _ in range(max(1, min(jobs, len(items) or 1)))]
    try:
        for t in threads:
            t.start()
        while any(t.is_alive() for t in threads):
            for t in threads:
                t.join(0.2)
    except KeyboardInterrupt:
        # cancel every running request, kill its processes, and wait for the runner threads,
        # before passing the interrupt on (review 15a I2)
        # stop admitting, cancel every request that has joined (whatever stage it is at), and wait
        # for the runner threads: a request can no longer start a process after this
        stop.set()
        registry.stop()
        for t in threads:
            t.join(GRACE + CANCEL_WAIT + 15)
        registry.stop()
        raise
    finally:
        for i in range(len(items)):
            if not reported[i]:
                report(i, CrashResult("never run (the runner stopped before reaching it)"))
    return results
