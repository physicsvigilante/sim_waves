| id | attempts | engine_fit | answer |
|----|----------|-----------|--------|
| R1 | 1 (v1) | partial | a 1489 m/s; b 393 W; c 552.5 Pa; d 1.44e-8 m, 104.0 dB |
| R2 | 3 (v1 rejected, v2, v3) | partial | a 6.99e10 Pa; b 5089 m/s; c 3180 Hz; d 0.800 m |
| R3 | 2 (v1 parse error on mW, v2) | partial | a 75.1 dB; b 0.163 Pa; c 87.3 dB |

Friction points:
1. No input for compressibility or static-test Young's modulus; stress/strain and 1/kappa written by hand in medium fields.
2. Unit "mW" not accepted; rod medium with length forces resonator length to match (second rod needed its own medium).
3. pressure_amplitude takes one ray only; the same sources cannot be switched between coherent and incoherent, so they were duplicated.
