"""Point sources of sound, plane reflectors and rays: interference by path difference.

Physics kept here:
* a source emits a harmonic pressure wave p = A sin(w t - k s + phi) along every path of length s;
* rays from different directions add as PRESSURE (a scalar); displacement is a vector and is
  not added between rays;
* a plane reflector acts through an image source; a rigid wall reflects pressure with no
  phase change, an open (pressure-release) boundary with a change of pi;
* amplitude spreading is explicit: none, spherical (1/s) or cylindrical (1/sqrt(s));
* sources with `phase: random` are incoherent with every other source: intensities add.
"""
import itertools
import math

import sympy as sp

from .errors import SceneError, UndeterminedError
from .expr import Ref
from .units import split_quantity
from .scene import (D_FREQ, DIMLESS, LENGTH, OBS_DIMS, OBSERVABLES, TWO_PI, GasMedium, T,
                    _keys, _obj)

KEYS = ("sources", "reflectors", "points", "rays")
SPREADING = ("none", "spherical", "cylindrical")


def _vector(sc, value, where):
    if not isinstance(value, list) or len(value) not in (2, 3):
        raise SceneError(f"{where}: a position is a list of 2 or 3 lengths, e.g. [0 m, 2 m]")
    return [sc.quantity(v, LENGTH, f"{where}[{i}]") for i, v in enumerate(value)]


def _plain_vector(sc, value, where):
    if not isinstance(value, list) or len(value) not in (2, 3):
        raise SceneError(f"{where}: a direction is a list of 2 or 3 numbers, e.g. [0, 1]")
    v = [sc.quantity(c, DIMLESS, f"{where}[{i}]") for i, c in enumerate(value)]
    norm = sp.sqrt(sum(c ** 2 for c in v))
    if norm == 0:
        raise SceneError(f"{where}: zero vector")
    return [c / norm for c in v]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


class Source:
    KEYS_ = {"on", "at", "f", "A", "A_at", "phase", "spreading"}

    def __init__(self, sc, name, spec):
        w = f"sources.{name}"
        _keys(spec, self.KEYS_, w)
        self.name = name
        m = sc.objects.get(spec.get("on"))
        if not isinstance(m, GasMedium):
            raise SceneError(f"{w}.on: point sources need a gas medium (sound)")
        self.medium = m
        self.at = _vector(sc, spec["at"], f"{w}.at") if "at" in spec else None
        if "f" not in spec or "A" not in spec or "spreading" not in spec or "phase" not in spec:
            raise SceneError(f"{w}: give f, A, phase and spreading (none | spherical | cylindrical)")
        self.f = sc.quantity(spec["f"], D_FREQ, f"{w}.f")
        if self.f.is_positive is False or (self.f.is_number and not self.f > 0):
            raise SceneError(f"{w}.f: frequency must be positive")
        self.A = sc.quantity(spec["A"], None, f"{w}.A")     # pressure or relative amplitude
        unit_dim = split_quantity(spec["A"])[3]
        self.A_kind = unit_dim if unit_dim is not None else ("number" if self.A.is_number else None)
        self.spreading = spec["spreading"]
        if self.spreading not in SPREADING:
            raise SceneError(f"{w}.spreading: one of {SPREADING}")
        self.A_at = None
        if self.spreading != "none":
            if "A_at" not in spec:
                raise SceneError(f"{w}: with {self.spreading} spreading give A_at, the distance at which "
                                 f"the amplitude is A")
            self.A_at = sc.quantity(spec["A_at"], LENGTH, f"{w}.A_at")
        elif "A_at" in spec:
            raise SceneError(f"{w}.A_at: only with spherical or cylindrical spreading")
        self.random = spec["phase"] == "random"
        self.phi = None if self.random else sc.quantity(spec["phase"], DIMLESS, f"{w}.phase")

    @property
    def k(self):
        return TWO_PI * self.f / self.medium.speed()

    def amplitude_at(self, s):
        if self.spreading == "none":
            return self.A
        if self.spreading == "spherical":
            return self.A * self.A_at / s
        return self.A * sp.sqrt(self.A_at / s)


class Reflector:
    KEYS_ = {"point", "normal", "boundary", "phase_change"}

    def __init__(self, sc, name, spec):
        w = f"reflectors.{name}"
        _keys(spec, self.KEYS_, w)
        self.name = name
        if "point" not in spec or "normal" not in spec:
            raise SceneError(f"{w}: a plane reflector needs point and normal")
        self.p0 = _vector(sc, spec["point"], f"{w}.point")
        self.n = _plain_vector(sc, spec["normal"], f"{w}.normal")
        if len(self.n) != len(self.p0):
            raise SceneError(f"{w}: point and normal must have the same number of components")
        if ("boundary" in spec) == ("phase_change" in spec):
            raise SceneError(f"{w}: give exactly one of boundary (rigid | open) or phase_change "
                             f"(only when the problem itself states the phase change)")
        if "boundary" in spec:
            if spec["boundary"] not in ("rigid", "open"):
                raise SceneError(f"{w}.boundary: rigid or open")
            # pressure: rigid wall -> no change; pressure-release (open) -> pi
            self.dphi = sp.Integer(0) if spec["boundary"] == "rigid" else sp.pi
        else:
            self.dphi = sc.quantity(spec["phase_change"], DIMLESS, f"{w}.phase_change")

    def image(self, s):
        d = _dot([a - b for a, b in zip(s, self.p0)], self.n)
        return [a - 2 * d * c for a, c in zip(s, self.n)]

    def side(self, q):
        return _dot([a - b for a, b in zip(q, self.p0)], self.n)


class Ray:
    """One path from a source to the listening point: direct, via one plane reflector, or a
    path of stated length (tubes)."""
    KEYS_ = {"from", "to", "via", "length", "phase_change"}

    def __init__(self, sc, name, spec):
        w = f"rays.{name}"
        _keys(spec, self.KEYS_, w)
        self.name = name
        src = sc.objects.get(spec.get("from"))
        if not isinstance(src, Source):
            raise SceneError(f"{w}.from: a source defined in `sources`")
        self.source = src
        self.dphi = sp.Integer(0)
        if "length" in spec:
            if "to" in spec or "via" in spec:
                raise SceneError(f"{w}: give either length (a stated path) or to/via (geometry)")
            self.L = sc.quantity(spec["length"], LENGTH, f"{w}.length")
            if self.L.is_positive is False or (self.L.is_number and not self.L > 0):
                raise SceneError(f"{w}.length: must be positive")
            self.to = None
            if "phase_change" in spec:
                self.dphi = sc.quantity(spec["phase_change"], DIMLESS, f"{w}.phase_change")
            return
        if "phase_change" in spec:
            raise SceneError(f"{w}.phase_change: only for rays of stated length; a reflector carries "
                             f"its own phase change")
        to = sc.objects.get(spec.get("to"))
        if not isinstance(to, Point):
            raise SceneError(f"{w}.to: a point defined in `points`")
        if src.at is None:
            raise SceneError(f"{w}: source '{src.name}' has no position (at)")
        if len(to.at) != len(src.at):
            raise SceneError(f"{w}: source and point must have the same number of coordinates")
        self.to = to
        start = src.at
        via = spec.get("via")
        if via is not None:
            ref = sc.objects.get(via)
            if not isinstance(ref, Reflector):
                raise SceneError(f"{w}.via: one reflector defined in `reflectors` (v0: one reflection)")
            if len(ref.p0) != len(src.at):
                raise SceneError(f"{w}: reflector and source must have the same number of coordinates")
            a, b = sp.simplify(ref.side(src.at)), sp.simplify(ref.side(to.at))
            prod = sp.simplify(a * b)
            if prod.is_positive is False:
                raise SceneError(f"{w}: source and point must be on the same side of reflector "
                                 f"'{ref.name}', off its surface")
            if prod.is_positive is None:
                raise SceneError(f"{w}: cannot tell whether source and point are on the same side of "
                                 f"'{ref.name}'; use numbers or positive symbols for the positions")
            start = ref.image(src.at)
            self.dphi = ref.dphi
        self.L = sp.sqrt(sum((a - b) ** 2 for a, b in zip(start, to.at)))
        if self.L.is_zero:
            raise SceneError(f"{w}: the path has zero length")

    def amplitude(self):
        return self.source.amplitude_at(self.L)

    def total_phase(self, t, allow_random=False):
        if self.source.random and not allow_random:
            raise SceneError(f"ray '{self.name}': its source has a random phase")
        s = self.source
        phi = 0 if s.random else s.phi        # rays of one random source share its phase
        return TWO_PI * s.f * t - s.k * self.L + phi + self.dphi

    def phasor_key(self):
        """Rays with the same key add as amplitudes; different keys add as intensities."""
        return ("random", self.source.name) if self.source.random else ("coherent",)


class Point:
    def __init__(self, sc, name, value):
        self.name = name
        self.at = _vector(sc, value, f"points.{name}")


def build(sc, data):
    makers = {"sources": Source, "reflectors": Reflector, "points": Point, "rays": Ray}
    for key in ("sources", "reflectors", "points", "rays"):
        for name, spec in (data.get(key) or {}).items():
            sc._add(name, makers[key](sc, name, spec))


# ------------------------------------------------------------------ observables
def _rays(args, fname):
    rays = [_obj(a, (Ray,), fname) for a in args]
    if not rays:
        raise SceneError(f"{fname}(): give one or more rays")
    if len({id(r) for r in rays}) != len(rays):
        raise SceneError(f"{fname}(): a ray is listed twice")
    kinds = {r.source.A_kind for r in rays} - {None}
    if len(kinds) > 1:
        raise SceneError(f"{fname}(): the sources' amplitudes A are in different units (or mix units "
                         f"and plain numbers); give them all in one unit, or all as plain numbers")
    return rays


def _freq(sc, r):
    return sp.sympify(r.source.f).xreplace(getattr(sc, "solution", None) or {})


def _same_freq(sc, a, b, fname):
    from .scene import _same
    same = _same(_freq(sc, a), _freq(sc, b))
    if same is None:
        raise UndeterminedError(f"{fname}(): cannot tell whether rays '{a.name}' and '{b.name}' have the "
                                f"same frequency ({_freq(sc, a)} vs {_freq(sc, b)})")
    return same


def _groups(sc, rays, fname):
    """Rays that add as amplitudes: one group per random source, and coherent rays grouped
    by frequency. Groups add as intensities (time average)."""
    groups = []
    for r in rays:
        for g in groups:
            h = g[0]
            if r.source.random or h.source.random:
                if r.source is h.source:
                    g.append(r)
                    break
                continue
            if _same_freq(sc, r, h, fname):
                g.append(r)
                break
        else:
            groups.append([r])
    return groups


def _amp2(rs):
    """|sum of phasors|^2 for rays of one frequency, written as
    sum A_i^2 + 2 sum A_i A_j cos(phase_i - phase_j) (no trig expansion)."""
    total = sum(r.amplitude() ** 2 for r in rs)
    for a, b in itertools.combinations(rs, 2):
        dphi = sp.simplify(a.total_phase(0, allow_random=True) - b.total_phase(0, allow_random=True))
        total += 2 * a.amplitude() * b.amplitude() * sp.cos(dphi)
    return sp.simplify(total)


def _resultant_amplitude(sc, *args):
    rays = _rays(args, "resultant_amplitude")
    if any(r.source.random for r in rays) and len({id(r.source) for r in rays}) > 1:
        raise SceneError("resultant_amplitude(): the rays are not all coherent (a source has a random "
                         "phase); only relative_intensity is defined")
    if len(_groups(sc, rays, "resultant_amplitude")) > 1:
        raise SceneError("resultant_amplitude(): rays of different frequencies beat; there is no steady "
                         "amplitude (use relative_intensity for the time average)")
    return sp.simplify(sp.sqrt(_amp2(rays)))


def _relative_intensity(sc, *args):
    """Time-averaged intensity in units of amplitude^2: coherent same-frequency rays add as
    phasors; incoherent or different-frequency rays add as intensities."""
    rays = _rays(args, "relative_intensity")
    return sp.simplify(sum(_amp2(g) for g in _groups(sc, rays, "relative_intensity")))


def _path_difference(_sc, a, b):
    ra, rb = _obj(a, (Ray,), "path_difference"), _obj(b, (Ray,), "path_difference")
    return sp.simplify(ra.L - rb.L)


def _phase_difference(sc, a, b):
    ra, rb = _obj(a, (Ray,), "phase_difference"), _obj(b, (Ray,), "phase_difference")
    if not _same_freq(sc, ra, rb, "phase_difference"):
        raise SceneError("phase_difference(): the rays have different frequencies")
    return sp.simplify(ra.total_phase(0) - rb.total_phase(0))


def _extrema(kind):
    def f(sc, a, b, vary=None, lo=None, hi=None):
        name = f"{kind}()"
        ra, rb = _obj(a, (Ray,), kind), _obj(b, (Ray,), kind)
        if vary is None or lo is None or hi is None or not isinstance(vary, sp.Symbol):
            raise SceneError(f"{name}: {kind}(ray1, ray2, vary=<symbol>, lo=..., hi=...)")
        if ra.source.random or rb.source.random:
            raise SceneError(f"{name}: needs coherent sources")
        known = {u: v for u, v in (sc.solution or {}).items() if u != vary}
        d = sp.simplify((ra.total_phase(T) - rb.total_phase(T)).xreplace(known))
        if d.has(T):
            raise SceneError(f"{name}: the rays have different frequencies")
        lo, hi = sp.sympify(lo).xreplace(known), sp.sympify(hi).xreplace(known)
        if not d.has(vary):
            raise SceneError(f"{name}: the phase difference does not depend on {vary}")
        extra = (d.free_symbols | lo.free_symbols | hi.free_symbols) - {vary}
        if extra:
            raise UndeterminedError(f"{name}: needs values for {sorted(map(str, extra))}")
        # the extremum condition is D(vary) = whole number, D = phase difference / 2pi
        # (minus 1/2 for minima). Count the whole numbers D crosses on [lo, hi], piece by piece.
        D = d / TWO_PI - (0 if kind == "maxima" else sp.Rational(1, 2))
        lo_v, hi_v = float(sp.N(lo)), float(sp.N(hi))
        if not lo_v < hi_v:
            raise SceneError(f"{name}: lo must be below hi")
        def real_roots(e):
            out = []
            for r in sp.solve(e, vary):
                c = complex(sp.N(r))
                if abs(c.imag) < 1e-12 and lo_v < c.real < hi_v:
                    out.append(c.real)
            return out
        num, den = sp.fraction(sp.together(D))
        ends = [float(sp.N(den.subs(vary, v))) for v in (lo_v, hi_v)] if den.has(vary) else []
        if any(abs(e) < 1e-15 for e in ends):
            raise SceneError(f"{name}: the phase difference is infinite at an end of [lo, hi] "
                             f"(e.g. a wavelength of 0); move that end")
        if den.has(vary) and real_roots(den):
            raise SceneError(f"{name}: the phase difference is singular inside [lo, hi]; narrow the range")
        cuts = sorted([lo_v, hi_v] + real_roots(sp.diff(D, vary)))
        N = sp.Dummy("n", integer=True)
        branches = sp.solve(sp.Eq(D, N), vary)
        if not branches:
            raise SceneError(f"{name}: no value of {vary} gives a {kind[:-1]}um")
        ns = set()
        for a_, b_ in zip(cuts, cuts[1:]):
            da, db = (float(sp.N(D.subs(vary, v))) for v in (a_, b_))
            lo_n, hi_n = math.ceil(min(da, db) - 1e-9), math.floor(max(da, db) + 1e-9)
            if hi_n - lo_n > 5000:
                raise SceneError(f"{name}: more than 5000 {kind} in range; narrow it")
            ns.update(range(lo_n, hi_n + 1))
        positive = sc.kinds.get(vary) == "positive"
        eps = 1e-9 * max(1.0, abs(lo_v), abs(hi_v))
        found = []
        for n in sorted(ns):
            for br in branches:
                v = sp.simplify(br.xreplace({N: n}))
                c = complex(sp.N(v))
                if abs(c.imag) < 1e-12 and lo_v - eps <= c.real <= hi_v + eps and not (positive and c.real <= 0):
                    if abs(float(sp.N(D.subs(vary, v))) - n) < 1e-9 and all(
                            sp.N(r.L.xreplace(known).subs(vary, v)) > 0 for r in (ra, rb)):
                        found.append(v)
        return sp.Tuple(*sorted(set(found), key=lambda v: float(sp.N(v))))
    return f


def _length(_sc, r):
    return _obj(r, (Ray,), "length").L


def _distance(_sc, a, b):
    pa, pb = (_obj(v, (Point, Source), "distance") for v in (a, b))
    if pa.at is None or pb.at is None or len(pa.at) != len(pb.at):
        raise SceneError("distance(): two positions with the same number of coordinates")
    return sp.sqrt(sum((x - y) ** 2 for x, y in zip(pa.at, pb.at)))


def _wrap_obs(name, handler):
    old = OBSERVABLES[name]

    def f(sc, w, *a, **kw):
        if isinstance(w, Ref) and isinstance(w.obj, (Ray, Source)):
            return handler(w.obj, *a, **kw)
        return old(sc, w, *a, **kw)
    OBSERVABLES[name] = f


def _ray_or_source(o):
    return o if isinstance(o, Source) else o.source


def _ray_amplitude(o):
    if isinstance(o, Source):
        if o.spreading != "none":
            raise SceneError(f"amplitude({o.name}): spreading source; ask for amplitude(ray)")
        return o.A
    return o.amplitude()


def _ray_phase(o, x=None, t=None):
    if not isinstance(o, Ray) or x is not None or t is None:
        raise SceneError("phase(ray, t=...): the phase of one ray at its end point")
    return o.total_phase(t)


_wrap_obs("amplitude", _ray_amplitude)
_wrap_obs("frequency", lambda o, at=None, harmonic=None: _ray_or_source(o).f)
_wrap_obs("omega", lambda o: TWO_PI * _ray_or_source(o).f)
_wrap_obs("period", lambda o: 1 / _ray_or_source(o).f)
_wrap_obs("wavelength", lambda o, at=None, harmonic=None: TWO_PI / _ray_or_source(o).k)
_wrap_obs("k", lambda o, at=None: _ray_or_source(o).k)
_wrap_obs("phase", _ray_phase)

OBSERVABLES.update({
    "length": _length, "distance": _distance, "path_difference": _path_difference,
    "phase_difference": _phase_difference, "resultant_amplitude": _resultant_amplitude,
    "relative_intensity": _relative_intensity,
    "maxima": _extrema("maxima"), "minima": _extrema("minima"),
})
OBS_DIMS.update({
    "length": LENGTH, "distance": LENGTH, "path_difference": LENGTH, "phase_difference": DIMLESS,
    "resultant_amplitude": None, "relative_intensity": None, "maxima": None, "minima": None,
})
