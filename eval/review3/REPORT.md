# Review 3: superposition, junctions, gas media, resonators

Scenes are in `eval/review3/`. All findings CONFIRMED (run) unless marked SUSPECTED.
Regression (29) and negative (12) suites pass.

## Silent wrong answers

**1. Odd-harmonics rule skipped when the harmonic is not a literal** (`_check` only tests numbers).
- `a01`: closed-open pipe 0.5 m, v = 340 m/s, `unknowns: {n: integer}`,
  `frequency(p, harmonic=n) == 340[Hz]`. Observed `solved n = 2`, `lam = 1`.
  Expected: inconsistent (modes are 170, 510 Hz, ...).
- `d03`: unknown L and n, facts at harmonics n and n+1 (340, 510 Hz). Observed `n = 2,
  L = 1/2`. Expected: rejection; mode 2 does not exist.
- `b12`: `symbols: {n: positive}` gives `fn = 85*n`, no integer/odd condition.

Fix: a non-literal harmonic adds an implicit fact (integer, >= 1, odd if mixed) for the re-check.

**2. `resonances()` stops early when the varied quantity falls as n rises** (break rules
assume growth with n).
- `a02`: string 1 m, 0.01 kg/m, 100 Hz, vary tension in [10, 50] N. Observed `()`, count 0.
  Expected 4 values: 400/n^2 = 44.4, 25, 16, 11.1 N.
- `b10`: closed pipe 1 m, 255 Hz, vary temperature in [10, 200] K. Observed `()`.
  Expected 6 values (2592/n^2 K, n = 5..15 odd).

**3. `resonances()`/`count()` return 0 where an error is due.**
- `a03`: gas speed is a free symbol; solutions containing it are filtered. Observed `n = 0`.
  Expected: undetermined.
- `b09`: `vary=q`, unused by the resonator; pipe resonates at 170 Hz for every q.
  Observed `n = 0`. Expected: error.

**4. Non-physical resonator sizes accepted.** `b08`: `length: -1 m` gives `f = -170`;
`end_correction: -6 cm` on a 10 cm open pipe gives `-8500`; `length: 0 m` gives `zoo`.
Expected: "(effective) length must be positive".

**5. No dimension checks on new observables.** `a04`: `beat_frequency(3[m], 2[s])` gives
`1`; `min(2[m], 3[s])` gives `2`. `d05`: `resonances(col, f=660[m], vary=L, lo=0[s],
hi=1.5[kg])` returns the correct call's list. `c02`: `beat_frequency(omega(a), omega(b))`
gives `8*pi` (dimension cannot catch this; worth a doc line).

**6. Viewer draws waves outside their medium.** `d04`: junction at 0, incident `w` on
string `a` (x <= 0). Panels for `w` and `sum: [w, w_reflected]` are sampled on x = 0..6 m,
entirely inside string `b`, where `y(w, ...)` is itself an error. Expected: window clipped
to the extent, or rejection.

## Leaky conventions

**7. Extent check gaps.** `a07`: `phase(w, x=1[m], t=0)` beyond the junction returns
`-2*pi/3`; `wavelength(w, at=1[m])` returns 3; `y(w, x=x, t=0)` with free x is unchecked.

**8. Junction geometry not validated.** `a06`: `J` at 0 (left a, right b) plus `wall` at
-1 m (left b) gives b the extent (0, -1); `amplitude(w_transmitted)` still answers.
`e02`: `left: a, right: a` accepted.

**9. Complete cancellation is an error, not zero.** `b01`: equal waves, phases 0 and pi;
`amplitude(tot)` gives `wave 'tot' does not oscillate`. Expected `0`, a standard answer.

**10. Sum across unrelated media.** `b06`: waves on two separate strings give
`amp = 7/100`. Expected: error.

**11. Gas: unused inputs dropped silently.** `c04`: `{v, gamma, pressure}` and
`{gamma, pressure, density, temperature: 5000 K}` run with extras ignored.
SUSPECTED gap: R is fixed at 8.314462; a book's R = 8.3 or 25/3 cannot be recorded as a convention.

## Confusing errors, crashes

12. `d06`: `resonances(...) + 1[m]` ends in a raw traceback
    (`TypeError: unsupported operand ... 'Tuple' and 'One'`).
13. `a05`: junction `at: L` (symbol), then `y(st, x=L, t=t)` gives
    `y(): bad arguments (Cannot convert expression to float)`. Support it or say
    "junction position must be numeric".
14. `b12`: `limit(sin(1/dl), dl, 0)` prints `AccumBounds(-1, 1)` as a result.
15. `e03`: a `given:` wave on a junctioned string yields `unknown name 'w_reflected'`;
    should say only harmonic waves reflect.
16. `b13`: `resonances` at 1 MHz takes 30 s before the 5000-mode error (one solve per mode).
17. One failing observable hides all others (`b06` with `power(tot)` suppressed a valid `amp`).

## Doc mismatches

- "Media" still says `gas and rod: not yet` and `fixed/free ends (reflection): not yet`.
- Limits: "`at=` positions are not yet checked" now matters (item 7).
- Symbolic `harmonic=` is undocumented (item 1).

## Checked and correct

- r = (Z1-Z2)/(Z1+Z2), t = 2Z1/(Z1+Z2); phase jump pi on a denser string, none on a
  lighter; fixed end node (`c08`); free end antinode with zero slope (`a08`).
- Incidence from the right (`a08`): displacement and slope continuity proved, tr = 4/3,
  transmitted velocity and wavelength right; power balance 0 (`a07`).
- Unknown direction, or undetermined amplitude sign, at a junction: clean errors.
- Phasors: 3 cm and 4 cm at pi/2 give 5 cm, phase atan(4/3); nested sums; standing-wave
  envelope sqrt(A1^2 + A2^2 + 2 A1 A2 cos 2kx); standing and two-frequency sums refuse a
  single amplitude or frequency.
- Pipes: end correction once per open end; literal even harmonic rejected; overtone k maps
  to 2k+1 (mixed) or k+1; overtone 0, harmonic 0 and 2.0 rejected; string and pipe end
  names not interchangeable.
- Two-resonance end-correction problem (`b11`): v = 350 m/s, e = 0.5 cm.
- Resonances varying length (with end correction) or frequency: correct.
- `beat_frequency` is |f1 - f2|, order-independent, mixes waves and numbers.
- Gas speed from gamma P/rho and gamma R T/M (degC converted); negative absolute
  temperature rejected.
