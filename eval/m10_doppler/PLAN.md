# Milestone 10: the Doppler effect (moving sources, listeners, walls; wind)

**Charter tier:** light. This plan is written BEFORE implementation.
**Design set:** folders 24/02 and 24/03 (Doppler 1 and 2, 20 pages).
**Reserved set:** Doppler problems from the book (wanes_full.pdf). A separate agent
transcribes them; the developer does not read them before the freeze.

## What is blocked, and at which layer
- **Physics:** the engine has only stationary point sources (`sources`, `points`, `rays`).
  Nothing moves, the air has no wind, and the heard frequency is always the source
  frequency.
- **Every Doppler problem was excluded** from runs 1–5.

## Approach: first principles, not the textbook formula
The engine does not apply f' = f (v ± vo)/(v ∓ vs). It follows the wave:
- **Emission time.** For a listener at r_L(t), it finds the emission time t_e, the
  moment when the sound that arrives at time t left the source:
  |r_L(t) - r_S(t_e) - w (t - t_e)| = v (t - t_e), with w the wind.
- **Heard frequency.** The phase received is the phase emitted at t_e, so the heard
  frequency is f0 · dt_e/dt (implicit derivative, exact when t_e has a closed form).

The textbook cases come out of this (along the line, perpendicular, wind at an angle,
"after the trains cross"), and so do the cases that need time (a passing train, a source
on a circle, a source that starts to move at t = 5 s).

## Scope
1. **Motion of sources and listeners.** Every point carries a position at t = 0 plus one
   of:
   - `velocity: [vx, vy]` (constant);
   - `velocity` + `starts: <time>` (at rest until then);
   - `circle: {center, speed, sense}` (uniform circular motion).
   A source may also have `emits_from: <time>`.
   - The format is to be settled at implementation: probably `points` and `sources`
     accept a dict with `at` and the motion keys.
2. **Wind:** `media.air.wind: [wx, wy]`. Sound moves at v relative to the air.
3. **Observables:**
   - `frequency(ray, t=...)`, the frequency heard at reception time t;
   - `frequency(ray, emitted=...)`, the frequency of the sound emitted at that time;
   - `emitted_at(ray, t=...)` and `arrives_at(ray, emitted=...)`;
   - `beat_frequency(ray1, ray2, t=...)`.
   - With no time given, the heard frequency is reported only if it does not depend on
     time (constant velocities along one line, before or after the crossing).
   - Otherwise the engine says: "depends on time; give t= or emitted=".
   - Sound not yet arrived is "no sound yet".
4. **Moving plane reflector** (a wall, a car as a reflector) moving along its normal,
   with source and listener on that normal line (1D in v0). The reflection is a chain:
   source → wall (a listener) → listener (the wall re-emitting).
5. **Teaching views:** the heard frequency against time (plot), and snapshots of the
   wavefronts emitted at equal intervals (circles; their crowding shows the effect).

## Excluded (refused with a clear message)
- Source or listener at or above the speed of sound (several emission times, shocks).
- Accelerated motion other than uniform circular.
- Reflection from a moving wall off its normal line, and multiple reflections.
- Light, radar, relativistic Doppler, and Doppler inside tubes or strings.

## Implementation-cost hypothesis
After this milestone these need scene data only:
- **(a)** a source and/or listener moving with constant velocity, in any direction, with
  or without wind, asking a heard frequency or a ratio (with m9 `arbitrary` values);
- **(b)** reflection from a wall or vehicle moving along the line, and beats between the
  direct and reflected sound;
- **(c)** time-resolved hearing: a passing source, circular motion, motion or emission
  that starts at a stated time.

## Motivating arrangements (exposed design set)
- **24/02 asc_004 #1:** a train passes a man; the shape of f(t) (graph options).
- **24/02 asc_006 #3:** a source on a circle; the order of frequencies emitted at A, B, C.
- **24/02 bmc_004 #6:** a wall approaching a stationary horn; the reflected frequency
  and the percentage change.
- **24/02 dmt_004 #9:** a source starts emitting at 0 and moves from 5 s; the pressure
  frequency at (t, x) pairs (matrix).
- **24/03 bmc_004 #6:** two people with sources, one moving; the beats heard by each.
- **24/03 cnt_005 #12:** a man and an approaching wall; beats between direct and
  reflected sound.
- **24/03 cnt_006 #13:** wind at 60° to the source's motion.

## Negative and boundary cases
- A supersonic source is refused.
- A heard frequency asked without a time when it depends on time gives a clear error.
- A listener asked before the first sound arrives gets "no sound yet".
- A moving wall off its normal line is refused.
- A listener at the source's position is refused (zero distance).
