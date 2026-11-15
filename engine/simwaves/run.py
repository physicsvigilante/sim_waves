"""Run a scene: solve its facts, evaluate its observe block."""
import copy

import sympy as sp
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


def _evaluate_arbitrary(sc, timeout):
    """Run the scene at the stated arbitrary values and at two other scalings; keep only the
    observables that agree in all three runs."""
    sol, res = _evaluate_once(sc, timeout)
    names = list(sc.arbitrary)
    others = []
    for k, f in enumerate(ARBITRARY_SCALES):
        # each arbitrary value gets its own factor so that no two scale together by accident
        scale = {n: f ** (j + 1) if k == 0 else f * sp.Rational(101 + 7 * j, 100) for j, n in enumerate(names)}
        # (k == 0: powers 1.37, 1.37^2, ...; later runs: one shared factor times 1.01, 1.08, ...)
        sc2 = Scene(copy.deepcopy(sc.data), scale=scale)
        try:
            others.append(_evaluate_once(sc2, timeout))
        except SceneError as exc:
            for name in list(res):
                sc.obs_errors[name] = SceneError(f"with other arbitrary values the scene fails ({exc}); the "
                                                 f"answer depends on them")
                res.pop(name)
            return sol, res
    for name in list(res):
        if all(name in r2 and _same_result(res[name], r2[name]) for _, r2 in others):
            sc.basis[name] = (sc.basis.get(name, "exact") + "; same at 5 scalings of the arbitrary values (x0.01 to x89; sampled)")
        else:
            sc.obs_errors[name] = SceneError(f"depends on the arbitrary value(s) {names}: the problem does not "
                                             f"fix this result")
            res.pop(name)
    sc.arbitrary_solved = {k: all(k in s2 and _same_result(v, s2[k]) for s2, _ in others) for k, v in sol.items()}
    return sol, res


def evaluate(sc, timeout=120):
    if getattr(sc, "arbitrary", None):
        return _evaluate_arbitrary(sc, timeout)
    return _evaluate_once(sc, timeout)


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
    sc.solution = sol
    results, sc.basis, errors = {}, {}, []
    for name, text in (sc.data.get("observe") or {}).items():
        try:
            v, basis = resolve_deferred(sp.sympify(sc.expr(text, check_dims=True)).xreplace(sol).doit())
        except SceneError as exc:
            errors.append((name, exc))
            continue
        except Exception as exc:                       # an engine fault in one observable only
            errors.append((name, SceneError(f"engine internal error ({type(exc).__name__}: {exc}); "
                                            f"please report it")))
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
