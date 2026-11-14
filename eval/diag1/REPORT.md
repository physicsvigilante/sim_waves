# Diagnostic 1: report (per charter section 14)

**Scope (approved):**
- Run 4 gaps attributed to layers.
- Track A: a teacher revision and investigation test on two structurally different scenes.
- Track B: one rejected combination (pulses at junctions).

**No production changes were made during the diagnostic.** Frozen inputs are in
`FROZEN.md5` (task, hidden expectations, FORMAT.md).

## Evidence and independence
- **Baselines:** developer-authored fixtures (`baselines/`). Not independent.
- **Teacher:** a fresh Claude Sonnet agent with no engine source, FORMAT.md and examples
  only; it did not see the expectations. Independence level: fresh context, different model
  from the developer.
- **Expectations:** hand calculations written and hashed before the run
  (`expected/EXPECTED.md`). The developer compared outcomes against them.
- **Teacher's rule breaches:** E3 used 4 attempts (limit 3), and the agent ran the
  baseline once to compare. Both are disclosed in `teacher/REPORT.md`.

## Track A: outcomes per operation

| Step | Operation | Outcome | Engine result vs frozen expectation | Responsible layer for friction |
|---|---|---|---|---|
| E1 | property change (ceiling 25 to 30 m) | done, 1 attempt | 14.164 m = expected 60*sqrt(5) - 120 | none |
| E2 | structural change (rigid to open boundary) | done, 1 attempt | 20 m = expected | none |
| E3 | new question (loudness vs listener distance) | done, 4 attempts | 4 at 120 m, the only maximum = expected | observation: no "value at a point" (needed an `illustrate` workaround); maths: an empty `minima` list aborts the whole run |
| E4 | view of E3 | done | plot correct; y-range 2.85 to 4 hides the minimum level | presentation: auto y-range |
| P1 | property change (v = 350) | done, 1 attempt | 102.94 Hz = expected | none |
| P2 | structural change (open the closed end) | done, 1 attempt | 200 Hz; 2nd harmonic 400 Hz exists = expected | none |
| P3 | new question (nodes; 500 Hz fork) | done, 1 attempt | nodes 0, 0.567 m; pressure nodes 0.283, 0.85 m; lengths 0.51, 0.85, 1.19 m = expected | authoring: the fork question needed a second resonator with a symbolic length |
| P4 | view of a mode profile | done, 3 attempts | profile correct | presentation: the viewer crashes on a list-valued observe (defect); authoring: `x` is reserved |

- **Physical results:** all 8 operations are correct against the frozen expectations.
  There were no wrong numbers.
- **Revision:** both property changes and both structural changes were one-line edits.
  Parents were named and unchanged facts preserved. The engine re-derived the consequences
  (e.g. the phase flip at an open boundary) without author physics.
- **Investigation:** new questions worked on unchanged physics. The friction is in the
  observation and presentation layers, not physics or assembly.
- **Not tested:**
  - a revision chain (a revision of a revision);
  - comparison of a baseline and a revision in one view;
  - real teachers or students (educational rung 3 and above).

## Track B: pulses at junctions
See `trackB/DIAGNOSIS.md`.
- **Immediate behaviour:** not refused. The pulse silently ignores the junction and the
  medium extent (silent wrong position). This is a defect, not a restriction.
- **Underlying restriction:** reflection and transmission are missing because a pulse has
  no shape. That is a conservative software restriction in the assembly layer. The physics
  is admissible for uniform non-dispersive strings with the existing coefficients, and not
  for non-uniform strings.

## Layer attribution of the run 4 gaps
See `LAYERS.md`.
- New or extended laws: acoustic amplitudes, fluid and solid media, gas extras.
- Assembly: pulse shape, and the emitter/source split (two components for one physical
  thing).
- Observation and maths: travel time, dB, families, energy integrals.
- Retained restrictions: mechanics outside waves, side holes in pipes.

## Defects found (to correct after the diagnostic, each with a test)
1. A pulse on a junctioned string is accepted and ignores the junction (silent wrong).
2. The viewer crashes on a list-valued observe.
3. One failing or empty observable aborts the whole run. The charter says an undefined
   unrequested quantity must not invalidate the others: the run should report it per
   observable.

## Next decision (one)
**Corrections first.** Fix the 3 defects above. Add a "value at a point" maths service
(`at(expr, d=120[m])`), which a teacher needs and which also replaces the `illustrate`
workaround. These are routine, with no architecture review.

**Then one bounded shared extension: acoustics with a unified source.**
- **Scope:**
  - fluid and solid media (B, Y), plus rod resonators reusing the mode logic;
  - pressure, displacement and intensity amplitudes linked by the medium;
  - a dB service;
  - one source object carrying power or amplitude, replacing the emitter/source split.
- **Excluded:** mechanics outside waves, side holes, loci, Doppler.
- **Motivating arrangements (exposed, run 4):**
  - 11/03/013 (pressure amplitude from intensity);
  - 24/01/cnt_004 (sound speed in a liquid);
  - 11/05/004 (rod).
- **Reserved transfer case:** 3 problems written by an agent the developer never reads,
  each with an independent key.
- **Implementation-cost hypothesis:** after this, these need only scene data and no new
  validators or branches:
  - a liquid, gas or solid medium;
  - an amplitude conversion between pressure, displacement and intensity;
  - a dB level;
  - a point source with given power.
- **Verification:** regression per law with hand values; a Fable review; the reserved
  cases; the cost hypothesis compared with the actual changes.
