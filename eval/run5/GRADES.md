# Run 5 grades (independent grader, Fable 5.2)

80 problems, book chapter "Waves". Graded on A, B, C, E of `eval/SCORECARD.md`; D was not asked for.
All 80 final scenes were re-run on the current engine (both scenes for B4/integer/14). Every re-run reproduced the values the authors report.

## Headline

- **One silent wrong engine result:** `vy` (and `slope`) at a pulse corner print `0` with no warning. It appeared in B4/comprehension/17. Details under "Suspected engine defects".
- **No other engine result is wrong.** All 11 automatic mismatches are explained: 4 book-key errors, 2 hand conclusions, 2 interpretive, 1 clerical letter slip, 2 comparison artefacts (rounding in integer/12, two-part answer in integer/14). A fifth book-key error (single/123) was counted as a match.
- **Automatic score 69/80 is slightly generous.** Two of the 69 are not engine-derived matches: B4/single/123 (letter b coincides with a misprinted key) and B4/jee_advanced/62 (Column II recalled from memory).

## How I applied the grades

- **B:** `verified-proved` when every engine value used is exact or proved. `unverified` when the physical step that decides the answer was done by hand. `wrong` when an engine value is wrong.
- **E:** `matches` when the engine value fixes the answer up to reading, rounding or picking an option. `not-produced` when a physical relation outside the engine was needed, even if the letter equals the key.
- **differs-book-disputed** only where the corpus has a reproducible calculation that the engine confirms. The two interpretive disputes (comprehension/17, reasoning/5) are graded `differs`.

## Counts

| Dimension | Counts |
|---|---|
| A | faithful 69, minor-deviation 11, misrepresented 0 |
| B | verified-proved 68, verified-sampled 1, unverified 10, wrong 1 |
| C | full 56, partial 23, unsupported 1 |
| E | matches 62, differs-book-disputed 5, differs 5, not-produced 8 |

## Table

| id | A | B | C | E | note |
|---|---|---|---|---|---|
| B4/comprehension/1 | faithful | verified-proved | full | matches | max over t of abs(y) at 5 cm = 2*sqrt(3) cm, exact |
| B4/comprehension/9 | faithful | unverified | partial | not-produced | pressure profile by hand (no pressure mode shape); author's coverage "full" is too high |
| B4/comprehension/17 | faithful | wrong | partial | differs | ENGINE: vy = 0 printed at a pulse corner (one-sided values are -0.1 and +0.1 m/s); author's reasoning says "nonzero velocity" against that printed 0; answer C is a sketch judgement, key D; corpus dispute is a low-confidence judgement, not evidence |
| B4/comprehension/22 | faithful | verified-proved | partial | matches | arc lengths typed by hand (declared), R fixed at 1 m; minima list exact |
| B4/comprehension/28 | faithful | verified-proved | full | matches | mode_shape zero only at ends; "KE zero = shape zero" is a reading |
| B4/comprehension/35 | faithful | unverified | partial | differs | engine gives only Ar = 0.8 A; v_max, v_min by hand; chose C (v_min 0.2 Ab, v_max printed negative) against key D; max_in refused under at() |
| B4/integer/8 | faithful | verified-proved | full | matches | Lx = 0.6 m; which end is ambiguous in the source (flagged) |
| B4/integer/10 | faithful | verified-proved | full | matches | 6.02 dB |
| B4/integer/12 | faithful | verified-proved | full | matches | 4.08 N, key 4 is rounded (automatic "n" is a tolerance artefact) |
| B4/integer/14 | faithful | verified-proved | full | matches | 36.02 dB and 632.5 m; power carried by hand from v1 to v3, so fit "full" is an over-claim |
| B4/integer/15 | faithful | verified-proved | full | differs-book-disputed | 138.25 W; key 43.7 W needs mu = 62.5 g/m (corpus calculation, reproduced) |
| B4/integer/20 | faithful | verified-proved | full | matches | E = m w^2 A^2/4 at two instants; mode formula typed by the author |
| B4/integer/26 | faithful | verified-proved | full | matches | harmonic 6 picked by hand from the list (2, 6, 10) |
| B4/jee_advanced/7 | faithful | verified-proved | full | matches | ratios 3/4 and 5/4 |
| B4/jee_advanced/8 | faithful | unverified | partial | not-produced | f_air = f_water entered as an assumption; no interface between sound media |
| B4/jee_advanced/10 | faithful | verified-proved | full | matches | e = 1/40 m |
| B4/jee_advanced/14 | faithful | verified-proved | full | matches | pulse shapes assumed (declared); KE = 4e-8 J, PE = 0 at t = 2 s |
| B4/jee_advanced/28 | faithful | verified-proved | full | matches | numeric k, w; option A misprint read as kx + wt |
| B4/jee_advanced/30 | faithful | verified-proved | full | matches | 1024 Hz |
| B4/jee_advanced/36 | minor-deviation | verified-proved | partial | matches | driven end modelled as a free end; option frequencies read off by hand |
| B4/jee_advanced/38 | minor-deviation | verified-proved | partial | differs-book-disputed | point source and wall stand in for a pipe end; engine: open end pi, rigid end 0, so B, D; key A, B, D has A and B contradicting each other (corpus) |
| B4/jee_advanced/58 | faithful | verified-proved | full | matches | 200 m/s from both waves |
| B4/jee_advanced/62 | minor-deviation | unverified | partial | not-produced | Column II missing from the problem file, filled from memory (disclosed); engine wavelengths 4L, 2L, 2L, L are right; the letters equal the key but cannot be derived from the source given |
| B4/jee_main/1 | faithful | verified-proved | full | matches | 9/4 |
| B4/jee_main/3 | faithful | verified-proved | full | matches | 12 cm |
| B4/jee_main/10 | minor-deviation | unverified | partial | not-produced | engine gives T = 81 N and mu; extension by hand (Hooke); f = 10 Hz and A = 1 mm invented and not listed in assume |
| B4/jee_main/14 | faithful | verified-proved | full | matches | I0*(3 + 2*sqrt(2)) |
| B4/jee_main/16 | faithful | verified-proved | full | matches | p = q/2 |
| B4/jee_main/17 | faithful | verified-proved | full | matches | 277.54 K; K to degC by hand; gamma and density assumed |
| B4/jee_main/25 | faithful | verified-proved | full | matches | phi = pi from figure facts |
| B4/jee_main/33 | faithful | verified-proved | full | matches | 12.5 N |
| B4/jee_main/40 | faithful | verified-proved | full | matches | 420 Hz; 5 - 3 = 2 Hz done by hand |
| B4/jee_main/41 | faithful | verified-proved | full | matches | 32 cm; 3rd harmonic chosen by hand, so fit "full" is an over-claim |
| B4/jee_main/45 | faithful | verified-proved | full | matches | ratio 1 |
| B4/jee_main/55 | faithful | verified-sampled | partial | not-produced | identity only sampled; pair beats 1, 1, 2; the count of 2 is the author's convention |
| B4/matrix/4 | minor-deviation | verified-proved | partial | matches | string analogue, wave kind not stated (flagged); corpus disputes row D only; answer equals key |
| B4/matrix/9 | minor-deviation | verified-proved | partial | matches | string-junction analogue for refraction and reflection |
| B4/matrix/10 | faithful | verified-proved | full | matches | 2, 1, 2, 1/2 |
| B4/multiple/3 | faithful | verified-proved | full | matches | symbolic |
| B4/multiple/6 | faithful | verified-proved | full | matches | f = 500/pi Hz, lambda = pi/50 m |
| B4/multiple/7 | faithful | verified-proved | full | differs-book-disputed | engine: wavelength ratio 1, speed +0.995%, f = 1507 Hz, so A, C, D; key B, C, D (B is false, A omitted) |
| B4/multiple/13 | faithful | verified-proved | full | matches | f1 = sqrt(5 Y alpha/rho)/l, all four dependences |
| B4/multiple/14 | faithful | verified-proved | full | matches | v = -1.5 m/s, lambda 0.2 m |
| B4/multiple/16 | faithful | verified-proved | full | matches | plane constant, point 1/r^2, flux = P |
| B4/multiple/17 | faithful | verified-proved | partial | matches | moisture and composition mapped to M and gamma by the author |
| B4/multiple/23 | faithful | verified-proved | full | matches | phase A > B; A moves down, B up |
| B4/reasoning/5 | faithful | unverified | partial | differs | speed ratio only; answered A, key B; the dispute is interpretive, no evidence |
| B4/reasoning/10 | minor-deviation | verified-proved | full | matches | assume text is garbled (mentions a 1 m string not in the scene); in-phase and antiphase proved |
| B4/reasoning/11 | faithful | unverified | unsupported | not-produced | no damping model; placeholder scene, honestly reported |
| B4/reasoning/20 | faithful | verified-proved | partial | matches | statement 1: 15.5% by engine; statement 2 from knowledge |
| B4/single/5 | faithful | verified-proved | partial | matches | 16/9; Archimedes relation typed into the tension |
| B4/single/6 | faithful | verified-proved | full | matches | 3/8 |
| B4/single/13 | faithful | verified-proved | full | differs-book-disputed | sqrt(2) : 1 (a); key b; length does not enter (corpus) |
| B4/single/27 | faithful | verified-proved | full | matches | 16.65 Hz exact against 16.67 linearised |
| B4/single/30 | faithful | verified-proved | partial | matches | 270 m, v = 360 m/s; echo criterion tagged assumption |
| B4/single/37 | faithful | verified-proved | full | matches | 0.256 kgf |
| B4/single/47 | faithful | verified-proved | full | matches | ratio^2 = 303.15/288.15, pressure drops out |
| B4/single/58 | faithful | verified-proved | full | matches | 12 kg |
| B4/single/60 | minor-deviation | verified-proved | full | matches | "same material" assumed; the source does not state it and the answer file says nothing is missing |
| B4/single/63 | faithful | verified-proved | full | matches | 2 pi/3 |
| B4/single/66 | faithful | unverified | partial | not-produced | rms speed proportional to sqrt(T) by hand |
| B4/single/67 | faithful | verified-proved | full | matches | 1/(30000 pi) m |
| B4/single/69 | faithful | verified-proved | full | matches | 0.4 pi |
| B4/single/71 | minor-deviation | verified-proved | full | matches | "wax lowers the frequency" tagged stated; it is the author's physics |
| B4/single/92 | faithful | verified-proved | full | matches | 10 m |
| B4/single/95 | faithful | verified-proved | full | matches | 4 I; antiphase typed as phase pi |
| B4/single/100 | faithful | verified-proved | full | matches | 125% |
| B4/single/107 | faithful | verified-proved | partial | matches | tension proportional to extension typed by hand, so fit "full" is an over-claim |
| B4/single/112 | faithful | verified-proved | full | matches | 2 I0 |
| B4/single/118 | faithful | verified-proved | full | matches | free-end reflection: 2 cm at O, 0 at 1 cm from O |
| B4/single/123 | faithful | verified-proved | full | differs-book-disputed | engine 16.99 dB; no option is 17 dB (page p-091 checked, options as transcribed); key b "1.7 dB" is in bels; author's letter b equals the key, so the automatic Y is a coincidence |
| B4/single/125 | faithful | unverified | partial | differs | answered 1 (b) by hand from pair beats; key 2 |
| B4/single/129 | faithful | verified-proved | full | matches | 0.5 m; a hand step is listed beside fit "full" |
| B4/single/136 | faithful | verified-proved | full | matches | n/2 |
| B4/single/138 | minor-deviation | verified-proved | partial | matches | cot(10 pi x) is as printed (page checked); replaced by the intended standing wave (declared); v = 5, not 4 |
| B4/single/145 | faithful | verified-proved | full | matches | 43.01 dB |
| B4/single/149 | faithful | unverified | partial | not-produced | engine gives the period only; "compression to rarefaction = half a period" by hand |
| B4/single/152 | faithful | verified-proved | partial | matches | ratio 5, start-independent |
| B4/single/165 | minor-deviation | verified-proved | full | differs | engine d1/d2 = 1/4, which is key b; the author wrote letter a (clerical slip); equal length assumed and not flagged |
| B4/single/173 | faithful | verified-proved | full | matches | 4; molar masses and gamma supplied by the author |

## Adjudication of the known issues

- **B4/jee_advanced/62 (Column II missing).** The corpus record keeps Column II under a top-level `column_ii` key, while the other matrix records keep both columns inside `options`. The problem export dropped it. The author disclosed that the labels were recalled from memory. The engine part (fundamental wavelengths 4L, 2L, 2L, L) is correct. Graded A minor-deviation, B unverified, E not-produced.
- **Author B ran other authors' scenes read-only.** This breaks the isolation of the batches. I found no sign of it in batch B's files: the 20 problems are disjoint from the other batches and 19 were single attempts. I cannot verify it further from the files, so no grade was changed.
- **B4/single/123 (no option is 17 dB).** Confirmed. The page image (p-091) shows the options exactly as transcribed: 7, 1.7, 2.7, 3.7 dB. The engine gives 16.99 dB. Key b is the value in bels. Graded E differs-book-disputed; the automatic "Y" is a coincidence of letters.

## Over-claims (engine_fit full with hand work)

Clear:
- **B4/integer/14:** the source power solved in v1 was typed into v3 by hand; the hand step is listed beside `full`.
- **B4/jee_main/41:** "next resonance = 3rd harmonic" was chosen by hand (admitted in friction); `resonances()` was not used.
- **B4/single/107:** tension proportional to extension (Hooke) was typed into the tensions by hand (admitted in friction).
- **B4/single/129:** a hand step is listed beside `full`.
- **B4/single/71:** "wax lowers the frequency" is author physics, tagged `stated`.

Borderline:
- **B4/jee_main/40:** 5 - 3 = 2 Hz by hand.
- **B4/single/95:** the minimum was imposed by typing phase pi.
- **B4/integer/20:** the mode formula A sin(pi x/L) cos(w t) was typed by the author.
- **B4/single/173:** molar masses supplied from memory.
- **B4/single/123:** the option letter was chosen against the engine value.

Other honesty notes:
- **B4/comprehension/17:** the reasoning claims "y = 0 at centre with nonzero velocity", but the scene printed `opp_vel_note = 0`.
- **B4/comprehension/9:** coverage `full` although the pressure profile is not represented.
- **B4/single/165:** the reasoning says 1 : 4 but the answer letter is a (1 : 2).
- **B4/jee_main/10:** a wave with f = 10 Hz and A = 1 mm was invented and is not in `assume`.

## Suspected engine defects

1. **WRONG, silent: `vy` and `slope` at a corner of a shaped pulse return 0.**
   - Seen in B4/comprehension/17: `vy(opp, x=0, t=1 s) = 0` for an upright and an inverted triangular pulse at full overlap.
   - My probe (same two pulses): `vy` at x = -1 mm is -0.1 m/s and at x = +1 mm is +0.1 m/s; exactly at x = 0 it prints 0. For a single pulse, `vy` and `slope` at its peak also print 0.
   - Inconsistent with the engine's own energy: `kinetic_density` at the same point prints 1/200, which is (1/2)*mu*(0.1)^2. So the engine reports a moving particle and zero velocity at one point.
   - FORMAT.md says a density exactly at a corner is refused. It was not refused here (sum of two pulses), and nothing covers `vy`/`slope`.
   - Effect: the passage's central claim ("displacement zero, but not their velocities") reads as contradicted by the engine. Expected: refuse, or give the one-sided values.
2. **Refusal contrary to the documentation: `at(max_in(...), A=..., ...)`.** `max_in`/`min_in` reject free symbols even when `at()` supplies every value (B4/comprehension/35, all four observables NOT AVAILABLE). This blocked the only engine route to v_max and v_min. Not a wrong value.
3. **Documentation mismatch: `nodes()` on a fixed-fixed string.** `count(nodes(r, harmonic=1))` gives 2 (the ends), while FORMAT.md says nodes "inside the resonator" (B4/comprehension/28). Value defensible, wording misleading.
4. **Reported by an author, not reproduced by me:** a sum of three waves of different frequencies was refused for B4/single/125, yet the same kind of sum evaluated in B4/jee_main/55.

## Transcription defects

- **B4/jee_advanced/62:** Column II stored under `column_ii` outside `options`, so the problem file lost it. This is the only defect that changed a result.
- **B4/single/138:** `cot(10 pi x)` is what the book prints (page checked); almost certainly a misprint for cos. The record should say so; the corpus check instead builds nodes and antinodes from the cot form.
- **B4/single/60 and B4/single/165:** the source does not state "same material" (60) or "same length" (165). The corpus checks assume them silently.
- **B4/single/152:** the area is "a" in the statement and "s" in the options (book defect, noted in the record).
- **B4/jee_advanced/28:** option A is printed "kx x wt" (book defect, noted).
- **B4/single/136:** "fundamental not produced" corrected to "note" by the transcriber (noted, harmless).
- **B4/integer/15:** key "43, 7" read as 43.7 (noted).
- **B4/comprehension/17:** the options are sketches described in words. The description agrees with the page image (p-100), but the answer cannot be settled from words alone.
- No difference was found between any problem file and its corpus record in statement or options, apart from jee_advanced/62.

## Missing capabilities, ranked by problems blocked or forced into hand work

| # | Capability | Layer | Problems |
|---|---|---|---|
| 1 | Symbolic scale: symbolic lengths in rays, `node_at`, thermal fall; ratio questions needing invented mu, L or T; two log-unknowns; sign-undecidable `travel_time`; `max_in` under `at()` | maths | 13: comprehension/22, comprehension/35, integer/14, integer/26, jee_advanced/28, jee_advanced/36, jee_advanced/62, jee_main/1, jee_main/25, jee_main/40, jee_main/55, multiple/13, single/30 |
| 2 | Composite and driven resonators: joined wires with a node at the joint, a clamp at mid-length, a pressed string, a driven end, testing a given standing-wave formula against a resonator | assembly | 5: jee_main/16, single/60, jee_advanced/62, jee_advanced/36, integer/8 |
| 3 | Sound at boundaries: interface between two sound media, pipe-end reflection of a pulse, partly reflecting obstacle, reflection and refraction for waves other than on strings | assembly | 5: jee_advanced/8, jee_advanced/38, comprehension/35, matrix/4, matrix/9 |
| 4 | Mechanics that sets string tension: Hooke/Young extension, buoyancy on a hanging load, loads in kg or kgf | assembly | 5: jee_main/10, single/107, single/5, single/37, single/58 |
| 5 | Point and mode observables: pressure mode shape, particle kinetic energy of a mode, compression phase at a point, energy of mode n with amplitude A | observation | 4: comprehension/9, comprehension/28, single/149, integer/20 |
| 6 | Gas properties: bulk modulus (isothermal, adiabatic), rms molecular speed, humidity and composition, degC output | observation | 4: reasoning/5, single/66, multiple/17, jee_main/17 |
| 7 | List operations and option matching: next element of a list, compare a value with option expressions | maths | 4: integer/26, jee_main/41, single/37, single/47 |
| 8 | Authoring conventions: `tension: free` hides tension and energy; harmonic phase convention sin(wt - kx) against the book's sin(kx - wt + phi); reserved name `mu`; units um and microW | authoring | 6: jee_main/10, jee_main/33, single/152, jee_main/25, integer/12, single/149 |
| 9 | Beats and loudness envelope of three or more tones | maths | 2: jee_main/55, single/125 |
| 10 | Corners of shaped pulses: `vy`/`slope` at a corner (wrong 0), sum of shaped pulses refused for energy | maths | 2: comprehension/17, jee_advanced/14 |
| 11 | Flagging a non-physical or misprinted source (cot profile, self-contradicting key, missing column) instead of substituting | qualification | 3: single/138, single/123, jee_advanced/62 |
| 12 | Sketch options and statement-explanation questions: comparing an engine shape with drawn options, damping | teaching | 3: comprehension/17, reasoning/11, reasoning/20 |
