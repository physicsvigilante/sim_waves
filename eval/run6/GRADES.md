# Run 6 grades (independent grader, Fable 5.2)

47 problems, book chapter "Waves": set D (Doppler, 15) and set S (sealed sample, 32). Graded on A, B, C, E of `eval/SCORECARD.md`; D was not asked for.
All 47 final scenes were re-run on the current engine (`eval/run6/grading/out/`). Every re-run reproduced the values the authors report.

## Headline

- **No silent wrong engine result.** Every engine value used in the 47 final scenes was checked against the corpus calculation or by hand and is correct for the scene as written.
- **One engine value differs from a key without being wrong:** B4/jee_advanced/63 prints 8.24 Hz, key 8.13. The scene puts both distances at the emission instant. My probe (`grading/probe_ja63_mixed.yaml`: S1 800 m away when it emits, O 600 m away when it hears) gives 1520/187 = 8.128 Hz on the same engine. This is an authoring reading, not an engine fault.
- **Radio and radar are accepted without complaint as `type: gas, v: 3e8 m/s`** (B4/single/33, B4/integer/7). The numbers are right (499.999 m/s, 30.0000 m/s), but the scenes say "gas". H1 expected a clean refusal; there is none, and the format gives authors nothing else to use.
- **Automatic score 40/47 is close to the graded score, by cancellation.** Engine-derived matches are 39.
  - 2 automatic misses are answer-format artefacts and are matches: B4/integer/19 (mapping against "60, 20") and B4/jee_main/47 ("170 Hz" against letter D).
  - 3 automatic hits are not engine-derived matches: B4/jee_advanced/63 (8.24 rounded to "8 Hz" and accepted against 8.13), B4/single/73 and B4/single/90 (answered from knowledge).
  - The other 5 misses stand: 2 book-key disputes the engine supports (reasoning/9, matrix/2), 2 judgement calls (reasoning/15, single/169), 1 author misreading (jee_advanced/54, where the engine's own numbers give the key).

## How I applied the grades

Same conventions as run 5, with one addition for B.

- **B:** `verified-proved` when every engine value used is exact or proved. `verified-sampled` when the value the answer rests on carries the engine's "same at 5 scalings/values (sampled)" basis, i.e. it is exact at each run but its independence of the arbitrary values is only sampled. Run 5 had almost no arbitrary values, so this grade was rare there; here it is common and is not a weakness of the value itself. `unverified` when the step that decides the answer was done by hand. `wrong` when an engine value is wrong.
- **E:** `matches` when the engine value fixes the answer up to reading, rounding or picking an option. `not-produced` when a relation outside the engine was needed, even if the letter equals the key.
- **differs-book-disputed** only where the corpus has a reproducible calculation that the engine confirms (reasoning/9: wavelength unchanged; matrix/2: 0.2 m and 0.4 pi m/s). Interpretive disputes (reasoning/15, single/169) are `differs`. multiple/4 is disputed in the corpus on option D only; the answer equals the key, so `matches` (as run 5 did for matrix/4).
- **A:** a declared stand-in is `minor-deviation`; a stand-in that the answer file presents as full coverage is `misrepresented`. Shapes and scales assumed from a verbal figure and declared are `faithful` (as run 5).

## Counts

| Dimension | Overall (47) | Set D (15) | Set S (32) |
|---|---|---|---|
| A | faithful 43, minor-deviation 3, misrepresented 1 | faithful 12, minor-deviation 2, misrepresented 1 | faithful 31, minor-deviation 1, misrepresented 0 |
| B | verified-proved 29, verified-sampled 15, unverified 3, wrong 0 | verified-proved 7, verified-sampled 7, unverified 1, wrong 0 | verified-proved 22, verified-sampled 8, unverified 2, wrong 0 |
| C | full 32, partial 14, unsupported 1 | full 10, partial 4, unsupported 1 | full 22, partial 10, unsupported 0 |
| E | matches 39, differs-book-disputed 2, differs 4, not-produced 2 | matches 11, differs-book-disputed 1, differs 2, not-produced 1 | matches 28, differs-book-disputed 1, differs 2, not-produced 1 |

Run 5 for comparison (80): A 69/11/0; B 68/1/10/1; C 56/23/1; E 62/5/5/8.

## Table: set D (Doppler)

| id | A | B | C | E | note |
|---|---|---|---|---|---|
| B4/single/73 | faithful | unverified | unsupported | not-produced | intensity on a moving ray refused (clean); frequency rise proved; answer from knowledge, honestly reported |
| B4/single/33 | misrepresented | verified-sampled | partial | matches | radar wave entered as `type: gas, v: 3e8 m/s`; answer file claims coverage full, engine_fit full; c not stated (assumed, declared); u = 300000000/600001 = 499.999 m/s is right for the classical echo |
| B4/single/141 | faithful | verified-sampled | full | matches | 11/9; the `== 1.22` option checks print False (exact comparison), option picked by nearness |
| B4/multiple/18 | faithful | verified-sampled | full | matches | 1020.2 Hz, +2.02%; v = 330 m/s not in the source, assumed and declared; v1 showed the answer depends on it |
| B4/reasoning/9 | faithful | verified-proved | partial | differs-book-disputed | engine: heard frequency 514.7 against 500 Hz, wavelength unchanged, so S2 false; S1 by knowledge (intensity refused); answered C, key B needs S2 true; listener speed 10 m/s assumed (declared) |
| B4/integer/7 | minor-deviation | verified-sampled | partial | matches | radio wave as a gas with v = c, declared as a stand-in with coverage partial; u = 30.0000 m/s |
| B4/jee_main/49 | faithful | verified-sampled | full | matches | 264000/31 = 8516.13 Hz |
| B4/jee_main/21 | faithful | verified-sampled | full | matches | 12 and 18 m/s; directions deduced from the sign of the shift (declared) |
| B4/jee_main/47 | faithful | verified-proved | full | matches | f0 = 169.96 Hz; answer written "170 Hz" without the letter (automatic "n" is an artefact); distances fixed as assumptions because scaling them removed the echo |
| B4/jee_main/48 | faithful | verified-proved | full | matches | 1066.7 and 941.2 Hz; 11.76% of the approach value (12.5% of 1000 Hz), both nearest 12%; passing modelled as two far sources |
| B4/jee_main/11 | faithful | verified-sampled | full | matches | u = 0.250000 m/s; assume text says "opposite sides" but both forks start at -D (disclosed, harmless) |
| B4/jee_advanced/63 | faithful | verified-proved | full | differs | engine 8.24 Hz (both distances at emission) or 8.36 (reception); key 8.13 is exact for S1 at emission and O at reception (my probe: 8.128); answer "8 Hz" by rounding; ambiguity honestly reported; automatic Y is a tolerance artefact |
| B4/jee_advanced/37 | faithful | verified-proved | full | matches | all four comparisons proved for every allowed u, w, V |
| B4/jee_advanced/54 | minor-deviation | verified-proved | partial | differs | engine: 360 m/s for a passenger behind the whistle, 310 for B, which is key B; the passage states "engines are at the front ends", but the author listed the passenger's position as missing, added a passenger ahead of the whistle and answered D; relative speed built as f * wavelength by hand |
| B4/jee_advanced/55 | faithful | verified-proved | full | matches | band edges stay 800 and 1120 Hz; continuous band represented by its two edges |

## Table: set S (sealed sample)

| id | A | B | C | E | note |
|---|---|---|---|---|---|
| B4/single/142 | faithful | verified-sampled | full | matches | harmonic 3, 4 nodes, 3 antinodes (ends counted) |
| B4/single/35 | faithful | verified-proved | full | matches | c v/(4 l^2); water end closed is an assumption (declared) |
| B4/single/90 | faithful | unverified | partial | not-produced | engine says all four forms travel (true for the numbers typed); D chosen by a hand proxy (pattern speed 17000 against c = 340); the dimensional error cannot be expressed; c, T, lambda invented as numbers (declared) |
| B4/single/56 | faithful | verified-proved | full | matches | v = sqrt(g s), slope and concavity decided |
| B4/single/117 | faithful | verified-sampled | full | matches | 3 pi/5 m/s = 60 pi cm/s; cm conversion by hand |
| B4/single/175 | faithful | verified-sampled | full | matches | period 4 s; water wave as a harmonic wave with no medium (no gas stand-in); author's coverage "partial" is cautious |
| B4/single/49 | faithful | verified-proved | full | matches | ratio 2 pi A/lambda; the "iff" comparison of two symbols was refused, read by hand |
| B4/single/111 | faithful | verified-proved | full | matches | sqrt(2) A, omega; same direction assumed (declared); v = 340 m/s typed as a number rather than arbitrary |
| B4/single/102 | faithful | verified-sampled | full | matches | L2 = 1 m; fundamental assumed and tagged; overtone ambiguity (2 m also resonates) reported |
| B4/single/169 | faithful | unverified | full | differs | answered B, key D; engine gave 3.27 Hz (dl = L/10) and 2 Hz (dl = 3L); the for-all comparison was refused; conclusion from two samples; see adjudication |
| B4/single/64 | faithful | verified-proved | full | matches | columns 25 and 75 cm, water 45 cm |
| B4/single/11 | faithful | verified-proved | full | matches | path difference 1 m, first maximum 330 Hz; f -> 0 excluded with lo = 1 Hz (declared) |
| B4/multiple/33 | faithful | verified-proved | full | matches | 80, 240, 400 Hz; harmonic 4 refused; one stray failed observable (undeclared `fs`) |
| B4/multiple/9 | faithful | verified-proved | full | matches | four comparisons proved; factor 2 is a declared choice |
| B4/multiple/4 | faithful | verified-proved | partial | matches | A true both ways, B for +x, D for -x, C never; +x assumed to answer A, B = key; harmonic family only; corpus disputes D |
| B4/reasoning/7 | faithful | verified-sampled | partial | matches | (v_adiabatic/v_isothermal)^2 = 7/5; S2 and the explanation link from knowledge; assume text mentions 300 K and 29 g/mol that the scene does not use (disclosed) |
| B4/reasoning/15 | faithful | verified-proved | partial | differs | incident and reflected powers equal, loop energy constant (proved); answered A, key B; the explanation link is a judgement |
| B4/comprehension/12 | faithful | verified-proved | partial | matches | KE density at E proved greater than at D, F, G; shape and point positions assumed from the verbal figure (declared) |
| B4/comprehension/11 | faithful | verified-proved | partial | matches | harmonic 5, L = 15/16 m, closed end is a pressure antinode; P0 +/- dP0 read by hand |
| B4/comprehension/16 | faithful | verified-proved | full | matches | net y and net peak 0, each amplitude 1 cm, vy of each pulse and of the sum non-zero; observables named "..._nonzero" test `== 0` and print False (confusing, correct) |
| B4/matrix/2 | faithful | verified-proved | full | differs-book-disputed | engine 2, 20 pi, 0.2, 0.4 pi, so C-s, D-q; key has C and D swapped (corpus calculation, reproduced); B-p is a flagged guess (omega = 20 pi matches nothing) |
| B4/integer/19 | faithful | verified-sampled | full | matches | 0.6, 0.3, 0.2 m; automatic "?" is a format artefact |
| B4/integer/23 | faithful | verified-sampled | partial | matches | 79.06 Hz; tension = Y * strain * area typed by hand (declared) |
| B4/integer/24 | faithful | verified-proved | full | matches | harmonic 7, Lo = 8 cm |
| B4/jee_main/15 | faithful | verified-proved | full | matches | n = 6, L = 15/7 m |
| B4/jee_main/37 | faithful | verified-proved | full | matches | free-free rod, node at the middle checked, 4883 Hz |
| B4/jee_main/5 | faithful | verified-proved | partial | matches | resonance lists per option; 7.5 cm spacing read by hand; water heights not in the scene |
| B4/jee_main/54 | faithful | verified-proved | full | matches | T = 25/4 N from the cross-check |
| B4/jee_advanced/21 | faithful | verified-proved | full | matches | A omega; option C (d omega/dk) not checkable |
| B4/jee_advanced/4 | minor-deviation | verified-sampled | partial | matches | n = 344; the stated "2 beats" replaced by "fewer beats" (declared); string mode and length arbitrary |
| B4/jee_advanced/25 | faithful | verified-proved | partial | matches | option A proved; weight and buoyancy typed into the tensions (declared) |
| B4/jee_advanced/1 | faithful | verified-proved | full | matches | 15.206 cm; end correction 0.3 d is not in the source, entered as a declared convention |

## Adjudication of the known issues

- **B4/reasoning/9 (key B, corpus DISPUTED).** The engine shows the moving listener hears 8750/17 Hz while the wavelength stays 17/25 m. Statement 2 is false, so key B cannot hold. Statement 1 is the author's judgement. Graded E differs-book-disputed.
- **B4/matrix/2 (key C-q, D-s, corpus DISPUTED).** Engine: wavelength 1/5 m (s), maximum particle speed 2 pi/5 m/s (q). The key has them swapped. Graded differs-book-disputed. Row B has no correct partner in Column II.
- **B4/multiple/4 (corpus DISPUTED on D).** Engine confirms D holds for a wave toward -x and B fails there. The answer equals the key under the +x reading. Graded matches, with the dispute noted.
- **B4/reasoning/15 (judgement).** Both statements are supported by the engine; whether statement 2 explains statement 1 is not decidable by it. Graded differs.
- **B4/single/169 (judgement).** The beat is |v/(2(L+dl)) - v/(4L)|. For every dl > 0 it is below the initial 4 Hz: it falls to 0 at dl = L, then rises toward 4 Hz without reaching it. So "decrease" (B) is true against the initial count, and "may increase or decrease" (D) is true as a description of a continuous lengthening. The engine refused the for-all comparison although it is provable in two sign cases. Graded B unverified, E differs; the key is not refuted.
- **B4/jee_advanced/54.** Not a dispute. The scene contains the key's numbers (360, 310); the author overlooked a stated fact.
- **Author A's glob run.** File times show that when author A first ran (about 13:39), the only other authors' scenes in `work/` were comprehension/11, comprehension/12, integer/19, integer/23, jee_advanced/37, integer/7, jee_advanced/1, jee_advanced/25 and jee_main/11. None is in batch A and none shares a passage with a batch A problem (jee_advanced/54, the passage partner of A's jee_advanced/55, was written at 13:40:36). Outputs carry no answer to any batch A problem. No grade is affected.

## Over-claims (engine_fit or coverage full with hand work)

Clear:
- **B4/single/33:** coverage full and engine_fit full for a radar wave modelled as a gas.
- **B4/jee_main/48:** fit full, but the percentage is formed against the approach frequency by the author's choice; "passing" is two separate sources.

Borderline:
- **B4/single/117, B4/integer/24, B4/single/64:** m to cm conversion by hand beside fit full.
- **B4/single/111:** v = 340 m/s and a density typed as plain numbers.
- **B4/jee_advanced/55:** fit full with a continuous band reduced to two tones.
- **B4/single/102:** fit full, with both deciding facts tagged assumption.

Other honesty notes:
- Authors were on the whole more cautious than in run 5: 19 partial and 1 none out of 47, and several "partial" claims are stricter than needed (integer/19, single/175, single/49).
- **B4/jee_advanced/54:** `missing_in_source` lists a fact that the passage states.
- **B4/jee_main/11, B4/reasoning/7:** assume text does not match the scene (both disclosed in the answer file).

## Hypotheses

- **H1 (set D): mostly holds.**
  - 10 of 15 full coverage, 11 of 15 engine-derived matches, 14 of 15 with correct engine values that bear on the answer.
  - No silent wrong answer.
  - The one refusal (intensity on a moving ray, single/73) is clean.
  - The light/radar part fails: nothing was refused. Both radio problems ran on a gas medium with v = 3e8 m/s and gave the right classical values. No supersonic case occurred in the set.
  - Two misses come from reading, not physics: which instant the distances refer to (jee_advanced/63) and a stated fact overlooked (jee_advanced/54).
- **H2 (set S): holds for invented values, not for hand steps.**
  - 20 of 47 final scenes use `arbitrary:` (set S: mu, T, L, area, sound speed), and comparisons proved for every allowed value answered multiple/9, comprehension/12 and jee_advanced/37 directly.
  - The share of answers with a non-empty `hand_steps` did not fall: 20 of 47 (43%) against 31 of 80 (39%) in run 5.
  - What fell is the share where the hand step decided the answer: unverified 3 of 47 (6%) against 10 of 80 (12.5%), not-produced 2 of 47 (4%) against 8 of 80 (10%).
  - Numbers are still invented where `arbitrary` breaks the scene: time-dependent observables (comprehension/16, reasoning/15 moved to symbols), echo existence (jee_main/47), a comparison that turned NOT AVAILABLE (reasoning/9).
- **H3: confirmed only for tension set by mechanics.**
  - Tension from mechanics: 2 problems, both hand-typed (integer/23 Hooke, jee_advanced/25 buoyancy).
  - Composite resonators: the two cases in the sample worked without hand physics (integer/19 as three resonators with a length sum, jee_main/37 as a free-free rod with the node checked).
  - Sound at a boundary between media, and driven resonators: not exercised by this sample.

## Suspected engine defects

No wrong value was found. The items below are refusals or gaps.

1. **No guard on the medium: electromagnetic waves run as a gas.** `type: gas, v: 3e8 m/s` with f = 780e6 Hz or 5e9 Hz is accepted with no warning (single/33, integer/7). The classical result agrees with the book to the digits shown, so the scene looks fully verified while naming the wrong medium.
2. **Provable comparison refused (single/169).** `beat_frequency(...) < 4[Hz]` with one positive symbol inside an `abs` is "cannot decide", though both sign cases are negative. FORMAT.md says `abs` around unknowns is solved by sign cases; this does not extend to comparisons in `observe`.
3. **Arbitrary values break time-dependent and existence-dependent scenes.** A meeting time that depends on arbitrary mu, T makes every observable NOT AVAILABLE (comprehension/16 v1, reasoning/15 v1); scaling distances removes an echo (jee_main/47 v1). Authors fell back to symbols or fixed numbers. Reported by authors; I did not re-run the v1 files.
4. **`frequency(ray, t=...)` refused with an unknown speed** because the listener's side is undecidable (jee_main/21 v1); `emitted=0[s]` is the documented way, but the message did not lead the author there on the first attempt.
5. **Exact equality against rounded options.** `u == (1/4)[m/s]`, `L == 15.2[cm]`, `ratio == 1.22` all print False for the correct option (jee_main/11, jee_advanced/1, single/141). Correct, but a reader of the output sees four False options. There is no "nearest option" service.
6. **Emission and reception instants (jee_advanced/63).** The engine is exact for whichever instant is asked, and the two readings differ in the second decimal (8.24, 8.36) from the textbook's 8.13. The textbook value needs the source placed at emission and the listener at reception, which the author must build by hand (my probe typed the 1000 m path and 100/33 s).

## Transcription defects

- **B4/single/49:** option D prints "lambda/mu" (book defect, noted in the record).
- **B4/comprehension/11:** option C prints "Pmin" without the prime (noted).
- **B4/matrix/2:** Column II has no entry for the angular frequency 20 pi; the record explains p = 10 as the frequency in Hz.
- **B4/multiple/18, B4/single/33, B4/integer/7, B4/jee_advanced/1:** the source omits a needed value or rule (speed of sound, c, end correction 0.3 d). The records say so and the authors flagged all four.
- **B4/jee_advanced/63:** the record's check uses instantaneous geometry and does not say which instant each distance refers to.
- No difference was found between any problem file and its corpus record in statement, figure or options. The Column II export fault of run 5 did not recur (matrix/2 carries both columns).

## Top gaps by layer

| # | Gap | Layer | Count | Problems |
|---|---|---|---|---|
| 1 | Media and quantities outside the model: electromagnetic waves, intensity heard by a moving listener or from a moving source, wave speed relative to a moving listener, heat exchange (adiabatic against isothermal) | physics | 6 | single/33, integer/7, single/73, reasoning/9, jee_advanced/54, reasoning/7 |
| 2 | Mechanics that sets string tension: Hooke/Young strain, buoyancy | assembly | 2 | integer/23, jee_advanced/25 |
| 3 | Pipe and tube set-up: end correction from the diameter, water levels against air-column length, pressure at a point as P0 +/- amplitude | assembly | 3 | jee_advanced/1, jee_main/5, comprehension/11 |
| 4 | Deciding and comparing: for-all comparison through `abs`, "iff" between two symbols, nearest option, list spacing and arithmetic on lists, "slightly increased" as a limit, d omega/dk | maths | 8 | single/169, single/49, jee_main/11, jee_advanced/1, single/141, jee_main/5, jee_advanced/4, jee_advanced/21 |
| 5 | Arbitrary values with time-dependent or existence-dependent results; unknown speeds with `t=` | maths | 5 | comprehension/16, reasoning/15, jee_main/47, reasoning/9, jee_main/21 |
| 6 | Reading the source: emission against reception instant, a stated fact overlooked, "first maximum", unstated mode or direction | authoring | 5 | jee_advanced/63, jee_advanced/54, single/11, single/102, multiple/4 |
| 7 | Stand-ins claimed as full, option letters omitted, assume text not matching the scene | authoring | 5 | single/33, jee_main/47, integer/19, jee_main/11, reasoning/7 |
| 8 | Things the format cannot state: a continuous frequency band, an arbitrary profile F(wt - kx) in observables, dimensional consistency of a formula, figure shapes without scale, output units (cm), MHz | format | 7 | jee_advanced/55, multiple/4, single/90, comprehension/12, integer/19, single/117, single/33 |
| 9 | Statement-explanation links and judgement keys | teaching | 4 | reasoning/7, reasoning/9, reasoning/15, single/169 |

## Comparison with run 5

- **Wrong engine values:** 1 in run 5 (`vy` at a pulse corner), 0 here. No scene in run 6 asked `vy` or `slope` exactly at a corner, so this run does not test that fix.
- **Engine-derived matches:** 39 of 47 (83%) against 62 of 80 (78%). Set D alone: 11 of 15 (73%); set S: 28 of 32 (88%).
- **Answer decided by hand:** unverified 6% against 12.5%; not-produced 4% against 10%.
- **Full coverage:** 68% against 70%, unchanged.
- **Misrepresentation:** 1 against 0. It comes from a new kind of problem (radio waves in a Doppler set) rather than from a regression.
- **Run 5's top gap** (symbolic scale and ratio questions needing invented values, 13 problems) is largely closed by `arbitrary:` and proved comparisons. What replaced it is narrower: arbitrary values with time-dependent results (5) and deciding or comparing services (8).
- **Run 5's gaps 2 to 4** (composite resonators, sound at boundaries, tension from mechanics): only tension from mechanics recurred (2). The sample did not contain the other two in a form that needed hand physics.
- **Book-key disputes:** 2 of 47 against 5 of 80.
