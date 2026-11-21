# Review 14 brief: milestone 14, service repairs (stage 1: the build)

**Reviewer:** ChatGPT (Astra), reviewing the pull request on GitHub and posting its
findings there. Claude Code reads them from the PR and records them, with the action
taken on each, in `eval/review14/REPORT.md`.

sim_waves is an engine for JEE wave problems (Python and SymPy, `engine/simwaves/`). Its
rule: **one correct answer or a clear error, never a silent wrong answer, and no
invented facts.**

- **Compute every expected value by hand.** Do not take the engine's output as the
  reference.
- **The reserved problems** (`eval/m14_repairs/reserved/`) test this milestone blind.
  They are not in the branch; do not ask for them.
- **Background:** `eval/m14_repairs/PLAN.md` (the plan and its cost hypothesis) and the
  m14 entry at the end of `format/FINDINGS.md`. The run 7 evidence is in
  `eval/run7/SCORECARD.md` and `eval/run7/GRADES.md`.

## What changed
| Change | Where |
|---|---|
| `nearest()` is deferred (`Nearest`, a sympy Function) until all its arguments are numbers, so it works on solved unknowns; still symbolic after the solve: refused | `scene.py`: `Nearest`, `_nearest`, `_pick_nearest`, `resolve_deferred` |
| `nearest(x in u, ...)`: x converted to u with the same checks as `observe: x in u`; bare options read in u; options with units converted | `expr.py`: `_Tr._nearest_in`, `_is_in`, the `_Dim` call branch; `scene.py`: `Scene.unit_for_nearest` |
| A value with a unit against bare-number options: refused with a hint to write `in <unit>` | `scene.py`: `call_dim` |
| A written zero takes its bracket's unit (`"0[m]"`) | `expr.py`: `_pure_number`, `_Dim` subscript |
| `x in cm` is no longer classed as a comparison (it got the wide x1000 comparison check, which pushed a sound speed to 340000 m/s); real comparisons skip runs that raise `PhysicalRangeError`, and need at least 5 left | `run.py`: `_is_comparison`, `_check_comparisons`; `errors.py`; `doppler.py`: `check_media`; `scene.py`: `_not_light` |
| `limit()` on a symbol with a stated bound | `scene.py`: `_limit` |
| Unknown k (or omega) and phase from two facts off the origin, branch by branch | `solver.py`: `_single_trig`, `_solve_phase_pair`, `_Periods`, the no-solution check in `_core_solve`, substitution of the chosen branch in `_branches` |
| Units km/h, kmph, h (not as a lone trailing word), um, μm, nm; `in μm` | `units.py`; `run.py`: `_split_unit` |
| Test harness: spawn where fork is missing (Windows) | `harness.py` |
| Docs | `format/FORMAT.md`, `format/FINDINGS.md` |

Regression tests: `engine/tests/regression/r176`–`r195`.

## What to hunt for, silent wrong answers first
1. **`nearest()`:** can it pick an option from a value that is not fixed: a family, a
   branch choice, or an arbitrary value whose pick changes at a scaling the 5 sampled
   runs miss? Is the deferred `Nearest` ever evaluated with stale or partial
   substitutions (in `given` facts, `explore`, `view`, export, or comparisons)? Can
   `Nearest.eval` raising a `SceneError` during a sympy rebuild escape as an internal
   error, or be swallowed?
2. **`nearest(x in u, ...)`:** a wrong conversion, an offset unit (degC), an option of
   unknown dimension (a symbol) read as a number in u, an angle unit.
3. **Phase-pair solver:** a lost or a spurious branch. Check against hand enumeration:
   - the two inverse-sine (or ±acos) choices per fact;
   - the sign of the phase in each fact (dir +x against −x);
   - the period 2*pi/|x2 − x1|;
   - cos facts, facts at a nonzero time, mixed sin and cos.

   Is the phase right for every k branch? The `_branches` change substitutes the chosen
   k into values that depend on it: can that change any existing behaviour wrongly? Can
   `_Periods(probe=4)` hide a branch in a bounded case?
4. **No-solution check in `_core_solve`:** `|c/A| > 1` returns no solution. Is there a
   case where the angle can be complex, or where A and c are not what `_single_trig`
   assumes (for example the same trig atom twice with different arguments)?
5. **Comparison skipping:** can a skipped run hide a case where the comparison is false?
   Is `PhysicalRangeError` raised anywhere it should not be skipped?
6. **`limit()` on a bounded symbol:** the direction of approach at the bound's edge; a
   symbolic limit point; integer-kind bounded symbols.
7. **Units:** an existing scene where a trailing `nm`, `um` or `kmph` was a variable and
   is now read as a unit; the `h` exception.
8. Then ordinary bugs, wrong messages and missing tests.

## Output wanted
For each finding: the file and line, a scene (YAML) that reproduces it, the expected
result worked by hand, the engine's result, and the severity (silent wrong answer,
wrong refusal, message, test gap).
