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
        for r in rels:
            lhs, rhs = sp.sympify(r.lhs).doit(), sp.sympify(r.rhs).doit()
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
    return any(f.has(u) for e in E for f in e.atoms(sp.sin, sp.cos, sp.tan, sp.asin, sp.acos,
                                                     sp.atan, sp.exp, sp.log))


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


def _core_solve(E, targets, kinds):
    """Return (solutions, periods). periods[u] is the period of an angular unknown u."""
    trig_u = [u for u in targets if _in_trig(u, E)]
    bases = {}
    for u in trig_u:
        b = _angular_base(u, E)
        if b is None:
            raise SceneError(f"unknown '{u}' sits inside a sine/cosine in a way v0 cannot solve "
                             f"reliably (non-numeric or mixed coefficient); restate the facts")
        bases[u] = b
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
        return True if (neg or zero) else (False if pos else None)
    return True if (pos or zero) else (False if neg else None)


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
            n_lo = 0 if lo == -sp.oo else int(sp.ceiling(sp.N((lo - u0) / p)))
            n_hi = n_lo + PROBE if hi == sp.oo else int(sp.floor(sp.N((hi - u0) / p)))
            if hi == sp.oo and lo == -sp.oo:
                n_lo, n_hi = -PROBE // 2, PROBE // 2
            elif lo == -sp.oo:
                n_lo, n_hi = n_hi - PROBE, n_hi
        else:
            n_lo = int(sp.ceiling(sp.N((lo - u0) / p, 30))) - 1
            n_hi = int(sp.floor(sp.N((hi - u0) / p, 30))) + 1
            if n_hi - n_lo > MAX_BRANCHES:
                raise AmbiguousError(f"more than {MAX_BRANCHES} values of '{u}' fit the facts")
        choices[u] = [u0 + n * p for n in range(n_lo, n_hi + 1)]
    kept = []
    keys = list(choices)
    for combo in itertools.product(*[choices[k] for k in keys]):
        b = {**s, **dict(zip(keys, combo))}
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
                                 f"({e} = 0); it over-specifies the scene")
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
            s2, _ = _solve(sc, e2, i2, strict=False)
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
        raise AmbiguousError(f"{count} fit the facts, e.g. {shown}. "
                             f"Add a constraint and record the reason in 'assume'.")
    return sols[0]
