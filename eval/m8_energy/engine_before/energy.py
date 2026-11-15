"""Energy of transverse waves and pulses on strings, time averages, and pulse width.

Per unit length: kinetic (1/2) mu (dy/dt)^2, potential (1/2) T (dy/dx)^2, with mu and T taken
from the wave's string at the point (strings with a coordinate variable included).
"""
import sympy as sp

from .errors import SceneError, UndeterminedError
from .expr import Ref
from .scene import (DIMLESS, LENGTH, OBS_DIMS, OBSERVABLES, TIME, StringMedium, ShapedPulse, T, WAVES, X,
                    _Budget, _obj, _within, dim)

D_ENERGY, D_ELEN = dim(2, 1, -2), dim(1, 1, -2)       # J, J/m


def _string_of(wave, fname):
    meds = [getattr(p, "medium", None) for p in getattr(wave, "parts", [wave])]
    if not meds or any(m is None for m in meds):
        raise UndeterminedError(f"{fname}(): wave '{wave.name}' is not on a string (give `on:`), so mu and T are unknown")
    if any(m is not meds[0] for m in meds):
        raise SceneError(f"{fname}(): the parts of '{wave.name}' are on different strings")
    m = meds[0]
    if not isinstance(m, StringMedium):
        raise SceneError(f"{fname}(): energy is defined here for waves on strings")
    if m.mu is None:
        raise UndeterminedError(f"{fname}(): string '{m.name}' has no mass per length")
    if m.kind == "free":
        raise UndeterminedError(f"{fname}(): string '{m.name}' has tension: free")
    mu = m.mu.xreplace({m.s: X}) if m.var is not None else m.mu
    ten = m.tension(at=X) if not m.uniform else m.tension()
    return m, mu, ten


def _pw(e):
    return sp.piecewise_fold(sp.sympify(e).rewrite(sp.Piecewise))


def _check_continuous(e_x, what):
    """Refuse a field with a jump in x (infinite stretching energy at the jump)."""
    pw = _pw(e_x)
    if not isinstance(pw, sp.Piecewise):
        return
    pts = set()
    for _, c in pw.args:
        for rel in ([c] if isinstance(c, sp.Rel) else list(c.atoms(sp.Rel))):
            roots = sp.solveset(rel.lhs - rel.rhs, X, sp.S.Reals)
            if isinstance(roots, sp.FiniteSet):
                pts.update(roots)
    eps = sp.Rational(1, 10 ** 9)
    for q in pts:
        if not q.is_number:
            continue
        left, right = pw.xreplace({X: q - eps}), pw.xreplace({X: q + eps})
        try:
            if abs(float(sp.N(left - right))) > 1e-6 * (1 + abs(float(sp.N(left))) + abs(float(sp.N(right)))):
                raise SceneError(f"{what}: the shape jumps at x = {q} m, so the string's stretching energy there "
                                 f"is infinite; use a continuous shape")
        except (TypeError, ValueError):
            continue


def _fields(wave, fname):
    f = wave.field()
    if not f.has(X):
        raise SceneError(f"{fname}(): wave '{wave.name}' does not depend on x")
    pwf = _pw(f)
    return pwf, sp.diff(pwf, T), sp.diff(pwf, X)


def _time(wave, t, fname):
    if t is not None:
        return sp.sympify(t)
    if isinstance(wave, ShapedPulse):
        return sp.Integer(0)          # a lone pulse keeps its energy: any instant will do
    raise SceneError(f"{fname}(wave, ..., t=...): give the instant")


def _density(kind):
    def f(sc, w, x=None, t=None):
        fname = f"{kind}_density" if kind != "total" else "energy_density"
        wave = _obj(w, WAVES, fname)
        if x is None or t is None:
            raise SceneError(f"{fname}(wave, x=..., t=...): give both")
        m, mu, ten = _string_of(wave, fname)
        pwf, vy, sl = _fields(wave, fname)
        rep = {X: sp.sympify(x), T: sp.sympify(t)}
        k = (mu * vy ** 2 / 2).xreplace(rep)
        u = (ten * sl ** 2 / 2).xreplace(rep)
        return sp.simplify({"kinetic": k, "potential": u, "total": k + u}[kind])
    return f


def _integrate(e, lo, hi, what):
    def sym():
        return sp.integrate(e, (X, lo, hi))
    try:
        val = _within(30, sym)
        if not val.has(sp.Integral):
            return sp.simplify(val)
    except _Budget:
        pass
    if sp.sympify(e).free_symbols - {X} or lo.free_symbols or hi.free_symbols:
        raise SceneError(f"{what}: the integral has no closed form here; give numbers")
    import mpmath
    fn = sp.lambdify(X, e, modules=["mpmath"])
    return sp.Float(mpmath.quad(fn, [float(lo) if lo.is_finite else -mpmath.inf,
                                     float(hi) if hi.is_finite else mpmath.inf]), 12)


def _energy(kind):
    def f(sc, w, start=None, end=None, t=None):
        fname = {"kinetic": "kinetic_energy", "potential": "potential_energy", "total": "energy"}[kind]
        wave = _obj(w, WAVES, fname)
        m, mu, ten = _string_of(wave, fname)
        t0 = _time(wave, t, fname)
        pwf, vy, sl = _fields(wave, fname)
        _check_continuous(pwf.xreplace({T: t0}), f"{fname}() of '{wave.name}'")
        lo_e, hi_e = getattr(m, "extent", None) or (None, None)
        lo = sp.sympify(start) if start is not None else (lo_e if lo_e is not None else -sp.oo)
        hi = sp.sympify(end) if end is not None else (hi_e if hi_e is not None else sp.oo)
        for pos in (lo, hi):
            if pos.is_finite and pos.is_number and ((lo_e is not None and pos < lo_e) or
                                                    (hi_e is not None and pos > hi_e)):
                raise SceneError(f"{fname}(): x = {pos} m is outside string '{m.name}'")
        if (hi - lo).is_negative:
            lo, hi = hi, lo
        k = (mu * vy ** 2 / 2).xreplace({T: t0})
        u = (ten * sl ** 2 / 2).xreplace({T: t0})
        e = {"kinetic": k, "potential": u, "total": k + u}[kind]
        return _integrate(_pw(e), lo, hi, f"{fname}() of '{wave.name}'")
    return f


def _mean_over(sc, var, e, lo, hi):
    """Average of e over var from lo to hi: (1/(hi - lo)) * integral."""
    if not isinstance(var, sp.Symbol):
        raise SceneError("mean_over(var, expr, lo, hi): first argument must be a variable")
    lo, hi = sp.sympify(lo), sp.sympify(hi)
    span = sp.simplify(hi - lo)
    if span.is_zero or span.is_positive is False:
        raise SceneError("mean_over(): hi must be greater than lo")
    val = _within(30, lambda: sp.integrate(sp.sympify(e), (var, lo, hi)))
    if val.has(sp.Integral):
        raise SceneError("mean_over(): the integral has no closed form")
    return sp.simplify(val / span)


def _width(sc, p):
    """Length of x over which a shaped pulse is non-zero."""
    pulse = _obj(p, (ShapedPulse,), "width")
    pw = _pw(pulse.g)
    if not isinstance(pw, sp.Piecewise):
        raise SceneError(f"width(): pulse '{pulse.name}' never falls to zero (e.g. a Gaussian or Lorentzian); "
                         f"its width is not defined without a threshold")
    taken, support = sp.S.EmptySet, sp.S.EmptySet
    for piece, cond in pw.args:
        cset = cond.as_set() if cond is not sp.true else sp.S.Reals
        region = cset - taken
        taken = taken.union(cset)
        if sp.simplify(piece) != 0:
            support = support.union(region)
    if support.measure.is_infinite or not support.measure.is_number:
        raise SceneError(f"width(): pulse '{pulse.name}' is non-zero over an unbounded region")
    return sp.simplify(support.measure)


OBSERVABLES.update({
    "kinetic_density": _density("kinetic"), "potential_density": _density("potential"),
    "energy_density": _density("total"),
    "kinetic_energy": _energy("kinetic"), "potential_energy": _energy("potential"), "energy": _energy("total"),
    "mean_over": _mean_over, "width": _width,
})
OBS_DIMS.update({
    "kinetic_density": D_ELEN, "potential_density": D_ELEN, "energy_density": D_ELEN,
    "kinetic_energy": D_ENERGY, "potential_energy": D_ENERGY, "energy": D_ENERGY,
    "mean_over": None, "width": LENGTH,
})
