"""Export a scene as view data: sampled arrays plus labelled provenance.

The viewer only draws these arrays; it never evaluates physics. The exporter never
invents facts:
* a display window is chosen automatically only where the physics supplies a natural scale
  (wavelength, period) and is then labelled as an engine display choice;
* symbols without values, windows without a scale and inputs to vary must come from the
  scene (`illustrate`, `view`, `explore`); otherwise the export lists what is missing;
* every varied value carries its own results, illustrative values, facts and re-checks;
  windows, plot ranges and y-ranges are fixed across varied values so differences show.
"""
import copy
import math

import sympy as sp

from .errors import SceneError
from .expr import dimension_of, show_dim
from .run import evaluate, show
from .scene import GivenWave, Harmonic, Scene, T, X
from .units import DIMLESS, LENGTH, TIME, split_quantity

N_X, N_FRAMES, N_PLOT = 240, 60, 240
PANEL_KEYS = {"snapshot": {"snapshot", "t", "x"}, "animate": {"animate", "x", "t"},
              "plot": {"plot", "vs", "range"}}


class ViewError(SceneError):
    """The scene does not carry enough to draw it without inventing something."""


def _num(e):
    return float(sp.N(e))


def _finite(v):
    return v if (v is not None and math.isfinite(v)) else None


# ------------------------------------------------------------------ illustrate
def _illustrate(sc):
    """Return ({symbol: SI value}, {name: text as written}). Checks unit, dimension, kind."""
    vals, texts = {}, {}
    for name, val in (sc.data.get("illustrate") or {}).items():
        sym = sc.names.get(name)
        bound = getattr(sc, "bounds", {}).get(name)
        if bound is not None:
            sym = bound[0]                 # check against the declared symbol, then store the offset
        if sym is None or sym not in sc.kinds or sym in sc.unknowns:
            raise ViewError(f"illustrate.{name}: must be a declared symbol (not an unknown)")
        text, unit, factor, udim = split_quantity(val)
        want = sc.symbol_dims.get(sym)
        if bound is not None and want is None:
            want = sc.bound_dims.get(name)   # a bounded symbol has its bound's dimension
        if udim is None:
            if want not in (None, DIMLESS) or (want is None and text.strip() not in ("0",)):
                if want is None:
                    raise ViewError(f"illustrate.{name}: give a unit (e.g. '1 cm'), or '1 rad' if dimensionless")
                raise ViewError(f"illustrate.{name}: needs a unit of dimension {show_dim(want)}")
        elif want is not None and udim != want:
            raise ViewError(f"illustrate.{name}: unit '{unit}' has the wrong dimension "
                            f"(expected {show_dim(want)})")
        q = sc.expr(text) * factor
        if q.free_symbols or not q.is_real:
            raise ViewError(f"illustrate.{name}: must be a plain number with a unit")
        kind = sc.kinds[sym]
        if kind == "positive" and not q.is_positive:
            raise ViewError(f"illustrate.{name}: '{name}' is declared positive")
        if kind == "integer" and not q.is_integer:
            raise ViewError(f"illustrate.{name}: '{name}' is declared integer")
        if bound is not None:
            orig, p, back = bound
            off = sp.simplify(back.xreplace({orig: q}))
            if off.is_negative or (p.is_positive and not off.is_positive):
                raise ViewError(f"illustrate.{name}: {val} is outside the stated bound on '{name}'")
            vals[p], texts[name] = off, str(val)
            continue
        vals[sym], texts[name] = q, str(val)
    return vals, texts


_BOUNDS = {}       # offset symbol -> (declared symbol, offset); set per export by _one


def _closed(e, sol, illus, allowed, missing, what):
    """Substitute solution and illustrative values; report leftover symbols.
    Returns (value or None, used_illustrative)."""
    e1 = sp.sympify(e).xreplace(sol).doit()
    used = bool(e1.free_symbols & set(illus))
    e2 = e1.xreplace(illus).doit()
    free = {s for s in e2.free_symbols if s not in allowed}
    if free:
        names = sorted({str(b[0]) if s == b[1] else str(s) for s in free
                        for b in (_BOUNDS.get(s, (None, None)),)})
        missing.append(f"{what}: no value for {names} (add them to `illustrate`)")
        return None, used
    return e2, used


# ------------------------------------------------------------------ windows
def _bound(sc, text, want, what, sol, illus, missing):
    """A window/range bound such as '0 m' or '2*period(w)': (value, used_illustrative)."""
    t, unit, factor, udim = split_quantity(text)
    if udim is not None and want is not None and udim != want:
        raise ViewError(f"{what}: unit '{unit}' has the wrong dimension (expected {show_dim(want)})")
    if udim is None:
        d = dimension_of(t, sc)
        if d is not None and want is not None and d != want:
            raise ViewError(f"{what}: '{text}' has dimension {show_dim(d)}, expected {show_dim(want)}")
    v, used = _closed(sc.expr(t) * factor, sol, illus, set(), missing, what)
    return (None if v is None else _num(v)), used


def _default_scale(sc, sol, illus, kind):
    best, used_any = None, False
    for o in sc.objects.values():
        if not isinstance(o, (Harmonic, GivenWave)):
            continue
        try:
            s = (2 * sp.pi / o.wavenumber()) if kind == "x" else (2 * sp.pi / o.ang_freq())
        except SceneError:
            continue
        s1 = sp.sympify(s).xreplace(sol)
        used = bool(s1.free_symbols & set(illus))
        s2 = s1.xreplace(illus)
        if not s2.free_symbols and _num(s2) > 0:
            if best is None or _num(s2) > best:
                best, used_any = _num(s2), used
    return best, used_any


def _window(sc, spec, kind, sol, illus, missing):
    """(lo, hi, label) for kind 'x' or 't'."""
    want = LENGTH if kind == "x" else TIME
    if kind in spec:
        b = [_bound(sc, v, want, f"view {kind}", sol, illus, missing) for v in spec[kind]]
        if any(v is None for v, _ in b):
            return None
        lo, hi = b[0][0], b[1][0]
        label = "author-chosen display window"
        if any(u for _, u in b):
            label += " (computed with illustrative values)"
        return lo, hi, label
    s, used = _default_scale(sc, sol, illus, kind)
    if s is None:
        missing.append(f"view: no natural {kind}-scale for this panel; give `{kind}: [lo, hi]`")
        return None
    unit = "wavelengths" if kind == "x" else "periods"
    label = f"engine display choice: 2 {unit} of the longest wave (not source geometry)"
    if used:
        label += ", computed with illustrative values"
    return 0.0, 2 * s, label


def _clip(wave, xw, sol, illus, missing, what):
    """Clip an x window to the extent of the medium (or media) the wave lives on."""
    if xw is None:
        return None
    lo, hi, label = xw
    exts = []
    for part in getattr(wave, "parts", [wave]):
        ext = getattr(getattr(part, "medium", None), "extent", None) or (None, None)
        vals = []
        for b in ext:
            v = None if b is None else sp.sympify(b).xreplace(sol).xreplace(illus)
            vals.append(float(v) if v is not None and v.is_number else None)
        exts.append((part, vals))
    if label.startswith("engine display choice"):
        # an engine-chosen window is placed inside the medium, not across a junction
        width = hi - lo
        e_hi = min((v[1] for _, v in exts if v[1] is not None), default=None)
        e_lo = max((v[0] for _, v in exts if v[0] is not None), default=None)
        before = (lo, hi)
        if e_hi is not None and hi > e_hi:
            lo, hi = e_hi - width, e_hi
        if e_lo is not None and lo < e_lo:
            lo, hi = e_lo, e_lo + width
        if (lo, hi) != before:
            label += "; placed inside the medium"
    clipped = []
    for part, vals in exts:
        for k, v in enumerate(vals):
            if v is None:
                continue
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


# ------------------------------------------------------------------ panels
def _wave(sc, name, missing, what):
    wave = sc.objects.get(name)
    if not isinstance(wave, (Harmonic, GivenWave)):
        missing.append(f"{what}: '{name}' is not a wave with a field")
        return None, None
    try:
        return wave, wave.field()
    except SceneError as exc:
        missing.append(f"{what} {name}: {exc}")
        return None, None


def _panel(sc, spec, sol, illus, missing, fixed):
    kinds = [k for k in PANEL_KEYS if k in spec]
    if len(kinds) != 1:
        raise ViewError(f"view panel {spec}: use exactly one of snapshot / animate / plot")
    kind = kinds[0]
    extra = set(spec) - PANEL_KEYS[kind]
    if extra:
        raise ViewError(f"view {kind} panel: unknown key(s) {sorted(extra)}")
    fixed = fixed or {}
    if kind in ("snapshot", "animate"):
        name = spec[kind]
        wave, field = _wave(sc, name, missing, f"view {kind}")
        if wave is None:
            return None, {}
        xw = fixed.get("x") or _clip(wave, _window(sc, spec, "x", sol, illus, missing),
                                     sol, illus, missing, f"view {kind} {name}")
        if kind == "snapshot":
            if "t" not in spec:
                raise ViewError("view snapshot: give t: <instant>")
            t0, used_t = _bound(sc, spec["t"], TIME, "view snapshot t", sol, illus, missing)
            f, used = _closed(field.xreplace({T: t0}) if t0 is not None else field, sol, illus, {X},
                              missing, f"snapshot of {name}")
            if f is None or xw is None or t0 is None:
                return None, {}
            fn = sp.lambdify(X, f, "math")
            xs = [xw[0] + (xw[1] - xw[0]) * i / (N_X - 1) for i in range(N_X)]
            return ({"kind": "snapshot", "wave": name, "t": t0, "x": xs,
                     "y": [_finite(float(fn(x))) for x in xs], "x_basis": xw[2],
                     "uses_illustrative": used or used_t,
                     "y_label": f"y of {name} (m)", "x_label": "x (m)"}, {"x": xw})
        tw = fixed.get("t") or _window(sc, spec, "t", sol, illus, missing)
        f, used = _closed(field, sol, illus, {X, T}, missing, f"field of {name}")
        if f is None or xw is None or tw is None:
            return None, {}
        fn = sp.lambdify((X, T), f, "math")
        xs = [xw[0] + (xw[1] - xw[0]) * i / (N_X - 1) for i in range(N_X)]
        ts = [tw[0] + (tw[1] - tw[0]) * k / N_FRAMES for k in range(N_FRAMES)]
        frames = [[_finite(float(fn(x, t))) for x in xs] for t in ts]
        return ({"kind": "animate", "wave": name, "x": xs, "t": ts, "frames": frames,
                 "x_basis": xw[2], "t_basis": tw[2], "uses_illustrative": used,
                 "y_label": f"y of {name} (m)", "x_label": "x (m)"}, {"x": xw, "t": tw})
    # plot
    target = spec["plot"]
    text = (sc.data.get("observe") or {}).get(target, target)
    var_name = spec.get("vs")
    var = {"x": X, "t": T}.get(var_name) or sc.names.get(var_name)
    if not isinstance(var, sp.Symbol):
        raise ViewError(f"view plot {target}: unknown variable '{var_name}'")
    if "range" not in spec or len(spec["range"]) != 2:
        raise ViewError(f"view plot {target}: give range: [lo, hi] for {var_name}")
    want = {"x": LENGTH, "t": TIME}.get(var_name) or sc.symbol_dims.get(var)
    rng = fixed.get("range")
    if rng is None:
        b = [_bound(sc, v, want, f"view plot {target} range", sol, illus, missing) for v in spec["range"]]
        if any(v is None for v, _ in b):
            return None, {}
        label = "author-chosen display range"
        if any(u for _, u in b):
            label += " (computed with illustrative values)"
        rng = (b[0][0], b[1][0], label)
        if want is None:
            want = split_quantity(spec["range"][0])[3] or split_quantity(spec["range"][1])[3]
    e, used = _closed(sc.expr(text, check_dims=True), sol,
                      {k: v for k, v in illus.items() if k != var}, {var}, missing, f"plot {target}")
    if e is None:
        return None, {}
    from .doppler import HeardFrequency
    if e.has(HeardFrequency):          # each instant solved on its own (emission time)
        fn = lambda v_: sp.N(e.xreplace({var: sp.Float(v_, 20)}), 15)
    else:
        fn = sp.lambdify(var, e, "math")
    vs = [rng[0] + (rng[1] - rng[0]) * i / (N_PLOT - 1) for i in range(N_PLOT)]
    ys = []
    for v in vs:
        try:
            y = complex(fn(v))
            ys.append(_finite(y.real) if abs(y.imag) < 1e-12 else None)
        except (ZeroDivisionError, ValueError, OverflowError, TypeError):
            ys.append(None)
    ydim = dimension_of(text, sc)
    return ({"kind": "plot", "name": target, "expr": text, "vs": var_name, "v": vs, "y": ys,
             "x_label": f"{var_name} ({show_dim(want) if want else 'SI'})",
             "y_label": f"{target} ({show_dim(ydim) if ydim is not None else 'SI units'})",
             "range_basis": rng[2], "uses_illustrative": used}, {"range": rng})


# ------------------------------------------------------------------ scene export
def _numbers(sc, res, illus):
    out = {}
    for k, e in getattr(sc, "obs_errors", {}).items():
        out[k] = {"text": f"not available: {e}", "basis": None, "value": None, "unavailable": True}
    for k, v in res.items():
        if isinstance(v, sp.logic.boolalg.BooleanAtom):
            out[k] = {"text": str(bool(v)), "basis": sc.basis.get(k)}
            continue
        if isinstance(v, sp.Tuple):                 # a list result: shown as text, no single value
            out[k] = {"text": show(v), "basis": sc.basis.get(k), "value": None,
                      "uses_illustrative": bool(v.free_symbols & set(illus))}
            continue
        e = v.xreplace(illus)
        val = _finite(_num(e)) if not e.free_symbols and e.is_real is not False else None
        out[k] = {"text": show(v), "basis": sc.basis.get(k), "value": val,
                  "uses_illustrative": bool(v.free_symbols & set(illus))}
    return out


def _one(data, fixed):
    """Export one scene (no variants). `fixed` is a list of per-panel windows, or None."""
    sc = Scene(copy.deepcopy(data))
    sol, res = evaluate(sc)
    _BOUNDS.clear()
    _BOUNDS.update({b[1]: (b[0], b[1]) for b in getattr(sc, "bounds", {}).values()})
    arb = getattr(sc, "arbitrary_solved", {})
    illus, illus_text = _illustrate(sc)
    view = sc.data.get("view")
    missing, panels, windows = [], [], []
    if not view:
        waves = [n for n, o in sc.objects.items() if isinstance(o, (Harmonic, GivenWave))]
        if not waves:
            missing.append("no `view` given and no wave with a field to show by default")
        view = [{"animate": n} for n in waves]
    for i, spec in enumerate(view):
        p, win = _panel(sc, spec, sol, illus, missing, fixed[i] if fixed else None)
        if p and getattr(sc, "arbitrary", None):
            p["arbitrary_note"] = (f"drawn at arbitrary values {sorted(sc.arbitrary)} the problem does not "
                                   f"give: only scale-free features (ratios, shapes) are meaningful")
        panels.append(p)          # keep indices aligned; None = could not draw
        windows.append(win)
    return {
        "id": data.get("id"),
        "assume": data.get("assume") or [],
        "facts": [{"text": t, "source": s} for t, s in getattr(sc, "facts", [])],
        "solved": {str(k): show(sc.show_back(v)) + ("" if arb.get(k, True) else
                                                     "  (depends on the arbitrary values: for drawing only)")
                   for k, v in sol.items()},
        "arbitrary": {k: str(v) for k, v in (data.get("arbitrary") or {}).items()},
        "results": _numbers(sc, res, illus),
        "verification": [{"fact": t, "basis": b} for _, t, b in getattr(sc, "verification", [])],
        "illustrative": illus_text,
        "panels": panels,
        "missing": missing,
    }, windows, sc


def _get_path(data, path):
    node = data
    for k in path.split("."):
        if not isinstance(node, dict) or k not in node:
            raise ViewError(f"explore: path '{path}' not found in the scene")
        node = node[k]
    return node


def _set_path(data, path, value):
    keys = path.split(".")
    _get_path(data, path)
    node = data
    for k in keys[:-1]:
        node = node[k]
    node[keys[-1]] = value


def _same_quantity(sc, a, b):
    try:
        qa, qb = (sp.sympify(sc.expr(split_quantity(v)[0])) * split_quantity(v)[2] for v in (a, b))
        return bool(sp.simplify(qa - qb) == 0)
    except SceneError:
        return str(a) == str(b)


def _y_ranges(items):
    """One y-range per panel index across all exported variants (and frames)."""
    n = max((len(it["panels"]) for it in items if it.get("panels")), default=0)
    for i in range(n):
        lo, hi = math.inf, -math.inf
        for it in items:
            p = (it.get("panels") or [None] * n)[i]
            if not p:
                continue
            arrays = p["frames"] if p["kind"] == "animate" else [p["y"]]
            for arr in arrays:
                for y in arr:
                    if y is not None:
                        lo, hi = min(lo, y), max(hi, y)
        if lo <= hi:
            for it in items:
                p = (it.get("panels") or [None] * n)[i]
                if p:
                    p["y_range"] = [lo, hi]


def export(data):
    base, windows, sc = _one(data, None)
    base["variants"] = None
    ex = data.get("explore")
    if not ex:
        base["missing"].append("no `explore` block: nothing declared to vary")
        _y_ranges([base])
        return base
    if not isinstance(ex, dict) or set(ex) != {"vary"} or not isinstance(ex["vary"], dict) \
            or len(ex["vary"]) != 1:
        raise ViewError("explore: {vary: {<symbol or scene.path>: [values...]}} with one entry")
    (target, values), = ex["vary"].items()
    if not isinstance(values, list) or len(values) < 2:
        raise ViewError("explore.vary: give a list of at least two values")
    in_illustrate = target in (data.get("illustrate") or {})
    is_arbitrary = target.startswith("arbitrary.")
    source_value = (data["illustrate"][target] if in_illustrate else _get_path(data, target))
    for p in base["panels"]:
        if p:
            for key in ("x_basis", "t_basis", "range_basis"):
                if key in p:
                    p[key] += "; kept fixed for every varied value"
    items = []
    for val in values:
        d2 = copy.deepcopy(data)
        d2.pop("explore", None)
        if in_illustrate:
            d2["illustrate"][target] = val
        else:
            _set_path(d2, target, val)
        item = {"value": str(val),
                "is_source": False if is_arbitrary else _same_quantity(sc, val, source_value)}
        try:
            sub, _, _ = _one(d2, windows)
            for p in sub["panels"]:
                if p:
                    for key in ("x_basis", "t_basis", "range_basis"):
                        if key in p:
                            p[key] = (p[key] + "; kept fixed for every varied value"
                                      if "kept fixed" not in p[key] else p[key])
            item.update({k: sub[k] for k in ("panels", "results", "solved", "missing",
                                             "illustrative", "facts", "verification")})
        except SceneError as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
        items.append(item)
    _y_ranges([base] + items)
    base["variants"] = {"target": target,
                        "target_kind": ("illustrative value" if in_illustrate else
                                        "arbitrary value (not given by the problem)" if is_arbitrary
                                        else "physical input"),
                        "source_value": None if is_arbitrary else str(source_value), "items": items}
    return base
