"""Usage:
  python -m simwaves run  <scene.yaml>               evaluate one scene
  python -m simwaves test <folder> [-j N]            run every scene's expect block (N in parallel)
  python -m simwaves view <out.html> <scene.yaml>... build a viewer page from scenes
Options (run, test, view): --time S (default 120 s per request), --memory MB (default 2048).
Each request runs in a contained worker process; one stopped by a limit is reported as
RESOURCE LIMIT, which says nothing about the physics.
"""
import sys

from .errors import SceneError
from .harness import run_dir
from .run import evaluate, load, show


def _round(o):
    if isinstance(o, float):
        return float(f"{o:.5g}")
    if isinstance(o, list):
        return [_round(v) for v in o]
    if isinstance(o, dict):
        return {k: _round(v) for k, v in o.items()}
    return o


def view(out, files, seconds=None, memory_mb=None):
    """Build a viewer page. Each scene is exported as its own contained request under the
    time and memory limits (never multiplied: review 15a G3); the page is written only if
    every scene finished."""
    import json
    import os
    from .contain import CrashResult, LimitResult, run_request
    data = []
    for f in files:
        try:
            r = run_request("simwaves.export:_export_file", (f,), seconds, memory_mb)
        except SceneError as exc:
            print(f"{os.path.basename(f)}: {type(exc).__name__}: {exc}")
            print("no page written")
            return 1
        if isinstance(r, LimitResult):
            print(f"{os.path.basename(f)}: {_limit_text(r)}")
            print("no page written")
            return 3
        if isinstance(r, CrashResult):
            print(f"{os.path.basename(f)}: engine crash: {r.message}")
            print("no page written")
            return 4
        data.append(_round(r))
    tpl = open(os.path.join(os.path.dirname(__file__), "..", "viewer", "template.html"), encoding="utf-8").read()
    # allow_nan=False: a NaN would make the page's JSON unparseable; '<' is escaped so
    # scene text can never close the data block or open an HTML comment inside it.
    blob = json.dumps(data, allow_nan=False).replace("<", "\\u003c")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(tpl.replace("/*DATA*/", blob))
    print(f"wrote {out} ({len(data)} scenes)")
    return 0


def _options(argv):
    """Pull -j/--jobs, --time and --memory out of argv; returns (rest, options) or None."""
    opts, rest, i = {}, [], 0
    names = {"-j": "jobs", "--jobs": "jobs", "--time": "time", "--memory": "memory"}
    while i < len(argv):
        a = argv[i]
        if a in names:
            text = argv[i + 1] if i + 1 < len(argv) else ""
            # ASCII digits only (str.isdigit also accepts '²'), and no conversion of a huge digit
            # string: anything over 40 digits is simply "above 10**40", which every limit refuses
            # with a clear error (review 15a N2)
            if not (text.isascii() and text.isdigit()):
                return None
            # only the significant digits are ever converted (review 15a O1: leading zeros must
            # not reach int(), whose input length Python limits)
            digits = text.lstrip("0") or "0"
            value = int(digits) if len(digits) <= 40 else 10 ** 40 + 1
            if value <= 0:
                return None
            opts[names[a]] = value
            i += 2
            continue
        rest.append(a)
        i += 1
    return rest, opts


def _limit_text(result):
    return (f"{result.message}: the request was stopped before it finished; this says nothing about "
            f"the physics of the scene. Use --time or --memory to change the limits.")


QUALIFIED_SYMPY = "1.12"        # engine/requirements.txt


def main(argv):
    from .contain import DEFAULT_MEMORY, DEFAULT_TIME, CrashResult, LimitResult, run_request
    import sympy
    if sympy.__version__ != QUALIFIED_SYMPY:
        print(f"warning: SymPy {sympy.__version__} is installed; the engine is qualified on SymPy "
              f"{QUALIFIED_SYMPY} (engine/requirements.txt). Results may differ.", file=sys.stderr)
    parsed = _options(argv)
    if parsed is None:
        print(__doc__)
        return 2
    argv, opts = parsed
    seconds, memory = opts.get("time", DEFAULT_TIME), opts.get("memory", DEFAULT_MEMORY)
    from .contain import LimitError, check_limits
    try:
        check_limits(seconds, memory)
    except LimitError as exc:
        print(f"error: {exc}")
        return 2
    if len(argv) >= 3 and argv[0] == "view":
        return view(argv[1], argv[2:], seconds, memory)
    elif len(argv) == 2 and argv[0] == "test":
        counts = run_dir(argv[1], opts.get("jobs"), seconds, memory)
        return 0 if set(counts) <= {"PASS"} else 1
    elif len(argv) == 2 and argv[0] == "run" and "jobs" not in opts:
        r = run_request("simwaves.__main__:_run_text", (argv[1],), seconds, memory)
    else:
        print(__doc__)
        return 2
    if isinstance(r, LimitResult):
        print(_limit_text(r))
        return 3
    if isinstance(r, CrashResult):
        print(f"engine crash: {r.message}")
        return 4
    text, code = r
    print(text, end="", flush=True)
    return code


def _run_text(path):
    """Evaluate one scene and return its printed report and exit code (what a contained
    worker runs for `python -m simwaves run`)."""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _run_one(path)
    return buf.getvalue(), code


def _run_one(path):
    try:
        sc = load(path)
        sol, res = evaluate(sc)
    except SceneError as exc:
        sol_, res_ = getattr(exc, "partial", ({}, {}))
        for k, v in list(sol_.items()) + list(res_.items()):
            print(f"{k} = {show(v)}")
        print(f"{type(exc).__name__}: {exc}")
        return 1
    for k, v in sol.items():
        note = "" if getattr(sc, "arbitrary_solved", {}).get(k, True) else "  (depends on the arbitrary values)"
        print(f"solved {k} = {show(sc.show_back(v))}{note}")
    for k, v in res.items():
        basis = getattr(sc, "basis", {}).get(k, "exact")
        unit = getattr(sc, "units", {}).get(k)
        print(f"{k} = {show(v)}" + (f" {unit}" if unit else "") + ("" if basis == "exact" else f"  <{basis}>"))
    errs = getattr(sc, "obs_errors", {})
    for k, e in errs.items():
        print(f"{k}: NOT AVAILABLE ({type(e).__name__}: {e})")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
