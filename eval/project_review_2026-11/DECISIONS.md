# Project review after milestone 15a: decisions (2026-11-25)

The owner accepted the five recommendations of the project review. Inputs:
- the architecture debate, [debates_simwaves #1](https://github.com/physicsvigilante/debates_simwaves/issues/1);
- the independent assessment ([text](https://github.com/physicsvigilante/debates_simwaves/blob/686f2f6c4119441c142f415ab31d415c8075487a/debates/independent-assessment-sim-waves.md));
- Opus's response ([text](https://github.com/physicsvigilante/debates_simwaves/blob/819941fbe374ed780f1d478707c043dab09b8b5d/debates/opus-response-independent-assessment.md));
- Astra's response ([text](https://github.com/physicsvigilante/debates_simwaves/blob/ad6c44cdddc7c4d52e7aee5569c4b42fb18ce3ff/debates/astra-response-opus-independent-assessment.md)).

The baseline was `main` at `7244bb6`. These decisions authorise no build: each milestone still needs its own PLAN, approved by the owner.

## 1. Order of the next milestones

| Step | Milestone | Open defects it takes |
|---|---|---|
| 0 | **Fence bundle:** a fix or a sound refusal for six live wrong answers, with valid-neighbour tests written as single-observable scenes. Proposed without a blind stage, since fences are refusals (to be stated in its PLAN) | D3-6 (fix), D3-2, D3-1, D3-3, D2-3, D4-5 |
| 1 | **Reference Contract Integrity:** honest test grading | G1, D4-10, D4-11, D5-1, D5-2, D5-3 |
| 2 | **Units and checked binding:** dimensions as constraints; the textbook x/t convention as an explicit context; solved values applied before decisions; observations that leave no state behind | H17-3, D4-1 to D4-4, D4-6 to D4-9, D5-4, H17-4, D1-5, D1-6, D2-4, D2-5, G2, and the full D4-5 fix |
| 3 | **Solution-set and search contracts** | H17-1, H17-2, D1-2, D1-3, D1-4, D1-7, D2-1, D2-2, D1-1 (message), G3, and the full D2-3 fix |
| 4 | **Physical applicability** | H17-5, D3-4, D3-5, and the full D3-1, D3-2, D3-3 fixes |
| 5 | **Physical composition:** pipe pressure and particle velocity first, then the waveguide designs (P-A, P-B) if they pay | new capability |
| 6 | **Broad stratified evaluation** | evidence |

The next four steps are about correctness; new combinations of phenomena wait until step 5.

## 2. Blind stage for M1

For M1, a separate agent writes **reserved grading cases**: reference and result pairs, with independently computed verdicts, including mutated and unresolved cases. They replace a fresh author solving book problems, which would test authoring, not grading. This follows the m15a precedent. Every other charter safeguard stays:
- reserved cases stay out of git until the blind run;
- independent review;
- a separately approved freeze;
- the stage-2 update of the same PR.

## 3. The defect ledger

Every open defect has a fix or fence now, or a required repair in a named milestone. **No known wrong answer is waived.** The ledger is `eval/KNOWN_ISSUES.md`.

## 4. Test totals already reported

Frozen RESULT files, hashes and CI logs stay unchanged. Once M1's grade inventory exists, a versioned erratum linked from each affected report will distinguish "the old harness said PASS" from "the reference now matches". It does not reconstruct exact counts for past revisions. (See G1: until M1, the harness grades symbolic expectations PASS without requiring the comparison to succeed.)

## 5. Review policy

`CLAUDE.md` gains points 7–11: scope by the rule, not by files; review the rule before the examples; systematic transformation and composition tests; separate ledgers; no waiver of a known wrong answer. The stop rule for repeated structural causes (point 5) is kept.
