# Transcription task: book chapter "Waves" (wanes_full.pdf), sampled problems only

Transcribe the problems that are SAMPLED into a blind authoring test. Leave every other
problem in the book untouched and unrecorded: they stay sealed for later tests.

## Source
- Page images of book pages 82–124 are on the device:
  `~/Documents/sim_waves/.export/book_pages/p-082.png` ... `p-124.png`.
  - Copy them into your container with `mcp__remote-devices__device_stage_files` (at most
    50 per call), then open each one with the Read tool.
  - You may also use the PDF text layer on the device:
    `pdftotext -f N -l N -layout ~/mnt/sim_waves/wanes_full.pdf -`. It garbles formulas, so
    trust the image.
- **Section pages:**
  - single correct 82–94;
  - multiple correct 94–98;
  - reasoning 98–99;
  - linked comprehension 99–104;
  - matrix match 104–106;
  - integer 106–107;
  - JEE Main archive 107–112;
  - JEE Advanced archive 112–121 (its subsections are single, multiple, comprehension,
    matrix and integer; number its problems 1, 2, 3, ... in order of appearance across all
    its subsections).
- **Answer keys:** pages 121–124, keys only, no worked solutions.

## Which problems
`candidates.json` lists, for each section, a quota and a random order of problem numbers.
Go down the order and take problems until the quota is met. Skip a problem, recording why
in `_SKIPPED.md`, if:
- it is about the Doppler effect (moving sources or observers, beats from motion, radar,
  echoes from moving bodies);
- it duplicates a problem already in the corpus: run
  `python3 corpus/book4_waves/dedupe.py "<statement>"` from the project root; a score above
  about 0.75 with the same numbers counts as a duplicate;
- it cannot be transcribed (an unreadable figure, or the key is missing);
- its number does not exist.

For comprehension, a sampled number is one question. Include its full passage in its
statement.

## Record format (one YAML per problem)
Write the record to `corpus/book4_waves/<section>/<number>.yaml`, using the fields from
`corpus/README.md`. Read one record in `corpus/23_Superposition_and_Standing_Waves/` as a
model.
- `id`: `B4/<section>/<number>`.
- `source`: book page(s).
- `format`: single_correct | multiple_correct | numerical | matrix_match.
  - Reasoning questions are single_correct with their options.
  - Integer questions are numerical.
- `statement`, `figure` (every number on it), `options`.
- `answer`: the book's key, as printed.
- `verified`: your own independent calculation. Write "Matches key." or mark it DISPUTED
  with the working.
- `notes`.

Never write a hint toward the answer in `statement`, `figure` or `options`. Check that
each file parses with
`python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <file>`.

## Your sections
Given in your prompt. Work only on them. At the end write
`corpus/book4_waves/<section>/_INDEX.md` listing the taken ids, and add your skips to
`_SKIPPED.md` (one line each: section, number, reason; append, do not overwrite).
