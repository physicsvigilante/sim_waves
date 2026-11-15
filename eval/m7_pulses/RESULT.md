# Milestone 7 (shaped pulses): result

## Transfer evidence (reserved cases)
- **Setup:** three problems written by a separate agent (Opus, fresh context). Each key was
  checked by a closed form and by an independent numerical simulation. The developer did
  not read them before the freeze (`run/FROZEN.md5`).
- **Author:** a fresh Claude Sonnet agent, with FORMAT.md and examples only.
- **Grading:** by the developer after the run (not independent; numeric parts only).

| Case | Structure | Attempts | Key match (all parts) | Hand steps | Production change needed |
|---|---|---|---|---|---|
| R1 | triangular pulse at a clamped end; displacement during overlap; largest displacement and where | 2 | yes: 1.2 mm; 3.0 mm at 0.70 m | the position of the maximum, by sampling y at 11 points | none to answer; `peak_position` added after the run |
| R2 | half-sine pulse into a 9x heavier string; transmitted length, peak position at 0.1 s, transmitted energy | 2 | yes: 0.20 m; 0.70 m; 1.78 mJ | the length and the peak position by sampling; the energy by hand (E = T * integral of y'^2) | energy is out of milestone scope (see note) |
| R3 | rope with linearly rising mu; end-to-end travel time; position at half time | 3 | yes: 7/60 s; 1.726 m | the half-time typed by hand (nesting worked; the author did not know it was allowed) | none |

All 3 problems matched in every part, and no production change was needed to author them.
The hand steps show three observation-layer gaps: the position of a maximum, the extent of
a pulse, and pulse energy.

## Cost hypothesis vs actual
- **(a) pulses at junctions and ends need data only:** confirmed (R1, R2); the physics
  needed no change.
- **(b) peak of any pulse at a time:** confirmed (R1). Where the peak occurs is a new
  observation need, added after the run as `peak_position`.
- **(c) travel times, uniform and non-uniform:** confirmed (R3).

## Production changes by reason
- **New capability (planned):** the shaped pulse, the image method at junctions and ends,
  the start-on-own-string qualification, `peak`, `step`, `travel_time`.
- **Mathematics (unplanned):** a piecewise-aware extremes search, a time-budgeted symbolic
  attempt, and a numerical fallback shown as a decimal.
- **Review 7 corrections:** symbolic extremes now error instead of returning 0; second
  reflections refused; `travel_time` extents and sign; a doc idiom; messages.
- **Post-run (author friction):** `peak_position`; docs for nesting observables and for
  horizontal pulse launch.
- **Arrangement-specific handling:** none.

## Notes and limits
- **Energy (R2 c):** the reserved-problem writer was prompted by the developer with an
  "energy split" suggestion, outside the planned scope. Pulse or segment energy (T times
  the integral of y'^2, plus kinetic) is a reusable observation gap, also seen in run 4
  (gap 9). It was not added during this milestone, to avoid building toward an exposed
  test.
- **Multiple reflections:** refused, one junction per scene.
- **Pulse extent:** no observable yet; it was sampled by the author in R2.
