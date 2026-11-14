# View experiment: findings

Question: can a faithful view (plus one varied physical input) be drawn from a scene and
the engine's output alone, with the viewer doing no physics?

Scenes: 22/03/dmt_004 (two strings), 22/02/bmc_006 (hanging rope), 22/01/bmc_004
(fully symbolic, inverse), 22/03/cnt_005 (rope power, inverse). Viewer: `viewer.html`
(built with `python -m simwaves view`). Inspected by headless-browser screenshots; no
teacher has used it yet.

## Pass/fail against the criteria set beforehand
- **Phase 1, scenes exactly as written: FAIL for 3 of 4** (`phase1_as_is.md`).
  - Symbolic scenes have no numbers to draw.
  - The default "animate" needed a time scale that the source does not give.
  - The hanging rope needed plots, not an animation.
  - No scene said what to vary.
- **Phase 2, with three additions to the scene: PASS for 4 of 4.** The viewer draws
  arrays produced by the engine; its script contains no physics.
- **The three additions:**
  - **`view` panels:** `snapshot` (a wave at one instant), `animate`, and
    `plot <expression> vs <variable> over a range`.
  - **`illustrate`:** values for symbols, used only for drawing and labelled
    "not from the source".
  - **`explore`:** one physical input to vary (a symbol or a scene path). Each value
    re-solves the whole scene, so inverse problems are re-solved too.

## What the screenshots showed that tests could not
1. **Auto-scaled windows hid the effect being explored.** Each varied value got its own
   "2 wavelengths" window, so every variant looked identical. Fixed: one window shared by
   all panels and all values, with the other values drawn in grey.
2. **The two strings were on different x-scales.** Fixed by the same shared window.
3. **A snapshot needs fewer facts than an animation.** The two-strings source gives only
   the shapes at t = 0, which a snapshot shows with nothing invented. An animation would
   need tension and mu, which the source never gives.

## Still open
- Points used by observables (e.g. A at x = 20 cm) are not marked on the plots.
- Animations play slowed down, but the slow-down factor is not stated.
- Facts in the existing examples are "untagged". Provenance tags exist now but are
  not yet used in them.
- Educational usefulness remains **available-untested** until a teacher task is done.

## Independent review of this round (Fable 5.2, medium effort)

- **What it confirmed:**
  - **The viewer's honesty labels did not follow the slider.** A rejected value showed
    the base results; the illustrative values and re-check cards stayed on the base scene.
  - **Plot ranges still rescaled between varied values.** Item 1 above had been fixed
    for snapshots and animations only, not plots.
  - **Unchecked or unsafe inputs:**
    - `illustrate` accepted wrong units and impossible values;
    - a single NaN blanked the page;
    - each variant took the first panel's window;
    - `_verify` did not check declared kinds;
    - a true redundant fact was reported as a contradiction.
  - Plus minor issues: axis units, unknown panel keys, an unshown `missing` list,
    `equivalent()` sampling, and docs.
- **All fixed.** Each finding has a check in `engine/tests/test_export.py` (22 checks).
  The animation y-range is now fixed across frames and values, and scene text is fully
  escaped in the page.
- **Its view of the main teaching gap:** the explored view is not anchored to the
  source. The source's own value is now marked, but the points the problem asks about
  (e.g. A at x = 20 cm) are still not marked on the plots.
