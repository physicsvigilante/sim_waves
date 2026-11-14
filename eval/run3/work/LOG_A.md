# LOG batch A

| id | attempts | engine_fit | answer |
|---|---|---|---|
| 23_01_asc_004 | 1 | full | [d] |
| 23_01_asc_005 | 1 | full | [b] |
| 23_01_cnt_004 | 3 | partial | 420 Hz |
| 23_01_cnt_006 | 1 | partial | 32.4 cm |
| 23_01_cnt_007 | 1 | full | 1/9 |
| 23_01_dmt_004 | 1 | partial | a->s, b->r, c->q, d->r |
| 23_02_asc_004 | 1 | full | [b] |
| 23_02_asc_006 | 1 | full | [d] |
| 23_02_asc_007 | 1 | full | [b] |
| 23_02_asc_008 | 1 | full | [d] |
| 23_02_bmc_005 | 1 | partial | [b, c] |
| 23_02_cnt_004 | 1 | full | 2 |
| 23_02_cnt_005 | 3 | full | 75 % |
| 23_02_cnt_008 | 1 | full | 9 |
| 23_03_asc_004 | 3 | partial | 205 |
| 23_03_asc_005 | 2 | full | [d] |
| 23_03_asc_006 | 1 | partial | [a] |
| 23_03_asc_008 | 1 | full | [c] 500 m/s |

Notes: 23_03_asc_004 v3 contains a typo of mine (5 Hz written as 25 Hz) and the revision budget was spent; the answer 205 is from scaling, not an engine result.

## Most common friction points
1. Path differences, reflectors and two-source interference have no objects: sources, walls and tube paths had to be faked by evaluating one wave at two distances (and doubling distances or taking sqrt by hand), which is geometry done outside the engine (23_01_asc_004, asc_005, cnt_004, cnt_006, cnt_007, dmt_004).
2. "Adjacent" / "first" conditions cannot be expressed: cnt_004 gave an infinite periodic family and needed an invented bound; cnt_005 was ambiguous in the sign of the impedance step.
3. Engine robustness and notation: beat_frequency with unknowns inside given crashed (sympy NaN comparison, 23_03_asc_004), and a bracketed unit inside a YAML flow mapping failed to parse. Also pulses, incoherent sources, kinetic energy/intensity and pluck/touch have no observables.
