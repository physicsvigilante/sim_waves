# Milestone 14 (service repairs): result

## Transfer evidence (reserved cases)
- **Setup:** six original problems, written by a separate agent prompted with the PLAN
  scope. Each key is checked two ways: by formula and by a short calculation. The developer
  did not read the problems or keys before the freeze (`run/FROZEN.md5`, taken at
  `4a0dcf8`, the commit Astra approved in review round 23).
- **Author:** a fresh Claude Sonnet agent, given TASK.md, FORMAT.md and the examples only.
  It did not open the engine source, the reserved folder or `run/engine_at_run/`.
- **Verification:** after the run, the developer checked that the frozen files were
  unchanged, re-ran each final scene and read the keys.

| Case | Structure | Attempts | Key match | Engine fit |
|---|---|---|---|---|
| R1 | closed tube with an unknown end correction and sound speed (two resonances); open pipe with end corrections; options in cm | 1 | yes: B (79 cm; engine 78.95 cm) | full: v = 340 m/s and e = 1 cm solved, `nearest` picks B |
| R2 | horn of a passing car: 600 Hz approaching and 500 Hz receding; car speed in km/h | 2 | yes: A (111 km/h; engine 340/11 m/s = 111.27 km/h) | full engine work, coverage partial: the one car is modelled as two copies of the source |
| R3 | beats between two open pipes as one lengthens by dl; K = beats per mm as dl → 0 | 2 | yes: 4 Hz per mm | full: `limit` on the bounded dl gives 4 |
| R4 | wave equation from a crest at 10 cm and a point at rest and rising at 25 cm (t = 0); wavelength > 20 cm picks the branch | 1 | yes: A (k = 10π/3, phase 5π/6) | full: the engine found the solution unique under the bound |
| R5 | open pipe P and closed pipe Q, sound speed not given: four statements | 1 | yes: A, B | full: A proved true and C and D proved false over every allowed speed; ratio 6/5 exact (checked at 5 sampled speeds) |
| R6 | ultrasound in tissue, 2.5 MHz, 1540 m/s: least distance for a phase difference of π/3, options in μm | 1 | yes: B (103 μm; engine 102.67 μm) | full |

**All 6 matched**, with the engine doing every step (no `hand_steps`).

## Cost hypothesis vs actual
- **(a) `nearest` on a solved value:** confirmed (R1, R2, R6; R1 and R2 on values that depend on two solved unknowns).
- **(b) Options in a non-SI unit:** confirmed: cm (R1), km/h (R2), μm (R6), with no hand conversion.
- **(c) `limit` on a bounded symbol:** confirmed (R3). To get "per mm", the author divided by `dl/1[mm]` inside the limit. Without that the result is 4000 per metre, which is correct but in other units.
- **(d) A wave equation from two points off the origin, with a bound that picks the branch:** confirmed (R4).
- **(e) A comparison over an arbitrary sound speed:** confirmed (R5). No guard refusal, and the true/false statements were proved, not sampled.

## Post-run fixes
None. No blind-run case exposed an engine defect.

## Friction (for later)
- **A source that passes the listener (R2):** a heard frequency needs an emission time, and the time of the pass depends on the unknown speed. The author used two copies of the source, one before and one after the pass. A direct form ("approaching" / "receding" for a source moving through the listener) is a candidate.
- **The author's v1 of R2 had one fact for two unknowns** and was correctly refused. The message names the inequality `u < 340[m/s]` as "cannot be checked" rather than saying the facts are too few. The wording could be clearer.
- **Framing choices left to the author:** overtone-to-harmonic mapping (R5: `harmonic(r, overtone=k)` exists but was not used), and "least distance" written as the smallest positive solution (R6).

## Production changes by reason
- **Planned (PLAN.md scope):**
  - `nearest` on values that depend on solved unknowns, and `nearest(x in <unit>, ...)`;
  - a quoted zero with a unit in position lists;
  - comparison checks that do not scale an unranged arbitrary value too far;
  - `limit` on a symbol with a stated bound;
  - unknown k and phase with both points off the origin;
  - the units km/h, kmph, μm and nm;
  - the test harness on Windows.
- **Review 14 fixes (23 rounds with ChatGPT Astra; `eval/review14/REPORT.md`; r176–r338).** The main threads:
  - `limit` narrowed to numbers apart from its variable;
  - conditions kept beside every value as it is read: every log, root, division, power, tan, asin/acos and wave value must be defined, even where SymPy would cancel it, and the condition is checked after the solve;
  - wave profiles, sums, shaped pulses, fields and arbitrary values carry their written domain;
  - every wave observable respects that domain: `at(field(...))`, `phase`, energies, range functions;
  - extremum searches rebuilt to find only reached extremes, with exact ordering, exact breakpoints and certified branch regions;
  - powers with an unknown exponent decided after the solve;
  - non-real results refused.
- **Post-run fixes:** none.

## Open limitations (to m15a)
- r84, r93 and r96 cannot be run safely on Windows: there is no per-scene time or memory limit there.
- There is no CI.
- SymPy is not pinned. Tests here ran on SymPy 1.12, and some of its calls can run for minutes on Windows.
