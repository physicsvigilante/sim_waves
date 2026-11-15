# Run 5: broad blind test on a new source (book chapter "Waves", wanes_full.pdf)

- **Source:** the practice exercises and JEE archives of the chapter (pages 82–121).
  - 80 problems were sampled at random, stratified by question type
    (`corpus/book4_waves/candidates.json`, seed 20261115).
  - The sample excludes Doppler problems and duplicates of the existing corpus.
  - Unsampled problems stay untranscribed and sealed for later tests.
- **Transcription:** three Sonnet agents read the page images and wrote the records with
  the book keys and their own checks. The developer saw only counts.
- **Exposure:**
  - **What the developer saw before the run:** the chapter's opening pages and table of
    contents; a few lines of its theory pages about sound level; and, while counting the
    answer-key pages, the key letters for practice single-correct questions 1–183 and
    multiple-correct questions 1–25 (keys only, no statements).
  - **What the authors saw:** nothing of the source.
- **Engine:** after milestones 6–8 (main at PR #4).
- **Authors:** four fresh Sonnet agents, 20 problems each.
- **Grading:** an independent Fable 5.2 agent.
