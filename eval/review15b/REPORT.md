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
