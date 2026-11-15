# Milestone 12: deciding services and electromagnetic waves

**Charter tier:** light. This plan is written BEFORE implementation.
**Source:** the run 6 grades (`eval/run6/GRADES.md`, gaps 1 and 3, and engine defect 1).

## What is blocked, and at which layer
- **Deciding (maths, 8 in run 6):**
  - A for-all comparison through `abs` is refused even when both sign cases agree
    (single/169).
  - Options are exact numbers rounded in print. `x == 1.22` is False for the right option,
    and there is no "nearest option" service (jee_main/11, jee_advanced/1, single/141).
  - A list result (`resonances`, `harmonics`) cannot be indexed or differenced, so the
    spacing of resonance lengths was read by hand (jee_main/5).
- **Electromagnetic waves (physics, 2, plus 1 misrepresentation):** radar and radio were
  entered as `type: gas` with v = 3e8 m/s. The engine accepted this without a word, and
  one scene claimed full coverage (single/33, integer/7).
- **Speed of the wave relative to a moving listener (physics, 1):** jee_advanced/54.

## Smallest shared change (scope)
1. **Comparisons through `abs` and `max`/`min`:** if the direct decision fails, split
   into sign cases (piecewise). The result is decided if every feasible case gives the
   same truth; otherwise it stays "cannot decide".
2. **`nearest(x, a, b, c, ...)`:** the 1-based position of the option closest to x
   (relative distance). It is refused if the two closest options are about equally close
   (within a factor of 2 of each other).
3. **Lists:**
   - `item(list, n)` (1-based);
   - `spacing(list)`: the common difference, refused if the spacing is not equal;
   - `count` already exists.
4. **Medium `type: em`** (light, radar, radio: no air).
   - The speed defaults to c (exact SI), or v may be given in a medium.
   - The Doppler effect follows from the same emission-time construction, with the
     source and receiver proper times included: f = f0 (γ_receiver / γ_source) dte/dt
     in the frame where the light speed is isotropic. This is exact special relativity,
     with no medium frame, so wind is refused.
   - Sound observables (intensity, pressure) are refused on EM rays.
5. **Guard:** a gas or fluid medium with v ≥ 1e5 m/s is refused, with a pointer to
   `type: em`.
6. **`wave_speed_seen(ray, t= | emitted=)`:** the speed of the arriving wavefront relative
   to the listener, along the direction it travels (sound in moving air, with a moving
   listener).

## Excluded
- Intensity with moving sources or listeners.
- Strain or buoyancy setting the tension (assembly; the author can still write it).
- A continuous frequency band, and arbitrary profiles (format).

## Implementation-cost hypothesis
After this milestone, these need scene data only:
- **(a)** an option given as a rounded number is picked by the engine (`nearest`);
- **(b)** a statement holding for all allowed values of a symbol inside `abs` is
  decided;
- **(c)** radar and radio Doppler, including echoes from a moving reflector, with the
  correct medium and exact relativistic results that match the classical book
  approximations to the digits shown;
- **(d)** a question about the speed of sound measured by a moving listener.

## Motivating arrangements (exposed, run 6)
single/169, single/141, jee_main/5, single/33, integer/7, jee_advanced/54.

## Negative and boundary cases
- `nearest` with a tie is refused.
- `spacing` of an unequal list is refused.
- `item` out of range is refused.
- EM with wind is refused.
- EM faster than c is refused.
- A gas with v = 3e8 m/s is refused.
- A comparison whose sign cases disagree stays "cannot decide".
