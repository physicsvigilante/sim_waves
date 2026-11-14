# Run 3 grades (independent grader)

Graded per `eval/SCORECARD.md` on A, B, C, E (D not graded: no teacher task). Every final scene was re-run;
result bases read from the engine (`exact`/`proved`/`sampled`/`counterexample`). "hand" = done by the author, not by an engine observable.
B abbreviations: v-proved = verified-proved, v-sampled = verified-sampled.

| id | A | B | C | E | note |
|---|---|---|---|---|---|
| 23/01/asc_004 | faithful | v-proved | partial | matches | Path difference encoded by hand as two x positions; no sources. Redundant facts re-state typed parameters. |
| 23/01/asc_005 | minor-deviation | wrong | partial | differs | Reflection phase not in source; author assumed none (declared) and forced an answer; key needs lambda/2 flip. 130 m path is hand geometry (sqrt in expression). No `given` tags. |
| 23/01/cnt_004 | minor-deviation | v-proved | partial | matches | Invented bound f < 840 Hz (tagged assumption); "stated" fact hides hand doubling 2 x 20 cm and equal amplitudes; `assume` describes a mid-shift fact that is not in the scene. 3 attempts. |
| 23/01/cnt_006 | faithful | unverified | unsupported | not-produced | Engine gave only lambda; 2d doubling and lambda/2 = 32.4 cm are hand (answer equals key). Honest partial claim. |
| 23/01/cnt_007 | faithful | v-proved | partial | differs-book-disputed | 1/9 vs key 9; corpus records the key as inverted (sign of path lag). "Nearly 1:2" taken exact (declared). 100.25 lambda typed as positions. |
| 23/01/dmt_004 | faithful | v-proved | partial | matches | b, c from engine; a (incoherent, 2 I0) hand; d by argument. Honest partial claim. Stray `c_amp` observable ignores the path. |
| 23/02/asc_004 | faithful | v-sampled | full | matches | "All particles" checked at 4 hand-picked points; node positions chosen by hand. Illustrative string values declared in `assume`. |
| 23/02/asc_006 | faithful | v-sampled | partial | matches | Kinetic energy not an observable: abs(vy) at one point as proxy; candidate instants hand-picked. Flatness at T/4 proved. |
| 23/02/asc_007 | faithful | v-proved | full | matches | Wavelength ratio sqrt(2) exact; "node spacing = lambda/2" is a hand relation (engine node_spacing at fixed length gave 1). |
| 23/02/asc_008 | faithful | v-proved | full | matches | w, k, a fixed to numbers (declared, scale-free). Option d proved, a-c counterexamples. |
| 23/02/bmc_005 | faithful | v-proved | partial | matches | Node at support proved; (c) from amplitudes at 4 points; (d) not engine-checked (no standing-wave intensity). Honest partial claim. |
| 23/02/cnt_004 | faithful | v-proved | partial | matches | Pulse replaced by a harmonic wave; equal tension assumed (both declared). |
| 23/02/cnt_005 | faithful | v-proved | partial | differs-book-disputed | 75 % vs key 25; corpus records key mismatch (25 is the reflected part). Boundary type invented but tagged; both branches give 3/4 (v3 re-run). 3 attempts. |
| 23/02/cnt_008 | faithful | v-proved | full | matches | Clean. |
| 23/03/asc_004 | misrepresented | unverified | full | not-produced | Final scene states 25 Hz beats (typo for 5 Hz) tagged `stated`; engine gives 1025 Hz. 205 is hand scaling (equals key). v1/v2 are real engine crashes (NaN comparison). Answer given as "205", not the letter. 3 attempts. |
| 23/03/asc_005 | faithful | v-proved | full | matches | Lengths 1 m / 0.75 m are an undeclared illustrative scale. |
| 23/03/asc_006 | faithful | v-proved | partial | matches | Node/antinode amplitudes exact; pluck/touch rule is hand. Honest partial claim. |
| 23/03/asc_008 | faithful | v-proved | full | matches | Answer file is not valid YAML (`[c] 500 m/s`). |
| 23/03/bmc_004 | minor-deviation | v-proved | full | matches | Dummy fact `1 == 1` tagged `stated`. Physics clean. |
| 23/03/cnt_006 | faithful | v-proved | full | matches | Resonance assumption declared. |
| 23/03/cnt_007 | faithful | v-proved | full | matches | "Interior nodes = n - 1" typed by hand (tagged assumption). Answer file has reasoning/friction swapped. |
| 23/03/cnt_008 | faithful | v-proved | full | matches | T = M g typed by hand (g = 9.8 assumed, cancels); hanging load tagged assumption although stated. |
| 23/04/asc_005 | faithful | v-proved | full | matches | Search bound hi = 119 cm is the author's (harmless). |
| 23/04/asc_006 | faithful | v-proved | full | matches | 20 kHz only in `assume`, not a tagged fact; comparison with the limit hand. Honest partial claim. |
| 23/04/asc_007 | faithful | v-proved | full | matches | Clean. |
| 23/04/bmc_005 | faithful | v-proved | full | matches | RULE BREACH: 6 attempts (v1-v5 rejected). Ratios exact; integer/odd test hand. |
| 23/04/bmc_006 | faithful | v-proved | full | differs | [b, d] vs key [b, c, d]. Corpus: option (c) "85 cm" is a unit misprint, key reads it as 85 Hz; engine f1 = 85 Hz supports that reading (borderline, key itself not disputed). Open-open exclusion is in an off-pattern probe file `v1oo`, not the final scene. Answer file fields swapped. |
| 23/05/asc_005 | faithful | v-proved | full | matches | Clean. |
| 23/05/asc_007 | faithful | v-proved | full | matches | Clean. |
| 23/05/asc_008 | faithful | v-proved | full | matches | Clean. |
| 23/05/asc_009 | faithful | unverified | partial | matches | 4 beats/s from engine; 1/(2 f_beat) is a hand relation typed into `observe`. Honest partial claim. |
| 23/05/asc_010 | faithful | v-proved | full | matches | Wax lowering tagged assumption. |
| 23/05/asc_012 | faithful | unverified | partial | matches | Beats 2 Hz from engine; ((a1+a2)/(a1-a2))^2 = 49 is hand, and it is what separates (a) from (b). Honest partial claim. y given unit m (source has none). |
| 23/05/cnt_004 | faithful | v-proved | full | matches | Exact 2.01 % vs key's first-order 2.0. |
| 23/05/cnt_005 | faithful | v-proved | full | matches | Clean; `max()` used for "higher pitch". |
| 23/05/cnt_006 | faithful | v-proved | full | matches | Clean. |

## Counts

| Dim | Grade | Count |
|---|---|---|
| A | faithful | 32 |
| A | minor-deviation | 3 |
| A | misrepresented | 1 |
| B | verified-proved | 29 |
| B | verified-sampled | 2 |
| B | unverified | 4 |
| B | wrong | 1 |
| C | full | 23 |
| C | partial | 12 |
| C | unsupported | 1 |
| E | matches | 30 |
| E | differs-book-disputed | 2 |
| E | differs | 2 |
| E | not-produced | 2 |

Of the 29 verified-proved, 9 still rest on a hand step outside the engine (01/asc_004, 01/cnt_004, 01/cnt_007,
01/dmt_004, 02/asc_007, 02/bmc_005, 03/asc_006, 04/asc_006, 04/bmc_005); the engine-computed part is exact.
RESULTS.txt marks 03/asc_004 wrong only for the answer form (205 vs c), but the number is not an engine result.

## TASK rule breaches
- 23/04/bmc_005: 6 attempts (limit 3). Author disclosed it.
- 23/04/bmc_006: extra probe file `v1oo.yaml` outside the v1/v2/v3 naming; part of the answer rests on it.
- 23/03/asc_004: budget spent, final scene knowingly carries a typo.
- No overwritten attempt files found (each version is a separate file; timestamps consistent).
- Minor: 03/asc_008 answer file is invalid YAML; 03/cnt_007 and 04/bmc_006 have reasoning/friction swapped; 03/bmc_004 dummy fact.

## engine_fit over-claims ("full" with key steps by hand)
1. 23/01/asc_005: reflected path by hand Pythagoras, and the answer is decided by an assumed reflection phase.
2. 23/04/bmc_005: which ratios are allowed modes (integer / odd) judged by hand.
3. 23/02/asc_006: kinetic energy never computed; one-point speed proxy at hand-picked instants.
4. 23/02/asc_007: node spacing = lambda/2 is the author's relation.
5. 23/03/cnt_007: interior-node count n - 1 typed by hand.
6. 23/03/cnt_008: tension = M g typed by hand.
7. 23/02/asc_004: "all particles" claim from 4 hand-placed sample points.
8. 23/01/asc_004, 23/01/cnt_007 (mild): path difference inserted by hand as positions.
9. 23/04/bmc_006 (mild): option (a) ruled out in a probe file, not in the final scene.

Honest partial claims: 01/cnt_004, 01/cnt_006, 01/dmt_004, 02/bmc_005, 03/asc_004, 03/asc_006, 04/asc_006, 05/asc_009, 05/asc_012.

## Capability gaps, ranked by problems blocked
| # | Missing capability | Count | Problems |
|---|---|---|---|
| 1 | Sources, path lengths and path differences as objects (two-source interference, reflectors/walls with reflection phase, tube paths, incoherent sources, "adjacent/first extremum" conditions) | 6 | 01/asc_004, 01/asc_005, 01/cnt_004, 01/cnt_006, 01/cnt_007, 01/dmt_004 |
| 2 | Standing-wave pattern observables: node/antinode positions and counts, "same phase over a region", pluck/touch | 4 | 02/asc_004, 02/asc_007, 03/asc_006, 03/cnt_007 |
| 3 | Mode counting/matching: count modes under a limit, test whether a frequency is an allowed mode of another resonator; `resonances()` cannot use solved unknowns or symbols | 2 | 04/asc_006, 04/bmc_005 |
| 4 | Beat envelope: max/min amplitude and intensity, time from max to min (`max_over` rejects two frequencies) | 2 | 05/asc_009, 05/asc_012 |
| 5 | Energy of a standing wave: kinetic energy, intensity vs position/time | 2 | 02/asc_006, 02/bmc_005 |
| 6 | Engine bug: `beat_frequency` with a resonator frequency and two unknowns in `given` crashes (Invalid NaN comparison) | 1 | 03/asc_004 |
| 7 | Hanging-mass tension on a resonator string (sonometer) | 1 | 03/cnt_008 |
| 8 | Pulse reflection/transmission at a junction | 1 | 02/cnt_004 |
| 9 | Notation: bracketed units inside YAML flow mappings fail to parse (cost an attempt) | 3 | 03/asc_005, 04/asc_005, 04/bmc_005 |
