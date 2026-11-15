# Review 8: string energy and pulse width (m8)

Scenes/outputs: `eval/review8/*.yaml`, `*.out`. All CONFIRMED (ran) unless marked.
Base string unless stated: mu 0.01 kg/m, T 4 N (v 20 m/s).

## A. Silent wrong answers (items 2-4: expected the r91 refusal)

1. **Numeric integral fallback is inaccurate and shown to 12 digits** (`_integrate`: `mpmath.quad` over
   (-oo, oo) or the extent, ignoring breakpoints).
   - a15: `energy(p)`, shape `0.01*sin(pi*x)*exp(sin(3*x))` on [0,1] -> 0.0131908365074. Hand (T*int g'^2): 0.0133307807
     (1% off). b11, same pulse with `start=0,end=1`, gives 0.0133307806695.
   - a07d: `energy(sum[p, p_reflected], t=0.03 s)` on r90's junction -> 0.00155303457. Hand: E_in/2 + E_r/2 =
     15*pi^2/100000 = 0.0014804 (4.9% off). Also took 33 s.
2. **Jump refusal is skipped whenever the breakpoint is not a number; answer is 0**.
   - a03: r91's rectangle with `energy(p, start=0, end=50, t=t)` -> `E = 0`. a03b: `mean_over(t, kinetic_energy(..., t=t), 0, 1)` -> 0.
   - a01: rectangle at symbolic position `step(x-a) - step(x-a-0.2)`, `energy(p)` -> 0.
3. **Jumps at periodic breakpoints missed** (solveset not a FiniteSet). a04: `0.001*x*(10-x)*step(sin(x))` on [0,10]
   (jumps at pi, 2pi, 3pi) -> finite 0.00128783.
4. **Small jumps missed**: tolerance `1e-6*(1+...)` is absolute in metres. a02: rectangle of height 1e-7 m -> `E = 0`.
5. **`peak_position` numeric fallback (`_numeric_argmax`)**:
   - b14: Gaussians 0.035 m at x=300.3 and 0.02 m at x=0.5 (width 0.05) -> `where = 0.500000000336`. Expected 300.3
     (outside +-50 the grid is log-spaced, ~2 m apart there).
   - b15: two equal 0.02 m Gaussians at 0.5123 and 2.7391 -> 0.5123. Expected "ambiguous": the tie test compares grid
     samples to 1e-9, so off-grid equal peaks never tie.
6. **Densities have no extent check**. a06: `potential_density(p, x=0.5 m, t=0.05 s)` with p on L (ends at x=0) ->
   pi^2/10000, the incident image beyond the junction. `y(p, x=0.5)` correctly errors (b04).
7. **Pulse energy with `start/end` but no `t` silently uses t=0**. a07a: `energy(p_reflected, start=-1.2, end=0)` -> 0;
   a07e: `energy(p_transmitted, start=0, end=1)` -> 0 (the image lies off the string at t=0). Expected: demand `t`
   when a stretch is given.
8. **Density at a kink returns a value that is neither one-sided slope**. b03 (r87's shape, kink at 0.6):
   `potential_density(p, x=0.6, t=0)` -> 81/5000 (slope 0.09); left 0.0018, right 0.0072. Expected an error.

## B. Dimension holes
- a13b: `kinetic_density(w, x=0[s], t=0[m])` accepted (energy() does check, a13a).
- a13c: `mean_over(t, ..., 0[m], 1[m])` accepted.
- a13f: `mean_over(t, kinetic_density(...), 0[s], period(w)) + 1[J]` accepted (J/m + J); the bare density + 1[J] is refused (b02).

## C. Errors and limits
- width(): "engine internal error ... please report" for symbolic `A*sin(pi*x/L)` on [0,L] (w01) and for any periodic
  condition, `abs(sin(pi*x))` window (w04, true width 2), `max(0, 0.01*sin(x))` (w07). Shape `0*x`: "never falls to
  zero" (w05); identically-zero piecewise: "bad arguments ('int' object has no attribute 'is_infinite')" (w11).
- w06: two separate bumps (each 1 m, gap 2 m) -> width 2; span is 4. Definition should be stated, or refused.
- b06: `given: 0.02*sin(pi*x)*cos(20*pi*t)` with `on:` is rejected ("not a travelling wave"), so a given standing wave
  has no energy; only `sum:` works.
- a12b: symbolic `start=a, end=b` gives a signed result, while numeric reversed bounds are swapped (a12).
- a11c: harmonic on a hanging string: "wavelength is not specified" (misleading).
- Timing: any fallback first spends the 30 s symbolic budget (a15, a07d: 33 s).
- SUSPECTED: kinks with slope > ~500 would be reported as jumps (eps 1e-9, tol 1e-6); slope 1000 at height 0.5 passed (a05).

## Verified correct (hand values)
- Partially standing wave (A 0.02/0.01, a09): K0 = 9pi^2/5000, U0 = pi^2/5000, total pi^2/500 at any t, mean K = pi^2/1000.
- Given wave in cm (a10): E per wavelength pi^2/625, densities right.
- Non-uniform mu(s) and hanging string with a given wave (a11, a11b): densities at a number and at `s`.
- Junction mid-transit (a07c): transmitted and reflected each half at t=0.03 s; before arrival 0; fixed end E_r = E_in, width kept (b05).
- Triangle and asymmetric triangle energies and widths (a06b, b03); Gaussian energy sqrt(2pi)/500 (b16); symbolic half-sine 2pi^2A^2/L (b10).
- width: abs-built triangle 2, `step(1-x^2)` 2, rectangle 1, Gaussian and half-line refused clearly (w02, w03, w08-w10, w12).
- Reversed/equal bounds, unbounded harmonic energy (clear error), hi<lo in mean_over, energy() kwarg dimensions.
