# Run 7 scorecard: broad blind test after milestones 12–13 (book chapter "Waves")

- **Problems:** 44.
  - **Set D2:** the 12 Doppler problems found while sampling for run 6.
  - **Set S2:** 32 more sealed problems, sampled with the seeded order.
- **Authors:** three fresh Claude Sonnet agents.
- **Grading:** an independent Claude Opus agent, standing in for Fable 5.2 (which needs
  usage credits). It re-ran all 44 final scenes (`GRADES.md`). The automatic key check
  (`RESULTS.txt`) gives 38/44 raw.
- **Engine:** milestones 1–13, frozen (`FROZEN.md5`).

| Dimension | Overall (44) | Set D2 (12) | Set S2 (32) |
|---|---|---|---|
| A. Interpretation | faithful 43, minor 1, misrepresented 0 | 11 / 1 / 0 | 32 / 0 / 0 |
| B. Correctness | proved 20, sampled 18, unverified 6, wrong 0 | 7 / 4 / 1 / 0 | 13 / 14 / 5 / 0 |
| C. Coverage | full 34, partial 10, unsupported 0 | 11 / 1 / 0 | 23 / 9 / 0 |
| D. Educational | not assessed | | |
| E. Textbook answer | matches 35, disputed 2, differs 1, not-produced 6 | 10 / 1 / 0 / 1 | 25 / 1 / 1 / 5 |

## Compared with run 6
These are different samples, so treat the comparison as an indication only.

| Measure | Run 6 | Run 7 |
|---|---|---|
| Wrong engine values | 0 | 0 |
| Misrepresented | 1 | 0 |
| Full coverage | 68% | **77%** |
| Engine-derived textbook matches | 83% | 80% (Doppler 83%, sealed 78%) |
| Answer decided by hand (unverified) | 6% | **14%** |

## Hypotheses (written before the run)
- **H1 (no wrong value; light and radar with `type: em`):** the values hold.
  - The light and radar part was **not tested**. Set D2 has no light or radar problem.
    The README's claim that it did was the developer's assumption, made without reading
    the problems, and it was wrong.
  - The m12 guard fired once, wrongly, in a sound problem (defect 4 below).
- **H2 (hand-decided answers at or below 6%):** **fails** (14%).
  - Four of the six come from physics outside the model: an accelerating source, pressure
    at a point, a pulse train, and a "beats unchanged" crossing.
  - The other two come from engine refusals (defects 5 and 6).
- **H3 (remaining gaps mostly format and authoring):** **does not hold.**
  - Reading the source was strong: no stated fact was overlooked, unlike run 6.
  - The gaps are engine services, physics outside the model, and units.

## Engine defects (verified by the grader; all refusals or wrong messages, no wrong values)
1. **`nearest()` refuses values that depend on solved unknowns** ("needs numbers"). This
   hit 7 of the 16 final scenes that use it, and the behaviour is inconsistent.
2. **`in` inside `nearest()`** gives "comparison not allowed here".
3. **A quoted zero in a position list is rejected:** `"0[m]"` gives "needs a unit".
4. **The comparison check over-scales arbitrary values.** It goes out to about ×1000,
   past the documented ×89, and trips the m12 "not sound" guard on an arbitrary sound
   speed.
5. **`limit()` refuses a symbol that has a stated bound.**
6. **An unknown k and phase with both points off the origin are refused,** even with a
   bound that leaves one branch.
7. **Missing units:** km/h and μm.

## Test-process notes
- **README error:** the README said set D2 includes light and radar problems. That was
  not true; see H1.
- **Shared work folder:** authors noticed the other authors' answer files in the shared
  work folder. They ran only their own files, and there is no effect on the grades.

## Top gaps (layer)
1. **Maths services (11):** `nearest` on solved unknowns (7); solver and sampler
   refusals (4).
2. **Physics outside the model (6):** accelerating sources, pressure at a point, pulse
   trains, statics on an incline.
3. **Format (10):** units and syntax (5); approximations and instants such as "when
   closest" or v ≪ c (5).
4. **Source (4):** disputed or judgement book keys.
5. **Authoring (3).**
