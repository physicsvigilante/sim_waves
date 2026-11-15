# Run 6: broad blind test after milestones 9–11 (book chapter "Waves", including Doppler)

## Two sets
- **Set D (Doppler):** every Doppler problem in the book not used as an m10 reserved case.
  - These are the 19 listed as Doppler in `corpus/book4_waves/_SKIPPED.md`, minus
    single/44, jee_advanced/17, jee_main/50 and jee_advanced/50.
  - About 15, including those the m10 agent judged out of scope (light or radio; a sound
    speed relative to a train). They test honest refusal and coverage.
- **Set S (sealed sample):** 32 more problems drawn from the problems still sealed after
  run 5.
  - They are taken by continuing down each section's seeded order in
    `corpus/book4_waves/candidates.json` past what run 5 took.
  - Quotas: single 12, multiple 3, reasoning 2, comprehension 3, matrix 1, integer 3,
    jee_main 4, jee_advanced 4.
  - Duplicates and unreadable problems are skipped and recorded.

## Process
1. **Transcription:** a separate agent. Full records, with keys and its own checks, go to
   `corpus/book4_waves/<section>/`. Author copies, with no answer or verification
   fields, go to `eval/run6/problems/`. The developer sees only counts.
2. **Freeze:** the engine after m11 (main at PR #8, plus the parallel test runner) and
   FORMAT.md (`FROZEN.md5`).
3. **Authors:** three fresh Sonnet agents, about 16 problems each.
4. **Grading:** an independent Fable 5.2 (medium) agent re-runs every final scene and
   grades the five dimensions (A interpretation, B correctness, C coverage, D
   educational: not assessed, E textbook answer), as in run 5.
5. **Write-up:** `SCORECARD.md`, top gaps by layer, and a comparison with run 5.

## Exposure
- **Developer:** has not seen any set D or set S statement. m10's agent reported
  structural one-liners for 4 reserved problems (not in this run) and the reasons for 3
  skips.
- **Authors:** nothing of the source.

## Hypotheses (written before the run)
- **H1, set D:** most constant-velocity and wall problems run with full coverage.
  Refusals are clean for light/radar and supersonic cases, with no silent wrong answers.
- **H2, set S:** ratio and comparison questions need no invented values (m9 and m11),
  so fewer hand steps than in run 5.
- **H3:** known gaps still show up: composite and driven resonators, sound at boundaries
  between media, tension set by mechanics.
