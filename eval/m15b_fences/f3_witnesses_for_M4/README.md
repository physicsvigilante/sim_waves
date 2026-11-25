# F3 (D3-1) witnesses, kept for M4

**F3 was moved out of milestone 15b to M4 by the owner on 2026-11-25.**

**Why.** In four rounds of Astra's review on PR #25, each fence for derivatives at corners exposed new holes from one structural cause. The stop rule (CLAUDE.md point 5, and the PLAN's stop rule) applied three times. The rounds tried, in turn:
1. a precise one-sided check;
2. a switching-point fence;
3. the same fence with branch points and solved values.

The last holes were outside F3's producers:
- exact-zero conditions that `at()` accepts on floating-point evidence (`expr.holds`);
- roots erased by simplification before any check sees them;
- expressions restricted before `diff`.

The F3 code was reverted to `main`, and D3-1 stays open in the ledger.

**What these scenes are.** Each scene here is a refusal or value that a sound regularity contract must give. They **fail on the engine as it stands** (main's F3 behaviour), so they are kept out of `engine/tests/regression`. M4 moves them back as it fixes each class. The comments in each scene give the hand-computed reasoning. Some comments describe the m15b fence's expected messages, so M4 may reword those expectations.

| Class | Scenes | What goes wrong |
|---|---|---|
| A derivative whose lower order jumps (corner) | r351, r359 | `ay` at a corner where `vy` jumps |
| Corner through `diff`, or at a symbolic point | r353, r354, r355 | |
| Corner in t at a fixed x (superposition) | r374, r375, r376 | |
| Jump in the displacement (`step`) | r378–r381 | |
| Energy densities at a corner | r383–r386, r425 | r425 is a recursion error at a valid point |
| Inactive `max` branch | r387, r388, r400 | r387/r400 hit a recursion error |
| Isolated spike | r402–r405 | |
| Switching point with a zero field; odd `abs` through `diff` | r406–r410 | |
| Breakpoints closer than 1e-12; tiny jumps | r412–r414 | |
| Radical cusps and branch points | r420–r422, r424, r431 | |
| Solved parameters that place a switch | r426–r428 | |
| `diff` parity across coordinates | r429 | |

**The round-4 witnesses** (R15, R16, R18) are in `eval/review15b/REPORT.md`, round 4, and must join this set in M4:
- `at()` accepting `x + sin(π/7)² + cos(π/7)² − 1 ≠ 0` on a floating-point residual;
- `sqrt(-x^2)^2` and `cos(acos(1+x^2))` simplified to a smooth polynomial;
- `diff(y(w, x=0, t=t), t)` after restriction.

The valid controls that pass on the current engine stay in the regression suite:
- r352, r356, r357, r358, r377, r382;
- r401, r411, r415, r416, r423, r430.
