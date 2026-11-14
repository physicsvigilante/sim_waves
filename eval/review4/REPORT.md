# Review 4: point sources, reflectors, rays (milestone 4)

Scratch scenes are `eval/review4/tNN.yaml`. Regression suite: 49 PASS. Engine, docs and tests untouched.

## Findings, by severity

**1. CONFIRMED, silent wrong answer: `relative_intensity` decides coherence before `given` is solved (t01, t24).**
S1 `f: 170 Hz`, S2 `f: f0` (unknown), fact `wavelength(S2) == 2[m]` solves f0 = 170. Equal paths, A = 1 each.
Observed `I = 2`. Expected 4 (same frequency, in phase).
Why: `_groups_loose` keys on `srepr(simplify(f))` of the unsolved expression, so `f0` and `170` are "different frequencies" and intensities add. The solution is substituted only afterwards. On the same scene `resultant_amplitude` and `phase_difference` reject with "different frequencies" (t01b, t01c): safe, but false. `maxima` substitutes `sc.solution` and is correct.
Same root, t24: two free symbols f1, f2 give `I = 2` instead of "cannot tell whether the frequencies are equal".

**2. CONFIRMED, hang: symbolic `relative_intensity` on ordinary geometry (t31).**
The r41 scene (paths 120 m and 130 m, `f: 340/lam`) with `relative_intensity(up, direct)` hits the 120 s limit: "evaluation exceeded 120 s; simplify the scene". Expected `4*cos(10*pi/lam)**2`.
Why: `expand_trig` in `_coherent_amp2` expands cos(240*pi/lam) into a degree-240 polynomial. Milder case t22 (paths 1 m, 3 m) returns a correct but unreadable degree-6 polynomial instead of `4*cos(2*pi/lam)**2`. Only phase differences should enter.

**3. CONFIRMED, silent nonsense: amplitudes of different dimensions add (t07).**
`A: 1 Pa` and `A: 1 mm` give `resultant_amplitude = 1001/1000`, `relative_intensity = 1.002001`. Expected a dimension error. `A` is parsed with dimension `None` and never compared between sources.

**4. CONFIRMED, no dimension check on `maxima`/`minima` `lo`/`hi` (t05b).**
`lo=0.5[Hz], hi=2[kg]` with `vary=lam` and bare `lo=0.5, hi=2` both return the same list as metres. `resonances` checks this; `maxima` does not (`call_dim` has no branch).

**5. CONFIRMED, missing validation of unphysical inputs (t13, t06).**
- stated `length: 0 m` with spherical spreading: `amplitude = zoo`, printed as a result;
- `length: -2 m`: accepted, amplitude -1/2;
- `f: 0 Hz`: `wavelength = zoo`; `f: -170 Hz`: `wavelength = -2`;
- `maxima(vary=L)` with `L: real` lists L = -2, -1, 0 as maxima of a ray of negative or zero length.
Expected: rejection, as r34 does for strings.

**6. CONFIRMED, confusing errors.**
- t05: `lo=0[m]` for a wavelength gives "maxima(): bad arguments (Cannot convert complex to float)". The singularity check only looks strictly inside (lo, hi).
- t24: `beat_frequency(S1, S2)` on sources says "frequency(): first argument must be a Harmonic/GivenWave".
- t03: a point coordinate named `x` gives "name 'x' is reserved", with no hint to rename.
- t10b: `resultant_amplitude(...) == 2` with an unknown wall distance is refused (acceptable, but the message does not suggest stating a path difference).

**7. CONFIRMED, low: the same ray listed twice counts twice (t12).**
`relative_intensity(n1, n1) = 4`. Expected an error or 1.

**8. CONFIRMED, low: a direct ray crosses a reflector unchecked (t16).**
Source and point on opposite sides of `wall`, no `via`: `length = 2`, no warning. Defensible (a reflector only acts through `via`), but FORMAT.md should say so.

**9. SUSPECTED, doc overstatements.**
- `maxima`/`minima` are "in phase / opposite" conditions for exactly two rays. With spreading and a varied position, or a third ray, intensity extrema lie elsewhere. FORMAT.md says "in phase", but "Adjacent maxima" invites the stronger reading.
- "units of amplitude^2" is only proportional to intensity if A is a pressure amplitude in one medium. Displacement amplitudes at different frequencies (I ~ f^2 s^2) or sources in different gases (I ~ p^2/(rho v)) give wrong ratios silently. The code comment allows "pressure or relative amplitude".
- Endpoint inclusion ([lo, hi] closed) and the sign of `phase_difference(r1, r2)` (r1 minus r2, longer r1 negative) are not stated in FORMAT.md.
- Mutual coherence of all non-random sources is assumed by default; the scene never has to say so.

## Verified correct (hand or independent numeric check)

- Rigid = 0 and open = pi for pressure; examples cnt_005 (120) and cnt_008 (4 m); t17 open wall moves maxima to 8/(2n-1); t23 explore rigid/open gives 4cos^2 and 4sin^2 of sqrt(13)*pi.
- Image geometry: 3D tilted unnormalised normal (t08, length sqrt(33), amplitude 1/sqrt(33), phase pi*(7 - 2*sqrt(33))); 2D tilted (t17, 2*sqrt(29)); float coordinates (t25); normal sign irrelevant; same-side and 2D/3D mismatch rejected.
- Spreading: spherical 1/s over the full image path, cylindrical 1/sqrt(s) (t30).
- Non-monotonic phase difference: 25 maxima and 26 minima, turning point counted once (t03b); two-source sweep 5 and 6 (t18).
- Vary frequency (t09), wavelength (t05b), tube length (t27), endpoints included, `lo > hi` rejected, more than 5000 rejected.
- Unknown in geometry solved from a path difference (t10, d = 4); unknown amplitude (t20, a = 4); unknown phase (t21, pi/2); `maxima` inside `given` (t28); solved unknown feeding `maxima` (t19).
- Random sources: self-interference of one random source, independence of two (t12); r43, r44.
- Three phasors cancel (t14); two media with one frequency (t29); `wrap` at +/-pi and 7*pi/2 (t04); equal frequencies written seven different ways group correctly (t02).
- Dimension checks on sums with ray observables (t16); view and explore export (t22, t23).
