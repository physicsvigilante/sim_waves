# Review 12: milestone 12 (deciding services, em waves)

Scenes are in `eval/review12/`. Regression suite: 156/156 pass. f0 = 1 GHz unless stated.

## Findings, by severity

### 1. HIGH, CONFIRMED: the gas guard is bypassed by a symbolic speed
- **Scene:** `g2.yaml`. Gas with `v: vv`, `given: vv == 3e8[m/s]`, 10 GHz echo from a car at 30 m/s.
- **Observed:** `solved vv = 300000000`, `shift = 2000.00` (the classical value), with no warning.
- **Expected:** refused with the pointer to `type: em`, as in r150.
- **Why:** `_not_light` runs only at construction, on numbers; nothing re-checks after solving.
- **Also:** `g1.yaml` (v from a wavelength), `g7.yaml` (temperature solved to 2.2e14 K).

### 2. HIGH, CONFIRMED: Doppler in an em material (`n` or `v` < c) is wrong
- **Scene:** `e3.yaml`. n = 1.5, source approaching at 0.1c; separately, receiver approaching at 0.1c.
- **Observed:** 1.16316e9 Hz in both cases.
- **Expected:** source moving: f0·sqrt(1−β²)/(1−nβ) = 1.17058e9. Receiver moving: f0·γ(1+nβ) = 1.15579e9.
- **Why:** `trace` passes `medium.speed()` (c/n) to `_gamma`; time dilation needs vacuum c.
- **Also:** `wave_speed_seen` returns c/n = 1.99862e8 for the moving listener. Relativistic velocity addition gives 0.71875c = 2.1548e8.

### 3. HIGH, CONFIRMED: `wavelength()` on an em ray with a moving source is wrong
- **Scene:** `e1.yaml`, `e5.yaml`. Source approaching at 0.6c, listener at rest.
- **Observed:** 0.119917 m (c / 2.5 GHz), while `frequency` correctly gives 2 GHz.
- **Expected:** c / 2 GHz = 0.149896 m.
- **Why:** `air_wavelength` rebuilds the rate without the 1/γ_source factor.
- **Also:** with a moving listener (`e5`) it returns c/f0 = 0.2998 m; the listener measures c/f = 0.1499 m.

### 4. MEDIUM, CONFIRMED: sound observables are not refused on em
- **Scene:** `e5.yaml`.
- **Observed:** `intensity(w)` = 1/(40π), and `sound_level(intensity(w))` = 99.0 dB for a radio source.
- **Expected:** refused, per PLAN item 4 and FORMAT line 417.
- **Why:** no em check exists in the intensity or level paths; no test covers it.

### 5. MEDIUM, CONFIRMED: the faster-than-light check is bypassed by unknowns
- **Scene:** `e12.yaml` (v unknown, fixed by λ = 0.6 m at 1 GHz) and `e8.yaml` (n unknown).
- **Observed:** `solved vv = 600000000`; `solved nn = 0.499654`.
- **Expected:** rejected as inconsistent (v > c, n < 1), as in r155.
- **Why:** both checks run only on numbers at construction.

### 6. LOW: `_decide_cases` is narrower than FORMAT says (refusals only, never wrong)
- **Scene:** `d1.yaml`, `d3.yaml`. "Cannot decide" for `abs(q-1)+abs(q+1) >= 2`, `max(a,b) >= a`, `max(abs(q),1) >= 1`, and `abs(y-1) <= 1` with 0 < y < 2.
- **Why (SUSPECTED):** `solveset` on a compound (And) case condition raises and is caught; two-symbol cases return None at once.

### 7. LOW: wording
- Light-speed violations (`e4`, `e9`) are refused, but the message says "speed of sound relative to the air".

## Verified correct (by hand)
- **Relativistic Doppler in vacuum** (`e1`, `e2`, `e6`, `e9`-`e11`, `e14`), β = 0.6:
  - approach 2 GHz, recession 0.5 GHz;
  - transverse at emission 0.8; moving receiver at closest approach 1.25; oblique cases 1.25 and 0.8;
  - both moving: 4, 0.25, and 1 when co-moving;
  - mirror: 4 approaching, 0.25 receding; moving gun (0.2c) and car (0.5c): 4.5;
  - circling source 0.8, circling receiver 1.25; static-wall image 0.8; symbolic u;
  - radar speed solved back from the shift;
  - `wave_speed_seen` = c; wind refused; speeds ≥ c refused; MHz, GHz.
- **`_decide_cases`** (`d1`-`d3`): about 45 comparisons, no wrong decision (infeasible cases, bounds, integers, nested abs, Max/Min, excluded end points, chains). Mixed-truth statements stay undecided.
- **`nearest`** (`n1`, `n2`): negatives, opposite signs, zero and near-zero, exact hits, duplicates, the tie at exactly 2x (refused), units, mixed dimensions and symbols (refused), arbitrary dependence (caught). The relative rule cannot pick an option that is not also nearest in absolute distance.
- **`item` / `spacing`** (`s1`, `s2`): out-of-range, 0, negative, fractional n; non-lists; single-entry and empty lists; decimal inputs; end correction; symbolic medium (refused).
- **`wave_speed_seen`, sound** (`w1`): perpendicular wind 338.824, oblique listener 339.706, reflected 330, direct 350, own echo 370, moving wall 340, wind 355; unchanged by source motion.
- **Guard with numbers:** v, γP/ρ, γRT/M, bulk modulus and an arbitrary value are refused; 99999 m/s passes.
- **Sound Doppler** (`w1`): 564.516, 563.492 (wind), 596.774 (own echo), 499.567 (oblique), 514.925 (moving wall), λ = 0.62 m.

## Not tested
- `spacing` on a genuinely unequal list (my `maxima` scene was malformed); the refusal was read in code only.
