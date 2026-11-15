# Milestone 6 (acoustics): result

## Transfer evidence (reserved cases)
- **Setup:** three problems written by a separate agent (Opus, fresh context). The keys were
  each checked twice by two methods. The developer did not read them before implementation
  was frozen (`run/FROZEN.md5`).
- **Author:** a fresh Claude Sonnet agent, given FORMAT.md and the examples only.
- **Grading:** by the developer, comparing the answer files with the keys after the run.
  This is not independent grading; there are 3 problems and every part is numeric.

| Case | Structure | Attempts | Key match (all parts) | Hand steps | Production change needed |
|---|---|---|---|---|---|
| R1 | hemispherical powered source in seawater; power from a level; pressure, displacement and level at a second distance | 1 | yes: 1489 m/s, 393 W, 552.5 Pa (key 553), 1.44e-8 m, 104.0 dB | bulk modulus as 1/compressibility | none |
| R2 | rod with clamped and free ends; Y from a static test; second-lowest mode; matching free-free length | 3 | yes: 6.99e10 Pa, 5089 m/s, 3180 Hz, 0.800 m | Y = stress/strain; area from diameter; a repeated medium | none |
| R3 | two powered sources, coherent and incoherent; levels and resultant pressure | 2 | yes: 75.1 dB, 0.163 Pa, 87.3 dB | duplicate random sources for part (c); resultant amplitude as a pressure | none |

All 3 problems matched in every part, and no production change was needed to author them.

## Cost hypothesis vs actual

| Hypothesis item | Outcome |
|---|---|
| (a) amplitude conversions in any medium need data only | Confirmed by R1 (liquid) and R3 (air) |
| (b) powered sources, several, coherent or incoherent, levels | Confirmed by R1 and R3 |
| (c) liquid speed from compressibility data | Confirmed with one authoring step (1/compressibility typed by hand); `compressibility` added after the run |
| (d) rod modes, any end combination | Confirmed by R2 (clamped-free and free-free) |

## Production changes by reason

| Reason | Changes |
|---|---|
| New physics (planned) | fluid and rod media; gas density (also P,T,M); sound-wave amplitude links; `pressure_amplitude`, `displacement_amplitude` and `intensity` on waves and rays; powered sources; `sound_level`; rod resonator (1 line in `modes.py`) |
| Mathematics (unplanned) | solving unknowns inside log/exp/inverse trig (`_in_monotonic`, `_solve_monotonic`, `_log_linear`) |
| Review 6 corrections | the dimension of `amplitude(ray)`; lost log roots; a level-difference timeout; rod leftover inputs; a tube from a powered source; messages |
| Post-run corrections (from author friction, recorded after the run) | `compressibility` route; units mW, kW, kHz, kPa; `pressure_amplitude(r1, r2, ...)`; removal of the medium/resonator length cross-check, which review 6 #4 had added and which forced a duplicate medium in R2 |
| Arrangement-specific handling | none |

## Notes and limits
- **The length cross-check was a mistake:** the review 6 fix wrongly required a resonator
  to have the medium's length. It is now reverted: a medium is a material, and its length
  only fixes the density. This is recorded here and not hidden.
- **Switching coherence needs a second source pair:** coherence cannot be switched on the
  same sources without one. This is an investigation-level change, like a property
  revision (diagnostic 1).
- **Not tested:** educational use of the new media; structural revision chains.
