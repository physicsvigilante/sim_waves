# Known issues: confirmed defects ledger

Every confirmed defect stays here until a merged milestone closes it. Each has one of three actions:
- **fix now**;
- **fence now** (a sound refusal);
- a required repair in a **named milestone**.

**No known wrong answer is waived** (CLAUDE.md, review policy points 3 and 11). Any milestone that touches a listed path must repair or fence the defect.

**Severity**, as in the error hunts:
- **1** a wrong value accepted;
- **2** an invented fact;
- **3** a wrong refusal of a valid scene;
- **4** a wrong test grade.

**Evidence:** findings H17-x and D1–D5 were reproduced on the engine (Windows, SymPy 1.12) on 2026-11-23, at `4aeb3e4`, as predicted. D1-1 was refused correctly, but with an incomplete message. G1 and G2 are confirmed from the source only and must be reproduced before a fix is credited. G3 comes from the m15a reserved run.

Opened 2026-11-25 from the project review (`eval/project_review_2026-11/DECISIONS.md`). Baseline `7244bb6`.

| ID | Issue | Defect | Sev | Action |
|---|---|---|---|---|
| D3-6 | [#21](https://github.com/physicsvigilante/sim_waves/issues/21) | A circular listener's arrival time comes from a bisection that moves the wrong end: 1 s accepted where the answer is 0.25 s | 1 | fix now (fence bundle) |
| D3-2 | [#21](https://github.com/physicsvigilante/sim_waves/issues/21) | Sound `travel_time` ignores wind and loses direction (18/17 s both ways; the answers are 1 s and 9/8 s) | 1 | fence now; full model in M4 |
| D3-1 | [#21](https://github.com/physicsvigilante/sim_waves/issues/21) | `ay` reports zero acceleration at a triangular pulse's corner, where it does not exist | 1 | fence now; M4 |
| D3-3 | [#21](https://github.com/physicsvigilante/sim_waves/issues/21) | `phase(ray, t=)` gives a phase before any sound has arrived | 2 | fence now; M4 |
| D2-3 | [#20](https://github.com/physicsvigilante/sim_waves/issues/20) | `width()` invents the support of a profile written with an unspecified function | 2 | fence now; M3 |
| D4-5 | [#22](https://github.com/physicsvigilante/sim_waves/issues/22) | An equivalent spelling of degC loses the 273.15 K offset | 1 | fence now; M2 |
| G1 | debates #1 | The harness grades every symbolic comparison PASS: it tests the non-empty `(truth, basis)` pair, not its first element. About 36 expectations in about 22 scenes are exposed (a static estimate) | 4 | M1 |
| D4-10 | [#22](https://github.com/physicsvigilante/sim_waves/issues/22) | Expected-value conversion loses Celsius offsets and accepts incompatible units | 4 | M1 |
| D4-11 | [#22](https://github.com/physicsvigilante/sim_waves/issues/22) | A tolerance floor in display units lets a 100× error pass; the grade changes with the display unit | 4 | M1 |
| D5-1 | [#23](https://github.com/physicsvigilante/sim_waves/issues/23) | Percentage tolerances can grade a thousandfold-wrong reference as PASS | 4 | M1 |
| D5-2 | [#23](https://github.com/physicsvigilante/sim_waves/issues/23) | A frequency reference written in metres is graded PASS | 4 | M1 |
| D5-3 | [#23](https://github.com/physicsvigilante/sim_waves/issues/23) | A correct Celsius expectation is converted twice and graded FAIL | 4 | M1 |
| H17-3 | [#17](https://github.com/physicsvigilante/sim_waves/issues/17) | A symbol's recorded unit is ignored in facts and expressions | 1 | M2 |
| D4-1 | [#22](https://github.com/physicsvigilante/sim_waves/issues/22) | The absence of a contradiction is treated as proof of the requested output unit | 1 | M2 |
| D4-2 | [#22](https://github.com/physicsvigilante/sim_waves/issues/22) | `at()` accepts seconds as a value for a bounded length | 1 | M2 |
| D4-3 | [#22](https://github.com/physicsvigilante/sim_waves/issues/22) | A trailing field unit skips the unit check inside the field's own expression | 1 | M2 |
| D4-4 | [#22](https://github.com/physicsvigilante/sim_waves/issues/22) | Range services accept limits of the wrong dimension | 1 | M2 |
| D4-6 | [#22](https://github.com/physicsvigilante/sim_waves/issues/22) | `equivalent()` proves a length equal to a time | 1 | M2 |
| D4-7 | [#22](https://github.com/physicsvigilante/sim_waves/issues/22) | The angular-frequency guard refuses an expression already converted to cycles | 3 | M2 |
| D4-8 | [#22](https://github.com/physicsvigilante/sim_waves/issues/22) | `frequency_of` and time derivatives lose a determinable result dimension | 3 | M2 |
| D4-9 | [#22](https://github.com/physicsvigilante/sim_waves/issues/22) | Output conversion accepts fewer unit spellings than the unit parser | 3 | M2 |
| D5-4 | [#23](https://github.com/physicsvigilante/sim_waves/issues/23) | Node position lists cannot be converted to cm or mm | 3 | M2 |
| H17-4 | [#17](https://github.com/physicsvigilante/sim_waves/issues/17) | A solved emission-start time is still treated as unknown | 3 | M2 |
| D1-5 | [#19](https://github.com/physicsvigilante/sim_waves/issues/19) | Field domain conditions are checked after uniqueness, giving a false "ambiguous" | 3 | M2 |
| D1-6 | [#19](https://github.com/physicsvigilante/sim_waves/issues/19) | Phase extraction ignores an already-solved amplitude sign | 3 | M2 |
| D2-4 | [#20](https://github.com/physicsvigilante/sim_waves/issues/20) | `harmonics()` refuses a cut-off the scene has already solved | 3 | M2 |
| D2-5 | [#20](https://github.com/physicsvigilante/sim_waves/issues/20) | `width()` searches a symbolic pulse scale after it has been solved | 3 | M2 |
| G2 | debates #1 | An observation that is itself refused can leave a harmonic record that makes the whole scene "inconsistent" (source trace; needs reproduction) | 3 | M2 |
| H17-1 | [#17](https://github.com/physicsvigilante/sim_waves/issues/17) | `resonances()` silently drops a physical higher mode | 1 | M3 |
| H17-2 | [#17](https://github.com/physicsvigilante/sim_waves/issues/17) | Ray maxima and minima omit periodic branches | 1 | M3 |
| D1-2 | [#19](https://github.com/physicsvigilante/sim_waves/issues/19) | A symbolic coefficient hides a degenerate branch, inventing a unique amplitude | 1 | M3 |
| D1-3 | [#19](https://github.com/physicsvigilante/sim_waves/issues/19) | A solved harmonic is accepted without proving it is a whole number | 1 | M3 |
| D2-1 | [#20](https://github.com/physicsvigilante/sim_waves/issues/20) | Extremum search misses finite corners; a beat-envelope minimum becomes its maximum | 1 | M3 |
| D2-2 | [#20](https://github.com/physicsvigilante/sim_waves/issues/20) | Ray extrema miss a whole range of phase orders at a corner | 1 | M3 |
| D1-4 | [#19](https://github.com/physicsvigilante/sim_waves/issues/19) | Fractional phase multipliers create invalid candidates before the ambiguity decision | 3 | M3 |
| D1-7 | [#19](https://github.com/physicsvigilante/sim_waves/issues/19) | An integer harmonic fixed by a frequency band is reported as undetermined | 3 | M3 |
| D1-1 | [#19](https://github.com/physicsvigilante/sim_waves/issues/19) | Refused correctly as ambiguous, but the list of possible values shown is incomplete | — | M3 |
| G3 | m15a RESULT | The numerical peak fallback printed 0.999999911344 for a peak that is exactly 1, with no stated precision | 1 | M3 |
| H17-5 | [#17](https://github.com/physicsvigilante/sim_waves/issues/17) | Exact cancellation makes string energy unavailable, though a zero field has zero energy | 3 | M4 |
| D3-4 | [#21](https://github.com/physicsvigilante/sim_waves/issues/21) | Two paths from one random-phase source lose their valid relative phase | 3 | M4 |
| D3-5 | [#21](https://github.com/physicsvigilante/sim_waves/issues/21) | `distance()` wrongly applies a Doppler frequency-jump refusal to a position | 3 | M4 |
