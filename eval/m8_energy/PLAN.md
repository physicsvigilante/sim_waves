# Milestone 8: wave energy on strings, and pulse width

**Charter tier:** light. Written BEFORE implementation. This is an observation-layer
extension: no new physics.

## What is blocked, and at which layer
- **Run 4 gap 9 (3 problems), observation + maths:** energy density, kinetic energy of a
  standing-wave segment, energy over time.
- **m7 reserved R2(c), observation:** the energy carried by a transmitted pulse was done by
  hand.
- **m7 reserved R2(a), observation:** the pulse width was sampled by hand.

## Smallest shared change (scope)
All on string waves: harmonic, given, sum, shaped pulses and their reflected or
transmitted parts. mu and T come from the wave's string, including strings with a
coordinate variable.
1. **Energy densities per unit length at (x, t):**
   - `kinetic_density(w, x=, t=)` = (1/2) mu (dy/dt)^2;
   - `potential_density(w, x=, t=)` = (1/2) T (dy/dx)^2;
   - `energy_density(w, x=, t=)` = their sum.
2. **Energy in a stretch of string, integrated over x at an instant:**
   - `kinetic_energy(w, start=, end=, t=)`, `potential_energy(...)` and `energy(...)`.
   - With no `start`/`end` the integral runs over the wave's whole string (its extent, or
     the whole line).
   - For a lone shaped pulse, `t` may be omitted.
3. **Time average:** `mean_over(var, expr, lo, hi)` = (1/(hi - lo)) * integral of expr from
   lo to hi, as a neutral maths service. It is used for averages over a period.
4. **Pulse width:** `width(p)` is the length of x over which a shaped pulse is non-zero. It
   is an error for shapes that never reach zero, such as a Gaussian.
5. **Qualification:** a shape with a jump (e.g. a rectangular pulse) has infinite
   stretching energy at the jump, so its potential and total energy are refused. Its kinetic
   energy is refused too, since the moving jump has the same singularity.

## Excluded
- Energy of sound waves in 3D (intensity and power already cover that).
- Rods.
- Energy flux through areas.
- Damping.

## Implementation-cost hypothesis
After this milestone, these need scene data only:
- **(a)** any energy question about a string wave or pulse: densities at a point; kinetic,
  potential or total energy in a stretch, at an instant or averaged over a period;
- **(b)** the energy split between reflected and transmitted pulses at a junction;
- **(c)** the width of any compact pulse and of its transmitted version.

## Motivating arrangements (exposed)
- **11/02/004:** potential energy per unit volume of y = A sin(kx - wt). There is no book
  key; theory gives (1/2) T k^2 A^2 cos^2(kx - wt) per length, divided by the area.
- **11/05/009:** kinetic energy between two nodes of a standing wave: instantaneous,
  maximum, and averaged over a cycle. Key: K_max = pi k A^2 T, with the average half of
  it.
- **m7 R2(c), exposed:** energy of a transmitted half-sine pulse. Key: 1.7765e-3 J.

## Negative and boundary cases
- A jump in the shape: energy refused.
- A wave with no string (a given wave without `on:`): refused, since mu and T are unknown.
- Energy conservation at a junction: E_reflected + E_transmitted = E_incident, checked in
  a test.
- For a travelling harmonic wave, average energy per wavelength times v divided by
  wavelength equals `power`. This cross-checks the existing observable.

## Reserved transfer cases
Three problems by a separate agent, strictly within the scope above, unread until the
freeze.

## Verification and stopping condition
- Regression tests with hand values.
- A Fable 5.2 (medium) review.
- The reserved run.
- The cost hypothesis compared with the actual changes.
- Stop after one review round and one reserved run.
