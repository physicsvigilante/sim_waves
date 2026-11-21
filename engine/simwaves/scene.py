"""Scene: media, waves and emitters, plus the physical observables the LLM may call.

All physics formulas live here (and only here). Internal units are SI.
"""
import random

import sympy as sp
from sympy.core.function import AppliedUndef
from sympy.simplify.fu import TR8

from .errors import AmbiguousError, SceneError, UndeterminedError
import ast

from .expr import Ref, dimension_of, show_dim, translate

ast_unparse = ast.unparse
from .units import CELSIUS_OFFSET, DIMLESS, FORCE, LENGTH, MASS, TEMP, TIME, dim, split_quantity

X = sp.Symbol("x", real=True)
T = sp.Symbol("t", real=True)
TWO_PI = 2 * sp.pi

KINDS = {"positive": dict(positive=True), "real": dict(real=True),
         "integer": dict(integer=True), "phase": dict(real=True),
         "direction": dict(real=True, nonzero=True)}    # direction: +1 or -1, solved by cases
RESERVED = {"x", "t", "pi"}
TOP_KEYS = {"id", "assume", "symbols", "unknowns", "functions", "media", "junctions", "waves",
            "resonators", "emitters", "arbitrary", "sources", "reflectors", "points", "rays", "given", "observe", "view", "expect", "illustrate", "explore"}
R_GAS = sp.Rational(831446261815324, 10 ** 14)     # J/(mol K), exact SI value
I0_HEARING = sp.Rational(1, 10 ** 12)                # W/m^2: the standard reference of the decibel scale

D_FREQ, D_SPEED, D_WAVENUM = dim(T=-1), dim(L=1, T=-1), dim(L=-1)
D_LINDENS, D_DENS, D_PRESS = dim(L=-1, M=1), dim(L=-3, M=1), dim(-1, 1, -2)
D_POWER, D_ACC, D_AREA = dim(2, 1, -3), dim(L=1, T=-2), dim(L=2)


def _keys(spec, allowed, where):
    extra = set(spec) - set(allowed)
    if extra:
        raise SceneError(f"{where}: unknown key(s) {sorted(extra)}; allowed: {sorted(allowed)}")


def _same(a, b):
    """True if a == b, False if provably different, None if undecidable."""
    d = sp.simplify(a - b)
    if d == 0:
        return True
    if d.free_symbols:
        return None
    return bool(abs(sp.N(d)) < 1e-12 * (1 + abs(sp.N(a))))


def _pick(sc, cands, label, where):
    """Choose among several specifications of one quantity; all must agree.
    If agreement cannot be decided now, it becomes an implicit fact for the solver."""
    cands = [c for c in cands if c is not None]
    if not cands:
        return None
    for other in cands[1:]:
        same = _same(cands[0], other)
        if same is False:
            raise SceneError(f"{where}: inconsistent {label}: {cands[0]} vs {other}")
        if same is None:
            sc.implicit.append((f"{where}: {label} given twice", cands[0] - other))
    return cands[0]


class Scene:
    def __init__(self, data, scale=None):
        if not isinstance(data, dict):
            raise SceneError("scene must be a mapping")
        _keys(data, TOP_KEYS, "scene")
        self.data = data
        self.implicit = []       # (label, expr == 0) cross-checks the solver must enforce
        self.harmonic_terms = {}  # symbolic harmonic numbers: key -> (expr, need_odd, resonator)
        self.implicit_ineqs = {}  # key -> (label, op, expr): expr op 0 must hold (e.g. a point on a string)
        self.symbol_dims = {}    # dimension a symbol takes where it fills a dimensional field
        self.names = {"x": X, "t": T, "pi": sp.pi}
        self.kinds = {}          # symbol -> kind
        self.unknowns = []
        self.functions = {}
        self.objects = {}
        for section, is_unknown in (("symbols", False), ("unknowns", True)):
            for name, kind in (data.get(section) or {}).items():
                self._new_name(name)
                if kind == "direction" and not is_unknown:
                    raise SceneError(f"{section}.{name}: direction must be an unknown")
                if kind not in KINDS:
                    raise SceneError(f"{section}.{name}: kind must be one of {sorted(KINDS)}")
                s = sp.Symbol(name, **KINDS[kind])
                self.names[name], self.kinds[s] = s, kind
                if is_unknown:
                    self.unknowns.append(s)
        # values the problem leaves unstated and the answer must not depend on (checked by re-running)
        self.arbitrary = {}
        self.arbitrary_ranges = {}
        for name, value in (data.get("arbitrary") or {}).items():
            self._new_name(name)
            rng = None
            if isinstance(value, dict):
                extra = set(value) - {"value", "below", "above"}
                if extra or "value" not in value or not ({"below", "above"} & set(value)):
                    raise SceneError(f"arbitrary.{name}: a ranged value is {{value: ..., below: ..., above: ...}} "
                                     f"(value and at least one of below/above), e.g. {{value: 20 m/s, below: 340 m/s}}")
                rng = value
                value = value["value"]
            text, unit, factor, udim = split_quantity(value)
            v = self.expr(text) * factor
            if not v.is_number or not v.is_positive:
                raise SceneError(f"arbitrary.{name}: give a positive number with its unit, e.g. 10 g/m")
            if rng is not None:
                bounds = {}
                for key in ("above", "below"):
                    if key in rng:
                        bt, bu, bf, bd = split_quantity(rng[key])
                        b = self.expr(bt) * bf
                        if not b.is_number or b.is_real is not True:
                            raise SceneError(f"arbitrary.{name}.{key}: a real number with a unit (other names "
                                             f"cannot be used in a range)")
                        if (bd or DIMLESS) != (udim or DIMLESS):
                            raise SceneError(f"arbitrary.{name}.{key}: a number with the same unit dimension as "
                                             f"the value")
                        bounds[key] = b
                lo, hi = bounds.get("above", sp.Integer(0)), bounds.get("below", sp.oo)
                if lo.is_negative:
                    raise SceneError(f"arbitrary.{name}.above: arbitrary values are positive; use above >= 0")
                if not (lo < hi):
                    raise SceneError(f"arbitrary.{name}: below must be greater than above")
                if not (lo < v < hi):
                    raise SceneError(f"arbitrary.{name}: the value {value} lies outside its own range")
                self.arbitrary_ranges[name] = (lo, hi)
            if scale:
                v = scale[name](v) if callable(scale[name]) else v * scale[name]
            self.names[name] = v
            self.arbitrary[name] = DIMLESS if udim is None else udim
        self._bounds_from_given(data)
        for name in data.get("functions") or []:
            self._new_name(name)
            self.functions[name] = sp.Function(name)
        for name, spec in (data.get("media") or {}).items():
            self._add(name, make_medium(self, name, spec))
        self.junctions = []
        for name, spec in (data.get("junctions") or {}).items():
            j = Junction(self, name, spec)
            self._add(name, j)
            self.junctions.append(j)
        for name, spec in (data.get("waves") or {}).items():
            wave = make_wave(self, name, spec)
            self._add(name, wave)
            for dname, dwave in derived_waves(self, wave):
                self._add(dname, dwave)
        for name, spec in (data.get("resonators") or {}).items():
            self._add(name, Resonator(self, name, spec))
        for name, spec in (data.get("emitters") or {}).items():
            self._add(name, Emitter(self, name, spec))
        from . import rays as _rays
        _rays.build(self, data)
        self.solution = {}

    def _bounds_from_given(self, data):
        """A given inequality between one symbol and a constant is a stated bound: the symbol is
        rewritten as bound + (positive), so every sign decision can use it."""
        self.bounds = {}
        self.bound_dims = {}
        for item in data.get("given") or []:
            text = item if isinstance(item, str) else (item.get("fact") if isinstance(item, dict) else None)
            if not isinstance(text, str):
                continue
            try:
                tree = ast.parse(text.strip(), mode="eval").body
            except SyntaxError:
                continue
            if not (isinstance(tree, ast.Compare) and len(tree.ops) == 1):
                continue
            flip = {ast.Gt: ast.Lt, ast.GtE: ast.LtE, ast.Lt: ast.Gt, ast.LtE: ast.GtE}
            if not isinstance(tree.left, ast.Name) and isinstance(tree.comparators[0], ast.Name) and \
                    type(tree.ops[0]) in flip:
                # '1 < n' is the same bound as 'n > 1'
                tree = ast.Compare(left=tree.comparators[0], ops=[flip[type(tree.ops[0])]()],
                                   comparators=[tree.left])
            if not isinstance(tree.left, ast.Name):
                continue
            name = tree.left.id
            if name in self.bounds and type(tree.ops[0]) in (ast.Gt, ast.GtE, ast.Lt, ast.LtE):
                raise SceneError(f"given: '{name}' has two bounds; v0 supports one bound per symbol")
            sym = self.names.get(name)
            if not isinstance(sym, sp.Symbol) or sym in self.unknowns or self.kinds.get(sym) not in (
                    "positive", "real", "integer"):
                continue
            right = ast_unparse(tree.comparators[0])
            try:
                c = sp.sympify(self.expr(right))
            except SceneError:
                continue
            if not c.is_number or c.free_symbols:
                continue
            op = type(tree.ops[0])
            if op not in (ast.Gt, ast.GtE, ast.Lt, ast.LtE):
                continue
            if name in self.bounds:
                raise SceneError(f"given: '{name}' has two bounds; v0 supports one bound per symbol")
            lower = op in (ast.Gt, ast.GtE)
            kind = self.kinds.get(sym)
            if kind == "positive" and lower and c <= 0:
                continue                       # weaker than 'positive': nothing to add
            if kind == "positive" and not lower and c <= 0:
                raise SceneError(f"given: '{name}' is declared positive but bounded by {text!r}")
            strict = op in (ast.Gt, ast.Lt)
            try:
                bdim = dimension_of(right, self)
            except SceneError:
                bdim = None
            if bdim is None and "[" not in right:
                bdim = DIMLESS
            # the offset from the bound gets a name no scene can declare, so it never merges
            # with a user symbol; messages show it as Δ(n)
            pname = f"Δ({name})"
            if kind == "integer":
                # integer n > c: n = (first integer allowed) + (integer >= 0)
                first = (sp.floor(c) + 1 if strict else sp.ceiling(c)) if lower else \
                    (sp.ceiling(c) - 1 if strict else sp.floor(c))
                p = sp.Symbol(pname, integer=True, nonnegative=True)
                self.names[name] = first + p if lower else first - p
                self.kinds[p] = "integer"
                self.bounds[name] = (sym, p, (sym - first) if lower else (first - sym))
                self.bound_dims[name] = bdim
                continue
            p = sp.Symbol(pname, **({"positive": True} if strict else {"nonnegative": True}))
            self.names[name] = c + p if lower else c - p
            self.kinds[p] = "positive"
            self.bounds[name] = (sym, p, (sym - c) if lower else (c - sym))
            self.bound_dims[name] = bdim

    def bound_variable(self, v):
        """If v is a bounded symbol as it appears in expressions (base + s*offset), return
        (declared symbol, offset symbol, s, base); otherwise None."""
        for sym, p, _ in getattr(self, "bounds", {}).values():
            if isinstance(v, sp.Basic) and v.has(p) and v.free_symbols == {p}:
                sgn = sp.diff(v, p)
                base = v.xreplace({p: 0})
                if sgn in (1, -1) and sp.expand(v - base - sgn * p) == 0:
                    return sym, p, sgn, base
        return None

    def show_back(self, v):
        """Write a result in the original symbols (undo bound substitutions)."""
        if not getattr(self, "bounds", None) or not isinstance(v, sp.Basic):
            return v
        return sp.simplify(v.xreplace({p: back for _, p, back in self.bounds.values()}))

    def _new_name(self, name):
        if not isinstance(name, str) or not name.isidentifier():
            raise SceneError(f"invalid name {name!r}")
        if name in RESERVED or name in self.names or name in self.functions or name in self.objects:
            if name in RESERVED:
                raise SceneError(f"name '{name}' is reserved (x, t and pi are reserved: choose another name)")
            raise SceneError(f"name '{name}' is declared twice (a name may be a symbol, an unknown or an "
                             f"object, but only one of them)")

    def _add(self, name, obj):
        self._new_name(name)
        self.objects[name] = obj

    # ---- expression context -------------------------------------------------
    def name(self, n):
        if n in self.objects:
            return Ref(n, self.objects[n])
        if n in self.names:
            return self.names[n]
        if n in self.functions:
            raise SceneError(f"function '{n}' must be called, e.g. {n}(x - c*t)")
        raise SceneError(f"unknown name '{n}'")

    def call(self, fname, args, kwargs):
        if fname in self.functions:
            if kwargs:
                raise SceneError(f"{fname}() takes no keyword arguments")
            return self.functions[fname](*args)
        if fname not in OBSERVABLES:
            raise SceneError(f"unknown function '{fname}'")
        try:
            return OBSERVABLES[fname](self, *args, **kwargs)
        except (TypeError, AttributeError, ValueError) as exc:
            raise SceneError(f"{fname}(): bad arguments ({exc})") from exc

    def expr(self, text, allow_rel=False, check_dims=False):
        return translate(text, self, allow_rel, check_dims)

    def unit_for_nearest(self, x_text, unit_text):
        """(factor, offset, dimension) for 'nearest(x in unit, ...)', with the same checks as
        'observe: x in unit' (known unit, matching dimension, no angle units)."""
        from .run import _split_unit
        from .units import parse_unit
        text, unit = _split_unit(self, "nearest", f"{x_text} in {unit_text}")
        if unit is None:
            raise SceneError(f"nearest(): cannot read the unit {unit_text!r} after 'in'")
        _, factor, offset = unit
        return factor, offset, parse_unit(unit_text)[1]

    # ---- dimension checking (used for `given` and `observe`) -----------------
    def name_dim(self, n):
        if n in self.objects:
            return "obj"
        if n in getattr(self, "arbitrary", {}):
            return self.arbitrary[n]
        if n in getattr(self, "bound_dims", {}):
            return self.bound_dims[n]       # a bounded symbol has its bound's dimension
        # x and t inside free formulas are plain SI numbers (book formulas such as
        # 0.2*sin(2*pi*(6*t - x/60)) carry implicit units); observables are still checked.
        return {"pi": DIMLESS}.get(n)

    def call_dim(self, fname, args, kwargs, node, chk):
        if fname in self.functions:
            return None
        for key, want in (("x", LENGTH), ("t", TIME), ("emitted", TIME), ("at", LENGTH), ("r", LENGTH), ("node_at", LENGTH),
                          ("start", LENGTH), ("end", LENGTH),
                          ("antinode_at", LENGTH), ("no_node_at", LENGTH)):
            if key in kwargs:
                chk.same(kwargs[key], want, f"argument {key}=")
        if fname == "sound_level" and args:
            chk.same(args[0], dim(0, 1, -3), "the argument of sound_level() (an intensity in W/m^2)")
        if fname == "intensity_of_level" and args:
            chk.same(args[0], DIMLESS, "the argument of intensity_of_level() (a level in dB, a number)")
        if fname == "beat_frequency":
            for a_ in args:
                if a_ != "obj":
                    chk.same(a_, D_FREQ, "the arguments of beat_frequency() (frequencies in Hz, "
                                         "not angular frequencies)")
        if fname in ("item", "spacing") and args:
            return args[0]
        if fname == "frequencies_in":
            for key in ("lo", "hi"):
                if key in kwargs:
                    chk.same(kwargs[key], D_FREQ, f"argument {key}= of frequencies_in() (a frequency)")
        if fname == "nearest" and len(args) >= 2:
            for a_ in args[1:]:
                if args[0] not in (None, DIMLESS, "obj") and a_ == DIMLESS:
                    raise SceneError("nearest(): the value has a unit but the options are bare numbers; write "
                                     "nearest(x in <unit>, ...) to read them in that unit, or give the options "
                                     "units, e.g. 150[Hz]")
                chk.same(args[0], a_, "the value and the options of nearest()")
        if fname in ("min", "max") and len(args) == 2 and "obj" not in args:
            chk.same(args[0], args[1], f"the two arguments of {fname}()")
        if fname in ("maxima", "minima"):
            lo_hi = chk.same(kwargs.get("lo"), kwargs.get("hi"), "lo= and hi=")
            vnode = next((k.value for k in node.keywords if k.arg == "vary"), None)
            if isinstance(vnode, ast.Name) and vnode.id in self.names:
                chk.same(lo_hi, self.symbol_dims.get(self.names[vnode.id]),
                         f"lo=/hi= (the dimension of {vnode.id})")
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
        a = args[0] if args else None
        a = None if a == "obj" else a
        if fname in ("abs", "simplify"):
            return a
        if fname == "sqrt":
            return None if a is None else tuple(sp.Rational(x, 2) for x in a)
        if fname in ("sin", "cos", "tan", "exp", "log", "atan", "asin", "acos"):
            chk.same(a, DIMLESS, f"the argument of {fname}()")
            return DIMLESS
        if fname == "mean_over" and len(args) >= 4:
            span = chk.same(args[2], args[3], "the limits of mean_over()")
            v0 = node.args[0]
            if isinstance(v0, ast.Name):
                want_ = {"x": LENGTH, "t": TIME}.get(v0.id)
                if want_ is None and v0.id in self.names:
                    want_ = self.symbol_dims.get(self.names[v0.id])
                chk.same(span, want_, f"the limits of mean_over() (the dimension of {v0.id})")
        if fname in ("max_in", "min_in") and len(args) >= 2:
            return args[1]
        if fname in ("max_over", "min_over", "mean_over"):
            return args[1] if len(args) > 1 else None
        if fname in ("min", "max", "limit", "at"):
            if fname == "at":
                for k_ in node.keywords:
                    if k_.arg in self.names and isinstance(self.names[k_.arg], sp.Symbol):
                        want_ = {"x": LENGTH, "t": TIME}.get(k_.arg) or self.symbol_dims.get(self.names[k_.arg])
                        chk.same(kwargs.get(k_.arg), want_, f"the value given for {k_.arg} in at()")
            return args[0] if args else None
        if fname == "diff":
            if len(args) < 2 or args[0] is None or args[1] is None:
                return None
            n = 1
            if len(node.args) > 2:
                n = int(translate(ast_unparse(node.args[2]), self))
            return tuple(x - n * y for x, y in zip(args[0], args[1]))
        return None

    def quantity(self, value, d, where, temperature=False):
        """Parse a scene field value such as '0.2 m'; check its dimension."""
        if value is None:
            return None
        text, unit, factor, udim = split_quantity(value)
        e = self.expr(text) * factor
        if unit == "degC" and temperature:
            e = e + CELSIUS_OFFSET
        if udim is not None and d is not None and udim != d:
            raise SceneError(f"{where}: unit '{unit}' has the wrong dimension")
        names_in = set()
        try:
            names_in = {nd.id for nd in ast.walk(ast.parse(str(text).strip(), mode="eval")) if isinstance(nd, ast.Name)}
        except SyntaxError:
            pass
        if udim is None and d is not None and names_in & set(getattr(self, "arbitrary", {})):
            got = dimension_of(text, self)
            if got is not None and got != d:
                raise SceneError(f"{where}: '{value}' has dimension {show_dim(got)}, expected {show_dim(d)}")
            udim = d
        if udim is None and d is not None and str(text).strip() in getattr(self, "bound_dims", {}):
            bd = self.bound_dims[str(text).strip()]
            if bd is not None and bd != d:
                raise SceneError(f"{where}: '{text}' is bounded by a value with dimension {show_dim(bd)}, "
                                 f"but is used here as {show_dim(d)}")
            udim = d
        if udim is None and "[" in str(text) and d is not None:
            # an expression with unit brackets, e.g. '9[kg]*9.8[m/s^2]': check its dimension
            got = dimension_of(text, self)
            if got is not None and got != d:
                raise SceneError(f"{where}: '{value}' has dimension {show_dim(got)}, expected {show_dim(d)}")
            if got == d:
                udim = d
        if udim is None and d not in (None, DIMLESS) and not e.free_symbols:
            raise SceneError(f"{where}: number '{value}' needs a unit")
        if udim is None and d is not None and isinstance(e, sp.Symbol) and e in self.kinds:
            known = self.symbol_dims.get(e)
            if known is not None and known != d:
                raise SceneError(f"{where}: symbol '{e}' is used with two different dimensions")
            self.symbol_dims[e] = d
        return e


# ============================== media =========================================
def make_medium(sc, name, spec):
    if not isinstance(spec, dict) or "type" not in spec:
        raise SceneError(f"media.{name}: needs a 'type'")
    if spec["type"] == "string":
        return StringMedium(sc, name, spec)
    if spec["type"] == "open3d":
        _keys(spec, {"type"}, f"media.{name}")
        return Open3D(name)
    if spec["type"] == "gas":
        return GasMedium(sc, name, spec)
    if spec["type"] == "fluid":
        return FluidMedium(sc, name, spec)
    if spec["type"] == "rod":
        return RodMedium(sc, name, spec)
    if spec["type"] == "em":
        return EMMedium(sc, name, spec)
    raise SceneError(f"media.{name}: type '{spec['type']}' not supported yet (string, gas, fluid, rod, em, open3d)")


SPEED_OF_LIGHT = sp.Integer(299792458)          # m/s, exact SI
SOUND_SPEED_LIMIT = 10 ** 5                      # m/s: no sound in matter is this fast


def _not_light(v, w):
    """Refuse a gas or fluid whose 'speed of sound' is that of light (radar, radio)."""
    if sp.sympify(v).is_number and float(sp.N(v)) >= SOUND_SPEED_LIMIT:
        from .errors import PhysicalRangeError
        raise PhysicalRangeError(f"{w}: a speed of {sp.N(v, 6)} m/s is not sound in a gas or fluid; for light, radar or "
                         f"radio use a medium of type: em")


class EMMedium:
    """Light, radar or radio waves: no material medium. Speed c (exact SI) unless v or a
    refractive index n is given. The Doppler effect is relativistic (see doppler.py)."""
    KEYS = {"type", "v", "n", "c"}

    def __init__(self, sc, name, spec):
        w = f"media.{name}"
        _keys(spec, self.KEYS, w)
        self.name, self.kind, self.mu, self.extent, self.rho, self.wind = name, "em", None, None, None, None
        if "v" in spec and "n" in spec:
            raise SceneError(f"{w}: give v or n (refractive index), not both")
        # the problem's value of c (books often take 3e8 m/s): used for travel and for time
        # dilation alike; default the exact SI value
        self.c = sc.quantity(spec["c"], D_SPEED, f"{w}.c") if "c" in spec else SPEED_OF_LIGHT
        if "c" in spec and self.c.is_number and abs(float(sp.N(self.c / SPEED_OF_LIGHT)) - 1) > 0.01:
            raise SceneError(f"{w}.c: the speed of light is about 3e8 m/s; c sets the problem's rounded value only")
        if "n" in spec:
            n = sc.quantity(spec["n"], DIMLESS, f"{w}.n")
            if n.is_number and not n >= 1:
                raise SceneError(f"{w}.n: a refractive index is at least 1")
            if not n.is_number:
                sc.implicit_ineqs = getattr(sc, "implicit_ineqs", {})
                sc.implicit_ineqs[f"{w}.n"] = (f"{w}.n >= 1 (a refractive index)", ">=", n - 1)
            self.v = self.c / n
        elif "v" in spec:
            self.v = sc.quantity(spec["v"], D_SPEED, f"{w}.v")
            if self.v.is_number and self.v > self.c:
                raise SceneError(f"{w}.v: faster than light in vacuum (c = {self.c} m/s; for a book's rounded "
                                 f"c = 3e8 m/s write c: 3e8 m/s instead of v)")
        else:
            self.v = self.c

    @property
    def uniform(self):
        return True

    def speed(self, at=None):
        return self.v


def _wind(sc, spec, w):
    """The velocity of the air (a list of speeds), or None."""
    wind = spec.get("wind")
    if wind is None:
        return None
    if not isinstance(wind, list) or len(wind) not in (2, 3):
        raise SceneError(f"{w}.wind: a list of 2 or 3 speeds, like positions, e.g. [10 m/s, 0 m/s]")
    return [sc.quantity(c, D_SPEED, f"{w}.wind[{i}]") for i, c in enumerate(wind)]


class GasMedium:
    """Air or another gas: speed of sound given directly, or from gamma, P, rho, or from
    gamma, T, molar mass (uses the gas constant R, an exact SI constant)."""
    KEYS = {"type", "v", "gamma", "pressure", "density", "temperature", "molar_mass", "gas_constant", "wind"}

    def __init__(self, sc, name, spec):
        w = f"media.{name}"
        _keys(spec, self.KEYS, w)
        self.name, self.kind, self.mu, self.extent = name, "gas", None, None
        q = lambda k, d, **kw: sc.quantity(spec.get(k), d, f"{w}.{k}", **kw)
        gamma = q("gamma", DIMLESS)
        P, rho = q("pressure", D_PRESS), q("density", D_DENS)
        Tk, M = q("temperature", TEMP, temperature=True), q("molar_mass", MASS)
        R = q("gas_constant", dim(L=2, M=1, T=-2, K=-1))
        Rg = R_GAS if R is None else R
        cands, used = [q("v", D_SPEED)], {"type", "v", "density", "wind"}    # density is always a property
        self.wind = _wind(sc, spec, w)
        # density from the ideal-gas law when pressure, temperature and molar mass are all given
        rho_c = [rho]
        if P is not None and Tk is not None and M is not None:
            rho_c.append(P * M / (Rg * Tk))
            used |= {"pressure", "temperature", "molar_mass", "gas_constant"}
        rho = _pick(sc, rho_c, "density (given vs ideal gas P*M/(R*T))", w) if any(
            c is not None for c in rho_c) else None
        if gamma is not None and P is not None and rho is not None:
            cands.append(sp.sqrt(gamma * P / rho))
            used |= {"gamma", "pressure"}
        if gamma is not None and Tk is not None and M is not None:
            cands.append(sp.sqrt(gamma * Rg * Tk / M))
            used |= {"gamma", "temperature", "molar_mass", "gas_constant"}
        if all(c is None for c in cands):
            raise SceneError(f"{w}: give v, or gamma + pressure + density, or gamma + temperature + molar_mass")
        unused = sorted(set(spec) - used)
        if unused:
            raise SceneError(f"{w}: {unused} not used: they do not complete a route to the speed of "
                             f"sound (v; gamma + pressure + density; gamma + temperature + molar_mass "
                             f"[+ gas_constant]) or to the density (pressure + temperature + molar_mass)")
        self.v = _pick(sc, cands, "speed of sound", w)
        _not_light(self.v, w)
        if self.v.is_positive is False:
            raise SceneError(f"{w}: speed must be positive")
        self.rho = rho
        if rho is not None and rho.is_positive is False:
            raise SceneError(f"{w}: density must be positive")

    @property
    def uniform(self):
        return True

    def speed(self, at=None):
        return self.v


class FluidMedium(GasMedium):
    """A liquid (or any fluid): speed of sound from bulk modulus and density, or given."""
    KEYS = {"type", "v", "bulk_modulus", "compressibility", "density", "flow"}

    def __init__(self, sc, name, spec):
        w = f"media.{name}"
        _keys(spec, self.KEYS, w)
        self.wind = _wind(sc, dict(spec, wind=spec.get("flow")) if "flow" in spec else spec, w)
        self.name, self.kind, self.mu, self.extent = name, "fluid", None, None
        q = lambda k, d: sc.quantity(spec.get(k), d, f"{w}.{k}")
        kappa = q("compressibility", dim(1, -1, 2))
        B_c = [q("bulk_modulus", D_PRESS), 1 / kappa if kappa is not None else None]
        B = _pick(sc, B_c, "bulk modulus (vs 1/compressibility)", w) if any(c is not None for c in B_c) else None
        rho = q("density", D_DENS)
        cands = [q("v", D_SPEED), sp.sqrt(B / rho) if B is not None and rho is not None else None]
        if all(c is None for c in cands):
            raise SceneError(f"{w}: give v, or bulk_modulus + density")
        if B is not None and rho is None:
            raise SceneError(f"{w}: bulk_modulus needs density")
        for label, val in (("bulk_modulus", B), ("density", rho)):
            if val is not None and val.is_positive is False:
                raise SceneError(f"{w}: {label} must be positive")
        self.v = _pick(sc, cands, "speed of sound", w)
        _not_light(self.v, w)
        if self.v.is_positive is False:
            raise SceneError(f"{w}: speed must be positive")
        self.rho = rho


class RodMedium:
    """A solid rod or wire carrying longitudinal waves: v = sqrt(Y / density)."""
    KEYS = {"type", "v", "Y", "density", "mass", "length", "area", "diameter"}

    def __init__(self, sc, name, spec):
        w = f"media.{name}"
        _keys(spec, self.KEYS, w)
        self.name, self.kind, self.mu, self.extent = name, "rod", None, None
        q = lambda k, d: sc.quantity(spec.get(k), d, f"{w}.{k}")
        Y, length, mass = q("Y", D_PRESS), q("length", LENGTH), q("mass", MASS)
        area = _pick(sc, [q("area", D_AREA), sp.pi * q("diameter", LENGTH) ** 2 / 4
                          if spec.get("diameter") is not None else None], "cross-section", w) \
            if (spec.get("area") is not None or spec.get("diameter") is not None) else None
        rho_c = [q("density", D_DENS)]
        if mass is not None:
            if length is None or area is None:
                raise SceneError(f"{w}: mass needs length and area (or diameter) to give the density")
            rho_c.append(mass / (length * area))
        rho = _pick(sc, rho_c, "density", w) if any(c is not None for c in rho_c) else None
        if Y is not None and rho is None:
            raise SceneError(f"{w}: Y needs the density (or mass + length + area) to give the speed")
        if rho is not None and Y is None and "v" not in spec:
            raise SceneError(f"{w}: give Y with the density, or v")
        cands = [q("v", D_SPEED), sp.sqrt(Y / rho) if Y is not None and rho is not None else None]
        if all(c is None for c in cands):
            raise SceneError(f"{w}: give v, or Y + density (or Y + mass + length + area)")
        self.v = _pick(sc, cands, "longitudinal speed", w)
        if self.v.is_positive is False:
            raise SceneError(f"{w}: speed must be positive")
        self.rho, self.length, self.area = rho, length, area

    @property
    def uniform(self):
        return True

    def speed(self, at=None):
        return self.v


ACOUSTIC_MEDIA = (GasMedium, RodMedium)      # FluidMedium is a GasMedium


def acoustic_density(medium, what):
    rho = getattr(medium, "rho", None)
    if rho is None:
        raise UndeterminedError(f"{what} needs the density of '{medium.name}' (add density to the medium)")
    return rho


class Open3D:
    def __init__(self, name):
        self.name = name


def _must_be_positive(sc, q, where):
    """A number must be positive now; a symbol becomes an implicit condition (checked when
    the facts are solved)."""
    q = sp.sympify(q)
    if q.is_number:
        if not q > 0:
            raise SceneError(f"{where} must be positive (got {q})")
    elif q.is_positive is not True:
        sc.implicit_ineqs[where] = (f"{where} > 0", ">", q)


def _load_tension(sc, spec, w):
    """T = M g (a hanging load), less the buoyancy of the immersed part: T = M g - rho_f V g."""
    if not isinstance(spec, dict):
        raise SceneError(f"{w}: {{mass: M, g: g, buoyancy: {{...}}}} (buoyancy optional)")
    _keys(spec, {"mass", "g", "buoyancy"}, w)
    if "mass" not in spec or "g" not in spec:
        raise SceneError(f"{w}: give mass and g (g as the problem states it, e.g. 9.8 m/s^2 or 10 m/s^2)")
    M = sc.quantity(spec["mass"], MASS, f"{w}.mass")
    _must_be_positive(sc, M, f"{w}.mass")
    g = sc.quantity(spec["g"], D_ACC, f"{w}.g")
    _must_be_positive(sc, g, f"{w}.g")
    T = M * g
    b = spec.get("buoyancy")
    if b is not None:
        if not isinstance(b, dict):
            raise SceneError(f"{w}.buoyancy: {{fluid_density, volume}} or {{fluid_density, load_density, fraction}}")
        _keys(b, {"fluid_density", "volume", "load_density", "fraction"}, f"{w}.buoyancy")
        if "fluid_density" not in b:
            raise SceneError(f"{w}.buoyancy: needs fluid_density")
        rf = sc.quantity(b["fluid_density"], D_DENS, f"{w}.buoyancy.fluid_density")
        if ("volume" in b) == ("load_density" in b):
            raise SceneError(f"{w}.buoyancy: give exactly one of volume (immersed) or load_density "
                             f"(with fraction immersed, default 1)")
        if "volume" in b:
            if "fraction" in b:
                raise SceneError(f"{w}.buoyancy: fraction goes with load_density, not with volume")
            V = sc.quantity(b["volume"], dim(L=3), f"{w}.buoyancy.volume")
        else:
            rb = sc.quantity(b["load_density"], D_DENS, f"{w}.buoyancy.load_density")
            x = sc.quantity(b.get("fraction", 1), DIMLESS, f"{w}.buoyancy.fraction")
            if x.is_number and not (0 < x <= 1):
                raise SceneError(f"{w}.buoyancy.fraction: between 0 and 1")
            if not x.is_number:
                _must_be_positive(sc, x, f"{w}.buoyancy.fraction")
                sc.implicit_ineqs[f"{w}.buoyancy.fraction<=1"] = (f"{w}.buoyancy.fraction <= 1", "<=", x - 1)
            V = x * M / rb
        T = M * g - rf * V * g
    T = sp.simplify(T)
    if T.is_positive is False or (T.is_number and not T > 0):
        raise SceneError(f"{w}: the buoyancy is at least the weight (T = {T}): the load floats and the string "
                         f"is slack")
    return T


def _stretch_tension(sc, spec, w, area):
    """T = Y A dL/L0 (a stretched wire) or T = k dL (a spring)."""
    if not isinstance(spec, dict):
        raise SceneError(f"{w}: {{Y, area, extension, length}} or {{k, extension}}")
    _keys(spec, {"Y", "area", "extension", "length", "k"}, w)
    if "extension" not in spec:
        raise SceneError(f"{w}: needs extension")
    dL = sc.quantity(spec["extension"], LENGTH, f"{w}.extension")
    if dL.is_positive is False or (dL.is_number and not dL > 0):
        raise SceneError(f"{w}.extension must be positive")
    if "k" in spec:
        if {"Y", "area", "length"} & set(spec):
            raise SceneError(f"{w}: give k (a spring) or Y, area, length (a wire), not both")
        k = sc.quantity(spec["k"], dim(M=1, T=-2), f"{w}.k")
        _must_be_positive(sc, k, f"{w}.k")
        return k * dL
    if "Y" not in spec or "length" not in spec:
        raise SceneError(f"{w}: a stretched wire needs Y, length (unstretched) and area (here or on the string)")
    Y = sc.quantity(spec["Y"], D_PRESS, f"{w}.Y")
    _must_be_positive(sc, Y, f"{w}.Y")
    L0 = sc.quantity(spec["length"], LENGTH, f"{w}.length")
    _must_be_positive(sc, L0, f"{w}.length")
    A = sc.quantity(spec["area"], dim(L=2), f"{w}.area") if "area" in spec else area
    if A is None:
        raise SceneError(f"{w}: needs area (here, or area/diameter on the string)")
    if "area" in spec and area is not None and A.is_number and sp.sympify(area).is_number:
        # books round pi (3.14 mm^2 for a 2 mm wire): allow 1 %; use the stated area
        if abs(float(sp.N(A / area)) - 1) > 0.01:
            raise SceneError(f"{w}.area differs from the string's own area (more than 1 %)")
    return Y * A * dL / L0


class StringMedium:
    KEYS = {"type", "mu", "mass", "length", "density", "area", "diameter", "Y", "alpha",
            "tension", "coordinate", "ends"}

    def __init__(self, sc, name, spec):
        w = f"media.{name}"
        _keys(spec, self.KEYS, w)
        self.name = name
        q = lambda k, d: sc.quantity(spec.get(k), d, f"{w}.{k}")
        self.length = q("length", LENGTH)
        self.density = q("density", D_DENS)
        area = q("area", D_AREA)
        dia = q("diameter", LENGTH)
        area = _pick(sc, [area, sp.pi * dia ** 2 / 4 if dia is not None else None],
                     "cross-section (area vs diameter)", w)
        self.area = area
        mass = q("mass", MASS)
        mu_c = [q("mu", D_LINDENS)]
        if mass is not None:
            if self.length is None:
                raise SceneError(f"{w}: 'mass' needs 'length'")
            mu_c.append(mass / self.length)
        if self.density is not None and area is not None:
            mu_c.append(self.density * area)
        self.mu = _pick(sc, mu_c, "mass per length", w)
        self.ends = spec.get("ends") or {}
        for side, kind in self.ends.items():
            if side not in ("left", "right") or kind not in ("driven", "absorbing", "fixed", "free"):
                raise SceneError(f"{w}.ends: use left/right: driven|absorbing|fixed|free")
            if kind in ("fixed", "free"):
                raise SceneError(f"{w}.ends: {kind} ends (reflection) are not modelled in v0")
        self.extent = None          # (lo, hi) set by junctions
        coord = spec.get("coordinate") or {}
        _keys(coord, {"origin", "direction", "variable"}, f"{w}.coordinate")
        self.origin = coord.get("origin")
        self.direction = coord.get("direction")

        self.kind, self.T, self.stress, self.s = None, None, None, sp.Dummy("s_" + name, real=True)
        self.var = None
        if coord and "variable" not in coord:
            raise SceneError(f"{w}.coordinate: name the position variable too, e.g. "
                             f"{{origin: lower_end, direction: up, variable: s}} with s declared in `symbols`")
        if "variable" in coord:
            v = sc.names.get(coord["variable"])
            if not isinstance(v, sp.Symbol) or v not in sc.kinds or v in sc.unknowns:
                raise SceneError(f"{w}.coordinate.variable: a symbol declared in `symbols` (the position "
                                 f"along the string, from the origin)")
            if self.origin is None or self.direction is None:
                raise SceneError(f"{w}.coordinate: a variable needs origin and direction too")
            self.var = self.s = v
            sc.symbol_dims[v] = LENGTH
        if self.mu is not None and self.mu.has(self.s) and self.var is None:
            raise SceneError(f"{w}: mu depends on the position; declare it with coordinate: {{variable: ...}}")
        ten = spec.get("tension")
        if ten is None:
            raise SceneError(f"{w}: needs 'tension' (a value, hanging, thermal, or free)")
        if ten == "free":
            self.kind = "free"
        elif isinstance(ten, dict):
            if set(ten) == {"hanging"}:
                h = ten["hanging"]
                _keys(h, {"load", "g"}, f"{w}.tension.hanging")
                if self.mu is None:
                    raise SceneError(f"{w}: hanging tension needs mass per length")
                if (self.origin, self.direction) != ("lower_end", "up"):
                    raise SceneError(f"{w}: hanging string needs coordinate {{origin: lower_end, direction: up}}")
                load = sc.quantity(h["load"], MASS, f"{w}.tension.hanging.load")
                g = sc.quantity(h["g"], D_ACC, f"{w}.tension.hanging.g")
                self.kind = "hanging"
                u = sp.Dummy("u", nonnegative=True)
                below = sp.integrate(self.mu.xreplace({self.s: u}), (u, 0, self.s))
                self.T = load * g + g * below    # weight of load + string below s
            elif set(ten) == {"thermal"}:
                th = ten["thermal"]
                _keys(th, {"slack_at", "now"}, f"{w}.tension.thermal")
                Y, alpha = q("Y", D_PRESS), q("alpha", dim(K=-1))
                if Y is None or alpha is None or self.density is None:
                    raise SceneError(f"{w}: thermal tension needs Y, alpha and density")
                t0 = sc.quantity(th["slack_at"], TEMP, f"{w}.slack_at", temperature=True)
                t1 = sc.quantity(th["now"], TEMP, f"{w}.now", temperature=True)
                dT = sp.nsimplify(t0 - t1)
                if dT.is_positive is False:
                    raise SceneError(f"{w}: wire is slack (now >= slack_at); no tension")
                self.kind = "thermal"
                self.stress = Y * alpha * dT
                self.T = self.stress * area if area is not None else None
            elif set(ten) == {"weight"}:
                self.kind = "uniform"
                self.T = _load_tension(sc, ten["weight"], f"{w}.tension.weight")
            elif set(ten) == {"stretch"}:
                self.kind = "uniform"
                self.T = _stretch_tension(sc, ten["stretch"], f"{w}.tension.stretch", area)
                if self.T.is_positive is False or (self.T.is_number and not self.T > 0):
                    raise SceneError(f"{w}.tension: must be positive (got {self.T})")
            else:
                raise SceneError(f"{w}.tension: use one of a value, {{weight: ...}}, {{stretch: ...}}, "
                                 f"{{hanging: ...}}, {{thermal: ...}} or free")
        else:
            self.kind = "uniform"
            self.T = sc.quantity(ten, FORCE, f"{w}.tension")
            if self.T.is_positive is False:
                raise SceneError(f"{w}.tension must be positive (got {self.T})")

    @property
    def uniform(self):
        return self.kind != "hanging" and not (self.mu is not None and self.mu.has(self.s))

    def _at(self, at):
        """Position for a non-uniform string; refuse a position symbol that mu uses
        without being declared as the coordinate variable."""
        if at is not None and self.var is None and self.mu is not None:
            shared = sp.sympify(at).free_symbols & self.mu.free_symbols
            if shared:
                raise SceneError(f"'{self.name}': mu uses {sorted(map(str, shared))}, which you also use "
                                 f"as a position; if mu varies along the string, declare "
                                 f"coordinate: {{variable: {sorted(map(str, shared))[0]}}}")
        return at

    def speed(self, at=None):
        at = self._at(at)
        if self.kind == "free":
            raise UndeterminedError(f"speed on '{self.name}' is set by its wave (tension: free)")
        if self.kind == "thermal":
            return sp.sqrt(self.stress / self.density)
        if self.mu is None:
            raise UndeterminedError(f"'{self.name}' has no mass per length")
        if not self.uniform:
            if at is None:
                raise SceneError(f"'{self.name}' is non-uniform: give at=<position>")
            return sp.sqrt((self.T / self.mu).subs(self.s, at))
        return sp.sqrt(self.T / self.mu)

    def tension(self, at=None):
        at = self._at(at)
        if self.kind == "free":
            raise UndeterminedError(f"tension of '{self.name}' is set by its wave (tension: free)")
        if self.T is None:
            raise UndeterminedError(f"tension of '{self.name}' is not determined: thermal tension "
                                    f"needs the cross-section (area or diameter)")
        if self.kind == "hanging":
            if at is None:
                raise SceneError(f"'{self.name}' is non-uniform: give at=<position>")
            return self.T.subs(self.s, at)
        return self.T


# ============================== waves =========================================
def make_wave(sc, name, spec):
    if not isinstance(spec, dict) or len({"harmonic", "given", "pulse", "sum"} & set(spec)) != 1:
        raise SceneError(f"waves.{name}: use exactly one of harmonic / given / pulse / sum")
    if "harmonic" in spec:
        _keys(spec, {"harmonic"}, f"waves.{name}")
        return Harmonic(sc, name, spec["harmonic"])
    if "given" in spec:
        return GivenWave(sc, name, spec)
    if "pulse" in spec:
        _keys(spec, {"pulse"}, f"waves.{name}")
        if isinstance(spec["pulse"], dict) and "shape" in spec["pulse"]:
            return ShapedPulse(sc, name, spec["pulse"])
        return Pulse(sc, name, spec["pulse"])
    if "sum" in spec:
        return SumWave(sc, name, spec)
    raise SceneError(f"waves.{name}: use one of harmonic / given / pulse / sum")


def _direction(sc, spec, medium, w):
    if "dir" in spec and "from" in spec:
        raise SceneError(f"{w}: give either dir or from, not both")
    if "dir" in spec:
        d = spec["dir"]
        if d in ("+x", "-x"):
            return 1 if d == "+x" else -1
        sym = sc.names.get(d)
        if sym is None or sc.kinds.get(sym) != "direction":
            raise SceneError(f"{w}.dir must be +x, -x or an unknown of kind direction")
        return sym
    frm = spec.get("from")
    if frm == "left":
        return 1
    if frm == "right":
        return -1
    if frm is not None and medium is not None and frm == getattr(medium, "origin", None):
        if spec.get("toward") not in (None, medium.direction):
            raise SceneError(f"{w}: 'toward' must point along the medium coordinate")
        return 1
    if frm is not None:
        raise SceneError(f"{w}.from: use left, right or the medium's coordinate origin")
    return None


class Harmonic:
    KEYS = {"on", "A", "f", "omega", "period", "lambda", "k", "v", "dir",
            "phase", "from", "toward", "pressure_amplitude", "intensity"}

    def __init__(self, sc, name, spec):
        w = f"waves.{name}"
        _keys(spec, self.KEYS, w)
        self.name, self.sc = name, sc
        self.medium = None
        if "on" in spec:
            if spec["on"] not in sc.objects or not isinstance(sc.objects[spec["on"]], (StringMedium, GasMedium,
                                                                                      RodMedium)):
                raise SceneError(f"{w}.on: '{spec['on']}' is not a string, gas, fluid or rod medium defined above")
            self.medium = sc.objects[spec["on"]]
        q = lambda k, d: sc.quantity(spec.get(k), d, f"{w}.{k}")
        self.A = q("A", LENGTH)
        self.phi = q("phase", DIMLESS)
        f, period = q("f", D_FREQ), q("period", TIME)
        om = _pick(sc, [q("omega", D_FREQ), TWO_PI * f if f is not None else None,
                        TWO_PI / period if period is not None else None], "frequency", w)
        lam = q("lambda", LENGTH)
        k = _pick(sc, [q("k", D_WAVENUM), TWO_PI / lam if lam is not None else None], "wavelength", w)
        self.sign = _direction(sc, spec, self.medium, w)
        if self.sign is None:
            raise SceneError(f"{w}: give dir (+x, -x or a direction unknown) or from")
        for label, val in (("A", self.A), ("frequency", om), ("k", k), ("v", q("v", D_SPEED))):
            if val is not None and val.is_positive is False:
                raise SceneError(f"{w}: {label} must be positive (got {val})")

        self.nonuniform = self.medium is not None and not self.medium.uniform
        if self.nonuniform:
            if k is not None or "v" in spec:
                raise SceneError(f"{w}: on a non-uniform medium give only frequency (and A, phase)")
            if om is None:
                raise SceneError(f"{w}: needs a frequency")
            self.omega, self.k, self.v = om, None, None
            return

        v_c = [q("v", D_SPEED)]
        if self.medium is not None and self.medium.kind != "free":
            v_c.append(self.medium.speed())
        v = _pick(sc, v_c, "wave speed", w)
        if om is not None and k is not None and v is not None:
            same = _same(om, k * v)
            if same is False:
                raise SceneError(f"{w}: frequency, wavelength and speed are inconsistent (omega != k*v)")
            if same is None:
                sc.implicit.append((f"{w}: omega = k*v", om - k * v))
        elif om is not None and k is not None:
            v = om / k
        elif om is not None and v is not None:
            k = om / v
        elif k is not None and v is not None:
            om = k * v
        self.omega, self.k, self.v = om, k, v
        # sound: the amplitude may be stated as displacement, pressure or intensity (exactly one)
        amp_keys = [a for a in ("A", "pressure_amplitude", "intensity") if a in spec]
        if len(amp_keys) > 1:
            raise SceneError(f"{w}: give one amplitude: A (displacement), pressure_amplitude or intensity")
        if amp_keys and amp_keys[0] != "A":
            if not isinstance(self.medium, ACOUSTIC_MEDIA):
                raise SceneError(f"{w}.{amp_keys[0]}: only for sound waves (on a gas, fluid or rod medium)")
            if self.omega is None:
                raise SceneError(f"{w}: {amp_keys[0]} needs the frequency")
            rho = acoustic_density(self.medium, f"{w}.{amp_keys[0]}")
            if amp_keys[0] == "pressure_amplitude":
                p0 = sc.quantity(spec["pressure_amplitude"], D_PRESS, f"{w}.pressure_amplitude")
            else:
                inten = sc.quantity(spec["intensity"], dim(0, 1, -3), f"{w}.intensity")
                p0 = sp.sqrt(2 * rho * self.v * inten)
            if p0.is_positive is False:
                raise SceneError(f"{w}.{amp_keys[0]} must be positive")
            self.A = p0 / (rho * self.v * self.omega)       # p0 = rho v omega s0

    def _need(self, *attrs):
        for a in attrs:
            if getattr(self, a) is None:
                label = {"A": "amplitude", "phi": "phase", "omega": "frequency", "k": "wavelength",
                         "v": "speed"}[a]
                raise UndeterminedError(f"wave '{self.name}': {label} is not specified")

    def _theta(self, x, t):
        self._need("phi", "omega", "k")
        return self.omega * t - self.sign * self.k * x + self.phi

    def field(self):
        self._need("A", "phi", "omega", "k")
        return self.A * sp.sin(self._theta(X, T))      # A may be negative for derived waves

    def phase_expr(self, x, t):
        """Argument of A*sin(.) written with A > 0 (adds pi when the signed amplitude is negative)."""
        th = self._theta(x, t)
        if self.A is None or self.A.is_positive:
            return th
        if self.A.is_negative:
            return th + sp.pi
        raise UndeterminedError(f"wave '{self.name}': sign of its amplitude is not determined, "
                                f"so its phase is ambiguous by pi")

    def velocity(self):
        self._need("v")
        return self.sign * self.v

    def speed(self):
        return sp.Abs(self.velocity())

    def amplitude(self):
        self._need("A")
        return sp.Abs(self.A)

    def offset(self):
        return sp.Integer(0)

    def ang_freq(self):
        self._need("omega")
        return self.omega

    def wavenumber(self, at=None):
        if self.nonuniform:
            if at is None:
                raise SceneError(f"wave '{self.name}' is on a non-uniform medium: give at=<position>")
            return self.omega / self.medium.speed(at)
        self._need("k")
        return self.k

    def power(self):
        if self.medium is None or self.medium.mu is None:
            raise UndeterminedError(f"power of '{self.name}' needs a medium with mass per length")
        if self.nonuniform:
            raise SceneError("power on a non-uniform medium is not supported in v0")
        self._need("A", "omega")
        return sp.Rational(1, 2) * self.medium.mu * self.omega ** 2 * self.A ** 2 * self.speed()

    def extent_check(self, x):
        _check_extent(self.medium, x, self.name)


class _Cancelled(SceneError):
    """The parts of a wave cancel everywhere: amplitude 0, other properties undefined."""


class GivenWave:
    """A wave supplied as an explicit y(x, t). Properties are found by analysis."""

    def __init__(self, sc, name, spec):
        w = f"waves.{name}"
        _keys(spec, {"given", "units", "on"}, w)
        self.name, self.medium = name, None
        if "on" in spec:
            self.medium = sc.objects.get(spec["on"])
            if not isinstance(self.medium, StringMedium):
                raise SceneError(f"{w}.on: not a string medium")
        units = spec.get("units") or {}
        _keys(units, {"x", "y", "t"}, f"{w}.units")
        if set(units) != {"x", "y", "t"}:
            raise SceneError(f"{w}: give units for x, y and t (e.g. units: {{x: m, t: s, y: m}})")
        fac = {}
        for var, d in (("x", LENGTH), ("t", TIME), ("y", LENGTH)):
            if var in units:
                _, _, factor, udim = split_quantity("1 " + units[var])
                if udim != d:
                    raise SceneError(f"{w}.units.{var}: wrong dimension")
                fac[var] = factor
            else:
                fac[var] = sp.Integer(1)
        raw = sc.expr(spec["given"])
        if raw.free_symbols - set(sc.names.values()):
            raise SceneError(f"{w}: formula uses undeclared symbols")
        self.f = fac["y"] * raw.xreplace({X: X / fac["x"], T: T / fac["t"]})
        self._sin = None
        travelling = True
        if self.medium is not None:
            try:
                self.velocity()
            except SceneError:
                travelling = False      # e.g. a standing wave given directly: no single speed to compare
        if travelling and self.medium is not None and self.medium.uniform and self.medium.kind != "free":
            same = _same(self.speed(), self.medium.speed())
            if same is False:
                raise SceneError(f"{w}: formula speed {self.speed()} differs from the medium's "
                                 f"{sp.N(self.medium.speed(), 6)}")
            if same is None:
                sc.implicit.append((f"{w}: formula speed = medium speed",
                                    self.speed() - self.medium.speed()))

    def field(self):
        return self.f

    def velocity(self):
        yt, yx = sp.diff(self.f, T), sp.diff(self.f, X)
        if yx == 0:
            raise SceneError(f"wave '{self.name}' does not depend on x")
        c = sp.simplify(-yt / yx)
        if c.has(X, T):
            raise SceneError(f"wave '{self.name}' is not a travelling wave of fixed shape")
        return c

    def speed(self):
        return sp.Abs(self.velocity())

    def sinusoid(self):
        """Write the field as offset + C*sin(theta) with C > 0 and theta = w*t + kx*x + c,
        w > 0, combining every term of the same frequency and wavenumber (phasors)."""
        if self._sin is None:
            e = sp.expand(TR8(sp.expand(self.f)))
            terms = sp.Add.make_args(e)
            offset = sp.Add(*[a for a in terms if not a.has(X, T)])
            rest = [a for a in terms if a.has(X, T)]
            if not rest:
                raise _Cancelled(f"wave '{self.name}' does not oscillate (its amplitude is 0)")
            groups = {}
            for term in rest:
                C, trig = term.as_independent(X, T, as_Add=False)
                if not isinstance(trig, (sp.sin, sp.cos)):
                    raise SceneError(f"wave '{self.name}' is not a sum of sinusoids")
                arg = sp.expand(trig.args[0])
                wt, kx = sp.diff(arg, T), sp.diff(arg, X)
                if wt.has(X, T) or kx.has(X, T):
                    raise SceneError(f"wave '{self.name}' has a non-linear phase")
                c = sp.expand(arg - wt * T - kx * X)
                flip = sp.sign(wt) if wt != 0 else sp.sign(kx)
                if flip not in (1, -1):
                    raise UndeterminedError(f"wave '{self.name}': sign of a frequency is not determined")
                if flip == -1:                       # sin(-u) = -sin(u), cos(-u) = cos(u)
                    wt, kx, c = -wt, -kx, -c
                    if isinstance(trig, sp.sin):
                        C = -C
                key = (sp.simplify(wt), sp.simplify(kx))
                # C*sin(u + c) = C cos c sin u + C sin c cos u ; C*cos(u + c) = -C sin c sin u + C cos c cos u
                a_ = C * sp.cos(c) if isinstance(trig, sp.sin) else -C * sp.sin(c)
                b_ = C * sp.sin(c) if isinstance(trig, sp.sin) else C * sp.cos(c)
                pa, pb = groups.get(key, (0, 0))
                groups[key] = (pa + a_, pb + b_)
            if len(groups) != 1:
                raise SceneError(f"wave '{self.name}' is a sum of {len(groups)} different sinusoids, "
                                 f"not a single one")
            (wt, kx), (a_, b_) = next(iter(groups.items()))
            a_, b_ = sp.simplify(a_), sp.simplify(b_)
            C = sp.simplify(sp.sqrt(a_ ** 2 + b_ ** 2))
            if C == 0:
                raise _Cancelled(f"wave '{self.name}': the sinusoids cancel (amplitude 0); "
                                 f"its phase, frequency and wavelength are undefined")
            arg = wt * T + kx * X + sp.atan2(b_, a_)        # kx here is d(arg)/dx
            self._sin = (offset, C, sp.sin, arg, wt, kx)
        return self._sin

    def amplitude(self):
        try:
            return self.sinusoid()[1]
        except _Cancelled:
            return sp.Integer(0)

    def offset(self):
        return self.sinusoid()[0]

    def ang_freq(self):
        return sp.Abs(self.sinusoid()[4])

    def wavenumber(self, at=None):
        return sp.Abs(self.sinusoid()[5])

    def phase_expr(self, x, t):
        """Argument theta of A*sin(theta) with A > 0 and theta increasing in time."""
        return self.sinusoid()[3].xreplace({X: x, T: t})

    def power(self):
        if self.medium is None or self.medium.mu is None:
            raise UndeterminedError(f"power of '{self.name}' needs 'on: <string medium>'")
        return (sp.Rational(1, 2) * self.medium.mu * self.ang_freq() ** 2 *
                self.amplitude() ** 2 * self.speed())


class Pulse:
    def __init__(self, sc, name, spec):
        w = f"waves.{name}"
        _keys(spec, {"on", "from", "toward"}, w)
        self.name = name
        self.medium = sc.objects.get(spec.get("on"))
        if not isinstance(self.medium, StringMedium):
            raise SceneError(f"{w}.on: must be a string medium")
        if _direction(sc, spec, self.medium, w) != 1:
            raise SceneError(f"{w}: v0 supports pulses launched from the coordinate origin forward")
        if any(self.medium in J.side.values() for J in getattr(sc, "junctions", [])):
            raise SceneError(f"{w}: a pulse without a shape cannot meet a junction; give it a `shape` "
                             f"(y at t = 0) so it can be reflected and transmitted")

    def front(self, t):
        S, tau = sp.Dummy("S", positive=True), sp.Dummy("tau", positive=True)
        s = self.medium.s
        tt = sp.integrate(1 / self.medium.speed(s), (s, 0, S))
        sols = sp.solve(sp.Eq(tt, tau), S)
        if len(sols) != 1:
            raise SceneError(f"pulse '{self.name}': cannot invert travel time")
        return sp.simplify(sols[0].subs(tau, t))


class ShapedPulse(GivenWave):
    """A pulse of stated shape y(x, 0) moving at the medium speed: y = shape(x - s v t).
    Valid on uniform, non-dispersive strings (d'Alembert)."""
    KEYS = {"on", "shape", "units", "dir"}

    def __init__(self, sc, name, spec):
        w = f"waves.{name}"
        _keys(spec, self.KEYS, w)
        self.name, self._sin = name, None
        self.medium = sc.objects.get(spec.get("on"))
        if not isinstance(self.medium, StringMedium):
            raise SceneError(f"{w}.on: a shaped pulse needs a string medium")
        if not self.medium.uniform or self.medium.kind == "free":
            raise SceneError(f"{w}: a shaped pulse needs a uniform string with a known speed. On a "
                             f"non-uniform string the pulse reflects continuously and does not keep its "
                             f"shape; use a pulse without a shape and front(...) there")
        units = spec.get("units") or {}
        _keys(units, {"x", "y"}, f"{w}.units")
        if set(units) != {"x", "y"}:
            raise SceneError(f"{w}: give units for the shape, e.g. units: {{x: m, y: m}}")
        fac = {}
        for var, d in (("x", LENGTH), ("y", LENGTH)):
            _, _, factor, udim = split_quantity("1 " + units[var])
            if udim != d:
                raise SceneError(f"{w}.units.{var}: wrong dimension")
            fac[var] = factor
        raw = sc.expr(spec["shape"])
        if raw.has(T):
            raise SceneError(f"{w}.shape: the shape is y at t = 0 and must not contain t")
        if raw.free_symbols - set(sc.names.values()):
            raise SceneError(f"{w}: shape uses undeclared symbols")
        d = spec.get("dir")
        if d not in ("+x", "-x"):
            raise SceneError(f"{w}.dir: +x or -x")
        self.sign = 1 if d == "+x" else -1
        self.g = fac["y"] * raw.xreplace({X: X / fac["x"]})
        self.v = self.medium.speed()
        self.f = self.g.xreplace({X: X - self.sign * self.v * T})
        self.derived_from = None

    @classmethod
    def derived(cls, name, medium, g, sign, v, origin, coef=None, parent=None):
        p = cls.__new__(cls)
        p.name, p._sin, p.medium, p.g, p.sign, p.v = name, None, medium, g, sign, v
        p.f = g.xreplace({X: X - sign * v * T})
        p.derived_from, p.coef, p.parent = origin, coef, parent
        return p

    def peak(self):
        if getattr(self, "parent", None) is not None:      # reflection/transmission: |coef| x incident peak
            return sp.Abs(self.coef) * self.parent.peak()
        # the pulse's own amplitude: largest |shape| (for a reflected pulse this is |r| times the
        # incident peak, wherever the image happens to be at t = 0)
        return _peak_of(self.g, X, None, f"pulse '{self.name}'")

    def velocity(self):
        return self.sign * self.v


def _extreme_values(e, var, dom, points=False):
    """Candidate values of e over the interval dom: interval ends (or limits at infinity),
    breakpoints of piecewise parts (both sides), and interior critical points of each piece.
    Works for shapes built from max/min/abs/step as well as smooth formulas."""
    pw = sp.piecewise_fold(sp.sympify(e).rewrite(sp.Piecewise))
    pieces = [a for a, _ in pw.args] if isinstance(pw, sp.Piecewise) else [pw]
    conds = [c for _, c in pw.args] if isinstance(pw, sp.Piecewise) else []
    pts = set()
    for c in conds:
        for rel in ([c] if isinstance(c, sp.Rel) else list(c.atoms(sp.Rel))):
            roots = sp.solveset(rel.lhs - rel.rhs, var, sp.S.Reals)
            if isinstance(roots, sp.FiniteSet):
                pts.update(roots)
    regions = [c for _, c in pw.args] if isinstance(pw, sp.Piecewise) else [sp.true]
    taken = sp.S.EmptySet                  # Piecewise: a piece applies where no earlier one did
    for p, c in zip(pieces, regions):
        try:
            cset = c.as_set() if c is not sp.true else sp.S.Reals
            region = cset.intersect(dom) - taken
            taken = taken.union(cset)
        except Exception:
            region = dom
        if not p.has(var):
            continue
        if region is sp.S.EmptySet:
            continue
        crit = sp.solveset(sp.diff(p, var), var, region)
        if crit is sp.S.EmptySet:
            continue
        if not isinstance(crit, sp.FiniteSet):
            raise SceneError(f"cannot locate the extremes of {p}")
        pts.update(crit)
    if any(not q.is_number for q in pts):
        raise SceneError("the extremes depend on a symbol (a symbolic position or instant); give numbers")
    pts = {q for q in pts if dom.contains(q) is sp.true}
    vals, where = [], []
    eps = sp.Rational(1, 10 ** 9)
    for q in pts:
        for qq in (q, q - eps, q + eps):
            if dom.contains(qq) is sp.true:
                vals.append(sp.sympify(e).xreplace({var: qq}))
                where.append(q)
    for end_, side in ((dom.inf, "+"), (dom.sup, "-")):
        if end_.is_infinite:
            try:
                vals.append(sp.limit(pw, var, end_))
            except Exception:
                # the far tail of a piecewise shape: its value well beyond every breakpoint
                far = max([abs(float(sp.N(q))) for q in pts] + [1]) * 10 ** 6
                vals.append(pw.xreplace({var: far if end_ is sp.oo else -far}))
        else:
            vals.append(sp.sympify(e).xreplace({var: end_}))
        where.append(None if end_.is_infinite else end_)
    if points:
        return [(w_, v) for w_, v in zip(where, vals) if v.is_finite is not False]
    return [v for v in vals if v.is_finite is not False]


class _Budget(Exception):
    pass


def _within(seconds, fn):
    """Run fn with a time budget (POSIX); raises _Budget when it runs out. The outer evaluation
    alarm is restored afterwards with its remaining time."""
    import signal
    import time
    if not hasattr(signal, "SIGALRM"):
        return fn()
    remaining = signal.alarm(0)
    old = signal.getsignal(signal.SIGALRM)
    t0 = time.time()

    def stop(*_):
        raise _Budget()
    signal.signal(signal.SIGALRM, stop)
    signal.alarm(seconds if not remaining else min(seconds, remaining))
    try:
        return fn()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)
        if remaining:
            signal.alarm(max(1, int(remaining - (time.time() - t0))))


def _numeric_extremum(e, var, dom):
    """(x, |e|) of the largest |e| for a purely numeric e, as decimals, and whether another
    place reaches the same value (a tie). Candidates: the extremes of each additive term
    (found exactly, term by term), plus a coarse scan; each is refined by golden section on
    a window scaled to the term's own width."""
    import numpy as np
    f = sp.lambdify(var, e, modules=["numpy"])
    absf = lambda u: abs(float(f(u)))
    lo = float(dom.inf) if dom.inf.is_finite else -1e9
    hi = float(dom.sup) if dom.sup.is_finite else 1e9
    seeds = []
    for term in sp.Add.make_args(sp.expand(e)):
        if not term.has(var):
            continue
        try:
            pts = _within(5, lambda: _extreme_values(term, var, dom, points=True))
            seeds += [float(sp.N(q)) for q, _ in pts if q is not None]
        except Exception:
            continue
    grid = np.linspace(max(lo, -50), min(hi, 50), 20001)
    with np.errstate(all="ignore"):
        vals = np.abs(np.asarray(f(grid), dtype=float) * np.ones_like(grid))
    vals[~np.isfinite(vals)] = 0
    seeds += [float(grid[k]) for k in np.argsort(vals)[::-1][:20]]
    seeds = sorted({min(max(x0, lo), hi) for x0 in seeds})
    best = []
    for x0 in seeds:
        for w in (1e-3, 1e-1, 1.0):
            a, b = max(lo, x0 - w), min(hi, x0 + w)
            for _ in range(100):
                c, d = b - (b - a) / 1.618033988749895, a + (b - a) / 1.618033988749895
                if absf(c) > absf(d):
                    b = d
                else:
                    a = c
            xm = (a + b) / 2
            best.append((absf(xm), xm))
    best.sort(reverse=True)
    top_v, top_x = best[0]
    tie = any(abs(v - top_v) <= 1e-9 * max(top_v, 1e-300) and abs(x - top_x) > 1e-6 for v, x in best[1:])
    return sp.Float(top_x, 12), sp.Float(top_v, 12), tie


def _numeric_argmax(e, var, dom):
    x, _, tie = _numeric_extremum(e, var, dom)
    if tie:
        raise AmbiguousError("peak_position(): |y| is largest at several places")
    return x


def _numeric_peak(e, var, dom):
    return _numeric_extremum(e, var, dom)[1]


def _peak_of(e, var, extent, what):
    """Largest |e| over var (on the extent, if given)."""
    lo, hi = (extent or (None, None))
    dom = sp.Interval(-sp.oo if lo is None else lo, sp.oo if hi is None else hi)
    try:
        vals = _within(15, lambda: _extreme_values(e, var, dom))
        nums = [abs(float(sp.N(v))) for v in vals]
    except _Budget:
        if sp.sympify(e).free_symbols - {var}:
            raise SceneError(f"peak(): the extremes of {what} take too long to find symbolically; give numbers")
        return _numeric_peak(e, var, dom)
    except SceneError:
        raise
    except Exception as exc:          # symbolic shapes the candidate search cannot handle
        raise SceneError(f"peak(): cannot find the extremes of {what} ({type(exc).__name__}); give "
                         f"its shape with numbers") from exc
    if not nums:
        raise SceneError(f"peak(): no value found for {what}")
    best = max(range(len(nums)), key=lambda i: nums[i])
    return sp.Abs(sp.nsimplify(vals[best])) if vals[best].is_number else sp.Abs(vals[best])


def _shaped_pulse_derived(sc, wave, J, toward, far, near, r, t):
    """Image-method reflection and transmission of a shaped pulse at junction J."""
    s, xJ = toward, J.at
    # qualification: the pulse must start entirely on its own string (checked past both ends)
    beyond = sp.Interval(xJ, sp.oo) if s == 1 else sp.Interval(-sp.oo, xJ)
    lo_, hi_ = near.extent or (None, None)
    other = hi_ if s == -1 else lo_
    if other is not None:
        behind = sp.Interval(other, sp.oo) if s == -1 else sp.Interval(-sp.oo, other)
        try:
            back = max(abs(float(sp.N(v))) for v in _extreme_values(wave.g, X, behind))
        except Exception:
            back = None
        pk0 = float(sp.N(_peak_of(wave.g, X, None, f"pulse '{wave.name}'")))
        if back is not None and back > 1e-3 * pk0:
            raise SceneError(f"pulse '{wave.name}' extends past the other end of '{near.name}' (x = {other} m) at "
                             f"t = 0: it must start entirely on its own string")
    try:
        far_max = max(abs(float(sp.N(v))) for v in _extreme_values(wave.g, X, beyond))
        pk = float(sp.N(_peak_of(wave.g, X, None, f"pulse '{wave.name}'")))
    except Exception:
        raise SceneError(f"pulse '{wave.name}': cannot check that it starts on its own string before junction "
                         f"'{J.name}'; give its shape and the junction position as numbers")
    if far_max > 1e-3 * pk:
        raise SceneError(f"pulse '{wave.name}' already extends past junction '{J.name}' at t = 0 "
                         f"({far_max / pk:.3%} of its peak): it must start entirely on its own string")
    v1 = wave.v
    out = [(f"{wave.name}_reflected",
            ShapedPulse.derived(f"{wave.name}_reflected", near, r * wave.g.xreplace({X: 2 * xJ - X}), -s, v1,
                                (wave.name, J.name), coef=r, parent=wave))]
    if t is not None:
        v2 = far.speed()
        g_t = t * wave.g.xreplace({X: xJ + (v1 / v2) * (X - xJ)})
        out.append((f"{wave.name}_transmitted",
                    ShapedPulse.derived(f"{wave.name}_transmitted", far, g_t, s, v2, (wave.name, J.name),
                                        coef=t, parent=wave)))
    # a derived pulse heading for another junction or end would be reflected again: not modelled
    for dname, d in out:
        nxt = d.medium.extent[1] if d.sign == 1 else d.medium.extent[0]
        if nxt is not None:
            raise SceneError(f"pulse '{dname}' runs into another junction or end of '{d.medium.name}' "
                             f"(x = {nxt} m), where it would be reflected again; multiple reflections are not "
                             f"modelled in v0. Ask about one reflection at a time (one junction per scene)")
    return out


class Emitter:
    def __init__(self, sc, name, spec):
        w = f"emitters.{name}"
        _keys(spec, {"on", "geometry", "power", "power_per_length", "intensity"}, w)
        self.name = name
        if not isinstance(sc.objects.get(spec.get("on")), Open3D):
            raise SceneError(f"{w}.on: must be an open3d medium")
        self.geometry = spec.get("geometry")
        need = {"point": ("power", D_POWER), "line": ("power_per_length", dim(1, 1, -3)),
                "plane": ("intensity", dim(0, 1, -3))}
        if self.geometry not in need:
            raise SceneError(f"{w}.geometry: point | line | plane")
        key, d = need[self.geometry]
        if key not in spec or len(set(spec) - {"on", "geometry"}) != 1:
            raise SceneError(f"{w}: a {self.geometry} emitter takes exactly '{key}'")
        self.strength = sc.quantity(spec[key], d, f"{w}.{key}")

    def intensity(self, r):
        if self.geometry == "point":
            return self.strength / (4 * sp.pi * r ** 2)
        if self.geometry == "line":
            return self.strength / (2 * sp.pi * r)
        return self.strength




# ============================== superposition, junctions, resonators ==========
def _check_wave_x(wave, x):
    for part in getattr(wave, "parts", [wave]):
        _check_extent(getattr(part, "medium", None), x, part.name)


def _check_extent(medium, x, wave_name):
    ext = getattr(medium, "extent", None)
    if not ext or not getattr(sp.sympify(x), "is_number", False):
        return
    lo, hi = ext
    xv = float(sp.N(x))
    if (lo is not None and xv < float(sp.N(lo)) - 1e-12) or (hi is not None and xv > float(sp.N(hi)) + 1e-12):
        raise SceneError(f"x = {x} m is outside medium '{medium.name}', where wave '{wave_name}' lives")


class SumWave(GivenWave):
    """Superposition of waves already defined above: the field is the sum of their fields."""

    def __init__(self, sc, name, spec):
        w = f"waves.{name}"
        _keys(spec, {"sum"}, w)
        parts = spec["sum"]
        if not isinstance(parts, list) or len(parts) < 2:
            raise SceneError(f"{w}.sum: list at least two waves defined above")
        self.name, self.parts, self._sin = name, [], None
        for p in parts:
            o = sc.objects.get(p)
            if not isinstance(o, (Harmonic, GivenWave)):
                raise SceneError(f"{w}.sum: '{p}' is not a wave with a field defined above")
            self.parts.append(o)
        media = {id(o.medium): o.medium for o in self.parts if getattr(o, "medium", None) is not None}
        if len(media) > 1:
            names = sorted(m.name for m in media.values())
            raise SceneError(f"{w}.sum: the parts live on different media {names}; a sum is only "
                             f"defined where every part exists (sum waves on one medium)")
        self.medium = next(iter(media.values())) if len(media) == 1 else None
        self.f = sp.Add(*[o.field() for o in self.parts])


class Junction:
    """A point where a string meets another string, a fixed support or a free end."""
    KEYS = {"at", "left", "right"}

    def __init__(self, sc, name, spec):
        w = f"junctions.{name}"
        _keys(spec, self.KEYS, w)
        if set(spec) != self.KEYS:
            raise SceneError(f"{w}: give at, left and right")
        self.name = name
        self.at = sc.quantity(spec["at"], LENGTH, f"{w}.at")
        if self.at is None or not self.at.is_number:
            raise SceneError(f"{w}.at: give a number with a unit (symbolic junction positions are "
                             f"not supported)")
        if spec["left"] == spec["right"]:
            raise SceneError(f"{w}: left and right must differ")
        self.side = {}
        for side in ("left", "right"):
            v = spec[side]
            if v in ("fixed", "free"):
                self.side[side] = v
                continue
            m = sc.objects.get(v)
            if not isinstance(m, StringMedium) or not m.uniform or m.kind == "free":
                raise SceneError(f"{w}.{side}: '{v}' must be fixed, free, or a uniform string medium "
                                 f"with a known tension")
            lo, hi = m.extent or (None, None)
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
            m.extent = (lo, hi)
            self.side[side] = m
        if all(isinstance(v, str) for v in self.side.values()):
            raise SceneError(f"{w}: at least one side must be a string medium")


def derived_waves(sc, wave):
    """Reflected and transmitted waves created when a harmonic wave or a shaped pulse meets a junction."""
    if (isinstance(wave, GivenWave) and not isinstance(wave, (SumWave, ShapedPulse)) and wave.medium is not None
            and any(wave.medium in J.side.values() for J in sc.junctions)):
        raise SceneError(f"waves.{wave.name}: its string has a junction, and only `harmonic:` waves and "
                         f"`pulse:` waves with a `shape` are reflected and transmitted there")
    if not isinstance(wave, (Harmonic, ShapedPulse)) or wave.medium is None or not sc.junctions:
        return []
    out = []
    for J in sc.junctions:
        if wave.medium is J.side["left"]:
            toward = 1
        elif wave.medium is J.side["right"]:
            toward = -1
        else:
            continue
        if wave.sign not in (1, -1):
            raise SceneError(f"wave '{wave.name}' meets junction '{J.name}': its direction must be known")
        if wave.sign != toward:
            continue
        far = J.side["right"] if toward == 1 else J.side["left"]
        near = wave.medium
        if isinstance(far, str):
            r, t = sp.Integer(-1 if far == "fixed" else 1), None
        else:
            Z1 = sp.sqrt(near.tension() * near.mu)
            Z2 = sp.sqrt(far.tension() * far.mu)
            r = sp.simplify((Z1 - Z2) / (Z1 + Z2))
            t = sp.simplify(2 * Z1 / (Z1 + Z2))
            # energy flux is conserved at the junction: r^2 + (Z2/Z1) t^2 = 1 (checked as a fact)
            sc.implicit.append((f"junction {J.name}: energy conservation", sp.simplify(r ** 2 + Z2 / Z1 * t ** 2 - 1)))
        if isinstance(wave, ShapedPulse):
            if wave.derived_from is None:
                out += _shaped_pulse_derived(sc, wave, J, toward, far, near, r, t)
            continue
        s, xJ = toward, J.at

        def make(name, medium, A, k, v, sign, phi):
            d = Harmonic.__new__(Harmonic)
            d.name, d.sc, d.medium, d.nonuniform = name, sc, medium, False
            d.A, d.k, d.v, d.sign, d.phi, d.omega = A, k, v, sign, phi, wave.omega
            d.derived_from = (wave.name, J.name)
            return d
        A = wave.A
        mul = (lambda c: None if A is None else c * A)
        ok = wave.k is not None and wave.phi is not None
        phi_r = (wave.phi - 2 * s * wave.k * xJ) if ok else None
        out.append((f"{wave.name}_reflected", make(f"{wave.name}_reflected", near, mul(r), wave.k, wave.v, -s, phi_r)))
        if t is not None:
            v2 = far.speed()
            k2 = wave.omega / v2 if wave.omega is not None else None
            phi_t = (wave.phi - s * wave.k * xJ + s * k2 * xJ) if ok and k2 is not None else None
            out.append((f"{wave.name}_transmitted", make(f"{wave.name}_transmitted", far, mul(t), k2, v2, s, phi_t)))
    return out


class Resonator:
    """A finite string or air column with given end conditions: its standing-wave modes."""
    KEYS = {"type", "on", "length", "ends", "end_correction"}
    ENDS = {"string": ("fixed", "free"), "pipe": ("closed", "open"), "rod": ("clamped", "free")}

    def __init__(self, sc, name, spec):
        w = f"resonators.{name}"
        _keys(spec, self.KEYS, w)
        self.name, self.type = name, spec.get("type")
        if self.type not in self.ENDS:
            raise SceneError(f"{w}.type: string, pipe or rod")
        m = sc.objects.get(spec.get("on"))
        want = {"string": StringMedium, "pipe": GasMedium, "rod": RodMedium}[self.type]
        if not isinstance(m, want) or not m.uniform or getattr(m, "kind", None) == "free":
            label = {"string": "string", "pipe": "gas or fluid", "rod": "rod"}[self.type]
            raise SceneError(f"{w}.on: a {self.type} resonator needs a uniform {label} medium with a known speed")
        self.medium = m
        ends = spec.get("ends")
        if not (isinstance(ends, list) and len(ends) == 2 and all(e in self.ENDS[self.type] for e in ends)):
            raise SceneError(f"{w}.ends: two of {self.ENDS[self.type]}")
        self.ends = ends
        self.L = sc.quantity(spec.get("length"), LENGTH, f"{w}.length")
        if self.L is None:
            raise SceneError(f"{w}: needs a length")

        if self.type == "pipe":
            if "end_correction" not in spec:
                raise SceneError(f"{w}: give end_correction (0 m if the problem neglects it)")
            e = sc.quantity(spec["end_correction"], LENGTH, f"{w}.end_correction")
            if e.is_negative:
                raise SceneError(f"{w}.end_correction: must be >= 0")
            if "open" not in ends and e != 0:
                raise SceneError(f"{w}.end_correction: a pipe closed at both ends has no open end; "
                                 f"give 0 m")
            self.Leff = self.L + ends.count("open") * e
        else:
            if "end_correction" in spec:
                raise SceneError(f"{w}: end_correction applies to pipes only")
            self.Leff = self.L
        for label, val in (("length", self.L), ("effective length", self.Leff)):
            if val.is_positive is False or (val.is_number and not val > 0):
                raise SceneError(f"{w}: {label} must be positive (got {val})")
        self.mixed = ends[0] != ends[1]
        self.sc = sc

    def _check(self, n, odd=None, what="harmonic"):
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

    def wavelength(self, n):
        n = self._check(n)
        return (4 if self.mixed else 2) * self.Leff / n

    def frequency(self, n):
        return self.medium.speed() / self.wavelength(n)

    def harmonic_of_overtone(self, k):
        k = sp.sympify(k)
        if k.is_number and not (k.is_Integer and k >= 1):
            raise SceneError("overtone must be a whole number >= 1 (the 1st overtone is the first above the fundamental)")
        k = self._check(k, odd=False, what="overtone")
        return 2 * k + 1 if self.mixed else k + 1

    def allowed(self):
        n = 1
        while True:
            yield n
            n += 2 if self.mixed else 1


def harmonic_problem(sc, sol, final=False):
    """Why the solved values break a resonator's mode rules (None if they do not).
    With final=True, a harmonic still symbolic must be provably allowed."""
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


def _resonator(arg, fname):
    return _obj(arg, (Resonator,), fname)


def _frequency(_sc, w, at=None, harmonic=None):
    if isinstance(w, Ref) and isinstance(w.obj, Resonator):
        if harmonic is None:
            raise SceneError("frequency(resonator, harmonic=n): give the harmonic number")
        return w.obj.frequency(harmonic)
    if harmonic is not None:
        raise SceneError("frequency(): harmonic= applies to resonators only")
    return _obj(w, WAVES, "frequency").ang_freq() / TWO_PI


def _wavelength(_sc, w, at=None, harmonic=None):
    if isinstance(w, Ref) and isinstance(w.obj, Resonator):
        if harmonic is None:
            raise SceneError("wavelength(resonator, harmonic=n): give the harmonic number")
        return w.obj.wavelength(harmonic)
    if harmonic is not None:
        raise SceneError("wavelength(): harmonic= applies to resonators only")
    wave = _obj(w, WAVES, "wavelength")
    if at is not None:
        _check_wave_x(wave, at)
    return TWO_PI / wave.wavenumber(at)


def _harmonic(_sc, r, overtone=None):
    if overtone is None:
        raise SceneError("harmonic(resonator, overtone=k): give the overtone number")
    return _resonator(r, "harmonic").harmonic_of_overtone(overtone)


def _node_spacing(_sc, r, harmonic=None):
    if harmonic is None:
        raise SceneError("node_spacing(resonator, harmonic=n): give the harmonic number")
    return _resonator(r, "node_spacing").wavelength(harmonic) / 2


def _beat_frequency(_sc, a, b, t=None):
    """Beat frequency of two oscillations: waves, two frequencies, or two rays heard at time t."""
    kw = {} if t is None else {"t": t}
    if kw and not (isinstance(a, Ref) or isinstance(b, Ref)):
        raise SceneError("beat_frequency(..., t=...): t= needs at least one ray")
    fa = OBSERVABLES["frequency"](_sc, a, **kw) if isinstance(a, Ref) else sp.sympify(a)
    fb = OBSERVABLES["frequency"](_sc, b, **kw) if isinstance(b, Ref) else sp.sympify(b)
    return sp.Abs(fa - fb)


def _resonances(sc, r, f=None, vary=None, lo=None, hi=None):
    """Values of the symbol `vary` in [lo, hi] at which some allowed mode of the resonator
    has frequency f, in increasing order."""
    res = _resonator(r, "resonances")
    if f is None or vary is None or lo is None or hi is None:
        raise SceneError("resonances(r, f=..., vary=<symbol>, lo=..., hi=...)")
    bv = None if isinstance(vary, sp.Symbol) else sc.bound_variable(vary)
    if not isinstance(vary, sp.Symbol) and bv is None:
        raise SceneError("resonances(): vary must be a symbol used in the resonator")
    N = sp.Dummy("n", positive=True, integer=True)
    fN = res.medium.speed() / ((4 if res.mixed else 2) * res.Leff / N)
    if bv is not None:
        # a bounded symbol: solve in the declared symbol, keep only values inside the bound
        V, p_off, sgn, base = bv
        fN, f = (sp.sympify(a).xreplace({p_off: sgn * (V - base)}) for a in (fN, f))
        vary = V
    known = {u: v for u, v in (sc.solution or {}).items() if u != vary}
    fN = fN.xreplace(known)
    f, lo, hi = (sp.sympify(a).xreplace(known) for a in (f, lo, hi))
    if not (fN.has(vary) or f.has(vary)):
        raise SceneError(f"resonances(): neither f nor the mode frequencies of '{res.name}' depend on {vary}")
    extra = (f.free_symbols | fN.free_symbols | lo.free_symbols | hi.free_symbols) - {vary, N}
    if extra:
        solved_later = sorted(str(u) for u in extra if u in sc.unknowns)
        hint = (f" ({solved_later} are unknowns: use resonances() in observe, after they are solved)"
                if solved_later else "")
        raise UndeterminedError(f"resonances(): needs values for {sorted(map(str, extra))}{hint}")
    lo_v, hi_v = float(sp.N(lo)), float(sp.N(hi))
    if lo_v > hi_v:
        raise SceneError("resonances(): lo must not exceed hi")
    branches = sp.solve(sp.Eq(fN, f), vary)
    if not branches:
        raise SceneError(f"resonances(): no value of {vary} gives frequency {f}")
    positive = sc.kinds.get(vary) == "positive" or (bv is not None and bv[0].is_positive)
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
            v = expr.xreplace({N: n})
            cv = complex(sp.N(v))
            if abs(cv.imag) > 1e-12 * max(1.0, abs(cv.real)):
                done[b] = prev[b] == "nonreal"
                prev[b] = "nonreal"
                continue
            fv = cv.real
            inside = True if bv is None else (float(sgn * (fv - base)) > 0 if bv[1].is_positive
                                              else float(sgn * (fv - base)) >= 0)
            if lo_v - eps <= fv <= hi_v + eps and not (positive and fv <= 0) and inside:
                found.append(v)
            p_ = prev[b] if isinstance(prev[b], float) else None
            if p_ is not None and ((fv > hi_v + eps and fv >= p_) or (fv < lo_v - eps and fv <= p_)):
                done[b] = True          # each branch is monotonic in n: moving away for good
            if p_ is not None and fv == p_:
                done[b] = True
            prev[b] = fv
    return sp.Tuple(*sorted(set(found), key=lambda v: float(sp.N(v))))


def _count(_sc, items):
    if not isinstance(items, sp.Tuple):
        raise SceneError("count(): needs a list result such as resonances(...)")
    return sp.Integer(len(items))


def _item(_sc, items, n=None):
    """The n-th entry (1-based) of a list result."""
    if not isinstance(items, sp.Tuple):
        raise SceneError("item(list, n): needs a list result such as resonances(...)")
    if n is None or not sp.sympify(n).is_Integer:
        raise SceneError("item(list, n): n is a whole number, 1 for the first entry")
    n = int(n)
    if not 1 <= n <= len(items):
        raise SceneError(f"item(): the list has {len(items)} entries; n = {n} is out of range")
    return items[n - 1]


def _frequencies_in(sc, r, lo=None, hi=None):
    """The allowed mode frequencies of a resonator in [lo, hi] (a band of a variable source)."""
    res = _resonator(r, "frequencies_in")
    if lo is None or hi is None:
        raise SceneError("frequencies_in(resonator, lo=..., hi=...): give the band")
    known = getattr(sc, "solution", None) or {}
    lo, hi = sp.sympify(lo).xreplace(known), sp.sympify(hi).xreplace(known)
    if not (lo.is_number and hi.is_number):
        raise UndeterminedError("frequencies_in(): the band and the resonator need numbers")
    if not lo <= hi:
        raise SceneError("frequencies_in(): lo must not exceed hi")
    out = []
    f1 = sp.sympify(res.frequency(1)).xreplace(known)
    step = 2 if res.mixed else 1
    start = 1
    if f1.is_number and f1 > 0 and lo > f1:
        start = max(1, int(sp.floor(lo / f1)) - 2)
        if res.mixed and start % 2 == 0:
            start -= 1
        start = max(1, start)
        # the modes are n f1: check that the start is not above lo (else begin at 1)
        if not sp.sympify(res.frequency(start)).xreplace(known) <= lo:
            start = 1
    count = 0
    for n in range(start, 10 ** 9, step):
        count += 1
        f = sp.sympify(res.frequency(n)).xreplace(known)
        if not f.is_number:
            raise UndeterminedError(f"frequencies_in(): the mode frequencies of '{res.name}' need numbers ({f})")
        if f > hi * (1 + sp.Rational(1, 10 ** 12)):
            break
        if f >= lo * (1 - sp.Rational(1, 10 ** 12)):
            out.append(sp.simplify(f))
        if count > 100000:
            raise SceneError("frequencies_in(): more than 100000 modes; narrow the band")
    return sp.Tuple(*out)


def _spacing(_sc, items):
    """The common difference of an equally spaced list (refused otherwise)."""
    if not isinstance(items, sp.Tuple) or len(items) < 2:
        raise SceneError("spacing(list): needs a list result with at least 2 entries")
    diffs = [sp.simplify(b - a) for a, b in zip(items, items[1:])]
    for d in diffs[1:]:
        same = _same(d, diffs[0])
        if same is None:
            raise UndeterminedError("spacing(): cannot tell whether the entries are equally spaced")
        if not same:
            raise SceneError(f"spacing(): the entries are not equally spaced (differences {list(diffs)})")
    return diffs[0]


class Nearest(sp.Function):
    """nearest(), kept unevaluated until resolve_deferred, after the solved values are put
    in. resolve_deferred picks the option and records the numbers compared, so that with
    arbitrary values the run can require those numbers (not only the pick) to be the same
    at every scaling. Anything still symbolic then is refused."""


def _nearest(_sc, x, *options):
    """The position (1 for the first) of the option nearest to x, by relative distance.
    Refused when the two nearest options are about equally close. A value or option that
    depends on an unknown is decided after the solve (see Nearest)."""
    if len(options) < 2:
        raise SceneError("nearest(x, a, b, ...): give at least two options")
    if any(isinstance(o, (sp.Tuple, list, tuple)) for o in (x,) + options):
        raise SceneError("nearest(): the value and every option must be single values, not lists")
    return Nearest(*[sp.sympify(o) for o in (x,) + options])


def _pick_nearest(x, options):
    vals = []
    for o in (x,) + tuple(options):
        o = sp.sympify(o)
        c = complex(sp.N(o, 30))
        if abs(c.imag) > 1e-20:
            raise SceneError("nearest(): a value is not real")
        vals.append(c.real)
    xv, opts = vals[0], vals[1:]
    dist = [abs(xv - o) / max(abs(o), abs(xv), 1e-300) for o in opts]
    order = sorted(range(len(opts)), key=lambda i: dist[i])
    best, second = order[0], order[1]
    if dist[second] <= 2 * dist[best]:
        raise SceneError(f"nearest(): options {best + 1} and {second + 1} are about equally close to {xv:.6g} "
                         f"(relative distances {dist[best]:.3g} and {dist[second]:.3g}); no single nearest option")
    return sp.Integer(best + 1)


# ============================== observables ===================================
def _obj(arg, kinds, fname):
    if not isinstance(arg, Ref) or not isinstance(arg.obj, kinds):
        names = "/".join(k.__name__ for k in kinds)
        raise SceneError(f"{fname}(): first argument must be a {names}")
    return arg.obj


WAVES = (Harmonic, GivenWave)


def _point(sc, fname, deriv):
    def f(_sc, w, x=None, t=None):
        wave = _obj(w, WAVES, fname)
        if x is None or t is None:
            raise SceneError(f"{fname}(): give both x= and t=")
        _check_wave_x(wave, x)
        e = wave.field()
        if deriv and e.has(sp.Max, sp.Min, sp.Abs, sp.Heaviside, sp.Piecewise, sp.sign):
            e = sp.piecewise_fold(e.rewrite(sp.Piecewise))
            d = e
            for var in deriv:
                d = sp.diff(d, var)
            xv, tv = sp.sympify(x), sp.sympify(t)
            if xv.is_number and tv.is_number:
                from .energy import _breakpoints, _side_piece
                at_t = sp.piecewise_fold(d.xreplace({T: tv}))
                for q in _breakpoints(sp.piecewise_fold(e.xreplace({T: tv})), xv - 1, xv + 1, f"{fname}()"):
                    if sp.simplify(q - xv) != 0:
                        continue
                    a, b = _side_piece(at_t, xv, -1), _side_piece(at_t, xv, +1)
                    if a is not None and b is not None and sp.simplify((a - b).xreplace({X: xv})) != 0:
                        raise SceneError(f"{fname}(): x = {xv} m is a corner of the shape at that instant, "
                                         f"where the {'slope' if X in deriv else 'velocity'} is not defined; "
                                         f"ask just beside it")
            return d.xreplace({X: x, T: t}).doit()
        for var in deriv:
            e = sp.diff(e, var)
        return e.xreplace({X: x, T: t}).doit()
    return f


def _phase(_sc, w, x=None, t=None):
    wave = _obj(w, WAVES, "phase")
    if x is None or t is None:
        raise SceneError("phase(): give both x= and t=")
    _check_wave_x(wave, x)
    return wave.phase_expr(x, t)


def _speed(_sc, obj, at=None):
    if isinstance(obj, Ref) and isinstance(obj.obj, (StringMedium, GasMedium, RodMedium, EMMedium)):
        return obj.obj.speed(at)
    if isinstance(obj, Ref) and isinstance(obj.obj, Resonator):
        return obj.obj.medium.speed()
    if isinstance(obj, Ref) and isinstance(obj.obj, WAVES):
        if at is not None:
            raise SceneError("speed(wave) takes no at=")
        return obj.obj.speed()
    raise SceneError("speed(): argument must be a wave, a resonator, or a medium (string, gas, fluid, rod, em)")




def one_sinusoid(e, var):
    """Write e as B + C*sin(w*var + c) with C >= 0, w > 0, combining all terms of one
    frequency (phasors). Returns (B, C, w, c). Raises if e is not of that form."""
    e = sp.expand(TR8(sp.expand(e)))
    terms = sp.Add.make_args(e)
    B = sp.Add(*[t for t in terms if not t.has(var)])
    groups = {}
    for term in [t for t in terms if t.has(var)]:
        C, trig = term.as_independent(var, as_Add=False)
        if not isinstance(trig, (sp.sin, sp.cos)):
            raise SceneError(f"not a sinusoid in {var}")
        arg = sp.expand(trig.args[0])
        w = sp.diff(arg, var)
        if w.has(var):
            raise SceneError(f"not a sinusoid in {var} (non-linear phase)")
        c = sp.expand(arg - w * var)
        sw = sp.sign(w)
        if sw not in (1, -1):
            raise UndeterminedError(f"sign of the frequency in {var} is not determined")
        if sw == -1:
            w, c = -w, -c
            if isinstance(trig, sp.sin):
                C = -C
        a_ = C * sp.cos(c) if isinstance(trig, sp.sin) else -C * sp.sin(c)
        b_ = C * sp.sin(c) if isinstance(trig, sp.sin) else C * sp.cos(c)
        key = sp.simplify(w)
        pa, pb = groups.get(key, (0, 0))
        groups[key] = (pa + a_, pb + b_)
    if not groups:
        return B, sp.Integer(0), None, sp.Integer(0)
    if len(groups) != 1:
        raise SceneError(f"a sum of {len(groups)} different frequencies in {var}, not one sinusoid")
    (w, (a_, b_)), = groups.items()
    a_, b_ = sp.simplify(a_), sp.simplify(b_)
    return B, sp.simplify(sp.sqrt(a_ ** 2 + b_ ** 2)), w, sp.atan2(b_, a_)


def _max_over(_sc, var, e):
    """Maximum over var of e (or of |e|) when e is a constant plus one sinusoid in var."""
    if not isinstance(var, sp.Symbol):
        raise SceneError("max_over(var, expr): first argument must be a variable")
    e = sp.sympify(e)
    K, core = e.as_independent(var, as_Add=False)
    if K.is_nonnegative is not True:
        K, core = sp.Integer(1), e
    if isinstance(core, sp.Pow) and core.exp == sp.Rational(1, 2):    # sqrt is increasing
        _radicand_ok(_sc, var, core.base)
        return sp.simplify(K * sp.sqrt(_max_over(_sc, var, core.base)))
    absolute = isinstance(core, sp.Abs)
    inner = core.args[0] if absolute else core
    B, C, _, _ = one_sinusoid(inner, var)
    return sp.simplify(K * (sp.Abs(B) + C if absolute else B + C))


def _radicand_ok(_sc, var, base):
    low = sp.simplify(_min_over(_sc, var, base))
    if low.is_negative or (low.is_number and float(sp.N(low)) < -1e-12):
        raise SceneError(f"sqrt of an expression that becomes negative (its minimum is {low})")
    if low.is_nonnegative is not True and not low.is_number:
        raise SceneError("cannot tell whether the expression under sqrt stays non-negative")


def _min_over(_sc, var, e):
    """Minimum over var of e when e is a constant plus one sinusoid in var (or sqrt of one)."""
    if not isinstance(var, sp.Symbol):
        raise SceneError("min_over(var, expr): first argument must be a variable")
    e = sp.sympify(e)
    K, core = e.as_independent(var, as_Add=False)
    if K.is_nonnegative is not True:
        K, core = sp.Integer(1), e
    if isinstance(core, sp.Pow) and core.exp == sp.Rational(1, 2):
        _radicand_ok(_sc, var, core.base)
        return sp.simplify(K * sp.sqrt(_min_over(_sc, var, core.base)))
    if isinstance(core, sp.Abs):
        B, C, _, _ = one_sinusoid(core.args[0], var)
        return sp.simplify(K * sp.Max(sp.Abs(B) - C, 0))
    B, C, _, _ = one_sinusoid(core, var)
    return sp.simplify(K * (B - C))


def _frequency_of(_sc, var, e):
    """Frequency (cycles per unit of var) of an expression that oscillates sinusoidally in var."""
    if not isinstance(var, sp.Symbol):
        raise SceneError("frequency_of(var, expr): first argument must be a variable")
    _, C, w, _ = one_sinusoid(sp.sympify(e), var)
    if w is None or C == 0:
        raise SceneError("frequency_of(): the expression does not oscillate")
    return w / TWO_PI


def _kind_interval(s):
    """The values a symbol can take, from its sign assumptions."""
    if s.is_positive:
        return sp.Interval.open(0, sp.oo)
    if s.is_nonnegative:
        return sp.Interval(0, sp.oo)
    if s.is_negative:
        return sp.Interval.open(-sp.oo, 0)
    if s.is_nonpositive:
        return sp.Interval(-sp.oo, 0)
    return sp.Interval(-sp.oo, sp.oo)


def _show_interval(i):
    if not isinstance(i, sp.Interval):
        return str(i)
    return f"{'(' if i.left_open else '['}{i.inf}, {i.sup}{')' if i.right_open else ']'}"


def _limit(_sc, e, var, value, _written=()):
    """limit(expr, var, value), relative to the values var can take: its kind (positive, ...)
    intersected with any stated bound. The point must lie in the closure of that domain; at
    its edge the limit is taken from inside only, at an interior point from both sides, which
    must agree. A bounded symbol appears in expressions as base + s*offset, so the limit is
    computed in the offset, with each side mapped across (s = -1 reverses it).

    Apart from var, everything must be a number: no other symbol in the expression, in the
    point, or written in the text (`_written`, collected before SymPy simplified anything).
    A symbolic limit is only generic: it can hide values of the other symbols where no limit
    exists (|q|/q at q -> c is wrong at c = 0), and simplification as the text is read can
    erase a symbol together with its domain (log(c) - log(c) -> 0, c*q/(c*q) -> 1). Numbers
    (arbitrary: values) have neither problem."""
    bv = None if isinstance(var, sp.Symbol) else _sc.bound_variable(var)
    if any(sp.sympify(x).atoms(AppliedUndef) for x in (e, value)):
        raise SceneError("limit(): the expression or the point contains an arbitrary function, which is not "
                         "a number; apart from its variable, everything in a limit must be a number")
    own = {bv[0], bv[1]} if bv is not None else ({var} if isinstance(var, sp.Symbol) else set())
    others = (sp.sympify(e).free_symbols | sp.sympify(value).free_symbols | set(_written)) - own
    if others:
        names = ", ".join(sorted(str(_sc.show_back(s)) for s in others))
        shown_var = bv[0] if bv is not None else var
        raise SceneError(f"limit(): apart from its variable {shown_var}, everything in a limit must be a number, "
                         f"but {names} {'is a symbol' if len(others) == 1 else 'are symbols'}; give "
                         f"{'it a value' if len(others) == 1 else 'them values'} (a number, or arbitrary:)")
    if bv is not None:
        shown, p_off, sgn, base = bv           # messages name the declared symbol
        if shown.is_integer or p_off.is_integer:
            raise SceneError(f"limit(): {shown} takes whole-number values only, so a limit in it is not defined")
        strict = bool(p_off.is_positive)
        bound = sp.Interval(base, sp.oo, left_open=strict) if sgn == 1 else \
            sp.Interval(-sp.oo, base, right_open=strict)
        domain = _kind_interval(shown).intersect(bound)
    else:
        if not isinstance(var, sp.Symbol):
            raise SceneError("limit(expr, var, value): second argument must be a variable")
        if var.is_integer:
            raise SceneError(f"limit(): {var} takes whole-number values only, so a limit in it is not defined")
        shown, domain = var, _kind_interval(var)
    value = sp.sympify(value)
    if not isinstance(domain, sp.Interval) or domain.measure == 0:
        raise SceneError(f"limit(): {shown} has no range of values to approach {value} in {_show_interval(domain)}")
    # a real variable can approach only real points: the point must be proved real (infinity
    # cannot be written in expressions, so every point here is meant to be finite)
    if value.is_real is False:
        raise SceneError(f"limit(): the point {value} is not a real value")
    if value.is_real is not True:
        raise SceneError(f"limit(): cannot check that the point {value} is real for every allowed value of "
                         f"its symbols; {shown} can approach only real points")
    lo, hi = domain.inf, domain.sup
    at_edge = []
    for end, sign, side in ((lo, 1, "+"), (hi, -1, "-")):
        if not end.is_finite:
            continue
        gap = sp.simplify(sign * (value - end))          # >= 0 inside the closure
        if gap.is_negative:
            raise SceneError(f"limit(): {shown} -> {value} is outside the values {shown} can take {_show_interval(domain)}")
        if gap.is_nonnegative is not True:
            raise SceneError(f"limit(): cannot check that {shown} -> {value} is within the values {shown} "
                             f"can take {_show_interval(domain)}")
        if gap.is_zero:
            at_edge.append(side)               # at this end: approach from inside only
    sides = at_edge or ["+", "-"]
    vals = {}
    for side in sides:
        if bv is not None:                     # in the offset: n = base + sgn*p
            p_side = side if sgn == 1 else ("-" if side == "+" else "+")
            v = sp.limit(e, p_off, sp.simplify(sgn * (value - base)), dir=p_side)
        else:
            v = sp.limit(e, var, value, dir=side)
        if v.has(sp.AccumBounds, sp.zoo, sp.nan) or v in (sp.oo, -sp.oo) or isinstance(v, sp.Limit):
            word = "above" if side == "+" else "below"
            raise SceneError(f"limit(): the limit does not exist as a finite value (from {word}: {v})")
        vals[side] = v
    if len(vals) == 2 and sp.simplify(vals["+"] - vals["-"]) != 0:
        raise SceneError(f"limit(): the limit does not exist: from above it is {vals['+']}, "
                         f"from below {vals['-']}")
    return vals[sides[0]]


def _diff(_sc, e, var, n=sp.Integer(1)):
    if not (n.is_Integer and 1 <= n <= 10):
        raise SceneError("diff(): order must be an integer from 1 to 10")
    bv = None if isinstance(var, sp.Symbol) else _sc.bound_variable(var)
    if bv is not None:                 # a bounded symbol n = base + s*offset: d/dn = s*d/d(offset)
        _, p_off, sgn, _ = bv
        return sp.diff(e, p_off, int(n)) * sgn ** int(n)
    if not isinstance(var, sp.Symbol):
        raise SceneError("diff(): the second argument must be a variable or symbol")
    return sp.diff(e, var, int(n))


def sample_value(sym, rng):
    """A random test value respecting the symbol's assumptions, spread over magnitudes
    1e-3 .. 1e3 so that saturating functions are not always sampled in one regime."""
    if sym.is_integer:
        v = sp.Integer(rng.randint(1, 40))
    else:
        v = sp.Rational(rng.randint(11, 97), rng.randint(7, 23)) * sp.Integer(10) ** rng.randint(-3, 3)
    if sym.is_positive or sym.is_nonnegative:
        return v
    return v if rng.random() < 0.5 else -v


def equivalent(a, b):
    """Return (truth, basis). basis: 'proved' (difference reduces symbolically to 0),
    'sampled' (agrees at random points only; NOT a proof), 'counterexample' (differs at a
    point), or 'undecided' (involves arbitrary functions).
    A cheap numerical test runs first, so differing expressions are rejected quickly; the
    (possibly slow) symbolic proof is only attempted when they agree numerically."""
    a, b = sp.sympify(a), sp.sympify(b)
    d = a - b
    if d.has(AppliedUndef) or d.has(sp.Derivative):
        return (True, "proved") if sp.simplify(d) == 0 else (None, "undecided")
    syms = sorted(a.free_symbols | b.free_symbols, key=str)
    rng = random.Random(7)
    for _ in range(12):
        vals = {s: sample_value(s, rng) for s in syms}
        da = abs(complex(sp.N(a.xreplace(vals), 60)))
        db = abs(complex(sp.N(b.xreplace(vals), 60)))
        dd = abs(complex(sp.N(d.xreplace(vals), 60)))
        if dd > 1e-12 * max(da, db) or (max(da, db) == 0 and dd != 0):
            return False, "counterexample"
    for reduce in (sp.expand, lambda e: sp.expand(sp.expand_trig(e)), sp.simplify):
        if reduce is sp.simplify and sp.count_ops(d) > 400:
            break
        if reduce(d) == 0:
            return True, "proved"
    return True, "sampled"


class Equivalent(sp.Function):
    """Deferred equivalence test: evaluated only after unknowns are substituted."""
    nargs = 2


def _equivalent(_sc, a, b):
    return Equivalent(a, b)


def resolve_deferred(v, record=None):
    """Return (value, basis). Ordinary engine results are exact ('exact'). Each nearest()
    with numeric arguments is decided here; its arguments are appended to `record`."""
    if isinstance(v, sp.Basic) and v.has(Nearest):
        # innermost first: a nearest() inside another is picked, then put into the outer one
        while True:
            ready = [n for n in v.atoms(Nearest)
                     if not any(a.has(Nearest) for a in n.args) and all(a.is_number for a in n.args)]
            if not ready:
                break
            picks = {}
            for n in sorted(ready, key=sp.default_sort_key):
                picks[n] = _pick_nearest(n.args[0], n.args[1:])
                if record is not None:
                    record.append(tuple(n.args))
            v = v.xreplace(picks)
        if record is not None:                 # what is left (symbolic): kept for the proof run
            record.extend(tuple(n.args) for n in v.atoms(Nearest) if not any(a.has(Nearest) for a in n.args))
    if isinstance(v, Equivalent):
        truth, basis = equivalent(*v.args)
        if truth is None:
            raise UndeterminedError("equivalent(): cannot decide for arbitrary functions")
        return (sp.true if truth else sp.false), basis
    if v.has(Equivalent):
        raise SceneError("equivalent() must be the whole observe expression")
    if isinstance(v, sp.Basic) and v.has(Nearest):
        left = sorted({str(s) for n in v.atoms(Nearest) for s in n.free_symbols})
        raise UndeterminedError(f"nearest(): the value or an option still depends on "
                                f"{', '.join(left) or 'something unfixed'} after the solve, so no option can "
                                f"be picked")
    return v, "exact"


class Sphere:
    def __init__(self, r):
        self.r = r


def _flux(_sc, e, surface):
    em = _obj(e, (Emitter,), "flux")
    if not isinstance(surface, Ref) or not isinstance(surface.obj, Sphere) or em.geometry != "point":
        raise SceneError("flux(): v0 supports flux(point_emitter, sphere(r))")
    r = surface.obj.r
    return sp.simplify(em.intensity(r) * 4 * sp.pi * r ** 2)


def _pressure_amplitude(_sc, w, *more):
    from .rays import Ray, _pressure_amplitude_rays
    if isinstance(w, Ref) and isinstance(w.obj, Ray):
        return _pressure_amplitude_rays(_sc, w, *more)
    if more:
        raise SceneError("pressure_amplitude(): several arguments only for rays")
    wave = _obj(w, (Harmonic,), "pressure_amplitude")
    if not isinstance(wave.medium, ACOUSTIC_MEDIA):
        raise SceneError("pressure_amplitude(): only for sound waves (on a gas, fluid or rod medium)")
    rho = acoustic_density(wave.medium, "pressure_amplitude()")
    return rho * wave.speed() * wave.ang_freq() * wave.amplitude()


def _displacement_amplitude(_sc, w):
    from .rays import Ray
    if isinstance(w, Ref) and isinstance(w.obj, Ray):
        return w.obj.displacement_amplitude()
    return _obj(w, WAVES, "displacement_amplitude").amplitude()


def _sound_level(_sc, inten):
    i = sp.sympify(inten)
    if i.is_positive is False or i.is_zero:
        raise SceneError("sound_level(): the intensity must be positive")
    return 10 * sp.log(i / I0_HEARING) / sp.log(10)


def _intensity_of_level(_sc, level):
    return I0_HEARING * 10 ** (sp.sympify(level) / 10)


def _intensity(_sc, e, *more, r=None):
    from .rays import Ray, ray_intensity
    if isinstance(e, Ref) and isinstance(e.obj, Ray):
        return ray_intensity(_sc, [e] + list(more))
    if more:
        raise SceneError("intensity(): several arguments only for rays")
    if isinstance(e, Ref) and isinstance(e.obj, (Harmonic, GivenWave)) and r is None:
        p0 = _pressure_amplitude(_sc, e)
        rho = acoustic_density(e.obj.medium, "intensity()")
        return p0 ** 2 / (2 * rho * e.obj.speed())
    em = _obj(e, (Emitter,), "intensity")
    if r is None:
        raise SceneError("intensity(): give r=")
    return em.intensity(r)


def _front(_sc, p, t=None):
    if t is None:
        raise SceneError("front(): give t=")
    return _obj(p, (Pulse,), "front").front(t)


def _tension(_sc, m, at=None):
    return _obj(m, (StringMedium,), "tension").tension(at)


def _mu(_sc, m):
    med = _obj(m, (StringMedium,), "mu")
    if med.mu is None:
        raise UndeterminedError(f"'{med.name}' has no mass per length")
    return med.mu


def _impedance(_sc, m):
    med = _obj(m, (StringMedium,), "impedance")
    return sp.sqrt(med.tension() * _mu(_sc, m))


D_KGS = dim(M=1, T=-1)
OBS_DIMS = {
    "velocity": D_SPEED, "speed": D_SPEED, "amplitude": LENGTH, "offset": LENGTH,
    "frequency": D_FREQ, "omega": D_FREQ, "period": TIME, "wavelength": LENGTH, "k": D_WAVENUM,
    "field": LENGTH, "y": LENGTH, "vy": D_SPEED, "ay": D_ACC, "slope": DIMLESS, "phase": DIMLESS,
    "power": D_POWER, "front": LENGTH, "tension": FORCE, "mu": D_LINDENS, "impedance": D_KGS,
    "intensity": dim(0, 1, -3), "flux": D_POWER, "sphere": "obj", "equivalent": None,
    "pressure_amplitude": D_PRESS, "displacement_amplitude": LENGTH, "sound_level": DIMLESS,
    "intensity_of_level": dim(0, 1, -3),
    "is_travelling": None, "wrap": DIMLESS,
    "harmonic": DIMLESS, "node_spacing": LENGTH, "beat_frequency": D_FREQ, "resonances": None,
    "peak": LENGTH, "travel_time": TIME, "peak_position": LENGTH,
    "count": DIMLESS, "frequency_of": None, "item": None, "spacing": None, "nearest": DIMLESS, "frequencies_in": D_FREQ,
}

def _is_travelling(_sc, w):
    """True if the wave keeps a fixed shape while moving: y = F(x - c t) for some constant c."""
    wave = _obj(w, WAVES, "is_travelling")
    if isinstance(wave, Harmonic):
        return sp.true
    try:
        wave.velocity()
        return sp.true
    except SceneError:
        return sp.false


def _minmax(fn, args):
    """min/max of two values, or of one list result such as resonances(...) or maxima(...)."""
    if len(args) == 1 and isinstance(args[0], sp.Tuple):
        if len(args[0]) == 0:
            raise SceneError("min()/max() of an empty list: nothing was found in the range")
        return fn(*args[0])
    if any(isinstance(a, sp.Tuple) for a in args):
        raise SceneError("min()/max() take two values or one list")
    return fn(*args)


def _at(sc, e, **values):
    """The value of an expression with some variables set, e.g. at(expr, d=120[m])."""
    if not values:
        raise SceneError("at(expr, name=value, ...): give at least one variable")
    rep = {}
    for name, val in values.items():
        sym = sc.names.get(name)
        bound = getattr(sc, "bounds", {}).get(name)
        if bound is not None:
            orig, p_off, back = bound
            off = sp.simplify(back.xreplace({orig: sp.sympify(val)}))
            if off.is_negative or (p_off.is_positive and off.is_positive is False):
                raise SceneError(f"at(): {name} = {val} is outside the stated bound on '{name}'")
            rep[p_off] = off
            continue
        if not isinstance(sym, sp.Symbol):
            raise SceneError(f"at(): '{name}' is not a variable or symbol of the scene")
        if sym in sc.unknowns:
            raise SceneError(f"at(): '{name}' is an unknown; its value comes from the facts")
        rep[sym] = sp.sympify(val)
    if isinstance(e, sp.Tuple):
        return sp.Tuple(*[sp.sympify(i).xreplace(rep) for i in e])
    return sp.sympify(e).xreplace(rep)


def _peak(sc, w, t=None):
    """Largest |y| over x of a wave at an instant (a shaped pulse alone: its amplitude, no t needed)."""
    wave = _obj(w, WAVES, "peak")
    if isinstance(wave, ShapedPulse) and (t is None or wave.derived_from is None):
        return wave.peak()          # a lone pulse keeps its shape: the same height at every instant
    if t is None:
        raise SceneError("peak(wave, t=...): give the instant")
    ext = None
    meds = [getattr(p, "medium", None) for p in getattr(wave, "parts", [wave])]
    if meds and meds[0] is not None and all(m is meds[0] for m in meds):
        ext = getattr(meds[0], "extent", None)
    e = wave.field().xreplace({T: sp.sympify(t)})
    return _peak_of(e, X, ext, f"wave '{wave.name}'")


def _peak_position(sc, w, t=None):
    """x where |y| is largest at an instant (one place only; a tie is an error)."""
    wave = _obj(w, WAVES, "peak_position")
    if t is None:
        raise SceneError("peak_position(wave, t=...): give the instant")
    meds = [getattr(p, "medium", None) for p in getattr(wave, "parts", [wave])]
    ext = getattr(meds[0], "extent", None) if meds and meds[0] is not None and all(m is meds[0] for m in meds) else None
    lo, hi = ext or (None, None)
    dom = sp.Interval(-sp.oo if lo is None else lo, sp.oo if hi is None else hi)
    e = wave.field().xreplace({T: sp.sympify(t)})
    try:
        cands = _within(20, lambda: _extreme_values(e, X, dom, points=True))
    except _Budget:
        if e.free_symbols - {X}:
            raise SceneError("peak_position(): the extremes take too long to find symbolically; give numbers")
        return _numeric_argmax(e, X, dom)
    cands = [(q, abs(float(sp.N(v)))) for q, v in cands if q is not None]
    if not cands:
        raise SceneError("peak_position(): no maximum found")
    best = max(v for _, v in cands)
    at = sorted({q for q, v in cands if abs(v - best) <= 1e-12 * max(1.0, best)}, key=lambda q: float(sp.N(q)))
    if len(at) != 1:
        raise AmbiguousError(f"peak_position(): |y| is largest at several places: {at[:6]}")
    return at[0]


def _travel_time(sc, m, start=None, end=None):
    """Time for a disturbance to run along a string from start to end: the integral of ds/v."""
    med = _obj(m, (StringMedium, GasMedium), "travel_time")
    if start is None or end is None:
        raise SceneError("travel_time(medium, start=..., end=...): give both positions")
    a, b = sp.sympify(start), sp.sympify(end)
    lo_, hi_ = getattr(med, "extent", None) or (None, None)
    for pos in (a, b):
        if pos.is_number and ((lo_ is not None and pos < lo_) or (hi_ is not None and pos > hi_)):
            raise SceneError(f"travel_time(): x = {pos} m is outside '{med.name}' (it ends at a junction); "
                             f"add the times on each string")
    order = sp.simplify(b - a)
    if order.is_negative:
        a, b = b, a
    elif not order.is_nonnegative:
        raise SceneError("travel_time(): cannot tell whether start < end; give start before end")
    if getattr(med, "uniform", True):
        return (b - a) / med.speed()
    u = sp.Dummy("u", real=True)
    return sp.simplify(sp.integrate(1 / med.speed(u), (u, a, b)))


def _wrap(_sc, a):
    """Reduce an angle to the interval (-pi, pi]."""
    return a - 2 * sp.pi * sp.ceiling((a - sp.pi) / (2 * sp.pi))


OBSERVABLES = {
    "step": lambda sc, u: sp.Heaviside(u, 1),
    "is_travelling": _is_travelling, "at": _at, "peak": _peak, "travel_time": _travel_time,
    "peak_position": _peak_position,
    "wrap": _wrap,
    "harmonic": _harmonic, "node_spacing": _node_spacing, "beat_frequency": _beat_frequency,
    "resonances": _resonances, "count": _count, "item": _item, "spacing": _spacing, "nearest": _nearest,
    "frequencies_in": _frequencies_in,
    "frequency_of": _frequency_of, "limit": _limit,
    "min": lambda sc, *a: _minmax(sp.Min, a), "max": lambda sc, *a: _minmax(sp.Max, a),
    # waves
    "velocity": lambda sc, w: _obj(w, WAVES, "velocity").velocity(),
    "speed": _speed,
    "amplitude": lambda sc, w: (_obj(w, WAVES, "amplitude").peak() if isinstance(_obj(w, WAVES, "amplitude"),
                                                                              ShapedPulse)
                                else _obj(w, WAVES, "amplitude").amplitude()),
    "offset": lambda sc, w: _obj(w, WAVES, "offset").offset(),
    "frequency": _frequency,
    "omega": lambda sc, w: _obj(w, WAVES, "omega").ang_freq(),
    "period": lambda sc, w, harmonic=None: (1 / _frequency(sc, w, harmonic=harmonic))
    if (isinstance(w, Ref) and isinstance(w.obj, Resonator)) else TWO_PI / _obj(w, WAVES, "period").ang_freq(),
    "wavelength": _wavelength,
    "k": lambda sc, w, at=None: (_check_wave_x(_obj(w, WAVES, "k"), at) if at is not None else None,
                                 _obj(w, WAVES, "k").wavenumber(at))[1],
    "field": lambda sc, w: _obj(w, WAVES, "field").field(),
    "y": _point(None, "y", ()),
    "vy": _point(None, "vy", (T,)),
    "ay": _point(None, "ay", (T, T)),
    "slope": _point(None, "slope", (X,)),
    "phase": _phase,
    "power": lambda sc, w: _obj(w, WAVES, "power").power(),
    "front": _front,
    # media
    "tension": _tension, "mu": _mu, "impedance": _impedance,
    # emitters
    "intensity": _intensity, "flux": _flux,
    "pressure_amplitude": _pressure_amplitude, "displacement_amplitude": _displacement_amplitude,
    "sound_level": _sound_level, "intensity_of_level": _intensity_of_level,
    "sphere": lambda sc, r: Ref("sphere", Sphere(r)),
    # maths
    "diff": _diff, "max_over": _max_over, "min_over": _min_over, "equivalent": _equivalent,
    "abs": lambda sc, a: sp.Abs(a), "sqrt": lambda sc, a: sp.sqrt(a),
    "sin": lambda sc, a: sp.sin(a), "cos": lambda sc, a: sp.cos(a), "tan": lambda sc, a: sp.tan(a),
    "exp": lambda sc, a: sp.exp(a), "log": lambda sc, a: sp.log(a),
    "atan": lambda sc, a: sp.atan(a), "asin": lambda sc, a: sp.asin(a), "acos": lambda sc, a: sp.acos(a),
    "simplify": lambda sc, a: sp.simplify(a),
}


from . import rays as _rays_module  # noqa: E402,F401  (registers source/ray observables)
from . import modes as _modes_module  # noqa: E402,F401  (registers standing-wave pattern observables)
from . import energy as _energy_module  # noqa: E402,F401  (registers energy observables)
