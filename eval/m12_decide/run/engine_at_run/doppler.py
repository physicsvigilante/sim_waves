"""Moving sources, listeners and walls; wind (the Doppler effect from first principles).

Physics kept here:
* sound leaves the source at the emission time te and travels at v relative to the air;
  the air moves with the wind w. The sound heard at time t at the listener satisfies
      |R(t) - E(te) - w (t - te)| = v (t - te),   t > te;
* the phase heard at t is the phase emitted at te, so the heard frequency is f0 * dte/dt
  (implicit derivative of the condition above; exact whenever te is);
* a plane wall moving along its normal reflects: it hears the sound and re-emits it
  (a chain of two legs). v0 does this only when everything lies on one line;
* sources and listeners must move slower than sound relative to the air: then each
  instant of hearing has exactly one emission time.
"""
import mpmath
import sympy as sp

from .errors import SceneError, UndeterminedError
from .units import DIMLESS, LENGTH, TIME

class NoSound(SceneError):
    """The sound asked about has not been emitted (or has not arrived) at that time."""


def _decide(e):
    """'pos', 'neg', 'zero', or None if undecidable."""
    e = sp.simplify(e)
    if e.is_zero:
        return "zero"
    if e.is_positive:
        return "pos"
    if e.is_negative:
        return "neg"
    if e.is_number:
        v = complex(sp.N(e, 30))
        if abs(v.imag) > 1e-20:
            return None
        if abs(v.real) < 1e-25 * max(1.0, abs(v.real)):
            return "zero"
        return "pos" if v.real > 0 else "neg"
    return None


def _ge(a, b):
    """a >= b decided: True, False or None."""
    if a == sp.oo or b == -sp.oo:
        return True
    if a == -sp.oo or b == sp.oo:
        return False
    d = _decide(a - b)
    return None if d is None else d in ("pos", "zero")


# ------------------------------------------------------------------ motion
class Motion:
    """Position of a source or listener as a function of time, in segments
    (lo, hi, fn): fn(tau) is the position vector for lo <= tau <= hi."""
    KEYS = ("velocity", "starts", "circle")

    def __init__(self, sc, at, spec, where, speed_dim):
        self.at, self.where = at, where
        vel, starts, circle = spec.get("velocity"), spec.get("starts"), spec.get("circle")
        self.kind = "static"
        self.velocity = None
        self.starts = None
        if vel is not None and circle is not None:
            raise SceneError(f"{where}: give velocity or circle, not both")
        if starts is not None and vel is None:
            raise SceneError(f"{where}.starts: only with velocity (at rest at `at` until then)")
        if vel is not None:
            if not isinstance(vel, list) or len(vel) != len(at):
                raise SceneError(f"{where}.velocity: a list of {len(at)} speeds, like `at`, e.g. [15 m/s, 0 m/s]")
            self.velocity = [sc.quantity(c, speed_dim, f"{where}.velocity[{i}]") for i, c in enumerate(vel)]
            self.kind = "linear"
            if starts is not None:
                self.starts = sc.quantity(starts, TIME, f"{where}.starts")
        if circle is not None:
            if not isinstance(circle, dict) or set(circle) - {"center", "speed", "sense"} or \
                    not {"center", "speed", "sense"} <= set(circle):
                raise SceneError(f"{where}.circle: {{center: [x, y], speed: <speed>, sense: ccw | cw}}; "
                                 f"`at` is the position at t = 0, on the circle")
            if len(at) != 2:
                raise SceneError(f"{where}.circle: circular motion is in the plane (2 coordinates)")
            c = circle["center"]
            if not isinstance(c, list) or len(c) != 2:
                raise SceneError(f"{where}.circle.center: [x, y]")
            self.center = [sc.quantity(q, LENGTH, f"{where}.circle.center[{i}]") for i, q in enumerate(c)]
            self.speed = sc.quantity(circle["speed"], speed_dim, f"{where}.circle.speed")
            if circle["sense"] not in ("ccw", "cw"):
                raise SceneError(f"{where}.circle.sense: ccw (counter-clockwise) or cw")
            self.sense = 1 if circle["sense"] == "ccw" else -1
            dx, dy = at[0] - self.center[0], at[1] - self.center[1]
            self.radius = sp.sqrt(dx ** 2 + dy ** 2)
            if _decide(self.radius) != "pos":
                raise SceneError(f"{where}.circle: `at` must be off the centre (the radius is |at - center|)")
            self.theta0 = sp.atan2(dy, dx)
            self.kind = "circle"

    @property
    def moving(self):
        return self.kind != "static"

    def segments(self):
        at = self.at
        if self.kind == "static":
            return [(-sp.oo, sp.oo, lambda tau: list(at))]
        if self.kind == "linear":
            v = self.velocity
            if self.starts is None:
                return [(-sp.oo, sp.oo, lambda tau: [a + u * tau for a, u in zip(at, v)])]
            s0 = self.starts
            return [(-sp.oo, s0, lambda tau: list(at)),
                    (s0, sp.oo, lambda tau: [a + u * (tau - s0) for a, u in zip(at, v)])]
        c, R, om = self.center, self.radius, self.sense * self.speed / self.radius
        th = self.theta0
        return [(-sp.oo, sp.oo, lambda tau: [c[0] + R * sp.cos(th + om * tau), c[1] + R * sp.sin(th + om * tau)])]

    def speeds(self):
        """Speeds relative to the ground on each segment: list of vectors (circle: None)."""
        if self.kind == "static":
            return [[0] * len(self.at)]
        if self.kind == "linear":
            return ([[0] * len(self.at)] if self.starts is not None else []) + [self.velocity]
        return None


class FixedMotion(Motion):
    """A stationary position (sources and points without motion keys)."""

    def __init__(self, at):
        self.at, self.kind, self.velocity, self.starts, self.where = at, "static", None, None, ""


class WallMotion:
    """The point where the line of a 1D scene meets a plane wall moving along its normal."""

    def __init__(self, ref, anchor, n, sol=None):
        self.ref, self.anchor, self.n, self.sol = ref, anchor, n, sol or {}
        self.kind = "linear" if ref.moving else "static"

    def segments(self):
        p0, n, a = self.ref.p0, self.n, self.anchor
        u = [sp.sympify(c).xreplace(self.sol) for c in self.ref.velocity]
        def fn(tau):
            p = [x + ux * tau for x, ux in zip(p0, u)]
            s = sum((pi - ai) * ni for pi, ai, ni in zip(p, a, n))
            return [ai + s * ni for ai, ni in zip(a, n)]
        return [(-sp.oo, sp.oo, fn)]


# ------------------------------------------------------------------ one leg
def _seg_at(segs, t0, what, position_only=False):
    """The segment containing time t0 (refused exactly at a change of velocity, unless only the
    position is needed: positions are continuous)."""
    found = []
    for lo, hi, fn in segs:
        a, b = _ge(t0, lo), _ge(hi, t0)
        if a is None or b is None:
            raise UndeterminedError(f"{what}: cannot tell which part of the motion holds at t = {t0}; "
                                    f"give numbers")
        if a and b:
            found.append((lo, hi, fn))
    if len(found) > 1 and position_only:
        return found[0]
    if len(found) > 1:
        raise SceneError(f"{what}: t = {t0} is the instant the motion changes; the heard frequency jumps "
                         f"there; ask just before or after")
    if not found:
        raise SceneError(f"{what}: no motion defined at t = {t0}")
    return found[0]


def _norm2(vec):
    return sum(c ** 2 for c in vec)


class Leg:
    """Sound from an emitter (motion E) to a receiver (motion R) through air of speed v and wind w."""

    def __init__(self, E, R, v, w, what, line=None, sign=None):
        self.E, self.R, self.v, self.w, self.what, self.line = E, R, v, w, what, line
        self.sign = sign       # side of the receiver along the line, when geometry fixes it (walls)

    def _F(self, Eseg, Rseg, tau, t):
        d = [r - e - wi * (t - tau) for r, e, wi in zip(Rseg[2](t), Eseg[2](tau), self.w)]
        return _norm2(d) - self.v ** 2 * (t - tau) ** 2

    def _G1(self, Eseg, Rseg, tau, t, s):
        """1D: x_R(t) - x_E(tau) - w (t - tau) - s v (t - tau)."""
        a, n = self.line
        x = lambda p: sum((pi - ai) * ni for pi, ai, ni in zip(p, a, n))
        w1 = sum(wi * ni for wi, ni in zip(self.w, n))
        return x(Rseg[2](t)) - x(Eseg[2](tau)) - w1 * (t - tau) - s * self.v * (t - tau)

    def _sign1(self, Eseg, Rseg, time):
        if self.sign is not None:
            return self.sign
        a, n = self.line
        x = lambda p: sum((pi - ai) * ni for pi, ai, ni in zip(p, a, n))
        s = _decide(x(Rseg[2](time)) - x(Eseg[2](time)))
        if s is None:
            raise UndeterminedError(f"{self.what}: cannot tell on which side the listener is at t = {time} "
                                    f"(it depends on unknowns); ask with emitted= at a time whose positions "
                                    f"are known, e.g. emitted=0 s")
        if s == "zero":
            raise SceneError(f"{self.what}: source and listener are at the same place at t = {time}; "
                             f"the heard frequency is not defined there")
        return 1 if s == "pos" else -1

    def receive(self, t0):
        """Emission time te of the sound heard at t0, and dte/dt there."""
        Rseg = _seg_at(self.R.segments(), t0, self.what)
        tau, t = sp.Dummy("tau", real=True), sp.Dummy("t", real=True)
        hits = []
        for Eseg in self.E.segments():
            if self.line is not None:
                # the receiver is on the side it is on now: the emitter, slower than sound, is
                # always inside the sphere of sound it emitted earlier
                Enow = _seg_at(self.E.segments(), t0, self.what, True)
                s = self._sign1(Enow, Rseg, t0)
                eq = self._G1(Eseg, Rseg, tau, t0, s)
                cands = sp.solve(eq, tau)
            else:
                eq = sp.expand(self._F(Eseg, Rseg, tau, t0))
                cands = self._roots(eq, tau, Eseg, t0, below=True)
            for c in cands:
                if self._valid(c, Eseg, t0, below=True):
                    hits.append((c, Eseg))
        tau0, Eseg = self._one(hits, "emission")
        if self.line is not None:
            G = self._G1(Eseg, Rseg, tau, t, s)
        else:
            G = self._F(Eseg, Rseg, tau, t)
        rate = (-sp.diff(G, t) / sp.diff(G, tau)).xreplace({tau: tau0, t: t0})
        return tau0, sp.simplify(rate)

    def emit(self, tau0):
        """Arrival time t of the sound emitted at tau0, and dte/dt there."""
        Eseg = _seg_at(self.E.segments(), tau0, self.what)
        tau, t = sp.Dummy("tau", real=True), sp.Dummy("t", real=True)
        hits = []
        for Rseg in self.R.segments():
            if self.line is not None:
                Rnow = _seg_at(self.R.segments(), tau0, self.what, True)
                s = self._sign1(Eseg, Rnow, tau0)
                eq = self._G1(Eseg, Rseg, tau0, t, s)
                cands = sp.solve(eq, t)
            else:
                eq = sp.expand(self._F(Eseg, Rseg, tau0, t))
                cands = self._roots(eq, t, Rseg, tau0, below=False)
            for c in cands:
                if self._valid(c, Rseg, tau0, below=False):
                    hits.append((c, Rseg))
        t0, Rseg = self._one(hits, "arrival")
        if self.line is not None:
            G = self._G1(Eseg, Rseg, tau, t, s)
        else:
            G = self._F(Eseg, Rseg, tau, t)
        rate = (-sp.diff(G, t) / sp.diff(G, tau)).xreplace({tau: tau0, t: t0})
        return t0, sp.simplify(rate)

    def _roots(self, eq, var, seg, ref, below):
        """Roots of the (squared) condition in var: exact when it is a polynomial, else a
        bisection on the monotonic unsquared condition (circular motion; numbers only)."""
        if eq.is_polynomial(var):
            return [r for r in sp.solve(eq, var)]
        if eq.free_symbols - {var}:
            raise UndeterminedError(f"{self.what}: circular motion with symbols; give numbers")
        return [self._bisect(seg, ref, below)]

    def _bisect(self, seg, ref, below):
        mpmath.mp.dps = 40
        v, w = mpmath.mpf(str(sp.N(self.v, 45))), [mpmath.mpf(str(sp.N(c, 45))) for c in self.w]
        ref_ = mpmath.mpf(str(sp.N(ref, 45)))
        x = sp.Dummy("x")
        if below:          # unknown emission time; receiver fixed at ref
            Rp = [mpmath.mpf(str(sp.N(c, 45))) for c in _seg_at(self.R.segments(), ref, self.what)[2](ref)]
            Ef = sp.lambdify(x, seg[2](x), "mpmath")
            def g(tau):
                e = Ef(tau)
                d = [r - ei - wi * (ref_ - tau) for r, ei, wi in zip(Rp, e, w)]
                return mpmath.sqrt(sum(c ** 2 for c in d)) - v * (ref_ - tau)
            hi, step = ref_, mpmath.mpf(1)
            lo = hi - step
            while g(lo) > 0:
                step *= 2
                lo = hi - step
                if step > 1e12:
                    raise SceneError(f"{self.what}: no emission time found")
        else:              # unknown arrival time; emitter fixed at ref
            Ep = [mpmath.mpf(str(sp.N(c, 45))) for c in _seg_at(self.E.segments(), ref, self.what)[2](ref)]
            Rf = sp.lambdify(x, seg[2](x), "mpmath")
            def g(t):
                r = Rf(t)
                d = [ri - e - wi * (t - ref_) for ri, e, wi in zip(r, Ep, w)]
                return v * (t - ref_) - mpmath.sqrt(sum(c ** 2 for c in d))
            lo, step = ref_, mpmath.mpf(1)
            hi = lo + step
            while g(hi) < 0:
                step *= 2
                hi = lo + step
                if step > 1e12:
                    raise SceneError(f"{self.what}: the sound never arrives")
        for _ in range(200):
            mid = (lo + hi) / 2
            if (g(mid) > 0) == below:
                hi = mid
            else:
                lo = mid
        return sp.Float(str((lo + hi) / 2), 30)

    def _valid(self, c, seg, ref, below):
        if c.is_real is False or (c.is_number and abs(complex(sp.N(c)).imag) > 1e-20):
            return False
        gap = _decide(ref - c if below else c - ref)
        if gap is None and self.line is not None:
            # on a line the root of the side-aware equation has t > te whenever both move slower
            # than sound (checked again once the unknowns are known)
            gap = "pos"
        if gap is None:
            raise UndeterminedError(f"{self.what}: cannot decide which root is the physical one "
                                    f"(symbols in an oblique or moving geometry); give numbers")
        if gap != "pos":
            return False
        a, b = _ge(c, seg[0]), _ge(seg[1], c)
        if a is None or b is None:
            raise UndeterminedError(f"{self.what}: cannot tell which part of the motion holds at the "
                                    f"emission or arrival; give numbers")
        return a and b

    def _one(self, hits, kind):
        uniq = []
        for c, seg in hits:
            same = [u for u, s_ in uniq if sp.simplify(c - u) == 0]
            if same:
                raise SceneError(f"{self.what}: the {kind} falls exactly at an instant the motion changes; "
                                 f"the heard frequency jumps there; ask at a slightly different time")
            uniq.append((c, seg))
        if not uniq:
            raise SceneError(f"{self.what}: no {kind} time found (with a wall: has the wall reached the "
                             f"source or the listener by then? that echo does not exist)")
        if len(uniq) > 1:
            vals = [u for u, _ in uniq]
            if all(abs(float(sp.N(u - vals[0]))) < 1e-15 for u in vals if u.is_number):
                return uniq[0]
            raise SceneError(f"{self.what}: more than one {kind} time ({vals}); is something moving at "
                             f"or above the speed of sound?")
        return uniq[0]


# ------------------------------------------------------------------ rays
def _cross_zero(a, b):
    """a x b == 0 (2D or 3D) decided; None if undecidable."""
    if len(a) == 2:
        comps = [a[0] * b[1] - a[1] * b[0]]
    else:
        comps = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
    res = [_decide(c) for c in comps]
    if any(r is None for r in res):
        return None
    return all(r == "zero" for r in res)


def _unit(vec):
    n = sp.sqrt(_norm2(vec))
    if _decide(n) != "pos":
        return None
    return [sp.simplify(c / n) for c in vec]


def _line(motions, wind, normal=None):
    """(anchor, unit direction) if every position, velocity and the wind lie along one line;
    else None."""
    anchor = motions[0].at
    n = normal
    if n is None:
        for m in motions[1:]:
            n = _unit([b - a for a, b in zip(anchor, m.at)])
            if n is not None:
                break
    if n is None:
        for m in motions:
            for vel in (m.speeds() or []):
                n = _unit(vel)
                if n is not None:
                    break
            if n is not None:
                break
    if n is None:
        return None
    for m in motions:
        if m.kind == "circle":
            return None
        if _cross_zero([b - a for a, b in zip(anchor, m.at)], n) is not True:
            return None
        for vel in m.speeds():
            if _cross_zero(vel, n) is not True:
                return None
    if _cross_zero(wind, n) is not True:
        return None
    return anchor, n


class ImageMotion:
    """The mirror image of a motion in a stationary plane wall."""

    def __init__(self, m, ref):
        self.m, self.ref, self.kind, self.at = m, ref, m.kind, ref.image(m.at)

    def segments(self):
        return [(lo, hi, (lambda f: lambda tau: self.ref.image(f(tau)))(fn)) for lo, hi, fn in self.m.segments()]


def _check_subsonic(m, v, w, what, light=False):
    if light:
        msg = (f"{what}: moves at or above the speed of light in the medium; v0 does not model this "
               f"(Cherenkov radiation, superluminal motion)")
    else:
        msg = (f"{what}: moves at or above the speed of sound relative to the air; v0 handles subsonic "
               f"motion only (shock waves are not modelled)")
    if getattr(m, "kind", "static") == "circle":
        ok = _decide(v - m.speed - sp.sqrt(_norm2(w)))
        if ok in ("neg", "zero"):
            raise Supersonic(msg)
        return
    for vel in (m.speeds() if hasattr(m, "speeds") else []):
        ok = _decide(v ** 2 - _norm2([a - b for a, b in zip(vel, w)]))
        if ok in ("neg", "zero"):
            raise Supersonic(msg)


def legs(ray, air_listener_at=None):
    """The chain of legs from the source to the listener of a ray."""
    src, to, ref = ray.source, ray.to, ray.via_ref
    if to is None:
        raise SceneError(f"ray '{ray.name}': a stated-length path has no positions; motion needs to: <point>")
    v = src.medium.speed()
    w = getattr(src.medium, "wind", None) or [sp.Integer(0)] * len(src.at)
    if len(w) != len(src.at):
        raise SceneError(f"ray '{ray.name}': the wind needs {len(src.at)} components, like the positions")
    what = f"ray '{ray.name}'"
    sol = getattr(ray.sc, "solution", None) or {}
    v, w = sp.sympify(v).xreplace(sol), [sp.sympify(c).xreplace(sol) for c in w]
    E, R = SubsMotion(src.motion, sol), SubsMotion(to.motion, sol)
    for m, who in ((E, f"source '{src.name}'"), (R, f"point '{to.name}'")):
        _check_subsonic(m, v, w, who, light=getattr(src.medium, "kind", None) == "em")
    if ref is None:
        return [Leg(E, R, v, w, what, _line([E, R], w))]
    if ref.moving:
        uw = [sp.sympify(c).xreplace(sol) - wi for c, wi in zip(ref.velocity, w)]
        if _decide(v ** 2 - _norm2(uw)) in ("neg", "zero"):
            raise Supersonic(f"reflector '{ref.name}': moves at or above the speed of sound relative to the air")
    line = _line([E, R], w, normal=ref.n)
    if line is None:
        if ref.moving:
            raise SceneError(f"{what}: a moving wall is handled in v0 only when the source, the listener and "
                             f"their motion (and the wind) lie on one line along the wall's normal")
        if any(_decide(c) != "zero" for c in w):
            raise SceneError(f"{what}: a reflection with wind is handled in v0 only along the wall's normal line")
        return [Leg(ImageMotion(E, ref), R, v, w, what, None)]
    W = WallMotion(ref, line[0], line[1], sol)
    # the line runs along the wall's normal, which points to the front: sound goes to the wall
    # against the normal (receiver behind the emitter) and comes back along it
    return [Leg(E, W, v, w, what + f" (to the wall '{ref.name}')", line, sign=-1),
            Leg(W, R, v, w, what + f" (from the wall '{ref.name}')", line, sign=1)]


class SubsMotion:
    """A motion with solved unknowns substituted."""

    def __init__(self, m, sol):
        self.m, self.sol = m, sol
        self.kind = m.kind
        self.at = [sp.sympify(c).xreplace(sol) for c in m.at]
        if m.kind == "circle":
            self.speed = sp.sympify(m.speed).xreplace(sol)

    def segments(self):
        out = []
        for lo, hi, fn in self.m.segments():
            out.append((sp.sympify(lo).xreplace(self.sol), sp.sympify(hi).xreplace(self.sol),
                        (lambda f: lambda tau: [sp.sympify(c).xreplace(self.sol) for c in f(tau)])(fn)))
        return out

    def speeds(self):
        sp_ = self.m.speeds()
        return None if sp_ is None else [[sp.sympify(c).xreplace(self.sol) for c in vel] for vel in sp_]


def _front(ray, chain, te, tw, arrival):
    """With a wall: the source must be in front of the wall when it emits, and the listener
    when it hears (nothing passes through the wall)."""
    ref = ray.via_ref
    if ref is None:
        return
    sol = getattr(ray.sc, "solution", None) or {}
    wall = lambda time: [sp.sympify(p + u * time).xreplace(sol) for p, u in zip(ref.p0, ref.velocity)]
    for who, m, time in ((f"source '{ray.source.name}'", ray.source.motion, te),
                         (f"point '{ray.to.name}'", ray.to.motion, arrival)):
        pos = SubsMotion(m, sol)
        q = _seg_at(pos.segments(), time, ray.name, True)[2](time)
        side = _decide(sum((a - b) * c for a, b, c in zip(q, wall(time), ref.n)))
        if side in ("neg", "zero"):
            raise SceneError(f"ray '{ray.name}': at t = {time} the {who} is not in front of wall "
                             f"'{ref.name}' (it has reached or passed it); this echo does not exist")


def _sol(ray, e):
    return sp.sympify(e).xreplace(getattr(ray.sc, "solution", None) or {})


def trace(ray, t=None, emitted=None):
    """(emission time, arrival time, dte/dt) for the sound heard at t, or emitted at `emitted`."""
    if (t is None) == (emitted is None):
        raise SceneError(f"ray '{ray.name}': give exactly one of t= (when heard) or emitted= (when emitted)")
    chain = legs(ray)
    rate = sp.Integer(1)
    if ray.via_ref is None and _together(ray.source.motion, ray.to.motion):
        # a listener carrying its own source (same place at every instant): no delay, no shift
        te = arrival = _sol(ray, t if t is not None else emitted)
        chain = []
    elif t is not None:
        cur = _sol(ray, t)
        arrival = cur
        for leg in reversed(chain):
            cur, r = leg.receive(cur)
            rate = rate * r
        te = cur
    if chain and t is None:
        cur = _sol(ray, emitted)
        te = cur
        for leg in chain:
            cur, r = leg.emit(cur)
            rate = rate * r
        arrival = cur
    if getattr(ray.source.medium, "kind", None) == "em":
        # light: the phase is counted in the source's own time and read in the receiver's
        # own time, so f = f0 (gamma_receiver / gamma_source) dte/dt (special relativity)
        from .scene import SPEED_OF_LIGHT
        c = SPEED_OF_LIGHT                  # time dilation uses light's speed in vacuum
        rate = rate * _gamma(ray.to.motion, arrival, c, ray) / _gamma(ray.source.motion, te, c, ray)
    if _decide(rate) in ("neg", "zero"):
        raise SceneError(f"ray '{ray.name}': the sound cannot reach the listener this way (heard frequency "
                         f"{rate} x f); something moves at or above the speed of sound relative to the air")
    if ray.via_ref is not None and chain:
        _front(ray, chain, te, None, arrival)
    src = ray.source
    if src.emits_from is not None:
        ok = _ge(te, src.emits_from)
        if ok is None:
            raise UndeterminedError(f"ray '{ray.name}': cannot tell whether the source was already emitting")
        if not ok:
            raise NoSound(f"ray '{ray.name}': no sound yet: the sound arriving then would have left the "
                          f"source at t = {sp.nsimplify(te) if te.is_Float else te}, before it starts "
                          f"emitting at {src.emits_from}")
    return te, arrival, sp.simplify(rate)


def _together(a, b):
    """The two motions give the same position at every instant."""
    x = sp.Dummy("x", real=True)
    sa, sb = a.segments(), b.segments()
    if len(sa) != len(sb):
        return False
    for (l1, h1, f1), (l2, h2, f2) in zip(sa, sb):
        for u, v in ((l1, l2), (h1, h2)):
            if u != v and (u.is_infinite or v.is_infinite or sp.simplify(u - v) != 0):
                return False
        if any(sp.simplify(p - q) != 0 for p, q in zip(f1(x), f2(x))):
            return False
    return True


_RAYS = []


class HeardFrequency(sp.Function):
    """frequency(ray, t=t) against time for plots: evaluated sample by sample (each instant
    has its own emission time, and the formula may change between instants)."""

    @classmethod
    def eval(cls, rid, mode, x):
        if x.is_number:
            ray = _RAYS[int(rid)]
            kw = {"t": x} if int(mode) == 0 else {"emitted": x}
            try:
                return heard_frequency(ray, **kw)
            except SceneError:
                return sp.nan
        return None


def heard_frequency(ray, t=None, emitted=None):
    from .scene import T
    arg = t if t is not None else emitted
    if arg is not None and T in sp.sympify(arg).free_symbols:
        if ray not in _RAYS:
            _RAYS.append(ray)
        return HeardFrequency(_RAYS.index(ray), 0 if t is not None else 1, sp.sympify(arg))
    _, _, rate = trace(ray, t, emitted)
    return sp.simplify(_sol(ray, ray.source.f) * rate)


def emitted_at(ray, t=None):
    if t is None:
        raise SceneError("emitted_at(ray, t=...): give the time the sound is heard")
    return trace(ray, t=t)[0]


def arrives_at(ray, emitted=None):
    if emitted is None:
        raise SceneError("arrives_at(ray, emitted=...): give the time the sound leaves the source")
    return trace(ray, emitted=emitted)[1]


def air_wavelength(ray, t=None, emitted=None):
    """Wavelength of the sound arriving at the listener, measured in the air there:
    v / (frequency an observer moving with the air would hear)."""
    te, arrival, _ = trace(ray, t, emitted)
    chain = legs(ray)
    last = chain[-1]
    seg = _seg_at(last.R.segments(), arrival, last.what)
    pos = seg[2](arrival)
    air = FixedMotion([p - wi * arrival for p, wi in zip(pos, last.w)])
    air.kind, air.velocity, air.starts = "linear", list(last.w), None
    rate, cur = sp.Integer(1), arrival
    for k, leg in enumerate(reversed(chain)):
        if k == 0:
            leg = Leg(leg.E, air, leg.v, leg.w, leg.what, leg.line)
        cur, r = leg.receive(cur)
        rate = rate * r
    if getattr(ray.source.medium, "kind", None) == "em":
        from .scene import SPEED_OF_LIGHT
        rate = rate / _gamma(ray.source.motion, te, SPEED_OF_LIGHT, ray)
    return sp.simplify(ray.source.medium.speed() / (_sol(ray, ray.source.f) * rate))


class Supersonic(SceneError):
    """Motion at or above the speed of sound."""


def check_media(sc, sol):
    """After solving: a gas or fluid speed solved to light's range is refused; an em medium
    solved faster than light, or with n < 1, is inconsistent."""
    from .errors import InconsistentError
    from .scene import EMMedium, GasMedium, SOUND_SPEED_LIMIT, SPEED_OF_LIGHT
    for name, m in sc.objects.items():
        if isinstance(m, EMMedium):
            v = sp.sympify(m.v).xreplace(sol)
            if v.is_number and _decide(v - SPEED_OF_LIGHT) == "pos":
                raise InconsistentError(f"media.{name}: the facts make light faster than c ({sp.N(v, 6)} m/s)")
        elif isinstance(m, GasMedium):
            v = sp.sympify(m.v).xreplace(sol)
            if v.is_number and float(sp.N(v)) >= SOUND_SPEED_LIMIT:
                raise SceneError(f"media.{name}: the facts make the speed {sp.N(v, 6)} m/s: that is not sound in a "
                                 f"gas or fluid; for light, radar or radio use a medium of type: em")


def check_solution(sc, sol):
    """After the facts are solved: every moving ray must still be subsonic with the solved
    values (while solving, unknown speeds could not be checked)."""
    from .errors import InconsistentError
    from .rays import Ray
    if not sol:
        return
    old = getattr(sc, "solution", None)
    sc.solution = sol
    try:
        for name, obj in sc.objects.items():
            if isinstance(obj, Ray) and obj.moving and obj.to is not None:
                try:
                    legs(obj)
                except Supersonic as exc:
                    raise InconsistentError(f"the facts need motion at or above the speed of sound ({exc}); "
                                            f"no situation that v0 models fits them")
    finally:
        sc.solution = old


def _velocity(motion, time, ray):
    x = sp.Dummy("x", real=True)
    sol = getattr(ray.sc, "solution", None) or {}
    seg = _seg_at(SubsMotion(motion, sol).segments(), time, f"ray '{ray.name}'", True)
    return [sp.diff(c, x).xreplace({x: time}) for c in seg[2](x)]


def _gamma(motion, time, c, ray):
    u2 = _norm2(_velocity(motion, time, ray))
    if _decide(c ** 2 - u2) in ("neg", "zero"):
        raise Supersonic(f"ray '{ray.name}': something moves at or above the speed of light")
    return 1 / sp.sqrt(1 - u2 / c ** 2)


def wave_speed_seen(ray, t=None, emitted=None):
    """Speed of the arriving wave relative to the listener, along the direction it travels:
    v + (wind - listener velocity) . k for sound; c for light (relativity)."""
    te, arrival, _ = trace(ray, t, emitted)
    medium = ray.source.medium
    chain = legs(ray)
    if not chain:
        raise SceneError(f"ray '{ray.name}': the listener carries the source; no travelling wave reaches it")
    last = chain[-1]
    t_emit, _ = last.receive(arrival)
    Eseg = _seg_at(last.E.segments(), t_emit, last.what, True)
    Rseg = _seg_at(last.R.segments(), arrival, last.what, True)
    d = [r - e - wi * (arrival - t_emit) for r, e, wi in zip(Rseg[2](arrival), Eseg[2](t_emit), last.w)]
    k = [c_ / (last.v * (arrival - t_emit)) for c_ in d]
    uL = _velocity(ray.to.motion, arrival, ray)
    if getattr(medium, "kind", None) == "em":
        # relativistic velocity addition along the direction of travel (medium frame)
        from .scene import SPEED_OF_LIGHT
        c, w_ = SPEED_OF_LIGHT, last.v
        u = sum(ui * ki for ui, ki in zip(uL, k))
        return sp.simplify((w_ - u) / (1 - w_ * u / c ** 2))
    return sp.simplify(last.v + sum((wi - ui) * ki for wi, ui, ki in zip(last.w, uL, k)))
