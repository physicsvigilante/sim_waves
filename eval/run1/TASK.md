# Authoring test: write simulation scenes for unseen JEE wave problems

You are the scene author for the sim_waves engine. Your job is to turn each problem into a
scene file and use the engine's results to answer it.

## Read first
- `format/FORMAT.md`: the scene format (the only documentation you get)
- `format/examples/*.yaml`: 17 worked scenes for other problems

## Do NOT read
Anything under `engine/simwaves/`, `engine/tests/`, `corpus/`, or any `Solutions` folder.
You must work only from the documentation, as a real author would.

## For each problem in `eval/run1/problems/`
1. Write the scene to `eval/run1/work/<id>.v1.yaml`.
2. Run it from the `engine` folder: `python3 -m simwaves run ../eval/run1/work/<id>.v1.yaml`
3. If the engine rejects it, you may revise up to two more times. Save each revision as a
   new file (`.v2.yaml`, `.v3.yaml`) and never overwrite an earlier attempt.
4. Write `eval/run1/work/<id>.answer.yaml`:
   ```yaml
   answer: [b, c]          # option letters; a number with unit for numerical; a mapping for matrix
   final_scene: <id>.v2.yaml
   engine_fit: full | partial | none   # how much of the answer came from engine results
   reasoning: one or two lines linking the engine results to the answer
   friction: what was hard or impossible to express in the format (or "none")
   ```

## Rules
- Do not do physics in your head. Every number or formula behind the answer must come
  from an engine observable. If the format cannot express what you need, say so in
  `friction`, then answer from your own knowledge and set `engine_fit: none` or `partial`.
- Put every assumption you make in the scene's `assume` list.
- Conceptual statement questions: use the engine to check what it can (e.g. phases,
  dependence on parameters) and say which options it could not check.

## At the end
Write `eval/run1/work/LOG.md`: a short table (id, attempts, engine_fit, answer) plus the
three most common friction points.
