# Milestone 9: scale-free questions (arbitrary values, bounds on symbols, log systems)

**Charter tier:** light. Written BEFORE implementation. This is a maths and authoring
milestone: no new physics.

## What is blocked, and at which layer (run 5, gap 1: 13 problems)
- **Invented scale values (authoring + maths):** ratio and comparison questions ("same
  wire", "tension doubled") ran only after authors invented a mu, L, T or amplitude and
  tagged it as an assumption. The answer did not depend on it, but nothing proved that.
  Some services (`resonances`, `max_in`, lists) need numbers, so symbols alone did not
  work.
  - jee_main/1, jee_main/40, integer/26, jee_advanced/28, single/30, comprehension/22.
- **Bounds on symbols (maths):** "n > 1" on a symbol was refused as a fact that
  over-specifies, so signs such as n - 1 stayed undecidable (jee_main/55, single/30).
- **Several unknowns inside logs (maths):** refused (integer/14).

## Smallest shared change (scope)
1. **`arbitrary:` values.**
   - A scene may declare `arbitrary: {mu: 10 g/m, L: 1 m}`: values the problem does not
     give and the answer must not depend on.
   - The engine runs the whole scene with these values and with two other independent
     scalings (x1.37 and x0.61 per symbol).
   - It reports each observable only if all three runs agree. Otherwise the observable is
     NOT AVAILABLE with "depends on arbitrary value mu".
   - Solved unknowns are compared the same way. The basis is reported as "independent of
     arbitrary values (3 scalings)".
2. **Bounds on symbols:** a `given` inequality on a single symbol and a constant (e.g.
   `n > 1`, `L >= 2[m]`) becomes a stated bound, tagged like any fact, instead of an error.
   - Internally the symbol is written as bound + (a positive quantity), so every sign
     decision in the engine can use it.
   - Results are shown in the original symbol.
   - Only one bound per symbol in v0.
3. **Systems with several unknowns inside log/exp:** each equation that is linear in logs
   is rewritten as an algebraic equation. The system is solved, and each root is
   re-checked against the original facts.

## Excluded
- Two-sided bounds.
- Bounds on expressions.
- Scalings of non-positive arbitrary values.
- List indexing.
- Composite resonators.
- Media interfaces.

## Implementation-cost hypothesis
After this milestone, these need scene data only, with no invented values:
- **(a)** a ratio or comparison question whose answer does not depend on unstated scale
  values (string, pipe, rod, sound, pulse);
- **(b)** a question that needs a symbol to be larger or smaller than a constant for a
  sign decision;
- **(c)** two or more unknowns tied through sound levels.

## Motivating arrangements (exposed, run 5)
- **jee_main/1:** tensions with an arbitrary load; ratio only.
- **integer/26:** a resonator frequency list with an unstated mu and L.
- **jee_main/55:** beats with a symbol n > 1.
- **integer/14:** two levels with two unknowns.

## Negative and boundary cases
- An arbitrary value that does change an answer gives "depends on arbitrary value".
- An arbitrary value that is also declared in `symbols` or `unknowns` is a conflict.
- A bound fact containing an unknown stays a normal fact.
- Two bounds on one symbol are refused in v0.
- A bound that contradicts the symbol's kind (e.g. a positive symbol < -1) is refused.

## Reserved transfer cases
Three problems by a separate agent, strictly within scope, unread until the freeze.

## Verification and stopping condition
- Regression tests.
- A Fable 5.2 (medium) review.
- The reserved run.
- The cost hypothesis compared with the actual changes.
- Stop after one review round and one reserved run.
