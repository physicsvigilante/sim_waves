# Milestone 15a stage 2: the reserved-scene run

m15a changes how scenes run, not what authors write, so stage 2 runs reserved **scenes**
(PLAN, "Stage 2"), not a blind authoring task.

- **Freeze:** `FROZEN.md5`, taken at `2fe4ecb6cd53b627d908a6d7dad2e907883cb772`, the
  commit Astra passed in review round 12. It covers FORMAT.md, every engine source file,
  `engine/requirements.txt` and the CI workflow. `engine_at_run/` is a copy of the engine
  at the freeze. The hashes are of the Windows working copy; check them from this folder
  with `md5sum -c FROZEN.md5`.
- **Reserved set:** `../reserved/S1`-`S6`, each a scene and a key. They were written by a
  separate agent that read only the PLAN, FORMAT.md and the examples, and did not run the
  engine. The developer did not read them before the freeze.
- **Run, on Windows** (from `engine/`), with the default limits (120 s, 2048 MB):
  `python -m simwaves test ../eval/m15a_containment/reserved -j 3`, then each scene alone
  with `python -m simwaves run <scene>`, and a check that no `simwaves.child` process is
  left after each.
- **Run, in CI:** the same folder on Linux, in the workflow, after the freeze commit.
- **Acceptable outcome:** what each key lists, the hand-computed value or `LIMIT`. Never a
  wrong value, a hang or a surviving process.
