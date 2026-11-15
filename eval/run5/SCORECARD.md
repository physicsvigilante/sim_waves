# Run 5 scorecard: broad blind test on a new source (book chapter "Waves")

- **Problems:** 80 sampled at random from the practice exercises and JEE archives,
  stratified by type. Doppler problems and corpus duplicates were excluded. See
  `README.md` for exposure.
- **Authors:** four fresh Claude Sonnet agents.
- **Grading:** an independent Fable 5.2 (medium) agent, who re-ran all 80 final scenes;
  details are in `GRADES.md`. The automatic key check (`RESULTS.txt`) gives 69/80 raw.
- **Engine:** milestones 1–8, frozen (`FROZEN.md5`).

| Dimension | Result |
|---|---|
| A. Interpretation | faithful 69, minor-deviation 11, misrepresented 0 |
| B. Correctness | verified-proved 68, verified-sampled 1, unverified 10, wrong 1 |
| C. Coverage | full 56, partial 23, unsupported 1 |
| D. Educational | not assessed |
| E. Textbook answer | matches 62, differs-book-disputed 5, differs 5, not-produced 8 |

## Compared with run 4 (folder 11, before milestones 6–8)
These are different sources and different mixes of question types, so this is an
indication only.

| Measure | Run 4 | Run 5 |
|---|---|---|
| Engine-verified (B proved or sampled) | 53/77 (69%) | 69/80 (86%) |
| Full coverage | 42/77 (55%) | 56/80 (70%) |
| Misrepresented | 0 | 0 |

## Engine defects
- **Silent wrong (the B = wrong):** `vy`/`slope` at a corner of a shaped pulse printed 0
  instead of refusing (comprehension/17).
- **Refusal against the doc:** `max_in`/`min_in` reject free symbols even when `at()`
  supplies them.
- **Wording:** `nodes()` of a fixed-fixed string lists the ends, while the doc says
  "inside".

## Test-process defects (recorded, not hidden)
- **The developer's problem-file builder dropped the top-level `column_ii` of matrix
  records.** jee_advanced/62's author then recalled Column II from memory. It is graded
  E = not-produced.
- **One author ran other authors' scenes read-only.** No trace in the grades.
- **The developer saw part of the answer keys** while counting pages (README).

## Top gaps (layer)
1. **Symbolic scale for ratio questions (maths, 13):** symbolic lengths and mu/T; two
   unknowns in logs; `max_in` under `at()`.
2. **Authoring conventions (authoring, 6):** `tension: free` hides the tension; the phase
   convention; missing units.
3. **Composite and driven resonators (assembly, 5).**
4. **Sound at boundaries between media (assembly, 5).**
5. **Mechanics that sets tension: Hooke's law, buoyancy (assembly, 5).**
6. **Mode and point observables (observation, 4).**
7. **Gas properties: bulk modulus, rms speed (observation, 4).**
