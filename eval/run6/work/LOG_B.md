# LOG_B (batch B)

| id | attempts | engine_fit | answer |
|---|---|---|---|
| B4_integer_7 | 1 | full | 30 m/s |
| B4_jee_advanced_1 | 1 | partial | B (15.2 cm) |
| B4_jee_advanced_25 | 1 | partial | A |
| B4_jee_main_11 | 1 | full | D (1/4 m/s) |
| B4_jee_main_15 | 1 | full | D (2.1 m) |
| B4_jee_main_21 | 2 | full | D (12, 18) |
| B4_jee_main_5 | 3 | partial | C (2200 Hz) |
| B4_jee_main_54 | 3 | full | A (6.25 N) |
| B4_multiple_18 | 2 | full | [a, c] (v = 330 m/s assumed) |
| B4_multiple_33 | 1 | full | [a, b, d] |
| B4_multiple_4 | 1 | partial | [a, b] |
| B4_single_141 | 1 | full | B (1.22 f) |
| B4_single_169 | 1 | partial | B (decrease) |
| B4_single_175 | 1 | full | A (4.0 s) |
| B4_single_49 | 1 | partial | A |
| B4_single_90 | 1 | partial | D |

## Three most common friction points
1. Quantities the engine cannot take as input or compare: lists from resonances() cannot enter arithmetic or given (jee_main_5), no iff/comparison between two symbols (single_49), no for-all decision through abs (single_169).
2. Physics not modelled, so numbers were typed by hand: buoyancy (advanced_25), end-correction rule 0.3 d (advanced_1), EM / water-surface media (integer_7, single_175), dimensional consistency of formulas (single_90).
3. Doppler with unknown speeds: frequency(..., t=) is refused when the side is undecidable, so emitted=0[s] and arbitrary distances had to be added; also tension: free is not observable (main_54).
