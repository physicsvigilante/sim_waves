# Run 1 log

| id | attempts | engine_fit | answer |
|---|---|---|---|
| 22_01_asc_005 | 1 | full | c |
| 22_01_asc_006 | 3 | full | c |
| 22_01_bmc_005 | 1 | partial | a, b |
| 22_01_bmc_006 | 1 | partial | a, b |
| 22_01_bmc_007 | 1 | full | b, c, d |
| 22_01_cnt_006 | 1 | full | 16 m |
| 22_02_asc_006 | 3 (v2 was my error, v3 final) | full | b |
| 22_02_asc_007 | 1 | partial | c |
| 22_02_asc_008 | 3 (all failed) | none | d |
| 22_02_asc_009 | 1 | full | c |
| 22_02_bmc_004 | 2 | full | a, b, c, d |
| 22_02_bmc_005 | 1 | full | a, c |
| 22_02_cnt_005 | 3 | partial | a/b = 3x/(2 pi), 3/(2 pi) = 0.477 for x = 1 m |
| 22_03_bmc_006 | 1 | full | a, c, d |
| 22_03_cnt_004 | 1 | full | 3 |
| 22_03_cnt_006 | 1 | full | 511.64 W (1296 pi^2/25) |

## Three most common friction points
1. Symbols cannot be bounded or ordered in `given` (e.g. `xB < lam/4`, `0 < phi < pi/2`), and trigonometric unknowns (a point at a given height) cannot be solved; scenes needed sample values or failed (asc_008, asc_007).
2. No predicate for the questions options really ask: "is a travelling wave" (a rejected wave aborts the whole scene, so each had to be tried alone), "same phase mod 2 pi", "phase difference between two signals", "depends on medium"; figure geometry (zero crossings, point labels) is entered by hand in `assume`.
3. Waves that are not fixed-shape travelling waves (amplitude a/x, standing waves) get no velocity/speed; also observe table vs engine mismatch (`direction` is listed but unknown), and over-specified `given` with no unknowns is rejected.
