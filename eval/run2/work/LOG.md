# Run 2 LOG

| id | attempts | engine_fit | answer |
|---|---|---|---|
| 22_01_asc_005 | 2 | full | c |
| 22_01_asc_006 | 1 | full | c |
| 22_01_bmc_005 | 2 | partial | a, b, d |
| 22_01_bmc_006 | 1 | partial | a, b, c |
| 22_01_bmc_007 | 1 | full | b, c, d |
| 22_01_cnt_006 | 2 | full | 16 m |
| 22_02_asc_006 | 1 | full | b |
| 22_02_asc_007 | 2 | partial | c |
| 22_02_asc_008 | 2 | full | d |
| 22_02_asc_009 | 3 | full | c |
| 22_02_bmc_004 | 1 | full | a, b, c, d |
| 22_02_bmc_005 | 2 | full | a, c |
| 22_02_cnt_005 | 2 | partial | a/b = 3X/(2*pi), depends on X (under-determined) |
| 22_03_bmc_006 | 1 | full | a, c, d |
| 22_03_cnt_004 | 1 | full | 3 |
| 22_03_cnt_006 | 1 | full | 511.64 W (about 512 W) |

Note: attempts counted as scene files written; asc_005 and cnt_006 v2 only removed a pointless fact from v1 (not an engine rejection).

## Three most common friction points
1. Conceptual statements ("depends on medium", "is the shape at an instant", phase difference between y, v, a) have no direct observable; I had to choose a test (differentiate wrt a symbol, quarter-period shift with equivalent()) and the reading of the option is my choice.
2. Figure reading: points are placed by hand as fractions of lambda, symbolic bounds like 0 < phi < 90 deg are refused as undecidable (sample values used), and equivalent() against option formulas with decimals can exceed the 120 s limit (asc_009).
3. Things not in the travelling-wave form or without an engine notion: amplitude varying as 1/x (cnt_005), a single oscillation without x (modelled as a wave at x = 0), intensity on a string (used power), and phase wrap vs unwrapped differences.
