"""Run a scene: solve its facts, evaluate its observe block."""
import copy

import sympy as sp
from .errors import UndeterminedError
import yaml

from .errors import SceneError
from .scene import Scene, resolve_deferred
from .solver import solve_given


class _Loader(yaml.SafeLoader):
    """YAML 1.1 would read on/off/yes/no as booleans (so `on: rope` becomes True: 'rope').
    Only true/false are booleans here."""


_Loader.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:bool"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()}
_Loader.add_implicit_resolver("tag:yaml.org,2002:bool",
                              __import__("re").compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
                              list("tTfF"))


def load(path):
    with open(path, encoding="utf-8") as fh:
        try:
            data = yaml.load(fh, Loader=_Loader)
        except yaml.YAMLError as exc:
            hint = ""
            if "'['" in str(exc) or "flow" in str(exc):
                hint = ("\nhint: inside {...} or [...], quote any value that contains unit brackets, "
                        "e.g. length: \"(3/4)[m]\"")
            raise SceneError(f"the file is not valid YAML: {exc}{hint}") from exc
    return Scene(data)


# scalings of the arbitrary values: two near the stated values and two far away (x1/97, x89), so
# a threshold (max, min, abs, step, a cutoff) between them is crossed; a sampled check, not a proof
ARBITRARY_SCALES = (sp.Rational(137, 100), sp.Rational(61, 100), sp.Rational(1, 97), sp.Integer(89))


def _same_result(a, b):
    if isinstance(a, sp.logic.boolalg.BooleanAtom) or isinstance(b, sp.logic.boolalg.BooleanAtom):
        return a == b
    if isinstance(a, sp.Tuple) or isinstance(b, sp.Tuple):
        return isinstance(a, sp.Tuple) and isinstance(b, sp.Tuple) and len(a) == len(b) and all(
            _same_result(x, y) for x, y in zip(a, b))
    d = sp.simplify(sp.sympify(a) - sp.sympify(b))
    if d == 0:
        return True
    if d.is_number:
        # relative only: SI answers such as intensities (1e-11 W/m^2) are far below any absolute floor
        size = max(abs(complex(sp.N(a, 30))), abs(complex(sp.N(b, 30))))
        return abs(complex(sp.N(d, 30))) <= 1e-9 * size
    return False


RANGE_FRACTIONS = (sp.Rational(37, 100), sp.Rational(61, 100), sp.Rational(3, 100), sp.Rational(97, 100))


def _ranged(rng, k, j, factor):
    """For a ranged arbitrary value: a function value -> value used in run k. With both
    bounds, spread across the open range (3%, 37%, 61%, 97% of the way); with only a lower
    bound, scale the distance above it."""
    lo, hi = rng
    if hi.is_finite:
        frac = _frac(k, j, RANGE_FRACTIONS)
        return lambda v: lo + (hi - lo) * frac
    return lambda v: lo + (v - lo) * factor


def _frac(k, j, fracs):
    """The fraction of the range for name j in run k: a different rotation per name, so
    no two names move together (j and j + len(fracs) differ through the extra offset)."""
    n = len(fracs)
    base = fracs[(k + j) % n]
    if j >= n:
        # shift later names slightly so that they are not proportional to earlier ones
        base = base * sp.Rational(100 - (j // n) * 7 - (k % 3), 100)
    return base


def _evaluate_arbitrary(sc, timeout):
    """Run the scene at the stated arbitrary values and at two other scalings; keep only the
    observables that agree in all three runs."""
    sol, res = _evaluate_once(sc, timeout)
    names = list(sc.arbitrary)
    others = []
    for k, f in enumerate(ARBITRARY_SCALES):
        # each arbitrary value gets its own factor so that no two scale together by accident
        scale = {n: f ** (j + 1) if k == 0 else f * sp.Rational(101 + 7 * j, 100) for j, n in enumerate(names)}
        for j, n in enumerate(names):
            if n in sc.arbitrary_ranges:
                scale[n] = _ranged(sc.arbitrary_ranges[n], k, j, scale[n])
        # (k == 0: powers 1.37, 1.37^2, ...; later runs: one shared factor times 1.01, 1.08, ...)
        try:
            sc2 = Scene(copy.deepcopy(sc.data), scale=scale)
            others.append(_evaluate_once(sc2, timeout) + (sc2, f))
        except SceneError as exc:
            for name in list(res):
                sc.obs_errors[name] = SceneError(f"with other arbitrary values the scene fails ({exc}); the "
                                                 f"answer depends on them")
                res.pop(name)
            return sol, res
    for name in list(res):
        failed = [(f, sc2.obs_errors[name]) for _, r2, sc2, f in others if name not in r2 and name in
                  getattr(sc2, "obs_errors", {})]
        if failed:
            f, exc = failed[0]
            sc.obs_errors[name] = SceneError(f"cannot be shown independent of the arbitrary values: with them "
                                             f"scaled by about x{sp.N(f, 3)} it fails ({exc}); choose arbitrary "
                                             f"values for which every scaling stays valid (e.g. speeds well "
                                             f"below the speed of sound)")
            res.pop(name)
            continue
        if all(name in r2 and _same_result(res[name], r2[name]) for _, r2, _, _ in others):
            how = ("same at 5 values of each arbitrary value (ranged ones spread across their ranges, others "
                   "x0.01 to x89; sampled)" if sc.arbitrary_ranges else
                   "same at 5 scalings of the arbitrary values (x0.01 to x89; sampled)")
            sc.basis[name] = sc.basis.get(name, "exact") + "; " + how
        else:
            sc.obs_errors[name] = SceneError(f"depends on the arbitrary value(s) {names}: the problem does not "
                                             f"fix this result")
            res.pop(name)
    sc.arbitrary_solved = {k: all(k in s2 and _same_result(v, s2[k]) for s2, _, _, _ in others)
                           for k, v in sol.items()}
    _check_comparisons(sc, res, timeout)
    return sol, res


COMPARISON_FRACTIONS = (sp.Rational(1, 1000), sp.Rational(1, 100), sp.Rational(1, 10), sp.Rational(1, 4),
                        sp.Rational(1, 2), sp.Rational(3, 4), sp.Rational(9, 10), sp.Rational(99, 100),
                        sp.Rational(999, 1000))
COMPARISON_SCALES = (sp.Rational(1, 1000), sp.Rational(1, 100), sp.Integer(100), sp.Integer(1000))


def _is_comparison(text):
    import ast
    try:
        return isinstance(ast.parse(str(text).replace("^", "**"), mode="eval").body, ast.Compare)
    except SyntaxError:
        return False


def _check_comparisons(sc, res, timeout):
    """A True/False hides how close a comparison is to flipping, so comparisons get more:
    first a symbolic run over the whole range (a proof when it decides), else many more
    sampled values, close to the ends of every range."""
    comps = [n for n, text in (sc.data.get("observe") or {}).items() if n in res and _is_comparison(text)]
    if not comps:
        return
    names = list(sc.arbitrary)
    data = copy.deepcopy(sc.data)
    data["observe"] = {n: sc.data["observe"][n] for n in comps}
    for key in ("view", "explore", "illustrate"):
        data.pop(key, None)
    # symbolic run: each arbitrary value becomes a positive symbol mapped onto its range
    proved = {}
    try:
        syms = {n: sp.Dummy(n, positive=True) for n in names}

        def mapping(n):
            lo, hi = sc.arbitrary_ranges.get(n, (sp.Integer(0), sp.oo))
            s_ = syms[n]
            if hi.is_finite:
                return lambda v: lo + (hi - lo) * s_ / (1 + s_)
            return lambda v: lo + s_
        sc_sym = Scene(copy.deepcopy(data), scale={n: mapping(n) for n in names})
        _, r_sym = _evaluate_once(sc_sym, min(timeout, 60))
        proved = {n: v for n, v in r_sym.items() if isinstance(v, sp.logic.boolalg.BooleanAtom)}
    except Exception:            # noqa: BLE001 - any failure: fall back to sampling
        proved = {}
    for n in comps:
        if n in proved:
            if not _same_result(proved[n], res[n]):
                sc.obs_errors[n] = SceneError("engine inconsistency between the symbolic and the sampled "
                                              "comparison; please report it")
                res.pop(n)
            else:
                sc.basis[n] = "proved for every allowed arbitrary value"
    todo = [n for n in comps if n in res and n not in proved]
    if not todo:
        return
    runs = []
    for k in range(len(COMPARISON_FRACTIONS)):
        scale = {}
        for j, n in enumerate(names):
            lo, hi = sc.arbitrary_ranges.get(n, (None, None))
            if lo is not None and hi.is_finite:
                fr = COMPARISON_FRACTIONS[(k + 4 * j) % len(COMPARISON_FRACTIONS)]
                scale[n] = (lambda lo_, hi_, fr_: lambda v: lo_ + (hi_ - lo_) * fr_)(lo, hi, fr)
            else:
                f = COMPARISON_SCALES[(k + j) % len(COMPARISON_SCALES)]
                scale[n] = f if lo is None else (lambda lo_, f_: lambda v: lo_ + (v - lo_) * f_)(lo, f)
        runs.append(scale)
    for scale in runs:
        try:
            sc2 = Scene(copy.deepcopy(data), scale=scale)
            _, r2 = _evaluate_once(sc2, timeout)
            errs = getattr(sc2, "obs_errors", {})
        except SceneError as exc:
            r2, errs = {}, {n: exc for n in todo}
        for n in list(todo):
            if n not in res:
                continue
            if n not in r2:
                sc.obs_errors[n] = SceneError(f"cannot be shown to hold for all arbitrary values: near the ends "
                                              f"of the ranges it fails ({errs.get(n)}); give the arbitrary "
                                              f"values a range (below:/above:) that keeps the scene valid")
                res.pop(n)
            elif not _same_result(res[n], r2[n]):
                sc.obs_errors[n] = SceneError(f"depends on the arbitrary value(s) {names}: true for some allowed "
                                              f"values and false for others (not necessarily true)")
                res.pop(n)
    for n in todo:
        if n in res:
            sc.basis[n] = (f"decided; same at {5 + len(runs)} values of the arbitrary values, including near the "
                           f"ends of every range (sampled, not proved)")


def evaluate(sc, timeout=120):
    if getattr(sc, "arbitrary", None):
        return _evaluate_arbitrary(sc, timeout)
    return _evaluate_once(sc, timeout)


def _decide_comparison(sc, text, rels, sol):
    """observe: 'a > b' (or a chain): True or False when decided for all symbol values."""
    from .solver import _sign_ok
    from .doppler import HeardFrequency
    truths = []
    for r in rels:
        lhs, rhs = (sp.sympify(x) for x in (r.lhs, r.rhs))
        if any(isinstance(x, (sp.Tuple, sp.logic.boolalg.BooleanAtom, sp.logic.boolalg.BooleanFunction,
                              sp.core.relational.Relational)) for x in (lhs, rhs)):
            raise SceneError(f"comparison: both sides must be single values (not lists or truths): {text!r}")
        lhs, rhs = lhs.xreplace(sol).doit(), rhs.xreplace(sol).doit()
        d = sp.simplify(lhs - rhs)
        if d.has(HeardFrequency):
            raise SceneError(f"comparison: both sides must be single values: {text!r}")
        if d.is_real is False or (d.is_number and abs(complex(sp.N(d, 30)).imag) > 1e-25):
            raise SceneError(f"comparison: a side is not a real number: {text!r}")
        if r.op == "==":
            if d == 0 or d.is_zero:
                ok = True
            elif d.is_zero is False or (d.is_number and not d.has(sp.Float)):
                # exact numbers: equal only if the difference is exactly 0
                ok = False if d.is_zero is False else (abs(complex(sp.N(d, 50))) < 1e-45)
            elif d.is_number:
                # engine decimals (numeric results): relative tolerance only
                size = max(abs(complex(sp.N(lhs, 30))), abs(complex(sp.N(rhs, 30))))
                ok = abs(complex(sp.N(d, 30))) <= 1e-12 * size
            else:
                ok = None
        else:
            ok = _sign_ok(d, r.op)
        if ok is None:
            raise UndeterminedError(f"cannot decide {text!r} for all symbol values ({sc.show_back(d)} {r.op} 0)")
        truths.append(bool(ok))
    return (sp.true if all(truths) else sp.false), "decided"


def _evaluate_once(sc, timeout=120):
    """Solve and evaluate, with a wall-clock limit where the OS supports it (POSIX)."""
    import signal
    if hasattr(signal, "SIGALRM"):
        def _stop(*_):
            raise SceneError(f"evaluation exceeded {timeout} s; simplify the scene")
        old = signal.signal(signal.SIGALRM, _stop)
        signal.alarm(timeout)
        try:
            return _evaluate(sc)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
    return _evaluate(sc)


def _evaluate(sc):
    try:
        return _evaluate_inner(sc)
    except SceneError:
        raise
    except RecursionError as exc:
        raise SceneError("expression too deeply nested") from exc
    except Exception as exc:          # never show a raw traceback to the author
        raise SceneError(f"engine internal error ({type(exc).__name__}: {exc}); the scene may use a "
                         f"combination the engine cannot handle yet; please report it") from exc


def _evaluate_inner(sc):
    """Solve, verify, evaluate. Bases per result are left in sc.basis, and the
    independent re-check of every fact in sc.verification."""
    from .errors import InconsistentError
    from .scene import harmonic_problem
    sol = solve_given(sc)
    from .doppler import check_solution
    check_solution(sc, sol)
    sc.solution = sol
    results, sc.basis, errors = {}, {}, []
    for name, text in (sc.data.get("observe") or {}).items():
        try:
            parsed = sc.expr(text, allow_rel=True, check_dims=True)
            if isinstance(parsed, list):
                v, basis = _decide_comparison(sc, text, parsed, sol)
            else:
                v, basis = resolve_deferred(sp.sympify(parsed).xreplace(sol).doit())
        except SceneError as exc:
            errors.append((name, exc))
            continue
        except Exception as exc:                       # an engine fault in one observable only
            errors.append((name, SceneError(f"engine internal error ({type(exc).__name__}: {exc}); "
                                            f"please report it")))
            continue
        from .doppler import HeardFrequency
        if isinstance(v, sp.Basic) and v.has(HeardFrequency):
            errors.append((name, SceneError(f"observe.{name}: a heard frequency at the time variable t is a "
                                            f"curve, not a value; give a time, or draw it with a view plot "
                                            f"(vs: t)")))
            continue
        if not isinstance(v, sp.logic.boolalg.BooleanAtom):
            v = sp.simplify(v)
            if isinstance(v, sp.Basic) and not isinstance(v, sp.Tuple) and \
                    v.has(sp.zoo, sp.oo, -sp.oo, sp.nan, sp.AccumBounds):
                errors.append((name, SceneError(f"observe.{name} is infinite or undefined ({v})")))
                continue
        results[name], sc.basis[name] = sc.show_back(v), basis
    why = harmonic_problem(sc, sol, final=True)
    if why:                                   # a whole-scene contradiction, not one observable
        exc = InconsistentError(why)
        exc.partial = (sol, results)
        raise exc
    # an observable that cannot be computed is reported on its own; the others stand
    sc.obs_errors = dict(errors)
    return sol, results


def show(v):
    if isinstance(v, sp.logic.boolalg.BooleanAtom):
        return str(bool(v))
    if v.is_number and not v.is_Integer:
        pretty = v
        if v.has(sp.atan, sp.atan2, sp.acos, sp.asin):        # display only: try rational*pi
            q = sp.nsimplify(sp.N(v / sp.pi, 40), rational=True, tolerance=1e-30)
            if q.q < 10**6 and abs(sp.N(q * sp.pi - v, 40)) < 1e-30:
                pretty = q * sp.pi
        try:
            return f"{pretty}  (= {sp.N(v, 6)})"
        except (ValueError, ArithmeticError, TypeError):
            return str(v)
    return str(v)
