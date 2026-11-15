# Milestone 11 (ranged arbitrary values, comparisons in observe): result

## Transfer evidence (reserved cases)
- **Setup:** three original problems by a separate agent, prompted with the PLAN scope;
  each key checked by formula and by a numerical sweep. The developer did not read them
  before the freeze (`run/FROZEN.md5`).
- **Author:** a fresh Claude Sonnet agent, given FORMAT.md and examples only.
- **Grading:** by the developer after the run.

| Case | Structure | Attempts | Key match | Hand steps |
|---|---|---|---|---|
| R1 | car of unstated (subsonic) speed toward a wall; direct and echoed sound; multiple correct, one option depends on the speed | 1 | yes: A, B, C (D shown "not necessarily true") | none |
| R2 | open pipe vs a closed pipe of unstated length between two bounds; ordering options | 1 | yes: A | none |
| R3 | oblique Doppler, unstated subsonic speed; delay until the source frequency is heard (integer) | 2 | yes: 500 ms (the same at every sampled speed) | none ("after passing N" read as the reception time: recorded as an assumption) |

All 3 matched with `engine_fit: full` and no hand steps.

## Cost hypothesis vs actual
- **(a) An unstated quantity with a physical ceiling or floor, with no illustrative
  value:** confirmed in R1 (speed below sound), R2 (a length between two bounds) and R3.
- **(b) Options that compare or order computed quantities, decided by the engine:**
  confirmed in R1 and R2. The engine proved them over the whole range or flagged them as
  not necessarily true.

## Friction (for later)
- **The instant for beats** (R1 D): a reception time at which both the direct sound and
  the echo exist had to be chosen with fixed distances. A candidate for later is beats
  "at the listener while both arrive".
- **Two-sided ranged values:** they work, but FORMAT.md shows only one-sided examples.
  An example was added after the run (docs only).
- **"When is f heard":** it took an unknown emission time plus `arrives_at`. This works,
  and the question's ambiguity (emission or reception) belongs to the LLM side.

## Production changes by reason
- **Planned:** ranged arbitrary values; comparisons in `observe`.
- **Review 11 fixes (r143–r147):**
  - exact `==`;
  - a symbolic proof over the range, and dense sampling near the range ends;
  - independent rotation per name;
  - ranges kept in `explore`;
  - refusal of non-real values.

No engine change was needed after the frozen run.
