# Milestone 13: tension from mechanics, frequency bands, output units

**Charter tier:** light. This plan is written BEFORE implementation.
**Source:** run 6 gaps that are still open after m12.

## What is blocked, and at which layer
- **Tension set by mechanics (assembly, 2 in run 6; recurring since run 5):**
  - integer/23: a wire stretched by Hooke/Young strain;
  - jee_advanced/25: a load hanging partly in a liquid (buoyancy).
  - Authors typed T = Y A ΔL/L or T = (M − ρV) g by hand. The physics is outside the
    engine and goes unchecked.
- **Frequency bands (format, 1):** jee_advanced/55, "a source of continuously variable
  frequency from 400 to 1000 Hz": which modes resonate? The author used the two edge
  tones.
- **Output units (format, 2):** answers in cm, MHz or ms. Results are SI only, so authors
  converted by hand (integer/19 shows the slip).
- **Docs:** "beat with the transmitted signal" (radar) works, but FORMAT.md has no
  example of it.

## Smallest shared change (scope)
1. **String tension from a load:**
   - `tension: {weight: {mass: M, g: g}}` gives T = M g;
   - optionally `buoyancy: {fluid_density: ρf, volume: V}`, or
     `{fluid_density: ρf, load_density: ρb, fraction: x}` (x is the immersed fraction,
     default 1), gives T = M g − ρf V g. T ≤ 0 is refused ("the load floats").
2. **String tension from strain:**
   - `tension: {stretch: {Y: Y, area: A, extension: ΔL, length: L0}}` gives
     T = Y A ΔL/L0;
   - `tension: {stretch: {k: k, extension: ΔL}}` gives T = k ΔL.
   - `area` may come from the string's own area or diameter, if given.
3. **`frequencies_in(resonator, lo=..., hi=...)`:** the list of allowed mode frequencies
   in [lo, hi], with `count`, `item` and `spacing` as for other lists.
4. **Output units in `observe`:** `"expr in cm"` reports the value in that unit. The
   dimension is checked; lists convert entry by entry. The unit is shown and exported.
5. **Docs:** add the radar beat example.

## Excluded
- Tension readback for `tension: free`.
- Arbitrary profiles F(ωt − kx) in observables.
- Rods under strain (only strings).

## Implementation-cost hypothesis
After this milestone, these need scene data only:
- **(a)** a string whose tension comes from a hanging load, with or without immersion,
  or from a stated strain or spring extension;
- **(b)** a "variable frequency source over a band" question (which or how many modes
  resonate);
- **(c)** answers reported in the unit the problem asks for, with no hand conversion.

## Motivating arrangements (exposed, run 6)
integer/23, jee_advanced/25, jee_advanced/55, integer/19.

## Negative and boundary cases
- A floating load is refused.
- A wrong dimension in `in <unit>` is refused.
- An unknown unit is refused.
- `frequencies_in` with lo > hi is refused.
- An extension that is not positive is refused.
- Two tension routes at once are refused.
