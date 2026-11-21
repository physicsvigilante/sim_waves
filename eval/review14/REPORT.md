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
