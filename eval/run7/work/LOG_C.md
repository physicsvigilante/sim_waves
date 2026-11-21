# LOG_C (batch C)

| id | attempts | engine_fit | answer |
|---|---|---|---|
| B4_comprehension_20 | 2 | partial | C |
| B4_comprehension_42 | 1 | full | A |
| B4_comprehension_47 | 1 | partial | A |
| B4_jee_advanced_23 | 1 | partial | A |
| B4_jee_main_19 | 3 | partial | D |
| B4_multiple_26 | 1 | partial | [A, D] |
| B4_multiple_28 | 1 | partial | [A, B, D] |
| B4_reasoning_19 | 1 | partial | C |
| B4_single_10 | 1 | full | D |
| B4_single_110 | 1 | full | A |
| B4_single_156 | 3 | partial | B |
| B4_single_26 | 2 | full | C |
| B4_single_52 | 3 | none | D |
| B4_single_85 | 1 | full | D |

Top friction points:
1. Picking among rounded options: nearest() refuses solved unknowns and needs units on options (cost attempts in jee_main_19, single_26, single_156); results depending on an arbitrary value are unavailable, so small-parameter approximations (single_156, single_52) are hard.
2. Approximation/limit questions (small dl, v<<c): limit() fails with arbitrary scalings, and symbolic facts like dl < L/2 are undecidable, so the sonometer beat (single_52) could not be run.
3. Qualitative concepts without observables: compression/rarefaction (pressure at a point), signed reflection coefficient, generic medium change; each needed a hand link (slope sign, y ratio, string junction stand-in).
