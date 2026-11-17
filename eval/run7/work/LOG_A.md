# Batch A log

| id | attempts | engine_fit | answer |
|---|---|---|---|
| B4_integer_13 | 1 | partial | (a) 2500 Hz, (b) 320 m |
| B4_integer_4 | 1 | full | 1029.65 Hz |
| B4_jee_advanced_13 | 1 | full | B |
| B4_jee_advanced_20 | 1 | partial | B (engine cannot decide; 0.2 and 0.4 s also plausible) |
| B4_jee_advanced_49 | 1 | partial | B, C |
| B4_jee_main_23 | 1 | full | D |
| B4_jee_main_7 | 1 | partial | D |
| B4_multiple_1 | 1 | partial | A, D |
| B4_reasoning_14 | 2 | full | D |
| B4_single_106 | 1 | full | D |
| B4_single_147 | 2 | partial | A (options garbled in source) |
| B4_single_159 | 1 | partial | D (exact 8.33 % is not an option) |
| B4_single_166 | 1 | full | C |
| B4_single_55 | 2 | partial | C |
| B4_single_97 | 1 | full | D |

## Three most common friction points
1. Unstated quantities (sound speed, g, distances) force `arbitrary` values; a speed written as a fraction of an unstated v, or symbolic v with u, breaks under scaling (B4_single_147, B4_integer_13).
2. Wording about instants/events ("when the source is closest", "after crossing", "slightly changed") has to be turned into explicit emission/reception times or extra copies of the scene computed partly by hand.
3. Answer matching: no km/h or um units, nearest() refuses exact sqrt expressions, and approximations (v_s << v) or a repeated pulse train / incline statics cannot be expressed at all.
