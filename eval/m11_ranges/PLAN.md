# Milestone 11: ranged arbitrary values and comparisons in `observe`

**Charter tier:** light (maths and format; no new physics). This plan is written BEFORE
implementation.

## What is blocked, and at which layer (m10 frozen run and design set)
- **Arbitrary speeds (maths):** an unstated source speed cannot be `arbitrary`. The m9
  check scales it up to ×89, past the speed of sound, so the scaled run is refused.
  Authors fell back to illustrative values tagged as assumptions, which nothing checks.
  - This happened in m10 R1, R3 and R4, and in the design-set circle case.
  - The same holds for any value with a physical ceiling or floor: an angle below 90°, a
    fraction below 1, a length shorter than a stated one.
- **Comparisons (format):** `observe` refuses `a > b`, so option checks such as "n2 > n3
  > n1" or "f_m < 2250 Hz" were done by hand (m10 R4) or through an undocumented
  `step(a - b)` trick.

## Smallest shared change (scope)
1. **Ranged arbitrary values:**
   `arbitrary: {u: {value: 20 m/s, below: 340 m/s}}`, optionally with `above:`.
   - The run at the stated value stands.
   - The other runs use values spread across the open range (3%, 37%, 61% and 97% of the
     way from `above`, or 0, to `below`), so they never leave it.
   - With `above` only, the ×-scalings apply to the distance above the bound.
   - Unranged values keep the m9 scalings.
   - The basis names both kinds.
2. **Comparisons in `observe`:** `a > b`, `a <= b`, chains such as `a > b > c`, and
   `a == b`.
   - The result is True or False when it can be decided for all symbol values (with the
     same sign machinery as `given`); otherwise "cannot be decided".
   - Both sides must have the same dimension.
   - Combined with arbitrary values: a comparison that holds at every run is reported;
     otherwise it "depends on the arbitrary values".

## Excluded
- Ranges for unknowns (use `given` bounds).
- Arbitrary values that are not positive.
- Logical and/or between comparisons (use separate observables).

## Implementation-cost hypothesis
After this milestone, these need scene data only:
- **(a)** a question whose answer must hold for every value of an unstated quantity with
  a physical ceiling or floor (an unstated speed below the speed of sound; an unstated
  length above a stated one), with no illustrative value;
- **(b)** an option that compares or orders computed quantities, decided by the engine.

## Motivating arrangements (exposed)
- **24/02 asc_006 #3:** a source on a circle at an unstated speed; the order n2 > n3 > n1.
- **m10 R1-like shape:** an unstated source speed (exposed in RESULT, not reread).
- **m9 r102:** a bound n > 1 with comparison options.

## Negative and boundary cases
- A value outside its own range is refused.
- `below` not above `above` is refused.
- A unit of the wrong dimension is refused.
- A comparison whose truth changes across the range gives "depends on the arbitrary
  values".
- An undecidable comparison is refused.
- Comparing different dimensions is refused.
