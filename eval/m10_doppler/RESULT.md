# Milestone 10 (Doppler effect): result

## Transfer evidence (reserved cases)
- **Setup:** four Doppler problems from the book (wanes_full.pdf). A separate agent
  chose them by a seeded draw within the PLAN scope, and wrote keys checked two ways.
  The developer did not read them before the freeze (`run/FROZEN.md5`).
- **Author:** a fresh Claude Sonnet agent, given FORMAT.md and examples only.
- **Grading:** by the developer after the run (not independent).

| Case | Book id | Structure | Attempts | Key match | Hand steps |
|---|---|---|---|---|---|
| R1 | single/44 | source passes a still listener: shape of f(t) (graph options) | 2 | yes: B | the shape read from sampled times; a 1 m offset from the line chosen by the author |
| R2 | jee_adv/17 | 1D source approaching at two speeds: ratio of heard frequencies | 1 | yes: D (ratio 19/18) | none |
| R3 | jee_main/50 | source and observer approaching: f against the observer's speed (graph and slope options) | 2 | yes: A (slope f0/(v−vs) proved by `equivalent`) | checked at illustrative numbers |
| R4 | jee_adv/50 | source passes at a distance: infer speed and f_m from an f(t) curve | 2 | **defective item:** the printed f0 = 2200 Hz contradicts the figure's 2000 Hz. As printed, the author answered A, which matches key reading 2. The alternative (figure) reading gives C, D, which matches the book's key. | comparisons with 2500 and 2250 Hz done by hand |

R1–R3 match the book's key. On R4 the author found both readings without help and
answered each correctly.

## Cost hypothesis vs actual
- **(a) Constant-velocity sources and listeners in any direction:** confirmed (R2, R3,
  R4), with no production change.
- **(b) Walls and echo beats:** not exercised by the reserved draw. It was covered by the
  design set and review 10 (r116, r117, r133, r135).
- **(c) Hearing over time (passing source):** confirmed (R1, R4).
  - The engine gives f at any instant and draws f(t).
  - There is no observable for the "shape" of a curve, so the author judged it from
    samples. This is acceptable for the engine, which stays close to physics; the
    framing is the LLM's job.

## Friction (layer attribution)
- **`arbitrary` and speeds (maths and format):** the ×89 scaling turns any arbitrary
  speed supersonic, so the author could not use `arbitrary` for an unstated source speed
  and used illustrative values instead. This happened in R1, R3 and R4, and also in the
  design set.
  - **Candidate for later:** arbitrary values with a stated range, e.g.
    `u: {value: 20 m/s, below: 340 m/s}`, scaled only within it.
- **Comparisons in `observe` (format):** comparisons are refused, so R4's option checks
  were done by hand. `step(a - b)` works, but FORMAT.md does not say so.
  - **Candidate for later:** a documented comparison observable.
- **Inconsistent sources (LLM side):** R4 needed one scene per reading. This is the
  intended behaviour.

## Production changes by reason
- **Planned:**
  - motion: `velocity`, `starts`, `circle`, `emits_from`;
  - moving walls and wind;
  - emission-time Doppler;
  - `emitted_at`, `arrives_at` and the wavelength in air;
  - `beat_frequency(..., t=)`;
  - f(t) plots.
- **Review 10 fixes (r129–r135):**
  - supersonic motion from solved unknowns, and walls in wind;
  - no echo once the wall is passed;
  - leaks of `period`, `omega` and `k`;
  - an unknown wall speed can now be solved;
  - the instant a motion starts.
- **m9 follow-up:** a scaled run that fails is now reported as a failure.

No production change was needed after the frozen run.
