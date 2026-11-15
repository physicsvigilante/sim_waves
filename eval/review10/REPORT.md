# Review 10: Doppler milestone (independent review)

Scenes are in this folder; `num.py` is an independent numeric check (bisection for the emission
time, finite difference). v = 340 m/s, f = 500 Hz.

## Findings, ranked

### 1. HIGH, CONFIRMED: supersonic motion is not refused when the speed comes from an unknown; a negative frequency is reported
- Scene `s1.yaml`: `unknowns: {u: positive}`, source velocity `[u, 0]` approaching a still listener,
  `given: u == 400[m/s]`.
- Observed: `f0 = -8500/3 (= -2833.33)` Hz for `frequency(rb, emitted=0[s])`, exit as a normal result.
- Expected: the supersonic refusal (the same scene with a number, or with `arbitrary: {u: 400 m/s}`
  in `s2.yaml`, is refused correctly).
- Why: `_check_subsonic` runs on the raw symbol, `_decide` returns None, and the check passes. The
  re-check promised in the `Leg._valid` comment does not exist.
- Related, `f7.yaml`: a receding source solves to `u = 510` m/s with no refusal.

### 2. HIGH, CONFIRMED: a wall that is supersonic relative to the air gives a negative frequency
- Scene `s3.yaml`: wind `[10, 0]`, wall velocity `[-335, 0]`, still source and listener.
- Observed: `f = -452100/7 (= -64585.7)` Hz, `arr = 15.04 s`.
- Expected: refusal. The echo travels at 330 m/s over the ground and the wall at 335 m/s, so the
  wall outruns its own echo.
- Why: `legs()` compares the wall's ground speed with v and ignores the wind.

### 3. HIGH, CONFIRMED: objects pass through the wall and the engine keeps answering
The same-side test is made once, on the t = 0 positions.
- `h4_wallcross.yaml`: wall from 200 m at −5 m/s, still source at 0, listener P at 50 m.
  - `frequency(e, t=35[s])` gives 500 (the wall is at 25 m, P is behind it).
  - `frequency(e, t=50[s])` gives 485.507 (the wall is past the source).
  - `arrives_at(e, emitted=35[s])` gives 35.147.
- `b1_car_wall.yaml` `late`: the car meets the approaching wall at t = 20 s; `frequency(a, t=30[s])`
  gives 431.562.
- `k2.yaml` `crossed` (still wall, image method): the car crosses the wall plane at t = 4 s;
  `frequency(e, t=8[s])` gives 470.600, the value for a mirror that no longer applies.
- Expected in all of these: refusal ("source or listener is at or behind the wall").

### 4. MEDIUM, CONFIRMED: `period(ray)`, `omega(ray)`, `k(ray)` leak the source's values on a moving ray
- `a1_both.yaml`: `period(r) = 1/500`, `omega(r) = 1000π`, `k(r) = 50π/17`, while the heard
  frequency is 554.69 Hz.
- `frequency(r)`, `wavelength(r)` and `length(r)` are refused on the same ray; these three are not.

### 5. MEDIUM, CONFIRMED: an unknown wall speed cannot be solved (refusal, not a wrong answer)
- `f3_unknown_wall.yaml`, `f3b.yaml`: wall velocity `[-u, 0]`, `frequency(e, emitted=0[s]) == 520[Hz]`,
  with and without a bound `u < 100[m/s]`.
- Observed: UndeterminedError "cannot tell on which side the listener is at t = 500/(u + 340) ...
  ask with emitted=0 s". The advice is what the scene already does.
- Expected: u = 20/3 m/s. Plan hypothesis (b) is not met for unknown wall speeds.
- Related (`s1.yaml`): with a solved speed, `t=` queries are refused; the solved value is not
  substituted into the motion.

### 6. LOW, CONFIRMED
- `h3_leaks.yaml`: a stated-length ray (`length: 3 m`) from a moving source gives
  `frequency(tube) = 500` with no time; `ray.moving` is never set for such rays.
- `e1_starts.yaml` `at5`: a still listener at 350 m asked at t = 5 s, the instant the source
  starts, is refused, although the sound heard then left at t = 4 s and the answer is 500 Hz.
  Safe, but a false refusal.
- `beat_frequency` has no `emitted=`; `beat_frequency(ray, 500[Hz], t=...)` is refused.

## Verified correct (ran; match hand formulas or `num.py` to 8+ digits)
- **Line, both moving:** approaching 554.6875, after crossing 451.389, same direction 515.625,
  overtaken 486.111, chasing 513.889; refused exactly at the crossing.
- **Wind:** along 530.303, against 471.429, moving listener 521.429; wavelengths 0.66 / 0.70 m.
- **Walls:** car to still wall 562.5; receding wall 471.429; approaching wall with moving car
  579.291; echo/direct beats 59.028; echo with wind 530.303, 562.443, 514.945.
- **Oblique:** `emitted=` at closest approach gives exactly 500; other times match; moving
  listener; wind at an angle; 3D with 3D wind.
- **Circles:** source on a circle, both on circles, circling listener with linear source, with
  wind, listener at the centre (500).
- **Timing:** `starts`, `emits_from`, no-sound-yet, arrival just after the start.
- **Consistency:** `arrives_at(emitted_at(t)) == t` and the reverse (line, oblique, circle).
- **Solving:** unknown source speed from beats (340/49); real-valued u reported ambiguous with
  both roots; arbitrary ratios 11/9, 9/11; dependence on arbitrary values is NOT AVAILABLE.
- **Two sources:** `beat_frequency` 40.602. **Image method:** 526.306, and 500 at closest approach.
- **Refusals:** numeric supersonic source, listener, circle, wall; wall off line; oblique wind
  with reflection; missing time; co-located source and listener.
- **No leaks:** `length`, `path_difference`, `relative_intensity`, `amplitude`, `phase` refused on
  moving or windy rays; the plot gives nulls before the first sound.
- **Regression:** all 36 scenes using sources or rays pass (r115-r128 included); `tests/negative`
  12/12. The full regression run was cut off after 55 scenes (all passing), so it is incomplete.
