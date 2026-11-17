# Milestone 13 (tension from mechanics, frequency bands, output units): result

## Transfer evidence (reserved cases)
- **Setup:** three original problems by a separate agent, prompted with the PLAN scope.
  The keys were checked two ways. The developer did not read them before the freeze
  (`run/FROZEN.md5`).
- **Author:** a fresh Claude Sonnet agent, given FORMAT.md and examples only.
- **Review:** by Opus, standing in for Fable 5.2, which needed usage credits.

| Case | Structure | Attempts | Key match | Engine fit |
|---|---|---|---|---|
| R1 | sonometer with the load in air and then immersed in oil; beats with a fork give the fork's frequency | 1 | yes: 84 Hz | full (the engine's f = 100, 80 Hz; f0 solved from two beat facts) |
| R2 | wire tension from a Young's-modulus strain; period of the fundamental in ms | 2 | yes: 20 ms | partial by the author's own rating (it wrote 1/frequency itself, since `period(resonator)` was missing) |
| R3 | closed pipe swept over a band: which and how many resonances, and their spacing | 1 | yes: A, B, D | full |

All 3 matched.

## Cost hypothesis vs actual
- **(a) Tension from a load with buoyancy, or from strain:** confirmed (R1, R2).
- **(b) A band question:** confirmed (R3).
- **(c) Answers in the asked unit:** confirmed for R2 (ms). R1's `f0 in Hz` was refused,
  because a solved unknown with no field fixing its dimension could not be checked.

## Post-run fixes (r174, r175)
- `period(resonator, harmonic=n)`.
- An unknown's dimension for `in <unit>` is now taken from the facts that use it. A unit
  that does not fit is still refused.

## Friction (for later)
- **"Is there a resonance at exactly f?"** Authors used `resonances` with lo = hi. A
  direct form, `resonant_at(resonator, f=...)`, is a candidate.

## Production changes by reason
- **Planned:**
  - `tension: {weight: ...}` with buoyancy, and `{stretch: ...}`;
  - `frequencies_in`;
  - `in <unit>`;
  - the radar-beat docs.
- **Review 13 fixes (r168–r173):**
  - the degC offset;
  - angle units refused;
  - positivity of k, Y, mass, g and lengths;
  - the immersed fraction kept at 1 or less;
  - harness units;
  - lists and unknowns converted with `in`;
  - rounded areas accepted;
  - band start near lo.
- **Post-run fixes (r174, r175):** see above.
