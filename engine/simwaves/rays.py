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
from .expr import dimension_of
from .units import split_quantity
from .scene import (D_FREQ, D_PRESS, D_SPEED, DIMLESS, LENGTH, OBS_DIMS, OBSERVABLES, TWO_PI, GasMedium, T,
                    acoustic_density, dim,
                    _keys, _obj)
from .units import TIME
from . import doppler as _dop

KEYS = ("sources", "reflectors", "points", "rays")
SPREADING = ("none", "spherical", "hemispherical", "cylindrical")


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
    KEYS_ = {"on", "at", "f", "A", "A_at", "phase", "spreading", "power", "velocity", "starts", "circle",
             "emits_from"}

    def __init__(self, sc, name, spec):
        w = f"sources.{name}"
        _keys(spec, self.KEYS_, w)
        self.name = name
        m = sc.objects.get(spec.get("on"))
        from .scene import EMMedium
        if not isinstance(m, (GasMedium, EMMedium)):
            raise SceneError(f"{w}.on: point sources need a gas, fluid (sound) or em (light, radio) medium")
        self.medium = m
        self.at = _vector(sc, spec["at"], f"{w}.at") if "at" in spec else None
        moves = any(k in spec for k in _dop.Motion.KEYS)
        if moves and self.at is None:
            raise SceneError(f"{w}: a moving source needs `at`, its position at t = 0 (or when it starts)")
        self.motion = _dop.Motion(sc, self.at, spec, w, D_SPEED) if moves else _dop.FixedMotion(self.at)
        self.emits_from = sc.quantity(spec.get("emits_from"), TIME, f"{w}.emits_from")
        if "spreading" not in spec or "phase" not in spec or \
                ("A" in spec) == ("power" in spec):
            raise SceneError(f"{w}: give phase, spreading (none | spherical | hemispherical | cylindrical), "
                             f"exactly one of A (amplitude) or power, and f unless no phase is needed")
        self._f = sc.quantity(spec.get("f"), D_FREQ, f"{w}.f")       # optional: only phases need it
        if self._f is not None and (self._f.is_positive is False or (self._f.is_number and not self._f > 0)):
            raise SceneError(f"{w}.f: frequency must be positive")
        self.spreading = spec["spreading"]
        if self.spreading not in SPREADING:
            raise SceneError(f"{w}.spreading: one of {SPREADING}")
        self.power = None
        if "power" in spec:
            # a source of stated acoustic power: pressure amplitude follows from I = P/(Omega s^2)
            if self.spreading not in ("spherical", "hemispherical") or "A_at" in spec:
                raise SceneError(f"{w}: a source with power needs spreading spherical or hemispherical "
                                 f"(and no A_at)")
            self.power = sc.quantity(spec["power"], dim(2, 1, -3), f"{w}.power")
            if self.power.is_positive is False:
                raise SceneError(f"{w}.power must be positive")
            self.A, self.A_kind, self.A_at = None, D_PRESS, None
            self.random = spec["phase"] == "random"
            self.phi = None if self.random else sc.quantity(spec["phase"], DIMLESS, f"{w}.phase")
            return
        self.A = sc.quantity(spec["A"], None, f"{w}.A")     # pressure or relative amplitude
        unit_dim = split_quantity(spec["A"])[3]
        if unit_dim is None and "[" in str(spec["A"]):
            unit_dim = dimension_of(split_quantity(spec["A"])[0], sc)
        self.A_kind = unit_dim if unit_dim is not None else ("number" if self.A.is_number else None)
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
    def f(self):
        if self._f is None:
            raise UndeterminedError(f"source '{self.name}' has no frequency (f); phases, wavelengths and "
                                    f"displacement amplitudes need it")
        return self._f

    @property
    def k(self):
        return TWO_PI * self.f / self.medium.speed()

    def amplitude_at(self, s):
        if self.power is not None:
            omega = 4 * sp.pi if self.spreading == "spherical" else 2 * sp.pi
            rho = acoustic_density(self.medium, f"source '{self.name}' with power")
            return sp.sqrt(2 * rho * self.medium.speed() * self.power / (omega * s ** 2))
        if self.spreading == "none":
            return self.A
        if self.spreading in ("spherical", "hemispherical"):
            return self.A * self.A_at / s
        return self.A * sp.sqrt(self.A_at / s)


class Reflector:
    KEYS_ = {"point", "normal", "boundary", "phase_change", "velocity"}

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
        self.velocity = [sp.Integer(0)] * len(self.p0)
        self.moving = False
        if "velocity" in spec:
            vel = spec["velocity"]
            if not isinstance(vel, list) or len(vel) != len(self.p0):
                raise SceneError(f"{w}.velocity: a list of {len(self.p0)} speeds; `point` is where the wall "
                                 f"is at t = 0")
            self.velocity = [sc.quantity(c, D_SPEED, f"{w}.velocity[{i}]") for i, c in enumerate(vel)]
            if _dop._cross_zero(self.velocity, self.n) is not True:
                raise SceneError(f"{w}.velocity: v0 moves a wall only along its normal")
            self.moving = True
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

    @property
    def L(self):
        if self.moving:
            raise SceneError(f"ray '{self.name}': something on it moves (or the air moves), so it has no fixed "
                             f"path; path lengths, phases and intensities are not defined in v0. Ask "
                             f"frequency(ray, t=...), emitted_at(...) or arrives_at(...)")
        if self._L.is_zero:
            raise SceneError(f"ray '{self.name}': the path has zero length (the source is at the point)")
        return self._L

    @L.setter
    def L(self, value):
        self._L = value

    def __init__(self, sc, name, spec):
        w = f"rays.{name}"
        _keys(spec, self.KEYS_, w)
        self.name = name
        self.sc = sc
        self.via_ref = None
        self.moving = False
        src = sc.objects.get(spec.get("from"))
        if not isinstance(src, Source):
            raise SceneError(f"{w}.from: a source defined in `sources`")
        self.source = src
        self.dphi = sp.Integer(0)
        if "length" in spec:
            if "to" in spec or "via" in spec:
                raise SceneError(f"{w}: give either length (a stated path) or to/via (geometry)")
            self.L = sc.quantity(spec["length"], LENGTH, f"{w}.length")
            if src.power is not None:
                raise SceneError(f"{w}: a stated-length path (a tube) from a source given by power: how the "
                                 f"sound spreads along it is not modelled; give the source an amplitude A")
            if self.L.is_positive is False or (self.L.is_number and not self.L > 0):
                raise SceneError(f"{w}.length: must be positive")
            self.to = None
            # moving air makes a stated path moving too, as it does a geometric one: the delay
            # then depends on the direction, which a length does not give (review m15b round 2, R10)
            wind = getattr(src.medium, "wind", None)
            self.moving = src.motion.moving or bool(wind and any(_dop._decide(c) != "zero" for c in wind))
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
            self.via_ref = ref
        wind = getattr(src.medium, "wind", None)
        self.moving = src.motion.moving or to.motion.moving or bool(self.via_ref and self.via_ref.moving) or \
            bool(wind and any(_dop._decide(c) != "zero" for c in wind))
        self.L = sp.sqrt(sum((a - b) ** 2 for a, b in zip(start, to.at)))


    def amplitude(self):
        return self.source.amplitude_at(self.L)

    def total_phase(self, t, allow_random=False):
        if self.source.random and not allow_random:
            raise SceneError(f"ray '{self.name}': its source has a random phase")
        s = self.source
        phi = 0 if s.random else s.phi        # rays of one random source share its phase
        return TWO_PI * s.f * t - s.k * self.L + phi + self.dphi

    def pressure_amplitude(self):
        _not_em(self, "pressure amplitude")
        if self.source.A_kind != D_PRESS:
            raise SceneError(f"ray '{self.name}': its source amplitude is not a pressure (give A in Pa, or power)")
        return self.amplitude()

    def sqrt_intensity(self):
        _not_em(self, "intensity")
        """sqrt of this ray's own intensity (W/m^2): from power and spreading directly, or p0/sqrt(2 rho v)."""
        src = self.source
        if src.power is not None:
            omega = 4 * sp.pi if src.spreading == "spherical" else 2 * sp.pi
            return sp.sqrt(src.power / (omega * self.L ** 2))
        rho = acoustic_density(src.medium, f"intensity of ray '{self.name}'")
        return self.pressure_amplitude() / sp.sqrt(2 * rho * src.medium.speed())

    def displacement_amplitude(self):
        _not_em(self, "displacement amplitude")
        rho = acoustic_density(self.source.medium, f"displacement amplitude of ray '{self.name}'")
        return self.pressure_amplitude() / (rho * self.source.medium.speed() * TWO_PI * self.source.f)

    def phasor_key(self):
        """Rays with the same key add as amplitudes; different keys add as intensities."""
        return ("random", self.source.name) if self.source.random else ("coherent",)


def _not_em(ray, what):
    if getattr(ray.source.medium, "kind", None) == "em":
        raise SceneError(f"ray '{ray.name}': {what.replace('_', ' ')} is a sound quantity; light, radar and radio "
                         f"(type: em) have no pressure, displacement or acoustic intensity in v0")


class Point:
    def __init__(self, sc, name, value):
        self.name = name
        w = f"points.{name}"
        if isinstance(value, dict):
            _keys(value, {"at"} | set(_dop.Motion.KEYS), w)
            if "at" not in value:
                raise SceneError(f"{w}: a moving point needs `at`, its position at t = 0 (or when it starts)")
            self.at = _vector(sc, value["at"], f"{w}.at")
            self.motion = _dop.Motion(sc, self.at, value, w, D_SPEED)
        else:
            self.at = _vector(sc, value, w)
            self.motion = _dop.FixedMotion(self.at)


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


def _amp2(rs, weight=None):
    """|sum of phasors|^2 for rays of one frequency, written as
    sum A_i^2 + 2 sum A_i A_j cos(phase_i - phase_j) (no trig expansion)."""
    amp = weight or (lambda r: r.amplitude())
    total = sum(amp(r) ** 2 for r in rs)
    for a, b in itertools.combinations(rs, 2):
        dphi = sp.simplify(a.total_phase(0, allow_random=True) - b.total_phase(0, allow_random=True))
        total += 2 * amp(a) * amp(b) * sp.cos(dphi)
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


def _pressure_amplitude_rays(sc, *args):
    """Pressure amplitude of the resultant of one or more coherent rays (sources with power or A in Pa)."""
    rays = _rays(args, "pressure_amplitude")
    if any(r.source.A_kind != D_PRESS for r in rays):
        raise SceneError("pressure_amplitude(): needs sources with power or A in Pa")
    if len(rays) == 1:
        return rays[0].pressure_amplitude()
    return _resultant_amplitude(sc, *args)


def ray_intensity(sc, args):
    """Physical time-averaged intensity (W/m^2) of superposed rays with pressure amplitudes in one
    medium: I = <p^2>/(rho v), i.e. relative_intensity / (2 rho v)."""
    rays = _rays(args, "intensity")
    media = {id(r.source.medium): r.source.medium for r in rays}
    if len(media) != 1:
        raise SceneError("intensity(): the rays are in different media")
    if any(r.source.A_kind != D_PRESS for r in rays):
        raise SceneError("intensity(): needs pressure amplitudes (A in Pa, or power); use relative_intensity "
                         "for amplitudes in other units")
    total = 0
    for g in _groups(sc, rays, "intensity"):
        total += _amp2(g, weight=lambda r: r.sqrt_intensity())
    return sp.simplify(total)


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
        branches = sp.solve(sp.Eq(D, N), vary)    # may be empty: then solve for each n below
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
            cands = [br.xreplace({N: n}) for br in branches] if branches else sp.solve(sp.Eq(D, n), vary)
            for br in cands:
                v = sp.simplify(br)
                c = complex(sp.N(v))
                if abs(c.imag) < 1e-12 and lo_v - eps <= c.real <= hi_v + eps and not (positive and c.real <= 0):
                    if abs(float(sp.N(D.subs(vary, v))) - n) < 1e-9 and all(
                            sp.N(r.L.xreplace(known).subs(vary, v)) > 0 for r in (ra, rb)):
                        found.append(v)
        return sp.Tuple(*sorted(set(found), key=lambda v: float(sp.N(v))))
    return f


def _length(_sc, r):
    return _obj(r, (Ray,), "length").L


def _distance(_sc, a, b, t=None):
    pa, pb = (_obj(v, (Point, Source), "distance") for v in (a, b))
    if pa.at is None or pb.at is None or len(pa.at) != len(pb.at):
        raise SceneError("distance(): two positions with the same number of coordinates")
    if t is None:
        if pa.motion.moving or pb.motion.moving:
            raise SceneError("distance(): one of them moves; give t=")
        return sp.sqrt(sum((x - y) ** 2 for x, y in zip(pa.at, pb.at)))
    t = sp.sympify(t).xreplace(getattr(_sc, "solution", None) or {})
    qa, qb = (_dop._seg_at(p.motion.segments(), t, "distance()")[2](t) for p in (pa, pb))
    return sp.simplify(sp.sqrt(sum((x - y) ** 2 for x, y in zip(qa, qb))))


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
    if getattr(o if isinstance(o, Source) else o.source, "A_kind", None) == D_PRESS:
        raise SceneError("amplitude(): this sound source carries a pressure; ask for pressure_amplitude(...) or "
                         "displacement_amplitude(...) so the units are explicit")
    if isinstance(o, Source):
        if o.spreading != "none":
            raise SceneError(f"amplitude({o.name}): spreading source; ask for amplitude(ray)")
        return o.A
    return o.amplitude()


def _ray_phase(o, x=None, t=None):
    if not isinstance(o, Ray) or x is not None or t is None:
        raise SceneError("phase(ray, t=...): the phase of one ray at its end point")
    src = o.source
    if src.emits_from is not None:
        # a switched-on source: the sound heard at t must exist, the same causal check as a
        # timed frequency (review m15b, D3-3: a phase was given before any sound arrived)
        if o.to is None:
            # a stated-length path in still air: the delay is L/v (review m15b round 1, R5:
            # trace() needs positions, which such a path has none of)
            te = _dop._sol(o, t) - o.L / src.medium.speed()
            ok = _dop._ge(te, src.emits_from)
            if ok is None:
                raise UndeterminedError(f"ray '{o.name}': cannot tell whether the source was already emitting")
            if not ok:
                raise _dop.NoSound(f"ray '{o.name}': no sound yet: the sound arriving then would have left the "
                                   f"source at t = {te}, before it starts emitting at {src.emits_from}")
        else:
            _dop.trace(o, t=t)
    return o.total_phase(t)


_wrap_obs("amplitude", _ray_amplitude)
def _ray_frequency(o, at=None, harmonic=None, t=None, emitted=None):
    if isinstance(o, Source):
        if t is not None or emitted is not None:
            raise SceneError(f"frequency({o.name}): a source's own frequency; for what a listener hears, "
                             f"ask frequency(<ray>, t=...)")
        return o.f
    if t is None and emitted is None:
        if o.moving:
            raise SceneError(f"frequency({o.name}): something on this ray moves (or the air moves), so the "
                             f"heard frequency can change with time; give t= (when heard) or emitted= "
                             f"(when emitted)")
        return o.source.f
    return _dop.heard_frequency(o, t, emitted)


def _ray_wavelength(o, at=None, harmonic=None, t=None, emitted=None):
    if isinstance(o, Ray) and (o.moving or t is not None or emitted is not None):
        if t is None and emitted is None:
            raise SceneError(f"wavelength({o.name}): something on this ray moves; give t= or emitted=")
        return _dop.air_wavelength(o, t, emitted)
    if t is not None or emitted is not None:
        raise SceneError("wavelength(source): no t= or emitted=; ask wavelength(<ray>, t=...)")
    return TWO_PI / _ray_or_source(o).k


_wrap_obs("frequency", _ray_frequency)
def _still(o, fname):
    if isinstance(o, Ray) and o.moving:
        raise SceneError(f"{fname}({o.name}): something on this ray moves (or the air moves); the heard "
                         f"frequency changes with time: ask frequency({o.name}, t=...) and work from it")
    return _ray_or_source(o)


_wrap_obs("omega", lambda o: TWO_PI * _still(o, "omega").f)
_wrap_obs("period", lambda o: 1 / _still(o, "period").f)
_wrap_obs("wavelength", _ray_wavelength)
_wrap_obs("k", lambda o, at=None: _still(o, "k").k)
_wrap_obs("phase", _ray_phase)

OBSERVABLES.update({
    "wave_speed_seen": lambda _sc, r, t=None, emitted=None: _dop.wave_speed_seen(
        _obj(r, (Ray,), "wave_speed_seen"), t, emitted),
    "emitted_at": lambda _sc, r, t=None: _dop.emitted_at(_obj(r, (Ray,), "emitted_at"), t),
    "arrives_at": lambda _sc, r, emitted=None: _dop.arrives_at(_obj(r, (Ray,), "arrives_at"), emitted),
    "length": _length, "distance": _distance, "path_difference": _path_difference,
    "phase_difference": _phase_difference, "resultant_amplitude": _resultant_amplitude,
    "relative_intensity": _relative_intensity,
    "maxima": _extrema("maxima"), "minima": _extrema("minima"),
})
OBS_DIMS.update({
    "emitted_at": TIME, "arrives_at": TIME, "wave_speed_seen": D_SPEED,
    "length": LENGTH, "distance": LENGTH, "path_difference": LENGTH, "phase_difference": DIMLESS,
    "resultant_amplitude": None, "relative_intensity": None, "maxima": None, "minima": None,
})
