| id | attempts | engine_fit | answer |
|----|----------|------------|--------|
| R1 | 2 | full | 2 |
| R2 | 2 | partial | A, C |
| R3 | 2 | partial | 74.2 dB |

Friction points:
1. Points defined by coordinates only, no placement by stated distances (R3), so geometry was hand-computed.
2. A stated bound on a symbol (L > 0.40 m) breaks diff(), at() and resonances(vary=) on that symbol (R2); also no boolean/range comparison of observables.
3. No interior clamp/support element for resonators (R1; used node_at filter), and arbitrary vs symbols declaration is easy to get wrong (R1 v1).
