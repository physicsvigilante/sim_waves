# LOG_B (batch B)

| id | attempts | engine_fit | answer |
|---|---|---|---|
| B4_integer_1 | 2 | partial | 60 degrees (hand-derived kinematic link) |
| B4_integer_17 | 1 | full | 250 m/s |
| B4_integer_25 | 1 | full | O2 314 m/s, He 972 m/s |
| B4_integer_5 | 3 | none | not determined (ambiguous wavelength family) |
| B4_jee_advanced_2 | 1 | full | B (10 g) |
| B4_jee_main_26 | 3 | full | B (40 cm) |
| B4_jee_main_30 | 1 | full | D (666 Hz) |
| B4_jee_main_36 | 1 | full | C (328 m/s) |
| B4_jee_main_42 | 1 | full | B (1:2) |
| B4_jee_main_44 | 1 | full | D (2 sqrt 2 s) |
| B4_matrix_7 | 1 | partial | A-q, B-p, C-p, D-r |
| B4_single_130 | 2 | partial | B (33 m, assumed 0.2 s) |
| B4_single_139 | 1 | full | B (0.5 m) |
| B4_single_182 | 2 | full | C (378 m/s) |
| B4_single_2 | 2 | full | A (105 Hz) |

## Three most common friction points
1. `nearest()` accepts only plain numbers: dimensional values and `x in unit` are refused (v1/v2 retries in 4 problems).
2. Unknown quantities inside positions/trig: unknown at a point list needs a unit-bearing entry (`"0[m]"` rejected, `0 m` accepted); unknown angles/wavelengths inside sine or oblique Doppler geometry are refused or ambiguous, forcing restating via k or coordinates.
3. Physics outside the engine: accelerating sources (integer_1), perceptual persistence (single_130), string intensity / volumetric energy density (matrix_7); ranges for arbitrary speeds must be given to stay subsonic.
