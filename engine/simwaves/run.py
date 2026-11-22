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


def _symbolic_scale(sc):
    """Each arbitrary value as a positive symbol mapped onto its allowed range (all of it):
    (scale for Scene, the symbols)."""
    syms = {n: sp.Dummy(n, positive=True) for n in sc.arbitrary}

    def mapping(n):
        lo, hi = sc.arbitrary_ranges.get(n, (sp.Integer(0), sp.oo))
        s_ = syms[n]
        if hi.is_finite:
            return lambda v: lo + (hi - lo) * s_ / (1 + s_)
        return lambda v: lo + s_
    return {n: mapping(n) for n in sc.arbitrary}, set(syms.values())


def _is_bare_nearest(text):
    """True when the observe text is a single nearest(...) call and nothing around it."""
    import ast
    try:
        body = ast.parse(str(text).replace("^", "**"), mode="eval").body
    except SyntaxError:
        return False
    return isinstance(body, ast.Call) and isinstance(body.func, ast.Name) and body.func.id == "nearest"


def _nearest_proved(sc, names, timeout):
    """The names whose nearest() compares numbers proved independent of the arbitrary
    values: the scene is run once with them as symbols, and every recorded argument must
    simplify to an expression free of those symbols. A pick is discrete, so agreement at
    sampled values proves nothing; anything not proved here is refused."""
    if not names:
        return set()
    data = copy.deepcopy(sc.data)
    data["observe"] = {n: sc.data["observe"][n] for n in names}
    for key in ("view", "explore", "illustrate"):
        data.pop(key, None)
    try:
        scale, syms = _symbolic_scale(sc)
        sc_sym = Scene(data, scale=scale)
        _evaluate_once(sc_sym, min(timeout, 60))
        recorded = getattr(sc_sym, "nearest_args", {})
    except Exception:                  # noqa: BLE001 - no proof: refused by the caller
        return set()
    proved = set()
    numeric = getattr(sc, "nearest_args", {})
    for n in names:
        args, ref = recorded.get(n), numeric.get(n)
        if not args or not ref or len(args) != len(ref):
            continue
        try:
            simp = [[sp.simplify(a) for a in call] for call in args]
            free = set().union(*(a.free_symbols for call in simp for a in call))
            # the proof must agree with the numbers actually compared in the stated run
            agree = all(len(c) == len(r) and all(_same_result(x, y) for x, y in zip(c, r))
                        for c, r in zip(simp, ref))
        except Exception:              # noqa: BLE001
            continue
        if not free and agree:         # every compared number is the same constant: proved
            proved.add(n)
    return proved


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
    proved_nearest = None
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
        # nearest(): the pick is discrete, so agreeing picks prove little; the numbers it
        # compared must themselves be the same at every scaling (as any value must)
        args0 = getattr(sc, "nearest_args", {}).get(name)
        if args0 is not None and not all(
                len(getattr(sc2, "nearest_args", {}).get(name, ())) == len(args0) and
                all(len(a) == len(b) and all(_same_result(x, y) for x, y in zip(a, b))
                    for a, b in zip(args0, sc2.nearest_args[name]))
                for _, _, sc2, _ in others):
            sc.obs_errors[name] = SceneError(f"nearest(): the value it compares depends on the arbitrary "
                                             f"value(s) {names}, so the problem does not fix the option")
            res.pop(name)
            continue
        if args0 is not None:
            # agreement at samples is not enough for a discrete pick: it needs a proof
            if proved_nearest is None:
                proved_nearest = _nearest_proved(
                    sc, [n for n in res if n in getattr(sc, "nearest_args", {})], timeout)
            if name not in proved_nearest:
                sc.obs_errors[name] = SceneError(
                    f"nearest(): cannot prove that the value it compares is independent of the arbitrary "
                    f"value(s) {names} (sampled agreement is not enough for a choice of option); give the "
                    f"value without them, or read the option from the value")
                res.pop(name)
                continue
            if _is_bare_nearest(sc.data["observe"][name]):
                # the observable is the pick itself, and every compared number is proved fixed
                sc.basis[name] = (sc.basis.get(name, "exact") + "; the compared value is proved independent "
                                  "of the arbitrary values")
                continue
            # an expression around a nearest() (e.g. a + nearest(...)) still needs its own check
            # as a whole: the proof covers the pick only
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
MIN_COMPARISON_RUNS = 5        # fewer extra runs that stay physical: the comparison is refused


def _is_comparison(text):
    import ast
    try:
        body = ast.parse(str(text).replace("^", "**"), mode="eval").body
    except SyntaxError:
        return False
    # 'x in cm' parses as a comparison but is a unit conversion, not a True/False result
    return isinstance(body, ast.Compare) and not any(isinstance(op, (ast.In, ast.NotIn)) for op in body.ops)


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
    from .errors import PhysicalRangeError
    skipped = []
    for scale in runs:
        try:
            sc2 = Scene(copy.deepcopy(data), scale=scale)
            _, r2 = _evaluate_once(sc2, timeout)
            errs = getattr(sc2, "obs_errors", {})
        except PhysicalRangeError as exc:
            # this scaling left the physics (e.g. a sound speed in light's range): the
            # comparison has no meaning there, so the run is skipped and the basis says so
            skipped.append(str(exc))
            continue
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
    done = len(runs) - len(skipped)
    if done < MIN_COMPARISON_RUNS:
        for n in todo:
            if n in res:
                sc.obs_errors[n] = SceneError(
                    f"cannot be checked widely enough: only {done} of {len(runs)} extra runs stay physical "
                    f"({skipped[0]}); give the arbitrary values a range (below:/above:)")
                res.pop(n)
        return
    note = (f"; {len(skipped)} far scalings skipped, outside the physical range ({skipped[0]})"
            if skipped else "")
    for n in todo:
        if n in res:
            sc.basis[n] = (f"decided; same at {5 + done} values of the arbitrary values, including near the "
                           f"ends of every range (sampled, not proved){note}")


def evaluate(sc, timeout=120):
    if getattr(sc, "arbitrary", None):
        return _evaluate_arbitrary(sc, timeout)
    return _evaluate_once(sc, timeout)


def _split_unit(sc, name, text):
    """'expr in cm' -> ('expr', ('cm', factor)) after checking the dimension; else (text, None)."""
    import re
    from .expr import dimension_of, show_dim
    from .units import parse_unit
    m = re.match(r"^(.*\S)\s+in\s+([A-Za-zµμ][A-Za-z0-9/^*µμ]*)\s*$", str(text))
    if not m:
        return text, None
    expr_text, unit = m.groups()
    try:
        # the unit is named explicitly after 'in', so parse it directly (split_quantity's
        # rule against a lone trailing 'h' is for field values only)
        factor, udim = parse_unit(unit)
    except SceneError:
        udim = None
    if udim is None:
        raise SceneError(f"observe.{name}: unknown unit '{unit}' after 'in'")
    if "rad" in unit or "deg" in unit.replace("degC", ""):
        # radians carry no dimension, so a frequency and an angular frequency (or a count and
        # an angle) cannot be told apart: angle units are not offered
        raise SceneError(f"observe.{name}: 'in {unit}': angle units cannot be checked (radians have no "
                         f"dimension); give the result in SI")
    import re as _re
    if udim == (0, 0, -1, 0) and _re.search(r"\b(omega|k)\s*\(", expr_text):
        raise SceneError(f"observe.{name}: 'in {unit}' converts frequencies (cycles per second), not angular "
                         f"frequencies; ask frequency(...) instead of omega(...)")
    offset = 0
    if unit == "degC":
        from .units import CELSIUS_OFFSET
        offset = CELSIUS_OFFSET
    got = dimension_of(expr_text, sc)
    if got is None:
        # a bare symbol or unknown: use its recorded dimension
        sym = sc.names.get(expr_text.strip())
        if isinstance(sym, sp.Symbol):
            got = sc.symbol_dims.get(sym)
    if got is None and isinstance(sc.names.get(expr_text.strip()), sp.Symbol):
        got = _dim_from_facts(sc, expr_text.strip(), unit, udim)
    if got is None:
        raise SceneError(f"observe.{name}: cannot check that '{expr_text}' is measured in {unit}; give the "
                         f"result in SI (drop 'in {unit}')")
    if got != udim:
        raise SceneError(f"observe.{name}: '{expr_text}' has dimension {show_dim(got)}, not that of {unit}")
    return expr_text, (unit, factor, offset)


def _dim_from_facts(sc, sym_name, unit, udim):
    """The dimension of an unknown that no field fixes: put one unit of the asked kind in its
    place in every given fact that uses it. If at least one fact then checks and none
    fails, the unit fits."""
    import re
    fits, used = False, False
    for item in sc.data.get("given") or []:
        text = item if isinstance(item, str) else (item.get("fact") if isinstance(item, dict) else None)
        if not isinstance(text, str) or not re.search(rf"\b{re.escape(sym_name)}\b", text):
            continue
        used = True
        trial = re.sub(rf"\b{re.escape(sym_name)}\b", f"(1[{unit}])", text)
        try:
            sc.expr(trial, allow_rel=True, check_dims=True)
            fits = True
        except SceneError as exc:
            if "dimension" in str(exc):
                return None
    return udim if (used and fits) else None


def _decide_cases(d, op):
    """d op 0 through abs/max/min: split into sign cases (piecewise); decided only if every
    feasible case gives the same truth. A case is checked on its own condition when one
    symbol is involved."""
    from .solver import _sign_ok
    pw = sp.piecewise_fold(d.rewrite(sp.Piecewise))
    pieces = pw.args if isinstance(pw, sp.Piecewise) else [(pw, sp.true)]
    truths = set()
    prior = sp.false
    for expr, cond in pieces:
        cond_eff = sp.And(cond, sp.Not(prior))
        prior = sp.Or(prior, cond)
        if cond_eff.simplify() is sp.false:
            continue
        ok = _sign_ok(expr, op)
        if ok is None:
            syms = (expr.free_symbols | cond_eff.free_symbols)
            if len(syms) != 1:
                return None
            x = next(iter(syms))
            try:
                dom = sp.Interval.open(0, sp.oo) if x.is_positive else (
                    sp.Interval(0, sp.oo) if x.is_nonnegative else sp.Reals)
                region = dom.intersect(sp.solveset(cond_eff, x, sp.Reals) if cond_eff is not sp.true else dom)
                if region.is_empty:
                    continue
                rel = {"<": sp.Lt, "<=": sp.Le, ">": sp.Gt, ">=": sp.Ge}[op](expr, 0)
                good = sp.solveset(rel, x, sp.Reals)
                if region.is_subset(good):
                    ok = True
                elif region.intersect(good).is_empty:
                    ok = False
                else:
                    return None
            except (NotImplementedError, TypeError, ValueError):
                return None
        truths.add(bool(ok))
    if len(truths) == 1:
        return truths.pop()
    return None


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
            if ok is None and d.has(sp.Abs, sp.Max, sp.Min):
                ok = _decide_cases(d, r.op)
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


_KIND_WORD = {"positive": "positive", "nonneg": "0 or more", "nonzero": "nonzero", "unit": "between -1 and 1"}


def _check_observe_conditions(sc, name, conditions, sol):
    """Each condition recorded while the observe was read (a log argument positive, a
    denominator nonzero, a wave value at a point inside its profile's domain, ...) must hold
    with the solved values put in. SymPy may have cancelled the part that needed it
    (log(-1) - log(-2) -> -log(2)), so the value alone cannot show this. A condition that
    fails, or cannot be decided, refuses the observable. Conditions on a profile's shape
    (still in the free coordinates x, t) describe where that function is defined, and are not
    required of an observable that is the function itself."""
    from .expr import holds
    from .scene import X, T
    for kind, g in conditions:
        gs = sp.sympify(g).xreplace(sol)
        if gs.has(X, T):
            continue
        h = holds(kind, sp.simplify(gs))
        if h is True:
            continue
        if h is False:
            raise SceneError(f"observe.{name}: not defined: it needs {sc.show_back(gs)} to be {_KIND_WORD[kind]} "
                             f"(a log, root, division, power, tan, asin/acos or wave value written in it fails)")
        raise SceneError(f"observe.{name}: cannot check that it is defined: it needs {sc.show_back(gs)} to be "
                         f"{_KIND_WORD[kind]} for every allowed value of its symbols")


def _check_fact_conditions(sc, sol):
    """The '!= 0' and asin/acos conditions recorded in the given facts (the '> 0' and '>= 0'
    ones are inequalities of the solve) must hold on the solution."""
    from .errors import InconsistentError
    from .expr import holds
    for where, value, kind, g in getattr(sc, "field_conditions", []):
        gs = sp.simplify(sp.sympify(g).xreplace(sol))
        h = holds(kind, gs)
        if h is not True:
            raise SceneError(f"{where}: '{value}' {'is not defined' if h is False else 'cannot be checked'}: a part "
                             f"written in it needs {sc.show_back(gs)} to be {_KIND_WORD[kind]}")
    for i, text, kind, g in getattr(sc, "fact_conditions", []):
        gs = sp.simplify(sp.sympify(g).xreplace(sol))
        h = holds(kind, gs)
        if h is False:
            raise InconsistentError(f"given[{i}] {text!r}: the solution makes it undefined ({sc.show_back(gs)} must "
                                    f"be {_KIND_WORD[kind]})")
        if h is None:
            raise UndeterminedError(f"given[{i}] {text!r}: cannot check that the solution keeps it defined "
                                    f"({sc.show_back(gs)} must be {_KIND_WORD[kind]})")


def _evaluate_inner(sc):
    """Solve, verify, evaluate. Bases per result are left in sc.basis, and the
    independent re-check of every fact in sc.verification."""
    from .errors import InconsistentError
    from .scene import harmonic_problem
    sol = solve_given(sc)
    _check_fact_conditions(sc, sol)
    from .doppler import check_media, check_solution
    check_media(sc, sol)
    check_solution(sc, sol)
    sc.solution = sol
    results, sc.basis, errors = {}, {}, []
    sc.units = {}
    for name, text in (sc.data.get("observe") or {}).items():
        try:
            text, unit = _split_unit(sc, name, text)
            parsed = sc.expr(text, allow_rel=True, check_dims=True, collect=True)
            _check_observe_conditions(sc, name, list(getattr(sc, "last_obligations", [])), sol)
            from .scene import Nearest
            if isinstance(parsed, list):
                if any(sp.sympify(side).has(Nearest) for r in parsed for side in (r.lhs, r.rhs)):
                    raise SceneError(f"observe.{name}: nearest() picks an option; observe it on its own, "
                                     f"not inside a comparison")
                v, basis = _decide_comparison(sc, text, parsed, sol)
            else:
                rec = []
                try:
                    v, basis = resolve_deferred(sp.sympify(parsed).xreplace(sol).doit(), record=rec)
                finally:                   # kept even when refused: the proof run reads them
                    if rec:
                        sc.nearest_args = getattr(sc, "nearest_args", {})
                        sc.nearest_args[name] = rec
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
            # every physical result is real: a value with an imaginary part means a root or log
            # was evaluated outside its domain (sqrt(x - t) at x < t gives I)
            parts = list(v) if isinstance(v, sp.Tuple) else [v]
            if any(isinstance(p, sp.Basic) and (p.is_real is False or (p.is_number and abs(complex(sp.N(p, 30)).imag)
                   > 1e-12 * max(1.0, abs(complex(sp.N(p, 30)))))) for p in parts):
                errors.append((name, SceneError(f"observe.{name} is not a real value ({v}): a root, log or power "
                                                f"is evaluated outside the values where it is defined")))
                continue
        if unit is not None:
            if isinstance(v, sp.logic.boolalg.BooleanAtom):
                errors.append((name, SceneError(f"observe.{name}: a True/False result has no unit")))
                continue
            u, factor, offset = unit
            conv = lambda x: sp.simplify((x - offset) / factor)
            v = sp.Tuple(*[conv(x) for x in v]) if isinstance(v, sp.Tuple) else conv(v)
            sc.units[name] = u
            sc.unit_conv = getattr(sc, "unit_conv", {})
            sc.unit_conv[name] = (factor, offset)
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
