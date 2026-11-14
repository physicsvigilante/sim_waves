# Run 4 grades (independent grader)

Graded from the problem file, the final scene named in each answer file, a re-run of every final scene,
and the corpus record (key + transcriber verification). Dimension D is not graded here.

Conventions used
- **B**: `verified-proved` = the answer's physics result is an exact engine result from the scene;
  `verified-sampled` = engine only checked a hand-derived claim at sample points; `unverified` = a decisive
  step (or the whole answer) was done by hand; `wrong` = the stated answer is incorrect.
  The `run` command prints no basis label, so an `equivalent()` printed as True could not be told apart
  as proved or sampled from the output (affects 11/01/004, 11/01/012, 11/04/005, 11/05/001, 11/05/003, 24/01/bmc_004).
- **E**: the answer file against the key, all parts, 2 % numeric tolerance; where the key itself is rounded
  the corpus verification value is used. `differs-book-disputed` only where the corpus record documents the dispute.
- An asterisk in the id column marks the 15 partly exposed ids.

## Table

| id | A | B | C | E | note |
|---|---|---|---|---|---|
| 11/01/001* | faithful | verified-proved | full | differs-book-disputed | lam 0.08 m, f 3750 Hz match; answer is the sign-corrected form y=0.06 sin(kx-wt) (corpus: key sign contradicts figure) |
| 11/01/002* | faithful | wrong | full | differs | answers 75 m/s 'if lam>0.1 m'; that bound still admits lam=0.3 m (key 150 m/s). Author misled by engine's incomplete ambiguity list; final scene ends AmbiguousError; 4 attempt files |
| 11/01/003* | faithful | verified-proved | partial | matches | velocity = v from engine; piecewise support (|x-vt|<=a) by hand; misprint reading declared |
| 11/01/004 | faithful | verified-proved | full | matches | wave-equation check equivalent()=True, v=w/k |
| 11/01/005 | faithful | verified-proved | full | matches | dx=0.12 m; smallest-separation assumption tagged |
| 11/01/006 | faithful | unverified | partial | matches | final scene v3 exits with error (max_over not a sinusoid); boundedness criterion and a,b,c verdicts by hand; only d's value at 1000 m from engine |
| 11/01/007 | faithful | verified-proved | full | matches | v=3 cm/s, expressions at t=0,1,2; peak 2 cm and centres read by eye; view not rendered |
| 11/01/008 | minor-deviation | unverified | partial | matches | omega=sqrt(2k/m) by hand and typed as a wave parameter; springs/block absent from scene |
| 11/01/009 | faithful | verified-proved | full | matches | all four values from engine |
| 11/01/010 | faithful | verified-proved | full | matches | crest line x=-2t found by hand (amplitude() refuses pulses) but hand_steps empty |
| 11/01/011 | faithful | verified-proved | full | matches |  |
| 11/01/012* | faithful | verified-proved | full | differs-book-disputed | engine proves cancellation on whole line t=0.75 s and at x=1 m for all t (corpus: key incomplete); candidates found by hand; fit 'full' with non-empty hand_steps |
| 11/02/001 | faithful | unverified | partial | matches | answer by hand (correct). ENGINE WRONG: T=g*mu0*s^2, front=g t^2/4 |
| 11/02/002 | faithful | unverified | full | matches | speed(s) from engine, integral by hand. ENGINE WRONG: front()=10t/sqrt(alpha s+mu0) |
| 11/02/003 | faithful | verified-proved | partial | matches | 79.2/62.6 vs 80/63.24 (g=9.8 vs book 10, 1%); load statics typed by hand but hand_steps empty |
| 11/02/004* | faithful | unverified | full | not-produced | no book key; PE density assembled by hand from engine slope/speed; agrees with transcriber's reference derivation |
| 11/02/005 | faithful | verified-proved | full | matches | 0.06*sqrt(3) m |
| 11/02/006 | faithful | unverified | partial | matches | T=64 N from engine; extension (Hooke) by hand; undeclared placeholder A=1 mm, f=100 Hz |
| 11/02/007 | faithful | unverified | partial | matches | v from engine; t=L/v by hand; tension=mg typed |
| 11/02/008 | faithful | verified-proved | full | matches | power ratio 1/8 |
| 11/02/009 | faithful | verified-proved | full | matches |  |
| 11/02/010 | faithful | verified-proved | full | matches |  |
| 11/02/011 | faithful | verified-proved | partial | matches | pulse modelled as harmonic wave (declared); t typed as L/v in observe; inversion of reflected pulse not stated in answer |
| 11/02/012 | faithful | verified-proved | full | matches | ratios symbolic; ordering m2>m1 applied by hand |
| 11/02/013 | faithful | verified-proved | partial | matches | T=kx and t=L/v typed into the scene (disclosed) |
| 11/03/001 | faithful | unverified | partial | matches | only I from engine; p0 and s0 by hand; f, v, rho not in scene |
| 11/03/002 | faithful | unverified | partial | matches | v_rms and ratio by hand; gamma=7/5 assumed (as book) |
| 11/03/003 | minor-deviation | verified-proved | partial | matches | hemisphere faked by doubling emitter power; dB formula typed |
| 11/03/004 | minor-deviation | verified-proved | partial | matches | water disguised as gas (gamma=1, pressure=B), declared hack |
| 11/03/005 | faithful | verified-proved | full | matches | -2.87 % vs key '3 %' (key rounded; corpus confirms 2.87) |
| 11/03/006 | minor-deviation | unverified | partial | matches | I=1e-6 inverted by hand and typed as a plane emitter; P and E by hand |
| 11/03/007 | faithful | verified-proved | full | matches | 23.32 K |
| 11/03/008 | minor-deviation | verified-proved | partial | matches | solid disguised as gas, declared hack |
| 11/03/009 | faithful | unverified | unsupported | matches | engine only echoes I; p0 by hand (author says coverage partial) |
| 11/03/010 | minor-deviation | unverified | partial | matches | B hack + disconnected emitter; I, p0, s0 all by hand; engine gives v, k |
| 11/03/011* | faithful | verified-proved | partial | matches | 590.1 vs key 591 (0.15 %; corpus notes key slip); mixture molar mass typed |
| 11/03/012 | faithful | unverified | unsupported | matches | placeholder scene; all by hand |
| 11/03/013 | faithful | unverified | unsupported | matches | engine echoes I; both amplitudes by hand |
| 11/04/001 | faithful | verified-proved | full | matches | amplitude and phi from engine; only +phi reported (key +-), sign note given |
| 11/04/002 | minor-deviation | verified-proved | partial | matches | invented sound sources/paths to build in-phase and antiphase cases (declared) |
| 11/04/003 | faithful | verified-proved | full | matches | 5A/6, -atan(3/4) |
| 11/04/004 | faithful | verified-proved | full | matches | 1440 Hz; family bound chosen by hand |
| 11/04/005 | faithful | verified-proved | full | matches | cos-phase guessed, proved by equivalent() |
| 11/04/006* | faithful | verified-proved | full | differs-book-disputed | antiphase matches; I=8.2e-5 W/m^2 vs key 0.6 mW power difference (corpus: key wrong quantity); amplitude ~ sqrt(power) typed by hand |
| 11/04/007 | faithful | verified-proved | full | matches | n*188.3 Hz, 106 audible |
| 11/04/008 | faithful | verified-proved | full | matches | 1003n / 501(2n-1) vs key 1000n / 500(2n-1) (0.3 %); family generalised by hand from min() |
| 11/04/009* | faithful | verified-proved | full | matches | 17.52 cm vs key 17.54 (0.1 %) |
| 11/04/010 | faithful | unverified | partial | matches | (a) 3 m from engine; (b) 0.6 m by hand because minima() wrongly reports no minimum |
| 11/04/011 | faithful | verified-sampled | full | matches | ratio 4:2:0 checked at two invented R values only (R-independence sampled); f from invented v by hand, hand_steps empty |
| 11/04/012 | faithful | verified-sampled | full | matches | hyperbola derived by hand, engine checks 3 points; x^2/15.9-y^2/9.1=1 vs key (lam=16) x^2/16-y^2/9=1 |
| 11/05/001 | faithful | verified-proved | full | matches | 10.13 vs 10.12 cm/s |
| 11/05/002 | faithful | verified-proved | full | matches | n=8, 144 cm, 17.36 Hz |
| 11/05/003* | faithful | verified-proved | full | differs-book-disputed | (a),(b),(d) match; (c) 76.5 vs key 78.5 cm/s (corpus: no consistent evaluation gives 78.5) |
| 11/05/004* | faithful | unverified | partial | matches | (a) rod longitudinal by hand; (b) thermal tension 48.4 N, 11 Hz from engine |
| 11/05/005 | faithful | verified-proved | full | matches | 72/24/18 cm |
| 11/05/006 | faithful | verified-proved | full | matches | 15/7 m |
| 11/05/007 | minor-deviation | verified-proved | partial | matches | obstacle as junction to a denser string; antinode/node relation typed by hand; 24/25 from engine |
| 11/05/008* | faithful | unverified | unsupported | differs-book-disputed | rod rejected, all by hand; 0.364 m, 9.84 kHz, 2.83e-6 m amplitude vs key 9939 Hz, 2.57e-6 (corpus: key rounding error) |
| 11/05/009* | faithful | unverified | partial | matches | energy integral by hand; (1/2) mu A^2 w^2 lam sin^2 wt == pi k A^2 T sin^2 wt (written with mu, lam instead of the given T, k) |
| 11/05/010 | faithful | verified-proved | full | matches | 353.6 m/s |
| 11/05/011 | faithful | verified-proved | full | matches |  |
| 11/05/012 | faithful | verified-proved | full | matches |  |
| 11/05/013 | faithful | verified-proved | full | matches | engine reports both open lengths (ambiguity is in the source); both match key |
| 11/05/014 | minor-deviation | verified-proved | partial | matches | hole modelled as a second, shorter open pipe |
| 11/05/015 | faithful | verified-proved | full | matches | 367 Hz; d<3 assumption tagged |
| 11/05/016 | faithful | verified-proved | full | matches | inequality tagged 'stated' though it is an inference |
| 11/05/017* | faithful | verified-proved | full | matches | k, omega, mode shape from engine; equation assembled by hand |
| 24/01/asc_004 | faithful | verified-proved | full | matches |  |
| 24/01/asc_005 | minor-deviation | unverified | partial | matches | pressure wave entered as displacement wave with A=1 m; s0 by hand |
| 24/01/asc_006 | minor-deviation | unverified | partial | matches | invented v=340 m/s; B by hand |
| 24/01/bmc_004 | faithful | verified-proved | partial | matches | slope facts proved; dp=-B dy/dx link and options a,b by hand |
| 24/01/bmc_005 | faithful | verified-proved | partial | matches | slopes at A,B,C from engine; pressure link by hand; undeclared placeholders |
| 24/01/cnt_004 | faithful | unverified | unsupported | matches | probe rejected; all by hand |
| 24/01/cnt_005 | faithful | verified-proved | full | matches | mixture molar mass typed |
| 24/01/cnt_006 | faithful | unverified | unsupported | matches | engine used as calculator only |
| 24/01/cnt_007* | faithful | unverified | partial | differs-book-disputed | 0.278 vs key 2.8 (corpus: key factor-of-10 slip); B and dV/V by hand |
| 24/01/dmt_004* | minor-deviation | verified-proved | partial | matches | case (i) drops the pressure change; case (ii) Boyle scaling by hand; column II absent from problem file, verbal answers equal q,r,q,s |

## Counts, all 77

| Dim | Counts |
|---|---|
| A | faithful 65, minor-deviation 12, misrepresented 0 |
| B | verified-proved 51, verified-sampled 2, unverified 23, wrong 1 |
| C | full 42, partial 29, unsupported 6 |
| E | matches 69, differs-book-disputed 6, differs 1, not-produced 1 |

## Counts, 62 held-out ids (excluding the 15 partly exposed)

| Dim | Counts |
|---|---|
| A | faithful 51, minor-deviation 11, misrepresented 0 |
| B | verified-proved 42, verified-sampled 2, unverified 18, wrong 0 |
| C | full 34, partial 23, unsupported 5 |
| E | matches 62, differs-book-disputed 0, differs 0, not-produced 0 |

Automatic RESULTS.txt said 31/77; graded by hand, E is matches or book-disputed for 75 of 77. The one
`differs` is 11/01/002; the one `not-produced` is 11/02/004 (no book key).
Only 51 of 77 answers rest on the engine alone (B = verified-proved);
23 needed a decisive hand step.

## Over-claims (`engine_fit: full` with hand work)

- **11/01/012**: `engine_fit: full` with a non-empty `hand_steps` (candidate t = 3/4 s, x = 1 m found by own algebra). Direct breach of the TASK rule.
- **11/01/010**: `full`, empty `hand_steps`, but the crest line x = -2t was identified by hand (admitted in `friction`).
- **11/02/003**: `full`, empty `hand_steps`, but which load each wire carries (2mg, mg) is hand statics typed into `tension` (admitted in `friction`).
- **11/04/011**: `full`, empty `hand_steps`, but f = 17 Hz comes from an invented v = 340 m/s divided by the stated wavelength by hand, and the R-independence is only sampled at two values.
- Minor: 11/01/007 (peak height and centres read by eye, view never rendered), 11/05/010 (20 beats / 6 s typed), 11/05/016 (inference tagged `stated`).
- Under-reported hand work in `partial` files: 11/02/006 and 24/01/bmc_005 carry undeclared placeholder wave parameters.

## Rule breaches

- **11/01/002**: four attempt files (v1 to v4). v4 is empty (0 bytes), never run, disclosed by the author. Technical breach only.
- No other problem has more than three attempt files.
- **Final scene does not run cleanly**: 11/01/006 v3 (SceneError on `max_over`; the third attempt was spent and the answer's "c reaches 1e60" comes from the crashed v2), 11/05/008 and 24/01/cnt_004 (deliberate rejected probes), 11/01/002 and 11/05/013 (AmbiguousError, intended and disclosed).
- **Physics formulas typed into scenes** (against FORMAT's "the LLM never writes a physics formula"), all disclosed: L/v travel times (11/02/011, 11/02/013), k*x spring force (11/02/013), m*g loads (11/02/003, 11/02/007), 10 log10(I/I0) (11/03/003, 11/03/006, 11/03/010), (Ai+Ar)/(Ai-Ar) (11/05/007), mixture molar mass (11/03/011, 24/01/cnt_005), amplitude ~ sqrt(power) (11/04/006).
- **Medium disguises**: liquid or solid entered as a gas with gamma = 1, pressure = B (11/03/004, 11/03/008, 11/03/010). Numerically right, declared, but the scene states something the source does not.

## Suspected engine defects

Silent wrong results (most serious)
1. **Hanging string with position-dependent mu** (11/02/001, re-run confirmed). `mu: "mu0*s"`, `tension: {hanging: {load: 0 kg, g: g}}` gives `tension(wire, at=s) = g*mu0*s**2` (correct: g*mu0*s^2/2) and `speed = sqrt(g*s)` (correct sqrt(g*s/2)); v1 gives `front(p, t=t) = g*t**2/4` (correct g*t^2/8), i.e. arrival at 2*sqrt(l0/g) instead of sqrt(8*l0/g). The engine uses mu(s)*g*s instead of integrating the mass below. FORMAT says non-uniform resonators are unsupported but nothing rejects this medium.
2. **`front()` on a non-uniform string under fixed tension** (11/02/002, re-run confirmed). Returns `10*t/sqrt(alpha*s + mu0)`: local speed times t, still containing the position symbol. Not a front position; the correct front solves the integral of ds/v(s) = t.

Wrong statements raised as errors
3. **`minima()` false negative** (11/04/010 v2 and v3, re-run confirmed). `minima(bounce, direct, vary=W, lo=2[m], hi=6[m])` says "no value of W gives a minimum", while `maxima()` on the same rays returns (sqrt(10), 3*sqrt(2), 2*sqrt(7)). Minima exist at W = sqrt(27)/2 = 2.598, sqrt(55)/2, sqrt(91)/2; the engine itself gives `relative_intensity` = 3.7e-18 and phase difference -pi at W = 2.598 (grader test). Cause: in `rays.py::_extrema`, `sp.solve(Eq(D, N), vary)` returns no branch for the half-integer offset with a square-root path, and the code raises instead of falling back.
4. **Incomplete "infinitely many situations" list** (11/01/002 v3). The message lists only k = 40*pi/3, 100*pi/3, 160*pi/3, 220*pi/3 with ph = pi and omits the whole ph = 0 family, including the smallest k = 20*pi/3 (the book's 150 m/s). Adding `k < 30` makes the engine solve k = 20*pi/3, ph = 0, v = 150; adding `k < 50` gives "2 situations: k=40*pi/3, ph=pi; k=20*pi/3, ph=0" (grader tests). So the solver knows the branch but the report hides it, and the author took 40*pi/3 for the smallest. This produced the only wrong answer of the run.

Robustness
5. `limit()` whose value is infinite ends in an unhandled Python traceback (`decimal.InvalidOperation` in `show()`), 11/01/006 v2.
6. `tension: free` plus `tension()` fails with a misleading "need area?" (11/02/006 v1, v2; reported by author, not re-run).
7. `run` prints no result basis (exact / proved / sampled), although FORMAT promises one per result.

## Missing capabilities, ranked by problems blocked

| # | Capability | n | Problems |
|---|---|---|---|
| 1 | Acoustic amplitude relations: pressure amplitude, displacement amplitude, intensity, B (p0 = B k s0, I = p0^2/(2 rho v)); a pressure observable on a gas wave; emitters that carry v and rho | 9 | 11/03/001, 11/03/009, 11/03/010, 11/03/012, 11/03/013, 24/01/asc_005, 24/01/asc_006, 24/01/bmc_004, 24/01/bmc_005 |
| 2 | Liquid and solid media (bulk modulus, Young's modulus), including rods and longitudinal resonators | 7 | 11/03/004, 11/03/008, 11/03/010, 24/01/cnt_004, 24/01/cnt_007, 11/05/004, 11/05/008 |
| 3 | Travel time over a length: time-of-flight observable and an integral for non-uniform strings (correct `front()`) | 5 | 11/02/001, 11/02/002, 11/02/007, 11/02/011, 11/02/013 |
| 4 | Closed forms from lists: families (n*f1), indexing, loci in x-y, bounding an infinite family without spending an attempt | 5 | 11/01/002, 11/04/004, 11/04/007, 11/04/008, 11/04/012 |
| 5 | Sound level in dB, and solving for an unknown inside log | 4 | 11/03/003, 11/03/006, 11/03/010, 24/01/cnt_006 |
| 6 | Mechanics around the string: spring-mass oscillator, Hooke extension, spring force and hanging-load statics as tension sources | 4 | 11/01/008, 11/02/003, 11/02/006, 11/02/013 |
| 7 | Gas extras: mixtures, rms speed, pressure together with temperature | 4 | 11/03/002, 11/03/011, 24/01/cnt_005, 24/01/dmt_004 |
| 8 | Pulse tools: piecewise profiles, peak or amplitude of a pulse, boundedness, solving where a sum vanishes | 4 | 11/01/003, 11/01/006, 11/01/010, 11/01/012 |
| 9 | Energy: energy density, kinetic energy of a standing-wave segment (integral over x), power through an area over a time | 3 | 11/02/004, 11/05/009, 11/03/006 |
| 10 | Partial standing waves and phasor extremes: antinode/node amplitude with partial reflection, max/min of a coherent sum over phase, a hole in a pipe | 3 | 11/04/002, 11/05/007, 11/05/014 |
| 11 | Source geometry: hemispherical emitter, power-to-amplitude link between `emitters` and `sources`, a source given by wavelength, symbolic distances | 4 | 11/03/003, 11/04/006, 11/04/009, 11/04/011 |
