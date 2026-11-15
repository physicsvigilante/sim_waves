| id | attempts | engine_fit | answer |
|----|----------|-----------|--------|
| R1 | 2 | partial | a 1.2 mm; b 3.0 mm at x=0.70 m |
| R2 | 2 | partial | a 0.20 m; b x=0.70 m; c 1.78 mJ (hand) |
| R3 | 3 | partial | a 7/60 s; b 1.726 m |

Friction points:
1. No observables for pulse geometry: position of the maximum, spatial extent, energy (power() rejects pulses); had to probe y at grid points / compute by hand.
2. Observables cannot be chained (e.g. front(p, t=travel_time(...)/2)); half-times typed by hand, which caused a typo attempt in R3.
3. Pulse launching for horizontal non-uniform string not documented (from/toward use lower_end/up in doc; left_end/right worked).
