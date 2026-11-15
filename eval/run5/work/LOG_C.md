# Batch C log

| id | attempts | engine_fit | answer |
|---|---|---|---|
| B4_comprehension_22 | 1 | partial | b |
| B4_integer_10 | 1 | full | 6 dB |
| B4_integer_20 | 1 | full | x = 4 |
| B4_jee_advanced_14 | 2 | partial | b |
| B4_jee_advanced_38 | 1 | partial | b, d |
| B4_jee_advanced_8 | 1 | partial | d |
| B4_jee_main_16 | 1 | full | b |
| B4_jee_main_33 | 2 | full | d |
| B4_jee_main_55 | 3 | partial | c (ambiguous vs d) |
| B4_multiple_13 | 2 | full | a, b, c, d |
| B4_multiple_23 | 1 | full | a, d |
| B4_reasoning_10 | 1 | partial | a |
| B4_single_100 | 1 | full | c |
| B4_single_123 | 1 | full | b (options lack 17 dB) |
| B4_single_136 | 1 | full | a |
| B4_single_152 | 2 | full | c |
| B4_single_30 | 3 | full | d |
| B4_single_58 | 1 | full | c |
| B4_single_66 | 1 | partial | b |
| B4_single_92 | 2 | full | c |

## Three most common friction points
1. Unknowns need to be positive and ordered for several services: travel_time and `n-1` frequency refuse undecidable signs; two unknowns inside sound_level() refused; tension: free hides tension and energy (need an explicit unknown T plus cross-check).
2. Shaped-pulse sums and corners: sum of two shaped pulses with corners was refused for energy; given-wave formulas needed (positions written by hand).
3. Missing physics objects: no interface between sound media, no pipe-end reflection for pulses, no tube geometry, no rms molecular speed, no 3-component beat/loudness envelope.
