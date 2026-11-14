# LOG A

| id | attempts | engine_fit | answer |
|---|---|---|---|
| 11_01_001 | 1 | full | y = 0.06 sin(25 pi x - 7500 pi t); lam 0.08 m, f 3750 Hz |
| 11_01_002 | 3 (+ stray empty v4 file) | partial | ambiguous; 75 m/s if lam > 0.1 m |
| 11_01_003 | 1 | partial | rigid shift at +v |
| 11_01_004 | 1 | full | verified; v = w/k, +x |
| 11_01_005 | 1 | full | 0.12 m |
| 11_01_006 | 3 | partial | d |
| 11_01_007 | 1 | full | 3 cm/s pulse, peak 2 cm |
| 11_01_008 | 1 | partial | y = 0.02 cos(100x-10t); pi/50 m |
| 11_01_009 | 1 | full | A 2 cm, 100 Hz, 30 cm, 30 m/s |
| 11_01_010 | 2 | full | -x, 2 m/s, 2 m |
| 11_01_011 | 1 | full | 4 m/s, +x |
| 11_01_012 | 1 | full | +x / -x at 4/3; cancel t=0.75 s, x=1 m |
| 11_02_001 | 2 | none | 2 sqrt(2 l0/g) (engine wrong, see below) |
| 11_02_002 | 2 | partial | (1/(15 alpha))((mu0+alpha l)^1.5 - mu0^1.5) |
| 11_02_003 | 1 | full | 79.2, 62.6 m/s |
| 11_02_004 | 2 | partial | 0.5 rho w^2 A^2 cos^2(kx-wt) |
| 11_02_005 | 2 | full | 0.104 m |
| 11_02_006 | 3 | partial | 2e-5 m |
| 11_02_007 | 1 | partial | 0.47 s |

## Friction (top 3)
1. Non-uniform strings: mu(s) on a hanging string silently gets the wrong tension (g*mu0*s^2 instead of half); no integrator or time-of-flight observable, front() is wrong for non-hanging non-uniform strings.
2. Missing physics: no elastic (Y/strain) or mass-spring oscillator, no energy density; times (L/v), extensions done by hand.
3. Unknowns: wavelength inside sin() refused (must use k), infinite families can't be bounded without a spare attempt; tension: free fails with 'need area?'; amplitude() of pulses and boundedness/finite checks unavailable; limit() to oo crashes with traceback.
