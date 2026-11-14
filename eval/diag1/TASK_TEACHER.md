# Teacher task: revise and explore two existing scenes

You are a physics teacher preparing a class. Two working scenes already exist (written by
the developer). Your job: change them the way a teacher would, ask new questions of them,
and build a view a class could look at. You test whether the format supports teaching
work, not whether you know the answers.

## Read first
- `format/FORMAT.md` (the only documentation).
- `format/examples/*.yaml` (skim).
- The baselines: `eval/diag1/baselines/echo.yaml` and `eval/diag1/baselines/pipe.yaml`.

## Do NOT read
- `engine/simwaves/`, `engine/tests/`, `corpus/`, the numbered source folders, or any
  folder under `eval/` except `eval/diag1/baselines/` and `eval/diag1/teacher/`.
- `eval/diag1/expected/` in particular.

## Rules for every step
- Never edit a baseline. Each step is a NEW file in `eval/diag1/teacher/`, named
  `<scene>.<step>.yaml` (e.g. `echo.E1.yaml`).
- Start each file with comment lines naming:
  - `# parent: <file it was derived from>`
  - `# change: <exactly what you changed and why>`
  - `# kind: property change | structural change | new question | view`
- Change only what the step needs. Keep every other fact. A hypothetical value is a
  teacher's choice, so tag it as `assumption`, never as `stated`.
- Run each file from `engine/`: `python3 -m simwaves run ../eval/diag1/teacher/<file>`.
- If a step fails, you may make up to 2 more tries (`echo.E1b.yaml`, `echo.E1c.yaml`).
  Never overwrite a file.
- Do not compute physics yourself. If the format cannot do something, say so; do not work
  around it with your own formulas.

## Steps
Echo hall (`echo.yaml`):
- **E1 (property change):** the hall is rebuilt with a 30 m ceiling. How does the
  longest wavelength heard loud at the listener change?
- **E2 (structural change):** from the BASELINE, replace the rigid ceiling with an
  open (pressure-release) boundary. What happens to the longest loud wavelength?
- **E3 (new question):** from the BASELINE, at a fixed wavelength of 10 m, how does
  the loudness at the listener vary as the listener walks from 100 m to 140 m from the
  source? Give the loudness at 120 m and say where it is largest.
- **E4 (view):** a viewer page for E3 that a class could look at
  (`python3 -m simwaves view ../eval/diag1/teacher/echo.html <scene files>`).

Pipe (`pipe.yaml`):
- **P1 (property change):** a warm day, with sound at 350 m/s. New fundamental?
- **P2 (structural change):** from the BASELINE, open the closed end. New fundamental?
  Is a 2nd harmonic now possible?
- **P3 (new question):** from the BASELINE:
  - Where are the displacement nodes and the pressure nodes of the 3rd harmonic?
  - With a 500 Hz tuning fork, which pipe lengths between 0.2 m and 1.2 m resonate?
- **P4 (view):** a viewer page showing the 3rd-harmonic displacement profile along the
  pipe (`pipe.html`).

## Report
Write `eval/diag1/teacher/REPORT.md` with one row per step:
- step, files tried, outcome (done / refused by engine / not expressible / not tried);
- the engine's numbers and what they mean physically;
- what was awkward.

End with three lines on whether this would work in a real class.
