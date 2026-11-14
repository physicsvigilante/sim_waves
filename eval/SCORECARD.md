# Evaluation scorecard (applies from run 2 on)

Run 1 (`eval/run1/`) is frozen: its single score and notes stay exactly as written.

Each problem is scored on five SEPARATE dimensions. Never add them into one number;
report a count per dimension and per grade.

| Dim | Question | Grades |
|---|---|---|
| A. Interpretation fidelity | Does the scene say what the source says: media, relations, conditions, units, directions, assumptions? Missing facts kept missing? Nothing invented? | faithful / minor-deviation / misrepresented |
| B. Physical & numerical correctness | Are results computed by the engine and verified? | verified-proved / verified-sampled / unverified / wrong |
| C. Simulation coverage | How much of the source's physical system does the scene represent? | full / partial (say what is missing) / unsupported |
| D. Educational usefulness | Can a teacher view the situation and vary a real parameter? | demonstrated (by a teacher task) / available-untested / none |
| E. Textbook-answer completeness | Does the engine also give the requested quantity, and does it match the key? | matches / differs-book-disputed / differs / not-produced |

Rules
- **A is graded against the source, not against the answer.** A correct final answer from
  a misread scene is A = misrepresented. A refused scene that faithfully reports missing
  information is A = faithful, E = not-produced.
- **"Book disputed" needs evidence** (a reproducible calculation or a source misprint),
  recorded in the corpus record.
- **D stays "available-untested"** until a real teacher or student task has been done.
  A nice-looking view is not evidence.

Also record per problem
- source exposure: development-exposed (seen while designing the format) / unfamiliar
- production changes needed to author it: none / engine / format
- facts by provenance: stated / figure / convention / assumption / untagged
- illustrative values used (never allowed to change a reported result)
- result basis: exact / proved / sampled
