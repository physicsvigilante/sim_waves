"""Solve a scene's `given` facts (plus the scene's implicit cross-checks) for its unknowns.

Contract: exactly one situation, or an error. Never a silently chosen branch.

* Direction unknowns (+1/-1) are solved by trying both cases.
* An unknown that appears only inside sines/cosines, with numeric coefficients, is an angle:
  it is solved on the unit circle (S, C with S^2 + C^2 = 1) and recovered with atan2, then
  every branch is enumerated: phases mod 2*pi; other unknowns over the interval allowed by
  their sign and the scene's inequalities (an unbounded family is ambiguous).
* Any other appearance of an unknown inside a trig function is refused, because SymPy's
  trig solving can silently drop roots.
* An equation with a free t must hold for all t: products are reduced to sums of sines and
  cosines and every Fourier coefficient must vanish; unknown frequencies are refused.
"""
import itertools
import random

import sympy as sp
from sympy.core.function import AppliedUndef
from sympy.simplify.fu import TR8

from .errors import AmbiguousError, InconsistentError, SceneError, UndeterminedError
from .scene import T, TWO_PI, X, sample_value

SOURCES = ("stated", "figure", "convention", "assumption")

MAX_BRANCHES = 2000
PROBE = 60


def _facts(sc):
    """given items: a string, or {fact: <text>, source: stated|figure|convention|assumption}."""
    out = []
    for i, item in enumerate(sc.data.get("given") or []):
        if isinstance(item, str):
            out.append((item, "untagged"))
        elif isinstance(item, dict) and "fact" in item and set(item) <= {"fact", "source", "note"}:
            src = item.get("source", "untagged")
            if src not in SOURCES + ("untagged",):
                raise SceneError(f"given[{i}].source must be one of {SOURCES}")
            out.append((item["fact"], src))
        else:
            raise SceneError(f"given[{i}]: a string or {{fact: ..., source: ...}}")
    sc.facts = out
    return out


def _relations(sc):
    out = []
    for i, (text, _src) in enumerate(_facts(sc)):
        rels = sc.expr(text, allow_rel=True, check_dims=True)
        if not isinstance(rels, list):
            raise SceneError(f"given[{i}] must be an equation (==) or inequality: {text!r}")
        from .scene import Nearest, Defined
        for r in rels:
            lhs, rhs = sp.sympify(r.lhs).doit(), sp.sympify(r.rhs).doit()
            if (lhs - rhs).has(Nearest):
                raise SceneError(f"given[{i}]: nearest() picks an option; use it in observe only")
            # a wave value whose written profile needs conditions at a symbolic point: the
            # conditions become inequalities the solution must satisfy; then the plain value
            for g in (lhs - rhs).atoms(Defined):
                for c in g.args[1:]:
                    parts = c.args if isinstance(c, sp.And) else (c,)
                    for c1 in parts:
                        if isinstance(c1, sp.Unequality):
                            raise SceneError(f"given[{i}]: the wave's written profile needs {c1} at a point the "
                                             f"facts fix later; this cannot be checked inside a fact")
                        op = {sp.StrictGreaterThan: ">", sp.GreaterThan: ">=", sp.StrictLessThan: "<",
                              sp.LessThan: "<="}[type(c1)]
                        out.append((i, f"[defined] {text}: {c1}", op, sp.sympify(c1.lhs), sp.sympify(c1.rhs)))
            if (lhs - rhs).has(Defined):
                plain = lambda z: isinstance(z, Defined)
                lhs = lhs.replace(plain, lambda z: z.args[0])
                rhs = rhs.replace(plain, lambda z: z.args[0])
            if (lhs - rhs).has(X):
                raise SceneError(f"given[{i}] has a free x; evaluate at a point with x=...")
            out.append((i, text, r.op, lhs, rhs))
    base = len(out) and (max(r[0] for r in out) + 1)
    for j, (label, e) in enumerate(sc.implicit):
        out.append((base + j, f"[implicit] {label}", "==", sp.sympify(e), sp.Integer(0)))
    base += len(sc.implicit)
    for j, (label, op, e) in enumerate(getattr(sc, "implicit_ineqs", {}).values()):
        out.append((base + j, f"[implicit] {label}", op, sp.sympify(e), sp.Integer(0)))
    return out


# ---------------------------------------------------------------- identities in t
def _split_time(e):
    rep = {}
    for f in e.atoms(sp.sin, sp.cos):
        if not f.has(T):
            continue
        a = sp.expand(f.args[0])
        at = sp.Add(*[term for term in sp.Add.make_args(a) if term.has(T)])
        a0 = a - at
        if isinstance(f, sp.sin):
            rep[f] = sp.sin(at) * sp.cos(a0) + sp.cos(at) * sp.sin(a0)
        else:
            rep[f] = sp.cos(at) * sp.cos(a0) - sp.sin(at) * sp.sin(a0)
    return sp.expand(e.xreplace(rep))


def _identity_in_t(sc, e, i, text):
    e = _split_time(sp.expand(TR8(sp.expand(e))))
    gens = sorted({f for f in e.atoms(sp.sin, sp.cos) if f.has(T)}, key=sp.default_sort_key)
    for g in gens:
        w = sp.diff(g.args[0], T)
        if w.has(T) or any(w.has(u) for u in sc.unknowns):
            raise SceneError(f"given[{i}]: the time dependence involves an unknown frequency or is "
                             f"not sinusoidal; v0 cannot match it for all t: {text!r}")
    if not gens:
        raise SceneError(f"given[{i}]: free t only supported inside sines/cosines: {text!r}")
    poly = sp.Poly(e, *gens)
    if poly.total_degree() > 1 or any(c.has(T) for c in poly.coeffs()):
        raise SceneError(f"given[{i}]: cannot treat as an identity in t: {text!r}")
    return [c for c in poly.coeffs() if c != 0]


def _conditions(sc, rels):
    eqs, ineqs = [], []
    for i, text, op, lhs, rhs in rels:
        if op == "==":
            e = sp.expand(lhs - rhs)
            parts = _identity_in_t(sc, e, i, text) if e.has(T) else [e]
            eqs += [(i, text, p) for p in parts]
        else:
            if (lhs - rhs).has(T):
                raise SceneError(f"given[{i}]: inequality with a free t is not supported")
            ineqs.append((i, text, op, lhs - rhs))
    return eqs, ineqs


# ---------------------------------------------------------------- angular unknowns
def _function_atoms(E):
    atoms = []
    for e in E:
        for a in sorted(e.atoms(sp.Derivative), key=sp.default_sort_key):
            if a not in atoms:
                atoms.append(a)
    for e in E:
        bare = e.xreplace({a: sp.Dummy() for a in atoms})
        for a in sorted(bare.atoms(AppliedUndef), key=sp.default_sort_key):
            if a not in atoms:
                atoms.append(a)
    return atoms


def _in_trig(u, E):
    """u inside a periodic function (many roots, solved on the unit circle). Monotonic functions
    such as log, exp and atan are left to the algebraic solver: they lose no roots."""
    return any(f.has(u) for e in E for f in e.atoms(sp.sin, sp.cos, sp.tan))


def _in_monotonic(u, E):
    """u inside log, exp, an inverse trig function or an exponent (e.g. 2**u)."""
    for e in E:
        for f in e.atoms(sp.log, sp.exp, sp.atan, sp.asin, sp.acos):
            if f.has(u):
                return True
        for p in e.atoms(sp.Pow):
            if p.exp.has(u):
                return True
    return False


def _solve_monotonic(E, targets):
    """One unknown inside log/exp/inverse trig: the full real root set from solveset (sympy's
    solve() can drop roots such as log(u) = 0 in polynomial-in-log equations). Every root is
    checked against every equation. More unknowns: refused rather than risk a lost root."""
    if len(targets) != 1:
        return _solve_monotonic_system(E, targets)
    u = targets[0]
    roots = None
    for e in E:
        if not e.has(u):
            continue
        ss = None
        e_log = sp.expand_log(e, force=True)
        if e_log != sp.expand_log(e):
            # force=True assumed a sign the unknown does not have (log(u^2) -> 2 log(u) loses u < 0)
            forms = [e]
        else:
            forms = [f for f in (_log_linear(e_log, u), e_log, e) if f is not None]
        for form in forms:
            num = sp.numer(sp.together(form))
            if num.is_polynomial(u) and sp.degree(num, u) <= 4:
                # polynomial: sympy's polynomial solver is complete up to degree 4
                cand = sp.FiniteSet(*[r for r in sp.solve(num, u) if _real(r)])
                if cand.is_empty and sp.degree(num, u) < 1:
                    cand = None
                if cand is not None:
                    ss = cand
                    break
                continue
            try:
                cand = sp.solveset(form, u, sp.S.Reals)
            except (NotImplementedError, ValueError, TypeError):
                continue
            if isinstance(cand, sp.FiniteSet):
                ss = cand
                break
        if ss is None:
            raise SceneError(f"cannot solve reliably for '{u}' inside log/exp/inverse trig in {e} = 0; "
                             f"restate the fact")
        good = set()
        for v in ss:
            try:
                ok = all(abs(complex(sp.N(ei.xreplace({u: v}), 30))) < 1e-20 for ei in E) and \
                    _logs_defined(E, {u: v})
            except (TypeError, ValueError):
                ok = False
            if ok:
                good.add(v)
        roots = good if roots is None else roots & good
    return [{u: v} for v in sorted(roots or [], key=lambda v: float(sp.N(v)))]


def _log_linear(e, u):
    """If e = sum c_i log(g_i(u)) + c0 with rational ratios c_i/c_1, return the algebraic
    equivalent prod g_i^(c_i/c_1) - exp(-c0/c_1) (same real roots where every g_i > 0;
    the caller re-checks each root against the original equation)."""
    logs = [f for f in e.atoms(sp.log) if f.has(u)]
    if not logs:
        return None
    L = {f: sp.Dummy("L") for f in logs}
    e1 = sp.expand(e.xreplace(L))
    if e1.has(u):
        return None
    coeffs = [sp.diff(e1, d) for d in L.values()]
    if any(c.has(*L.values()) or c.has(u) for c in coeffs):
        return None
    c0 = sp.simplify(e1.xreplace({d: 0 for d in L.values()}))
    ratios = [sp.nsimplify(sp.simplify(c / coeffs[0])) for c in coeffs]
    if not all(r.is_Rational for r in ratios):
        return None
    prod = sp.Mul(*[f.args[0] ** r for f, r in zip(L, ratios)])
    return sp.together(prod - sp.exp(sp.simplify(-c0 / coeffs[0])))


def _log_linear_multi(e, us):
    """Like _log_linear, for several unknowns: e = sum c_i log(g_i) + c0 with rational ratios
    c_i/c_1 becomes prod g_i^(c_i/c_1) - exp(-c0/c_1)."""
    logs = [f for f in e.atoms(sp.log) if f.has(*us)]
    if not logs:
        return e
    L = {f: sp.Dummy("L") for f in logs}
    e1 = sp.expand(e.xreplace(L))
    if e1.has(*us):
        return None
    coeffs = [sp.diff(e1, d) for d in L.values()]
    if any(c.has(*L.values()) or c.has(*us) for c in coeffs):
        return None
    c0 = sp.simplify(e1.xreplace({d: 0 for d in L.values()}))
    ratios = [sp.nsimplify(sp.simplify(c / coeffs[0])) for c in coeffs]
    if not all(r.is_Rational for r in ratios):
        return None
    prod = sp.Mul(*[f.args[0] ** r for f, r in zip(L, ratios)])
    return sp.numer(sp.together(prod - sp.exp(sp.simplify(-c0 / coeffs[0]))))


def _solve_monotonic_system(E, targets):
    """Several unknowns inside logs: rewrite each fact linear in logs as an algebraic equation,
    solve the algebraic system, and keep only roots that satisfy the original facts."""
    alg = []
    for e in E:
        if not any(e.has(u) for u in targets):
            continue
        e_log = sp.expand_log(e, force=True)
        if e_log != sp.expand_log(e):
            raise SceneError(f"unknowns {sorted(map(str, targets))} appear inside logs whose sign v0 cannot "
                             f"track ({e} = 0); declare them positive if the problem says so, or fix one first")
        a = _log_linear_multi(e_log, targets)
        if a is None or _in_monotonic_any(a, targets):
            raise SceneError(f"unknowns {sorted(map(str, targets))} appear together inside log/exp/inverse-trig "
                             f"functions in a form v0 cannot rewrite reliably ({e} = 0); fix one of them first")
        alg.append(a)
    raw = sp.solve(alg, targets, dict=True)
    out = []
    for r in raw:
        if set(r) != set(targets) or any(v.free_symbols & set(targets) for v in r.values()):
            raise UndeterminedError(f"the facts tie {sorted(map(str, targets))} together but do not fix "
                                    f"each one (a family of solutions); a fact is missing")
        if not all(_real(v) for v in r.values()):
            continue
        try:
            ok = all(abs(complex(sp.N(e.xreplace(r), 30))) < 1e-20 for e in E) and _logs_defined(E, r)
        except (TypeError, ValueError):
            ok = False
        if ok:
            out.append(r)
    return out


def _logs_defined(E, r):
    """Every log in the facts has a positive real argument at the root (a real log of a
    negative number is undefined, even when the complex parts cancel)."""
    for e in E:
        for f in e.atoms(sp.log):
            if not f.has(*r):
                continue
            a = sp.N(f.args[0].xreplace(r), 30)
            if not a.is_number:
                continue
            c = complex(a)
            if abs(c.imag) > 1e-20 or c.real <= 0:
                return False
    return True


def _in_monotonic_any(e, us):
    return any(_in_monotonic(u, [e]) for u in us)


def _angular_base(u, E):
    """Numeric base b such that u enters every equation only as sin/cos(m*b*u + ...), m integer."""
    coeffs = []
    for e in E:
        trig = [f for f in e.atoms(sp.sin, sp.cos) if f.has(u)]
        others = [f for f in e.atoms(sp.tan, sp.asin, sp.acos, sp.atan, sp.exp, sp.log) if f.has(u)]
        if others or e.xreplace({f: sp.Dummy() for f in trig}).has(u):
            return None
        for f in trig:
            a = sp.diff(f.args[0], u)
            if not a.is_number or a == 0:
                return None
            coeffs.append(sp.nsimplify(a))
    if not coeffs:
        return None
    a0 = coeffs[0]
    ratios = [sp.nsimplify(c / a0) for c in coeffs]
    if not all(r.is_Rational for r in ratios):
        return None
    g = ratios[0]
    for r in ratios[1:]:
        g = sp.gcd(g, r)
    return sp.Abs(a0 * g)


def _expand_angles(e, thetas):
    def split(f):
        a = sp.expand(f.args[0])
        th = [t for t in sp.Add.make_args(a) if t.free_symbols & thetas]
        if not th:
            return f
        if len(th) == 1 and a == th[0]:
            coeff, sym = th[0].as_coeff_Mul()
            if coeff in (1, -1):
                return f
            return sp.expand(sp.expand_trig(type(f)(coeff * sym)))
        first, rest = th[0], a - th[0]
        s1, c1 = split(sp.sin(first)), split(sp.cos(first))
        s2, c2 = split(sp.sin(rest)), split(sp.cos(rest))
        return s1 * c2 + c1 * s2 if isinstance(f, sp.sin) else c1 * c2 - s1 * s2
    rep = {f: split(f) for f in e.atoms(sp.sin, sp.cos) if f.free_symbols & thetas}
    return sp.expand(e.xreplace(rep))


def _real(v):
    if v.is_real is False:
        return False
    if v.is_number:
        return abs(sp.N(sp.im(v), 30)) < 1e-20
    return True


def _single_trig(e, targets):
    """e = A*f(L) + c with f sin or cos, A and c numbers, L linear in targets with numeric
    coefficients: return (f, A, c, L); else None."""
    e = sp.expand(e)
    trig = [f for f in e.atoms(sp.sin, sp.cos) if f.free_symbols & set(targets)]
    if len(trig) != 1:
        return None
    f = trig[0]
    D = sp.Dummy("f")
    e2 = e.xreplace({f: D})
    A = sp.diff(e2, D)
    c = sp.expand(e2 - A * D)
    L = sp.expand(f.args[0])
    if not (A.is_number and A != 0 and c.is_number and _real(A) and _real(c)):
        return None
    if not all(sp.diff(L, u).is_number for u in targets) or \
            sp.expand(L - sum(sp.diff(L, u) * u for u in targets)).free_symbols & set(targets):
        return None
    return type(f), A, c, L


def _solve_phase_pair(E, targets, kinds):
    """Two facts A_i*sin(s_i*ph + a_i*q + c_i) = y_i (or cos) for a phase ph and one other
    angular unknown q (two points off the origin): each fact fixes its angle up to the two
    inverse-sine branches and 2*pi*n; subtracting eliminates ph, so q = q0 + n*P with
    P = 2*pi/|s1*a1 - s2*a2|, and ph follows from q. Returns (sols, periods) or None.
    The branches of q are then enumerated against the stated bounds by _branches."""
    if len(E) != 2 or len(targets) != 2:
        return None
    ph = [u for u in targets if kinds.get(u) == "phase"]
    if len(ph) != 1:
        return None
    ph = ph[0]
    q = next(u for u in targets if u != ph)
    parts = [_single_trig(e, targets) for e in E]
    if any(p is None for p in parts):
        return None
    angles, coef = [], []
    for f, A, c, L in parts:
        s, a = sp.diff(L, ph), sp.diff(L, q)
        if s not in (1, -1) or a == 0:
            return None
        r = sp.nsimplify(-c / A)
        if abs(sp.N(r, 30)) > 1:
            return [], {}                          # |y| > |A|: this fact has no solution at all
        base = sp.expand(L - s * ph - a * q)       # the constant part of the angle
        th = [sp.asin(r), sp.pi - sp.asin(r)] if f is sp.sin else [sp.acos(r), -sp.acos(r)]
        angles.append([(t - base) * s for t in th])   # s*(angle - base) = ph + s*a*q
        coef.append(s * a)
    d = coef[0] - coef[1]
    if d == 0 or not d.is_number:
        return None
    sols = []
    for t1, t2 in itertools.product(*angles):
        q0 = sp.simplify((t1 - t2) / d)
        sols.append({q: q0, ph: t1 - coef[0] * q})   # ph in terms of q: fixed per branch of q
    return sols, _Periods({q: sp.simplify(TWO_PI / sp.Abs(d))}, probe=4)


class _Periods(dict):
    """Periods with a smaller probe for unbounded branches: in the phase-pair case every
    further branch of q fits as well, so a few show that there are infinitely many."""

    def __init__(self, data, probe):
        super().__init__(data)
        self.probe = probe


def _core_solve(E, targets, kinds):
    """Return (solutions, periods). periods[u] is the period of an angular unknown u."""
    for e in E:
        p = _single_trig(e, targets)
        if p is not None and abs(sp.N(p[2] / p[1], 30)) > 1:
            return [], {}                          # A*sin(L) = y with |y| > |A|: no real solution
    pair = _solve_phase_pair(E, targets, kinds)
    if pair is not None:
        return pair
    trig_u = [u for u in targets if _in_trig(u, E)]
    bases = {}
    for u in trig_u:
        b = _angular_base(u, E)
        if b is None:
            raise SceneError(f"unknown '{u}' sits inside a sine/cosine in a way v0 cannot solve "
                             f"reliably (non-numeric or mixed coefficient); restate the facts")
        bases[u] = b
    mono = [u for u in targets if u not in bases and _in_monotonic(u, E)]
    if mono and not bases:
        return _solve_monotonic(E, targets), {}
    if not bases:
        return sp.solve(E, targets, dict=True), {}
    theta = {u: sp.Dummy(f"th_{u}") for u in bases}
    E1 = [_expand_angles(sp.expand(e.xreplace({u: theta[u] / b for u, b in bases.items()})),
                         set(theta.values())) for e in E]
    S = {u: sp.Dummy(f"S_{u}", real=True) for u in bases}
    C = {u: sp.Dummy(f"C_{u}", real=True) for u in bases}
    rep = {}
    for u in bases:
        rep[sp.sin(theta[u])], rep[sp.cos(theta[u])] = S[u], C[u]
    E2 = [sp.expand(e.xreplace(rep)) for e in E1]
    if any(e.has(*theta.values()) for e in E2):
        raise SceneError("v0 could not reduce the trig equations to polynomial form")
    E2 += [S[u] ** 2 + C[u] ** 2 - 1 for u in bases]
    algebraic = [u for u in targets if u not in bases]
    raw = sp.solve(E2, algebraic + list(S.values()) + list(C.values()), dict=True)
    sols = []
    for r in raw:
        if not all(_real(v) for v in r.values()):
            continue
        out = {u: r[u] for u in algebraic if u in r}
        for u, b in bases.items():
            if S[u] in r and C[u] in r:
                out[u] = sp.atan2(sp.simplify(r[S[u]]), sp.simplify(r[C[u]])) / b
        sols.append(out)
    return sols, {u: TWO_PI / b for u, b in bases.items()}


def _sign_ok(d, op):
    d = sp.simplify(d)
    pos, neg, zero = d.is_positive, d.is_negative, d.is_zero
    if d.is_number and None in (pos, neg, zero):
        v = float(sp.N(d, 30))
        pos, neg, zero = v > 1e-15, v < -1e-15, abs(v) <= 1e-15
    if op == "<":
        return neg
    if op == ">":
        return pos
    if op == "<=":
        return True if (neg or zero or d.is_nonpositive) else (False if pos else None)
    return True if (pos or zero or d.is_nonnegative) else (False if neg else None)


def _assumptions_ok(sc, sol):
    for u, v in sol.items():
        kind = sc.kinds.get(u)
        if kind in ("real", "phase", "positive", "direction") and not _real(v):
            return False
        if kind == "positive" and (v.is_positive is False or (v.is_number and not float(sp.N(v)) > 0)):
            return False
        if kind == "integer" and v.is_integer is False:
            return False
    from .scene import harmonic_problem
    if harmonic_problem(sc, sol):
        return False
    return True


def _interval(sc, u, sol, ineqs, unknowns):
    """Values of u allowed by its sign and by inequalities that involve u algebraically."""
    I = sp.Interval.open(0, sp.oo) if sc.kinds.get(u) == "positive" else sp.Reals
    for _, _, op, d in ineqs:
        d2 = d.xreplace({k: v for k, v in sol.items() if k != u})
        if d2.free_symbols != {u} or _in_trig(u, [d2]):
            continue
        rel = {"<": sp.Lt, "<=": sp.Le, ">": sp.Gt, ">=": sp.Ge}[op](d2, 0)
        try:
            I = I.intersect(sp.solve_univariate_inequality(rel, u, relational=False))
        except (NotImplementedError, ValueError):
            pass
    return I


def _check_ineqs(b, ineqs, unknowns, strict):
    for i, text, op, d in ineqs:
        d2 = d.xreplace(b)
        if any(d2.has(u) for u in unknowns):
            if strict:
                raise UndeterminedError(f"given[{i}] cannot be checked; unknowns left: {text!r}")
            continue
        ok = _sign_ok(d2, op)
        if ok is None:
            if strict:
                raise AmbiguousError(f"given[{i}] cannot be decided for all symbol values: {text!r}")
            continue
        if not ok:
            return False
    return True


def _norm_phase(v):
    if v.is_number:
        return sp.nsimplify(v - TWO_PI * sp.floor(sp.N(v / TWO_PI, 30)), [sp.pi]) \
            if abs(sp.N(v - sp.nsimplify(v, [sp.pi]), 30)) < 1e-25 else v - TWO_PI * sp.floor(sp.N(v / TWO_PI, 30))
    return v


def _branches(sc, s, periods, ineqs, unknowns, strict):  # noqa: C901
    """Expand one principal solution into all branches; returns (kept, infinite_flag)."""
    choices = {}
    infinite = False
    for u, p in periods.items():
        if u not in s:
            continue
        u0 = s[u]
        if any(u0.has(w) for w in unknowns if w != u):
            continue                      # fixed only in terms of other unknowns: undetermined later
        if not u0.is_number or not p.is_number:
            raise AmbiguousError(f"'{u}' is only fixed up to a period {p} that depends on symbols")
        if sc.kinds.get(u) == "phase":
            ratio = sp.nsimplify(TWO_PI / p)
            if not ratio.is_Rational:
                raise SceneError(f"phase '{u}' has an irrational multiplier")
            count = int(sp.Abs(ratio.p)) if ratio.q == 1 else int(sp.Abs(ratio.p))
            choices[u] = sorted({_norm_phase(u0 + n * p) for n in range(count)},
                                key=lambda v: float(sp.N(v)))
            continue
        I = _interval(sc, u, s, ineqs, unknowns)
        if I is sp.S.EmptySet:
            choices[u] = []
            continue
        lo, hi = I.inf, I.sup
        if lo == -sp.oo or hi == sp.oo:
            infinite = True
            probe = getattr(periods, "probe", PROBE)
            n_lo = 0 if lo == -sp.oo else int(sp.ceiling(sp.N((lo - u0) / p)))
            n_hi = n_lo + probe if hi == sp.oo else int(sp.floor(sp.N((hi - u0) / p)))
            if hi == sp.oo and lo == -sp.oo:
                n_lo, n_hi = -probe // 2, probe // 2
            elif lo == -sp.oo:
                n_lo, n_hi = n_hi - probe, n_hi
        else:
            n_lo = int(sp.ceiling(sp.N((lo - u0) / p, 30))) - 1
            n_hi = int(sp.floor(sp.N((hi - u0) / p, 30))) + 1
            if n_hi - n_lo > MAX_BRANCHES:
                raise AmbiguousError(f"more than {MAX_BRANCHES} values of '{u}' fit the facts")
        choices[u] = [u0 + n * p for n in range(n_lo, n_hi + 1)]
    kept = []
    keys = list(choices)
    for combo in itertools.product(*[choices[k] for k in keys]):
        chosen = dict(zip(keys, combo))
        # a value fixed in terms of a branched unknown (a phase from its wavenumber) takes
        # that branch's value
        b = {**{k: sp.sympify(v).xreplace(chosen) for k, v in s.items()}, **chosen}
        for u in b:
            if sc.kinds.get(u) == "phase":
                b[u] = _norm_phase(sp.simplify(b[u]))
        if _assumptions_ok(sc, b) and _check_ineqs(b, ineqs, unknowns, strict):
            kept.append(b)
    return kept, infinite and bool(kept)


def _dedupe(sols):
    out = []
    for b in sols:
        dup = False
        for c in out:
            if set(b) == set(c) and all(
                    (sp.simplify(b[k] - c[k]) == 0) or
                    (b[k].is_number and c[k].is_number and abs(sp.N(b[k] - c[k], 30)) < 1e-20)
                    for k in b):
                dup = True
                break
        if not dup:
            out.append(b)
    return out


def _solve(sc, eqs, ineqs, strict):
    """Return (solutions, infinite_flag)."""
    E0 = [e for _, _, e in eqs]
    atoms = _function_atoms(E0)
    dummies = {a: sp.Dummy(f"fn{j}") for j, a in enumerate(atoms)}
    back = {d: a for a, d in dummies.items()}
    E0 = [e.xreplace(dummies) for e in E0]
    ineqs = [(i, t, op, d.xreplace(dummies)) for i, t, op, d in ineqs]
    unknowns = list(sc.unknowns) + list(dummies.values())
    dirs = [u for u in sc.unknowns if sc.kinds.get(u) == "direction"]
    # |u| with unknowns inside: solved by sign cases, u >= 0 or u < 0, each checked afterwards
    absq = sorted({a for e in E0 for a in e.atoms(sp.Abs) if any(a.has(u) for u in unknowns)}, key=str)
    if len(absq) > 6:
        raise SceneError("more than 6 absolute values of unknowns in the facts; simplify the scene")
    results, infinite = [], False
    for case in itertools.product((1, -1), repeat=len(dirs) + len(absq)):
        cs = dict(zip(dirs, map(sp.Integer, case[:len(dirs)])))
        signs = case[len(dirs):]
        E0c = [e.xreplace({a: s_ * a.args[0] for a, s_ in zip(absq, signs)}) for e in E0]
        case_ineqs = ineqs + [(-1, f"sign case {'+' if s_ > 0 else '-'}({a.args[0]})",
                               ">=" if s_ > 0 else "<", a.args[0].xreplace(cs))
                              for a, s_ in zip(absq, signs)]
        E = [sp.expand(e.xreplace(cs)) for e in E0c]
        E = [e for e in E if e != 0]
        free_of_unknowns = [e for e in E if not any(e.has(u) for u in unknowns)]
        bad_case = False
        for e in free_of_unknowns:
            se = sp.simplify(e)
            if se == 0:
                continue
            if se.free_symbols:
                raise SceneError(f"a fact without unknowns cannot be checked for all symbol values "
                                 f"({sc.show_back(e)} = 0); it over-specifies the scene")
            bad_case = True
        if bad_case:
            continue
        E = [e for e in E if e not in free_of_unknowns]
        targets = [u for u in unknowns if u not in cs and any(e.has(u) for e in E)]
        if not E:
            sols, periods = [{}], {}
        elif not targets:
            sols, periods = [{}], {}
        else:
            try:
                sols, periods = _core_solve(E, targets, sc.kinds)
            except NotImplementedError as exc:
                raise SceneError(f"cannot solve the given equations: {exc}") from exc
        for s in sols:
            s = {k: sp.simplify(v) for k, v in s.items()}
            s.update(cs)
            for u in list(s):
                if sc.kinds.get(u) == "phase" and u not in periods:
                    s[u] = _norm_phase(s[u])
            kept, inf = _branches(sc, s, periods, case_ineqs, unknowns, strict)
            infinite = infinite or inf
            results += [{back.get(k, k): v for k, v in b.items()} for b in kept]
    return _dedupe(results), infinite


def _range_hint(sc, prior, i, text, op, lhs, rhs):
    g = sp.expand(sp.sympify(lhs).xreplace(prior))
    free = [u for u in sc.unknowns if g.has(u)]
    if len(free) != 1:
        return ""
    u = free[0]
    terms = sp.Add.make_args(g)
    B = sp.Add(*[a for a in terms if not a.has(u)])
    rest = [a for a in terms if a.has(u)]
    if len(rest) != 1:
        return ""
    C, trig = rest[0].as_independent(u, as_Add=False)
    if not isinstance(trig, (sp.sin, sp.cos)) or not (B.is_number and C.is_number):
        return ""
    lo, hi, r = sp.N(B - sp.Abs(C), 4), sp.N(B + sp.Abs(C), 4), sp.N(rhs.xreplace(prior), 4)
    return f"; its left side can only range over [{lo}, {hi}] but must equal {r}"


def _fmt(v):
    if getattr(v, "is_number", False) and v.has(sp.atan, sp.atan2):
        q = sp.nsimplify(sp.N(v / sp.pi, 40), rational=True, tolerance=1e-30)
        if abs(sp.N(q * sp.pi - v, 40)) < 1e-30:
            return q * sp.pi
    return v


def _verify(sc, rels, sol):
    """Independent re-check: substitute the final solution into every ORIGINAL fact
    (not the transformed system the solver worked on). A failure is an engine bug."""
    out, rng = [], random.Random(11)
    for i, text, op, lhs, rhs in rels:
        d = sp.sympify(lhs - rhs).xreplace(sol).doit()
        if op == "==":
            if sp.simplify(d) == 0:
                out.append((i, text, "proved"))
                continue
            syms = sorted(d.free_symbols, key=str)
            scale_expr = sp.Abs(sp.sympify(lhs).xreplace(sol)) + sp.Abs(sp.sympify(rhs).xreplace(sol))
            ok = True
            for _ in range(8):
                vals = {s: sample_value(s, rng) for s in syms}
                dd = abs(complex(sp.N(d.xreplace(vals), 30)))
                sc_ = abs(complex(sp.N(scale_expr.xreplace(vals), 30)))
                if dd > 1e-20 + 1e-12 * sc_:
                    ok = False
                    break
            if not ok:
                raise SceneError(f"internal check failed: the solution does not satisfy {text!r}; "
                                 f"this is an engine bug, please report it")
            out.append((i, text, "sampled"))
        else:
            ok = _sign_ok(d, op)
            if ok is False:
                raise SceneError(f"internal check failed: the solution violates {text!r}; "
                                 f"this is an engine bug, please report it")
            out.append((i, text, "proved" if ok else "undecided"))
    for u, val in sol.items():
        kind = sc.kinds.get(u)
        bad = ((kind in ("positive", "real", "phase", "direction") and val.is_real is False)
               or (kind == "positive" and val.is_positive is False)
               or (kind == "integer" and val.is_integer is False)
               or (kind == "direction" and val not in (1, -1))
               or (kind == "phase" and val.is_number and not (0 <= float(sp.N(val)) < 2 * 3.141592653589794)))
        if bad:
            raise SceneError(f"internal check failed: {u} = {val} violates its declared kind "
                             f"'{kind}'; this is an engine bug, please report it")
    from .scene import harmonic_problem
    why = harmonic_problem(sc, sol)
    if why:
        raise SceneError(f"internal check failed: {why}; this is an engine bug, please report it")
    if sol:
        out.append((-1, "declared kinds of the solved unknowns", "proved"))
    if sc.harmonic_terms:
        out.append((-1, "resonator mode rules (whole, odd where required)", "proved"))
    return out


def solve_given(sc):
    sol = _solve_given(sc)
    sc.verification = _verify(sc, _relations(sc), sol) if (sc.data.get("given") or sc.implicit) else []
    return sol


def _solve_given(sc):
    rels = _relations(sc)
    if not rels:
        if sc.unknowns:
            raise UndeterminedError(f"unknowns {sc.unknowns} declared but nothing is given")
        return {}
    eqs, ineqs = _conditions(sc, rels)
    sols, infinite = _solve(sc, eqs, ineqs, strict=True)
    if not sols:
        idxs = sorted({r[0] for r in rels})
        prior = {}
        for m in idxs:
            sub = [r for r in rels if r[0] <= m]
            e2, i2 = _conditions(sc, sub)
            try:
                s2, _ = _solve(sc, e2, i2, strict=False)
            except UndeterminedError:
                s2 = [{}]                      # the first facts alone leave a family: no contradiction yet
            if not s2:
                culprit = next(r for r in rels if r[0] == m)
                hint = _range_hint(sc, prior, *culprit) if culprit[2] == "==" else ""
                raise InconsistentError(f"no situation satisfies the facts; contradiction appears at "
                                        f"given[{m}] {culprit[1]!r}{hint}")
            prior = s2[0]
        raise InconsistentError("no situation satisfies the facts")
    for s in sols:
        missing = [u for u in sc.unknowns if u not in s]
        if missing:
            raise UndeterminedError(f"unknowns not fixed by the facts: {missing}")
        for u, v in s.items():
            if any(v.has(w) for w in sc.unknowns):
                raise UndeterminedError(f"{u} is only fixed in terms of other unknowns: {u} = {v}")
    if len(sols) > 1 or infinite:
        shown = "; ".join(", ".join(f"{k}={_fmt(v)}" for k, v in s.items()) for s in sols[:4])
        count = "infinitely many situations" if infinite else f"{len(sols)} situations"
        # every distinct value each unknown takes (smallest first), so no family is hidden
        spread = []
        for u in sc.unknowns:
            vals = {_fmt(s[u]) for s in sols if u in s}
            if len(vals) > 1:
                try:
                    vals = sorted(vals, key=lambda v: abs(float(sp.N(v))))
                except TypeError:
                    vals = sorted(vals, key=str)
                more = ", ..." if len(vals) > 6 or infinite else ""
                spread.append(f"{u} in {{{', '.join(map(str, vals[:6]))}{more}}}")
        extra = f" Values seen: {'; '.join(spread)}." if spread else ""
        raise AmbiguousError(f"{count} fit the facts, e.g. {shown}.{extra} "
                             f"Add a constraint and record the reason in 'assume'.")
    return sols[0]
