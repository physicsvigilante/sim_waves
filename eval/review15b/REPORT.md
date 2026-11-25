# Review report: milestone 15b, wrong-answer fences

Reviewer: ChatGPT (Astra), independent. Builder: Claude Code.

## Round 1: commit `a1387e3d0b783ef236a34a9660ed8bc81ea154a8`, verdict FAIL

Astra's review: a source trace with independent SymPy 1.14 and 65-digit mpmath checks; CI run 45554037700 green; no reserved material. Each finding was first reproduced on the engine at `a1387e3`.

| # | Astra's finding | Reproduced at a1387e3? | What was done | Regressions |
|---|---|---|---|---|
| **R1** REQUIRED | F3 misses a corner in **t** at a fixed x: `0.01*(abs(x-10*t)+abs(x+10*t))`, `vy(w, x=0, t=0)` gave **0.2** (y(0, t) = 0.2\|t\|) | **Yes**: vy = 1/5, ay = 0 | **Fixed by a new rule.** The derivative is checked along the variable it is taken in: the wave is restricted to that variable through the point (`_regular_along`, `_regular_1d`), and at a breakpoint every order 0…n must have equal one-sided values. The earlier comparison along x stays for `vy`/`ay` (the PLAN keeps it) | r374, r375 (refused), r376 (symbolic, refused), r377 (valid: 0.2, 0, 0) |
| **R2** REQUIRED | F3 misses a jump in the displacement: `0.01*step(x)`, `vy(p, x=1, t=0.1)` gave **0** | **Yes**: vy, ay and slope all 0 | **Fixed by the same rule:** order 0 (the displacement) is included, and a piece that cannot be established refuses instead of being skipped | r378, r379, r380 (refused), r381 (symbolic, refused), r382 (valid: 0, 0, 0) |
| **R3** REQUIRED | Energy densities bypass F3: `at(potential_density(p, x=x, t=0.1), x=1.5)` gave **0.005 J/m** at the tip | **Yes**: 1/200 | **Stop rule applied:** the densities were outside F3's listed producers. **The owner chose to extend F3** (2026-11-25; recorded in the PLAN). `_density` uses the same check at a numeric point (kinetic: velocity; potential: slope; total: both) and the same corner notes at a symbolic point | r383, r384, r385 (refused), r386 (valid flanks: 0.005, 0.005, 0.01) |
| **R4** OPTIONAL | The symbolic guard refuses an inactive branch's zero: `0.01*max(0,1-abs(x),3-abs(x-1))`, `at(diff(y(p, x=0, t=t), t), t=0)` should be **−0.1 m/s** | **Yes**, and the direct `vy(p, x=0, t=0)` crashed with a RecursionError (whole-field rewrite) | **Refined.** At a symbolic point, each switching argument with one free symbol and finitely many real zeros is decided by the numeric rule at each zero, and only the irregular zeros are recorded; others are recorded whole, as before (conservative). Numeric points use only the one-variable restriction, so the recursion is gone | r387 (−0.1 by both spellings), r388 (the active corner, refused) |
| **R5** REQUIRED | F4 wrongly refuses a stated-length path: `{from: S, length: 340 m}`, `phase(r, t=1.1)` should be **100π** | **Yes**: "a stated-length path has no positions" | **Fixed.** For a stated-length path, the causal check uses the delay length/v (such a path is never moving; a moving source already refuses L) | r389 (100π), r390 (0.5 s: no sound yet), r391 (symbolic t: refused) |
| **R6** REQUIRED or deferral | Wind phase: `phase(r, t=1.1)` in a 20 m/s wind gives **700π/17** instead of 100π | **No.** A ray in a medium with wind is `moving`, and `Ray.L` refuses ("something on it moves (or the air moves) … phases … are not defined in v0") before `total_phase` forms a value, for switched-on and always-on sources alike | **No code change.** The existing refusal is kept by two new regressions | r392 (switched on), r393 (always on): both refused |

**Optional controls from the review, all added and passing:**
- r394: listener circling in wind, arrival **0.2361265964843030086528995191749 s** (the engine agrees to 30 digits);
- r395: circling source, emission **0.7027659548733808953913096897499 s** (agrees to 30 digits);
- r396–r398: F2 with wind solved to 0 (18/17 s), solved to 20 m/s (refused), and a 3-D wind (refused);
- r399: F5 with a derived pulse. A pulse with an unspecified F cannot be reflected, because its start cannot be checked, so no derived pulse carries F to `width()`.

**Not changed: the F6 output message.** `300[K] in degC^1` says "unknown unit 'degC^1' after 'in'" rather than the Celsius message. The refusal is sound. The message is built in `run.py`, which this milestone leaves untouched.

**The 26 new scenes (r374–r399) on the reviewed commit a1387e3:** 13 fail and 13 pass.
- Six are accepted wrong values: r374, r375, r378, r379, r380 and r383.
- r387 hits the RecursionError.
- r389–r391 hit the R5 refusal.
- r384, r385 and r386 fail on their refusal messages, or because a symbolic-t flank was refused.

**Coverage cost, disclosed:**
- `vy` and `ay` at a node where two opposite pulses meet (r99) stay refused, though the node does not move. This is the PLAN's kept x-side comparison.
- A switching argument whose zeros cannot be listed (more than one free symbol, or no finite solution) is still recorded whole.

## Round 2: commit `963f25ea8288646dc4ab0bf6396fa538a73e8002`, verdict FAIL

Astra's review: [6052771314](https://github.com/physicsvigilante/sim_waves/pull/25#pullrequestreview-6052771314). It was a source trace plus a reconstruction of the helpers in SymPy 1.14 and 60-digit mpmath checks.
- **R1–R5:** the original witnesses are resolved.
- **R6:** withdrawn. Geometric rays in wind are already refused.
- **R7–R10:** new, all REQUIRED.
- **The stop rule:** Astra said CLAUDE.md point 5 applies to R7–R9. They share round 1's cause: local piecewise regularity, symbolic admissibility and the returned value are not one contract.

**The owner's scope decisions (2026-11-25, recorded in the PLAN):**
- **F3 is reduced to a switching-point fence**, not repaired precisely. The precise rule is M4's.
- **For F4, the `Ray` constructor fix is approved.**

| # | Astra's finding | Reproduced at 963f25e? | What was done | Regressions |
|---|---|---|---|---|
| **R7** | An isolated spike, `0.01*step(x)*step(-x)`: slope, vy and potential density returned 0; the open-side values match, but the point value differs | yes | **The fence:** at a numeric point, every switching argument (of abs, step, sign; the pairwise differences in max and min; piecewise conditions) must be **proved** nonzero, exactly, or the point is refused, whether it is a corner or cannot be decided. Away from those points, the derivative comes from the piece containing the point, along the one variable. At a symbolic point, and through `diff`, every switching argument is recorded as nonzero for `at()` to check. The precise one-sided machinery (`_regular_1d`, `_regular_along`, `_note_corners`, `_point_regular`) is removed | r402–r405 |
| **R8** | A switching point where the field is 0 (`0.01*x*step(x)*step(-x)`): the symbolic, `diff` and density spellings returned 0.01 or 0.00005 J/m. And `abs(x)*(2*step(x)-1)` through `diff` gave 0 | yes | **The same fence.** All spellings refuse at the switching point (a coverage cost: there the field is identically 0). Numeric densities now use the derivative of the piece containing the point, not the whole-field branch | r406–r410; valid neighbours r411 (0.01, 0.01, 0) |
| **R9** | Breakpoints closer than the 1e-12 tolerance: the wrong one was checked, and slope at 1e-13 m returned 2e-15 where the shape jumps; `1e-31*step(x)` was accepted under the 1e-30 tolerance; `abs(x)` at 1e-13 m was refused | yes | **The same fence.** There is no tolerance: each switching argument is decided exactly at the point (decimals are exact rationals) | r412–r414 (refused); r415 (4e-15 beside both points), r416 (`abs(x)` at 1e-13 m: 0.01) |
| **R10** | A stated-length ray in wind skipped the wind check: `phase` returned 700π/17 | yes | **The constructor fix:** a stated-length path in nonzero (or unproved) wind is `moving`, as a geometric path already was. So `L`, and every phase built from it, is refused | r417, r418 (refused); r419 (zero wind: 100π) |

**Optional hardening (the `MemoryError` catch around `solveset`):** moot, because `_note_corners` is removed.

**Coverage cost of the fence (the owner's decision; in FORMAT.md):** these smooth switching points are now refused:
- r358: the C¹ pulse edge, where `vy` = 0 was expected (it was a PLAN valid neighbour);
- r387: an inactive `max` branch (−0.1 m/s), with r400 just beside it;
- r406–r409: the identically-zero field;
- r99: the meeting node;
- r98: `max_in` of a kinetic density over a range containing the transmitted pulse's smooth edges, which was 9π²/3200. r401 keeps that value with a range inside the pulse.

The expectations of r358 and r98 were changed to refusals. Both comments say why.

## Round 3: commit `319eaac66dbce930a6226c3c59d579374ed44df3`, verdict FAIL

Astra's review: a source trace and component reproductions in SymPy 1.14.
- **R1–R10:** resolved or accepted as coverage cost.
- **R11–R14:** new, REQUIRED.
- **The stop rule:** Astra said it still applies to F3, and asked for a supported-class decision on radicals and on the order of solved substitution, not a precise repair.
- **Also asked:** reconcile the older PLAN and BRIEF wording with the scope notes.

**The owner's decisions (2026-11-25, recorded in the PLAN):**
- **Branch points join the fence.**
- **Solved values go in before switches are classified.**

| # | Astra's finding | Reproduced at 319eaac? | What was done | Regressions |
|---|---|---|---|---|
| **R11** | A radical cusp: `0.01*sqrt(x^2+(10t)^2)`, `at(slope(w, x=0, t=t), t=0)` gave **0** (no `abs`/`max`/`step` atom, so no fence); with `sqrt(x^2+a)` and a solved to 0, the direct slope gave **0** | yes: both 0, and `at(vy(x=x, t=0), x=0)` also 0 | **Branch points are switching points:** the base of any non-integer power, and 1 ∓ the argument of asin/acos. The fence now triggers on any switching or branch point, by every spelling | r420–r422 (refused), r424 (solved a = 0, refused), r431 (acos edge, refused); valid r423 (0 at t = 1 s, 0.01 at x = 1 m) |
| **R12** | Numeric densities ran the whole-field rewrite before the fence: a RecursionError at r400's valid point | yes | At a numeric point with only numeric switches, densities take vy and the slope from the one-variable restriction and **never call the whole-field rewrite** | r425 (1/20000, 1/20000, 1/10000 J/m) |
| **R13** | The fence ignored solved values: `0.01*abs(x-a)`, a = 1, slope at 2 m refused ("cannot tell whether a − 2 = 0") | yes, at 0, 1 and 2 m | **The solution is substituted into the field first** (`_point`, `_density`). A switch that still depends on an unsolved unknown goes to the symbolic route, where it is recorded as a condition | r426 (0.01, −0.01, 0.01 by the symbolic spelling); r427, r428 (a = 2: refused by both spellings) |
| **R14** | `diff` recorded only switches in its own variable: `at(diff(field(w), t), x=0, t=1)` of `0.01 t \|x\|` gave 0, but `vy` there is refused | yes | `diff` records switches in x and t as well as its variable (**parity** with the point fence) | r429 (refused), r430 (x = 1 m: 0.01) |

**Also done:** the PLAN's F3 section is marked superseded, and its cost hypothesis (c) and coverage cost now state the fence. The BRIEF's coverage line is updated.

**The 12 new scenes on 319eaac: 8 fail.**
- Four accepted wrong values: r420, r421, r424, r429.
- The recursion error: r425.
- A wrongly refused valid neighbour: r426.
- Two message changes: r422, r428.

## Round 4: commit `b8021de58501bf3a5e7f0a348bdc9f1ad08230be`, verdict FAIL

Astra's review was published as a PR comment, [7155552505](https://github.com/physicsvigilante/sim_waves/pull/25#issuecomment-7155552505). It was a source trace plus SymPy 1.14 component reproductions.
- **R1–R14:** resolved, or accepted costs.
- **R15–R19:** new and REQUIRED.
- **The stop rule:** Astra said it applies again. R15, R16 and R18 share one structural cause: the canonical expression, its written domain and switch provenance, and the admissibility of the returned derivative do not travel together. That reaches `expr.py`'s condition semantics, the capture of the written profile, and restriction before `diff`.

| # | Astra's finding | Disposition |
|---|---|---|
| **R15** | `at(slope(w, x=x, t=0), x=0)` for `0.01*step(x+sin(π/7)^2+cos(π/7)^2-1)`: the exact zero `x + c` is accepted as nonzero, because `holds` falls back to a floating-point residual (~1e-166). The result is a slope of 0 at a jump | **Moved to M4 with F3.** The cause is `expr.holds`' proof standard, outside F3's producers |
| **R16** | `0.01*sqrt(-x^2)^2` (and `cos(acos(1+x^2))`) simplifies to a smooth polynomial before the fence sees the root, so the slope at 0 is 0 where no neighbourhood exists | **Moved to M4 with F3.** It needs switch and branch provenance from the written profile |
| **R17** | Solved-first is not used by `diff` (through `field(w)`) or by the density fallback: `0.01*(x-10t)^a` with a = 1 is refused or undefined, where the slope is 0.01 and the potential density 1/20000 J/m | **Moot after the revert.** `diff` and the densities are back to `main` and refuse these points; no wrong value. Kept for M4's solved-first contract |
| **R18** | Parity: `diff(y(w, x=0, t=t), t)` of `0.01 t \|x\|` gives 0 (true), while the fence refuses `vy` there | **Moved to M4 with F3:** whether the contract covers restricted expressions |
| **R19** | Linux CI red: r02_symbolic_period hit the 2048 MB memory limit; the other suites were skipped | r02 uses only `y` and the solver, not code changed in round 3. It passes locally at 256 MB on b8021de and on a1387e3, and it passed in every earlier CI run. **The failed job was re-run;** its result is in the PR comment for the next commit |

**The owner's decision (2026-11-25), applying the PLAN's stop rule ("that item moves to its milestone"): F3 is moved to M4.**
- **Production code:** `scene.py` (`_point`, `_diff`, `_switching_args` and the fence helpers, `_at`'s message, the import) and `energy.py` (`_density`) are reverted to `main` (`7244bb6`). F2's `_travel_time` guard and F5's `_width` guard are kept.
- **Production diff against `main`:** `doppler.py` (F1), `scene.py` (F2), `rays.py` (F4, including R5 and R10), `energy.py` (F5), `units.py` (F6). 78 lines added, 5 removed.
- **Tests:**
  - The 41 F3 scenes that fail on the reverted engine moved to `eval/m15b_fences/f3_witnesses_for_M4/`, with a README listing their classes and the round-4 witnesses still to add.
  - r98 is restored to `main`'s version.
  - r358 is restored to its stage-1 version (`vy` = 0 at the C¹ edge; `main` gives it).
  - The valid controls that pass stay in the regression suite: r352, r356, r357, r358, r377, r382, r401, r411, r415, r416, r423, r430.
- **Documentation:**
  - **FORMAT.md:** the derivative section is back to `main`'s text, with a note that D3-1 is open for M4. The F1, F2, F4, F5 and F6 notes stay.
  - **PLAN:** the round-4 scope decision is recorded, F3's section is marked as moved, and cost hypothesis (c) is withdrawn. The coverage cost gains R10's stated-length rays in wind.
  - **BRIEF:** the F3 row, witnesses and limitations are marked as history.
  - **PR description:** updated.
- **D3-1 stays open** in the known-issues ledger, with every witness from rounds 1–4. Policy point 11 is respected: no wrong value is accepted as fixed. The engine's F3 behaviour is exactly `main`'s.
