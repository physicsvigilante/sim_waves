# Run 2 scorecard (per eval/SCORECARD.md)

- **Exposure:** development-exposed (same 16 problems as run 1).
- **Author:** Claude Sonnet, FORMAT.md v0.1.
- **Production changes needed during the run:** none.
- **Grading:**
  - Dimension E (book key) is graded automatically (`RESULTS.txt`).
  - Dimensions A to C were graded by the developer reading each final scene against the
    problem record. The grader is not independent.

| Dimension | Result |
|---|---|
| A. Interpretation fidelity | faithful 14, minor-deviation 2, misrepresented 0 |
| B. Physical & numerical correctness | verified (exact/proved) 16 |
| C. Simulation coverage (author-reported, checked) | full 12, partial 4 |
| D. Educational usefulness | not assessed (no `view` authored; no teacher task) |
| E. Textbook-answer completeness | matches 13, differs-book-disputed 1, differs 2 |

## Minor deviations (A)
- **22/02/asc_007:** the bound 0 < phi < 90 deg was replaced by two sample values,
  30 and 60 deg, because the engine cannot use a symbolic range on a symbol. The figure's
  curves were not matched to engine output.
- **22/02/asc_009:** the phase was given directly as 0 "because the curve rises from the
  origin". With the engine's convention, phase 0 at t = 0 gives a falling curve.
  - Writing the figure fact as `slope(w, x=0, t=0) > 0` would have let the engine catch
    this.
  - The answer letter is unaffected, and the book ignores the phase too.

## E outcomes that are not plain errors
- **22/02/cnt_005 (book disputed):** the misprinted equation was modelled faithfully. The
  engine shows the answer depends on x, and the author reported that instead of forcing
  1.5.
- **22/01/bmc_006 (differs):** a conceptual option ("must have sinusoidal form" for a
  simple harmonic wave). The book's key excludes it; the author included it. Debatable.
- **22/02/asc_007 (differs):** the figure labels are unreadable (already flagged in the
  corpus).

## Compared with run 1 (run 1 stays as recorded)
- **Book-key matches:** 13/16 in both runs. Run 2 recovered 22/01/bmc_005 and missed
  22/01/bmc_006.
- **Answers from engine results:** fully 12 in run 2 vs 10 in run 1. In run 1,
  22/02/asc_008 ran no scene at all; in run 2 it is fully engine-derived.
- **First-attempt success:** 7/16 vs 9/16. Two of run 2's extra files were voluntary
  tidy-ups, not engine rejections.
- **Provenance tags:** used for all 9 facts written as `given` in run 2.

## Friction carried forward
1. **Symbol ranges:** there is no way to declare a symbol's range (0 < phi < pi/2).
2. **Slow `equivalent()`:** it timed out on option formulas with decimals.
3. **Figure facts entered as parameters:** they bypass the engine's check (asc_009 above).
   FORMAT.md should say to write figure facts as `given`.
