"""Energy of transverse waves and pulses on strings, time averages, and pulse width.

Per unit length: kinetic (1/2) mu (dy/dt)^2, potential (1/2) T (dy/dx)^2, with mu and T taken
from the wave's string at the point (strings with a coordinate variable included).
"""
import sympy as sp

from .errors import SceneError, UndeterminedError
from .scene import (LENGTH, OBS_DIMS, OBSERVABLES, StringMedium, ShapedPulse, T, WAVES, X,
                    _Budget, _check_wave_x, _obj, _within, dim)

D_ENERGY, D_ELEN = dim(2, 1, -2), dim(1, 1, -2)       # J, J/m
SYMBOLIC_BUDGET = 10                                 # seconds before a numerical integral is used


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


def _breakpoints(pw, lo, hi, what):
    """Breakpoints in x of a Piecewise expression inside [lo, hi] (numbers only)."""
    if not isinstance(pw, sp.Piecewise):
        return []
    region = sp.Interval(lo, hi)
    pts = set()
    for _, c in pw.args:
        for rel in ([c] if isinstance(c, sp.Rel) else list(c.atoms(sp.Rel))):
            d = rel.lhs - rel.rhs
            if not d.has(X):
                continue
            if d.free_symbols - {X}:
                raise SceneError(f"{what}: the shape has a corner or edge at a symbolic position, so its "
                                 f"continuity cannot be checked; give numbers (including the instant)")
            roots = sp.solveset(d, X, region)
            if roots is sp.S.EmptySet:
                continue
            if not isinstance(roots, sp.FiniteSet):
                raise SceneError(f"{what}: the shape has infinitely many corners or edges in the range; "
                                 f"cannot check it")
            pts.update(roots)
    return sorted(pts, key=lambda q: float(sp.N(q)))


def _side_piece(pw, q, side):
    """The Piecewise branch that applies just left (-1) or right (+1) of q."""
    probe = q + side * sp.Rational(1, 10 ** 12)
    for expr, cond in pw.args:
        try:
            if bool(cond.xreplace({X: probe})):
                return expr
        except TypeError:
            continue
    return None


def _check_continuous(pw, lo, hi, what):
    """Refuse a field with a jump in x (infinite stretching energy at the jump); compares the
    two one-sided branches exactly at each breakpoint."""
    for q in _breakpoints(pw, lo, hi, what):
        a, b = _side_piece(pw, q, -1), _side_piece(pw, q, +1)
        if a is None or b is None:
            continue
        if sp.simplify(a.xreplace({X: q}) - b.xreplace({X: q})) != 0:
            raise SceneError(f"{what}: the shape jumps at x = {q} m, so the string's stretching energy there "
                             f"is infinite; use a continuous shape")


def _fields(wave, fname):
    f = wave.field()
    if not f.has(X):
        raise SceneError(f"{fname}(): wave '{wave.name}' does not depend on x")
    pwf = _pw(f)
    return pwf, sp.diff(pwf, T), sp.diff(pwf, X)


def _density(kind):
    def f(sc, w, x=None, t=None):
        fname = f"{kind}_density" if kind != "total" else "energy_density"
        wave = _obj(w, WAVES, fname)
        if x is None or t is None:
            raise SceneError(f"{fname}(wave, x=..., t=...): give both")
        _check_wave_x(wave, x)
        m, mu, ten = _string_of(wave, fname)
        pwf, vy, sl = _fields(wave, fname)
        xv, tv = sp.sympify(x), sp.sympify(t)
        at_t = pwf.xreplace({T: tv})
        if xv.is_number and isinstance(at_t, sp.Piecewise):
            if any(sp.simplify(q - xv) == 0 for q in _breakpoints(at_t, xv - 1, xv + 1, f"{fname}()")):
                da, db = (_side_piece(sp.diff(at_t, X), xv, s) for s in (-1, 1))
                if da is not None and db is not None and sp.simplify((da - db).xreplace({X: xv})) != 0:
                    raise SceneError(f"{fname}(): x = {xv} m is a corner of the shape, where the slope (and the "
                                     f"stretching energy density) is not defined; ask just beside it")
        rep = {X: xv, T: tv}
        k = (mu * vy ** 2 / 2).xreplace(rep)
        u = (ten * sl ** 2 / 2).xreplace(rep)
        return sp.simplify({"kinetic": k, "potential": u, "total": k + u}[kind])
    return f


def _numeric_integral(pw, lo, hi):
    """Integral of a numeric (piecewise) expression, split at its breakpoints; a decimal."""
    import mpmath
    mpmath.mp.dps = 30
    pts = [lo] + [q for q in _breakpoints(pw, lo, hi, "integral") if lo < q < hi] + [hi]
    total = mpmath.mpf(0)
    for a, b in zip(pts, pts[1:]):
        mid = (a + b) / 2 if a.is_finite and b.is_finite else (a + 1 if a.is_finite else (b - 1 if b.is_finite else 0))
        piece = _side_piece(pw, mid, 0) if isinstance(pw, sp.Piecewise) else pw
        if piece is None or sp.simplify(piece) == 0:
            continue
        fn = sp.lambdify(X, piece, modules=["mpmath"])
        total += mpmath.quad(fn, [mpmath.mpf(float(a)) if a.is_finite else -mpmath.inf,
                                  mpmath.mpf(float(b)) if b.is_finite else mpmath.inf], maxdegree=10)
    return sp.Float(total, 12)


def _integrate(e, lo, hi, what):
    try:
        val = _within(SYMBOLIC_BUDGET, lambda: sp.integrate(e, (X, lo, hi)))
        if not val.has(sp.Integral):
            return sp.simplify(val)
    except _Budget:
        pass
    if sp.sympify(e).free_symbols - {X} or lo.free_symbols or hi.free_symbols:
        raise SceneError(f"{what}: the integral has no closed form here; give numbers")
    return _numeric_integral(_pw(e), lo, hi)


def _energy(kind):
    def f(sc, w, start=None, end=None, t=None):
        fname = {"kinetic": "kinetic_energy", "potential": "potential_energy", "total": "energy"}[kind]
        wave = _obj(w, WAVES, fname)
        m, mu, ten = _string_of(wave, fname)
        whole_pulse = isinstance(wave, ShapedPulse) and t is None
        if t is None and not whole_pulse:
            raise SceneError(f"{fname}(wave, ..., t=...): give the instant")
        if whole_pulse and (start is not None or end is not None):
            raise SceneError(f"{fname}(): a stretch of string (start/end) needs the instant t; without t the "
                             f"whole pulse's energy is meant")
        t0 = sp.Integer(0) if whole_pulse else sp.sympify(t)
        pwf, vy, sl = _fields(wave, fname)
        lo_e, hi_e = (None, None) if whole_pulse else (getattr(m, "extent", None) or (None, None))
        lo = sp.sympify(start) if start is not None else (lo_e if lo_e is not None else -sp.oo)
        hi = sp.sympify(end) if end is not None else (hi_e if hi_e is not None else sp.oo)
        for pos in (lo, hi):
            if pos.is_finite and pos.is_number and ((lo_e is not None and pos < lo_e) or
                                                    (hi_e is not None and pos > hi_e)):
                raise SceneError(f"{fname}(): x = {pos} m is outside string '{m.name}'")
        order = sp.simplify(hi - lo)
        if order.is_extended_negative:
            lo, hi = hi, lo
        elif not order.is_extended_nonnegative:
            raise SceneError(f"{fname}(): cannot tell whether start < end; give start before end")
        what = f"{fname}() of '{wave.name}'"
        _check_continuous(pwf.xreplace({T: t0}), lo, hi, what)
        k = (mu * vy ** 2 / 2).xreplace({T: t0})
        u = (ten * sl ** 2 / 2).xreplace({T: t0})
        e = {"kinetic": k, "potential": u, "total": k + u}[kind]
        return _integrate(_pw(e), lo, hi, what)
    return f


def _mean_over(sc, var, e, lo, hi):
    """Average of e over var from lo to hi: (1/(hi - lo)) * integral."""
    if not isinstance(var, sp.Symbol):
        raise SceneError("mean_over(var, expr, lo, hi): first argument must be a variable")
    lo, hi = sp.sympify(lo), sp.sympify(hi)
    span = sp.simplify(hi - lo)
    if span.is_zero or span.is_positive is False:
        raise SceneError("mean_over(): hi must be greater than lo")
    try:
        val = _within(30, lambda: sp.integrate(sp.sympify(e), (var, lo, hi)))
    except _Budget:
        raise SceneError("mean_over(): the integral takes too long; simplify")
    if val.has(sp.Integral):
        raise SceneError("mean_over(): the integral has no closed form")
    return sp.simplify(val / span)


def _extreme_in(kind):
    def f(sc, var, e, lo, hi):
        """Largest (or smallest) value of e for var in [lo, hi]; exact where possible."""
        from .scene import _extreme_values
        if not isinstance(var, sp.Symbol):
            raise SceneError(f"{kind}_in(var, expr, lo, hi): first argument must be a variable")
        lo, hi = sp.sympify(lo), sp.sympify(hi)
        if not (lo.is_number and hi.is_number) or not lo < hi:
            raise SceneError(f"{kind}_in(): give numeric limits with lo < hi")
        e = sp.sympify(e)
        if e.free_symbols - {var}:
            raise SceneError(f"{kind}_in(): the expression must depend only on {var}; other symbols need values. "
                             f"Put at(...) inside: {kind}_in({var}, at(expr, a=...), lo, hi)")
        try:
            vals = _within(20, lambda: _extreme_values(e, var, sp.Interval(lo, hi)))
        except _Budget:
            raise SceneError(f"{kind}_in(): the extremes take too long to find")
        nums = [(float(sp.N(v)), v) for v in vals if v.is_number]
        if not nums:
            raise SceneError(f"{kind}_in(): no value found")
        pick = max(nums, key=lambda t_: t_[0]) if kind == "max" else min(nums, key=lambda t_: t_[0])
        return sp.nsimplify(pick[1]) if pick[1].is_Float else pick[1]
    return f


def _width(sc, p):
    """Length of the one stretch of x over which a shaped pulse is non-zero."""
    pulse = _obj(p, (ShapedPulse,), "width")
    try:
        pw = _pw(pulse.g)
        if sp.simplify(pulse.g) == 0:
            raise SceneError(f"width(): pulse '{pulse.name}' is zero everywhere")
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
        if support is sp.S.EmptySet or support.measure == 0:
            raise SceneError(f"width(): pulse '{pulse.name}' is zero everywhere")
        if not support.measure.is_finite:
            raise SceneError(f"width(): pulse '{pulse.name}' is non-zero over an unbounded region")
        hull = sp.Interval(support.inf, support.sup)
        if sp.simplify(hull.measure - support.measure) != 0:
            raise SceneError(f"width(): pulse '{pulse.name}' has several separate parts; its width is ambiguous "
                             f"(span {sp.simplify(hull.measure)}, non-zero length {sp.simplify(support.measure)})")
        return sp.simplify(support.measure)
    except SceneError:
        raise
    except Exception as exc:
        raise SceneError(f"width(): cannot find where pulse '{pulse.name}' is non-zero ({type(exc).__name__}); "
                         f"give its shape with numbers") from exc


OBSERVABLES.update({
    "kinetic_density": _density("kinetic"), "potential_density": _density("potential"),
    "energy_density": _density("total"),
    "kinetic_energy": _energy("kinetic"), "potential_energy": _energy("potential"), "energy": _energy("total"),
    "mean_over": _mean_over, "width": _width, "max_in": _extreme_in("max"), "min_in": _extreme_in("min"),
})
OBS_DIMS.update({
    "kinetic_density": D_ELEN, "potential_density": D_ELEN, "energy_density": D_ELEN,
    "kinetic_energy": D_ENERGY, "potential_energy": D_ENERGY, "energy": D_ENERGY,
    "width": LENGTH,
})
