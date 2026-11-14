# Transcription task (corpus records from problem and solution images)

Write one YAML record per problem, in the format of `corpus/README.md`. Read one record
from `corpus/23_Superposition_and_Standing_Waves/` as a model.

**Viewing images.** The images are on the user's device. Copy them into your container
with `mcp__remote-devices__device_stage_files`:
- Paths look like `~/Documents/sim_waves/11_Mechanical_Waves_sardana/01_Wave_Equation_and_Properties/Problems/001.png`.
- Use at most 50 files per call.
- The copies appear under `/mnt/user-data/uploads/`; open each one with the Read tool.

**Writing records.** Write each record on the device with
`mcp__remote-devices__device_bash`, using a heredoc
(`cat > file <<'EOF2' ... EOF2`), to
`$HOME/mnt/sim_waves/corpus/<folder>/<subfolder>/<name>.yaml`, where name is the image
stem (e.g. `001`).

**Record ids.** Use `<folder number>/<subfolder number>/<name>`, e.g. `11/01/001`.

**Fields.**
- `number`: the question number printed on the image, if any.
- `source`: the problem and solution paths, relative to the project root.

**Rules.**
- Copy the statement, options and every number in the figure faithfully. Equations go in
  plain ASCII. Describe each figure in words and include every number read off it.
- `answer`: the book's key, as printed.
- `verified`: recompute the answer yourself. Write "Matches key." or explain the
  mismatch and mark it DISPUTED, with the calculation.
- `notes`: misprints, ambiguities and missing data. Keep notes about the answer out of
  `statement`, `figure` and `options`.
- If an image holds more than one question, or a question is cut off, say so in `notes`.
- Check each file parses: `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <file>`.
- At the end, write `corpus/<folder>/<subfolder>/_INDEX.md`: a list of ids, with one line
  for each problem you could not transcribe.
