# Review brief: milestone 15b, wrong-answer fences

**For:** ChatGPT (Astra), the independent reviewer.
**PLAN (approved 2026-11-25):** `eval/m15b_fences/PLAN.md`. Base: `main` at `7244bb6`.
**What this milestone is:** one correct fix and five fences (sound refusals) for six confirmed defects. No physics formula changes, and no new capability. The fenced defects stay open in the known-issues ledger for their later milestones.

**What to hunt for, in order:**
1. **A wrong value still accepted through another spelling of a fenced input** (the review policy: a rule must cover equivalent ways of writing the same input).
2. **A wrong refusal of a valid neighbour:** a fence broader than its class.
3. **Wrong values on the F1 path.**

Expected values below are computed by hand. No reserved problems exist for this milestone: the owner approved its exception (PLAN, "Process"), so the evidence is the witnesses, the spelling tests and this review.

## The six rules, where they live, and what to try

| Rule | Code | The rule | Try to break it with |
|---|---|---|---|
| **F1** (D3-6, a fix) | `doppler.py` `Leg._bisect` | Both bisected functions increase strictly when motion is subsonic relative to the air, so one update rule (g > 0 moves the upper end) serves both branches. The bracket g(lo) ≤ 0 ≤ g(hi) is checked first; the unsquared residual must be ≤ 10⁻²⁰·max(1, v·\|x − ref\|) at the result, or the time is refused | other circular geometries; a source on a circle (emission branch); wind with circular motion; echoes involving a circle; times at segment boundaries (`starts`) |
| **F2** (D3-2) | `scene.py` `_travel_time` | `travel_time` is refused on a gas or fluid unless every `wind`/`flow` component is proved zero after the solve | wind solved from a fact; symbolic wind; wind in other units; 3-D wind; a fluid with `flow` |
| **F3** (D3-1) | `scene.py` `_point`, `_switching_args`, `_diff`; the message in `_at` | **Numeric point:** at a breakpoint, a derivative of order n needs every order 1…n to have equal one-sided values. **Symbolic point, or `diff`:** the switching argument (inside abs, max/min, step, sign) must be nonzero, recorded as a condition that `at()` checks | other routes to a point derivative at a corner (`max_in`, `frequency_of`, energy densities, views); `diff` in x at a spatial corner; nested `at`; a C¹ join through the `diff` route (refused conservatively; see Limitations) |
| **F4** (D3-3) | `rays.py` `_ray_phase` | For a source with `emits_from`, `phase(ray, t=)` runs the same causal check as a timed frequency (`doppler.trace`); "no sound yet", or refused if it cannot be decided | reflected rays; `phase_difference`; a source with `starts`; a time just after onset |
| **F5** (D2-3) | `energy.py` `_width` | `width()` is refused when the shape contains any unspecified function | F through a derived (reflected or transmitted) pulse; F combined with explicit terms |
| **F6** (D4-5) | `units.py` `parse_unit` (and `split_quantity`) | If degC's net power in a unit is nonzero, either it is ±1 inside a compound unit that is not pure temperature (a difference, allowed), or the unit text must be exactly `degC`; anything else is refused | spellings in fields, `in <unit>`, `nearest(x in …)`, expected values; `degC^-1`; `K*degC/K` |

## Independent expected values (public witnesses, regression r339–r373)

**F1:**
- a listener circling a still source at 85 m: 340t = 85, so t = **1/4 s** (the old engine gave 1 s);
- the round trip `emitted_at(arrives_at(0))` = **0**;
- off-centre circle (centre 100 m, radius 30 m, 10 m/s), emitted at 0.3 s: 340(t − 0.3) = \|P(t)\|, so t = **0.68060972853145303223705425890** (a separate mpmath root-find), and the round trip = **0.3 s**.

**F2:**
- the refused cases would be 1 s downstream and 9/8 s upstream; the old engine gave 18/17 s both ways;
- valid neighbours: zero wind gives 18/17 s; a string at 10 m/s over 2 m gives 0.2 s; a ray in the wind gives **1 s** (360 − 20t = 340t).

**F3:** string at v = 10 m/s.
- The triangle's tip passes x = 1.5 m at t = 0.1 s: there, y(t) = 0.01 − \|t − 0.1\|, so vy jumps from +1 to −1, and `ay` is refused (the old engine gave 0). On the flanks, `ay` = 0.
- `at(diff(y, t), t=0.099)` = **+1 m/s**.
- `at(vy(x=x, t=0.1), x=1.49)` = **−1 m/s**.
- Harmonic: `ay` = −ω²A = **−π²/25**.
- C¹ edge, f = (1 − u²)²: the slope is continuous, so vy = **0**; y_xx jumps from 0 to 8 m⁻¹, so `ay` is refused.

**F4:** delay 1 s.
- phase at 0.5 s: refused;
- phase at 1.1 s = 2π·500·1.1 − (2π/0.68)·340 = **100π**;
- without `emits_from`: phase at 0.5 s = **−500π**.

**F5:** explicit triangles give widths **1 m** and **1/2 m**.

**F6:**
- 27 degC = 300.15 K, so v = √(1.4 × 8.31 × 300.15 / 0.029) = **347.0041786…** m/s (the old engine read `27 (degC)` as 27 K: 104.075 m/s);
- `1.7e-5 1/degC` = `1.7e-5 1/K`, so √(1.3×10¹¹ × 1.7×10⁻⁵ × 20 / 9000) = **70.0793…** m/s.

**On the old engine** (`eval/m15b_fences/engine_before`), 20 of the 35 new scenes fail with the old wrong behaviour; r359 fails only on its message ("velocity" corrected to "acceleration"); the 14 others are controls that pass on both.

## Limitations, and what is deliberately left open

- **Conservative refusals (a declared cost):** through `diff` or a symbolic point, a derivative exactly at a switching point is refused even where it exists (a smooth C¹ join). The precise one-sided check runs only at a numeric point in `vy`/`slope`/`ay`.
- **Coverage cost:** `travel_time` in wind; `ay` at corners; timed phase at a symbolic time for switched-on sources; `width` of unspecified profiles; non-canonical Celsius spellings.
- **Found during the build, not fixed here (outside the stop list):** a value that cannot be converted to a number (for example DiracDelta(0)) makes `run.py`'s realness check abort the **whole scene**, outside the per-observable error handling ([run.py L644](https://github.com/physicsvigilante/sim_waves/blob/7244bb6fa984c441d9fbcdcbf2954e99c44b5efb/engine/simwaves/run.py#L644)). It was reached by `at(diff(y, t, 2), corner)`, which F3 now refuses earlier. It will be added to the ledger as **G4**.
- **Test grading:** G1 (the harness passes symbolic comparisons unchecked) is unfixed until M1. So every new expected value here is a number or a refusal, and every refusal is a scene with one observable.
- **Untouched:** the solver, searches, grading, `expr.py` and `run.py`.
