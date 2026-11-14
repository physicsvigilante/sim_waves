"""Test harness: compare engine results with the book answers in a scene's `expect` block.

`expect` is never read by the engine itself.
"""
import glob
import os
import traceback

import sympy as sp

from .errors import AmbiguousError, InconsistentError, SceneError, UndeterminedError
from .run import evaluate, load, show
from .scene import equivalent
from .units import split_quantity

ERRORS = {"inconsistent": InconsistentError, "ambiguous": AmbiguousError,
          "undetermined": UndeterminedError, "rejected": SceneError}


def _parse_expected(sc, value):
    text, _, factor, _ = split_quantity(value)
    return sp.sympify(sc.expr(text)) * factor


def _tol(spec):
    if spec is None:
        return 1e-9
    s = str(spec).strip()
    return float(s[:-1]) / 100 if s.endswith("%") else float(s)


def check(sc, got, exp):
    """Return (ok, detail)."""
    tol = None
    if isinstance(exp, dict):
        tol, exp = exp.get("tol"), exp.get("value")
    if isinstance(exp, bool):
        ok = isinstance(got, sp.logic.boolalg.BooleanAtom) and bool(got) == exp
        return ok, ""
    s = str(exp).strip()
    if s == "even integer":
        q = sp.simplify(got / 2)
        return bool(q.is_integer) or (q.is_number and abs(float(q) - round(float(q))) < 1e-9), ""
    if s.startswith("(") and s.endswith(")") and (s.count(",") or s == "()"):
        items = [i for i in s[1:-1].split(",") if i.strip()]
        if not isinstance(got, sp.Tuple) or len(got) != len(items):
            return False, f"want {s}"
        return all(check(sc, g, i)[0] for g, i in zip(got, items)), f"want {s}"
    if s[:1] in "<>":
        target = _parse_expected(sc, s[1:])
        d = sp.simplify(got - target)
        return bool(d.is_positive if s[0] == ">" else d.is_negative), ""
    want = _parse_expected(sc, s)
    if isinstance(got, sp.logic.boolalg.BooleanAtom):
        return False, "got a truth value"
    if got.is_number and want.is_number:
        g, w = complex(sp.N(got)), complex(sp.N(want))
        return abs(g - w) <= _tol(tol) * max(1.0, abs(w)), f"want {sp.N(want, 6)}"
    return equivalent(got, want), f"want {want}"


def run_file(path):
    lines, status = [], "PASS"
    name = os.path.basename(path)
    import yaml
    with open(path, encoding="utf-8") as fh:
        expect = (yaml.safe_load(fh) or {}).get("expect") or {}
    if "error" in expect:
        kind = ERRORS[expect["error"]]
        try:
            evaluate(load(path))
        except kind as exc:
            want = expect.get("message")
            if want and want not in str(exc):
                return "FAIL", [f"{name}: rejected, but not for the expected reason "
                                f"({want!r}): {type(exc).__name__}: {exc}"]
            return "PASS", [f"{name}: rejected as expected ({expect['error']}): {exc}"]
        except SceneError as exc:
            return "FAIL", [f"{name}: wrong rejection: {type(exc).__name__}: {exc}"]
        return "FAIL", [f"{name}: expected {expect['error']} but the scene ran"]
    try:
        sc = load(path)
    except SceneError as exc:
        return "ERROR", [f"{name}: scene rejected: {exc}"]
    try:
        sol, res = evaluate(sc)
    except SceneError as exc:
        return "FAIL", [f"{name}: {type(exc).__name__}: {exc}"]
    except Exception:  # engine bug
        return "CRASH", [f"{name}: engine crashed\n{traceback.format_exc()}"]
    if sol:
        lines.append(f"{name}: solved " + ", ".join(f"{k}={show(v)}" for k, v in sol.items()))
    ver = getattr(sc, "verification", [])
    if ver:
        kinds = {}
        for _, _, b in ver:
            kinds[b] = kinds.get(b, 0) + 1
        lines.append("  re-checked facts: " + ", ".join(f"{v} {k}" for k, v in sorted(kinds.items())))
    for key, exp in expect.items():
        if key not in res:
            lines.append(f"  {key}: no such observable")
            status = "FAIL"
            continue
        ok, detail = check(sc, res[key], exp)
        disputed = isinstance(exp, dict) and exp.get("status") == "disputed"
        tag = "ok" if ok else "MISMATCH"
        if disputed:
            tag += f" (book disputed: {exp.get('book')}, {exp.get('why')})"
        if not ok:
            status = "FAIL"
        basis = getattr(sc, "basis", {}).get(key, "exact")
        btag = "" if basis == "exact" else f" <{basis}>"
        lines.append(f"  {key} = {show(res[key])}{btag}  [{tag}] {detail if not ok else ''}".rstrip())
    return status, lines


def run_dir(path):
    files = sorted(glob.glob(os.path.join(path, "*.yaml")))
    counts = {}
    for f in files:
        status, lines = run_file(f)
        counts[status] = counts.get(status, 0) + 1
        print(f"[{status}] " + "\n".join(lines))
    print("\nsummary: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    return counts
