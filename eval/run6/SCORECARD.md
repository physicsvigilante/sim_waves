# Run 6 scorecard: broad blind test after milestones 9–11 (book chapter "Waves", with Doppler)

- **Problems:** 47 in two sets.
  - **Set D:** 15 Doppler problems from the book, not used in m10.
  - **Set S:** 32 more sealed problems, sampled with the seeded order and stratified by
    type.
  - See `README.md` for exposure and the hypotheses written before the run.
- **Authors:** three fresh Claude Sonnet agents.
- **Grading:** an independent Fable 5.2 (medium) agent re-ran all 47 final scenes
  (`GRADES.md`). The automatic key check (`RESULTS.txt`) gives 40/47 raw.
- **Engine:** milestones 1–11 plus the parallel test runner, frozen (`FROZEN.md5`).

| Dimension | Overall (47) | Set D (15) | Set S (32) |
|---|---|---|---|
| A. Interpretation | faithful 43, minor 3, misrepresented 1 | 12 / 2 / 1 | 31 / 1 / 0 |
| B. Correctness | proved 29, sampled 15, unverified 3, wrong 0 | 7 / 7 / 1 / 0 | 22 / 8 / 2 / 0 |
| C. Coverage | full 32, partial 14, unsupported 1 | 10 / 4 / 1 | 22 / 10 / 0 |
| D. Educational | not assessed | | |
| E. Textbook answer | matches 39, disputed 2, differs 4, not-produced 2 | 11 / 1 / 2 / 1 | 28 / 1 / 2 / 1 |

B is "sampled" when the answer rests on the arbitrary-value check, which samples values
rather than proving the answer. That check is new since run 5, which is why this grade is
more common here.

## Compared with run 5 (80 problems, before m9–m11)
These are different samples, and this run includes Doppler, so treat the comparison as
an indication only.

| Measure | Run 5 | Run 6 |
|---|---|---|
| Wrong engine values | 1 | **0** |
| Engine-derived textbook matches | 62/80 (78%) | 39/47 (83%); set S 28/32 (88%) |
| Answer decided by hand (unverified) | 12.5% | 6% |
| Not produced | 10% | 4% |
| Full coverage | 70% | 68% |
| Misrepresented | 0 | 1 (radar entered as a gas) |

## Hypotheses (written before the run)
- **H1 (Doppler):** mostly holds.
  - 10/15 have full coverage, with no silent wrong answer and one clean refusal.
  - It failed for light and radar: an electromagnetic wave entered as `type: gas` was
    accepted without a warning.
- **H2 (ratio and comparison questions without invented values):** holds.
  - 20 final scenes use `arbitrary:`, and answers decided by hand halved.
  - Answers with any hand step did not fall, because new kinds of hand step appeared.
- **H3 (known gaps):** only tension set by mechanics recurred (Hooke's law, buoyancy).

## Engine defects
- **No wrong value.**
- **Misleading acceptance:** electromagnetic waves run as a gas with no guard
  (single/33, integer/7).
- **Refusals that could be decided:**
  - a for-all comparison through `abs` (single/169);
  - `t=` with an unknown speed, whose message does not point to `emitted=` (jee_main/21).
- **Arbitrary values with time- or existence-dependent results** (a meeting time, an
  echo) become NOT AVAILABLE. Authors then fall back to fixed numbers.

## Test-process defects (recorded, not hidden)
- **Author A's first run used a wildcard** that also executed other authors' scenes. It
  saw their outputs only, and the grader found no effect: no shared passage, and none of
  them was in its batch.
- **The developer saw the automatic key-check output** (letters and keys) after the run,
  before grading.

## Top gaps (layer)
1. **Deciding and comparing services (maths, 8):**
   - for-all comparisons through `abs`;
   - "iff" between two symbols;
   - nearest option;
   - arithmetic on lists (spacing of resonances);
   - "slightly increased" as a limit.
2. **Things the format cannot state (format, 7):** a continuous frequency band, an
   arbitrary profile F(ωt − kx), output units.
3. **Physics outside the model (physics, 6):**
   - electromagnetic waves (they need a guard);
   - intensity with a moving source or listener;
   - wave speed relative to a moving listener;
   - adiabatic against isothermal.
4. **Arbitrary values with time- or existence-dependent results (maths, 5).**
5. **Reading the source and authoring conventions (authoring, 10):** emission against
   reception instant, an overlooked stated fact, stand-ins claimed as full coverage.
