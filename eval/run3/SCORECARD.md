# Run 3 scorecard (per eval/SCORECARD.md): held-out folder 23

- **Exposure:** held-out, 36 problems. Nine were partly exposed to the developer through
  one-line transcriber notes (listed in `../split_23.md`). The authors saw none of them.
- **Authors:** two fresh Claude Sonnet agents, 18 problems each.
- **Engine and format:** after review 3; FORMAT.md md5 0092e8cc7bc244f951f90c84baafe6e1.
- **Production changes during the run:** none (the run is frozen as recorded).
- **Grading:**
  - Dimensions A, B, C and E were graded by an independent Fable 5.2 (medium) agent, with
    every final scene re-run; details are in `GRADES.md`.
  - The automatic key comparison is in `RESULTS.txt`: 31/36, and 22/36 on the first attempt.

| Dimension | Result |
|---|---|
| A. Interpretation fidelity | faithful 32, minor-deviation 3, misrepresented 1 (03/asc_004: a typo, 25 Hz for 5 Hz, tagged as stated) |
| B. Correctness | verified-proved 29, verified-sampled 2, unverified 4, wrong 1 (01/asc_005: assumed no phase change at the ceiling) |
| C. Coverage | full 23, partial 12, unsupported 1 |
| D. Educational usefulness | not assessed (no teacher task) |
| E. Textbook answer | matches 30, differs-book-disputed 2 (01/cnt_007, 02/cnt_005), differs 2 (01/asc_005; 04/bmc_006, where option (c) has a unit misprint), not-produced 2 |

## Caveats
- **engine_fit over-claims:** about 8 answers claim "full" engine fit but rest on one
  hand step (a path length, a node count, M*g, an odd/integer judgement). Of the 29
  verified-proved results, 9 contain such a step.
- **Rule breaches:**
  - 04/bmc_005 took 6 attempts (the limit is 3).
  - 04/bmc_006 relies partly on an extra probe file.
- **Exposure split:**
  - The two disputed keys and the 04/bmc_006 misprint are in the partly exposed set.
  - Results on the 27 unexposed problems are in `GRADES.md`.

## Capability gaps by problems blocked
1. Point sources, path lengths and reflectors with a phase change: 6.
2. Standing-wave pattern observables (node/antinode positions and counts, pluck/touch): 4.
3. Three gaps blocked 2 problems each:
   - mode matching with solved unknowns;
   - the beat envelope;
   - standing-wave energy.

## Engine defects found
- `abs()` and `beat_frequency()` with unknowns in `given` crashed with a raw sympy error.
- Unit brackets inside YAML flow mappings must be quoted (3 problems).
