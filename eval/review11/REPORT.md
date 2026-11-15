# Review m11: ranged arbitrary values and comparisons in observe

Scenes are in eval/review11/. Regression (143) and negative (12) suites pass.

## Findings, by severity

1. **CONFIRMED, high: `==` has an absolute tolerance floor, so unequal numbers are reported equal** (a01, a03).
   `_decide_comparison` uses `|d| < 1e-12*(1+|lhs|)`.
   - `1e-13[W/m^2] == 2e-13[W/m^2]` -> True; `1e-16 == 0` -> True; `300000000 == 300000000.0001` -> True; `z == 6.000000000001` (z solved = 6) -> True. Expected False: inputs are exact rationals.
   - Contradiction: with w solved = 1e-14, both `w == 0` and `w > 0` are True.

2. **CONFIRMED, high: a comparison that flips near a range end is reported True** (b01, b02, b05, c01, a05).
   Samples are only the stated value and 3/37/61/97 %.
   - c01 (r138 scene, u below 340 m/s): `frequency > 505[Hz]` -> True. By hand f = 500*340/(340-u) > 505 only if u > 3.37 m/s; expected "depends".
   - b01: `u < 335[m/s]`, `u > 5[m/s]` -> True. b05: `tan(th) < 30` for th below pi/2 -> True (tan is unbounded).
   - above-only (b02): `L > 1.01[m]` and `L < 100[m]` with `above: 1 m` -> True (samples span 1.0104 to ~91 m).
   A True/False collapses the value, so five samples are far weaker evidence than for numeric results; the basis says "decided; ... sampled", but FORMAT says "at every arbitrary value".

3. **CONFIRMED, medium: ranged names four positions apart move together** (b03, b07).
   The fraction index is `(k+j) % 4`. In b07, a (34 m/s, below 340) and b (17 m/s, below 170) are names 0 and 4: `a/b` = 2 "exact", `a == 2*b` True, `a > b` True. Expected "depends".

4. **CONFIRMED, medium: `explore: {vary: {arbitrary.u: [...]}}` (the documented path) drops the range** (c02).
   The dict is replaced by a plain value: 400 m/s is not refused as out of range, and variants revert to x0.01-x89 scalings (results merely unavailable). `arbitrary.u.value` works (c03).

5. **CONFIRMED, low: a non-real comparison is decided** (a05 g9): `sqrt(-1) > 0` -> False. Expected an error.

6. **CONFIRMED, low: internal errors and a raw traceback.**
   - `a + 1 == a`, `q == q + 1e-13` (symbolic lhs, numeric difference): "engine internal error (TypeError)". Expected False (a02 s22, d14).
   - `above: "sqrt(-1) m/s"`: raw Python traceback (d07).

7. **SUSPECTED, low: `_sign_ok` absolute 1e-15 threshold** when sympy cannot sign a number; it would misjudge tiny SI differences. Not reproduced: sympy signed every case tried (a04).

8. **Note: conservative refusals** (safe). A chain with one undecidable link is refused even when another link is definitely False (a05 g8). A bound that names another arbitrary value is refused with a misleading "same unit dimension" message (b04).

## Verified correct
- Ranged values stay inside their ranges: `max(u, 340 m/s)` = 340; `min(L, 1 m)` = 1 (above-only); both-bound, expression bounds (sqrt, pi/2) and six mixed names (b01, b02, b05).
- Refused: value outside or on a bound, below <= above, negative above, missing or mismatched bound unit, symbolic bound, unknown keys, dict without a bound (d01-d10).
- Dimension checks: `2[m] > 3`, `1[m] == 1[s]`, `u < 340` refused; `100[cm] == 1[m]`, `2[km] > 1500[m]` True.
- Bounds (n > 1): `n == 1` False, `n**2 > n`, `1/n < 1`, `n > 1 > 1/n` True. Free symbols: `a == b`, `a > b`, `q**2 > 0` refused.
- Solved unknowns in comparisons; unknowns depending on arbitrary values are flagged.
- "depends" verdicts where truth changes mid-range (b01 c5/c8/c12; c01 `< 10000 Hz`); no false "depends" seen.
- m9 behaviour for unranged values is unchanged (b06).
