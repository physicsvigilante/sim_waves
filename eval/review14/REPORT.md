# Review 14 report: milestone 14, stage 1

## Round 1
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-21.
- **Commit reviewed:** `3bbf5fa01ea29ddb96b3f64bab06015137fd60f4`.
- **Verdict:** FAIL, not approved for stage 2. There were 6 required findings (4 of them silent wrong answers) and 1 optional.
- **Method:** Astra predicted each result from the source path and could not run the engine. I reproduced every finding on the engine before fixing it. All 7 reproduced exactly as predicted.

| # | Severity | Finding | Reproduced | Fix | Tests |
|---|---|---|---|---|---|
| R1 | silent wrong answer | In `nearest(x in u, ...)`, an unknown option with no unit was read as a number in u. `nearest(1[m] in cm, ell, 90)` with ell = 1 m picked 2; it should pick 1. It also accepted ell = 1 s. | yes: pick = 2 | Such an option now passes the same dimension check as `x in u` (its recorded dimension, or the facts that use it) and is converted. If it cannot be checked, it is refused. (`expr.py` `_nearest_in`) | r196 (pick 1), r197 (refused) |
| R2 | silent wrong answer | With arbitrary values, `nearest` was accepted when the 5 sampled picks agreed, even though the value moved. For 1 + a/(a + 100000), all samples pick 1, but at a = 1e7 it picks 2. | yes: pick = 1, "sampled" | `nearest` stays unevaluated until `resolve_deferred`, which records the numbers it compared. Those numbers must be the same at every scaling, the same standard as any other value; otherwise it is refused. (`scene.py` `Nearest`, `resolve_deferred`; `run.py` `_evaluate_arbitrary`) | r198 |
| R3 | silent wrong answer | A bounded `limit()` at an interior point took one side only. With z < 1 m, the limit of \|z − 0.5\|/(z − 0.5) as z → 0.5 m gave −1; it does not exist. | yes: −1 | Both sides are taken at an interior point and must agree. One side, from inside, is used only at a domain edge. A limit in a whole-number symbol is refused. This also covers plain symbols with no bound, which used SymPy's right-side default. (`scene.py` `_limit`) | r199, r200, r201 (both edges, a positive symbol at 0, interior), r202 (integer) |
| R4 | silent wrong answer | Bracketed `20[degC]` was read as 20 K (a difference, with factor 1), then shifted by −273.15 in `nearest(x in degC, ...)`. It picked 2; it should pick 1. | yes: pick = 2 | `degC` inside unit brackets is refused as ambiguous (a temperature or a difference). Scene fields (`30 degC`) and `x in degC` are unchanged. No existing scene uses bracketed degC. (`expr.py` `_no_celsius`) | r203 (refused), r204 (bare options in degC, a K option converted with the offset) |
| R5 | wrong refusal | `7200[s] in h` was refused as an unknown unit. | yes | An explicit `in <unit>` is parsed directly. The rule against a lone trailing `h` applies only to field values. (`run.py` `_split_unit`) | r205 |
| R6 | uncaught error | Plotting a deferred `nearest()` raised a raw `NameError` in export. | yes: NameError | Plotting `nearest()` gives a clear `ViewError`. (`export.py`) | `tests/test_export.py` "m14 R6" |
| O1 | validation | `nearest(x in u, ...)` dropped keyword arguments. | yes: pick = 1 | Refused, as plain `nearest` does. (`expr.py`) | r206 |

**Related fixes found while fixing these:**
- `nearest()` inside a comparison is refused (r207).
- `nearest()` in a `given` fact is refused (r208).
- The `limit()` messages name the declared symbol, not its internal offset Δ(n). The Δ also crashed the Windows console while printing.

## Round 2
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-21.
- **Commit reviewed:** `a85c056ea38a15d5d786b8a289a25a4c4126ba3e`.
- **Verdict:** FAIL. Astra marked R1 and R3–R6 and O1 resolved. R2 was not resolved, and there were two new findings.
- **Reproduction:** all three reproduced on the engine as predicted.

| # | Severity | Finding | Reproduced | Fix | Tests |
|---|---|---|---|---|---|
| R2 (again) | silent wrong answer | Comparing the numbers `nearest` uses at the five sampled scalings is still not proof. 1 + exp(−((a − 2)/0.1)²) is within 1e-17 of 1 at every sample, but equals 2 at a = 2. | yes: pick = 1, "sampled" | When the compared numbers involve arbitrary values, the scene is run once more with those values as positive symbols over their whole allowed range. The pick stands only if every compared number simplifies to a constant (basis: "the compared value is proved independent of the arbitrary values"). Otherwise it is refused. (`run.py` `_symbolic_scale`, `_nearest_proved`, `_evaluate_arbitrary`) | r209 (the narrow bump: refused), r210 (an exact ratio of 2: proved, pick 2) |
| N1 | internal error | A `nearest()` inside another `nearest()` raised a TypeError. | yes | `resolve_deferred` resolves from the inside out: an inner pick is put into the outer call before it is decided. (`scene.py`) | r211 (pick 2) |
| N2 | silent wrong answer | `limit(q, q, -1)` with `q` positive returned −1, a point the domain never approaches. | yes: −1 | The point must be in the closure of the variable's domain (≥ 0 for a positive or nonnegative symbol, ≤ 0 for a negative or nonpositive one, and real). Outside, it is refused. If the sign cannot be checked, it is refused. (`scene.py` `_limit`) | r212 (refused), r213 (symbolic point of unknown sign: refused) |

**Effect on run 7 (all 44 final scenes re-run):** no value changed and no pick was lost. Eight picks over arbitrary values are now proved instead of sampled: jee_main/19, single/182 and single/2 (newly decided in m14), and jee_advanced/23, jee_main/44, single/106, single/159 and single/26 (already decided before m14).

## Round 3
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-21, with two inline comments (`run.py:191`, `scene.py:2160`).
- **Commit reviewed:** `59acb34e82f2ed1f1cd6f6a426e17d1fc41df6bd`.
- **Verdict:** FAIL. Resolved: R1, R3–R6, O1 and N1; R2 resolved for its examples. One new finding (N3), and N2 only partly fixed.
- **Reproduction:** all four scenes reproduced on the engine as predicted.

| # | Severity | Finding | Reproduced | Fix | Tests |
|---|---|---|---|---|---|
| N3 | silent wrong answer | A proof that the `nearest` part is constant also skipped the check of the whole observable. `a + nearest(2, 1, 2)` gave 3 with a "proved" basis, although it is a + 2. | yes: 3 (and 2 for `a*nearest(...)`) | The proof replaces the whole-result check only when the observable *is* a single `nearest(...)` call. Anything around it gets the ordinary check of the whole value. The proof must also agree with the numeric run: the constants it finds must equal the numbers actually compared. (`run.py` `_is_bare_nearest`, `_nearest_proved`, `_evaluate_arbitrary`) | r214 (sum: refused), r215 (product: refused), r216 (`nearest(2,1,2) + 1`: still 3) |
| N2 (rest) | silent wrong answer, and a wrong refusal | With a bound, `limit` checked only the bound's offset and lost the symbol's own kind. With q positive and q < 1, `limit(q, q, -1)` gave −1; `limit(\|q\|/q, q, 0)` was refused, though it is 1. | yes: −1, and refused | `_limit` now works on the variable's domain: its kind (positive, nonnegative, ...) intersected with any stated bound. The point must lie in the closure of that domain. At an edge it is approached from inside only; at an interior point both sides must agree. The sides are chosen for the user's variable, then mapped to the bound's offset (reversed for an upper bound). Messages show the domain, e.g. "(0, 1)". (`scene.py` `_kind_interval`, `_limit`) | r217 (outside (0, 1): refused), r218 (lower edge 1, interior 1/4, upper edge −1); r186's message now names the domain |

## Round 4
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-21, with one inline comment (`scene.py:2179`).
- **Commit reviewed:** `0bae434265f262386c842053c5071bf499bc2dc4`.
- **Verdict:** FAIL on one new finding. Every earlier finding (R1–R6, O1, N1, N2, N3) is marked resolved.
- **Reproduction:** reproduced on the engine as predicted.

| # | Severity | Finding | Reproduced | Fix | Tests |
|---|---|---|---|---|---|
| N4 | silent wrong answer | A limit point whose reality is unknown was accepted. Only points known to be non-real were refused. With b real, `limit(1, q, sqrt(b))` gave 1 although b = −1 makes the point i, which a real q cannot approach. | yes: 1 (and `sqrt(b)` for `limit(q, q, sqrt(b))`) | The point must be proved real (`is_real is True`); otherwise the limit is refused with a clear message. (`scene.py` `_limit`) | r219 (refused), r220 (controls: `sqrt(b)` with b positive, and a real symbol c, are accepted) |

**Checked while fixing:** infinity cannot be written in scene expressions (`oo` is an unknown name), so limits toward infinity were never available to authors. Requiring a real point removes no capability.

## Round 5
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-21, with one inline comment (`scene.py:2213`).
- **Commit reviewed:** `cf3b180bcc2e37e0af1d0a21ee1d318a0045debf`.
- **Verdict:** FAIL on one new finding. N4 is marked resolved, and every earlier fix is unchanged.
- **Reproduction:** reproduced on the engine as predicted, along with the pole variant, and a third case with the same cause: `q/(c*q)` at q → 0 gave 1/c.

| # | Severity | Finding | Reproduced | Fix | Tests |
|---|---|---|---|---|---|
| N5 | silent wrong answer | With other symbols in the point or the expression, SymPy's limit is generic. Two agreeing one-sided results can hide values of those symbols where no limit exists. `limit(\|q\|/q, q, c)` with c real gave `Abs(c)/c`, although at c = 0 the sides are +1 and −1. `limit(1/q, q, c)` gave 1/c. | yes: `Abs(c)/c`, and `1/c` (also `1/c` for `q/(c*q)` at 0) | When any symbol other than the variable appears, SymPy's limit is not used. Instead the engine proves the limit for every allowed value of those symbols, or refuses: (1) every denominator of the original expression must be nonzero near the point, vanishing at most through a factor (x − a); (2) the simplified expression must be continuous at the point: negative powers need a nonzero base, fractional or symbolic powers and logs a positive one, and the only functions allowed are sin, cos, exp, Abs, Min and Max. The limit is then its value there. With no other symbols, the exact two-sided check is unchanged. (`scene.py` `_limit_by_continuity`) | r221 (jump: refused), r222 (pole: refused), r223 (`q/(c*q)`: refused), r224 (controls with c positive: 1/c, 1, 1) |

**Checked:** the documented small-quantity use still works, in the FORMAT example 23_05_asc_004 (beat/dl as dl → 0 with v and l symbols gives v/(2l²)). So do run 7's single/52 probes (the coefficient 8, key A).

## Round 6
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-21, with an inline comment at `scene.py:2206`. The N5 inline note was carried over from round 5.
- **Commit reviewed:** `b6a790443764fa437630375fee709efcc36478f4`.
- **Verdict:** FAIL on one new finding. N5 is marked resolved for its examples, and every earlier fix is unchanged.
- **Reproduction:** reproduced on the engine as predicted.

| # | Severity | Finding | Reproduced | Fix | Tests |
|---|---|---|---|---|---|
| N6 | silent wrong answer | SymPy cancels `c*q/(c*q)` to 1 as the expression is read. The other symbol c disappears, so the round 5 proof never ran. With c real, c = 0 makes the expression 0/0 for every q, so there is no limit; the engine gave 1. | yes: 1 | The parser collects the denominators written in `limit`'s first argument (the right side of each `/`, and the base of each negative constant power; unit brackets are skipped). Each is translated on its own, so nothing can cancel it, and passed to `_limit`. Their symbols count toward whether other symbols are present. The continuity proof checks each one: a denominator in q must be nonzero near the point, vanishing at most through (q − a); one without q (e.g. `c` in `q/c`) must be proved nonzero. (`expr.py` `_written_denominators`; `scene.py` `_limit`, `_limit_by_continuity`) | r225 (`c*q/(c*q)`, c real: refused), r226 (controls: `q/q` → 1; `c*q/(c*q)` with c positive → 1; `q/2[m]` → 0, a unit bracket is not a denominator), r227 (`q/c`, c real: refused) |

**Checked:** the FORMAT example (v/(2l²)) and run 7's single/52 probe (8) are unchanged, as are the controls from rounds 4 and 5.

## Round 7
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-21.
- **Commit reviewed:** `aeffa2fc9f8fdb05d92568bf4f61145871a5c850`.
- **Verdict:** FAIL on two new findings. N6 is marked resolved for its case, and every earlier fix is unchanged.
- **Reproduction:** both reproduced on the engine as predicted (1 and 0).

| # | Severity | Finding | Reproduced | Resolution | Tests |
|---|---|---|---|---|---|
| N7 | silent wrong answer | `limit(c*q*(c*q)**(0-1), q, 0)` with c real gave 1. The denominator collector recognised only a literal negative exponent, not `0-1`, so c was cancelled away; at c = 0 the expression is undefined for every q. | yes: 1 | Covered by the decision below: c is written in the text, so the limit is refused. | r228 |
| N8 | silent wrong answer | `limit(q + log(c) - log(c), q, 0)` with c real gave 0. `log(c) - log(c)` cancels as it is read, so c and its domain (c > 0) are lost. | yes: 0 | Covered by the decision below. | r229 |

**Decision (the user's, after round 7): narrow `limit()` rather than keep patching.** Rounds 3 to 7 all found a way for a symbol, or its domain, to be lost in SymPy's automatic simplification before `limit` sees the expression. Each patch (proof by continuity, written denominators) closed one form and left the next.
- **The rule:** apart from its variable, everything in a limit must be a number. No other symbol may appear in the expression or the point, and none may be written in the text. The text is collected by the parser before SymPy simplifies anything (`expr.py` `_Tr._named_symbols`), so a symbol that cancels is still seen.
- **What still works:** numbers and `arbitrary:` values (numbers when the engine evaluates) are allowed. The exact two-sided check, domain edges, stated bounds and the real-point check all apply unchanged.
- **Removed:** `_limit_by_continuity`, `_SMOOTH` and `_written_denominators`.
- **Cost:** a formula can no longer be read off a limit. The FORMAT example `23_05_asc_004` now uses v = 340 m/s and l = 1 m, which gives 170 per metre (by hand: v/(2l(l + dl)) → v/(2l²) = 170).
- **Tests:** r228 (N7) and r229 (N8) are refused; r230 shows that a limit over an arbitrary length works (ratio 1). r213, r219 and r221–r227 now expect the numbers-only refusal, or became numeric controls.
- **Run 7 is unaffected:** its single limit scene, single/52, uses an arbitrary length and still gives 8.

## Round 8
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-21. An inline N5 note was carried over from round 5; the review itself marks N5 resolved.
- **Commit reviewed:** `7e9140c50e888472eb9511ee61e998bff5149631`.
- **Verdict:** FAIL on three findings in the numbers-only rule. N7 and N8 are marked resolved, and Astra accepts the narrowing as the owner's choice. All earlier fixes are unchanged.
- **Reproduction:** all five scenes reproduced as predicted: 0, 0, 0, `F(1)`, and a wrong refusal.

| # | Severity | Finding | Reproduced | Fix | Tests |
|---|---|---|---|---|---|
| K1 | silent wrong answer | The keyword form `limit(e=..., var=..., value=...)`, and a keyword point, bypassed the written-text check. `log(c) - log(c)` cancelled, giving 0. | yes: 0 and 0 | `limit` takes exactly three positional arguments; keywords are refused. (`expr.py`) | r231 (all keywords), r232 (keyword point) |
| K2 | silent wrong answer | A call to an arbitrary function from `functions:` has no free symbols, so it passed as a number. `F(0) - F(0)` cancelled to 0, and `limit(F(1), q, 0)` returned `F(1)`. | yes: 0 and `F(1)` | Any call to an arbitrary function in the expression or the point, as written, is refused. As a second guard, `_limit` refuses an expression or point that still holds an undefined function (`AppliedUndef`). (`expr.py`, `scene.py`) | r233 (cancelled F(0)), r234 (F(1)) |
| K3 | wrong refusal | The written-name scan visited unit brackets, so `2[m]` was read as a symbol `m` when a symbol named m was declared. | yes: refused | The scan skips the unit inside brackets (the unit parser handles it), and skips function names. (`expr.py` `_Tr._named_symbols`) | r235 (symbols m and s declared: `q/2[m]` → 0, `q*3[s]/3[s]` → 0) |

## Round 9
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-21. Inline comment at `expr.py:175`; an N5 note was carried over again.
- **Commit reviewed:** `7b1fdf6ff6bee951a7553bc0ae73b3a3e17ae9fb`.
- **Verdict:** FAIL on one finding. K1–K3 are marked resolved; nothing earlier regressed.
- **Reproduction:** reproduced on the engine as predicted (0). The same cancellation for the variable itself also reproduced: `limit(q + log(q) - log(q), q, 0)` with q real gave 0, although no log exists for q < 0.

| # | Severity | Finding | Reproduced | Fix | Tests |
|---|---|---|---|---|---|
| K4 | silent wrong answer | An arbitrary profile hidden behind a scene observable. With `p: {given: "F(x-t)"}`, each `y(p, x=0, t=0)` is `F(0)`; two cancel before `limit` checks anything, so `limit(q + y(...) - y(...), q, 0)` gave 0. | yes: 0 | `limit` now scans its written expression and point part by part (`expr.py` `_Tr._limit_scan`), translating each call on its own before anything can cancel. A call whose value holds an arbitrary function is refused, and the symbols in every call's value count as other symbols. | r236 (refused), r237 (control: a stated profile gives 0.1) |
| (same class) | silent wrong answer | Cancellation also hid the **variable's own** domain: `log(q) - log(q)` is 0, but with q real neither log exists below 0, so there is no limit from below. | yes: 0 | `_limit_scan` also records the condition each written function, power and division needs. `_limit` checks it on each side approached: a log argument, the base of a fractional power or a `sqrt` argument must be positive near the point (proved by assumptions, by a positive one-sided limit, or for a polynomial by its lowest-order term); an `asin`/`acos` argument must tend strictly inside (−1, 1); a denominator must be nonzero near the point. A denominator that is a polynomial in the variable and not identically 0 vanishes only at isolated points, so `q/q`, `sin(q)/q` and `(f - f0)/dl` are kept. (`scene.py` `_limit`, `_poly_sign_near`) | r238 (refused "from below"), r239 (controls: log(1+q)/q → 1, r·log r → 0, √r → 0, sin q/q → 1, asin q/q → 1, √(q²) → 0), r240 (√q with q real: refused), r241 (asin at the edge: refused) |

## Round 10
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-21, with inline comments at `scene.py:2257`, `expr.py:196` and `scene.py:2262`. N5 and K4 notes were carried over.
- **Commit reviewed:** `be0c90d4e91c0e3f409f063de74e5481ceaf9ffa`.
- **Verdict:** FAIL on three findings in the round 9 domain checker. K4 is marked resolved; nothing earlier regressed.
- **Reproduction:**
  - K5: `sqrt(q - 1)` with q < 1 gave 0. The mirror case, `sqrt(1 - q)`, happened to give the right answer (0), because its argument is the offset itself, positive by assumption. The underlying side mix-up was real.
  - K6: the sqrt-wave scene gave 0.
  - K7: `asin(1 - q**2)` was refused.

| # | Severity | Finding | Fix | Tests |
|---|---|---|---|---|
| K5 | silent wrong answer | For a bounded variable, the polynomial sign check was given the side in the user's variable but evaluated in the bound's offset. For an upper bound (q = 1 − p) the side is reversed, so `sqrt(q - 1)` with q < 1 was accepted. | The sign check and the one-sided limits now share one side mapping, `in_offset(side)`, in `_limit` (`sign_near`, `toward`). Messages show the expression in the declared symbol (`q - 1`), not the offset `-Δ(q)`, which also avoids the Windows console's trouble with `Δ`. | r242 (`sqrt(q - 1)`, q < 1: refused), r243 (controls: `sqrt(1 - q)`, q < 1 → 0; `sqrt(y - 1)`, y > 1 → 0), r244 (`sqrt(1 - y)`, y > 1: refused) |
| K6 | silent wrong answer | A domain condition inside a call's *value* was not recorded. A wave given as `sqrt(x - t)` (or `log(x - t)`) makes `y(p, x=q, t=0)` equal √q; two of them cancelled. | `_limit_scan` reads the conditions in every call's value from its SymPy tree, before anything cancels: a positive base for fractional powers, a nonzero base for negative powers, a positive log argument, and asin/acos arguments inside (−1, 1) (`expr.py` `_value_obligations`). | r245 (sqrt wave: refused), r246 (log wave: refused); r237 (a stated profile, 0.1) still passes |
| K7 | wrong refusal | asin/acos required the argument's *limit* to be strictly inside (−1, 1). An argument that tends to ±1 from inside is fine: asin(1 − q²) → π/2. r241 encoded the wrong refusal. | When the argument tends to 1 (or −1), the limit is accepted if 1 − g (or 1 + g) is shown positive near the point on that side (polynomial lowest-order term). | r241 rewritten (asin(1 − q²) → π/2, acos(1 − q²) → 0), r247 (asin(1 + q²): refused) |

## Round 11
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-21.
- **Commit reviewed:** `3cefc0d30d94519e844ee378ade52bdba5dab899`.
- **Verdict:** FAIL. K5 is resolved; K6 and K7 are resolved for their reported cases. There were three findings.
- **Reproduction:** each scene was run on the m14 engine and on the engine before m14 (`eval/m14_repairs/engine_before`).

| # | Severity | Finding | m14 engine | Before m14 | Resolution | Tests |
|---|---|---|---|---|---|---|
| K9 | wrong refusal (introduced in m14, round 10) | `limit(asin(1), q, 0)` refused, though asin(1) = π/2. | refused | π/2 | An asin/acos argument that is a constant in [−1, 1], ends included, is accepted. | r248 (asin(1) → π/2, acos(−1) → π) |
| K10 | wrong refusal (introduced in m14, round 9) | `limit(q + sqrt(0), q, 0)` refused, though √0 = 0. | refused | 0 | A new condition, "nonneg", for a `sqrt` argument and the base of a positive fractional power: an argument that is identically 0, or proved nonnegative, is accepted. Logs and negative fractional powers keep "positive". (`expr.py` `_power_obligation`; `scene.py` `_limit`) | r249 (√0, 0^0.5 → 0), r250 (0^(−0.5): refused) |
| K8 | silent wrong answer, **pre-existing and engine-wide** | A wave given as `log(x-t) - log(x-t)` is 0 inside a limit, though no log exists for q < 0. | 0 | 0 | **Scoped out of m14 (the owner's decision).** See below. | none (not fixed in m14) |

**Why K8 is out of scope for m14:** the cause is not in `limit()`. SymPy simplifies the wave's profile to 0 when the scene is read (`GivenWave.__init__`), so the domain of the written profile is lost for **every** use of the wave, not only in a limit. A plain observable shows it: `y(p, x=-1[m], t=0[s])` returns 0, though log(−1) does not exist. The engine before m14 behaves the same, so m14 neither introduced nor worsened it. A fix means keeping the conditions of every written scene definition (profiles, and probably fields) through parsing. That is an engine-wide change, beyond these service repairs. It is recorded in `FINDINGS.md` as a known issue and proposed as its own milestone ("domain of scene definitions"). Inside `limit()`, everything written in the observe expression, and every call's value, keeps being checked (rounds 9–10).

## Round 12
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-21.
- **Commit reviewed:** `5db4355960193c50e4c219e93ff7610297949213`.
- **Verdict:** FAIL. K9 and K10 are resolved.
  - **K8 is held as required:** an accepted scene returning a wrong value fails the project rule, even though the issue is pre-existing and its full fix is deferred. Astra accepts a conservative refusal at ingestion as the resolution.
  - **K11 (new, medium):** wrong refusals of non-polynomial limits.
  - **One optional message point.**
- **Owner's decision:** add the conservative K8 refusal and fix K11.

| # | Severity | Finding | Resolution | Tests |
|---|---|---|---|---|
| K8 | silent wrong answer (pre-existing) | A wave profile `log(x-t) - log(x-t)` is simplified to 0 as the scene is read, so `y(p, x=-1, t=0)` and a limit through it give 0. | **Conservative refusal at ingestion, targeted.** `GivenWave` reads each condition written in the profile (each log, root, power, division and asin/acos) before SymPy simplifies it, using the same part-by-part scan as `limit`, with arbitrary functions allowed (`expr.py` `written_obligations`). A condition must either hold for every real x and t (proved from the symbols' declared signs), or **still be present** in the simplified profile, where the engine meets it at the point of use (`scene.py` `_check_profile_defined`, `_same_condition`). A condition that is neither, i.e. one simplified away, is refused when the scene is read. A first, stricter version (every condition provable everywhere) also refused valid scenes: FORMAT example `02_cnt_005` (denominator 3(x + 4t)² + 4) and run 7 single/10, a JEE "which is a wave?" question whose options include profiles with poles. So the rule targets exactly the condition that is lost. With it, single/10 matches the grader's output again. **Added with it:** a result that is not real (e.g. `sqrt(x - t)` at x < t gives I) is now refused (`run.py`); before, it was reported as I. | r251 (the cancelled-log profile: refused), r252 (controls: Lorentzian with b positive → 3/b, √(1 + x²)·cos(x − t) → 1, Gaussian → 1), r253 (a profile with poles is accepted: −2 away from the poles), r256 (at the pole: refused as infinite), r257 (√(−1): refused, not real), r258 (√4 = 2) |
| K11 | wrong refusal (m14 regression) | The sign proofs handled only polynomials, so `sqrt(1 - cos q)` → 0 and `asin(cos q)` → π/2 were refused. | The sign just to one side of the point is read from the lowest-order term of the Taylor series when the expression is entire: built from +, ×, nonnegative integer powers, sin, cos, exp, sinh and cosh, whose series converge everywhere (`scene.py` `_poly_sign_near`, `_entire_in`). 1 − cos q ~ q²/2 > 0. | r254 (√(1 − cos q) → 0, asin(cos q) → π/2, acos(cos q) → 0), r255 (√(cos q − 1): refused) |
| optional | message | A root's refusal said "must be positive"; a root needs "0 or more". | The message names the condition: "0 or more" for roots, "positive" for logs. | r242, r244, r255 |

## Round 13
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-22.
- **Commit reviewed:** `7ec5907e8eaaadbd1e4f724e15e1a5e2ef7f6ef3`.
- **Verdict:** FAIL. K8 is resolved for its reported scene, and K11 is resolved. Three new findings.
- **Reproduction:** all three reproduced as predicted:
  - K12: −log 2 at the invalid point;
  - K13: refused;
  - K14: 0.

| # | Severity | Finding | Fix | Tests |
|---|---|---|---|---|
| K12 | silent wrong answer | `log(t-x) - log(2*(t-x))` keeps both logs, so round 12 accepted it. At x = 1, t = 0 both arguments are negative, and the complex parts cancel to −log 2. Checking only that the final result is real cannot see this. | **The profile's written conditions are now checked wherever the wave is evaluated at a point**, replacing round 12's check at ingestion. `GivenWave` records each condition its written profile needs, read before simplification (`self.domain`). `_point` (used by `y`, `slope`, `vy`, `ay`) attaches them to the value as a `Defined(value, conditions…)` guard (`scene.py`). It becomes the value when every condition is true, and is refused at once when one is false. A guard still undecided after the solve is refused (`resolve_deferred`). In a `given` fact, the conditions become inequalities for the solver (`solver.py`); inside `limit`, they become domain conditions (`expr.py` `_conditions_of`). A "point" that contains the free coordinates (`y(p, x=x, t=0)`, the profile's shape) is a function, not a value, and is not guarded. | r260 (x = 1: refused), r261 (x = −1: −log 2) |
| K13 | wrong refusal | `(x-t)**2/(x-t)**3` was refused at ingestion: the written denominator differs from the simplified 1/(x − t) by a non-constant factor. | Covered by the same change: the ingestion check is gone, and the written condition (x − t)³ ≠ 0 is checked at points. | r262 (x − t = 2: 0.5), r263 (at the pole: refused), r264 (a pole that simplification removes, at x − t = 1: refused) |
| K14 | silent wrong answer | `tan` records no condition, so `tan(x-t) - tan(x-t)` gave 0 at x − t = π/2. | tan and sec now record cos(argument) ≠ 0, and cot and csc record sin(argument) ≠ 0, in the written scan and in computed values. | r265 (refused at π/2), r266 (tan(π/4) = 1) |

**Also:**
- r259: `log(x-t) - log(x-t)` at x − t = 2 is 0, which is correct.
- r267: a guarded wave value inside a fact: √d = 2 gives d = 4.
- r268: a profile's shape is not guarded (run 7 single/10).
- r251, r256 and r257 now expect "not defined at this point".

## Round 14
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-22.
- **Commit reviewed:** `376ed613d29643dbf58919bf7491b21d0687e85e`.
- **Verdict:** FAIL. K12–K14 are resolved for their cases. Three required findings and one optional.
- **Reproduction:** all four reproduced as predicted:
  - K15: d = −1;
  - K16: 0;
  - K17: −log 2 and −1;
  - K18: refused before solving.

**One mechanism replaces the round 13 guard.** Every finding came from a condition carried *inside* a SymPy value, where cancellation could remove it. K17 also showed the problem is not limited to waves or limits.
- **Recorded beside the value:** while an `observe`, a `given` fact, a `limit` argument or a wave profile is being read, every log, root, division, power, tan/sec/cot/csc, asin/acos and wave value at a point records the condition it needs in a list kept **beside** the value (`expr.py` `translate`, `_note`, `holds`). No simplification can touch that list. Each reading has its own list, so nested readings cannot leak conditions.
- **Observe:** after the solve, each condition is checked with the solved values; one that fails or cannot be decided refuses the observable (`run.py` `_check_observe_conditions`).
- **Facts:** "> 0" and "≥ 0" conditions become inequalities of the solve; "≠ 0" and asin/acos conditions are checked on the solution (`solver.py` `_relations`, `run.py` `_check_fact_conditions`).
- **Limit:** its arguments are read into their own list, whose conditions in the limit variable are checked on each side approached.
- **Wave values:** a value at a point checks its profile's written conditions there. It refuses at once if one fails, and records it in the list if it cannot be decided yet (`scene.py` `_check_point`). A profile's shape records its conditions in x and t: a limit in x checks them, while an observe of the shape itself does not need them.
- **Removed:** the round 13 `Defined` guard.

| # | Severity | Finding | Now | Tests |
|---|---|---|---|---|
| K15 | silent wrong answer | The guard cancelled inside a fact: `y(p,x=d) - y(p,x=d) + d == -1` solved to d = −1. | The logs' condition d > 0 is a constraint of the solve: inconsistent. With `+ d == 3`, d = 3. An observe at x = −2 is refused. | r269, r270, r271 |
| K16 | silent wrong answer | The limit of an unguarded shape, `limit(y(p, x=x, t=0), x, 0)`, gave 0. | The shape's x > 0 condition is checked by the limit: refused "from below". The route through `y(p, x=q)` is also refused (r246). | r272 |
| K17 | silent wrong answer (pre-existing, any observe) | `log(-1) - log(-2)` gave −log 2, and `sqrt(-1)*sqrt(-1)` gave −1. | Refused: the written log and root conditions fail. `log(1) - log(2)` and `sqrt(1)*sqrt(1)` are unchanged. | r273, r274, r275 |
| K18 (optional) | wrong refusal | A wave pole condition in a fact was refused before solving. | Checked on the solution: d = 2 gives 0.5. If the facts put the point at the pole, they are inconsistent. | r276, r277 |

**Existing tests affected by the round 14 change:**
- **FORMAT example `14_03_bmc_005`** computed |vy|/|c| with c declared `real`, so c = 0, a wave that does not move, was allowed, and the ratio is undefined there. The book's 4/3 silently assumes c ≠ 0, and the engine now refuses rather than assuming it. The example now uses a positive speed v (toward +x), stating the assumption in `assume`: vy = −4v/3, |vy|/v = 4/3.
- **r147** (√(−1) > 0) is still refused, now by the written-root condition, with the new message.

## Round 15
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-22. It was found by the new 4-minute check of the PR.
- **Commit reviewed:** `f664c8f87abf5ec061288d887a810619c5bfb191`.
- **Verdict:** FAIL. K15–K18 are resolved for their cases. Two high and two medium findings.
- **Reproduction:** all four reproduced as predicted:
  - NEW-1: q = −1, and a limit gave 0;
  - NEW-2: 339.3 m/s;
  - NEW-3: "2 situations";
  - NEW-4: refused.

| # | Severity | Finding | Fix | Tests |
|---|---|---|---|---|
| NEW-1 | silent wrong answer (pre-existing) | An observable's result can hold a condition: `sound_level(q)` returns a log needing q > 0. Two of them cancelled in a fact (q = −1) and in a limit (0). | Every call's **result** also records the conditions in its SymPy tree, as the call is read and before it can cancel (`expr.py` `_value_conditions`): powers, logs, asin/acos, tan/sec/cot/csc. | r278 (fact: inconsistent), r279 (control: q = 2), r280 (limit: refused) |
| NEW-2 | silent wrong answer (pre-existing) | Scene fields were read without the condition list: `v: "(340 + log(-1) - log(-2)) m/s"` gave 339.3 m/s. | Fields read with units (`Scene.quantity`) record their conditions too. One that fails refuses the field when the scene is read; one involving an unknown is checked after the solve (`scene.py` `_check_field_conditions`, `run.py`). | r281 (refused), r282 (control: 340 m/s) |
| NEW-3 | wrong refusal (from round 14) | "≠ 0" and asin/acos conditions were checked only after the solver had already reported ambiguity: `d(d-1) + 1/d - 1/d = 0` gave "2 situations". | Each candidate is filtered by those conditions **before** the candidates are counted (`solver.py`); if none survives, the facts are inconsistent. | r283 (d = 1), r284 (asin: d = 0), r285 (all excluded: inconsistent) |
| NEW-4 | wrong refusal (from round 14) | `(-2)**n` with n an integer unknown required a positive base. | A symbolic integer exponent is treated as an integer: no condition if it is nonnegative, a nonzero base otherwise (`_power_obligation`). | r286 ((−2)² = 4), r287 ((−2)⁻¹ = −1/2) |

## Round 16
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-22. It was found by the 4-minute check on its third try.
- **Commit reviewed:** `5387bbdd96bb46f05a5213bb8685d3c675bd9fc3`.
- **Verdict:** FAIL. NEW-1 to NEW-4 are resolved for their cases. Three high and one medium finding.
- **Reproduction:** all four reproduced as predicted:
  - R1: e⁻¹;
  - R2: e⁻¹;
  - R3: 1, accepted;
  - R4: refused.

| # | Severity | Finding | Fix | Tests |
|---|---|---|---|---|
| R1 | silent wrong answer | A **sum wave** did not carry its parts' conditions: a part that cancels to 0 (`log(x-t) - log(x-t)`) let the sum be reported at x − t = −1. | A sum's conditions are all its parts' conditions, nested sums included (`scene.py` `SumWave`). | r288 (refused), r289 (x − t = 1: e⁻¹) |
| R2 | silent wrong answer | A **shaped pulse** read its shape without the condition list. | The shape's written conditions are recorded (in x) and moved along with the shape (x − s·v·t). Reflected and transmitted copies take the parent's conditions under the same map as their shapes (2x_J − x; x_J + (v₁/v₂)(x − x_J)) (`scene.py` `ShapedPulse`, `derived`). | r290 (refused), r291 (x − vt = 1: e⁻¹), r292 (reflected copy at an invalid point: refused) |
| R3 | silent acceptance | **Arbitrary values** and their range bounds were read without the condition list. | Read with it and checked like fields: a failing condition refuses the value. | r293 (refused), r294 (`(2 + log(1)) m/s`: c/c = 1) |
| R4 | wrong refusal (from round 15) | `0**n` with n an integer unknown required a nonzero base before n was known. | An integer exponent of unknown sign records a combined condition, "base ≠ 0 or exponent ≥ 0", decided after the solve (`expr.py` kind "intpow", `holds`). | r295 (n = 2: 0), r296 (n = −1: refused) |

## Round 17
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-22. It was found by the 4-minute check.
- **Commit reviewed:** `b841c3f5561339f5fc9f85141a14c4c3d0f49643`.
- **Verdict:** FAIL. R1 to R4 are resolved for their cases. Three high and one medium finding.
- **Reproduction:** all four reproduced as predicted:
  - H1: e⁻¹;
  - H2: 1;
  - H3: x = 0;
  - M1: refused ("needs 0 to be positive"), and the same for `(-2)**q`.

| # | Severity | Finding | Fix | Tests |
|---|---|---|---|---|
| H1 | silent wrong answer | `at(field(w), x=…, t=…)` put values into the simplified field without the wave's written conditions. | `field()` records the wave's conditions (in x and t) beside its value. `at()` reads its expression into a list of its own, puts its values into those conditions, refuses one that fails and passes the rest on (`scene.py` `_field`, `_at`; `expr.py`). The same principle for the **range functions**: `max_over`, `min_over`, `mean_over`, `max_in`, `min_in` and `frequency_of` refuse an expression whose conditions in their variable fail anywhere in the range (`expr.py` `_over_range`). | r297 (refused), r298 (nested sum: refused), r299 (x − t = 1: 2e⁻¹), r300 (`max_in` over [−2, 2] m: refused), r301 (over [1, 2] m: 0) |
| H2 | silent wrong answer | `phase(w, x=…, t=…)` did not check the written profile at the point. | It checks it, like `y` (`_check_point`). | r302 (refused), r303 (x − t = 1: −1) |
| H3 | silent wrong answer | `peak_position` searched the whole string, not where the shape is defined, and took a supremum it never reaches as the maximum. | Extremum searches (`peak`, `peak_position`, `amplitude` of a shaped pulse) work only where the written profile is defined at that instant (`_defined_set`, from its conditions). An open end of that region, like an end at infinity, is approached, not reached. When |y| comes closer to a larger value toward such an end than anywhere it is reached, there is no largest value, and the observable is refused (`_largest_reached`). On the same principle: an **energy** needs the profile defined over the whole stretch it integrates, a **width** needs the shape defined everywhere, and an **energy density** checks the point. | r304 (refused: no largest value), r305 (Gaussian centred at x = 1 m: at x = 1 m at t = 0, at x = 3 m at t = 2 s, height 1), r306 (energy: refused), r307 (width: refused), r308 (density at x = −1 m: refused) |
| M1 | wrong refusal | `0**q` with q declared real and solved to 2 required a positive base before q was known; `(-2)**q` likewise. | An exponent that is still a symbol, not known to be an integer, records a combined condition "the power base**exponent is real and finite" (kind `pow`), decided after the solve: a positive base; an integer exponent as for `intpow`; a non-integer exponent needs a base of 0 or more, and a zero base a positive exponent (`expr.py` `_power_obligation`, `holds`). | r309 (q = 2: 0 and 4), r310 (q = −1: refused), r311 ((−2)^(1/2): refused) |

## Round 18
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-22. It was found by the 4-minute check on its fourth try.
- **Commit reviewed:** `229bcf11a70deadcebf25cf534b2b9939aea0077`.
- **Verdict:** FAIL. H1 to H3 and M1 are resolved for their cases. Two high and three medium findings.
- **Reproduction:** all five reproduced as predicted:
  - S1: x = 0, height 1, amplitude 1, while y(p, 0, 0) = 0;
  - S2: height 1, x = 0;
  - S3: refused;
  - S4: refused;
  - S5: refused.

| # | Severity | Finding | Fix | Tests |
|---|---|---|---|---|
| S1 | silent wrong answer | Samples 10⁻⁹ beside a breakpoint were counted as values reached **at** the breakpoint, so a jump's one-sided limit passed as a maximum. | The candidate search is rewritten (`scene.py` `_extreme_rows`). Each candidate says whether it is **reached** (the value at a critical point, at a breakpoint itself, at a closed end, or a constant part over a stretch) or only **approached** (each one-sided limit at a breakpoint, an open end, infinity). One-sided values come from the piece that applies on that side, because SymPy 1.12's `limit` of a whole Piecewise at its own breakpoint can return the other side's value. `max_in` and `min_in` use the same rows. | r312 (refused), r313 (`exp(-x)*step(x)`: x = 0, height 1), r314 (`max_in` across a jump: refused), r315 (reached at the jump: 1) |
| S2 | silent wrong answer | A 10⁻⁹ relative tolerance let a supremum never reached (1 at infinity) pass for the value 1 − 10⁻¹⁰ reached at x = 0. | Values are ordered exactly (`_cmp`: SymPy's sign, or 60 digits beyond any doubt, or a proof of equality); a value approached that is beyond every value reached refuses the call, and one that cannot be ordered refuses it too (`_best_reached`). | r316 (refused), r317 (1 + 10⁻¹⁰ e^(−x²): x = 0, 10000000001/10000000000) |
| S3 | wrong refusal (from round 17) | A constant field had only its limits at infinity as candidates, so its peak was refused. | A part constant over a stretch is a value reached there (one point of the stretch is kept as a witness); `peak_position` of such a maximum is ambiguous. | r318 (peak 1), r319 (peak_position: ambiguous) |
| S4 | wrong refusal | An exponent declared positive, but still a symbol, made a negative base need to be 0 or more before the solve. | Any exponent that is still a symbol and not known to be an integer records the `pow` condition, decided after the solve (`expr.py` `_power_obligation`); `pow` holds outright for a base of 0 or more with a positive exponent. | r320 (q = 2: 4), r321 (q = 1/2: refused) |
| S5 | wrong refusal | `lo=` and `hi=` given by keyword were ignored by the range check, which then used the whole real line. | They are read like the positional ones (`expr.py` `_over_range`). The variable and the expression must be positional, and only `lo` and `hi` may be keywords, so no part bypasses the check. | r322 (log(x) on [1, 2]: log 2), r323 (on [−1, 2]: refused) |

## Round 19
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-22. It was found by the 4-minute check on its third try.
- **Commit reviewed:** `7a68e35ffd3f2f255ba656c58ac487c33d4b5faf`.
- **Verdict:** FAIL. S1 to S5 are resolved for their cases. Two high findings.
- **Reproduction:** both reproduced as predicted:
  - T1: 9999999999999/10000000000000;
  - T2: 0.

| # | Severity | Finding | Fix | Tests |
|---|---|---|---|---|
| T1 | silent wrong answer | Whether a side of a breakpoint lies inside the range was tested with a fixed 10⁻¹² probe, so on a range shorter than that the jump's one-sided limit was left out. | A side counts when the range has points arbitrarily close to the breakpoint there: inf < q for the left, q < sup for the right (`scene.py` `_extreme_rows`). | r324 (your scene: refused), r325 (on [−1, 0], the jump at the closed end: refused) |
| T2 | silent wrong answer | Breakpoints that SymPy returns as infinitely many (sin x = 0) were dropped, and a condition SymPy cannot turn into a set (sin x < 0) silently became the whole range. | Infinitely many breakpoints are re-solved within the range; if they are still not a finite list, the call is refused. A condition without a set is decided stretch by stretch between its breakpoints (one point each, after checking its sides are continuous on the range), plus each breakpoint itself; if that cannot be certified, the call is refused (`_cond_region`). | r326 (your scene: 1), r327 (min: 0), r328 (`step(-sin(x)**2)` on [1, 7]: 1, reached only at π and 2π), r329 (over the whole line: refused) |

## Round 20
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-22. It was found by the 4-minute check on its third try.
- **Commit reviewed:** `8656b7ea3dd0398f80e1611f2d2c5784432e463d`.
- **Verdict:** FAIL. T1 and T2 are resolved for their cases. One high finding.
- **Reproduction:** reproduced, with a different symptom on SymPy 1.12. The minimum was refused ("no smallest value", because the one-sided limits at π and 2π are 0), not the predicted 1. The cause is the same: the branch where sin(x)/x < 0 came back as an unresolved ConditionSet and got no point to evaluate.

| # | Severity | Finding | Fix | Tests |
|---|---|---|---|---|
| U1 | silent wrong answer (a wrong refusal here) | `_cond_region` accepted whatever `as_set()` returned, including an unresolved `ConditionSet`. A branch with no witness was then skipped silently. | Only a set built from intervals and finite sets (a solved one) is accepted; anything else goes to the stretch-by-stretch method, or is refused. A branch region that is not such a set is refused, and so is a nonempty branch with no point found to evaluate: it is never skipped (`scene.py` `_plain_set`, `_cond_region`, `_extreme_rows`). | r330 (your scene: 0), r331 (max: 1) |

## Round 21
- **Reviewer:** ChatGPT (Astra), posted on PR #14 on 2026-11-22. It was found by the 4-minute check on its fourth try.
- **Commit reviewed:** `36bf1a63c82bcb411dc3907fb811662b88915ad6`.
- **Verdict:** FAIL. U1 is resolved for its case. One high finding.
- **Reproduction:** confirmed, with a different symptom on SymPy 1.12. Here the scene did not finish: SymPy 1.12's `solveset`, `continuous_domain` and `as_set` each ran for minutes on `sin(10**17*(x - 1))`, and Windows has no per-scene time limit. The defect Astra found is in the code either way: breakpoints were sorted by `float()` keys, and these four all round to 1.0.

| # | Severity | Finding | Fix | Tests |
|---|---|---|---|---|
| V1 | silent wrong answer (on SymPy 1.14, hash-order dependent) | Breakpoints were sorted by `float(sp.N(q))`; roots closer than a double's spacing kept a set's arbitrary order, so a stretch was skipped and a constant branch's witness fell in the other branch. | Breakpoints are sorted by exact comparison, refused when an order cannot be proved (`scene.py` `_exact_sorted`, using `_cmp`). The zeros of c·sin(ax + b) and c·cos(ax + b) are listed exactly within a finite range (ax + b = kπ, or π/2 + kπ), without SymPy's `solveset`; over an unbounded range, or for more than 10 000 of them, the call is refused (`_trig_linear_roots`). A condition whose sides are built only from functions continuous everywhere goes straight to the certified stretch method (`_continuous_everywhere`). A constant branch's witness is checked to lie where that branch is the one that applies, or the call is refused. | r332 (your scene: −1, also with `PYTHONHASHSEED` 0, 2, 4, 5 and 7), r333 (a step with the same close breakpoints: max 1, min 0), r334 (`step(cos(x - t))` over the whole line: refused) |
