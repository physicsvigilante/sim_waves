# Milestone 7: pulses with a shape (reflection, transmission, peaks, travel time)

**Charter tier:** light. Written BEFORE implementation. It follows the diag1 Track B
recommendation (`eval/diag1/trackB/DIAGNOSIS.md`).

## What is blocked, and at which layer
- **Gap 8 (4 problems), assembly + observation:** a pulse has no shape, only a front
  position. It cannot be reflected, superposed or asked for its peak.
- **Gap 3 (5), observation:** there is no travel time over a length of string.
- **Track B finding:** pulse-at-junction is a conservative software restriction (assembly
  layer). For uniform, non-dispersive strings the existing junction coefficients apply to
  any shape. It stays justified for non-uniform strings.

## Smallest shared change (scope)
1. **A pulse may carry a shape:** `shape` = y(x, 0) as a formula in x, with
   `units: {x, y}` as for given waves, and a direction. Its field is
   y = shape(x - s v t), with v the medium speed. A shaped pulse is a wave with a field:
   `y`, `vy`, `slope`, `sum`, `is_travelling` and views all apply.
2. **Junctions and string ends act on shaped pulses (d'Alembert, image method):**
   - reflected: r * shape(2 xJ - x - s v1 t);
   - transmitted: t * shape(xJ + (v1/v2)(x - xJ) - s v1 t);
   - r and t as for harmonic waves; a fixed end gives r = -1, a free end r = +1.
3. **Qualification checks:**
   - The pulse must start entirely on its own string. A shape with a non-negligible part
     beyond the junction at t = 0 is refused.
   - Non-uniform strings with shaped pulses are refused, with the reason: continuous
     partial reflection.
4. **`peak(w, t=...)`:** the largest |y| over x at an instant, for any wave with a field.
   For a single pulse this is its amplitude.
5. **`travel_time(m, start=..., end=...)`:** the integral of ds/v along a medium, uniform
   or non-uniform with a coordinate variable.

## Excluded
- Multiple reflections (as for harmonic waves).
- Pulses on non-uniform strings at junctions.
- Dispersive media.
- "Where and when two pulses cancel everywhere" (an identity in x).

## Implementation-cost hypothesis
After this milestone, each of these needs scene data only:
- **(a)** a pulse of any shape on any chain of up to two uniform strings with a junction
  or a fixed/free end, asked for reflected/transmitted amplitudes, positions or shapes at
  a time, or the superposed field;
- **(b)** the peak or amplitude of any given pulse at a time;
- **(c)** travel times over strings, uniform or with mu varying along a declared coordinate.

## Motivating arrangements (exposed, run 4)
- **11/02/011:** a pulse sent along PQ into QR. Time to reach R; reflected and transmitted
  amplitudes. Key: 0.14 s, -1.5 cm, 2.0 cm.
- **11/01/010:** a given pulse 10/(5 + (x + 2t)^2): direction, speed, amplitude. Key: -x,
  2 m/s, 2 m.
- **11/01/007:** a given pulse 2/((x - 3t)^2 + 1): peak at t = 0, 1, 2 s. Key: peak
  2 cm, at x = 0, 3, 6 cm.

## Negative and boundary cases
- A pulse starting across the junction is refused.
- A shaped pulse on a non-uniform string with a junction is refused.
- A shapeless (legacy) pulse at a junction stays refused (r62).
- A fixed end inverts (r = -1); a free end keeps the sign.
- The transmitted width scales by v2/v1.
- The energy check: r^2 + (Z2/Z1) t^2 = 1 is already an implicit fact.

## Reserved transfer cases
Three problems written by a separate agent into `reserved/`, unread by the developer
until implementation is frozen. A fresh author agent solves them afterwards.

## Verification and stopping condition
- Regression tests with hand values.
- A Fable 5.2 (medium) review.
- The reserved run.
- The cost hypothesis compared with the actual changes.
- Stop after one review round and one reserved run.
