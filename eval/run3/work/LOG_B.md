# LOG B

| id | attempts | engine_fit | answer |
|---|---|---|---|
| 23_03_bmc_004 | 1 | full | c, d |
| 23_03_cnt_006 | 1 | full | 5 cm |
| 23_03_cnt_007 | 2 | full | 200 m/s |
| 23_03_cnt_008 | 2 | full | 25 kg |
| 23_04_asc_005 | 2 | full | d (45 cm) |
| 23_04_asc_006 | 2 | partial | c (6 overtones) |
| 23_04_asc_007 | 2 | full | c (880 Hz) |
| 23_04_bmc_005 | 6 (limit exceeded; v1-v5 errors) | full | b, d |
| 23_04_bmc_006 | 1 (+ open-open probe file) | full | b, d (c has unit misprint) |
| 23_05_asc_005 | 1 | full | b (94.9 cm) |
| 23_05_asc_007 | 1 | full | c (516 Hz) |
| 23_05_asc_008 | 1 | full | c (103 Hz) |
| 23_05_asc_009 | 1 | partial | c (1/8 s) |
| 23_05_asc_010 | 1 | full | c (259 Hz) |
| 23_05_asc_012 | 2 | partial | b |
| 23_05_cnt_004 | 1 | full | 2.01 % |
| 23_05_cnt_005 | 1 | full | 10 Hz |
| 23_05_cnt_006 | 1 | full | 0.01 kg/m |

## Friction points
1. Resonators and hanging loads: tension from a hanging mass has no direct form; resonances() needs numeric values and cannot see solved unknowns; tension: free is refused by a string resonator. (bmc_005, cnt_008)
2. Counting or comparing against a limit (audible range) and beat envelopes (max/min, max to min time) are not observables; max_over rejects two frequencies. (asc_006, asc_009, asc_012)
3. Symbols vs unknowns: a fact with only symbols is "over-specified", so quantities fixed by a given must be declared unknowns; speed of a resonator is only reachable via the medium. Also unquoted "[cm]" expressions in YAML flow mappings need quoting.
