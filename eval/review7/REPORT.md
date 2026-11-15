# Review 7: shaped pulses (milestone 7)

Scratch scenes are in this folder (`a`..`j2`). All findings below were run unless marked SUSPECTED.
Test strings: s1 mu 0.01 kg/m, s2 mu 0.04 kg/m, T 100 N (v 100 / 50 m/s, r = -1/3, t = 2/3).

## Findings, by severity

### 1. peak()/amplitude() silently return 0 when the peak position is symbolic — CONFIRMED, silent wrong
- Scenes `d.yaml`, `d_pk_sym_t`, `d_pk_given_sym_t`, `d_pk_p_t`.
- `0.01*exp(-((x - a)/0.05)**2)` with symbol `a`: `peak(p)` = 0, `amplitude(p)` = 0. Expected 0.01 (or an error).
- Numeric shape, symbolic instant: `peak(q, t=t0)` = 0 (expected 0.01). Same for a `given` wave
  `0.02/(1 + (x - 3t)^2)`: `peak(g, t=t0)` = 0 (expected 0.02).
- Why: `_extreme_values` drops every candidate point that is not a number (`q.is_number`), leaving only the
  limits at infinity. A symbolic amplitude `A*exp(...)` does error correctly.
- With a junction the same shape gives the "cannot check" error (`f1`), so the leak is peak/amplitude only.

### 2. Second reflection is silently missing — CONFIRMED, silent wrong
- `c.yaml`: string free at 0, fixed at 2 m, triangle at 0.5 m moving +x. `y(sum[p, p_reflected], x=0.5, t=0.04)`
  = 0 and `peak(s, t=0.04)` = 0. Expected -0.01 (reflected at the wall at 0.015 s, at the free end at 0.035 s).
- `i1.yaml`: `p_transmitted` reaching a second junction K is neither reflected nor refused (reads 0 afterwards).
- PLAN excludes multiple reflections, but nothing refuses or warns. Derived pulses heading for a junction
  should error once evaluated after their arrival time.

### 3. travel_time ignores string extents and can be negative — CONFIRMED
- `g2.yaml`: `travel_time(s1, start=0, end=5 m)` with the junction at 2 m returns 0.05 s. The true time is
  0.02 + 0.06 = 0.08 s. `y()` enforces extents; `travel_time` does not.
- Hanging rope: `travel_time(rope, start=L, end=0)` = -2*sqrt(L/g). Expected +2*sqrt(L/g). Symbolic limits on a
  non-uniform string are signed; numeric and uniform cases take the absolute value (inconsistent).

### 4. peak() of two smooth pulses runs 120 s, then errors — CONFIRMED (no wrong answer)
- `j1.yaml`: `peak(sum[p, p_reflected], t=0.01)` (example 11_02_011, before arrival; expected 0.035) and
  `j2.yaml` (two separated Gaussians; expected 0.02): "evaluation exceeded 120 s; simplify the scene".
- The same sum at the overlap instant returns 0.02 = t*A correctly. The documented use
  "`sum: [p, p_reflected]`" is therefore mostly unusable with `peak` for Gaussians; triangles work.

### 5. Adjacent step windows create a one-point spike — CONFIRMED, low
- `h1.yaml`: `0.02*x*step(x)*step(1-x) + 0.005*step(x-1)*step(2-x)` gives `peak` = 0.025; the intended shape
  peaks at 0.02. Both windows are 1 at x = 1 (step(0) = 1). Literal, but the FORMAT idiom invites it.

### 6. Symbolic impedance blocks amplitude(p_reflected) — CONFIRMED, low
- `i1.yaml`: numeric shape, `mu: mu2` on the far string: "cannot find the extremes ... give its shape with
  numbers". `y(q_reflected, ...)` returns the right symbolic value; the message blames the shape.

### 7. Stale or misleading messages — CONFIRMED, low
- `g4`: a `given` pulse on a junction string is told to "write it as a harmonic wave" (should name `pulse: shape`).
- `g3`: legacy pulse error says "for now use a harmonic wave" (same).
- `f3`: refusal prints "0.1% of its peak" for 0.116%, which reads as at the limit.

### 8. Qualification gaps — low
- CONFIRMED (`g1`): a pulse moving away from a junction but straddling it at t = 0 is accepted; only the
  junction ahead is checked.
- Strictness: a Lorentzian of 1 m width 1.5 m from the junction is refused (30.8%); it would need about
  32 m. Clear error, arguably correct.

## Verified correct (hand values matched)
- +x pulse, junction on the right (`a`): Ar 1/300, At 1/150, transmitted peak and half-height positions
  (width x v2/v1), reflected value and sign, zero reflected field before arrival, zero incident field after
  passing, velocities -100/+50, vy = -v*slope, peak of the sum at the junction = t*A.
- Mirror case, -x pulse with the junction on the left (`b`); heavy to light, r = +1/3, t = 4/3, width x2 (`i1`).
- Fixed end inverts, free end keeps sign and doubles at the end, wall displacement 0 (`c`, `f5`); cm units.
- Refusals: pulse starting past or across the junction, on the wrong string, symbolic centre, `given` wave,
  legacy pulse, sum across media.
- peak: triangle, rectangle (negative, half past the junction), half-sine, min-clipped, odd shape, cancelling and
  partly overlapping pulses; extent respected.
- travel_time: uniform, reversed numeric, gas, mu = 0.01(1+s)^2 (0.015 s), hanging rope 2*sqrt(L/g), unit errors.
- Harmonic wave and pulse at one junction coexist; frequency/wavelength/power of a pulse error clearly.
- Views build for pulse scenes (page content not inspected).
