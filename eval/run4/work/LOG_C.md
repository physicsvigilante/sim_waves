# LOG batch C

| id | attempts | engine_fit | answer |
|---|---|---|---|
| 11_04_001 | 1 | partial | a: 0.283 sin(x-3t+pi/4); b: phi = 1.287 rad |
| 11_04_002 | 1 | partial | 1/16 |
| 11_04_003 | 1 | full | 5A/6, phase -0.6435 rad |
| 11_04_004 | 2 | partial | 1440 Hz |
| 11_04_005 | 1 | partial | 26.5; phase 0.714 rad |
| 11_04_006 | 1 | partial | antiphase; 8.2e-5 W/m^2 |
| 11_04_007 | 1 | partial | n*188.3 Hz, n=1..106 |
| 11_04_008 | 1 | partial | a: n*1003 Hz; b: (n+1/2)*1003 Hz |
| 11_04_009 | 2 | partial | 17.5 cm |
| 11_04_010 | 3 | partial | a: 3 m; b: 0.60 m (hand; minima() failed) |
| 11_04_011 | 3 | full | 4:2:0 |
| 11_04_012 | 2 | partial | hyperbola x^2/15.9 - y^2/9.1 = 1 |
| 11_05_001 | 2 | partial | 4.77 Hz, 0.2 cm, 60 cm/s, 10.1 cm/s |
| 11_05_002 | 1 | full | a: 144 cm; b: 17 Hz |
| 11_05_003 | 3 | partial | 2.56 mm; 4 cm, 200 cm/s; 0.765 m/s; 5 loops |
| 11_05_004 | 2 | partial | a: 707 Hz (hand); b: 11 Hz |
| 11_05_005 | 1 | full | bridges at 72 and 96 cm |
| 11_05_006 | 1 | full | 2.14 m |
| 11_05_007 | 3 | partial | 96 % |

## Most common friction points
1. Cannot get a closed relation or a family from the engine (families, loci such as x-y hyperbola, "n times f1"): lists cannot be indexed, only min/max/count; patterns were read by hand.
2. Unit and convention traps: x in equivalence checks is SI metres even when the wave uses cm; phases come back in the sine convention (cos waves, book forms need translating); sources accept only f, not wavelength.
3. Symbolic geometry is brittle: symbols need values or sign facts (R > 2.5 undecidable, sqrt sign), and minima() failed for a varied wall/source position (11_04_010) while maxima() worked; longitudinal rods unsupported (11_05_004a).
