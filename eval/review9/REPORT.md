# Review 9: scale-free questions (arbitrary values, bounds, log systems)

Scratch scenes are in this folder (`a*`, `b*`, `c*`, `d1`, `e*`). All findings CONFIRMED by running unless marked.

## Findings, by severity

**1. HIGH: small-magnitude answers always pass as "independent" (silent leak).** `a1`, `a6`, `a7`.
`_same_result` accepts `|a-b| <= 1e-9*(1+|a|)`, an absolute 1e-9 floor in SI.
- `a1`: `arbitrary: {P: 1e-9 W}`, `intensity(a)` at 1 m. Observed `I = 7.96e-11 <independent of arbitrary values>`. Expected NOT AVAILABLE (I is proportional to P).
- `a6`: `A0: 1e-10 m`; `2*A0` and `A0^2/1[m]` reported as independent. `a7`: solved unknown `B == 3*A0` printed with no "depends" note.
- Sound intensities, displacement amplitudes and small masses all live below 1e-9. Fix: purely relative tolerance.

**2. HIGH: threshold dependence is missed by three scalings (0.61x to 1.37x).** `a2`, arbitrary `L: 1 m`.
- `max(L, 5[m])` = 5, `step(L - 0.5[m])` = 1, `abs(L - 3[m]) + L` = 3, `min(frequency(r1,1), 10[Hz])` = 10, all tagged independent. Each depends on L outside the sampled window. Same risk for counts, piecewise shapes, rounding. The "(3 scalings)" basis overstates what was proved.

**3. HIGH: log systems lose roots and accept undefined logs (silent unique answer).**
- `c2`: `log(a^2)+log(b)==0`, `log(b)-log(a^2)==log(16)`, a real. Observed a=1/2, b=4. Expected ambiguous (a=+-1/2). `c13` likewise (a=1; expected +-1). Cause: `expand_log(force=True)` turns log(a^2) into 2*log(a).
- `c11`: same in the single-unknown path (`log(a^2)==log(4)` gives a=2 only).
- `c12`: `log(a)-log(b)==0`, `a*b==4`, `a<0`. Observed a=b=-2. Expected inconsistent: the logs are undefined there; the re-check passes because the complex parts cancel. `c7`: the same spurious root produces a false "ambiguous" (only (2,2) is real).

**4. MEDIUM: `>=` / `<=` bounds do not work.** `b2`, `b2b`, `b2c`. FORMAT's own example `L >= 2[m]` gives `AmbiguousError: given[0] cannot be decided for all symbol values`. Expected a bound with `abs(L-2)` = L-2. Clear error, but a documented feature is dead.

**5. MEDIUM: a bounded symbol escapes dimension checks.** `b4`: `L > 2[s]`, then L used as a resonator length and a wave frequency, plus `L + 1[kg]`. All accepted (f = 10/L, fw = L, L + 1). Without the bound (`b4b`) the engine refuses "used with two different dimensions". The bound constant's own dimension is never checked.

**6. MEDIUM: export ignores the milestone.** `e1`, `e2`.
- Solved unknowns that depend on arbitrary values are exported bare (`solved: {F: '100'}`), without the CLI's "depends" note.
- Panels drawn from arbitrary values carry no label (`uses_illustrative: False`).
- `explore: {vary: {arbitrary.L: ...}}` is presented as a "physical input" with a "source value" of 1 m: an invented fact.
- Bounds: export shows `solved u = n_from_bound` and asks to illustrate `n_from_bound`; `illustrate: {n: ...}` is refused as "must be a declared symbol".

**7. LOW.**
- `c3`: dependent log facts (infinitely many solutions) reported as `InconsistentError`; expected undetermined.
- `b3`: integer symbol with `m > 2` is an error, not "its own handling"; reversed form `1 < n` is not recognised (same error).
- `b11`: message leaks the internal name (`n_from_bound + 1 = 0`) and says "over-specifies" instead of "contradicts the bound".
- `d1`: a user symbol named `n_from_bound` (positive) merges with the internal one: `n_from_bound + n` shows `2*n - 1`.
- `b10`: `abs(L - 0.6[m])` with L > 0.5 m stays `Abs(L - 3/5)`: correct, just unsimplified.
- `c9`: `exp(a)*exp(b)==exp(5)` refused (clear error; fine for v0).
- SUSPECTED, not run: a false "depends" for numerical peaks (overlapping Gaussians) whose noise exceeds 1e-9 relative; if a scaled run fails, every observable is dropped, including ones that do not use the arbitrary values.

## Verified correct (hand-checked)
- r100 to r104 pass.
- `a11`, three arbitrary values, irrational paths: frequency ratio sqrt(6)/6, power and impedance ratio sqrt(6), wavelength sqrt(6)/3, travel-time sqrt(6)/2; no false "depends".
- `a4`: `a^2/b`, which the first scaling alone cannot see (1.37^2/1.8769 = 1), is caught by the second.
- `a3`: unknown solved from arbitrary values: F flagged as dependent, q = F/(mu L^2) = 4 f^2 = 10000 reported.
- Dimension checks on arbitrary names in fields and expressions (`a8`, `a8b`, `a10`); arbitrary/symbol name conflict (`a9`); comparisons refused in observe.
- Strict bounds: `b6` (n < -1 gives abs(n) = -n), `b7` (bound symbol in tension, shown back as sqrt(F-4)), `b1` (upper bound keeps positivity in display), `b3b` (weaker than positive is ignored harmlessly), `b8` (two bounds refused), `b5`/`b12` (contradictions found), `b9` (bound on an unknown picks the beat branch, f = 104).
- Logs: `c1` (d real gives ambiguous +-100), `c4` ambiguous (2,3)/(3,2), `c5` unique with `a < b`, `c6` fractional coefficients (2, 9), `c10` level difference plus algebraic fact (10 W, 1 W).
