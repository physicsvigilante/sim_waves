# Milestone 8 (energy on strings, pulse width): result

## Transfer evidence (reserved cases)
- **Setup:** three problems by a separate agent (Opus, fresh context, prompted strictly
  with the PLAN scope). Keys were checked by a closed form and by numerical integration.
  The developer did not read them before the freeze (`run/FROZEN.md5`).
- **Author:** a fresh Claude Sonnet agent, given FORMAT.md and examples only.
- **Grading:** by the developer after the run (not independent; numeric parts only).

| Case | Structure | Attempts | Key match (all parts) | Hand steps | Production change needed |
|---|---|---|---|---|---|
| R1 | asymmetric triangle pulse: width, total energy, kinetic energy of a stretch at 20 ms, potential density at a point | 1 | yes: 0.40 m; 0.0384 J; 0.0104 J; 0.016 J/m | none | none |
| R2 | raised-cosine pulse, heavy to light string: transmitted width, reflected and transmitted energy, largest kinetic density | 3 | yes: 0.60 m; 5.55e-3 J; 1.67e-2 J; 2.78e-2 J/m | (d) the maximum over x found by sampling; the instant chosen by the author | none to answer; `max_in` added after the run |
| R3 | unequal counter-propagating waves: potential density, total energy in a stretch, period-averaged kinetic energy | 2 | yes: 0.0987 J/m; 0.0395 J; 1.21e-3 J | none (tension found by an author-written fact) | none |

All 3 problems matched in every part, with no production change needed to author them.

## Cost hypothesis vs actual
- **(a) any energy question about a string wave or pulse:** confirmed (R1, R3).
  Maximising a density over x was a new observation need; `max_in` was added after the run.
- **(b) the energy split at a junction:** confirmed (R2: reflected + transmitted =
  incident).
- **(c) widths of compact pulses and transmitted pulses:** confirmed (R1, R2).

## Production changes by reason
- **New observation and maths services (planned):** densities, stretch energies,
  `mean_over`, `width`, and the jump qualification.
- **Review 8 corrections:**
  - numeric integration split at breakpoints;
  - the jump check made exact, and refused at symbolic or periodic edges;
  - the `peak_position` fallback;
  - density extent and corner checks;
  - a stretch without `t` refused;
  - `mean_over` dimensions;
  - `width` errors;
  - given standing waves.
- **Post-run (author friction):** `max_in` / `min_in`.
- **Arrangement-specific handling:** none.

## Notes
- **Review findings:** review 8 found more silent wrong answers (8) than reviews 6–7. Most
  were in the numerical fallbacks and in the edge cases of the jump check, not in the
  energy physics, which matched hand values in every case the reviewer tried.
- **`tension: free` friction:** `tension: free` does not take the speed from a harmonic
  wave's omega and k. The author worked around it with an unknown tension and a fact. This
  is recorded as an authoring friction, not changed here.
