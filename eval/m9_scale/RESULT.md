# Milestone 9 (scale-free questions): result

## Transfer evidence (reserved cases)
- **Setup:** three problems by a separate agent, prompted with the PLAN scope. The
  developer did not read them before the freeze (`run/FROZEN.md5`).
- **Author:** a fresh Claude Sonnet agent, given FORMAT.md and examples only.
- **Grading:** by the developer after the run (not independent).

| Case | Structure | Attempts | Key match | Hand steps | Production change needed |
|---|---|---|---|---|---|
| R1 | rod clamped at L/2, then at L/4: ratio of fundamentals | 2 | yes: 2 | none | none |
| R2 | closed tube with only a bound L > 0.40 m: which statements must hold (multiple correct) | 2 | yes: A, C | the sign of d(diff)/dL read by hand; test lengths chosen by hand | yes (see below) |
| R3 | two incoherent speakers of unknown power, 80 dB and 75 dB readings, level at a third point | 2 | yes: 74.2 dB (powers 4.94e-3 W and 3.55e-4 W, matching the key) | coordinates of P, Q, R placed from the triangle sides (the engine's distance facts re-verified them) | none |

**R1 was not out of scope.** The clamp was modelled as a node filter,
`harmonics(node_at=...)`, on a free-free rod with arbitrary L, Y and ρ. No composite
resonator was needed. The engine reported the ratio as the same at 5 scalings.

**R1 v1 failure:** the author declared the arbitrary names in `symbols` as well. The
engine rejected this correctly, but the docs did not say it; FORMAT.md now does.

## Cost hypothesis vs actual
- **(a) Ratio questions with values the problem never gives:** confirmed (R1, and R3's
  geometry-free parts).
- **(b) Sign decisions from a stated bound:** partly confirmed.
  - The bound decided |250 − f| (A), but it broke `at()`, `diff()` and
    `resonances(vary=)`. The author dropped the bound from the final scene and reasoned
    by hand.
  - **Fixed after the run** (tests r113, r114): these functions now accept a bounded
    symbol, and the author's v1 scene runs as written (510 Hz, 127.5 Hz, crossings at
    1.02, 1.7 and 2.38 m).
- **(c) Unknowns tied through dB:** confirmed (R3). Two unknown powers were solved from
  two levels.

## Production changes by reason
- **Planned:** `arbitrary:`, bounds taken from `given`, log systems with several
  unknowns.
- **Review 9 fixes (r105–r112):**
  - a relative tolerance for comparing runs;
  - 5 scalings instead of 3;
  - log roots no longer lost or invented;
  - non-strict, integer and reversed bounds;
  - the bound's dimension;
  - the export notes.
- **Post-run fix (r113–r114):** bounded symbols in `at`, `diff` and `resonances(vary=)`.

## Layer attribution
- **R2's friction is an engine gap:** a bound was represented but not reachable from the
  functions an author uses next.
- **R1's v1 is a docs gap.**
- **R3's hand geometry is a format gap:** a point cannot be placed by its distances to
  other points. Candidate for later: points given by distances, with the engine solving
  the coordinates.

## Not done
- Two-sided bounds, `max_over` and `min_over` over a bounded range, composite resonators.
