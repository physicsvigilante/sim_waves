| id | attempts | engine_fit | answer |
|----|----------|------------|--------|
| R1 | 1 | full | a 0.40 m; b 0.0384 J; c 0.0104 J; d 0.016 J/m |
| R2 | 3 | partial | a 0.60 m; b 5.55e-3 J; c 1.67e-2 J; d 2.78e-2 J/m |
| R3 | 2 | full | a 0.0987 J/m; b 0.0395 J; c 1.21e-3 J |

Friction points:
1. No maximiser for a non-sinusoidal density over x (R2d): max_over fails on pulses, peak() takes only waves.
2. `tension: free` is not resolved from a harmonic wave's omega and k; needed an unknown T plus a speed(rope)==speed(y1) fact (R3).
3. Piecewise-linear and windowed shapes must be built from step() by hand; sign convention y = A sin(kx - wt) must be converted to phase = pi manually.
