# Milestone 14: service repairs

**Charter tier:** light. This plan is written BEFORE implementation.
**Source:** the seven engine defects that run 7 found (`eval/run7/SCORECARD.md`, "Engine
defects"; evidence in `eval/run7/GRADES.md`), plus one test-harness defect found when
the project moved to this Windows folder.

## What is blocked, and at which layer
All of these are refusals or wrong messages. None gave a wrong value.
- **`nearest()` on a value that depends on a solved unknown (maths services, 7 scenes in
  run 7):** single/156, jee_main/19, jee_main/36, single/2, single/182, single/55,
  jee_advanced/2. `_nearest` requires `is_number`, but it is evaluated before the solved
  values are put in, so it says "needs numbers". The authors read the option by eye.
- **`in <unit>` inside `nearest()` (format, 1):** single/182, `nearest(vs in m/s, ...)`
  gives "comparison not allowed here".
- **A quoted zero with a unit in a position list (format, 1):** jee_main/26, `"0[m]"`
  gives "needs a unit".
- **Comparison checks scale an unranged arbitrary value too far (maths services, 1):**
  jee_main/26. `COMPARISON_SCALES` goes to ×1000; an arbitrary sound speed sampled at
  340000 m/s trips the m12 "not sound" guard, and the comparison is lost.
- **`limit()` on a symbol with a stated bound (maths services, 1):** single/52. A
  bounded symbol becomes `base ± offset` in expressions (`Scene.bound_variable`), so
  `limit(..., dl, 0)` says "second argument must be a variable". `diff()` already
  handles this case.
- **Unknown k and phase with both points off the origin (solver, 1):** integer/5. "k
  only fixed up to a period that depends on symbols", even when a stated bound leaves one
  branch.
- **Missing units (format, 2):** km/h (jee_main/7, jee_main/30) and μm (single/97).
- **Test harness on Windows (tooling):** `harness.run_dir` uses
  `mp.get_context("fork")`, which does not exist on Windows, so `simwaves test` fails
  unless run with `-j 1`.

## Smallest shared change (scope)
1. **`nearest()` after the solve:** evaluate `nearest` on the solved values.
   - If the value is a single number after the solve, pick the option as now.
   - If it still depends on an arbitrary value or a family parameter, the picked option
     must be the same over the whole family (proved, or sampled like other observables,
     with that basis shown). Otherwise refuse and say the option depends on the value.
   - A value that is still unknown is refused as now, with a message that names it.
2. **`in <unit>` inside `nearest()`:** `nearest(x in u, a, b, ...)` converts x, and every
   bare-number option is read in the same unit. Options that carry units are converted to
   it. A wrong dimension is refused.
3. **Zero with a unit:** `"0[m]"` (and `0[s]`, etc.) is accepted wherever a quantity
   with a unit is; its dimension is still checked.
4. **Comparison scalings that leave the physics:** when a physical guard (such as the
   "not sound" guard) refuses a scaled run of an unranged arbitrary value, that run is
   dropped rather than failing the observable. The basis says which scalings were
   covered. If fewer than 5 runs remain, the comparison is refused (no silent loss of
   evidence). Bring FORMAT.md and the code in line on the scaling range.
5. **`limit()` on a bounded symbol:** handled as `diff()` already does: the limit is
   taken in the offset variable, mapped from the value given for the declared symbol. A
   limit point outside the bound (or on the wrong side of it) is refused.
6. **Off-origin k and phase with a bound:** when the period ambiguity can be resolved by
   a stated bound that leaves exactly one branch, return that branch. With no bound, or a
   bound that leaves two or more branches, refuse as now.
7. **Units:** `km/h` (also `kmph`) and `um` / `μm`.
8. **Harness:** use the platform's default process start method (spawn on Windows), so
   `simwaves test -j N` works here. Output and its order stay the same.

## Excluded
- Pressure at a point (P0 ± p) and accelerating sources in Doppler (the next milestones).
- Pulse trains, "when closest" instants, approximation rules such as v ≪ c.
- Any change to how `nearest` breaks near-ties (the 2× rule stays).

## Implementation-cost hypothesis
After this milestone, these need scene data only:
- **(a)** picking the nearest printed option for any value the engine solves, including
  one that depends on solved unknowns, without reading it by eye;
- **(b)** options printed in a non-SI unit (km/h, μm, cm, m/s) matched by `nearest(x in
  u, ...)` with no hand conversion;
- **(c)** a small-quantity approximation (`limit`) on a symbol that the problem bounds;
- **(d)** a wave equation fixed from two points off the origin when a stated bound
  picks one branch;
- **(e)** a comparison over an arbitrary sound speed without a spurious guard refusal.

The run 7 projection: the 7 `nearest` refusals and the 2 refusal-driven not-produced
answers (single/52, integer/5) become engine-derived. Unverified answers fall from 6/44 to
4/44; the other four are physics outside the model, which this milestone does not touch.

## Motivating arrangements (exposed, run 7)
single/156, jee_main/19, jee_main/36, single/2, single/182, single/55, jee_advanced/2,
jee_main/26, single/52, integer/5, jee_main/7, jee_main/30, single/97.

## Negative and boundary cases
- `nearest` on a value whose nearest option changes across the family is refused.
- `nearest` on an unknown that is never solved is refused, and the message names it.
- `nearest(x in u, ...)` with the wrong dimension is refused.
- `limit` toward a point outside a symbol's bound is refused.
- A bound that leaves two branches of k and phase is still refused.
- A comparison where fewer than 5 scaled runs survive the guards is refused.
- `0` with no unit where a unit is required is still refused; `"0[m]"` with the wrong
  dimension is refused.
- An unknown unit (for example `kmh2`) is refused.
