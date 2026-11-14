"""Run a scene: solve its facts, evaluate its observe block."""
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
        return Scene(yaml.load(fh, Loader=_Loader))


def evaluate(sc, timeout=120):
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
    """Solve, verify, evaluate. Bases per result are left in sc.basis, and the
    independent re-check of every fact in sc.verification."""
    sol = solve_given(sc)
    results, sc.basis = {}, {}
    for name, text in (sc.data.get("observe") or {}).items():
        v, basis = resolve_deferred(sp.sympify(sc.expr(text, check_dims=True)).xreplace(sol).doit())
        if not isinstance(v, sp.logic.boolalg.BooleanAtom):
            v = sp.simplify(v)
        results[name], sc.basis[name] = v, basis
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
        return f"{pretty}  (= {sp.N(v, 6)})"
    return str(v)
