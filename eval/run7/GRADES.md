# Run 7 grades (independent grader: Claude Opus, standing in for Fable 5.2)

**Grader note:** these grades were written by a Claude Opus agent standing in for the usual Fable 5.2 grader, which needs usage credits. I used the run 5 and run 6 conventions and layout (`eval/run6/GRADES.md`).

44 problems, book chapter "Waves": set D2 (Doppler, 12) and set S2 (sealed sample, 32). Graded on A, B, C, E of `eval/SCORECARD.md`; D was not assessed.
- **Re-runs:** all 44 final scenes were re-run on the current engine (`eval/run7/grading/out/`). Every re-run reproduced the values the authors report.
- **Frozen files:** the engine and FORMAT.md match `FROZEN.md5`. The "format/examples (combined)" line is a combined hash that `md5sum -c` cannot check.
- **Author copies:** all 44 copies are identical to their corpus records in statement, figure and options, and none carries an answer.
- **Probes:** my probe scenes and their outputs are in `grading/` and `grading/out/`.

## Headline

- **No silent wrong engine result.** I checked every engine value used in the 44 final scenes against the corpus calculation or by hand. For integer/4 I also did an independent retarded-time calculation, which gives 1029.649 Hz. Each value is correct for the scene as written. H1 holds for values.
- **No electromagnetic problem was in the run.** The README says set D2 includes radar and light. None of the 12 D2 problems does; jee_advanced/49 and multiple/1 match "light" only through "slightly" and "light pulley". The m12 guard therefore never met a real light problem.
  - The guard did fire once, wrongly, in a pure sound problem: jee_main/26 v1 and v2. An unranged arbitrary sound speed was sampled at 340000 m/s by the `in cm` check (defect 4).
- **Engine-derived matches: 35/44.** The automatic score is 38/44.
  - 1 automatic miss is a format artefact and counts as a match: integer/25 (mapping keys oxygen/helium against a/b).
  - 4 automatic hits are not engine-derived, because the deciding step was done by hand: integer/1, multiple/26, jee_advanced/20, jee_advanced/49.
  - The other 5 misses stand:
    - 2 book-key disputes that the engine supports: single/147, integer/17.
    - 1 disputed key where the scene was refused: integer/5.
    - 1 judgement on an unstated fact: single/130.
    - 1 wrong answer from the author's own knowledge after the engine was blocked: single/52. The key is A. Without the author's added bound, the engine gives the coefficient 8, which is key A (`grading/probe_s52_nobound.yaml`).
- **Answers decided by hand rose:** 6/44 (14%) are unverified, against 3/47 (6%) in run 6. H2 fails on its own measure.
  - None of the six is an option-picking or unit failure.
  - Four come from physics outside the model: an accelerating source, pressure at a point, a train of pulses, and a "beat unchanged" crossing.
  - Two come from engine refusals: `limit` on a bounded symbol, and a trig solve with both points off the origin.
- **`nearest()` failed in 7 of the 16 final scenes that use it.** Every failure involves a solved unknown (defect 1). The authors then read the option by eye. The letters are still right, so E is not affected.

## How I applied the grades

Same conventions as run 6.

- **B:**
  - `verified-proved` when every engine value used is exact or proved.
  - `verified-sampled` when the deciding value carries the "same at 5 scalings/values (sampled)" or "sampled, not proved" basis.
  - `unverified` when the step that decides the answer was done by hand.
  - `wrong` when an engine value is wrong.
- **Mechanics typed into the scene:**
  - A simple mechanical relation typed into the scene as a tagged fact, which the engine then solves with, keeps B verified and E matches, as for run 6 integer/23 and jee_advanced/25. Example: the incline balance in multiple/1.
  - integer/1 is different. Its hand-typed fact (u = (2/3) v cos θ) contains the whole non-trivial content of the problem (retardation plus kinematics), so it is graded unverified and not-produced.
- **E:**
  - `matches` when the engine value fixes the answer up to reading, rounding or picking an option. Reading an option by eye after a refused `nearest()` still counts as matches.
  - `not-produced` when a relation outside the engine decided the answer, or when the scene produced no value.
- **differs-book-disputed** only where the corpus marks the key DISPUTED with a reproducible calculation and the engine confirms it: single/147 and integer/17.
  - integer/5 is disputed too, but the final scene produced no value, so it is not-produced. My probe gives the transcriber's 290 cm branch, not 250 (see Adjudication).
  - single/130 depends on an unstated syllable time and is graded differs.
- **A:**
  - A declared stand-in is `minor-deviation`. The only one is integer/1: constant velocity in place of acceleration.
  - Declared assumed values are `faithful`: single/156 v2 = 0.1 m/s, single/130 0.1 s per syllable, single/147 v = 340 m/s for the symbol v.
  - Representative instances of a generic statement are `faithful`: multiple/28 uses a string junction.

## Counts

| Dimension | Overall (44) | Set D2 (12) | Set S2 (32) |
|---|---|---|---|
| A | faithful 43, minor-deviation 1, misrepresented 0 | faithful 11, minor-deviation 1, misrepresented 0 | faithful 32, minor-deviation 0, misrepresented 0 |
| B | verified-proved 20, verified-sampled 18, unverified 6, wrong 0 | verified-proved 7, verified-sampled 4, unverified 1, wrong 0 | verified-proved 13, verified-sampled 14, unverified 5, wrong 0 |
| C | full 34, partial 10, unsupported 0 | full 11, partial 1, unsupported 0 | full 23, partial 9, unsupported 0 |
| E | matches 35, differs-book-disputed 2, differs 1, not-produced 6 | matches 10, differs-book-disputed 1, differs 0, not-produced 1 | matches 25, differs-book-disputed 1, differs 1, not-produced 5 |

Run 6 for comparison (47): A 43/3/1; B 29/15/3/0; C 32/14/1; E 39/2/4/2.

## Table: set D2 (Doppler)

| id | A | B | C | E | note |
|---|---|---|---|---|---|
| B4/single/159 | faithful | verified-sampled | full | matches | exact receding change -1/12 (8.33%); `nearest` gives option 4 (10%) from the exact value, so the author's hand step "use v_s << v" was not needed (under-claim) |
| B4/single/147 | faithful | verified-proved | full | differs-book-disputed | wavelength ratio (v-u)/(v+u) proved for every allowed u; answered A, key C is the reflected *frequency* (corpus DISPUTED); v = 340 m/s typed for the symbol v (declared; u ranged across (0, 340)) |
| B4/single/156 | faithful | verified-proved | full | matches | exact Doppler gives v1 - v2 = 2.0148 m/s (checked by hand) with v2 = 0.1 m/s assumed and declared; option read by eye (`nearest` on an unknown refused); author's coverage "partial" is cautious |
| B4/single/26 | faithful | verified-sampled | full | matches | 14200/13 = 1092.3 Hz, nearest option 3 |
| B4/integer/4 | faithful | verified-proved | full | matches | 1029.65 Hz exact closed form; my retarded-time check gives 1029.649 |
| B4/integer/1 | minor-deviation | unverified | partial | not-produced | the kinematic and retardation link u = (2/3) v cos θ is hand-derived and typed as an assumption; constant velocity stands in for acceleration (declared); engine then solves 60 deg; my probe at v = 300 m/s, d = 80 m also gives 60 (the author claimed independence without running it) |
| B4/integer/13 | faithful | verified-sampled | full | matches | 2500 Hz; 50 sqrt(41) = 320.16 m; the reception instant t = D/(0.8 v) written by the author (framing, not physics) |
| B4/jee_main/7 | faithful | verified-proved | full | matches | u = 15 m/s; km/h options converted inside the observables (no km/h unit) |
| B4/jee_main/23 | faithful | verified-proved | full | matches | f0 = 6000/7, receding 750 Hz, nearest option 4 |
| B4/jee_main/19 | faithful | verified-sampled | full | matches | f0 = 2250 Hz exactly; `nearest(f0, ...)` refused (defect 1) |
| B4/jee_main/30 | faithful | verified-proved | full | matches | 660 Hz source, 665.56 Hz heard, nearest option 4; 10 km/h written as 10[km]/3600[s] |
| B4/jee_advanced/13 | faithful | verified-proved | full | matches | uB/uA = 2, option checks proved for every allowed v |

## Table: set S2 (sealed sample)

| id | A | B | C | E | note |
|---|---|---|---|---|---|
| B4/single/182 | faithful | verified-sampled | full | matches | v = 378 m/s; `nearest(vs in m/s, ...)` refused as "comparison not allowed here" (defects 1, 2) |
| B4/single/106 | faithful | verified-sampled | full | matches | Imax/Imin = 25/9 with three co-located sources (powers 16, 1, 1 W; phases 0, 0, pi) |
| B4/single/52 | faithful | unverified | partial | not-produced | three attempts blocked: `limit` refused because the author's fact dl < L/2 bounds dl (defect 5); answered D from knowledge, key A; my probe without the bound gives coefficient 8 (= key A) |
| B4/single/130 | faithful | verified-proved | partial | differs | d = 33 m from an assumed 0.2 s round trip (0.1 s per syllable, declared); key C needs 0.2 s per syllable, which is not stated (corpus note); judgement |
| B4/single/97 | faithful | verified-proved | full | matches | 0.9587 um, nearest option 4; spherical spreading assumed (declared); um options written as 1e-6[m] |
| B4/single/139 | faithful | verified-proved | full | matches | L_min = 1/2 m |
| B4/single/2 | faithful | verified-sampled | full | matches | fork 105 Hz unique over the sign cases; options printed in N (book misprint, noted); `nearest(fn in Hz, ...)` refused |
| B4/single/166 | faithful | verified-proved | full | matches | Lc/Lo = 3/4; (9, 6) proved, others proved false |
| B4/single/10 | faithful | verified-sampled | full | matches | only D has the printed t = 0 profile and +4.5 m/s; profile poles noted by the author, profile not altered |
| B4/single/110 | faithful | verified-sampled | full | matches | ratio 2 |
| B4/multiple/1 | faithful | verified-proved | partial | matches | T = 98 N from v and mu; M = 10 kg via `weight`; incline balance m g sin 30 = T typed as a tagged fact (no incline in the format); g = 9.8 assumed |
| B4/multiple/26 | faithful | unverified | partial | not-produced | slope signs proved; the link "compression where the displacement slope is < 0" is the author's (no pressure-at-a-point observable) |
| B4/multiple/28 | faithful | verified-proved | partial | matches | string junction as the medium change: speed, amplitude and wavelength change, frequency same (proved) |
| B4/reasoning/14 | faithful | verified-proved | full | matches | speed unchanged with P doubled at fixed T (proved); x4 T gives x2 speed; author's coverage "partial" is cautious |
| B4/reasoning/19 | faithful | verified-proved | full | matches | phi = 2 pi/3 solved; sum rule false there (a counterexample is enough) |
| B4/comprehension/20 | faithful | verified-sampled | partial | matches | Imax/I0 = 2; arcs pi R/2 and 3 pi R/2 typed from the figure; I0 built from two incoherent copies; one constructive branch chosen |
| B4/comprehension/42 | faithful | verified-proved | full | matches | rho = 1 kg/m^3, cross-checked v = 400 m/s; phase pi for the sin(kx - wt) form is right |
| B4/comprehension/47 | faithful | verified-sampled | full | matches | reflected/incident at B = -1/3 |
| B4/matrix/7 | faithful | verified-sampled | full | matches | 1/16, 1/8, 1/8, 2; intensity = power/area with equal areas written by hand (trivial, declared) |
| B4/integer/5 | faithful | unverified | full | not-produced | final scene refused ("kk only fixed up to a period 20*pi that depends on symbols"), even with a bound leaving one branch (defect 6); answer "not determined" is honest; key 250 corpus-DISPUTED; my shifted probe gives 290.47 cm |
| B4/integer/17 | faithful | verified-proved | full | differs-book-disputed | vs = 250 m/s for every consecutive pair (end correction left as a family); key 350 corpus-DISPUTED, engine confirms 250 |
| B4/integer/25 | faithful | verified-proved | full | matches | 314.009 and 971.825 m/s; gases with a stated bulk modulus entered as `fluid` (same physics); automatic "n" is a mapping-key artefact |
| B4/jee_main/44 | faithful | verified-sampled | full | matches | 2 sqrt(2) s; `nearest` with sqrt options worked |
| B4/jee_main/26 | faithful | verified-sampled | full | matches | d = 39.894 cm; v1/v2 hit defect 3 ("0[m]") and defect 4 (sound speed sampled at 340000 m/s) |
| B4/jee_main/42 | faithful | verified-sampled | full | matches | n1 : n2 = 1 : 2 with n1 = 1 pinned (declared); invariance over the family claimed, not run |
| B4/jee_main/36 | faithful | verified-proved | full | matches | e = 5 cm, v = 327.68 m/s read as 328 (`nearest` refused, defect 1) |
| B4/jee_advanced/49 | faithful | unverified | partial | not-produced | engine shows A and D raise the beat (sampled); B and C chosen by hand ("crossing"); my probe shows the engine can solve the crossing at the given values (a2 = 1.2544, a1 = 0.7864) |
| B4/jee_advanced/20 | faithful | unverified | partial | not-produced | v = 8 m/s, period 0.1 s exact; "constructive between successive pulses" decided by hand (no pulse train); author notes 0.2 and 0.4 s also qualify |
| B4/jee_advanced/23 | faithful | verified-sampled | partial | matches | sqrt(6)/2 = 1.2247 via `stretch`; mu taken unchanged (declared) |
| B4/single/85 | faithful | verified-sampled | full | matches | sqrt(2)/4, proved equivalent to 1/(2 sqrt 2) |
| B4/single/55 | faithful | verified-sampled | full | matches | 150 + 15 sqrt(101) = 300.75 Hz; `nearest` refused because the value depends on the solved tension, not because of the sqrt (defect 1) |
| B4/jee_advanced/2 | faithful | verified-proved | full | matches | M = 10 g; `nearest(M, ...)` refused (defect 1) |

## Adjudication of the known issues

- **B4/single/147 (key C, corpus DISPUTED).** The question asks for a wavelength, but every option is a frequency.
  - The engine proves that the reflected wavelength is (v-u)/(v+u) times the original wavelength. That is option A's coefficient.
  - Key C, (v+u)/(v-u) f, is the reflected frequency.
  - The author read A as the wavelength ratio and declared that reading. Graded differs-book-disputed.
- **B4/integer/5 (key 250, corpus DISPUTED).** The final scene was refused.
  - My probe `grading/probe_i5_twophase.yaml` shifts the origin (points at 0 and 15 cm) and adds k < 5 1/m. It solves lambda = 290.47 cm, the transcriber's near branch.
  - The other branch under "less than half a wavelength apart" is 53 cm.
  - 250 is not reproducible. Graded not-produced (no engine value from the author).
- **B4/integer/17 (key 350, corpus DISPUTED).** The engine gives 250 m/s from the two consecutive resonances (lambda/2 = 25 cm), and the end correction cancels. Graded differs-book-disputed.
- **B4/single/130 (judgement).** Not DISPUTED in the corpus, but the key needs 0.2 s per syllable, which the problem does not state. The author assumed 0.1 s, declared it, and answered 33 m. Graded differs.
- **B4/single/52 (author error after an engine refusal).**
  - The author added `dl < L/2` as a fact. That made dl a bounded symbol, and `limit` then refuses it.
  - The same scene without that fact gives coefficient 8 (key A).
  - The author's knowledge answer D (4 f0 dl/l) is wrong.
- **B4/single/2, B4/single/10.** Book misprints (N for Hz; the poles in 6/(x^2 - 3)) were noted by the authors and did not change the answer.

## Over-claims (engine_fit or coverage full with hand work)

Borderline:
- **B4/jee_main/42:** fit full, with n1 = 1 pinned by assumption and the family invariance not run.
- **B4/single/182, B4/single/2, B4/jee_main/36, B4/jee_advanced/2, B4/jee_main/26:** fit full, with the option read by eye after `nearest` was refused. The reading is trivial, so this is not a real over-claim.
- **B4/integer/1:** `missing_in_source` says that v and d were "shown irrelevant", but the author never varied them. My probe confirms the claim.

Under-claims, where the author was more cautious than needed:
- single/159: `nearest` gave D.
- single/156, reasoning/14: the coverage is in fact full.
- multiple/28: amplitude change proved for the instance.

Honesty overall is good:
- 19 partial and 2 none out of 44.
- No stand-in is presented as full.
- No assumption is tagged as stated.
- Refusals were reported plainly (integer/5, single/52, jee_advanced/20).

## Hypotheses

- **H1 (no wrong engine value; light and radar as `em` with no stand-ins): holds for values, but the light and radar part was not tested.**
  - Wrong values: 0.
  - No scene used a gas stand-in for light. But no light, radar or radio problem was in set D2, despite the README.
  - The m12 guard fired only as a false positive: an arbitrary sound speed scaled to 340000 m/s in jee_main/26 v1–v2 (defect 4).
- **H2 (hand-decided answers at or below 6%): fails.**
  - Unverified: 6/44 (14%). Answers with any hand step: 21/44 (48%), against 43% in run 6.
  - The tools named in H2 partly worked.
    - `nearest` decided 9 answers.
    - `in` converted units (g, cm).
    - `weight` and `stretch` set tensions (multiple/1, jee_advanced/23).
  - But `nearest` was refused in 7 of 16 final scenes (defect 1), so option picking by eye did not fall.
  - The six hand-decided answers come from elsewhere:
    - physics outside the model: integer/1, multiple/26, jee_advanced/20, jee_advanced/49;
    - engine refusals: single/52 (defect 5) and integer/5 (defect 6).
- **H3 (remaining gaps mostly format and authoring, rather than physics): does not hold.**
  - Reading the source was strong: no misreading of a stated fact (run 6 had two). The only judgement miss is single/130, on an unstated fact.
  - The gaps are mainly engine services (maths layer), physics outside the model, and some format gaps.
    - Engine services: `nearest` with unknowns (7), `limit` on a bounded symbol, trig solving, and the sampler against the guard.
    - Physics outside the model: acceleration, pressure at a point, pulse trains, incline statics, intensity on strings.
    - Format: km/h and um, quoted zero.
  - Authoring contributed in single/52 (a bound added that blocked `limit`) and jee_advanced/49 (crossing not tried).

## Suspected engine defects (each verified by a run)

No wrong value was found. All items are refusals or misleading messages.

1. **`nearest()` refuses values that depend on a solved unknown:** "needs numbers (the value and every option)".
   - It fails for a bare unknown (`nearest(d, ...)`, `nearest(f0, ...)`, `nearest(M, ...)`), with or without units on the options. It also fails for an observable built on a solved medium quantity (single/55: frequency with a solved tension; also without arbitrary values, `probe_s55_noarb`).
   - A ray frequency with a solved source frequency works (jee_main/23). The rule is therefore inconsistent.
   - 7 final scenes affected. Probes: `probe_nearest`, `probe_jm23_bare`, `probe_s55_noarb`.
   - **Refuted:** "nearest refuses exact sqrt expressions". `nearest(150 + 15*sqrt(101), ...)`, sqrt options and a known-tension frequency all work (`probe_sqrt_plain`, jee_main/44). single/55 fails only because of the solved tension.
2. **`in` inside `nearest()`** gives "comparison not allowed here".
   - FORMAT documents `in` only as a whole-observable suffix, so a refusal is acceptable. The message is wrong, and authors tried it 3 times in final scenes plus jee_main/26 v1–v2.
   - Probe: `probe_nearest` (n_unknown_in, n_obs_in).
3. **A quoted zero length is rejected:** `"0[m]"` and `"(0)[m]"` in a position list give "number '0[m]' needs a unit". `"5[m]"` and unquoted `0 m` are accepted.
   - Seen in single/130 v1 and jee_main/26 v1. Probes: `probe_zero_quoted`, `probe_paren_quoted`, `probe_five_quoted`.
4. **`expr in unit` uses the comparison sampler**, which runs an unranged arbitrary value out to about x1000. FORMAT documents x0.01 to x89. With an arbitrary sound speed, this trips the m12 guard ("a speed of 340000 m/s is not sound").
   - In the same scene, plain `d` (5 scalings) and `d < 0.5[m]` (proved) are fine.
   - Probe: `probe_arb_v`. Seen in jee_main/26 v1–v2.
5. **`limit(expr, var, 0)` refuses a symbol that has a bound** ("second argument must be a variable").
   - It is the bound, not the arbitrary values: the same scene without `dl < L/2` gives 8.
   - The author's claim "limit() refused with arbitrary scalings" is therefore refuted as to the cause.
   - FORMAT lists `at`, `diff` and `resonances` as working on bounded symbols; `limit` is not mentioned.
   - Probes: `probe_s52_nobound`, `probe_s52_bound`, `probe_s52_ratio`. Problem: single/52.
6. **Unknown k and phase with two points both off the origin** (x = 10 and 25 cm) are refused: "'kk' is only fixed up to a period 20*pi that depends on symbols".
   - This happens even with a bound that leaves one branch (kk < 5 1/m).
   - The same physics with the points at 0 and 15 cm solves (290.47 cm).
   - FORMAT says other unknowns are enumerated over the range allowed by the inequalities.
   - Probes: `probe_i5_bound`, `probe_i5_tight`, `probe_i5_noarb`, `probe_i5_twophase`. Problem: integer/5.
7. **Missing units:** km/h and um. `10 km/h` gives "cannot parse expression"; `um` gives "unknown unit".
   - Problems: jee_main/7, jee_main/30, single/97, all worked around correctly. Probes: `probe_units`, `probe_units2`.

Gaps rather than defects:
- **Arbitrary ranges cannot be relative to another arbitrary value.** In single/147 v1, `u below 340 m/s` together with an arbitrary v became supersonic when v was scaled by 0.61. The message was clear.
- **"Symbolic angle in oblique geometry"** (integer/1 v1) is a clean, documented refusal.

## Transcription defects

- No difference between any author copy and its corpus record.
- **README:** it says D2 "include[s] radar and light". It does not: all 12 are sound.
- **Disputed keys:**
  - single/147, integer/5 and integer/17 are marked DISPUTED in the corpus. All three were reproduced or confirmed here.
  - single/130's key rests on an unstated syllable time. The corpus notes this but does not mark it DISPUTED.
- **Book misprints:** single/2 (options in N) and single/10 (profile with poles) are recorded in the corpus notes or by the authors.

## Top gaps by layer

| # | Gap | Layer | Count | Problems |
|---|---|---|---|---|
| 1 | `nearest()` refused for solved unknowns; `in` inside `nearest` | maths (engine service) | 7 | single/182, single/2, single/130, single/55, jee_main/19, jee_main/36, jee_advanced/2 |
| 2 | Physics outside the model: accelerating source, pressure/compression at a point, repeated pulse train with reflections, incline/pulley statics, intensity and volume energy density on strings, mu changing with stretch | physics | 6 | integer/1, multiple/26, jee_advanced/20, multiple/1, matrix/7, jee_advanced/23 |
| 3 | Solver and sampler refusals: `limit` on a bounded symbol, k and phase with off-origin points, `in` sampler against the sound-speed guard, ranges relative to another arbitrary value | maths | 4 | single/52, integer/5, jee_main/26 (v1–v2), single/147 (v1) |
| 4 | Units and syntax: km/h, um, quoted zero | format | 5 | jee_main/7, jee_main/30, single/97, single/130 (v1), jee_main/26 (v1) |
| 5 | Approximations and instants: v_s << v, "when the source is closest", "slightly", a family pinned by assumption | format | 5 | single/159, single/156, integer/13, jee_advanced/49, jee_main/42 |
| 6 | Authoring: a bound added that blocked the engine, then a wrong knowledge answer; a possible solution not tried; an unstated fact chosen differently from the key | authoring | 3 | single/52, jee_advanced/49, single/130 |
| 7 | Book keys disputed (and one judgement) | source | 4 | single/147, integer/5, integer/17, single/130 |

## Comparison with run 6

| Measure | Run 6 (47) | Run 7 (44) |
|---|---|---|
| Wrong engine values | 0 | **0** |
| Engine-derived matches | 39 (83%); D 11/15, S 28/32 | 35 (80%); D2 10/12 (83%), S2 25/32 (78%) |
| Answer decided by hand (unverified) | 3 (6%) | 6 (14%) |
| Not produced | 2 (4%) | 6 (14%) |
| Full coverage | 32 (68%) | 34 (77%) |
| Misrepresented | 1 (radar as gas) | 0 |
| Book-key disputes (differs-book-disputed) | 2 | 2 (+1 disputed key not produced) |
| Answers with any hand step | 20 (43%) | 21 (48%) |

- **Doppler improved:** D2 has 10/12 engine-derived matches with no misreading, against 11/15 in run 6. The run 6 defect "t= with an unknown speed" did not recur; authors used `emitted=` throughout.
- **Run 6 gaps that closed:**
  - Stand-ins for light, as far as tested.
  - Misreading stated facts.
  - The for-all `abs` comparison did not recur. Here jee_advanced/49's `abs` comparisons were decided (sampled).
- **Run 6 gaps that persist or moved:**
  - Option picking: run 6 had no `nearest`. Now it exists but fails on solved unknowns.
  - Arbitrary values that break scenes: now the sampler against the m12 guard.
  - Physics outside the model grew in this sample (6, against 6 in run 6, but now decisive in 4 answers).
- **Set S2 is weaker than set S:** 78% against 88% engine-derived matches. Its sample had more conceptual problems (compression, pulse trains, "beats unchanged", the sonometer bridge limit), where the engine either lacks the physics or refused.
