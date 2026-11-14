# Run 4 scorecard (per eval/SCORECARD.md): held-out folder 11 (01–05) and 24/01

- **Problems:** 77 held-out; 15 partly exposed through one-line transcriber notes (see
  `README.md`).
- **Authors:** four fresh Claude Sonnet agents.
- **Grading:**
  - An independent Fable 5.2 (medium) agent graded every problem, re-running every final
    scene; details are in `GRADES.md`.
  - The automatic key check (`RESULTS.txt`, 31/77) is a format artefact: most answers are
    multi-part or symbolic.
- **Frozen engine:** a copy is in `engine_before_fixes/`.

| Dim | All 77 | 62 unexposed |
|---|---|---|
| A. Interpretation | faithful 65, minor 12, misrepresented 0 | 51 / 11 / 0 |
| B. Correctness | proved 51, sampled 2, unverified 23, wrong 1 | 42 / 2 / 18 / 0 |
| C. Coverage | full 42, partial 29, unsupported 6 | 34 / 23 / 5 |
| D. Educational | not assessed | — |
| E. Textbook answer | matches 69, book-disputed 6, differs 1, not-produced 1 | 62 / 0 / 0 / 0 |

## Reading the numbers
- **E is high, B is the real measure.** About a third of the matches rest on a decisive
  hand step (23 unverified). The engine's coverage of folder 11 is the limit, not the
  authors' fidelity.
- **The one wrong answer (11/01/002)** was caused by an engine message that hid the
  book's solution family; see the fixes below.

## Engine defects found by this run (all fixed after it, with tests)
- **Silent wrong (11/02/001):** a hanging string with position-dependent mu had double the
  tension. Fix: `coordinate.variable` is required, the hanging tension integrates mu, and a
  position symbol in mu that is not declared is refused (r58, r59).
- **Silent wrong (11/02/002):** `front()` on a non-uniform string under fixed tension.
  Same fix.
- **`minima()` false negative (11/04/010):** sympy found no general branch. It now
  solves for each whole number (r60).
- **Ambiguity message hid a solution family (11/01/002):** it now lists every value each
  unknown takes (r61).
- **Robustness:** a traceback on printing tiny or infinite values; infinite results are
  now an error per observable.
- **`run` output:** results now print their basis (`<sampled>`, `<proved>`) when not
  exact.

## Capability gaps by problems blocked
1. Acoustic pressure, displacement, intensity and bulk-modulus relations: 9.
2. Liquid and solid media, including rods: 7.
3. Travel time and integrals on non-uniform strings: 5 (partly addressed by the fix).
4. Families, list indexing and loci: 5.
5. Decibels and solving inside a log: 4.
6. Springs, Hooke extension and load statics: 4.
7. Gas mixtures, rms speed, pressure with temperature: 4.
8. Pulse tools: 4.
