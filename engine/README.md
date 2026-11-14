# simwaves engine (v0)

Physics engine for LLM-authored JEE wave scenes. The scene format is in `../format/FORMAT.md`.

Needs Python 3.10+, `sympy`, `pyyaml`.

```
python -m simwaves run  ../format/examples/17_03_dmt_004.yaml
python -m simwaves test ../format/examples      # worked corpus scenes vs book answers
python -m simwaves test tests/negative          # scenes that must be rejected
python -m simwaves test tests/regression        # one scene per defect found by reviews and runs
python tests/test_export.py                     # viewer export checks
```

## Modules
- `units.py`: unit text -> exact SI factor + dimension; dimension checks on every scene field
- `expr.py`: whitelisted expression language translated to SymPy; never calls eval()
- `scene.py`: media, waves, junctions, resonators, emitters and their observables
- `rays.py`: point sources, plane reflectors, rays, interference by path difference
- `modes.py`: standing-wave patterns (nodes, mode shapes, touch/pluck) and beat envelopes
- `export.py` + `viewer/template.html`: sampled view data and the static viewer (no physics in the viewer)
- `solver.py`: solves `given` facts; exactly one solution or a clear error
- `run.py`, `harness.py`, `__main__.py`: running scenes and checking `expect` blocks

## Guarantees
- No silent defaults: anything a result needs but the scene never fixed -> UndeterminedError
- Over-specified values are cross-checked -> SceneError on mismatch
- Contradictory facts -> InconsistentError naming the first contradicting fact
- Several fitting situations (incl. periodic families) -> AmbiguousError listing them
- Equations with a free t must hold for all t (matched sin/cos coefficients)
- Unknowns that live inside sines/cosines are solved on the unit circle (S, C with
  S^2 + C^2 = 1); SymPy's trig solver alone silently loses branches
