# Milestone 6: acoustics (fluid and solid media, acoustic amplitudes, sound level, powered sources)

**Charter tier:** light (one bounded shared extension). Written BEFORE implementation.

## What is blocked, and at which layer (from `eval/diag1/LAYERS.md`)
- **Gap 1 (9 problems), qualification + observation:** no link between displacement
  amplitude, pressure amplitude and intensity in a medium.
- **Gap 2 (7), qualification + assembly:** no liquid or solid media; no rod resonator.
- **Gap 5 (4), maths:** no sound level in dB.
- **Gap 11 (4), assembly:** `emitters` (power, intensity) and `sources` (amplitude,
  phase) are two components for one physical thing.

## Why existing capabilities are insufficient
- Gas media carry only a speed; the density, when given, is used only to compute that
  speed.
- Waves carry a displacement amplitude with no pressure counterpart.
- Rays add amplitudes with no unit or physical link to power.
- Resonators accept strings and pipes only.

## Smallest shared change (scope)
1. **Media:** every gas or fluid exposes density and bulk modulus where known.
   - A new `fluid` medium: liquid by bulk modulus and density, or by speed and density.
   - A new `rod` medium: Young's modulus and density, or mass, length and area, giving a
     longitudinal speed.
2. **Acoustic wave quantities:** on a fluid/gas medium, a harmonic wave's amplitude may be
   given as displacement `A`, `pressure_amplitude` or `intensity`; the others follow from
   p0 = rho v omega s0 and I = p0^2 / (2 rho v). New observables:
   - `pressure_amplitude(w)`;
   - `intensity(w)`, which also extends to rays;
   - `displacement_amplitude(w)`, the same as `amplitude`.
3. **Sound level:**
   - `sound_level(I)`, with reference I0 = 1e-12 W/m^2 stated as a definition in
     FORMAT.md;
   - its inverse, `intensity_of_level(L)`.
4. **Powered sources:** a `sources` entry may give `power` instead of `A`, with
   `spreading: spherical | hemispherical`. Its pressure amplitude at distance s then
   follows from I = P/(4 pi s^2) or P/(2 pi s^2) in its medium. `emitters` stay for
   compatibility but are no longer needed.
5. **Rod resonator:** `type: rod` on a rod medium, with ends `clamped | free` (clamped =
   displacement node), reusing the existing mode logic.

## Excluded
- Doppler, gas mixtures, rms speed, springs and statics, side holes, loci.
- Transverse waves in rods (bending), and energy integrals.

## Implementation-cost hypothesis
After this milestone, each of these needs scene data and verification only: no new
validator, compiler branch or observable.
- **(a)** A sound wave in any gas, liquid or solid given by any one of displacement,
  pressure or intensity, with the other two asked for.
- **(b)** A point or hemispherical source of stated power, asked for pressure,
  displacement or intensity at a point, or a level in dB, including several such sources
  (incoherent or coherent).
- **(c)** The speed of sound in a liquid from compressibility data.
- **(d)** Longitudinal modes of a rod with any end combination.

Expected production work: `scene.py` (media, wave amplitudes), `rays.py` (powered
sources, intensity), `modes.py` or `scene.py` (rod resonator), plus documentation.

## Motivating arrangements (exposed, run 4)
- **11/03/001:** a source of stated power, with pressure and displacement amplitude at
  1.5 m (gaps 1 and 11). Key: 4.98 Pa, 3e-6 m.
- **24/01/cnt_004:** the speed of sound in water from a pressure change and a volume change
  (gap 2). Key: 1414 m/s.
- **11/05/004(a):** a longitudinal fundamental of a steel wire as a rod (gap 2). Key:
  707 Hz.
- **11/03/003:** sound level of a hemispherical source, 1 and 5 incoherent dogs (gaps 5
  and 11). Key: 68 dB, 75 dB.

## Negative and boundary cases (to write as tests)
- A pressure amplitude asked on a gas with no density gives undetermined (no silent
  density).
- Two amplitude specifications at once is an error.
- A level of zero intensity is an error.
- A rod resonator on a gas, or a pipe on a rod, is refused.
- `power` together with `A`, or `power` with spreading `none`, is refused.
- An incoherent sum of 5 equal sources gives +10 log10(5) dB.

## Reserved transfer cases
Three problems written by a separate agent into `reserved/`, with keys and independent
solutions.
- The developer does not read them until implementation is frozen.
- A fresh author agent solves them afterwards; a grader compares.
- Their exposure history is recorded.

## Verification and stopping condition
- Regression tests per law with hand values; all suites green.
- A Fable 5.2 (medium) review.
- The reserved cases run.
- The cost hypothesis compared with the actual production changes.
- The milestone stops after one review round and one reserved run, whatever the outcome.
