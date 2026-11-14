"""Review-3 fixes. Applies exact string replacements; fails loudly if any anchor is missing."""
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1])


def sub(path, old, new, count=1):
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{path}: anchor found {n} times (want {count}):\n{old[:200]}")
    p.write_text(s.replace(old, new), encoding="utf-8")


S = "simwaves/scene.py"

# ---- scene bookkeeping for harmonic numbers --------------------------------
sub(S, """        self.implicit = []       # (label, expr == 0) cross-checks the solver must enforce
""", """        self.implicit = []       # (label, expr == 0) cross-checks the solver must enforce
        self.harmonic_terms = {}  # symbolic harmonic numbers: key -> (expr, need_odd, resonator)
""")

# ---- dimension checks for the new observables -------------------------------
sub(S, """        if fname in OBS_DIMS:
            return OBS_DIMS[fname]
        a = args[0] if args else None""", """        if fname == "beat_frequency":
            for a_ in args:
                if a_ != "obj":
                    chk.same(a_, D_FREQ, "the arguments of beat_frequency() (frequencies in Hz, "
                                         "not angular frequencies)")
        if fname in ("min", "max") and len(args) == 2 and "obj" not in args:
            chk.same(args[0], args[1], f"the two arguments of {fname}()")
        if fname == "resonances":
            if "f" in kwargs:
                chk.same(kwargs["f"], D_FREQ, "argument f=")
            lo_hi = chk.same(kwargs.get("lo"), kwargs.get("hi"), "lo= and hi=")
            vnode = next((k.value for k in node.keywords if k.arg == "vary"), None)
            if isinstance(vnode, ast.Name) and vnode.id in self.names:
                vd = self.symbol_dims.get(self.names[vnode.id])
                chk.same(lo_hi, vd, f"lo=/hi= (the dimension of {vnode.id})")
        if fname in OBS_DIMS:
            return OBS_DIMS[fname]
        a = args[0] if args else None""")

# ---- gas: every input must be used; optional gas constant -------------------
sub(S, """    KEYS = {"type", "v", "gamma", "pressure", "density", "temperature", "molar_mass"}
""", """    KEYS = {"type", "v", "gamma", "pressure", "density", "temperature", "molar_mass", "gas_constant"}
""")
sub(S, """        cands = [q("v", D_SPEED)]
        if gamma is not None and P is not None and rho is not None:
            cands.append(sp.sqrt(gamma * P / rho))
        if gamma is not None and Tk is not None and M is not None:
            cands.append(sp.sqrt(gamma * R_GAS * Tk / M))
        if all(c is None for c in cands):
            raise SceneError(f"{w}: give v, or gamma + pressure + density, or gamma + temperature + molar_mass")""",
    """        R = q("gas_constant", dim(L=2, M=1, T=-2, K=-1))
        cands, used = [q("v", D_SPEED)], {"type", "v"}
        if gamma is not None and P is not None and rho is not None:
            cands.append(sp.sqrt(gamma * P / rho))
            used |= {"gamma", "pressure", "density"}
        if gamma is not None and Tk is not None and M is not None:
            cands.append(sp.sqrt(gamma * (R_GAS if R is None else R) * Tk / M))
            used |= {"gamma", "temperature", "molar_mass", "gas_constant"}
        if all(c is None for c in cands):
            raise SceneError(f"{w}: give v, or gamma + pressure + density, or gamma + temperature + molar_mass")
        unused = sorted(set(spec) - used)
        if unused:
            raise SceneError(f"{w}: {unused} not used: they do not complete a route to the speed of "
                             f"sound (v; gamma + pressure + density; gamma + temperature + molar_mass "
                             f"[+ gas_constant])")""")

# ---- given waves: complete cancellation is amplitude 0 ----------------------
sub(S, """class GivenWave:
    \"\"\"A wave supplied as an explicit y(x, t). Properties are found by analysis.\"\"\"
""", """class _Cancelled(SceneError):
    \"\"\"The parts of a wave cancel everywhere: amplitude 0, other properties undefined.\"\"\"


class GivenWave:
    \"\"\"A wave supplied as an explicit y(x, t). Properties are found by analysis.\"\"\"
""")
sub(S, """            if not rest:
                raise SceneError(f"wave '{self.name}' does not oscillate")""",
    """            if not rest:
                raise _Cancelled(f"wave '{self.name}' does not oscillate (its amplitude is 0)")""")
sub(S, """            if C == 0:
                raise SceneError(f"wave '{self.name}': the sinusoids cancel; there is no wave")""",
    """            if C == 0:
                raise _Cancelled(f"wave '{self.name}': the sinusoids cancel (amplitude 0); "
                                 f"its phase, frequency and wavelength are undefined")""")
sub(S, """    def amplitude(self):
        return self.sinusoid()[1]

    def offset(self):
        return self.sinusoid()[0]
""", """    def amplitude(self):
        try:
            return self.sinusoid()[1]
        except _Cancelled:
            return sp.Integer(0)

    def offset(self):
        return self.sinusoid()[0]
""")

# ---- extent helper used by every point query ---------------------------------
sub(S, """def _check_extent(medium, x, wave_name):""", """def _check_wave_x(wave, x):
    for part in getattr(wave, "parts", [wave]):
        _check_extent(getattr(part, "medium", None), x, part.name)


def _check_extent(medium, x, wave_name):""")

# ---- sums: one medium only ----------------------------------------------------
sub(S, """        media = {id(o.medium): o.medium for o in self.parts if getattr(o, "medium", None) is not None}
        self.medium = next(iter(media.values())) if len(media) == 1 else None""",
    """        media = {id(o.medium): o.medium for o in self.parts if getattr(o, "medium", None) is not None}
        if len(media) > 1:
            names = sorted(m.name for m in media.values())
            raise SceneError(f"{w}.sum: the parts live on different media {names}; a sum is only "
                             f"defined where every part exists (sum waves on one medium)")
        self.medium = next(iter(media.values())) if len(media) == 1 else None""")

# ---- junction geometry --------------------------------------------------------
sub(S, """        self.at = sc.quantity(spec["at"], LENGTH, f"{w}.at")
        self.side = {}""", """        self.at = sc.quantity(spec["at"], LENGTH, f"{w}.at")
        if self.at is None or not self.at.is_number:
            raise SceneError(f"{w}.at: give a number with a unit (symbolic junction positions are "
                             f"not supported)")
        if spec["left"] == spec["right"]:
            raise SceneError(f"{w}: left and right must differ")
        self.side = {}""")
sub(S, """            lo, hi = m.extent or (None, None)
            if side == "left":
                hi = self.at
            else:
                lo = self.at
            m.extent = (lo, hi)""", """            lo, hi = m.extent or (None, None)
            if (hi if side == "left" else lo) is not None:
                raise SceneError(f"{w}.{side}: string '{v}' already ends on that side at x = "
                                 f"{hi if side == 'left' else lo} m; a string has at most one "
                                 f"junction on each side")
            if side == "left":
                hi = self.at
            else:
                lo = self.at
            if lo is not None and hi is not None and not lo < hi:
                raise SceneError(f"{w}: string '{v}' would run from x = {lo} m to x = {hi} m; a string's "
                                 f"left junction must lie left of its right junction")
            m.extent = (lo, hi)""")

# ---- only harmonic waves reflect ------------------------------------------------
sub(S, """    \"\"\"Reflected and transmitted waves created when a harmonic wave meets a junction.\"\"\"
    if not isinstance(wave, Harmonic) or wave.medium is None or not sc.junctions:
        return []""", """    \"\"\"Reflected and transmitted waves created when a harmonic wave meets a junction.\"\"\"
    if (isinstance(wave, GivenWave) and not isinstance(wave, SumWave) and wave.medium is not None
            and any(wave.medium in J.side.values() for J in sc.junctions)):
        raise SceneError(f"waves.{wave.name}: its string has a junction, and only waves written as "
                         f"`harmonic:` are reflected and transmitted there; write it as a harmonic wave")
    if not isinstance(wave, Harmonic) or wave.medium is None or not sc.junctions:
        return []""")

# ---- resonators: positive sizes, symbolic harmonic numbers --------------------
sub(S, """            e = sc.quantity(spec["end_correction"], LENGTH, f"{w}.end_correction")
            self.Leff = self.L + ends.count("open") * e""", """            e = sc.quantity(spec["end_correction"], LENGTH, f"{w}.end_correction")
            if e.is_negative:
                raise SceneError(f"{w}.end_correction: must be >= 0")
            self.Leff = self.L + ends.count("open") * e""")
sub(S, """            self.Leff = self.L
        self.mixed = ends[0] != ends[1]
""", """            self.Leff = self.L
        for label, val in (("length", self.L), ("effective length", self.Leff)):
            if val.is_positive is False or (val.is_number and not val > 0):
                raise SceneError(f"{w}: {label} must be positive (got {val})")
        self.mixed = ends[0] != ends[1]
        self.sc = sc
""")
sub(S, """    def _check(self, n):
        n = sp.sympify(n)
        if n.is_number:
            if not (n.is_Integer and n >= 1):
                raise SceneError(f"resonator '{self.name}': harmonic must be a whole number >= 1")
            if self.mixed and n % 2 == 0:
                raise SceneError(f"resonator '{self.name}' has one {self.ends[0]} and one {self.ends[1]} "
                                 f"end: only odd harmonics exist (harmonic {n} does not)")
        return n
""", """    def _check(self, n, odd=None, what="harmonic"):
        n = sp.sympify(n)
        odd = self.mixed if odd is None else odd
        if n.is_number:
            if not (n.is_Integer and n >= 1):
                raise SceneError(f"resonator '{self.name}': {what} must be a whole number >= 1")
            if odd and n % 2 == 0:
                raise SceneError(f"resonator '{self.name}' has one {self.ends[0]} and one {self.ends[1]} "
                                 f"end: only odd harmonics exist (harmonic {n} does not)")
            return n
        bad = sorted(str(s) for s in n.free_symbols if self.sc.kinds.get(s) != "integer")
        if bad:
            raise SceneError(f"resonator '{self.name}': {what} must be a whole number or an expression "
                             f"in symbols of kind integer ({bad} are not)")
        self.sc.harmonic_terms[(str(n), self.name, odd)] = (n, odd, self, what)
        return n
""")
sub(S, """        k = sp.sympify(k)
        if k.is_number and not (k.is_Integer and k >= 1):
            raise SceneError("overtone must be a whole number >= 1 (the 1st overtone is the first above the fundamental)")
        return 2 * k + 1 if self.mixed else k + 1""", """        k = sp.sympify(k)
        if k.is_number and not (k.is_Integer and k >= 1):
            raise SceneError("overtone must be a whole number >= 1 (the 1st overtone is the first above the fundamental)")
        k = self._check(k, odd=False, what="overtone")
        return 2 * k + 1 if self.mixed else k + 1""")
sub(S, """def _resonator(arg, fname):""", """def harmonic_problem(sc, sol, final=False):
    \"\"\"Why the solved values break a resonator's mode rules (None if they do not).
    With final=True, a harmonic still symbolic must be provably allowed.\"\"\"
    for n, odd, res, what in list(sc.harmonic_terms.values()):
        v = sp.sympify(n).xreplace(sol)
        if v.is_number:
            if not (v.is_Integer and v >= 1):
                return f"resonator '{res.name}': {what} {n} = {v} is not a whole number >= 1"
            if odd and v % 2 == 0:
                return (f"resonator '{res.name}' has one {res.ends[0]} and one {res.ends[1]} end: "
                        f"harmonic {n} = {v} is even, and only odd harmonics exist")
        elif final and odd and ((v + 1) / 2).is_integer is not True:
            return (f"resonator '{res.name}': harmonic {v} is left as a symbol, but only odd harmonics "
                    f"exist; write it as 2*m - 1 with m a symbol of kind integer")
    return None


def _resonator(arg, fname):""")

# ---- resonances(): solve once in the mode number, scan both directions --------
old_res_start = '''def _resonances(_sc, r, f=None, vary=None, lo=None, hi=None):'''
old_res_end = '''    return sp.Tuple(*sorted(set(found), key=lambda v: float(sp.N(v))))
'''
p = ROOT / S
s = p.read_text(encoding="utf-8")
i, j = s.index(old_res_start), s.index(old_res_end) + len(old_res_end)
s = s[:i] + '''def _resonances(sc, r, f=None, vary=None, lo=None, hi=None):
    """Values of the symbol `vary` in [lo, hi] at which some allowed mode of the resonator
    has frequency f, in increasing order."""
    res = _resonator(r, "resonances")
    if f is None or vary is None or lo is None or hi is None:
        raise SceneError("resonances(r, f=..., vary=<symbol>, lo=..., hi=...)")
    if not isinstance(vary, sp.Symbol):
        raise SceneError("resonances(): vary must be a symbol used in the resonator")
    N = sp.Dummy("n", positive=True, integer=True)
    fN = res.medium.speed() / ((4 if res.mixed else 2) * res.Leff / N)
    if not fN.has(vary):
        raise SceneError(f"resonances(): the mode frequencies of '{res.name}' do not depend on {vary}")
    f, lo, hi = sp.sympify(f), sp.sympify(lo), sp.sympify(hi)
    extra = (f.free_symbols | fN.free_symbols | lo.free_symbols | hi.free_symbols) - {vary, N}
    if extra:
        raise UndeterminedError(f"resonances(): needs values for {sorted(map(str, extra))}")
    lo_v, hi_v = float(sp.N(lo)), float(sp.N(hi))
    if lo_v > hi_v:
        raise SceneError("resonances(): lo must not exceed hi")
    branches = sp.solve(sp.Eq(fN, f), vary)
    if not branches:
        raise SceneError(f"resonances(): no value of {vary} gives frequency {f}")
    positive = sc.kinds.get(vary) == "positive"
    eps = 1e-12 * max(1.0, abs(lo_v), abs(hi_v))
    found, prev, done = [], [None] * len(branches), [False] * len(branches)
    for n in res.allowed():
        if all(done):
            break
        if n > 5000:
            raise SceneError("resonances(): more than 5000 modes scanned; narrow the range")
        for b, expr in enumerate(branches):
            if done[b]:
                continue
            v = sp.nsimplify(expr.xreplace({N: n})) if False else expr.xreplace({N: n})
            cv = complex(sp.N(v))
            if abs(cv.imag) > 1e-12 * max(1.0, abs(cv.real)):
                done[b] = prev[b] == "nonreal"
                prev[b] = "nonreal"
                continue
            fv = cv.real
            if lo_v - eps <= fv <= hi_v + eps and not (positive and fv <= 0):
                found.append(v)
            p_ = prev[b] if isinstance(prev[b], float) else None
            if p_ is not None and ((fv > hi_v + eps and fv >= p_) or (fv < lo_v - eps and fv <= p_)):
                done[b] = True          # each branch is monotonic in n: moving away for good
            if p_ is not None and fv == p_:
                done[b] = True
            prev[b] = fv
    return sp.Tuple(*sorted(set(found), key=lambda v: float(sp.N(v))))
''' + s[j:]
p.write_text(s, encoding="utf-8")

# ---- point queries check extents everywhere ------------------------------------
sub(S, """        for part in getattr(wave, "parts", [wave]):
            _check_extent(getattr(part, "medium", None), x, part.name)
        e = wave.field()""", """        _check_wave_x(wave, x)
        e = wave.field()""")
sub(S, """    if x is None or t is None:
        raise SceneError("phase(): give both x= and t=")
    return wave.phase_expr(x, t)""", """    if x is None or t is None:
        raise SceneError("phase(): give both x= and t=")
    _check_wave_x(wave, x)
    return wave.phase_expr(x, t)""")
sub(S, """    return TWO_PI / _obj(w, WAVES, "wavelength").wavenumber(at)""",
    """    wave = _obj(w, WAVES, "wavelength")
    if at is not None:
        _check_wave_x(wave, at)
    return TWO_PI / wave.wavenumber(at)""")
sub(S, """    "k": lambda sc, w, at=None: _obj(w, WAVES, "k").wavenumber(at),""",
    """    "k": lambda sc, w, at=None: (_check_wave_x(_obj(w, WAVES, "k"), at) if at is not None else None,
                                 _obj(w, WAVES, "k").wavenumber(at))[1],""")

# ---- limit must exist -----------------------------------------------------------
sub(S, """        raise SceneError("limit(expr, var, value): second argument must be a variable")
    return sp.limit(e, var, value)""", """        raise SceneError("limit(expr, var, value): second argument must be a variable")
    v = sp.limit(e, var, value)
    if v.has(sp.AccumBounds, sp.zoo, sp.nan) or v in (sp.oo, -sp.oo):
        raise SceneError(f"limit(): the limit does not exist as a finite value (got {v})")
    return v""")

# ---- expr: lists cannot take part in arithmetic -----------------------------------
E = "simwaves/expr.py"
sub(E, """            a, b = self.val(n.left), self.val(n.right)
            if isinstance(n.op, ast.Pow) and b.is_number and abs(sp.N(b)) > MAX_EXP:""",
    """            a, b = self.val(n.left), self.val(n.right)
            if isinstance(a, sp.Tuple) or isinstance(b, sp.Tuple):
                raise SceneError("a list result (such as resonances(...)) cannot be used in "
                                 "arithmetic; use count(...) on it, or observe it on its own")
            if isinstance(n.op, ast.Pow) and b.is_number and abs(sp.N(b)) > MAX_EXP:""")
sub(E, """            v = self.val(n.operand)
            return -v if isinstance(n.op, ast.USub) else v""", """            v = self.val(n.operand)
            if isinstance(v, sp.Tuple):
                raise SceneError("a list result (such as resonances(...)) cannot be negated")
            return -v if isinstance(n.op, ast.USub) else v""")

# ---- solver: mode rules during the search and in the re-check -------------------------
V = "simwaves/solver.py"
sub(V, """        if kind == "integer" and v.is_integer is False:
            return False
    return True""", """        if kind == "integer" and v.is_integer is False:
            return False
    from .scene import harmonic_problem
    if harmonic_problem(sc, sol):
        return False
    return True""")
sub(V, """    if sol:
        out.append((-1, "declared kinds of the solved unknowns", "proved"))
    return out""", """    from .scene import harmonic_problem
    why = harmonic_problem(sc, sol)
    if why:
        raise SceneError(f"internal check failed: {why}; this is an engine bug, please report it")
    if sol:
        out.append((-1, "declared kinds of the solved unknowns", "proved"))
    if sc.harmonic_terms:
        out.append((-1, "resonator mode rules (whole, odd where required)", "proved"))
    return out""")

# ---- run: every observable is evaluated; errors are collected --------------------------
R = "simwaves/run.py"
sub(R, """    sol = solve_given(sc)
    results, sc.basis = {}, {}
    for name, text in (sc.data.get("observe") or {}).items():
        v, basis = resolve_deferred(sp.sympify(sc.expr(text, check_dims=True)).xreplace(sol).doit())
        if not isinstance(v, sp.logic.boolalg.BooleanAtom):
            v = sp.simplify(v)
        results[name], sc.basis[name] = v, basis
    return sol, results""", """    from .errors import InconsistentError
    from .scene import harmonic_problem
    sol = solve_given(sc)
    results, sc.basis, errors = {}, {}, []
    for name, text in (sc.data.get("observe") or {}).items():
        try:
            v, basis = resolve_deferred(sp.sympify(sc.expr(text, check_dims=True)).xreplace(sol).doit())
        except SceneError as exc:
            errors.append((name, exc))
            continue
        if not isinstance(v, sp.logic.boolalg.BooleanAtom):
            v = sp.simplify(v)
        results[name], sc.basis[name] = v, basis
    why = harmonic_problem(sc, sol, final=True)
    if why and not errors:
        errors.append(("modes", InconsistentError(why)))
    if errors:
        first = errors[0][1]
        msg = first.args[0] if len(errors) == 1 else "; ".join(f"observe.{n}: {e}" for n, e in errors)
        exc = type(first)(msg)
        exc.partial = (sol, results)
        raise exc
    return sol, results""")
sub("simwaves/__main__.py", """    except SceneError as exc:
        print(f"{type(exc).__name__}: {exc}")
        return 1
    for k, v in sol.items():""", """    except SceneError as exc:
        sol_, res_ = getattr(exc, "partial", ({}, {}))
        for k, v in list(sol_.items()) + list(res_.items()):
            print(f"{k} = {show(v)}")
        print(f"{type(exc).__name__}: {exc}")
        return 1
    for k, v in sol.items():""")

# ---- export: clip display windows to the medium a wave lives on --------------------
X_ = "simwaves/export.py"
sub(X_, """# ------------------------------------------------------------------ panels""", """def _clip(wave, xw, sol, illus, missing, what):
    \"\"\"Clip an x window to the extent of the medium (or media) the wave lives on.\"\"\"
    if xw is None:
        return None
    lo, hi, label = xw
    clipped = []
    for part in getattr(wave, "parts", [wave]):
        ext = getattr(getattr(part, "medium", None), "extent", None) or (None, None)
        for k, b in enumerate(ext):
            if b is None:
                continue
            v = sp.sympify(b).xreplace(sol).xreplace(illus)
            if not v.is_number:
                continue
            v = float(v)
            if k == 0 and v > lo:
                lo = v
                clipped.append(part.medium.name)
            if k == 1 and v < hi:
                hi = v
                clipped.append(part.medium.name)
    if not lo < hi:
        missing.append(f"{what}: the display window lies outside the medium of '{wave.name}'; "
                       f"give `x: [lo, hi]` inside it")
        return None
    if clipped:
        label += f"; clipped to medium {sorted(set(clipped))}"
    return lo, hi, label


# ------------------------------------------------------------------ panels""")
sub(X_, """        xw = fixed.get("x") or _window(sc, spec, "x", sol, illus, missing)
        if kind == "snapshot":""", """        xw = fixed.get("x") or _clip(wave, _window(sc, spec, "x", sol, illus, missing),
                                     sol, illus, missing, f"view {kind} {name}")
        if kind == "snapshot":""")
print("patched")
