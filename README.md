# sim_waves

A simulation system for JEE Main/Advanced wave problems that an LLM can author and that
is used for teaching and exploration. The LLM frames a problem as a YAML scene: media,
waves, sources, facts with provenance, and the questions to observe. The engine stays
close to physics. It assembles the scene, solves it, verifies the result, and returns
exactly one answer or a clear error.

| Folder | Contents |
|---|---|
| `engine/` | The Python engine (SymPy) and the static viewer; see `engine/README.md` |
| `format/` | `FORMAT.md`, the only document authors read; `examples/`, worked scenes; `FINDINGS.md`, the design log and review history |
| `corpus/` | Transcribed problems, each with the book key and an independent check (`README.md`, `TRANSCRIBE.md`) |
| `eval/` | Authoring runs and diagnostics. Each run folder is frozen with its task, scenes, grades and the engine as it was |

The source images (`11_*`, `22_*`, `23_*`, `24_*` folders) and the book PDF are kept out
of the repository.

## Quick start
```
cd engine
pip install sympy pyyaml
python -m simwaves run ../format/examples/23_01_cnt_008.yaml
python -m simwaves test ../format/examples
python -m simwaves test tests/regression
```

## Evaluation history
- **run1–run2:** folder 22.
- **run3:** held-out folder 23.
- **run4:** held-out folder 11 and 24/01.
- **diag1:** charter diagnostic: layers, teacher test, boundary diagnosis.

Each run has a `SCORECARD.md`. Results are reported on five separate dimensions:
interpretation, correctness, coverage, educational use and textbook answer.
