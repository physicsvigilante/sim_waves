"""Standing-wave patterns of resonators, and the envelope of a two-frequency sum (beats).

Coordinates along a resonator: x from its first end (ends[0]) at x = 0 to the second
at x = length. For a pipe the displacement antinode at an open end sits end_correction
beyond the physical end. "Nodes" and "antinodes" mean DISPLACEMENT; for pipes the
pressure nodes are the displacement antinodes and the other way round.
"""
import sympy as sp

from .errors import SceneError
from .scene import (DIMLESS, LENGTH, OBS_DIMS, OBSERVABLES, TR8, Resonator, _obj, one_sinusoid)

NODE_ENDS = ("fixed", "closed")


def _geometry(r):
    """(offset of x = 0 from the effective start, end 0 is a displacement node?)"""
    if r.type == "pipe":
        e = (r.Leff - r.L) / r.ends.count("open") if "open" in r.ends else sp.Integer(0)
        e0 = e if r.ends[0] == "open" else sp.Integer(0)
    else:
        e0 = sp.Integer(0)
    return e0, r.ends[0] in NODE_ENDS


def _shape(r, n, x):
    """Displacement amplitude profile of harmonic n, scaled to a maximum of 1."""
    k = 2 * sp.pi / r.wavelength(n)
    e0, node0 = _geometry(r)
    u = x + e0
    return sp.sin(k * u) if node0 else sp.cos(k * u)


def _sol(sc):
    return getattr(sc, "solution", None) or {}


def _positions(sc, r, n, kind):
    """Displacement nodes (kind 'node') or antinodes inside [0, length], in order."""
    sol = _sol(sc)
    n = r._check(sp.sympify(n).xreplace(sol))
    if not n.is_number:
        raise SceneError("node/antinode positions need a numeric harmonic (unknowns are fine in "
                         "observe, once solved)")
    k = (2 * sp.pi / r.wavelength(n)).xreplace(sol)
    e0, node0 = _geometry(r)
    e0 = e0.xreplace(sol)
    L = r.L.xreplace(sol)
    # zeros of sin(k u) at k u = m pi; of cos(k u) at k u = (m + 1/2) pi; maxima swap
    half = (kind == "node") != node0
    out = []
    for m in range(0, 2 * int(n) + 3):
        u = (m + sp.Rational(1, 2) if half else m) * sp.pi / k
        x = sp.simplify(u - e0)
        lo, hi = sp.simplify(x), sp.simplify(x - L)
        if not (lo.is_number and hi.is_number):
            raise SceneError("node/antinode positions need a numeric length and end correction")
        if float(sp.N(lo)) >= -1e-12 and float(sp.N(hi)) <= 1e-12:
            out.append(x)
    return sp.Tuple(*out)


def _res(arg, fname):
    return _obj(arg, (Resonator,), fname)


def _need_h(harmonic, fname):
    if harmonic is None:
        raise SceneError(f"{fname}(resonator, harmonic=n): give the harmonic number")
    return harmonic


def _nodes(_sc, r, harmonic=None):
    return _positions(_sc, _res(r, "nodes"), _need_h(harmonic, "nodes"), "node")


def _antinodes(_sc, r, harmonic=None):
    return _positions(_sc, _res(r, "antinodes"), _need_h(harmonic, "antinodes"), "antinode")


def _pressure_nodes(_sc, r, harmonic=None):
    res = _res(r, "pressure_nodes")
    if res.type != "pipe":
        raise SceneError("pressure_nodes(): for pipes only")
    return _positions(_sc, res, _need_h(harmonic, "pressure_nodes"), "antinode")


def _pressure_antinodes(_sc, r, harmonic=None):
    res = _res(r, "pressure_antinodes")
    if res.type != "pipe":
        raise SceneError("pressure_antinodes(): for pipes only")
    return _positions(_sc, res, _need_h(harmonic, "pressure_antinodes"), "node")


def _mode_shape(_sc, r, harmonic=None, x=None):
    res = _res(r, "mode_shape")
    if x is None:
        raise SceneError("mode_shape(resonator, harmonic=n, x=...): give x")
    n = res._check(_need_h(harmonic, "mode_shape"))
    xv = sp.sympify(x).xreplace(_sol(_sc))
    L = res.L.xreplace(_sol(_sc))
    if xv.is_number and L.is_number and (float(sp.N(xv)) < -1e-12 or float(sp.N(xv - L)) > 1e-12):
        raise SceneError(f"mode_shape(): x = {x} m is outside the resonator (0 to {L} m)")
    if any(xv.has(u) for u in _sc.unknowns):
        # an unknown point must lie on the resonator: enforced as facts while solving
        _sc.implicit_ineqs[(str(xv), res.name, ">=")] = (f"{xv} on resonator '{res.name}' (x >= 0)", ">=", xv)
        _sc.implicit_ineqs[(str(xv), res.name, "<=")] = (f"{xv} on resonator '{res.name}' (x <= length)",
                                                         "<=", xv - res.L)
    return sp.simplify(_shape(res, n, xv))


def _harmonics(_sc, r, upto=None, node_at=None, antinode_at=None, no_node_at=None):
    """Allowed harmonics n <= upto that have a displacement node (or antinode, or no node)
    at a point: touching a string at a point forces a node there; plucking or striking it
    there excites only modes without a node there."""
    res = _res(r, "harmonics")
    given = [(k, v) for k, v in (("node_at", node_at), ("antinode_at", antinode_at),
                                 ("no_node_at", no_node_at)) if v is not None]
    if upto is None or len(given) != 1:
        raise SceneError("harmonics(r, upto=N, node_at=x | antinode_at=x | no_node_at=x)")
    upto = sp.sympify(upto)
    if not (upto.is_Integer and 1 <= upto <= 1000):
        raise SceneError("harmonics(): upto must be a whole number from 1 to 1000")
    key, x = given[0]
    sol = _sol(_sc)
    x = sp.sympify(x).xreplace(sol)
    if not x.is_number or float(sp.N(x)) < -1e-12 or float(sp.N(x - res.L.xreplace(sol))) > 1e-12:
        raise SceneError("harmonics(): the point must be a number inside the resonator")
    out = []
    for n in res.allowed():
        if n > upto:
            break
        s = sp.simplify(_shape(res, n, x).xreplace(sol))
        zero = abs(float(sp.N(s))) < 1e-12
        full = abs(abs(float(sp.N(s))) - 1) < 1e-12
        if (key == "node_at" and zero) or (key == "no_node_at" and not zero) or \
                (key == "antinode_at" and full):
            out.append(sp.Integer(n))
    return sp.Tuple(*out)


def _envelope(_sc, var, e):
    """Slowly varying amplitude of a sum of two sinusoids in var with different frequencies:
    sqrt(A1^2 + A2^2 + 2 A1 A2 cos((w1 - w2) var + c1 - c2)). Beats."""
    if not isinstance(var, sp.Symbol):
        raise SceneError("envelope(var, expr): first argument must be a variable")
    terms = sp.Add.make_args(sp.expand(TR8(sp.expand(sp.sympify(e)))))
    if any(not t.has(var) for t in terms):
        raise SceneError("envelope(): the expression has a constant part")
    groups = {}
    for t in terms:
        _, _, w, _ = one_sinusoid(t, var)
        groups.setdefault(sp.simplify(w), []).append(t)
    if len(groups) != 2:
        raise SceneError(f"envelope(): needs exactly two frequencies in {var}, found {len(groups)}")
    (w1, t1), (w2, t2) = groups.items()
    _, A1, _, c1 = one_sinusoid(sp.Add(*t1), var)
    _, A2, _, c2 = one_sinusoid(sp.Add(*t2), var)
    return sp.sqrt(A1 ** 2 + A2 ** 2 + 2 * A1 * A2 * sp.cos((w1 - w2) * var + c1 - c2))


OBSERVABLES.update({
    "nodes": _nodes, "antinodes": _antinodes, "pressure_nodes": _pressure_nodes,
    "pressure_antinodes": _pressure_antinodes, "mode_shape": _mode_shape,
    "harmonics": _harmonics, "envelope": _envelope,
})
OBS_DIMS.update({
    "nodes": None, "antinodes": None, "pressure_nodes": None, "pressure_antinodes": None,
    "mode_shape": DIMLESS, "harmonics": None, "envelope": None,
})
