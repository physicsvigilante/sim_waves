# Run 7: broad blind test after milestones 12–13 (book chapter "Waves")

## Two sets
- **Set D2 (Doppler):** the 12 Doppler problems found while sampling for run 6. They are
  listed in `corpus/book4_waves/_SKIPPED.md` with "run6:":
  - single 159, 147, 156, 26;
  - integer 4, 1, 13;
  - jee_main 7, 23, 19, 30;
  - jee_advanced 13.
  They include radar and light, which m12 added.
- **Set S2 (sealed sample):** 32 more problems.
  - They are taken by continuing down each section's seeded order in `candidates.json`,
    past runs 5 and 6.
  - Quotas: single 12, multiple 3, reasoning 2, comprehension 3, matrix 1, integer 3,
    jee_main 4, jee_advanced 4.
  - Duplicates, unreadable problems and any new Doppler problems are skipped and recorded.
    New Doppler problems stay sealed.

## Process (as in run 6)
1. **Transcription:** a separate agent writes the full records to the corpus, and author
   copies without answers to `eval/run7/problems/`. The developer sees counts only.
2. **Freeze:** the engine after m13 (main at PR #11) and FORMAT.md (`FROZEN.md5`).
3. **Authors:** three fresh Sonnet agents. Each runs only its own files; no wildcard runs.
4. **Grading:** an independent Opus agent, standing in for Fable 5.2, which needs usage
   credits. It uses the run 5 and run 6 conventions and grades the five dimensions.
5. **Write-up:** `SCORECARD.md`, top gaps by layer, and a comparison with run 6.

## Hypotheses (written before the run)
- **H1:** no wrong engine value. Radar and light problems use `type: em` with no
  stand-ins; the m12 guard makes a stand-in impossible.
- **H2:** answers decided by hand stay at or below run 6 (6%). Rounded options are picked
  with `nearest`, units with `in`, and tensions with `weight` or `stretch`.
- **H3:** the remaining gaps are mostly format and authoring (reading the source),
  rather than physics.
