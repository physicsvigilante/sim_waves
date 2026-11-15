# Findings from writing 17 problems in format v0

## What the format needed (and why)

1. **Arbitrary given formulas.** Of 33 problems, 13 hand over y(x,t). The engine must
   analyse a formula instead of only building sinusoids:
   - speed by testing y_t + c*y_x = 0 (works for pulses; `02_cnt_005` needs the sign: -4 m/s)
   - offset plus sinusoid for cos^2 (`08`)
2. **Arbitrary profiles.** `14` (slope 53 deg) only knows a local slope. `F(x - c*t)` with an
   undefined function F expresses this exactly, with no invented shape.
3. **Constraints instead of parameters.** Figure facts and conditions become `given`
   (`05`, `10`, `16`, `17`). Phases are solved for, not hand-derived by the LLM, which
   removes the commonest sign error.
4. **Multiple solutions must be explicit.** `10` (two particles 1 cm apart) has
   infinitely many wavelengths, and even two directions, before an assumption is added.
   The book silently picks one. The engine rejects until the LLM adds
   `wavelength > 2 cm` and writes why in `assume`.
5. **Tension as a composable source.** Three ways appeared: a number, hanging weight
   (varies along the string), and thermal contraction. Each is physics, not an exam
   feature.
6. **Non-uniform media** (`12`). These need observables taken at a position and a pulse
   `front(t)`. The engine should state its approximation: a slowly varying medium with
   no reflection.
7. **Boundaries matter for travelling waves too.** "Extracted without reflection" is an
   absorbing end (`15`).
8. **Units inside expressions** (`10[cm]`) are needed because figures mix mm, cm and
   degrees.

## What the engine caught

- **`16` (22/03/cnt_007) is physically impossible, not just keyed wrong.** With
  A = 4 mm and lambda = 4 cm, the steepest slope on the string is A*k = 0.63 (32 deg),
  so no point can have a 60 deg tangent. The drawn angle only works in the figure's
  unequal axis scales. The engine should reject the scene rather than produce 1.6 mJ.
- **`10`:** the unit slip (24 cm/s keyed as m/s) shows up as soon as the engine works in SI.

## Kept out of the engine, as agreed

Option checking, matrix codes, "x can be", and 'compare string 1 with 2'. These use
plain `observe` expressions plus `equivalent()`.

## Open decisions

1. **YAML or JSON** for the scene? The drafts use YAML: fewer tokens, comments allowed,
   and it maps 1:1 to JSON.
2. **Phase convention:** sin(wt - kx + phase). Most of the book uses it, but some
   problems use sin(kx - wt). The engine compares waves with `equivalent()`, so the
   convention is only for `phase` values.
3. **`dir` vs signed `velocity`:** RESOLVED. Only `dir` exists now. An unknown
   direction is declared as `unknowns: {d: direction}` and solved by trying both
   (signed velocity broke the phase convention, as the review showed).
4. **Not yet exercised:** 22/01/asc_006 (which functions are travelling waves). This
   needs an `is_travelling(w)` observable or a check that `velocity()` fails cleanly.

## Independent review (Fable 5.2, medium effort)

- **What it confirmed:** six ways the solver could return a wrong "unique" answer, plus
  denial-of-service inputs and silent defaults. All are fixed and covered by
  `engine/tests/regression` (21 scenes).
- **Main changes:**
  - Angles are now solved on the unit circle with full branch enumeration.
  - Undecidable cross-checks become solver facts.
  - `given` and `observe` are dimension-checked.
  - Units are required for `given` waves.
  - Size and time limits are in place.

## Review 3 (Fable 5.2, medium): folder 23 milestone

The full report is in `eval/review3/REPORT.md` and the reviewer's scenes are beside it.
Before the fixes there were six ways to get a wrong result with no error.

| # | Finding | Fix | Test |
|---|---|---|---|
| 1 | A harmonic given as a symbol skipped the whole-number and odd-only checks (an even mode was "solved" in a closed pipe) | Symbolic harmonics must use integer-kind symbols; the mode rules filter solver branches, are re-checked in `_verify`, and are enforced on observe results | r29, r30 |
| 2 | `resonances()` stopped early when the varied value falls with n (tension, temperature) | Solve once in the mode number; each branch stops only when it moves away from [lo, hi] | r31 |
| 3 | `resonances()` returned 0 for a free symbol or an unrelated `vary` | Undetermined error / "does not depend on" error | r32 |
| 4 | Zero or negative lengths and end corrections were accepted | Rejected | r34 |
| 5 | No dimension checks on beat_frequency, min/max, resonances | Added (omega-vs-f is documented: both are 1/s) | r35 |
| 6 | The viewer drew waves outside their string | Engine windows are placed in the medium and every window is clipped | eval/review3/d04 |
| 7 | `phase(x=)`, `wavelength(at=)`, `k(at=)` skipped extent checks | Checked; a symbolic x is documented as unchecked | r36 |
| 8 | Inverted or duplicate junction geometry; left = right | Rejected; `at` must be numeric | reviewer a05, a06, e02 |
| 9 | A fully cancelled sum raised an error | Amplitude 0; phase etc. stay undefined | r33 |
| 10 | Sums across different media | Rejected | r37 |
| 11 | Gas inputs that complete no route were silently ignored; R could not be set | Error; optional `gas_constant` | r38 |
| 12–17 | List arithmetic traceback; AccumBounds printed as a limit; a given wave on a junctioned string gave a confusing error; resonances slow at high f; one observable error hid the others | Clean errors; one symbolic solve; every observable is evaluated and all errors are reported, with the valid results printed | reviewer scenes |

Still open (deferred, not hidden):
- pressure-versus-displacement conventions for pipes (no pressure observables yet);
- multiple reflections;
- rods.

## Run 3 (held-out folder 23) and the fixes that followed

The full results are in `eval/run3/SCORECARD.md` and `GRADES.md`. The run is frozen; the
engine as it was is copied in `eval/run3/engine_before_fixes/`.

**Results:**
- 30/36 match the key.
- Two keys are book errors where the author was right.
- 04/bmc_006 has a misprinted option, and 01/asc_005 differs by a convention on the
  phase change at reflection.

**Fixes made after the run, with tests:**
- **`abs()` / `beat_frequency()` with unknowns in `given`** used to crash. They are now
  solved by sign cases, each one checked (r39). The author's own v1 scene for 03/asc_004
  now gives 205 Hz.
- **Unexpected errors** now become a clean "engine internal error" message instead of a
  traceback.
- **`resonances()` in observe** sees solved unknowns, and `speed(resonator)` exists (r40).
- **Expression values in scene fields** (`"9[kg]*9.8[m/s^2]"`) are accepted, with a
  dimension check.
- **YAML errors** caused by unquoted unit brackets get a hint.
- **Doc additions:** quoting, abs sign cases, counting modes below a limit.

**The next physics, by number of problems it blocked:**
- point sources, path lengths and reflectors with a phase change (6);
- standing-wave pattern observables (4);
- beat envelope, standing-wave energy, pulse reflection.

**Authoring honesty:** about 8 answers claimed "full" engine fit with one hand step. The
answer file could ask the author to list every hand step explicitly.

## Point sources, reflectors and rays (milestone 4)

New in `engine/simwaves/rays.py`:
- sources (position, f, A, phase or random, spreading stated);
- plane reflectors (image source; `boundary: rigid | open`, or a stated `phase_change`);
- points and rays (direct, via one reflector, or of stated length);
- observables: path and phase difference, resultant amplitude, relative intensity
  (coherent rays add as phasors, incoherent as intensities), and maxima/minima lists
  over a varied symbol.

`maxima`/`minima` count the whole numbers the phase difference crosses on [lo, hi], piece
by piece between turning points. A singular phase difference in range is an error. This
avoids open-ended scans.

**Convention, decided by physics:** rays add as pressure. A rigid wall gives no pressure
phase change. This settles two corpus disputes:
- **23/01/cnt_008 (design set):** key 4 m. The corpus note calls it doubtful (it applies a
  displacement pi shift); with pressure the key is right. Example `23_01_cnt_008.yaml`
  gives 4 m.
- **23/01/asc_005 (run 3):** the key (a) assumes a lambda/2 shift at the ceiling. With
  pressure the maxima are at 10/n m, option (b), which is what the run 3 author answered.
  - This is recorded here, not in the frozen run 3 grades.
  - The book's convention can be reproduced with `phase_change: pi`, tagged as a
    convention (r42).

Tests: r41 to r48, and examples `23_01_cnt_005` and `23_01_cnt_008`.

## Review 4 (Fable 5.2, medium): sources and rays

The full report is in `eval/review4/REPORT.md`. Fixes, each tested:

| # | Finding | Fix | Test |
|---|---|---|---|
| 1 | Coherence was grouped on the unsolved frequency expression, so `f0` (solved to 170) and `170 Hz` added as intensities (I = 2, not 4) | Frequencies are compared after substituting the solution; undecidable ones give an "undetermined" error | r49, r52 |
| 2 | Symbolic `relative_intensity` hung (trig expansion of cos(240*pi/lam)) | The sum is written as sum A^2 + 2 sum A_i A_j cos(dphi), with no expansion | r50 |
| 3 | Amplitudes in Pa and mm were added | The units of A must agree across rays | r51 |
| 4 | No dimension check on maxima/minima lo/hi | Checked against each other and against the varied symbol where its dimension is known | reviewer t05b |
| 5 | Zero or negative frequencies and stated lengths accepted; maxima listed values giving negative path lengths | Rejected or dropped | reviewer t06, t13 |
| 6 | Endpoint singularity crash; `beat_frequency` on sources; the reserved `x` name | Clear errors; `beat_frequency` takes sources | reviewer t05, t24, t03 |
| 7 | A ray listed twice counted twice | Error | reviewer t12 |
| 8–9 | Doc gaps | Documented: reflectors act only via `via`; maxima are a two-ray phase test; [lo, hi] is closed; the sign of the phase difference; coherence default; relative intensity is pressure-only | — |

**Still open:** with bare-number lo/hi and a varied symbol of unknown dimension, the
check cannot run. The doc asks for units.

## Standing-wave patterns and beats (milestone 5), and review 5

New in `engine/simwaves/modes.py`:
- `nodes`, `antinodes`, `pressure_nodes`, `pressure_antinodes`;
- `mode_shape`;
- `harmonics(node_at | no_node_at | antinode_at)`, for touch and pluck;
- `envelope`, plus `min_over` and sqrt support in `max_over`/`min_over`.

The test harness now compares list results.

Review 5 (Fable 5.2, medium; report in `eval/review5/REPORT.md`) found:

1. `max_over`/`min_over` of sqrt returned imaginary numbers. The radicand must now
   provably stay non-negative (r57).
2. An unknown point in `mode_shape` had no range. It is now kept on the resonator by
   implicit inequality facts (r55). An empty interval now means "no branch" instead of a
   crash.
3. nodes/antinodes/harmonics did not see solved unknowns. They do now (r56).
4. `list[1]` was silently read as a unit; it is refused now.
5. Two doc caveats added: the envelope's maximum is only attained for close frequencies,
   and the envelope period is not a beat period.
6. End correction on a closed-closed pipe is refused. The doc now notes the antinode count
   with an end correction.

Still open (low): an unknown integer harmonic in mode_shape counts negative n as
branches before the mode filter, so it may report "infinitely many".

## Run 4 (held-out folder 11 and 24/01) and the fixes that followed

See `eval/run4/SCORECARD.md`.
- **Key matches:** 69/77, with 6 more book-disputed.
- **Engine-verified:** about 53/77. Coverage, not fidelity, is the limit: 0
  misrepresented.
- **Two silent wrong answers** came from non-uniform strings, where a position symbol
  inside mu was treated as a constant. Strings with a `coordinate` must now name its
  `variable`. mu may depend on it, the hanging tension integrates mu, and an undeclared
  position symbol shared by mu and `at=` is refused.
- **Also fixed:** a minima false negative, an ambiguity message that hid a solution
  family, and a print traceback.
- **Next physics by demand:** acoustic pressure/intensity/bulk modulus (9), liquid and
  solid media including rods (7), decibels (4), gas mixtures and rms speed (4),
  springs/statics (4).

## Corrections after diagnostic 1

Each correction has a test:

- **Pulse on a junctioned string:** it ignored the junction (silent wrong). Now refused
  with the reason (r62).
- **Run behaviour:** one observable that cannot be computed no longer stops the run (charter
  section 7). It is reported as NOT AVAILABLE; the others stand; the exit status is non-zero
  (r64). Fact errors still stop the run.
- **Viewer:** list-valued and unavailable observables export as text instead of crashing
  (test_export 10).
- **Value at a point:** `at(expr, name=value)` replaces the `illustrate` workaround the
  teacher needed (r63).

The diagnostic's frozen outcomes are unchanged in `eval/diag1/`.

## Milestone 6: acoustics, and review 6

Built to `eval/m6_acoustics/PLAN.md`:
- fluid and rod media, and gas density;
- sound-wave amplitudes linked as displacement, pressure and intensity;
- sound level and its inverse;
- sources given by power (spherical or hemispherical), with physical intensity of rays;
- rod resonators.

The four motivating problems reproduce the book (examples `11_03_001`, `24_01_cnt_004`,
`11_05_004a`, `11_03_003`, plus `11_03_013`).

**Unplanned change:** unknowns inside log/exp are now solved (a power from a level). This
was a solver change, not physics.

Review 6 (Fable 5.2, medium; `eval/review6/REPORT.md`):

| # | Finding | Fix | Test |
|---|---|---|---|
| 1 | `amplitude(ray)` of a powered source returned a pressure typed as a length (silent wrong in a fact) | Refused, with a pointer to `pressure_amplitude` / `displacement_amplitude` | r72 |
| 2 | The log change lost roots: sympy's `solve` drops log(u) = 0 | One unknown at a time via solveset or polynomial roots, each re-checked; several unknowns refused | r73 |
| 3 | A level difference with an unknown distance timed out | Log-linear rewrite to an algebraic equation | r74 |
| 4 | Rod: Y ignored without density; medium and resonator lengths not cross-checked | Refused; cross-checked | r75 |
| 5 | A tube path from a powered source spread as a sphere | Refused | r76 |
| 6 | Messages: `A: "2[Pa]"` not seen as a pressure; "gas medium" when fluids work | Fixed | — |

**Still open:** `molar_mass: 29 g` is accepted, because mol is dimensionless in the unit
table.

**Reserved transfer (m6):** 3 of 3 reserved problems matched in every part, with no
production change (`eval/m6_acoustics/RESULT.md`). Post-run corrections from author
friction:
- a `compressibility` input;
- units mW, kW, kHz, kPa;
- `pressure_amplitude` of several rays;
- reverting the medium/resonator length cross-check added after review 6.
