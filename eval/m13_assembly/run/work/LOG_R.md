| id | attempts | engine_fit | answer |
|----|----------|-----------|--------|
| R1 | 1 (v1) | full | 84 Hz |
| R2 | 2 (v1, v2) | partial | 20 ms |
| R3 | 1 (v1) | full | A, B, D |

Friction points:
1. period() is not available for resonator modes; had to write 1/frequency myself (R2, hand step).
2. A solved unknown cannot be reported with `in <unit>` (R1 'f0 in Hz' refused); must read SI output.
3. Scenes needing no given facts/unknowns (R2, R3) and the resonance-at-a-single-frequency check (resonances with lo == hi, plus a dummy symbol fs) feel awkward; testing a specific frequency is not a first-class observable.
