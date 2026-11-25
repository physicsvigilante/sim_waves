# Milestone 15b: wrong-answer fences: PLAN

**Status:** **approved by the owner on 2026-11-25**, including the exception for the blind stage (see "Process, and the exception requested").
**Base:** `main` at `7244bb6`.
**Context:** step 0 of the roadmap accepted at the project review of 2026-11-25 (`eval/project_review_2026-11/DECISIONS.md`, in PR #24). The defects are listed in `eval/KNOWN_ISSUES.md`, also in PR #24.

## Purpose

Remove six live wrong or invented answers now, without waiting for the larger milestones:
- **one correct fix:** D3-6;
- **five fences:** D3-2, D3-1, D3-3, D2-3 and D4-5. A fence is a sound, documented refusal of the affected class, as the review policy allows (CLAUDE.md, points 3 and 11).

Each fence leaves its defect **open** in `eval/KNOWN_ISSUES.md`, with the full repair still assigned to its milestone (M2, M3 or M4). No physics formula changes, and no new capability.

**Rules that apply throughout:**
- **Equivalent spellings.** Each rule covers every equivalent way of writing the same input, not only the reported example.
- **Valid neighbours** prove that the fence is not broader than its class.
- **Testing around G1.** Until M1 fixes it, the harness grades symbolic expectations PASS without checking them (G1). So every new test here uses **numeric** expected values or **refusals**, never symbolic expressions.
- **Weak negative-test matching.** A negative test currently passes if *any* observable fails for the expected reason. So every refusal is tested in a scene with **exactly one observable**.

---

## The six rules (each the invariant it protects)

### F1: D3-6, fix. A numerically solved propagation time is accepted only from a maintained bracket, with a verified residual

**Defect** ([#21](https://github.com/physicsvigilante/sim_waves/issues/21), severity 1). The circular-motion path solves the emission or arrival time by bisection (`Leg._bisect`, [doppler.py L270–L309](https://github.com/physicsvigilante/sim_waves/blob/7244bb6fa984c441d9fbcdcbf2954e99c44b5efb/engine/simwaves/doppler.py#L270-L309)). Its update `if (g(mid) > 0) == below` reverses the arrival branch (`below=False`). So a listener circling a source at 85 m from it gets an arrival time of 1 s instead of 85/340 = 0.25 s, and nothing checks the result.

**Mathematics:**
- **Emission branch.** g(τ) = |R(t₀) − E(τ) − w(t₀ − τ)| − v(t₀ − τ). Then dg/dτ ≥ v − |Ė(τ) − w| > 0 when the source moves slower than sound relative to the air.
- **Arrival branch.** g(t) = v(t − τ₀) − |R(t) − E(τ₀) − w(t − τ₀)|. Then dg/dt ≥ v − |Ṙ(t) − w| > 0 when the listener moves slower than sound relative to the air.
- **[Source]** Subsonic motion is already enforced (`_check_subsonic`, [doppler.py L413](https://github.com/physicsvigilante/sim_waves/blob/7244bb6fa984c441d9fbcdcbf2954e99c44b5efb/engine/simwaves/doppler.py#L413)).
- **So both functions are strictly increasing.** The one correct update is: if g(mid) > 0, then hi = mid, else lo = mid, for **both** branches. The emission branch already behaves this way.

**The rule:**
- bisection starts only from a bracket with g(lo) ≤ 0 ≤ g(hi), and keeps it;
- after the iterations, the **unsquared** residual |g(x)| must be within a stated bound, for example ≤ 10⁻²⁰ · max(1, v·|x − ref|) at 40 digits. The build documents the bound with its derivation from the Lipschitz constant ≤ 2v;
- otherwise the scene is refused ("the propagation time could not be established");
- `_valid`'s reality, causality and segment checks are unchanged.

**Class:** circular or piecewise motion with numeric data (the existing "numbers only" class, [doppler.py L261–L268](https://github.com/physicsvigilante/sim_waves/blob/7244bb6fa984c441d9fbcdcbf2954e99c44b5efb/engine/simwaves/doppler.py#L261-L268)); subsonic. **Guarantee:** a 30-digit decimal whose residual is verified, or a refusal.

**Consumers** (all through `Leg.receive` and `Leg.emit`): `arrives_at`, `emitted_at`, `frequency(ray, t=|emitted=)`, `wavelength(ray, …)`, `wave_speed_seen`, timed `beat_frequency`.

**Witnesses** (expected values by hand):

| Scene | Expected |
|---|---|
| source still at the origin; listener on a circle of radius 85 m centred on it, 17 m/s; `arrives_at(r, emitted=0[s])` | **0.25** s (the distance is constant, so 340t = 85) |
| the same, with a still listener at [85 m, 0 m] (polynomial path) | **0.25** s |
| circular listener, `emitted_at(r, t=1[s])` | **0.75** s |
| circular listener, `frequency(r, t=1[s])` | **500** Hz (constant distance, so no Doppler shift) |
| round trip: `emitted_at(r, t=arrives_at(r, emitted=0[s]))` | **0** s, to the result's precision |
| round trip at another emission time (τ = 0.3 s) on a listener circle **not** centred on the source (centre [100 m, 0 m], radius 30 m, 10 m/s) | `emitted_at(arrives_at(τ))` returns **τ** to 25 digits. **This is the property test for the general (non-constant-distance) case: the emission branch was already correct and checks the arrival branch independently.** |

### F2: D3-2, fence. `travel_time()` is a still-medium service

**Defect** ([#21](https://github.com/physicsvigilante/sim_waves/issues/21), severity 1). `_travel_time` ([scene.py L3078–L3100](https://github.com/physicsvigilante/sim_waves/blob/7244bb6fa984c441d9fbcdcbf2954e99c44b5efb/engine/simwaves/scene.py#L3078-L3100)) ignores `wind` and `flow`, and sorts the endpoints. So 360 m with 20 m/s wind gives 18/17 s both ways, instead of 1 s downstream and 9/8 s upstream.

**The rule:** on a gas or fluid medium, `travel_time` is refused unless every component of its `wind` (or `flow`, which is stored as `wind`) is **proved zero**, after the solution is substituted. "Not proved zero" (a nonzero literal, an expression, an unknown, or undecidable) means refused, with a message pointing to rays and `arrives_at`. The check runs before any integration.

**Equivalent spellings covered:** `wind` and `flow`; literal and expression values; units in km/h; wind solved from a fact; 2-D and 3-D wind vectors.

**Witnesses:**

| Scene (one observable each) | Expected |
|---|---|
| air at 340 m/s, wind [20 m/s, 0 m/s], 0 → 360 m | **refused** |
| the same, 360 → 0 m | **refused** |
| a fluid with flow [5 m/s, 0 m/s] | **refused** |
| wind given as `72 km/h` | **refused** |
| wind [0 m/s, 0 m/s], either direction | **18/17** s (valid neighbour) |
| no wind | **18/17** s |
| a string, μ = 10 g/m, T = 1 N, 0 → 2 m | **0.2** s (valid neighbour; strings unchanged) |
| the same air with wind, as a ray from [0 m, 0 m] to [360 m, 0 m], `arrives_at(r, emitted=0[s])` | **1** s (the existing correct model the refusal points to) |

**Full repair:** M4 (moving-medium transit with direction).

### F3: D3-1, fence. A point derivative at a corner needs every lower order to exist there

**Defect** ([#21](https://github.com/physicsvigilante/sim_waves/issues/21), severity 1). `_point` ([scene.py L2421–L2452](https://github.com/physicsvigilante/sim_waves/blob/7244bb6fa984c441d9fbcdcbf2954e99c44b5efb/engine/simwaves/scene.py#L2421-L2452)) compares one-sided values of only the **final** derivative at a breakpoint. For `ay` at a triangular pulse's corner, both second-derivative branches are 0, so it reports 0. But the velocity jumps from +1 m/s to −1 m/s there, so there is no finite acceleration.

**The rule:** at a breakpoint of a piecewise field at the stated instant, a point derivative of order n (`vy`, `slope`, `ay`) is accepted only if, for **every** order k = 1…n along the requested variables, the one-sided values agree. Otherwise it is refused as a corner. The existing order-n comparison stays.

**Equivalent spelling.** The same derivative can be requested through `diff(y(p, x=…, t=t), t, 2)` with the instant set by `at(…)`. **The build first reproduces what that route returns at the corner.** If it gives a finite value, the same rule is applied there. If that needs changes outside `_point` and `diff`/`at` (the stop rule), the build stops and reports.

**Witnesses** (string μ = 10 g/m, T = 1 N, so v = 10 m/s):

| Scene (one observable each) | Expected |
|---|---|
| triangle `0.01*max(0, 1 - abs(x - 0.5)/0.1)`, `ay(p, x=1.5[m], t=0.1[s])` (the corner passes x = 1.5 m at t = 0.1 s) | **refused** |
| the same, t = 0.099 s and t = 0.101 s (on the flanks) | **0** |
| the same, `vy` at the corner | **refused** (existing) |
| harmonic A = 1 cm, f = 1 Hz, +x, phase 0: `ay(w, x=0[m], t=0.25[s])` | **−π²/25 ≈ −0.394784** m/s² (−ω²A·sin(π/2)); compared numerically |
| a C¹ pulse `0.01*max(0, 1 - ((x - 0.5)/0.1)**2)**2`, at its edge x = 1.6 m, t = 0.1 s: `vy` | **0** (the slope is continuous there) |
| the same edge: `ay` | **refused** (the second derivative jumps from 0 to v²·8 m⁻¹ = 800 m/s²) |

**Full repair:** M4 (regularity contracts).

### F4: D3-3, fence. A timed ray phase exists only once the sound exists

**Defect** ([#21](https://github.com/physicsvigilante/sim_waves/issues/21), severity 2). `phase(ray, t=)` (`_ray_phase`, [rays.py L540–L544](https://github.com/physicsvigilante/sim_waves/blob/7244bb6fa984c441d9fbcdcbf2954e99c44b5efb/engine/simwaves/rays.py#L540-L544)) calls `total_phase` without the causal check that timed frequencies make through `doppler.trace` ([doppler.py L511](https://github.com/physicsvigilante/sim_waves/blob/7244bb6fa984c441d9fbcdcbf2954e99c44b5efb/engine/simwaves/doppler.py#L511)). So a source switched on at t = 0 has a "phase" at a point 340 m away at t = 0.5 s, before any sound has arrived.

**The rule:** when the ray's source has `emits_from`, `phase(ray, t=τ)` first runs the **same** causal check as the timed frequency (`emitted_at` via `trace`):
- if the emission time is before `emits_from`: "no sound yet", the existing `NoSound` refusal;
- if it cannot be decided (for example, a symbolic τ): refused.

Sources without `emits_from` (always on) keep today's behaviour, symbolic τ included. `phase_difference` (steady state, no time) is unchanged.

**Equivalent spellings covered:** a literal τ; `at(phase(r, t=t), t=0.5[s])`, which is refused because τ is symbolic when the phase is formed; reflected rays (`via`).

**Witnesses** (source at the origin, 500 Hz, `emits_from: 0 s`; point at [340 m, 0 m]; delay 1 s):

| Scene (one observable each) | Expected |
|---|---|
| `phase(r, t=0.5[s])` | **refused** (no sound yet) |
| `at(phase(r, t=t), t=0.5[s])` | **refused** |
| `phase(r, t=1.1[s])` | **100π ≈ 314.159** (emitted at 0.1 s: 2π·500·0.1); compared numerically |
| `frequency(r, t=0.5[s])` | **refused** (existing, unchanged) |
| without `emits_from`: `phase(r, t=0.5[s])` | **−500π ≈ −1570.80** (valid neighbour); compared numerically |
| a reflected ray via a rigid wall at x = 170 m with the listener at the source (round trip 340 m, delay 1 s): `phase(echo, t=0.5[s])` | **refused** |

**Full repair:** M4 (causal applicability shared across all timed ray services).

### F5: D2-3, fence. A pulse's width needs a fully specified profile

**Defect** ([#20](https://github.com/physicsvigilante/sim_waves/issues/20), severity 2). `_width` ([energy.py L227–L263](https://github.com/physicsvigilante/sim_waves/blob/7244bb6fa984c441d9fbcdcbf2954e99c44b5efb/engine/simwaves/energy.py#L227-L263)) counts a whole piecewise region as support when the piece is "not identically 0". With an arbitrary function F windowed to [0, 1], it reports 1 m, though F could be nonzero on only half of that.

**The rule:** `width()` is refused when the pulse's shape contains **an arbitrary function** (any `functions:` entry) anywhere in it. This is checkable before any set computation.
- **[Hypothesis]** For explicit analytic pieces, the existing support logic is sound: a non-identically-zero analytic piece vanishes only at isolated points, which does not change the measure. The fence therefore targets only the class where support is unknown.

**Equivalent spellings covered:** F inside `max`, `abs` or `step`; F of a scaled argument (`F(2*x)`); nested functions; F appearing in a sum with explicit terms.

**Witnesses** (string μ = 10 g/m, T = 1 N):

| Scene (one observable each) | Expected |
|---|---|
| `functions: [F]`, shape `F(x)*(step(x)-step(x-1))`, `width(p)` | **refused** |
| shape `max(0, F(x))*(step(x)-step(x-1))` | **refused** |
| shape `max(0,1-abs(2*x-1))*(step(x)-step(x-1))` | **1** m (valid neighbour) |
| shape `max(0,1-abs(4*x-2))*(step(x)-step(x-1))` | **0.5** m (valid neighbour) |

Existing r90 and r307 must be unchanged.

**Full repair:** M3 (support contracts).

### F6: D4-5, fence. An absolute Celsius temperature must be written as `degC`

**Defect** ([#22](https://github.com/physicsvigilante/sim_waves/issues/22), severity 1). `degC` is stored as a scale-only unit ([units.py L19–L35](https://github.com/physicsvigilante/sim_waves/blob/7244bb6fa984c441d9fbcdcbf2954e99c44b5efb/engine/simwaves/units.py#L19-L35)). The 273.15 K offset is added only when the unit text is exactly `"degC"`: in `Scene.quantity` ([scene.py L414–L422](https://github.com/physicsvigilante/sim_waves/blob/7244bb6fa984c441d9fbcdcbf2954e99c44b5efb/engine/simwaves/scene.py#L414-L422)), and for output in `_split_unit` ([run.py L392](https://github.com/physicsvigilante/sim_waves/blob/7244bb6fa984c441d9fbcdcbf2954e99c44b5efb/engine/simwaves/run.py#L392)). So `27 (degC)` is read as 27 K, and the sound speed comes out as 104.075 m/s instead of 347.004 m/s.

**The rule**, in `parse_unit`, so that it covers fields, `in <unit>` output, `nearest(x in …)` and expected values alike:
- walk the unit expression and compute the net exponent of `degC`;
- if it is **+1 and the unit's dimension is pure temperature** (an absolute-temperature spelling), the unit text must be exactly `degC`, or it is refused ("write absolute temperatures as `27 degC` or in K");
- any other non-zero exponent of `degC` with a pure-temperature result (for example `degC^2`) is refused;
- `degC` inside a compound unit whose dimension is not pure temperature (`1/degC`, `J/degC`, `degC/s`) keeps its current scale-only meaning, which is correct for a temperature **difference**;
- `20[degC]` stays refused, as today.

**Witnesses** (gas: γ = 7/5, M = 29 g/mol, R = 8.31 J/(mol·K), `speed(air) in m/s`):

| Temperature written as | Expected |
|---|---|
| `27 degC` | **347.0041786…** m/s: √(1.4 × 8.31 × 300.15 / 0.029) |
| `300.15 K` | **347.0041786…** m/s |
| `"27 (degC)"` | **refused** |
| `27 degC^1` | **refused** |
| `27 degC**1` | **refused** |
| output `... in degC^1` | **refused** |
| an expansion coefficient `1.2e-5 1/degC` (a difference unit) | accepted, equal to `1.2e-5 1/K` (the build checks existing uses) |

Existing r168, r203, r204, n11 and example 11_02_cnt_007 must be unchanged.

**Full repair:** M2 (affine units carried through parsing).

---

## Scope, footprint and stop rule (by rule, per CLAUDE.md point 7)

| Rule | Producers that must change | Consumers re-tested |
|---|---|---|
| F1 | `Leg._bisect` (update rule, bracket check, residual postcondition) | every timed ray service on circular or piecewise motion; r122, r123, r131, r136 (circular-motion regressions) |
| F2 | `_travel_time` (guard) | `travel_time` on strings and still air; r81, r86, r102, example 11_02_011 |
| F3 | `_point` (lower-order continuity), and `diff`/`at` only if the equivalent route needs it | `vy`, `slope`, `ay`; energy densities that call `_point` (none expected) |
| F4 | `_ray_phase` (causal check through `trace`) | ray `phase`; no existing regression uses it |
| F5 | `_width` (guard) | `width`; r90, r307 |
| F6 | `parse_unit` (Celsius rule) | every unit parse; r168, r203, r204, n11, 11_02_cnt_007 |

- **Expected size:** about 100–150 changed production lines, plus FORMAT.md notes for each refusal.
- **Scope change, approved by the owner on 2026-11-25 (review round 1, R3):** F3's producers now include the energy densities (`energy.py` `_density`), which share F3's regularity check; the stop rule was applied and the owner chose to extend F3 rather than leave that spelling open.
- **Stop rule:** if any rule's dependency reaches beyond its listed producers (for example, F3's `diff` route needs changes to the expression parser or the limit machinery), the build **stops and reports**, and that item moves to its milestone.
- **Unchanged:** physics formulas, the solver, searches, grading. G1 is not touched here; it is M1's.

## Tests

- **New regression scenes r339+:** one per witness row, about 30 scenes. Every refusal is a single-observable scene with `expect: {error: rejected, message: "…"}`. Every value is numeric (because of G1).
- **Systematic transformations** (CLAUDE.md point 9):
  - unit rescaling (wind in km/h; temperature in K and in degC);
  - equivalent spellings (degC variants; `diff` against `ay`; `at(phase(…))`);
  - degenerate limits (zero wind; a flank point beside a corner);
  - nesting (`at` around `phase`);
  - reordered observations, by placing a valid and a refused observable in separate scenes and checking that the valid one's value is identical either way.
- **All suites,** on Windows and in Linux CI: regression, examples, negative, export, `test_limits.py`, `test_limits_review.py`.

## Cost hypothesis

After this milestone, without further work:
- **(a)** every arrival or emission time on circular or piecewise motion is either correct, with a verified residual, or refused;
- **(b)** no `travel_time` on a moving medium returns a value;
- **(c)** no point derivative at a corner of a piecewise field returns a value unless every lower order exists there;
- **(d)** no ray phase is reported before its sound exists;
- **(e)** no width is reported for an unspecified profile;
- **(f)** no absolute Celsius value loses its offset through its spelling.

**Coverage cost** (recorded in RESULT.md):
- `travel_time` in wind (use rays);
- `ay` at corners;
- timed phase with a symbolic time for switched-on sources;
- `width` of arbitrary-function pulses;
- non-canonical Celsius spellings.

## Process, and the exception requested

1. **The owner approves this PLAN,** including the exception below.
2. **Build** on `feat/m15b-fences`. `engine_before/` is copied at the start. Regressions, FORMAT.md notes, and `eval/review15b/BRIEF.md`, which tells the reviewer to hunt for spellings that bypass each rule and for wrong refusals of valid neighbours.
3. **Stage 1:** PR, Astra's review on Extra High, every confirmed finding fixed with a regression test, re-review. The stop rule for repeated causes applies (point 5).
4. **Stage 2, reduced:**
   - RESULT.md (the cost hypothesis against what happened, and the coverage cost);
   - a FINDINGS.md entry;
   - `eval/KNOWN_ISSUES.md` updated: D3-6 closed; D3-2, D3-1, D3-3, D2-3 and D4-5 marked "fenced", and **still open** for their milestones;
   - the same PR updated;
   - the owner merges.

**Exception requested: no reserved problems, freeze or blind run for this milestone.**
- **Reason:** five items are refusals and one is a numerical fix with an exact oracle. A fresh author solving reserved book problems would rarely reach these paths, and would not test the rules.
- **The evidence instead:**
  - (i) witnesses derived by hand, together with the property test of F1 (a round trip on a non-centred circle);
  - (ii) the systematic equivalent-spelling and valid-neighbour tests above;
  - (iii) Astra's adversarial stage-1 review, briefed to hunt for bypasses.
- This follows the m15a precedent of adapting stage 2 to what a milestone changes. **It needs the owner's explicit approval.**

## Dependencies

PR #24 (decisions, ledger, policy points 7–11) should be merged first. This branch will be rebased on it so that it can update `eval/KNOWN_ISSUES.md`.
