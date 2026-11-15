# Authoring test: write simulation scenes for unseen JEE wave problems

You are the scene author for the sim_waves engine. Your job is to turn each problem into a
scene file and use the engine's results to answer it.

## Read first
- `format/FORMAT.md`: the scene format (the only documentation you get)
- `format/examples/*.yaml`: the worked scenes for other problems (folders 22 and 23)

## Do NOT read
Anything under `engine/simwaves/`, `engine/tests/`, `corpus/`, the numbered source folders
(`11_*`, `22_*`, `23_*`, `24_*`), `wanes_full.pdf`, `.export/`, any `Solutions` folder, or `eval/` outside `eval/run5/`.
You must work only from the documentation, as a real author would.

## For each problem in your batch (listed in the prompt) from `eval/run5/problems/`
1. Write the scene to `eval/run5/work/<id>.v1.yaml`.
2. Run it from the `engine` folder: `python3 -m simwaves run ../eval/run5/work/<id>.v1.yaml`
3. If the engine rejects it, you may revise up to two more times. Save each revision as a
   new file (`.v2.yaml`, `.v3.yaml`) and never overwrite an earlier attempt.
4. Write `eval/run5/work/<id>.answer.yaml`:
   ```yaml
   answer: [b, c]          # option letters; a number with unit for numerical; a mapping for matrix
   final_scene: <id>.v2.yaml
   engine_fit: full | partial | none   # full ONLY if hand_steps is empty
   hand_steps: []   # every number or relation you worked out yourself (a path length, a count, M*g...)
   coverage: full | partial | unsupported  # how much of the problem's physical system the scene represents
   not_represented: what the scene leaves out, or "nothing"
   missing_in_source: facts the problem needs but does not give (or "none")
   reasoning: one or two lines linking the engine results to the answer
   friction: what was hard or impossible to express in the format (or "none")
   ```

## Rules
- Tag every fact in `given` with its source (stated / figure / convention / assumption), as
  FORMAT.md describes. Never present an assumption as a stated fact.
- If the problem as printed is impossible, ambiguous or missing information, a scene that
  shows this faithfully is a good result. Say so in the answer file; do not force an answer.
- Do not do physics in your head. Every number or formula behind the answer must come
  from an engine observable. If the format cannot express what you need, say so in
  `friction`, then answer from your own knowledge and set `engine_fit: none` or `partial`.
- Put every assumption you make in the scene's `assume` list.
- Conceptual statement questions: use the engine to check what it can (e.g. phases,
  dependence on parameters) and say which options it could not check.

## At the end
Write `eval/run5/work/LOG_<batch>.md`: a short table (id, attempts, engine_fit, answer) plus the
three most common friction points.

## Format notes for this run
- Problems are single correct, multiple correct (answer is a list of letters), matrix match
  (a mapping), or numerical. Numerical problems with several parts take a mapping.
- At most 3 attempts per problem (v1, v2, v3). Extra probe files count as attempts.
- Some problems need physics the engine does not model yet (for example rods, pressure
  waves from point sources, path differences, walls as reflectors, multiple reflections).
  Model what the format supports, set `coverage` honestly, and say what is missing.
- An `expect` block is not needed in your scenes.
