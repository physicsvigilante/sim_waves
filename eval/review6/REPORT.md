# Review 6: acoustics milestone (m6)

Scenes: `eval/review6/*.yaml`. Regression suite: 72 PASS.

## Findings, by severity

### 1. HIGH, CONFIRMED: `amplitude(ray)` of a powered source is a pressure typed as a length (silent wrong answer)
- Scene `c13.yaml`: source `power: P` (unknown), fact `amplitude(a) == 3e-6[m]` at 2 m, 600 Hz, air 340 m/s, 1.2 kg/m^3.
- Observed: accepted, `P = 5.54e-13 W`. `amplitude(r1) + 1[m]` is accepted, `+ 1[Pa]` rejected (`c01.yaml`).
- Expected: P = 1.31 W (p0 = rho v omega s0 = 4.61 Pa, I = p0^2/(2 rho v) = 0.0261 W/m^2, times 16 pi), which `displacement_amplitude(a)` gives (`c14.yaml`).
- Why: `OBS_DIMS["amplitude"] = LENGTH`, but for rays it returns `amplitude_at()`, now always in Pa for powered sources.

### 2. HIGH, CONFIRMED: the `_in_trig` change loses roots (solver.py docstring "they lose no roots" is false)
- `L2.yaml`: `log(u)**3 == log(u)`, `u > 0.5`, u positive. Observed: unique `u = e`. Expected: ambiguous {1, e}.
- `L3.yaml`: same with `u < 2`. Observed: unique `u = 1/e`. Expected: ambiguous {1/e, 1}.
- `d01.yaml`: `atan(u)**2 == atan(u)`, `u < 1`. Observed: InconsistentError. Expected: u = 0.
- Why: `sp.solve([eq], [u], dict=True)` (the list form `_core_solve` uses) drops the root f(u) = 0 when the equation is a polynomial in log(u) or atan(u) with zero constant term; the single-equation form returns it. Contrived for JEE, but the one-answer contract is broken. LambertW cases (`u - log(u) == 2`, `2**u == u**2`) do return both branches.

### 3. MEDIUM, CONFIRMED: a level difference with an unknown distance times out
- `L1.yaml`: one source, points at d and d + 10 m, `sound_level(intensity(a)) - sound_level(intensity(b)) == 6`.
- Observed: "evaluation exceeded 120 s" (hang inside `sp.solve`, solver.py line 198). Expected: d = 10/(10^0.3 - 1) = 10.05 m.
- A common JEE form; an error, not a wrong answer. The ratio form (`d07.yaml`) solves, k = 10.

### 4. LOW, CONFIRMED: rod inputs outside any route are accepted silently
- `b01.yaml`: `{type: rod, v: 5000 m/s, Y: 1e11 Pa}` runs; Y is ignored (FORMAT.md says leftover inputs are an error).
- `b03.yaml`: medium `length: 1 m` (no mass) with a resonator `length: 2 m`: no error, no cross-check.

### 5. LOW, CONFIRMED: a ray of stated `length` from a powered source gets I = P/(4 pi L^2) (`c03.yaml`, `tube`)
- A tube path does not spread.

### 6. LOW, CONFIRMED: confusing messages
- `A: "2[Pa]"` is not recognised as a pressure (`c03.yaml`, `i5`).
- A source on a rod: "point sources need a gas medium", though fluids work (`b14.yaml`).
- `molar_mass: 29 g` is accepted, since mol is dimensionless (`e05.yaml`).

## Verified correct (hand values)
- **Wave links:** p0 = rho v omega s0 and I = p0^2/(2 rho v) on gas, fluid and rod, from any one of A, pressure_amplitude, intensity (`a01`-`a04`, `a18`); rod stress amplitude equals Y times the strain amplitude (`a02`).
- **Media:** gas density P M/(R T), with the exact and a stated R and degC (`a04`, `a19`); fluid sqrt(B/rho) = 1500 m/s; rod sqrt(Y/rho) = 5000 m/s. Over-specified conflicts are rejected (`a05`, `b02`, `b12`, `b16`); gas leftovers are rejected (`a07`, `a08`).
- **No invented values:** no density gives undetermined (`a09`, `b13`); two amplitudes, zero intensity, intensity on a string are refused.
- **Dimensions:** `sound_level`, `intensity_of_level`, power, intensity + pressure are checked (`a11`, `c05`).
- **Powered sources (`c01`, `c02`, `c04`):** hemispherical = 2 x spherical; coherent in phase with P and 4P gives 9 I1; antiphase gives 0, and its level is an error; incoherent or different frequencies give 2 I1; spherical + hemispherical coherent gives 3 + 2 sqrt 2; rigid and open reflections give 9 and 1; power 0, cylindrical, A_at are refused.
- **Rods:** clamped-free odd only, f1 = v/4L, nodes and antinodes; free-free and clamped-clamped v/2L; pipe on a fluid works; pipe on a rod, rod on a gas, string on a rod are refused.
- **Solver:** power from a level, distance from a level, amplitude, frequency or density from a fact, n = 10 for +10 dB; out-of-range atan/asin/exp are inconsistent.
- **Other:** emitters unchanged; explore on power, density and Y export correctly (`v01`-`v04`).
