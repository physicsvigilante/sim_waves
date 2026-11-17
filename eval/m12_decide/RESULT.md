# Milestone 12 (deciding services, electromagnetic waves): result

## Transfer evidence (reserved cases)
- **Setup:** four original problems by a separate agent, prompted with the PLAN scope.
  Keys were checked by formula and by Python. The developer did not read them before the
  freeze (`run/FROZEN.md5`).
- **Author:** a fresh Claude Sonnet agent, given FORMAT.md and examples only.

| Case | Structure | Attempts | Key match | Engine fit |
|---|---|---|---|---|
| R1 | radar on a moving patrol car, echo from an approaching car, beat with the transmitted signal; rounded options | 3 | yes: B, **by hand** | none (no observable evaluated; see below) |
| R2 | resonance tube with end correction: spacing, a specific resonance, a count, a decoy | 1 | yes: A, B | full |
| R3 | wind and a running observer: sound speed seen and frequency heard (rounded pairs) | 1 | yes: A | full |
| R4 | sonometer and fork over a tension range: for-all statements through \|f1 − f2\| | 1 | yes: A, C | full |

R2–R4 were engine-derived. R1 failed on three production gaps, all fixed after the run:
1. **The book's rounded c = 3e8 m/s could not be stated.** `v: 3e8 m/s` was refused as
   faster than light. Fix: `c: 3e8 m/s` on an `em` medium sets the problem's c for
   travel and time dilation alike.
2. **`speed(medium)` refused `em`.** Fixed.
3. **The unit `us` (microseconds) did not exist.** `us` and `ns` were added.

With only these fixes, the author's own R1 v3 scene runs as written: beat = 4200.00 Hz,
`nearest` picks option 2 (B), and the result is the same at every scaling. It is kept as
regression r161. This re-run was done by the developer after the freeze; it is not a
transfer result.

## Cost hypothesis vs actual
- **(a) A rounded option picked by the engine:** confirmed (R4 statements; R3 needed the
  speed and frequency paired, see friction).
- **(b) For-all statements through `abs`:** confirmed (R4).
- **(c) Radar Doppler:** **not confirmed in transfer** (R1 failed on the gaps above).
  After the fix it works on the author's scene.
- **(d) The speed of sound seen by a moving listener:** confirmed (R3).

## Friction (for later)
- **`nearest` with paired options** (speed and frequency together): options that share
  one value make a tie on that value. A paired form, nearest by several values, is a
  candidate.
- **"Beat with the transmitted signal"** worked as `beat_frequency(frequency(echo, t=),
  frequency(gun))`, but FORMAT.md has no example of it.

## Production changes by reason
- **Planned:**
  - comparisons decided through `abs`, `max` and `min`;
  - `nearest`, `item` and `spacing`;
  - `type: em` with relativistic Doppler;
  - the guard against light speeds in gases and fluids;
  - `wave_speed_seen`;
  - the units MHz and GHz.
- **Review 12 fixes (r156–r160):**
  - the guard after solving;
  - vacuum c for time dilation;
  - the em wavelength;
  - sound quantities refused for light;
  - unknown v or n checked against c.
- **Post-run fixes (r161):** `c:` for the book's rounded c, `speed(em)`, and the units
  `us` and `ns`.
