"""Scene: media, waves and emitters, plus the physical observables the LLM may call.

All physics formulas live here (and only here). Internal units are SI.
"""
import random

import sympy as sp
from sympy.core.function import AppliedUndef
from sympy.simplify.fu import TR8

from .errors import SceneError, UndeterminedError
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
            "resonators", "emitters", "sources", "reflectors", "points", "rays", "given", "observe", "view", "expect", "illustrate", "explore"}
R_GAS = sp.Rational(831446261815324, 10 ** 14)     # J/(mol K), exact SI value

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
    def __init__(self, data):
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

    def _new_name(self, name):
        if not isinstance(name, str) or not name.isidentifier():
            raise SceneError(f"invalid name {name!r}")
        if name in RESERVED or name in self.names or name in self.functions or name in self.objects:
            hint = " (x, t and pi are reserved: choose another name)" if name in RESERVED else ""
            raise SceneError(f"name '{name}' is reserved or already used{hint}")

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

    # ---- dimension checking (used for `given` and `observe`) -----------------
    def name_dim(self, n):
        if n in self.objects:
            return "obj"
        # x and t inside free formulas are plain SI numbers (book formulas such as
        # 0.2*sin(2*pi*(6*t - x/60)) carry implicit units); observables are still checked.
        return {"pi": DIMLESS}.get(n)

    def call_dim(self, fname, args, kwargs, node, chk):
        if fname in self.functions:
            return None
        for key, want in (("x", LENGTH), ("t", TIME), ("at", LENGTH), ("r", LENGTH), ("node_at", LENGTH),
                          ("antinode_at", LENGTH), ("no_node_at", LENGTH)):
            if key in kwargs:
                chk.same(kwargs[key], want, f"argument {key}=")
        if fname == "beat_frequency":
            for a_ in args:
                if a_ != "obj":
                    chk.same(a_, D_FREQ, "the arguments of beat_frequency() (frequencies in Hz, "
                                         "not angular frequencies)")
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
        if fname in ("max_over", "min_over"):
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
    raise SceneError(f"media.{name}: type '{spec['type']}' not supported yet (string, gas, open3d)")


class GasMedium:
    """Air or another gas: speed of sound given directly, or from gamma, P, rho, or from
    gamma, T, molar mass (uses the gas constant R, an exact SI constant)."""
    KEYS = {"type", "v", "gamma", "pressure", "density", "temperature", "molar_mass", "gas_constant"}

    def __init__(self, sc, name, spec):
        w = f"media.{name}"
        _keys(spec, self.KEYS, w)
        self.name, self.kind, self.mu, self.extent = name, "gas", None, None
        q = lambda k, d, **kw: sc.quantity(spec.get(k), d, f"{w}.{k}", **kw)
        gamma = q("gamma", DIMLESS)
        P, rho = q("pressure", D_PRESS), q("density", D_DENS)
        Tk, M = q("temperature", TEMP, temperature=True), q("molar_mass", MASS)
        R = q("gas_constant", dim(L=2, M=1, T=-2, K=-1))
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
                             f"[+ gas_constant])")
        self.v = _pick(sc, cands, "speed of sound", w)
        if self.v.is_positive is False:
            raise SceneError(f"{w}: speed must be positive")

    @property
    def uniform(self):
        return True

    def speed(self, at=None):
        return self.v


class Open3D:
    def __init__(self, name):
        self.name = name


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
            else:
                raise SceneError(f"{w}.tension: use a value, {{hanging: ...}}, {{thermal: ...}} or free")
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
            "phase", "from", "toward"}

    def __init__(self, sc, name, spec):
        w = f"waves.{name}"
        _keys(spec, self.KEYS, w)
        self.name, self.sc = name, sc
        self.medium = None
        if "on" in spec:
            if spec["on"] not in sc.objects or not isinstance(sc.objects[spec["on"]], (StringMedium, GasMedium)):
                raise SceneError(f"{w}.on: '{spec['on']}' is not a string or gas medium defined above")
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
        if self.medium is not None and self.medium.uniform and self.medium.kind != "free":
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
            raise SceneError(f"{w}: pulses are not yet reflected or transmitted at junctions (a pulse has "
                             f"no shape in v0). On uniform strings the junction coefficients would apply to "
                             f"any pulse shape; for now use a harmonic wave to get r and t")

    def front(self, t):
        S, tau = sp.Dummy("S", positive=True), sp.Dummy("tau", positive=True)
        s = self.medium.s
        tt = sp.integrate(1 / self.medium.speed(s), (s, 0, S))
        sols = sp.solve(sp.Eq(tt, tau), S)
        if len(sols) != 1:
            raise SceneError(f"pulse '{self.name}': cannot invert travel time")
        return sp.simplify(sols[0].subs(tau, t))


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
    """Reflected and transmitted waves created when a harmonic wave meets a junction."""
    if (isinstance(wave, GivenWave) and not isinstance(wave, SumWave) and wave.medium is not None
            and any(wave.medium in J.side.values() for J in sc.junctions)):
        raise SceneError(f"waves.{wave.name}: its string has a junction, and only waves written as "
                         f"`harmonic:` are reflected and transmitted there; write it as a harmonic wave")
    if not isinstance(wave, Harmonic) or wave.medium is None or not sc.junctions:
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
    ENDS = {"string": ("fixed", "free"), "pipe": ("closed", "open")}

    def __init__(self, sc, name, spec):
        w = f"resonators.{name}"
        _keys(spec, self.KEYS, w)
        self.name, self.type = name, spec.get("type")
        if self.type not in self.ENDS:
            raise SceneError(f"{w}.type: string or pipe (rods are not supported yet)")
        m = sc.objects.get(spec.get("on"))
        want = StringMedium if self.type == "string" else GasMedium
        if not isinstance(m, want) or not m.uniform or getattr(m, "kind", None) == "free":
            raise SceneError(f"{w}.on: a {self.type} resonator needs a uniform "
                             f"{'string' if want is StringMedium else 'gas'} medium with a known speed")
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


def _beat_frequency(_sc, a, b):
    """Beat frequency of two oscillations: waves, or two frequencies."""
    fa = OBSERVABLES["frequency"](_sc, a) if isinstance(a, Ref) else sp.sympify(a)
    fb = OBSERVABLES["frequency"](_sc, b) if isinstance(b, Ref) else sp.sympify(b)
    return sp.Abs(fa - fb)


def _resonances(sc, r, f=None, vary=None, lo=None, hi=None):
    """Values of the symbol `vary` in [lo, hi] at which some allowed mode of the resonator
    has frequency f, in increasing order."""
    res = _resonator(r, "resonances")
    if f is None or vary is None or lo is None or hi is None:
        raise SceneError("resonances(r, f=..., vary=<symbol>, lo=..., hi=...)")
    if not isinstance(vary, sp.Symbol):
        raise SceneError("resonances(): vary must be a symbol used in the resonator")
    N = sp.Dummy("n", positive=True, integer=True)
    fN = res.medium.speed() / ((4 if res.mixed else 2) * res.Leff / N)
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
            v = expr.xreplace({N: n})
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


def _count(_sc, items):
    if not isinstance(items, sp.Tuple):
        raise SceneError("count(): needs a list result such as resonances(...)")
    return sp.Integer(len(items))


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
    if isinstance(obj, Ref) and isinstance(obj.obj, (StringMedium, GasMedium)):
        return obj.obj.speed(at)
    if isinstance(obj, Ref) and isinstance(obj.obj, Resonator):
        return obj.obj.medium.speed()
    if isinstance(obj, Ref) and isinstance(obj.obj, WAVES):
        if at is not None:
            raise SceneError("speed(wave) takes no at=")
        return obj.obj.speed()
    raise SceneError("speed(): argument must be a wave, a resonator, a string or a gas medium")




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


def _limit(_sc, e, var, value):
    if not isinstance(var, sp.Symbol):
        raise SceneError("limit(expr, var, value): second argument must be a variable")
    v = sp.limit(e, var, value)
    if v.has(sp.AccumBounds, sp.zoo, sp.nan) or v in (sp.oo, -sp.oo):
        raise SceneError(f"limit(): the limit does not exist as a finite value (got {v})")
    return v


def _diff(_sc, e, var, n=sp.Integer(1)):
    if not (n.is_Integer and 1 <= n <= 10):
        raise SceneError("diff(): order must be an integer from 1 to 10")
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


def resolve_deferred(v):
    """Return (value, basis). Ordinary engine results are exact ('exact')."""
    if isinstance(v, Equivalent):
        truth, basis = equivalent(*v.args)
        if truth is None:
            raise UndeterminedError("equivalent(): cannot decide for arbitrary functions")
        return (sp.true if truth else sp.false), basis
    if v.has(Equivalent):
        raise SceneError("equivalent() must be the whole observe expression")
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


def _intensity(_sc, e, r=None):
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
    "is_travelling": None, "wrap": DIMLESS,
    "harmonic": DIMLESS, "node_spacing": LENGTH, "beat_frequency": D_FREQ, "resonances": None,
    "count": DIMLESS, "frequency_of": None,
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
        if not isinstance(sym, sp.Symbol):
            raise SceneError(f"at(): '{name}' is not a variable or symbol of the scene")
        if sym in sc.unknowns:
            raise SceneError(f"at(): '{name}' is an unknown; its value comes from the facts")
        rep[sym] = sp.sympify(val)
    if isinstance(e, sp.Tuple):
        return sp.Tuple(*[sp.sympify(i).xreplace(rep) for i in e])
    return sp.sympify(e).xreplace(rep)


def _wrap(_sc, a):
    """Reduce an angle to the interval (-pi, pi]."""
    return a - 2 * sp.pi * sp.ceiling((a - sp.pi) / (2 * sp.pi))


OBSERVABLES = {
    "is_travelling": _is_travelling, "at": _at,
    "wrap": _wrap,
    "harmonic": _harmonic, "node_spacing": _node_spacing, "beat_frequency": _beat_frequency,
    "resonances": _resonances, "count": _count,
    "frequency_of": _frequency_of, "limit": _limit,
    "min": lambda sc, *a: _minmax(sp.Min, a), "max": lambda sc, *a: _minmax(sp.Max, a),
    # waves
    "velocity": lambda sc, w: _obj(w, WAVES, "velocity").velocity(),
    "speed": _speed,
    "amplitude": lambda sc, w: _obj(w, WAVES, "amplitude").amplitude(),
    "offset": lambda sc, w: _obj(w, WAVES, "offset").offset(),
    "frequency": _frequency,
    "omega": lambda sc, w: _obj(w, WAVES, "omega").ang_freq(),
    "period": lambda sc, w: TWO_PI / _obj(w, WAVES, "period").ang_freq(),
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
